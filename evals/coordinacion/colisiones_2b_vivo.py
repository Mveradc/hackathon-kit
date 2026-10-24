# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterios 1 (la parte con el relay vivo), 4 (la línea del monitor) y 5 de M11 con las piezas de verdad y sin modelo:
un remoto `bare` local, dos clones (una persona por clon) con los hooks reales del plugin, un demonio por clon, el
monitor de cada persona (scripts/coordinacion/escucha.sh, con un gh falso) y el relay en el clon de A con
`publicar_wip: sí`, `fusion_estructural: sí` y Mergiraf (≥ 0.20.0) de verdad en el PATH. Sin red ni GitHub.

  - C5, paso 1: A y B añaden un `import` distinto en el mismo sitio de app.py (y A cambia además `return 2`, lejos).
    Para git es un conflicto (merge-tree da 1, y un relay con 2b apagado lo da rojo); en ≤ 90 s desde que los dos
    trabajos en curso están en el remoto, amarillo `2b` en el estado-equipo.md de las dos, sin rojo, sin el nivel 1
    de app.py y sin ninguna línea del monitor.
  - C1: cinco relays más, cada uno en su clon del mismo remoto y con un `mergiraf` falso (hkos/pruebas/mergiraf_falso.py)
    que anota todas sus llamadas, también `--version`: con `fusion_estructural:` ausente, en `no`, con `publicar_wip:
    no`, con `sí` y sin mergiraf en el PATH y con `sí` y mergiraf 0.19.1. Ninguno ejecuta `mergiraf merge`; los tres
    primeros ni lo buscan; los de `sí` lo dicen una vez al arrancar y siguen con el nivel 2 (rojo). Un sexto, con el
    falso en 0.20.0, sí lo llama (comprueba que el registro funciona).
  - C5, paso 2: B cambia la misma línea que A (`return 2`): rojo de nivel 2 en ≤ 90 s desde su publicación, con una
    línea del monitor de cada persona.
  - En los dos pasos: los ficheros, el índice, `git status`, el stash y HEAD de las dos copias no cambian mientras
    trabaja el OS, ni las refs del clon del relay (salvo refs/hackathon/relay-wip/, que son las del nivel 2); no queda
    nada en el temporal del relay ni copias nuevas de Mergiraf en el sitio de siempre.

Uso: uv run --no-project evals/coordinacion/colisiones_2b_vivo.py      (0 OK · 1 falla; tarda unos 5 minutos)
     Hace falta mergiraf ≥ 0.20.0 en el PATH (solo para la prueba; el kit no lo instala).
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
PRUEBAS = os.path.join(KIT, "hkos", "pruebas")
ESCUCHA = os.path.join(KIT, "scripts", "coordinacion", "escucha.sh").replace("\\", "/")
BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe"))
                 if os.path.exists(b)), BASH)
UV = shutil.which("uv")
BASE = '"""App de prueba."""\nimport os\nimport sys\n\n\ndef uno():\n    return 1\n\n\ndef dos():\n    return 2\n'
APP_A = BASE.replace("import sys\n", "import sys\nimport json\n").replace("return 2\n", "return 20\n")
APP_B = BASE.replace("import sys\n", "import sys\nimport re\n")
APP_B2 = APP_B.replace("return 2\n", "return 30\n")
LINEA_2B = "AMARILLO · nivel 2b · fusión estructural sin conflictos"
PLAZO = 90
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


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def lanza(args, log, env=None):
    p = subprocess.Popen([UV, "run", "--no-project", "--quiet", *args], stdout=open(log, "w"), stderr=subprocess.STDOUT,
                         env=dict(env or os.environ, PYTHONUNBUFFERED="1"))
    procesos.append(p)
    return p


def hook(script, entrada, cwd):
    subprocess.run([BASH, os.path.join(KIT, "scripts", "os", script)], input=json.dumps(entrada).encode(), cwd=cwd,
                   capture_output=True, timeout=30)


class Sesion:
    """Una sesión que pasa por los hooks reales lo que haría Claude Code al editar (como en colisiones_vivo.py)."""

    def __init__(self, sid, cwd):
        self.sid, self.cwd, self.n = sid, cwd, 0

    def base(self, evento):
        return {"session_id": self.sid, "cwd": self.cwd, "hook_event_name": evento}

    def inicio(self):
        hook("emite.sh", dict(self.base("SessionStart"), source="startup"), self.cwd)

    def edita(self, ruta, texto):
        escribe(self.cwd, ruta, texto)
        self.n += 1
        d = dict(self.base("PostToolUse"), tool_name="Edit", tool_use_id=f"toolu_{self.sid}_{self.n}",
                 tool_input={"file_path": os.path.join(self.cwd, ruta), "old_string": "a", "new_string": "b"})
        hook("emite.sh", d, self.cwd)
        hook("arbol.sh", self.base("PostToolBatch"), self.cwd)


