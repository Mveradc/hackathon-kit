# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterio 5 de M9a (ADR-0011) con las piezas de verdad y sin modelo: un remoto `bare` local, dos clones (una persona
por clon), un demonio por clon (hkos/agente.py), el relay (hkos/relay.py) en el clon de B con `web_nueva: sí` y
`github: no`, y los hooks reales (emite.sh, arbol.sh y prueba.sh, con entradas con la forma de las de Claude Code). Sin
red ni GitHub. Cada caso se mide desde lo que lo provoca (el push, el hook o el arranque) hasta que sale en el
`estado.json` del relay, y tiene que caber en 30 s:

  1. puerto declarado sin respuesta (y, de control, un servicio que responde: sin desajuste);
  2. fichero fuera de todo servicio (el `arbol` de una sesión);
  3. Prueba corrida y fallando, con comando, procedencia (hook) y antigüedad;
  4. fila cambiada por otra persona: «declarado por @x, sin confirmar»;
  5. una Propuesta, confirmada al pasarla su dueño a su sección;
  6. comando de Prueba cambiado (por un dueño de la conexión): sin confirmar;
  7. sha reescrito (squash con `rebase -i`): sin confirmar y nunca confirmado;
  8. fila añadida por un worker de su dueño (rama `worktree-agent-*`, `merge --no-ff`): confirmada, y su salud se consulta;
  9. Salud que no es una ruta (`http://…`, `/../`): desajuste y sin consulta.

Además, `--apagada`: el criterio 1 en vivo (`web_nueva: no`): el demonio da 404 en `/`, el SSE del relay no trae
`eventos` y prueba.sh no escribe.

Uso: uv run --no-project evals/coordinacion/servicios_vivo.py [--apagada]      (0 OK · 1 falla; unos 10 minutos)
"""
import http.client
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTRADAS = os.path.join(KIT, "evals", "coordinacion", "entradas", "m9a-bash")
BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe"))
                 if os.path.exists(b)), BASH)
PLAZO_S = 30
PRUEBA = "uv run pytest tests/test_web_api.py"
fallos = 0
procesos = []
medidas = []


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(("OK    " if ok else "FALLO ") + nombre + ("" if ok or not detalle else f"\n        {detalle}"), flush=True)


def git(repo, *args, env=None):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.decode()}")
    return r.stdout.decode().strip()


def escribe(repo, ruta, texto):
    p = os.path.join(repo, ruta)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="\n", encoding="utf-8") as f:
        f.write(texto)


def lee(repo, ruta):
    with open(os.path.join(repo, ruta), encoding="utf-8") as f:
        return f.read()


def libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lanza(args, log):
    p = subprocess.Popen(["uv", "run", "--no-project", "--quiet", *args], stdout=open(log, "w"), stderr=subprocess.STDOUT)
    procesos.append(p)
    return p


def hook(script, entrada, cwd):
    subprocess.run([BASH, os.path.join(KIT, "scripts", "os", script)], input=json.dumps(entrada).encode(), cwd=cwd,
                   capture_output=True, timeout=30)


def espera(cond, segundos, paso=0.5):
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            if cond():
                return True
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(paso)
    try:
        return bool(cond())
    except (OSError, ValueError, KeyError):
        return False


class Registro(http.server.ThreadingHTTPServer):
    """Un servicio de mentira en 127.0.0.1 que responde 200 a todo y apunta cada GET (para ver qué consulta el demonio)."""
    daemon_threads = True

    def __init__(self, puerto):
        self.pedidos = []

        class Manejador(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(h):
                self.pedidos.append((time.time(), h.path))
                h.send_response(200)
                h.send_header("Content-Length", "2")
                h.end_headers()
                h.wfile.write(b"ok")
        super().__init__(("127.0.0.1", puerto), Manejador)
        threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()


class Sesion:
    def __init__(self, sid, cwd):
        self.sid, self.cwd, self.n = sid, cwd, 0

    def base(self, evento):
        return {"session_id": self.sid, "cwd": self.cwd, "hook_event_name": evento}

    def inicio(self):
        hook("emite.sh", dict(self.base("SessionStart"), source="startup"), self.cwd)

    def edita(self, ruta, texto):
        escribe(self.cwd, ruta, texto)
        self.n += 1
        hook("emite.sh", dict(self.base("PostToolUse"), tool_name="Write", tool_use_id=f"toolu_{self.sid}_{self.n}",
                              tool_input={"file_path": os.path.join(self.cwd, ruta), "content": texto}), self.cwd)
        hook("arbol.sh", self.base("PostToolBatch"), self.cwd)

    def bash(self, comando, falla):
        nombre = "02-principal-PostToolUseFailure-Bash.json" if falla else "01-principal-PostToolUse-Bash.json"
        with open(os.path.join(ENTRADAS, nombre), encoding="utf-8") as f:
            e = json.load(f)
        self.n += 1
        e = dict(e, session_id=self.sid, cwd=self.cwd, tool_use_id=f"toolu_{self.sid}_{self.n}",
                 tool_input=dict(e["tool_input"], command=comando))
        hook("prueba.sh", e, self.cwd)


def servicios_md(pw, pa):
    return f"""# Servicios

