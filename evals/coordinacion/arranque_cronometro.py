# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""K-82 (M8h): el ensayo del ensayo del criterio 3. Ejecuta, en dos clones de este portátil, los comandos de
docs/hackathon-os/arranque.md («Los 10 minutos» o su variante sin GitHub) y cronometra cada paso hasta que la web del
relay muestra a las dos personas. Mide el tiempo de máquina: lo que tarda una persona en leer, escribir y pegar se
estima aparte (el informe lo suma con un tiempo por paso humano).

  --modo github      origin = un bare local (nada se sube a GitHub); el relay sondea el sandbox de solo lectura y
                     `hk-os compilar --seco` (sin escrituras: las tareas ya están compiladas desde M8e). La persona B usa
                     su propia cuenta de gh (--gh-b, una carpeta de GH_CONFIG_DIR).
  --modo sin-github  `github: no`, `hk-os remoto --iniciar` y `unir --persona [--remoto]`; B clona del remoto.
  --con-claude       la sesión de cada persona es un `claude -p` real con Haiku (gasta; ~0,01–0,03 USD por sesión).
                     Sin él, se simula el SessionStart con los hooks reales (sesion.sh y emite.sh).

Uso: uv run --no-project evals/coordinacion/arranque_cronometro.py --modo sin-github [--con-claude]
     uv run --no-project evals/coordinacion/arranque_cronometro.py --modo github --repo Mveradc/hk-sandbox \
         --a mveradc --b hk-persona-b --gh-b C:/Users/mvera/.config/gh-persona-b [--con-claude]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(AQUI))
sys.path[:0] = [os.path.join(KIT, "hkos"), AQUI]
import colisiones_vivo as cv  # noqa: E402
from red import leer_texto  # noqa: E402

PLAN = os.path.join(KIT, "skills", "hack-plan", "examples", "03-xray-embat-real-plan.md")
CLI = os.path.join(KIT, "hkos", "cli.py")
ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
# Segundos que tarda una persona en lo que no es máquina (leer el chat, pegar, abrir el navegador). Estimación.
HUMANO = {"os.md": 60, "relay": 20, "compilar": 10, "pegar": 30, "pull": 10, "unir": 30, "sesion": 20, "web": 20}
pasos, procesos, coste = [], [], [0.0]


def paso(quien, que, f, humano=0):
    t = time.perf_counter()
    r = f()
    s = time.perf_counter() - t
    pasos.append((quien, que, s, humano))
    print(f"{s:7.1f} s  +{humano:3d} s  {quien}: {que}", flush=True)
    return r


def sh(cwd, *args, env=None, check=True):
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, env=dict(ENV, **(env or {})), timeout=300)
    if check and r.returncode:
        raise SystemExit(f"{' '.join(args)}: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def hk(cwd, *args, env=None):
    return sh(cwd, "uv", "run", "--no-project", "--quiet", CLI, *args, env=env)


def fondo(cwd, args, log, env=None):
    p = subprocess.Popen(["uv", "run", "--no-project", "--quiet", CLI, *args], cwd=cwd, stdout=open(log, "w"),
                         stderr=subprocess.STDOUT, env=dict(ENV, **(env or {})))
    procesos.append(p)
    return p


def leer(log):
    return open(log, encoding="utf-8", errors="replace").read()


def sesion(clon, persona, con_claude, env, usuario):
    if con_claude:
        claude = shutil.which("claude")
        r = subprocess.run([claude, "-p", "Responde solo: hola", "--model", "haiku", "--plugin-dir",
                            KIT.replace("\\", "/"), "--output-format", "json"], cwd=clon, capture_output=True,
                           env=dict(ENV, **env), timeout=300)
        try:
            coste[0] += json.loads(r.stdout.decode("utf-8", "replace")).get("total_cost_usd", 0)
        except ValueError:
            print(r.stdout.decode("utf-8", "replace")[-500:], r.stderr.decode("utf-8", "replace")[-500:])
        return
    sid = f"crono-{persona}"
    entrada = json.dumps({"hook_event_name": "SessionStart", "session_id": sid, "source": "startup", "cwd": clon}).encode()
    for script in (("coordinacion", "sesion.sh"), ("os", "emite.sh")):
        subprocess.run([cv.BASH, os.path.join(KIT, "scripts", *script)], input=entrada, cwd=clon, capture_output=True,
                       env=dict(ENV, **env), timeout=60)


def visibles(url, token, personas):
    try:
        req = urllib.request.Request(url + "/v1/vista", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=5) as r:
            v = json.loads(r.read())["vista"]
    except (OSError, ValueError):
        return False
    vistas = {p["persona"] for p in v["personas"] if p["activos"] or p["ultima_senal"]}
    return set(personas) <= vistas


def matar_todo(tmp):
    for p in procesos:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.terminate()
    # Los demonios los lanzó SessionStart, desacoplados: se buscan por su carpeta.
    if os.name == "nt":
        filtro = tmp.replace("\\", "\\\\").replace("'", "''")
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*{filtro}*' }} | "
                        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                       capture_output=True)
    else:
        subprocess.run(["pkill", "-f", tmp], capture_output=True)


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--modo", choices=("github", "sin-github"), required=True)
    p.add_argument("--con-claude", action="store_true")
    p.add_argument("--repo", default="equipo/reto")
    p.add_argument("--a", default="persona-a")
    p.add_argument("--b", default="persona-b")
    p.add_argument("--gh-b", help="GH_CONFIG_DIR de la persona B (modo github)")
    p.add_argument("--puerto", type=int, default=0)
    p.add_argument("--resumen", action="store_true", help="al final, hk-os recoger y ensayo/resumen.py")
    p.add_argument("--conservar", action="store_true", help="no borra la carpeta temporal ni para nada (depurar)")
    a = p.parse_args(argv)
    sin = a.modo == "sin-github"
    tmp = tempfile.mkdtemp(prefix="hk-arranque-")
    try:
        return prueba(a, sin, tmp)
    finally:
        if a.conservar:
            print(f"Conservado: {tmp}")
            return
        matar_todo(tmp)
        time.sleep(1)
        shutil.rmtree(tmp, ignore_errors=True)