def md(repo):
    return leer(os.path.join(repo, ".git", "hackathon", "os", "estado-equipo.md"))


def colisiones_md(repo):
    sec, salida = None, []
    for l in md(repo).splitlines():
        if l.startswith("## "):
            sec = l
        elif sec == "## Colisiones que te afectan" and l.startswith("- ") and l != "- ninguna":
            salida.append(l)
    return salida


def con_2b(repo):
    return any(LINEA_2B in l and "app.py" in l for l in colisiones_md(repo))


def con_rojo(repo):
    return any(l.startswith("- ROJO · nivel 2 · ") and "app.py" in l for l in colisiones_md(repo))


def estado(url, token):
    req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def estado_o_nada(url, token):
    try:
        return estado(url, token)
    except (OSError, ValueError):
        return {"colisiones": []}


def espera(cond, segundos, paso=0.5):
    fin = time.time() + segundos
    while time.time() < fin:
        if cond():
            return True
        time.sleep(paso)
    return cond()


def sha_texto(texto):
    return subprocess.run(["git", "hash-object", "--stdin"], input=texto.encode(), capture_output=True).stdout.decode().strip()


def en_wip(remoto, persona, texto):
    """¿El trabajo en curso de `persona` en el remoto tiene app.py con este contenido?"""
    r = subprocess.run(["git", "-C", remoto, "rev-parse", "-q", "--verify", f"refs/hackathon/wip/{persona}:app.py"],
                       capture_output=True)
    return r.returncode == 0 and r.stdout.decode().strip() == sha_texto(texto)


def foto(repo):
    """Los ficheros (sin .git), el índice, `git status`, el stash y HEAD de una copia."""
    ficheros = {}
    for d, subs, nombres in os.walk(repo):
        subs[:] = [s for s in subs if s != ".git"]
        for n in nombres:
            p = os.path.join(d, n)
            with open(p, "rb") as f:
                ficheros[os.path.relpath(p, repo)] = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.join(repo, ".git", "index"), "rb") as f:
        indice = hashlib.sha256(f.read()).hexdigest()
    return (ficheros, indice, git(repo, "status", "--porcelain=v2", "--untracked-files=all"), git(repo, "stash", "list"),
            git(repo, "rev-parse", "HEAD"))


def refs_relay(repo):
    """Las refs del clon del relay, sin las del nivel 2 (refs/hackathon/relay-wip/, que trae el relay a propósito)."""
    return [l for l in git(repo, "for-each-ref", "--format=%(refname) %(objectname)").splitlines()
            if not l.startswith("refs/hackathon/relay-wip/")]


def copias_mergiraf():
    """Lo que hay en el sitio donde Mergiraf guarda sus copias por defecto (P12 y P17)."""
    if os.name == "nt":
        d = os.path.join(os.environ.get("APPDATA", ""), "Mergiraf contributors", "Mergiraf", "data", "merges")
    else:
        d = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "mergiraf", "merges")
    return d, sorted(os.listdir(d)) if os.path.isdir(d) else []


def falso(directorio, registro, version):
    """Un `mergiraf` en `directorio` que anota cada llamada (también --version) en `registro` y pasa a mergiraf_falso.py
    (rc 0 por defecto, como si resolviera)."""
    os.makedirs(directorio, exist_ok=True)
    conf = os.path.join(directorio, "conf.json")
    with open(conf, "w", encoding="utf-8") as f:
        json.dump({"log": os.path.join(directorio, "merges.jsonl"), "version": version, "por_defecto": 0}, f)
    py = os.path.join(directorio, "registra.py")
    with open(py, "w", encoding="utf-8") as f:
        f.write("import json, os, sys\n"
                f"sys.path.insert(0, {PRUEBAS!r})\n"
                "import mergiraf_falso\n"
                f"with open({registro!r}, 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(mergiraf_falso.main(sys.argv[1:]))\n")
    if os.name == "nt":
        with open(os.path.join(directorio, "mergiraf.cmd"), "w", encoding="utf-8") as f:
            f.write(f'@"{sys.executable}" "{py}" %*\r\n')
    else:
        lanzador = os.path.join(directorio, "mergiraf")
        with open(lanzador, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\nexec '{sys.executable}' '{py}' \"$@\"\n")
        os.chmod(lanzador, 0o755)
    return {"HK_MERGIRAF_FALSO": conf}


