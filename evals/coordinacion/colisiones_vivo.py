# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterios 1, 2 y 6 de M8g con las piezas de verdad y sin modelo: dos clones de un remoto `bare` local (una persona
por clon), hooks reales del plugin (emite.sh y arbol.sh, con entradas con la forma de las de Claude Code), un demonio
por clon (hkos/agente.py) y un relay (hkos/relay.py) con `publicar_wip: sí`. Sin red ni GitHub.

  - C6: dos workers de A (dos worktrees, dos agent_id) sobre ficheros distintos y luego sobre el mismo: ninguna
    colisión.
  - C1 (G5): A y B cambian el mismo fichero en líneas distintas: amarillo en el estado-equipo.md de las dos; se mide
    desde la segunda edición (criterio: ≤ 30 s).
  - C2 (G5b): cambios incompatibles en la misma línea: rojo de nivel 2 con el fichero en las dos, antes de cualquier
    push a main. El índice (bytes), `git status`, el stash y HEAD de las dos copias no cambian mientras publica; ni
    .env ni datos/ ni un commit local con datos llegan al remoto, y .env tampoco es un objeto en la copia de la persona;
    el pre-push que falla de B no frena la publicación; /salud y wip.json dicen qué se publicó; al limpiar, la ref se
    borra.

Uso: uv run --no-project evals/coordinacion/colisiones_vivo.py      (0 OK · 1 falla; tarda unos 3 minutos)
"""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe"))
                 if os.path.exists(b)), BASH)
APP = "".join(f"linea {i}\n" for i in range(20))
fallos = 0
procesos = []


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(("OK    " if ok else "FALLO ") + nombre + ("" if ok or not detalle else f"\n        {detalle}"), flush=True)


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.decode()}")
    return r.stdout.decode().strip()


def escribe(repo, ruta, texto):
    p = os.path.join(repo, ruta)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="\n", encoding="utf-8") as f:
        f.write(texto)


def libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def lanza(args, log):
    p = subprocess.Popen(["uv", "run", "--no-project", "--quiet", *args], stdout=open(log, "w"), stderr=subprocess.STDOUT)
    procesos.append(p)
    return p


def hook(script, entrada, cwd):
    subprocess.run([BASH, os.path.join(KIT, "scripts", "os", script)], input=json.dumps(entrada).encode(), cwd=cwd,
                   capture_output=True, timeout=30)


class Sesion:
    """Una sesión (o un worker) que pasa por los hooks reales lo que haría Claude Code al editar."""

    def __init__(self, sid, cwd, agente=None):
        self.sid, self.cwd, self.agente, self.n = sid, cwd, agente, 0

    def base(self, evento):
        d = {"session_id": self.sid, "cwd": self.cwd, "hook_event_name": evento}
        if self.agente:
            d.update(agent_id=self.agente, agent_type="hackathon-kit:worker")
        return d

    def inicio(self):
        hook("emite.sh", dict(self.base("SessionStart"), source="startup"), self.cwd)

    def edita(self, ruta, texto):
        escribe(self.cwd, ruta, texto)
        self.n += 1
        d = dict(self.base("PostToolUse"), tool_name="Edit", tool_use_id=f"toolu_{self.sid}_{self.n}",
                 tool_input={"file_path": os.path.join(self.cwd, ruta), "old_string": "a", "new_string": "b"})
        hook("emite.sh", d, self.cwd)
        self.arbol()

    def arbol(self):
        hook("arbol.sh", self.base("PostToolBatch"), self.cwd)

    def fin_worker(self):
        hook("emite.sh", self.base("SubagentStop"), self.cwd)


def md(repo):
    try:
        with open(os.path.join(repo, ".git", "hackathon", "os", "estado-equipo.md"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def colisiones_md(repo):
    texto, sec, salida = md(repo), None, []
    for l in texto.splitlines():
        if l.startswith("## "):
            sec = l
        elif sec == "## Colisiones que te afectan" and l.startswith("- ") and l != "- ninguna":
            salida.append(l)
    return salida


def estado(url, token):
    req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def salud(puerto):
    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/salud", timeout=5) as r:
        return r.read().decode()


def espera(cond, segundos, paso=0.5):
    fin = time.time() + segundos
    while time.time() < fin:
        if cond():
            return True
        time.sleep(paso)
    return cond()


def foto(repo):
    with open(os.path.join(repo, ".git", "index"), "rb") as f:
        indice = hashlib.sha256(f.read()).hexdigest()
    return (indice, git(repo, "status", "--porcelain=v2", "--untracked-files=all"), git(repo, "stash", "list"),
            git(repo, "rev-parse", "HEAD"))


def hay_blob(repo, texto):
    sha = subprocess.run(["git", "hash-object", "--stdin"], input=texto.encode(), capture_output=True).stdout.decode().strip()
    return subprocess.run(["git", "-C", repo, "cat-file", "-e", sha], capture_output=True).returncode == 0


def main():
    for flujo in (sys.stdout, sys.stderr):  # en Windows, con la salida redirigida, cp1252 no sabe escribir «≤» (issue #18)
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="hk-colisiones-")
    try:
        return prueba(tmp)
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
                p.kill()
        shutil.rmtree(tmp, ignore_errors=True)


def prueba(tmp):
    remoto = os.path.join(tmp, "remoto.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remoto], check=True)
    semilla = os.path.join(tmp, "semilla")
    subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", remoto, semilla], check=True, capture_output=True)
    for k, v in (("user.email", "semilla@example.com"), ("user.name", "S")):
        git(semilla, "config", k, v)
    puerto_relay = libre()
    escribe(semilla, "app.py", APP)
    escribe(semilla, "motor/x.py", "x = 1\n")
    escribe(semilla, "web/comun.js", "// comun\n")
    escribe(semilla, ".gitignore", ".claude/worktrees/\n")
    escribe(semilla, ".hackathon/os.md", f"# Hackathon OS\nactiva: sí\nrelay: http://127.0.0.1:{puerto_relay}\n"
                                         "publicar_wip: sí\ndatos_excluidos: data/, datos/\n")
    escribe(semilla, ".hackathon/coordinacion.md", "# Coordinación\nactiva: sí\nrepo: alguien/sandbox\n\n"
                                                   "| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n| B | @persona-b |\n")
    git(semilla, "add", "-A")
    git(semilla, "commit", "-qm", "inicio")
    git(semilla, "push", "-q", "origin", "HEAD:main")
    clones, puertos = {}, {}
    for persona in ("persona-a", "persona-b"):
        c = os.path.join(tmp, persona)
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", remoto, c], check=True, capture_output=True)
        git(c, "config", "user.email", f"{persona}@example.com")
        git(c, "config", "user.name", persona)
        os.makedirs(os.path.join(c, ".git", "hackathon", "os"), exist_ok=True)
        escribe(c, ".git/hackathon/yo-prueba", persona + "\n")          # la caché de hk_yo que lee emite.sh
        clones[persona] = c
    a, b = clones["persona-a"], clones["persona-b"]
    # Relay en el clon de A (quien coordina), sin GitHub, con el nivel 2.
    dir_relay = os.path.join(a, ".git", "hackathon", "os", "relay")
    lanza([os.path.join(KIT, "hkos", "relay.py"), "--dir", dir_relay, "--equipo", os.path.join(a, ".hackathon", "coordinacion.md"),
           "--ip", "127.0.0.1", "--puerto", str(puerto_relay), "--os", os.path.join(a, ".hackathon", "os.md"), "--sin-github"],
          os.path.join(tmp, "relay.log"))
    url = f"http://127.0.0.1:{puerto_relay}"
    espera(lambda: os.path.exists(os.path.join(dir_relay, "token")), 30)
    time.sleep(1)
    token = open(os.path.join(dir_relay, "token")).read().strip()
    # B: un pre-push que falla (la publicación lo salta con --no-verify).
    escribe(b, ".git/hooks/pre-push", "#!/bin/sh\nexit 1\n")
    for persona, c in clones.items():
        d = os.path.join(c, ".git", "hackathon", "os")
        escribe(c, ".git/hackathon/os/relay.url", url + "\n")
        escribe(c, ".git/hackathon/os/token", token + "\n")
        puertos[persona] = libre()
        lanza([os.path.join(KIT, "hkos", "agente.py"), "--repo", c, "--persona", persona, "--puerto", str(puertos[persona]),
               "--apagado-min", "30"], os.path.join(tmp, f"agente-{persona}.log"))
    sa, sb = Sesion("s-a", a), Sesion("s-b", b)
    sa.inicio()
    sb.inicio()
    comprueba("relay y demonios arrancados; el md de cada persona escrito",
              espera(lambda: md(a) and md(b), 60), f"relay.log: {open(os.path.join(tmp, 'relay.log')).read()[-500:]}")

    print("\n== C6: dos workers de la misma persona", flush=True)
    for w in ("w1", "w2"):
        git(a, "worktree", "add", "-q", "-b", f"worktree-agent-{w}", os.path.join(a, ".claude", "worktrees", f"agent-{w}"))
    w1 = Sesion("s-a", os.path.join(a, ".claude", "worktrees", "agent-w1"), "w1")
    w2 = Sesion("s-a", os.path.join(a, ".claude", "worktrees", "agent-w2"), "w2")
    w1.edita("motor/x.py", "x = 2\n")
    w2.edita("motor/y.py", "y = 1\n")
    w2.edita("motor/x.py", "x = 3\n")                    # y luego el mismo fichero que w1
    sa.arbol()                                          # la copia principal ve .claude/worktrees/ sin seguimiento
    visto = espera(lambda: any(x.get("agente") == "w2" and x.get("ficheros")
                               for p in estado(url, token)["personas"] for x in p["actores"]), 30)
    time.sleep(4)
    e = estado(url, token)
    comprueba("C6: los dos workers de A están en el relay y no hay ninguna colisión",
              visto and e["colisiones"] == [], json.dumps(e["colisiones"], ensure_ascii=False))
    w1.fin_worker()
    w2.fin_worker()

    print("\n== C1 (G5): el mismo fichero, cambios compatibles", flush=True)
    sa.edita("app.py", APP.replace("linea 2\n", "linea 2 de A\n"))
    sb.edita("app.py", APP.replace("linea 17\n", "linea 17 de B\n"))
    t2 = time.time()
    ok = espera(lambda: any("AMARILLO · nivel 1" in l and "app.py" in l for l in colisiones_md(a)) and
                any("AMARILLO · nivel 1" in l and "app.py" in l for l in colisiones_md(b)), 60, 0.25)
    t_c1 = time.time() - t2
    comprueba(f"C1: amarillo con app.py en el estado-equipo.md de A y de B a los {t_c1:.1f} s de la segunda edición (≤ 30 s)",
              ok and t_c1 <= 30, f"A: {colisiones_md(a)} · B: {colisiones_md(b)}")
    print("        " + "\n        ".join(colisiones_md(a)), flush=True)

    print("\n== C2 (G5b): cambios incompatibles, publicar_wip: sí", flush=True)
    main_antes = git(remoto, "rev-parse", "main")
    escribe(a, "datos/privado.csv", "dni\nsecreto-commit-local\n")
    git(a, "add", "datos/privado.csv")
    git(a, "commit", "-qm", "datos locales")             # sin subir: no debe viajar con el WIP
    secretos = {".env": "TOKEN=secreto-vivo-env\n", "data/muestra.csv": "secreto-vivo-data\n"}
    for ruta, texto in secretos.items():
        escribe(a, ruta, texto)
    sa.edita("app.py", APP.replace("linea 9\n", "linea 9 segun A\n"))
    sb.edita("app.py", APP.replace("linea 9\n", "linea 9 segun B\n"))
    fotos = {p: foto(c) for p, c in clones.items()}       # después de los hooks: lo que sigue es solo del OS
    t2 = time.time()
    ok = espera(lambda: any("ROJO · nivel 2" in l and "app.py" in l for l in colisiones_md(a)) and
                any("ROJO · nivel 2" in l and "app.py" in l for l in colisiones_md(b)), 200, 1)
    comprueba(f"C2: rojo de nivel 2 con app.py en las dos a los {time.time() - t2:.0f} s (publicación cada 60 s, merge-tree cada 30 s)",
              ok, f"A: {colisiones_md(a)} · B: {colisiones_md(b)} · /salud A: {salud(puertos['persona-a'])} · "
                  f"/salud B: {salud(puertos['persona-b'])} · log A: {open(os.path.join(a, '.git', 'hackathon', 'os', 'agente.log'), encoding='utf-8').read()[-800:]}")
    print("        " + "\n        ".join(colisiones_md(b)), flush=True)
    e = estado(url, token)
    rojo = [c for c in e["colisiones"] if c["nivel"] == "2"]
    comprueba("C2: el amarillo de app.py lo tapa el rojo (mismas personas)",
              rojo and not any(c["nivel"] == "1" and "app.py" in c["rutas"] for c in e["colisiones"]), json.dumps(e["colisiones"]))
    comprueba("C2: antes de cualquier push a main", git(remoto, "rev-parse", "main") == main_antes)
    for p, c in clones.items():
        comprueba(f"C2: índice, status, stash y HEAD de {p} sin cambios mientras publica", foto(c) == fotos[p],
                  f"{fotos[p]} / {foto(c)}")
    refs = {p: subprocess.run(["git", "-C", remoto, "rev-parse", "-q", "--verify", f"refs/hackathon/wip/{p}"],
                              capture_output=True).stdout.decode().strip() for p in clones}
    comprueba("C2: las dos refs WIP en el remoto (la de B, con su pre-push que falla)", all(refs.values()), str(refs))
    ficheros_a = git(remoto, "ls-tree", "-r", "--name-only", refs["persona-a"]).split("\n") if refs["persona-a"] else []
    comprueba("C2: el WIP de A tiene app.py y no .env, data/ ni datos/", "app.py" in ficheros_a and not
              any(f in ficheros_a for f in (".env", "data/muestra.csv", "datos/privado.csv")), str(ficheros_a))
    for texto in [*secretos.values(), "dni\nsecreto-commit-local\n"]:
        comprueba(f"C2: ningún blob de {texto.split(chr(10))[0][:24]!r} en el remoto", not hay_blob(remoto, texto))
    comprueba("C2: .env no es un objeto en la copia de A", not hay_blob(a, secretos[".env"]))
    s_a = salud(puertos["persona-a"])
    wip_json = json.load(open(os.path.join(a, ".git", "hackathon", "os", "wip.json"), encoding="utf-8"))
    comprueba("C2: /salud dice qué se publicó y wip.json lo lista", "wip: " in s_a and "ficheros" in s_a and
              "app.py" in wip_json["ficheros"] and ".env" not in wip_json["ficheros"], s_a + json.dumps(wip_json))
    print("        /salud de A: " + next(l for l in s_a.splitlines() if l.startswith("wip:")), flush=True)
    # Al limpiar, B borra su ref (en la vuelta siguiente: como mucho 60 s).
    escribe(b, "app.py", APP)
    sb.arbol()
    ok = espera(lambda: subprocess.run(["git", "-C", remoto, "rev-parse", "-q", "--verify", "refs/hackathon/wip/persona-b"],
                                       capture_output=True).returncode != 0, 90, 1)
    comprueba("C2: B limpia su árbol y su ref WIP desaparece del remoto", ok)
    ok = espera(lambda: not any(c["nivel"] == "2" for c in estado(url, token)["colisiones"]), 60, 1)
    comprueba("C2: y el rojo se va", ok)
    print(f"\n{fallos} fallos", flush=True)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