def prueba(a, sin, tmp):
    pa, pb = a.a.lower(), a.b.lower()
    env_a = {"HK_GH": "false"} if sin else {}
    env_b = {"HK_GH": "false"} if sin else ({"GH_CONFIG_DIR": a.gh_b} if a.gh_b else {})
    if sin:
        env_a["HKOS_GITHUB_API"] = env_b["HKOS_GITHUB_API"] = "http://127.0.0.1:9"     # sin internet
    origen = os.path.join(tmp, "origen.git")
    sh(tmp, "git", "init", "-q", "--bare", "-b", "main", origen)
    semilla = os.path.join(tmp, "semilla")
    sh(tmp, "git", "clone", "-q", origen, semilla)
    for k, v in (("user.email", "s@example.com"), ("user.name", "S")):
        sh(semilla, "git", "config", k, v)
    cv.escribe(semilla, ".hackathon/coordinacion.md",
               f"# Coordinación\nactiva: sí\nrepo: {a.repo}\n\n| Persona | GitHub |\n|---|---|\n"
               f"| Persona A | @{pa} |\n| Persona B | @{pb} |\n")
    cv.escribe(semilla, ".hackathon/plan.md", leer_texto(PLAN))
    cv.escribe(semilla, ".gitignore", ".claude/worktrees/\n")
    sh(semilla, "git", "add", "-A")
    sh(semilla, "git", "commit", "-qm", "La cadena del kit, hecha")
    sh(semilla, "git", "push", "-q", "origin", "HEAD:main")
    ca, cb = os.path.join(tmp, "a"), os.path.join(tmp, "b")
    sh(tmp, "git", "clone", "-q", origen, ca)
    if not sin:
        sh(tmp, "git", "clone", "-q", origen, cb)
    for c, u in ((ca, pa), (cb, pb)):
        if os.path.isdir(c):
            sh(c, "git", "config", "user.email", f"{u}@example.com")
            sh(c, "git", "config", "user.name", u)
    puerto = a.puerto or cv.libre()
    print(f"\n== Arranque cronometrado, modo {a.modo}{' con Claude (Haiku)' if a.con_claude else ''} ==\n", flush=True)
    t0 = time.perf_counter()

    def os_md():
        cv.escribe(ca, ".hackathon/os.md", f"# Hackathon OS\nactiva: sí\nrelay: http://127.0.0.1:{puerto}\n"
                   + ("github: no\n" if sin else ""))
        sh(ca, "git", "add", ".hackathon/os.md")
        sh(ca, "git", "commit", "-qm", "Hackathon OS activo")
        if not sin:
            sh(ca, "git", "push", "-q", "origin", "HEAD:main")
    paso("coordina", "os.md activo, commit" + ("" if sin else " y push"), os_md, HUMANO["os.md"])
    url_r = None
    if sin:
        log_r = os.path.join(tmp, "remoto.log")
        puerto_r = cv.libre()

        def remoto():
            fondo(ca, ["remoto", "--iniciar", "--ip", "127.0.0.1", "--puerto", str(puerto_r)], log_r, env_a)
            if not cv.espera(lambda: "Remoto del equipo en" in leer(log_r), 60, 0.2):
                raise SystemExit("hk-os remoto no arranca:\n" + leer(log_r))
            sh(ca, "git", "push", "-q", "origin", "HEAD:main")
        paso("coordina", "hk-os remoto --iniciar y git push", remoto, HUMANO["relay"])
        url_r = f"http://127.0.0.1:{puerto_r}/equipo.git"
    log = os.path.join(tmp, "relay.log")

    def relay():
        fondo(ca, ["relay", "--ip", "127.0.0.1", "--puerto", str(puerto)], log, env_a)
        if not cv.espera(lambda: "Token: " in leer(log), 60, 0.2):
            raise SystemExit("hk-os relay no arranca:\n" + leer(log))
    paso("coordina", "hk-os relay", relay, HUMANO["relay"])
    token = next(l.split("Token: ", 1)[1].strip() for l in leer(log).splitlines() if "Token: " in l)
    url = f"http://127.0.0.1:{puerto}"
    if not sin:
        paso("coordina", "hk-os compilar --seco (las tareas ya están en el sandbox)", lambda: hk(ca, "compilar", "--seco", env=env_a),
             HUMANO["compilar"])
    pasos.append(("coordina", "pegar la línea de unir y la de la web en el chat", 0.0, HUMANO["pegar"]))
    unir_a = ["unir", url, token] + (["--persona", pa] if sin else [])
    salida_a = paso("coordina", "hk-os unir" + (" --persona" if sin else ""), lambda: hk(ca, *unir_a, env=env_a), HUMANO["unir"])
    if sin:
        def clonar():
            sh(tmp, "git", "-c", f"http.extraHeader=Authorization: Bearer {token}", "-c", "credential.helper=", "clone", "-q",
               url_r, cb, env={"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": ""})
            sh(cb, "git", "config", "user.email", f"{pb}@example.com")
            sh(cb, "git", "config", "user.name", pb)
        paso("persona B", "git clone del remoto (con la cabecera del token)", clonar, HUMANO["pull"])
        salida_b = paso("persona B", "hk-os unir --persona --remoto",
                        lambda: hk(cb, "unir", url, token, "--persona", pb, "--remoto", url_r, env=env_b), HUMANO["unir"])
    else:
        paso("persona B", "git pull", lambda: sh(cb, "git", "pull", "-q"), HUMANO["pull"])
        salida_b = paso("persona B", "hk-os unir", lambda: hk(cb, "unir", url, token, env=env_b), HUMANO["unir"])
    print("        " + salida_a.strip().replace("\n", "\n        "))
    print("        " + salida_b.strip().replace("\n", "\n        "))
    for c, u, e, h in ((ca, "A", env_a, pa), (cb, "B", env_b, pb)):
        paso(f"persona {u}", "sesión nueva" + (" (claude -p, Haiku)" if a.con_claude else " (SessionStart simulado)"),
             lambda c=c, u=u, e=e, h=h: sesion(c, u, a.con_claude, e, h), HUMANO["sesion"])
    ok = paso("las dos", "la web muestra a las dos personas", lambda: cv.espera(lambda: visibles(url, token, (pa, pb)), 120, 0.5),
              HUMANO["web"])
    maquina = time.perf_counter() - t0
    humano = sum(h for _, _, _, h in pasos)
    if a.resumen:   # recoger y resumen.py sobre lo que ha quedado (prueba de punta a punta del análisis del ensayo)
        cv.escribe(cb, "web/x.js", "// x\n")
        sh(cb, "git", "add", "-A")
        sh(cb, "git", "commit", "-qm", "T11 · algo")
        sh(cb, "git", "push", "-q", "origin", "HEAD:main", env={"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": ""})
        time.sleep(80)                            # el demonio de B trae origin cada 60 s
        zips = []
        for c in (ca, cb):
            z = os.path.join(tmp, f"recogido-{os.path.basename(c)}.zip")
            print(hk(c, "recoger", "--salida", z, env=env_a).strip())
            zips.append(z)
        informe = os.path.join(tmp, "resumen.md")
        print(sh(KIT, "uv", "run", "--no-project", os.path.join(AQUI, "ensayo", "resumen.py"), "--zips", *zips,
                 "--informe", informe)[:3000])
    if not ok:
        for c in (ca, cb):
            for f in ("arranque.log", "agente.log"):
                ruta = os.path.join(c, ".git", "hackathon", "os", f)
                print(f"--- {ruta}\n{leer(ruta)[-800:] if os.path.exists(ruta) else '(no existe)'}")
        print(f"--- relay.log\n{leer(log)[-800:]}")
    print(f"\n{'OK' if ok else 'FALLO'}: tiempo de máquina {maquina:.0f} s; con la estimación de lo humano, "
          f"{(maquina + humano) / 60:.1f} min (criterio 3: ≤ 10 min)."
          + (f" Gasto en Claude: {coste[0]:.3f} USD." if a.con_claude else ""))
    print("\n| Quién | Paso | Máquina (s) | Persona (s, estimado) |\n|---|---|---|---|")
    for q, que, s, h in pasos:
        print(f"| {q} | {que} | {s:.1f} | {h} |")
    return 0 if ok and maquina + humano <= 600 else 1


if __name__ == "__main__":
    sys.exit(main())