def sin_mergiraf(path):
    """El PATH sin ningún directorio que tenga un mergiraf."""
    dirs = path.split(os.pathsep)
    while shutil.which("mergiraf", path=os.pathsep.join(dirs)):
        quitar = os.path.dirname(shutil.which("mergiraf", path=os.pathsep.join(dirs)))
        dirs = [d for d in dirs if os.path.normcase(os.path.abspath(d or ".")) != os.path.normcase(quitar)]
    return os.pathsep.join(dirs)


def llamadas(registro):
    return [json.loads(l) for l in leer(registro).splitlines() if l.strip()]


def main():
    for flujo in (sys.stdout, sys.stderr):  # en Windows, con la salida redirigida, cp1252 no sabe escribir «≤» (issue #18)
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    real = shutil.which("mergiraf")
    if not real:
        print("Hace falta mergiraf (≥ 0.20.0) en el PATH para esta prueba.", flush=True)
        return 1
    print("mergiraf: " + real + " · " + subprocess.run([real, "--version"], capture_output=True, text=True).stdout.strip(),
          flush=True)
    tmp = tempfile.mkdtemp(prefix="hk-2b-vivo-")
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


def os_md(puerto, extra):
    return (f"# Hackathon OS\nactiva: sí\nrelay: http://127.0.0.1:{puerto}\ndatos_excluidos: data/, datos/\n" + extra)


def relay(tmp, nombre, repo, puerto, os_texto, env):
    """Un relay en `repo` (un clon del remoto) con este os.md, sin GitHub. Devuelve (url, token, log)."""
    if leer(os.path.join(repo, ".hackathon", "os.md")) != os_texto:
        escribe(repo, ".hackathon/os.md", os_texto)
    dir_relay = os.path.join(repo, ".git", "hackathon", "os", "relay")
    log = os.path.join(tmp, f"relay-{nombre}.log")
    lanza([os.path.join(KIT, "hkos", "relay.py"), "--dir", dir_relay, "--equipo",
           os.path.join(repo, ".hackathon", "coordinacion.md"), "--ip", "127.0.0.1", "--puerto", str(puerto),
           "--os", os.path.join(repo, ".hackathon", "os.md"), "--sin-github"], log, env)
    espera(lambda: os.path.exists(os.path.join(dir_relay, "token")), 30)
    time.sleep(1)
    return f"http://127.0.0.1:{puerto}", leer(os.path.join(dir_relay, "token")).strip(), log


def monitor(tmp, repo, persona, gh):
    """escucha.sh en la copia de la persona, dentro de un bash, como lo lanza Claude Code. Devuelve su fichero de salida."""
    escribe(repo, ".git/hackathon/yo-fijo", persona + "\n")       # hk_yo sin gh (M8h)
    salida = os.path.join(tmp, f"escucha-{persona}.out")
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    p = subprocess.Popen([BASH, "-c", f"bash '{ESCUCHA}'; :"], cwd=repo, stdout=open(salida, "wb"),
                         stderr=subprocess.DEVNULL, env=dict(env, HK_GH=gh, HK_ESCUCHA_PASO_S="1"))
    procesos.append(p)
    return salida