Qué se pone en marcha, dónde vive, de quién es y cómo se habla entre sí.

Fuera de servicios: docs/, README.md

## Servicios
| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |
|---|---|---|---|---|---|
| web | web/ | {pw} | `npm run dev` | /salud | — |
| api | api/ | {pa} | `uv run uvicorn api.main:app` | /salud | — |
| motor | motor/ | — | — | — | — |

## Conexiones
| De | A | Contrato | Prueba |
|---|---|---|---|
| web | api | web → api | `{PRUEBA}` |

## Propuestas de servicios
| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño | Autor | Hora |
|---|---|---|---|---|---|---|---|

## Propuestas de conexiones
| De | A | Contrato | Prueba | Autor | Hora |
|---|---|---|---|---|---|
"""


AUTORIDAD = """# Autoridad

## Servicios (`.hackathon/servicios.md`)
Un servicio lo confirma su dueño; una conexión, los dueños de sus dos extremos.

## Por dueño
### A (@persona-a) · `web/`
| Tema | Nivel | Ejemplos |
|---|---|---|
| `docs/contratos.md`: web → api | Agentes + confirmación | campos |

### B (@persona-b) · `api/`, `motor/`, `datos/`
| Tema | Nivel | Ejemplos |
|---|---|---|
| `docs/contratos.md`: api → motor | Agentes + confirmación | campos |
"""

CONTRATOS = """# Contratos

## web → api
GET /items → lista de items.

