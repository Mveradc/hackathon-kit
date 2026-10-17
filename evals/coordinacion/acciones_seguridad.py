# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterio 6 de M9a (ADR-0010) con las piezas de verdad y sin modelo: un demonio (hkos/agente.py) y un relay
(hkos/relay.py) lanzados como procesos, en un repo temporal con `web_nueva: sí`. Sin red ni GitHub.

  - un token en la query no vale (401), ni en las rutas de datos ni en las de acción;
  - una acción sin token, o con otro, da 401;
  - con un `Host` o un `Origin` ajenos, 403 (DNS rebinding, otra página);
  - como formulario (`text/plain`, `application/x-www-form-urlencoded`), 415;
  - `OPTIONS` (el preflight de otra página) no da cabeceras CORS, y ninguna otra respuesta tampoco;
  - con el token en `X-HK-Token`, JSON y Host local, la acción pasa las comprobaciones;
  - el relay no tiene rutas de acción (404 con su token) y el demonio solo escucha en 127.0.0.1.

Uso: uv run --no-project evals/coordinacion/acciones_seguridad.py      (0 OK · 1 falla; unos 15 s)
"""
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "hkos"))
import relay as relay_mod  # noqa: E402

PERSONA = "persona-b"
fallos = 0
procesos = []


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(("OK    " if ok else "FALLO ") + nombre + ("" if ok or not detalle else f"\n        {detalle}"), flush=True)


def libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lanza(args, log):
    p = subprocess.Popen(["uv", "run", "--no-project", "--quiet", *args], stdout=open(log, "w"), stderr=subprocess.STDOUT)
    procesos.append(p)
    return p


def pide(puerto, metodo, ruta, cabeceras=None, cuerpo=None, host=None):
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=10)
    c.putrequest(metodo, ruta, skip_host=True, skip_accept_encoding=True)
    c.putheader("Host", host or f"127.0.0.1:{puerto}")
    for k, v in (cabeceras or {}).items():
        c.putheader(k, v)
    if cuerpo is not None:
        c.putheader("Content-Length", str(len(cuerpo)))
    c.endheaders(cuerpo)
    r = c.getresponse()
    r.read()
    c.close()
    cabeceras_r = {k.lower(): v for k, v in r.getheaders()}
    cors = [k for k in cabeceras_r if k.startswith("access-control-")]
    return r.status, cors


def espera(condicion, s=30):
    fin = time.time() + s
    while time.time() < fin:
        if condicion():
            return True
        time.sleep(0.2)
    return False


def escucha(puerto):
    try:
        socket.create_connection(("127.0.0.1", puerto), timeout=0.5).close()
        return True
    except OSError:
        return False


def ips_locales():
    """Las IP de esta máquina que no son de loopback (para ver que el demonio no escucha en ellas)."""
    ips = set()
    for familia in (socket.AF_INET, socket.AF_INET6):
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, familia):
                ips.add(info[4][0])
        except OSError:
            pass
    lan = relay_mod.ip_de_lan()
    if lan:
        ips.add(lan)
    return sorted(ip for ip in ips if not ip.startswith(("127.", "::1")) and not ip.startswith("fe80"))


def prueba(tmp):
    repo = os.path.join(tmp, "repo").replace("\\", "/")
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
    os.makedirs(os.path.join(repo, ".hackathon"))
    os_md = os.path.join(repo, ".hackathon", "os.md")
    with open(os_md, "w", encoding="utf-8") as f:
        f.write("# Hackathon OS\nactiva: sí\ngithub: no\nweb_nueva: sí\n")
    coord = os.path.join(repo, ".hackathon", "coordinacion.md")
    with open(coord, "w", encoding="utf-8") as f:
        f.write(f"# Coordinación\nactiva: sí\n\n| Nombre | GitHub |\n|---|---|\n| B | @{PERSONA} |\n")
    dir_os = os.path.join(repo, ".git", "hackathon", "os")
    p_relay, p_agente = libre(), libre()
    lanza([os.path.join(KIT, "hkos", "relay.py"), "--dir", os.path.join(dir_os, "relay"), "--equipo", coord,
           "--ip", "127.0.0.1", "--puerto", str(p_relay), "--os", os_md, "--sin-github"], os.path.join(tmp, "relay.log"))
    lanza([os.path.join(KIT, "hkos", "agente.py"), "--repo", repo, "--persona", PERSONA, "--puerto", str(p_agente),
           "--apagado-min", "5"], os.path.join(tmp, "agente.log"))
    token_web = os.path.join(dir_os, "web.token")
    if not (espera(lambda: escucha(p_relay)) and espera(lambda: escucha(p_agente) and os.path.exists(token_web))):
        comprueba("el relay y el demonio arrancan", False, f"logs en {tmp}")
        return
    with open(token_web, encoding="utf-8") as f:
        t = f.read().strip()
    with open(os.path.join(dir_os, "relay", "token"), encoding="utf-8") as f:
        t_relay = f.read().strip()
    tok = {"X-HK-Token": t}
    js = {"Content-Type": "application/json"}
    cuerpo = json.dumps({"tarea": "T01"}).encode()
    cors = []

    def caso(nombre, esperado, metodo, ruta, cabeceras=None, datos=None, host=None, puerto=p_agente):
        codigo, c = pide(puerto, metodo, ruta, cabeceras, datos, host)
        cors.extend(c)
        ok = codigo in esperado if isinstance(esperado, tuple) else codigo == esperado
        comprueba(f"{nombre}: {codigo}", ok, f"se esperaba {esperado}")

    caso("token en la query de una acción, sin cabecera", 401, "POST", f"/v1/anotar?t={t}", js, cuerpo)
    caso("token en la query de los datos", 401, "GET", f"/v1/vista?t={t}")
    caso("token en la query del stream", 401, "GET", f"/v1/stream?token={t}")
    caso("token en la query junto a la cabecera buena", 401, "GET", f"/v1/vista?t={t}", tok)
    caso("acción sin token", 401, "POST", "/v1/reclamar", js, cuerpo)
    caso("acción con otro token", 401, "POST", "/v1/reclamar", dict(js, **{"X-HK-Token": "0" * 64}), cuerpo)
    caso("Host ajeno (DNS rebinding)", 403, "POST", "/v1/reclamar", dict(js, **tok), cuerpo, f"evil.example:{p_agente}")
    caso("Host ajeno en los datos", 403, "GET", "/v1/vista", tok, host=f"evil.example:{p_agente}")
    caso("Origin ajeno", 403, "POST", "/v1/anotar", dict(js, **tok, Origin="http://evil.example"), cuerpo)
    caso("Origin de otro puerto local", 403, "POST", "/v1/anotar",
         dict(js, **tok, Origin=f"http://127.0.0.1:{p_relay}"), cuerpo)
    caso("formulario text/plain", 415, "POST", "/v1/anotar", {"Content-Type": "text/plain"}, cuerpo)
    caso("formulario urlencoded", 415, "POST", "/v1/reclamar", {"Content-Type": "application/x-www-form-urlencoded"},
         b"tarea=T01")
    caso("OPTIONS (preflight)", 405, "OPTIONS", "/v1/anotar", {
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-hk-token, content-type"})
    caso("acción con token, JSON y Host local: pasa las comprobaciones", tuple(c for c in range(200, 600)
                                                                               if c not in (401, 403, 415)),
         "POST", "/v1/reclamar", dict(js, **tok), cuerpo, f"localhost:{p_agente}")
    caso("datos con token y Origin local", (200, 503), "GET", "/v1/vista", dict(tok, Origin=f"http://127.0.0.1:{p_agente}"))
    comprueba("ninguna respuesta del demonio lleva cabeceras CORS", not cors, ", ".join(sorted(set(cors))))
    for ruta in ("/v1/anotar", "/v1/reclamar"):
        caso(f"el relay no tiene {ruta}", 404, "POST", ruta, dict(js, Authorization=f"Bearer {t_relay}"), cuerpo,
             puerto=p_relay)
    ips = ips_locales()
    abiertas = []
    for ip in ips:
        try:
            socket.create_connection((ip, p_agente), timeout=3).close()
            abiertas.append(ip)
        except OSError:
            pass
    comprueba(f"el demonio solo escucha en 127.0.0.1 (probadas: {', '.join(ips) or 'ninguna otra IP'})", not abiertas,
              f"responde en {', '.join(abiertas)}")


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="hk-seguridad-")
    try:
        prueba(tmp)
    finally:
        for p in procesos:   # `uv run` deja un python hijo: en Windows, terminate() solo mata a uv
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
            else:
                p.terminate()
        for p in procesos:
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                pass
        if not fallos:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'Todo bien' if not fallos else f'{fallos} fallos'}.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