def prueba(tmp):
    remoto = os.path.join(tmp, "remoto.git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remoto], check=True)
    semilla = os.path.join(tmp, "semilla")
    subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", remoto, semilla], check=True, capture_output=True)
    for k, v in (("user.email", "semilla@example.com"), ("user.name", "S")):
        git(semilla, "config", k, v)
    puerto_relay = libre()
    escribe(semilla, "app.py", BASE)
    escribe(semilla, ".gitignore", ".claude/worktrees/\n")
    escribe(semilla, ".hackathon/os.md", os_md(puerto_relay, "publicar_wip: sí\nfusion_estructural: sí\n"))
    escribe(semilla, ".hackathon/coordinacion.md", "# Coordinación\nactiva: sí\nrepo: alguien/sandbox\n\n"
                                                   "| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n| B | @persona-b |\n")
    git(semilla, "add", "-A")
    git(semilla, "commit", "-qm", "inicio")
    git(semilla, "push", "-q", "origin", "HEAD:main")

    def clona(nombre):
        c = os.path.join(tmp, nombre)
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", remoto, c], check=True, capture_output=True)
        return c

    clones, puertos = {}, {}
    for persona in ("persona-a", "persona-b"):
        c = clona(persona)
        git(c, "config", "user.email", f"{persona}@example.com")
        git(c, "config", "user.name", persona)
        os.makedirs(os.path.join(c, ".git", "hackathon", "os"), exist_ok=True)
        escribe(c, ".git/hackathon/yo-prueba", persona + "\n")          # la caché de hk_yo que lee emite.sh
        clones[persona] = c
    a, b = clones["persona-a"], clones["persona-b"]
    # El relay de quien coordina, en el clon de A: nivel 2 y 2b, con Mergiraf de verdad. Su temporal, aparte, para ver
    # que no deja nada.
    tmp_relay = os.path.join(tmp, "tmp-relay")
    os.makedirs(tmp_relay)
    dir_copias, copias_antes = copias_mergiraf()
    url, token, log_relay = relay(tmp, "a", a, puerto_relay, leer(os.path.join(a, ".hackathon", "os.md")),
                                  dict(os.environ, TMPDIR=tmp_relay, TEMP=tmp_relay, TMP=tmp_relay))
    escribe(b, ".git/hooks/pre-push", "#!/bin/sh\nexit 1\n")          # la publicación lo salta con --no-verify
    for persona, c in clones.items():
        escribe(c, ".git/hackathon/os/relay.url", url + "\n")
        escribe(c, ".git/hackathon/os/token", token + "\n")
        puertos[persona] = libre()
        lanza([os.path.join(KIT, "hkos", "agente.py"), "--repo", c, "--persona", persona, "--puerto", str(puertos[persona]),
               "--apagado-min", "30"], os.path.join(tmp, f"agente-{persona}.log"))
    sa, sb = Sesion("s-a", a), Sesion("s-b", b)
    sa.inicio()
    sb.inicio()
    comprueba("relay y demonios arrancados; el md de cada persona escrito", espera(lambda: md(a) and md(b), 60),
              f"relay.log: {leer(log_relay)[-500:]}")
    avisos = [l for l in leer(log_relay).splitlines() if "Nivel 2b" in l]
    comprueba("el relay dice una vez «Nivel 2b activo: mergiraf 0.20.0» al arrancar",
              len(avisos) == 1 and "Nivel 2b activo: mergiraf 0.20." in avisos[0], str(avisos))
    gh = os.path.join(tmp, "gh-falso").replace("\\", "/")
    escribe(tmp, "gh-falso", "#!/usr/bin/env bash\nexit 0\n")
    os.chmod(gh, 0o755)
    salidas = {p: monitor(tmp, c, p, gh) for p, c in clones.items()}
    time.sleep(4)

    print("\n== C5, paso 1: un import distinto en el mismo sitio de app.py", flush=True)
    sa.edita("app.py", APP_A)
    sb.edita("app.py", APP_B)
    fotos = {p: foto(c) for p, c in clones.items()}       # después de los hooks: lo que sigue es solo del OS
    refs_antes = refs_relay(a)
    t_pub, vio_rojo = [None], [False]

    def paso1():
        if t_pub[0] is None and en_wip(remoto, "persona-a", APP_A) and en_wip(remoto, "persona-b", APP_B):
            t_pub[0] = time.time()
        vio_rojo[0] |= con_rojo(a) or con_rojo(b)
        return t_pub[0] is not None and con_2b(a) and con_2b(b)

    ok = espera(paso1, 240, 0.25)
    t_2b = time.time() - t_pub[0] if t_pub[0] else None
    comprueba(f"C5: amarillo 2b con app.py en el md de A y de B a los "
              f"{'?' if t_2b is None else f'{t_2b:.0f}'} s de la publicación de los dos trabajos en curso (≤ {PLAZO} s)",
              ok and t_2b is not None and t_2b <= PLAZO, f"A: {colisiones_md(a)} · B: {colisiones_md(b)} · "
                                                         f"relay: {leer(log_relay)[-800:]}")
    print("        " + "\n        ".join(colisiones_md(a)), flush=True)
    wa = git(remoto, "rev-parse", "refs/hackathon/wip/persona-a")
    wb = git(remoto, "rev-parse", "refs/hackathon/wip/persona-b")
    mt = subprocess.run(["git", "-C", remoto, "merge-tree", "--write-tree", "--name-only", "--no-messages", wa, wb],
                        capture_output=True, text=True)
    comprueba("C5: para git es un conflicto (merge-tree de los dos trabajos en curso da 1 con app.py)",
              mt.returncode == 1 and "app.py" in mt.stdout.splitlines()[1:], f"{mt.returncode} {mt.stdout}")
    comprueba("C5: en el relay con 2b, ni rojo de app.py ni nivel 1 de app.py (lo tapa el 2b)", not vio_rojo[0] and
              not any(l.startswith("- AMARILLO · nivel 1 ") and "app.py" in l for l in colisiones_md(a) + colisiones_md(b)),
              str(colisiones_md(a)))
    cols = [c for c in estado(url, token)["colisiones"] if c["nivel"] == "2b"]
    comprueba("C5: /v1/estado del relay: 2b:persona-a+persona-b amarillo con app.py",
              len(cols) == 1 and cols[0]["id"] == "2b:persona-a+persona-b" and cols[0]["gravedad"] == "amarillo"
              and cols[0]["rutas"] == ["app.py"], json.dumps(cols))

    print("\n== C1: el relay vivo, con 2b apagado o sin Mergiraf, no ejecuta mergiraf", flush=True)
    casos = {   # nombre: (líneas de os.md, versión del falso o None si no hay mergiraf en el PATH)
        "ausente": ("publicar_wip: sí\n", "mergiraf 0.20.0"),
        "no": ("publicar_wip: sí\nfusion_estructural: no\n", "mergiraf 0.20.0"),
        "sin-publicar-wip": ("publicar_wip: no\nfusion_estructural: sí\n", "mergiraf 0.20.0"),
        "sin-mergiraf": ("publicar_wip: sí\nfusion_estructural: sí\n", None),
        "0.19.1": ("publicar_wip: sí\nfusion_estructural: sí\n", "mergiraf 0.19.1"),
        "control-0.20.0": ("publicar_wip: sí\nfusion_estructural: sí\n", "mergiraf 0.20.0"),
    }
    vivos = {}
    for nombre, (lineas, version) in casos.items():
        c = clona(f"relay-{nombre}")
        d = os.path.join(tmp, f"falso-{nombre}")
        registro = os.path.join(tmp, f"llamadas-{nombre}.jsonl")
        extra = falso(d, registro, version or "mergiraf 0.20.0")
        path = os.environ.get("PATH", "")
        path = d + os.pathsep + sin_mergiraf(path) if version else sin_mergiraf(path)
        vivos[nombre] = (*relay(tmp, nombre, c, libre(), os_md(libre(), lineas), dict(os.environ, PATH=path, **extra)),
                         registro, d)

    def nivel_de(nombre):
        url_c, token_c = vivos[nombre][:2]
        return {c["nivel"] for c in estado_o_nada(url_c, token_c)["colisiones"] if "app.py" in c["rutas"]}

    espera(lambda: all(nivel_de(n) for n in casos if n != "sin-publicar-wip"), 90, 1)
    time.sleep(2)
    for nombre in casos:
        url_c, token_c, log, registro, d = vivos[nombre]
        hechas = llamadas(registro)
        merges = [x for x in hechas if x[:1] == ["merge"]]
        avisos = [l for l in leer(log).splitlines() if "Nivel 2b" in l]
        niveles = nivel_de(nombre)
        if nombre in ("ausente", "no", "sin-publicar-wip"):
            esperado = set() if nombre == "sin-publicar-wip" else {"2"}
            comprueba(f"C1 ({nombre}): ninguna llamada a mergiraf (ni --version), ningún aviso de 2b y nivel "
                      f"{'ninguno' if not esperado else '2 rojo'} con app.py",
                      hechas == [] and avisos == [] and niveles == esperado, f"{hechas} · {avisos} · {niveles}")
        elif nombre == "sin-mergiraf":
            comprueba("C1 (sí, sin mergiraf en el PATH): ninguna llamada, «Nivel 2b desactivado: mergiraf no está en el "
                      "PATH. Sigue el nivel 2.» una vez y nivel 2 rojo con app.py",
                      hechas == [] and avisos == ["Nivel 2b desactivado: mergiraf no está en el PATH. Sigue el nivel 2."]
                      and niveles == {"2"}, f"{hechas} · {avisos} · {niveles}")
        elif nombre == "0.19.1":
            comprueba("C1 (sí, mergiraf 0.19.1): solo `mergiraf --version`, ningún merge, «Nivel 2b desactivado: "
                      "mergiraf 0.19.1 < 0.20.0. Sigue el nivel 2.» una vez y nivel 2 rojo con app.py",
                      hechas == [["--version"]] and avisos == ["Nivel 2b desactivado: mergiraf 0.19.1 < 0.20.0. Sigue el "
                                                               "nivel 2."] and niveles == {"2"},
                      f"{hechas} · {avisos} · {niveles}")
        else:
            comprueba("C1 (control, el falso en 0.20.0): --version y un merge de app.py anotados, y 2b",
                      hechas[:1] == [["--version"]] and len(merges) == 1 and "app.py" in merges[0]
                      and niveles == {"2b"}, f"{hechas} · {avisos} · {niveles}")
        if nombre in ("ausente", "no"):
            print(f"        relay {nombre}: " + next((f"{c['id']} {c['gravedad']}" for c in
                                                      estado_o_nada(url_c, token_c)["colisiones"]), "-"), flush=True)

    comprueba("C5: el monitor de A y el de B, en silencio en el paso 1",
              all(leer(s).strip() == "" for s in salidas.values()), str({p: leer(s) for p, s in salidas.items()}))
    for p, c in clones.items():
        comprueba(f"C5: ficheros, índice, status, stash y HEAD de {p} sin cambios en el paso 1", foto(c) == fotos[p])
    comprueba("C5: las refs del clon del relay sin cambios (salvo refs/hackathon/relay-wip/)", refs_relay(a) == refs_antes,
              f"{refs_antes} / {refs_relay(a)}")

    print("\n== C5, paso 2: B cambia la misma línea que A", flush=True)
    sb.edita("app.py", APP_B2)
    t_edicion = time.time()
    fotos = {p: foto(c) for p, c in clones.items()}
    t_pub = [None]
    linea = {}

    def paso2():
        if t_pub[0] is None and en_wip(remoto, "persona-b", APP_B2):
            t_pub[0] = time.time()
        for p, s in salidas.items():
            if p not in linea and "colisión ROJA nueva" in leer(s):
                linea[p] = time.time()
        return t_pub[0] is not None and con_rojo(a) and con_rojo(b) and len(linea) == 2

    ok = espera(paso2, 240, 0.25)
    t_rojo = time.time() - t_pub[0] if t_pub[0] else None
    comprueba(f"C5: rojo de nivel 2 con app.py y la línea del monitor de A y de B a los "
              f"{'?' if t_rojo is None else f'{t_rojo:.0f}'} s de la publicación de B (≤ {PLAZO} s; "
              f"{time.time() - t_edicion:.0f} s desde la edición)",
              ok and t_rojo is not None and t_rojo <= PLAZO, f"A: {colisiones_md(a)} · B: {colisiones_md(b)} · "
                                                             f"monitor: {[leer(s) for s in salidas.values()]}")
    print("        " + "\n        ".join(colisiones_md(b)), flush=True)
    time.sleep(3)
    for p, s in salidas.items():
        lineas = leer(s).splitlines()
        comprueba(f"C5: el monitor de {p}: una sola línea, la roja nueva de app.py",
                  len(lineas) == 1 and lineas[0].startswith("hk-os · colisión ROJA nueva · nivel 2 · app.py · "),
                  str(lineas))
    print("        " + leer(salidas["persona-a"]).strip(), flush=True)
    comprueba("C5: el 2b se va (la ruta vuelve a rojo)", not con_2b(a) and not con_2b(b), str(colisiones_md(a)))
    for p, c in clones.items():
        comprueba(f"C5: ficheros, índice, status, stash y HEAD de {p} sin cambios en el paso 2", foto(c) == fotos[p])
    comprueba("C5: las refs del clon del relay sin cambios (salvo refs/hackathon/relay-wip/)", refs_relay(a) == refs_antes,
              f"{refs_antes} / {refs_relay(a)}")
    restos = [n for n in os.listdir(tmp_relay) if n.startswith("hk-2b-")]   # uv deja allí su propio .lock
    comprueba("C5: nada del 2b en el temporal del relay (ningún hk-2b-*)", restos == [], str(os.listdir(tmp_relay)))
    comprueba(f"C5: ninguna copia nueva de Mergiraf en {dir_copias}", copias_mergiraf()[1] == copias_antes,
              str(copias_mergiraf()[1]))
    print(f"\n{fallos} fallos", flush=True)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