## api → motor
motor.calcula(x) → float.
"""


class Equipo:
    def __init__(self, tmp, web_nueva=True):
        self.tmp = tmp
        self.remoto = os.path.join(tmp, "remoto.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remoto], check=True)
        semilla = os.path.join(tmp, "semilla")
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", self.remoto, semilla], check=True,
                       capture_output=True)
        for k, v in (("user.email", "scaffold@example.com"), ("user.name", "scaffold")):
            git(semilla, "config", k, v)
        self.puerto_relay = libre()
        self.pw, self.pa, self.pm = libre(), libre(), libre()
        escribe(semilla, ".hackathon/os.md", "# Hackathon OS\nactiva: sí\ngithub: no\n"
                f"web_nueva: {'sí' if web_nueva else 'no'}\nrelay: http://127.0.0.1:{self.puerto_relay}\n")
        escribe(semilla, ".hackathon/coordinacion.md", "# Coordinación\nactiva: sí\n\n"
                "| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n| B | @persona-b |\n")
        escribe(semilla, ".hackathon/autoridad.md", AUTORIDAD)
        escribe(semilla, ".hackathon/servicios.md", servicios_md(self.pw, self.pa))
        escribe(semilla, "docs/contratos.md", CONTRATOS)
        escribe(semilla, "README.md", "# Proyecto\n")
        escribe(semilla, "web/index.js", "// web\n")
        escribe(semilla, "api/main.py", "# api\n")
        escribe(semilla, "motor/m.py", "# motor\n")
        escribe(semilla, ".gitignore", ".claude/worktrees/\n")
        git(semilla, "add", "-A")
        git(semilla, "commit", "-qm", "scaffold: servicios.md")
        git(semilla, "push", "-q", "origin", "HEAD:main")
        self.clones = {}
        for persona in ("persona-a", "persona-b"):
            c = os.path.join(tmp, persona)
            subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", self.remoto, c], check=True,
                           capture_output=True)
            git(c, "config", "user.email", f"{persona}@example.com")
            git(c, "config", "user.name", persona)
            escribe(c, ".git/hackathon/yo-fijo", persona + "\n")
            self.clones[persona] = c
        self.a, self.b = self.clones["persona-a"], self.clones["persona-b"]
        # El relay, en el clon de B (quien coordina), sin GitHub.
        self.dir_relay = os.path.join(self.b, ".git", "hackathon", "os", "relay")
        lanza([os.path.join(KIT, "hkos", "relay.py"), "--dir", self.dir_relay, "--equipo",
               os.path.join(self.b, ".hackathon", "coordinacion.md"), "--ip", "127.0.0.1", "--puerto",
               str(self.puerto_relay), "--os", os.path.join(self.b, ".hackathon", "os.md"), "--sin-github"],
              os.path.join(tmp, "relay.log"))
        self.url = f"http://127.0.0.1:{self.puerto_relay}"
        if not espera(lambda: os.path.exists(os.path.join(self.dir_relay, "token")), 30):
            raise SystemExit("el relay no arranca: " + open(os.path.join(tmp, "relay.log")).read()[-800:])
        time.sleep(1)
        with open(os.path.join(self.dir_relay, "token")) as f:
            self.token = f.read().strip()

    def demonios(self):
        self.puertos, self.t_demonios = {}, time.time()
        for persona, c in self.clones.items():
            escribe(c, ".git/hackathon/os/relay.url", self.url + "\n")
            escribe(c, ".git/hackathon/os/token", self.token + "\n")
            self.puertos[persona] = libre()
            lanza([os.path.join(KIT, "hkos", "agente.py"), "--repo", c, "--persona", persona, "--puerto",
                   str(self.puertos[persona]), "--apagado-min", "60"], os.path.join(self.tmp, f"agente-{persona}.log"))

    def estado(self):
        req = urllib.request.Request(self.url + "/v1/estado", headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())

    def servicios(self):
        return self.estado().get("servicios") or {}

    def cambia(self, persona, ruta, de, a, mensaje):
        """Pull, cambio de texto, commit y push desde el clon de la persona. Devuelve la hora del push."""
        c = self.clones[persona]
        git(c, "pull", "-q", "--ff-only", "origin", "main")
        texto = lee(c, ruta)
        if de not in texto:
            raise SystemExit(f"{ruta} de {persona} no tiene «{de}»")
        escribe(c, ruta, texto.replace(de, a, 1))
        git(c, "commit", "-qam", mensaje)
        git(c, "push", "-q", "origin", "HEAD:main")
        return time.time()


def fila(s, nombre):
    return next((x for x in s.get("lista", []) if x["nombre"] == nombre), None)


def desajustes(s, tipo, clave=None):
    return [d for d in s.get("desajustes", []) if d["tipo"] == tipo and (clave is None or d.get("clave") == clave)]


def caso(nombre, desde, cond, segundos=150, detalle=lambda: ""):
    """Espera a que se cumpla `cond` y comprueba que llegó en ≤ PLAZO_S desde `desde`."""
    ok = espera(cond, max(1, desde + segundos - time.time()), 0.5)
    t = time.time() - desde
    medidas.append((nombre, ok, t))
    comprueba(f"{nombre}: {'a los %.1f s' % t if ok else 'no llega en %d s' % segundos} (≤ {PLAZO_S} s)",
              ok and t <= PLAZO_S, detalle() if not ok or t > PLAZO_S else "")
    return ok


def prueba(tmp):
    eq = Equipo(tmp)
    a, b = eq.a, eq.b
    web = Registro(eq.pw)                      # el servicio de A responde; el de B (api) no tiene a nadie escuchando
    eq.demonios()
    sa = Sesion("s-a", a)
    sa.inicio()
    Sesion("s-b", b).inicio()
    vistazo = lambda: json.dumps(eq.servicios(), ensure_ascii=False)[:1500]
    comprueba("relay y demonios arrancados; servicios en el estado, las tres filas confirmadas y de /hack-scaffold",
              espera(lambda: all((fila(eq.servicios(), n) or {}).get("confirmacion", {}).get("de_scaffold")
                                 and fila(eq.servicios(), n)["confirmacion"]["valor"] == "confirmada"
                                 for n in ("web", "api", "motor")), 150), vistazo())

    print("\n== 1. Puerto declarado sin respuesta", flush=True)
    api = fila(eq.servicios(), "api")
    caso("api (de B) :%d sin nadie escuchando → puerto_sin_respuesta, fuente demonio" % eq.pa, eq.t_demonios,
         lambda: any(d["fuente"] == "demonio" for d in desajustes(eq.servicios(), "puerto_sin_respuesta", api["clave"])),
         detalle=vistazo)
    w = fila(eq.servicios(), "web")
    comprueba("control: web (de A) responde 200 en /salud, sin desajuste y consultada solo por su dueño",
              espera(lambda: (fila(eq.servicios(), "web")["comprobado"] or {}).get("valor") == {"escucha": True, "salud": 200}, 30)
              and not [d for d in eq.servicios()["desajustes"] if d.get("clave") == w["clave"]]
              and web.pedidos and all(p == "/salud" for _, p in web.pedidos), vistazo())

    print("\n== 2. Fichero fuera de todo servicio", flush=True)
    t = time.time()
    sa.edita("suelto/nota.py", "x = 1\n")
    # Una carpeta sin seguimiento sale entera en `git status --porcelain` («?? suelto/»), y así llega en el arbol.
    caso("suelto/nota.py (sin subir, por el arbol de la sesión de A) → codigo_fuera con la ruta", t,
         lambda: any(r in ("suelto/", "suelto/nota.py") for d in desajustes(eq.servicios(), "codigo_fuera")
                     for r in d.get("rutas", [])), detalle=vistazo)
    comprueba("docs/, README.md y .hackathon/ no salen como código fuera",
              not any(r.startswith(("docs/", ".hackathon/")) or r == "README.md"
                      for d in desajustes(eq.servicios(), "codigo_fuera") for r in d.get("rutas", [])), vistazo())

    print("\n== 3. Prueba corrida y fallando", flush=True)
    t = time.time()
    sa.bash(PRUEBA, falla=True)
    con = lambda: next(c for c in eq.servicios()["conexiones"] if c["de"] == "web" and c["a"] == "api")
    caso("la Prueba de web → api falla en la sesión de A → prueba_falla", t,
         lambda: desajustes(eq.servicios(), "prueba_falla", con()["clave"]), detalle=vistazo)
    r = con()
    comprueba("con el comando, la procedencia (hook) y la antigüedad (observado_en)",
              r["prueba"] == PRUEBA and (r["resultado"] or {}).get("valor") == "falla"
              and r["resultado"].get("fuente") == "hook" and r["resultado"].get("observado_en"), json.dumps(r, ensure_ascii=False))

    print("\n== 4. Fila cambiada por otra persona", flush=True)
    pa2 = libre()
    t = eq.cambia("persona-a", ".hackathon/servicios.md", f"| api | api/ | {eq.pa} |", f"| api | api/ | {pa2} |",
                  "api en otro puerto")
    caso("A cambia el puerto de api (de B) → «declarado por @persona-a, sin confirmar»", t,
         lambda: (lambda f: f and f["puerto"] == pa2 and f["confirmacion"]["valor"] == "sin_confirmar"
                  and f["confirmacion"]["por"] == ["persona-a"] and f["confirmacion"]["faltan"] == ["persona-b"])(
             fila(eq.servicios(), "api")), detalle=vistazo)

    print("\n== 5. Propuesta confirmada por su dueño", flush=True)
    t = eq.cambia("persona-a", ".hackathon/servicios.md", "|---|---|---|---|---|---|---|---|\n",
                  "|---|---|---|---|---|---|---|---|\n| datos | datos/ | — | `uv run etl` | — | @persona-b | @persona-a | "
                  "2026-10-18 19:00 |\n", "propuesta: datos")
    caso("A propone «datos» (de B) en Propuestas → propuesta con autor_git persona-a, sin estar en la lista", t,
         lambda: any(p["campos"].get("nombre") == "datos" and p["autor_git"] == "persona-a" and p["duenos"] == ["persona-b"]
                     for p in eq.servicios()["propuestas"]) and not fila(eq.servicios(), "datos"), detalle=vistazo)
    git(b, "pull", "-q", "--ff-only", "origin", "main")
    texto = lee(b, ".hackathon/servicios.md")
    propuesta = next(l for l in texto.splitlines() if l.startswith("| datos |"))
    texto = texto.replace(propuesta + "\n", "").replace("| motor | motor/ |", "| datos | datos/ | — | `uv run etl` | — | "
                                                       "@persona-b |\n| motor | motor/ |", 1)
    escribe(b, ".hackathon/servicios.md", texto)
    git(b, "commit", "-qam", "datos: de Propuestas a Servicios")
    git(b, "push", "-q", "origin", "HEAD:main")
    t = time.time()
    caso("B pasa la propuesta a Servicios → «datos» confirmada (por persona-a y persona-b)", t,
         lambda: (lambda f: f and f["confirmacion"]["valor"] == "confirmada" and "persona-b" in f["confirmacion"]["por"])(
             fila(eq.servicios(), "datos")) and not eq.servicios()["propuestas"], detalle=vistazo)

    print("\n== 6. Comando de Prueba cambiado", flush=True)
    t = eq.cambia("persona-b", ".hackathon/servicios.md", f"`{PRUEBA}`", f"`{PRUEBA} -x`", "prueba de web → api con -x")
    caso("B (un dueño de web → api) cambia la Prueba → sin confirmar, falta persona-a", t,
         lambda: (lambda c: c["prueba"] == PRUEBA + " -x" and c["confirmacion"]["valor"] == "sin_confirmar"
                  and c["confirmacion"]["faltan"] == ["persona-a"])(con()), detalle=vistazo)

    print("\n== 7. Sha reescrito", flush=True)
    git(a, "pull", "-q", "--ff-only", "origin", "main")
    escribe(a, ".hackathon/servicios.md", lee(a, ".hackathon/servicios.md").replace("`npm run dev`", "`npm run start`"))
    git(a, "commit", "-qam", "web: start")
    escribe(a, ".hackathon/servicios.md", lee(a, ".hackathon/servicios.md").replace(
        f"| web | web/ | {eq.pw} | `npm run start` | /salud |", f"| web | web/ | {eq.pw} | `npm run start` | /estado |"))
    git(a, "commit", "-qam", "web: /estado")
    time.sleep(20)                              # el demonio de A emite los dos commits (cada 15 s)
    env = dict(os.environ, GIT_SEQUENCE_EDITOR="sed -i -e '2s/^pick/squash/'", GIT_EDITOR="true")
    git(a, "rebase", "-q", "-i", "HEAD~2", env=env)
    git(a, "push", "-q", "origin", "HEAD:main")
    t = time.time()
    caso("A junta sus dos commits (squash) y sube el sha nuevo → web sin confirmar", t,
         lambda: (lambda f: f["salud"] == "/estado" and f["confirmacion"]["valor"] == "sin_confirmar")(
             fila(eq.servicios(), "web")), detalle=vistazo)
    nunca = espera(lambda: fila(eq.servicios(), "web")["confirmacion"]["valor"] == "confirmada", 75, 1)
    comprueba("… y nunca confirmada (75 s más: varias vueltas del sondeo de git y un fetch del relay)", not nunca, vistazo())

    print("\n== 8. Fila añadida por un worker de su dueño", flush=True)
    git(b, "pull", "-q", "--ff-only", "origin", "main")
    wt = os.path.join(b, ".claude", "worktrees", "agent-w1")
    git(b, "worktree", "add", "-q", "-b", "worktree-agent-w1", wt)
    git(wt, "config", "user.name", "persona-b")
    escribe(wt, ".hackathon/servicios.md", lee(wt, ".hackathon/servicios.md").replace(
        "| motor | motor/ | — | — | — | — |", f"| motor | motor/ | {eq.pm} | `uv run motor` | /salud | — |"))
    git(wt, "commit", "-qam", "motor: puerto y salud (worker)")
    git(b, "merge", "-q", "--no-ff", "--no-edit", "worktree-agent-w1")
    git(b, "push", "-q", "origin", "HEAD:main")
    t = time.time()
    motor = Registro(eq.pm)
    caso("un worker de B añade puerto y salud a motor; merge --no-ff y push → confirmada por persona-b", t,
         lambda: (lambda f: f["puerto"] == eq.pm and f["confirmacion"]["valor"] == "confirmada"
                  and f["confirmacion"]["por"] == ["persona-b"] and not f["confirmacion"]["de_scaffold"])(
             fila(eq.servicios(), "motor")), detalle=vistazo)
    comprueba("… y el demonio de B consulta su salud (GET /salud en :%d)" % eq.pm,
              espera(lambda: any(p == "/salud" for _, p in motor.pedidos), 30), str(motor.pedidos[:5]))

    print("\n== 9. Salud que no es una ruta", flush=True)
    for mala in (f"http://127.0.0.1:{eq.pm}/salud", "/../salud"):
        anterior = fila(eq.servicios(), "motor")["salud"] or "/salud"
        t = eq.cambia("persona-b", ".hackathon/servicios.md", f"`uv run motor` | {anterior} |", f"`uv run motor` | {mala} |",
                      f"motor: salud {mala}")
        caso(f"Salud «{mala}» → formato_invalido, sin confirmar y sin Salud en la lista", t,
             lambda: (lambda f: f["salud"] is None and f["confirmacion"]["valor"] == "sin_confirmar"
                      and desajustes(eq.servicios(), "formato_invalido", f["clave"]))(fila(eq.servicios(), "motor")),
             detalle=vistazo)
        time.sleep(3)
        n = len(motor.pedidos)
        time.sleep(35)                          # más de dos vueltas de SaludServicios (cada 15 s)
        comprueba(f"… y el demonio deja de consultar :{eq.pm} (0 peticiones en 35 s)", len(motor.pedidos) == n,
                  str(motor.pedidos[n:]))
        if mala.startswith("http"):            # vuelta a una Salud buena para probar la siguiente desde «consultada»
            t = eq.cambia("persona-b", ".hackathon/servicios.md", f"`uv run motor` | {mala} |", "`uv run motor` | /salud |",
                          "motor: /salud")
            espera(lambda: fila(eq.servicios(), "motor")["salud"] == "/salud", 150)

    print("\n== Resumen de tiempos", flush=True)
    for nombre, ok, t in medidas:
        print(f"  {'≤30' if ok and t <= PLAZO_S else 'MAL'}  {t:6.1f} s  {nombre}")
    peores = [t for _, ok, t in medidas if ok]
    if peores:
        print(f"  máximo {max(peores):.1f} s; el relay hace `git fetch` y lee servicios.md cada "
              f"{60} s (NOVEDADES_S), el demonio mira git cada 15 s y la salud cada 15 s")


def apagada(tmp):
    """Criterio 1 en vivo: con `web_nueva: no`, el demonio da 404 en `/`, el SSE del relay no trae `eventos` y
    prueba.sh no escribe (aunque haya servicios.md y la Prueba exacta)."""
    eq = Equipo(tmp, web_nueva=False)
    eq.demonios()
    puerto = eq.puertos["persona-a"]
    comprueba("el demonio de A arranca", espera(lambda: socket.create_connection(("127.0.0.1", puerto), 0.5).close() or True, 30))
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
    c.request("GET", "/")
    r = c.getresponse()
    r.read()
    comprueba(f"GET / del demonio: {r.status} (se espera 404)", r.status == 404)
    trozos, parar = [], threading.Event()

    def leer_sse():
        cx = http.client.HTTPConnection("127.0.0.1", eq.puerto_relay, timeout=40)
        cx.request("GET", "/v1/stream", headers={"Authorization": f"Bearer {eq.token}"})
        resp = cx.getresponse()
        try:
            while not parar.is_set():
                linea = resp.fp.readline()
                if not linea:
                    break
                trozos.append(linea.decode("utf-8", "replace"))
        except OSError:                         # el relay se cierra al terminar
            pass
    threading.Thread(target=leer_sse, daemon=True).start()
    time.sleep(2)
    sa = Sesion("s-a", eq.a)
    sa.inicio()
    sa.edita("web/otro.js", "// otro\n")
    eventos_dir = os.path.join(eq.a, ".git", "hackathon", "os", "eventos")
    antes = {f: os.path.getsize(os.path.join(eventos_dir, f)) for f in os.listdir(eventos_dir)} if os.path.isdir(eventos_dir) else {}
    sa.bash(PRUEBA, falla=True)
    despues = {f: os.path.getsize(os.path.join(eventos_dir, f)) for f in os.listdir(eventos_dir)} if os.path.isdir(eventos_dir) else {}
    comprueba("prueba.sh con la Prueba exacta y servicios.md: no escribe nada", antes == despues, f"{antes} → {despues}")
    llego = espera(lambda: sum(l.startswith("event: estado") for l in trozos) >= 2, 30)   # el inicial y el de A
    time.sleep(5)
    parar.set()
    tipos = sorted({l.strip() for l in trozos if l.startswith("event:")})
    comprueba(f"SSE del relay con eventos de A llegando: {', '.join(tipos)}; ninguno `eventos`",
              llego and "event: eventos" not in tipos, "".join(trozos)[:600])
    comprueba("el estado del relay no lleva `servicios`", "servicios" not in eq.estado())


def main():
    for flujo in (sys.stdout, sys.stderr):  # en Windows, con la salida redirigida, cp1252 no sabe escribir «≤»
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="hk-servicios-")
    try:
        (apagada if "--apagada" in sys.argv else prueba)(tmp)
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
        if fallos:
            print(f"(carpeta conservada: {tmp})")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'Todo bien' if not fallos else f'{fallos} fallos'}.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
