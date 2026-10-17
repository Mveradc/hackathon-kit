# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Demonio local del Hackathon OS (M8d, api.md §4): uno por persona y clon. Sigue los JSONL que escriben los hooks,
los normaliza con normaliza.py, los envía al relay y le manda latidos. Solo biblioteca estándar (ADR-0005).

Lo lanza sesion.sh (scripts/os/arranque.sh) desacoplado de la sesión. El bloqueo es el puerto: si el bind falla, ya
hay otro y sale. Se apaga solo tras `apagado_min` sin eventos nuevos y sin sesiones activas.
  uv run --no-project hkos/agente.py --repo <copia principal> --persona <usuario> --puerto <n> [--apagado-min N]
"""
import argparse
import glob
import hashlib
import hmac
import http.client
import json
import os
import re
import secrets
import select
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from acciones import Acciones  # noqa: E402
from colisiones_merge import Publicador  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha  # noqa: E402
import proyeccion  # noqa: E402
import servicios  # noqa: E402
from normaliza import Contexto, Normalizador, relativa  # noqa: E402
import permisos  # noqa: E402
from red import Servidor, ahora_iso, conf, web_nueva  # noqa: E402

CICLO_S = 1
ESTADO_S = 3                     # M8f: GET /v1/estado con ETag (P15)
MD_S = 30                        # M8f: estado-equipo.md se reescribe al menos cada 30 s (horas y «viejo»)
LATIDO_S = 15
TTL_S = 90                       # R-18: una sesión sin señales deja de estar activa
LOTE_MAX = 200
ESPERA_MAX_S = 30
LOG_MAX = 1024 * 1024
# M9a (api.md §4, ADR-0010): la web de trabajo, solo con `web_nueva: sí`.
WEB_NUEVA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "nueva")
TIPOS_WEB = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".woff2": "font/woff2",
             ".svg": "image/svg+xml", ".png": "image/png"}
# Sin 'unsafe-inline' (issue #6): React pone los style={{…}} por CSSOM, que la CSP no bloquea.
CSP_WEB = ("default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; "
           "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
ACCIONES = ("/v1/anotar", "/v1/reclamar")
ACCION_MAX = 4096
PING_S = 20                      # el mismo que el relay: la web pasa a «sin conexión» tras max(umbral_viejo_s, 40 s)
WEB_COLA = 200
SOCKET_S = 10                    # issue #6: una petición a medias (cabeceras o cuerpo) no retiene un hilo para siempre
STREAM_MAX = 8                   # clientes de /v1/stream a la vez (pestañas de la persona); el siguiente, 429
CIERRE_S = 1                     # issue #15: cada cuánto mira /v1/stream si la pestaña ha cerrado, entre ping y ping


def git_comun(repo):
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise SystemExit(f"hk-os agente: {repo} no es un repo de git")
    return r.stdout.strip().replace("\\", "/")


class Fichero:
    """Un JSONL de eventos crudos: lo leído (bytes, nº de línea) y lo pendiente de confirmar por el relay."""

    def __init__(self, ruta, normalizador):
        self.ruta, self.nz = ruta, normalizador
        self.leido_bytes, self.leido_linea = 0, 0
        self.lineas = deque()       # [bytes al final de la línea, nº de línea, ids sin confirmar]


# La tarea de un commit es el ID con que empieza su asunto («T07 · …», ADR-0002), no cualquier mención: un commit
# del plan que dice «Ajuste del plan: T14 …» no es trabajo de T14 (en vivo, M8e).
ID_EN_MENSAJE = re.compile(r"^\s*\[?(T\d{2,3})\b")
# Issue #2 (hallazgos 2 y 5, ADR-0011): un commit es de este clon solo si se creó aquí con `git commit` (o `git revert`,
# issue #15) y el reflog lo dice. Ni el correo de git, ni traerlo con fetch, checkout, merge, pull, cherry-pick o rebase.
CREADO_AQUI = re.compile(r"^(?:commit(?: \((?:initial|amend)\))?|revert): ")


class SondeoGit:
    """Sondeo de git del demonio (api.md §4, M8e): commits nuevos de las ramas locales y cambios de origin/main, como
    eventos de fuente git. Lo que pide M8e: `commit` (con la tarea si el mensaje cita un ID, o la del encargo en una
    rama de worker) y `push` (con `incluye`), para que una tarea llegue a `publicada` y una rama sin ID salga en
    `sin_tarea`. Un commit o la punta nueva solo quedan vistos cuando el relay los confirma: si el demonio se reinicia
    antes, se vuelven a emitir con el mismo ID y el relay los descarta. Cuando cambia origin/main, además, el `arbol`
    de la copia principal: tras un push desde la terminal, el amarillo seguía hasta el siguiente `arbol` de una sesión
    (Pendiente de M8g). El `arbol` de git por worktree y la reconciliación de `fusion.*` por refs quedan para más
    adelante."""
    CADA_S, FETCH_S, MAX_VISTOS, MAX_RUTAS = 15, 60, 5000, 200

    def __init__(self, ag):
        self.ag = ag
        self.ruta = os.path.join(ag.dir, "git.json")
        try:
            with open(self.ruta, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        self.punta = d.get("punta")
        self.vistos = list(d.get("vistos", []))
        self._vistos = set(self.vistos)
        self.pendientes = {}                     # id del evento → ("commit", sha) | ("push", punta)
        self.firma_arbol = None                  # el último `arbol` emitido por el demonio (no se repite igual)
        self.ultimo = self.ultimo_fetch = -1e18

    def _git(self, *args, crudo=False):
        try:
            # Sin diálogos de credenciales (M8h): con el remoto del equipo y un token malo, git esperaría al askpass.
            r = subprocess.run(["git", "-C", self.ag.principal, *args], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=30,
                               env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_ASKPASS="",
                                        SSH_ASKPASS=""))
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode != 0:
            return None
        return r.stdout if crudo else r.stdout.strip()   # crudo: `status --porcelain` empieza por un espacio

    def _log(self, rango, *mas):
        """[(sha, hora en UTC, asunto)] del más viejo al más nuevo; None si git no puede (punta desconocida)."""
        t = self._git("log", "--reverse", "--format=%H%x1f%cI%x1f%s", *mas, rango)
        if t is None:
            return None
        salida = []
        for l in t.splitlines():
            if l.count("\x1f") == 2:
                sha, ts, asunto = l.split("\x1f", 2)
                ts = datetime.fromisoformat(ts).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                salida.append((sha, ts, asunto))
        return salida

    def _creados(self):
        """Los shas creados con `git commit` (`--amend` incluido) o `git revert` en la copia principal o en un worktree
        de worker: lo único que el demonio emite como commit de su persona. Salen de dos reflogs:
        - el de HEAD de la copia principal, que sobrevive al borrado de la rama (issue #15: rama → commit → merge →
          `branch -d` antes de la siguiente vuelta o con el demonio apagado) y recoge los commits con HEAD suelto que
          después se rescatan con `switch -c`;
        - el de las ramas `worktree-agent-<id>` (está en el git común), para los workers.
        No el de las demás ramas: no dice desde qué worktree se hizo el commit, y uno que no es el principal ni de
        worker puede ser de otra persona (issue #15). Nunca el autor ni el committer de git, que cualquiera pone
        (ADR-0011). Lo que llegó de fuera (fetch, checkout de una rama ajena, merge, pull, cherry-pick, rebase, reset)
        no tiene esa entrada y no se emite: ante la duda, el commit se queda sin confirmar, que es el lado seguro. Sin
        reflog (o si git no puede), nada."""
        workers = (self._git("for-each-ref", "--format=%(refname)", "refs/heads/worktree-agent-*") or "").split()
        salida = set()
        for l in (self._git("log", "-g", "--format=%H%x1f%gs", "HEAD", *workers, "--") or "").splitlines():
            sha, _, motivo = l.partition("\x1f")
            if CREADO_AQUI.match(motivo):
                salida.add(sha)
        return salida

    def _guardar(self):
        self.vistos = self.vistos[-self.MAX_VISTOS:]
        self._vistos = set(self.vistos)
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"punta": self.punta, "vistos": self.vistos}, f)
        os.replace(tmp, self.ruta)

    def _en_espera(self, sha):
        return ("commit", sha) in self.pendientes.values()

    def _commit(self, sha, ts, asunto, rama, alcanzable):
        actor = {"persona": self.ag.persona, "papel": "humano"}
        m = ID_EN_MENSAJE.search(asunto)
        tarea = m.group(1) if m else None
        if rama.startswith("worktree-agent-"):
            agente = rama[len("worktree-agent-"):]
            actor = {"persona": self.ag.persona, "papel": "worker", "agente": agente}
            tarea = tarea or next((f.nz.tarea_de_agente[agente] for f in self.ag.ficheros.values()
                                   if agente in f.nz.tarea_de_agente), None)
        e = {"v": 1, "id": f"git-{self.ag.persona}-commit-{sha[:12]}", "ts": ts, "actor": actor, "tipo": "commit",
             "fuente": "git", "datos": {"sha": sha, "rama": rama, "alcanzable": alcanzable}}
        if tarea:
            e["tarea"] = tarea
        self.pendientes[e["id"]] = ("commit", sha)
        return e

    def _arbol(self, punta):
        """`arbol` de la copia principal, como el de arbol.sh: `git status` y el diff contra origin/main, sin los
        contratos (colisiones.ficheros conserva los del último `arbol` mientras docs/contratos.md siga cambiado).
        None si git no puede o si no ha cambiado desde el último que emitió el demonio."""
        estado = self._git("-c", "core.quotepath=false", "status", "--porcelain", "-z", crudo=True)
        if estado is None:
            return None
        rutas, trozos = [], estado.split("\0")
        i = 0
        while i < len(trozos):
            t = trozos[i]
            i += 1
            if len(t) < 4:
                continue
            if t[0] in "RC":                     # renombrado o copia: tras el nuevo va el viejo, que no cuenta
                i += 1
            if t[3:] not in rutas:
                rutas.append(t[3:])
        sin_commit = len(rutas)
        if self._git("rev-parse", "HEAD") != punta:
            for r in (self._git("-c", "core.quotepath=false", "diff", "--name-only", f"{punta}...HEAD") or "").splitlines():
                if r and r not in rutas:
                    rutas.append(r)
        datos = {"base": punta}
        if len(rutas) > self.MAX_RUTAS:
            rutas, datos["truncado"] = rutas[:self.MAX_RUTAS], True
        if len(rutas) > sin_commit:              # las últimas, solo del diff (como en normaliza.py)
            datos["solo_diff"] = len(rutas) - sin_commit
        firma = (punta, tuple(rutas))
        if firma == self.firma_arbol:
            return None
        self.firma_arbol = firma
        resumen = hashlib.sha256("\n".join(rutas).encode("utf-8")).hexdigest()[:8]
        return {"v": 1, "id": f"git-{self.ag.persona}-arbol-{punta[:12]}-{resumen}", "ts": self.ag.ahora(),
                "actor": {"persona": self.ag.persona, "papel": "demonio", "worktree": ""}, "tipo": "arbol",
                "fuente": "git", "rutas": rutas, "datos": datos}

    def ciclo(self):
        ahora = self.ag.reloj()
        if ahora - self.ultimo < self.CADA_S:
            return []
        self.ultimo = ahora
        if self._git("rev-parse", "--verify", "-q", "refs/remotes/origin/main") is None:
            return []
        if ahora - self.ultimo_fetch >= self.FETCH_S:
            self.ultimo_fetch = ahora
            self._git("fetch", "--quiet", "origin")
        punta = self._git("rev-parse", "refs/remotes/origin/main")
        eventos, creados = [], None

        def de_aqui(sha):
            nonlocal creados
            if creados is None:                  # una vez por vuelta, y solo si hay algún commit nuevo que mirar
                creados = self._creados()
            return sha in creados
        for rama in (self._git("for-each-ref", "--format=%(refname:short)", "refs/heads") or "").split():
            for sha, ts, asunto in self._log(f"refs/remotes/origin/main..refs/heads/{rama}", "--no-merges") or []:
                if sha not in self._vistos and not self._en_espera(sha) and de_aqui(sha):
                    eventos.append(self._commit(sha, ts, asunto, rama, False))
        if self.punta is None:                   # primera vez: lo que ya estaba subido no es un push nuevo
            self.punta = punta
            self._guardar()
        elif punta != self.punta and ("push", punta) not in self.pendientes.values():
            tramo = self._log(f"{self.punta}..{punta}")
            if tramo is None:                    # punta anterior desconocida (push forzado): los últimos commits
                tramo = self._log(punta, "-n", "50") or []
            # Un merge (traer origin, por ejemplo) no es trabajo de una tarea: no sale como commit (en vivo, M8e).
            merges = set((self._git("rev-list", "--merges", f"{self.punta}..{punta}") or "").split())
            # Los de otras personas (o de otro clon) entran en el `incluye` del push, pero no como commits suyos.
            for sha, ts, asunto in tramo:
                if sha not in self._vistos and not self._en_espera(sha) and sha not in merges and de_aqui(sha):
                    eventos.append(self._commit(sha, ts, asunto, "origin/main", True))
            incluye = [sha for sha, _, asunto in tramo if ID_EN_MENSAJE.search(asunto) or sha in self.ag.fusiones]
            e = {"v": 1, "id": f"git-{self.ag.persona}-push-{punta[:12]}", "ts": self.ag.ahora(),
                 "actor": {"persona": self.ag.persona, "papel": "demonio"}, "tipo": "push", "fuente": "git",
                 "datos": {"sha": punta, "incluye": incluye}}
            self.pendientes[e["id"]] = ("push", punta)
            eventos.append(e)
            a = self._arbol(punta)
            if a:
                eventos.append(a)
        return eventos

    def confirmar(self, ids):
        cambio = False
        for i in list(ids & set(self.pendientes)):
            tipo, valor = self.pendientes.pop(i)
            if tipo == "commit" and valor not in self._vistos:
                self.vistos.append(valor)
                self._vistos.add(valor)
            elif tipo == "push":
                self.punta = valor
            cambio = True
        if cambio:
            self._guardar()


def mensajes_sse(r):
    """(event, data, id) de cada mensaje de un text/event-stream, hasta que se cierra."""
    evento, datos, ident = None, [], None
    while True:
        crudo = r.readline()
        if not crudo:
            return
        l = crudo.decode("utf-8", errors="replace").rstrip("\r\n")
        if not l:
            if evento or datos:
                yield evento or "message", "\n".join(datos), ident
            evento, datos, ident = None, [], None
            continue
        k, _, v = l.partition(":")
        v = v[1:] if v.startswith(" ") else v
        if k == "event":
            evento = v
        elif k == "data":
            datos.append(v)
        elif k == "id":
            ident = v


class Suscripcion:
    """M9a (api.md §4): con `web_nueva: sí`, el demonio lee `GET /v1/stream` del relay en vez de sondear /v1/estado.
    `estado` sustituye a la respuesta del sondeo y `eventos` se reenvía tal cual a la web. Si el stream se corta, el
    ciclo vuelve al sondeo cada 3 s hasta que reconecta (espera creciente hasta 30 s)."""
    TIEMPO_S = 2 * PING_S + 5    # sin nada (ni ping) en este tiempo, el stream se da por cortado

    def __init__(self, ag):
        self.ag = ag

    def correr(self, parar):
        espera = 1
        while not parar.is_set():
            url, token = self.ag._relay()
            if url:
                try:
                    req = urllib.request.Request(url + "/v1/stream", headers={"Authorization": f"Bearer {token}"})
                    with urllib.request.urlopen(req, timeout=self.TIEMPO_S) as r:
                        for evento, datos, ident in mensajes_sse(r):
                            espera = 1
                            self.ag.mensaje_relay(evento, datos, ident)
                            if parar.is_set():
                                return
                except (OSError, ValueError, http.client.HTTPException):
                    pass
                self.ag.corte_relay()
            parar.wait(espera)
            espera = min(espera * 2, ESPERA_MAX_S)


class SaludServicios:
    """M9a (api.md §4, ADR-0011): cada 15 s, puerto y salud de los servicios confirmados de esta persona, solo en
    127.0.0.1. Emite `servicio.estado` una vez al arrancar y después solo cuando cambia (escucha, salud). Nunca ejecuta
    Arranque ni Prueba, y no consulta filas sin confirmar, de otra persona o con un formato que no vale."""
    CADA_S, CONEXION_S, HTTP_S, LEER_MAX = 15, 0.5, 2, 4096

    def __init__(self, ag):
        self.ag = ag
        self.ultimo, self.emitidos, self.cuando = {}, set(), -1e18   # lo último emitido por clave (servicios.json)

    def candidatos(self, estado):
        s = (estado or {}).get("servicios") or {}
        malos = {d.get("clave") for d in s.get("desajustes", []) if d.get("tipo") == "formato_invalido"}
        for x in s.get("lista", []):
            p, salud = x.get("puerto"), x.get("salud")
            if ((x.get("confirmacion") or {}).get("valor") == "confirmada" and x.get("dueno_autoridad") == self.ag.persona
                    and isinstance(p, int) and 1 <= p <= 65535 and x.get("clave") not in malos
                    and servicios.NOMBRE.match(x.get("nombre") or "")
                    and (salud is None or (servicios.SALUD.match(salud) and ".." not in salud
                                           and not salud.startswith("//")))):
                yield x

    def comprobar(self, puerto, salud):
        """(escucha, salud): si el puerto acepta en 127.0.0.1 y el código HTTP de GET <Salud> (None sin Salud o sin
        respuesta). Sin seguir redirecciones y leyendo como mucho 4 KB. HTTP_S es el plazo de toda la consulta, no de
        cada recv (issue #6): un servicio que responde a gotas no bloquea el hilo ni deja sin mirar a los demás. Solo
        hace falta la línea de estado, así que se lee hasta ella."""
        try:
            s = socket.create_connection(("127.0.0.1", puerto), timeout=self.CONEXION_S)
        except OSError:
            return False, None
        datos = b""
        with s:
            if salud is None:
                return True, None
            fin = time.monotonic() + self.HTTP_S
            try:
                s.settimeout(self.HTTP_S)
                s.sendall(f"GET {salud} HTTP/1.1\r\nHost: 127.0.0.1:{puerto}\r\nAccept-Encoding: identity\r\n"
                          "Connection: close\r\n\r\n".encode("ascii"))
                while b"\n" not in datos and len(datos) < self.LEER_MAX:
                    resto = fin - time.monotonic()
                    if resto <= 0:
                        break
                    s.settimeout(resto)
                    trozo = s.recv(self.LEER_MAX - len(datos))
                    if not trozo:
                        break
                    datos += trozo
            except (OSError, UnicodeEncodeError):
                pass
        m = re.match(rb"HTTP/1\.[01] ([1-5][0-9][0-9])(?: [^\r\n]*)?\r?\n", datos)
        return True, int(m.group(1)) if m else None

    def ciclo(self):
        if self.ag.reloj() - self.cuando < self.CADA_S:
            return []
        self.cuando = self.ag.reloj()
        with self.ag.lock:
            estado = self.ag.estado
        eventos = []
        for x in list(self.candidatos(estado)):
            escucha, salud = self.comprobar(x["puerto"], x.get("salud"))
            k = x["clave"]
            valor = {"escucha": escucha, "salud": salud}
            if k in self.emitidos and self.ultimo.get(k) == valor:
                continue
            self.emitidos.add(k)
            self.ultimo[k] = valor
            eventos.append({"v": 1, "id": f"demonio-{self.ag.persona}-servicio-{k}-{int(self.ag.reloj() * 1000)}",
                            "ts": self.ag.ahora(), "actor": {"persona": self.ag.persona, "papel": "demonio"},
                            "tipo": "servicio.estado", "fuente": "demonio",
                            "datos": {"servicio": x["nombre"], "clave": k, "puerto": x["puerto"], **valor}})
        if eventos:
            self.ag._escribe("servicios.json", json.dumps(self.ultimo, ensure_ascii=False))
        return eventos


class Agente:
    def __init__(self, repo, persona, apagado_min=None, reloj=time.time, ahora=ahora_iso):
        self.repo = repo
        self.comun = git_comun(repo)
        self.principal = self.comun[:-len("/.git")] if self.comun.endswith("/.git") else repo
        self.dir = os.path.join(self.comun, "hackathon", "os")
        os.makedirs(self.dir, exist_ok=True)
        self.persona = persona.lower()
        self.reloj, self.ahora = reloj, ahora
        os_md = os.path.join(self.principal, ".hackathon", "os.md")
        try:
            self.apagado_s = 60 * float(apagado_min if apagado_min is not None else conf(os_md, "apagado_min") or 30)
        except ValueError:
            self.apagado_s = 30 * 60
        try:
            self.umbral_viejo_s = float(conf(os_md, "umbral_viejo_s") or 300)
        except ValueError:
            self.umbral_viejo_s = 300
        self.esquema = Esquema("eventos.schema.json")
        base, cache = Contexto(), {}

        def raices(cwd):
            if cwd not in cache:
                cache[cwd] = base.raices(cwd)
            return cache[cwd]
        self.ctx = Contexto(persona=self.persona, raices=raices)
        self.ficheros = {}
        self.cola = []              # eventos normalizados pendientes de enviar
        self.actores = {}           # (sesion, agente) → {papel, worktree, tarea, ultima, cerrado}
        self.corruptas = self.invalidos = 0
        self.ultimo_nuevo = reloj()
        self.espera_hasta, self.espera = 0, 1
        self.relay_estado = "sin token"
        self.ultimo_latido = 0
        self.posiciones = self._cargar_posiciones()
        self.fusiones = set()                    # shas de fusion.aprobada vistos (para el `incluye` del push de git)
        self.git = SondeoGit(self)
        self.lock = threading.Lock()
        # Proyección (M8f): el último estado.json del relay, su ETag, y desde cuándo no llega el relay.
        self.estado, self.etag, self.relay_caido_desde = None, None, None
        self.ultimo_estado = self.ultimo_md = self.ultimo_vivo = -1e18
        self.estado_nuevo = False
        self.tz = None                           # zona de las horas del md; None = la del portátil
        self.vivo, self.puerto = os.path.join(self.dir, "agente.vivo"), None
        # Nivel 2 (M8g): la publicación del trabajo en curso, con `publicar_wip: sí`. La lanza main() en su hilo.
        self.wip = Publicador(self.principal, self.dir, self.persona, lambda k: conf(os_md, k), log=self.log)
        # M9a (api.md §4): la web de trabajo, la suscripción al SSE del relay y la salud de los servicios propios.
        self.web_nueva = web_nueva(os_md)
        self.web_token = self._token_web() if self.web_nueva else None
        self.en_stream, self.md_pendiente, self.relay_ultimo_bueno = False, False, None
        self.web_cambio = threading.Condition()
        self.web_seq, self.web_cola = 0, deque(maxlen=WEB_COLA)     # (seq, evento, datos): lo que va a /v1/stream
        self.web_clientes = 0                                          # clientes de /v1/stream ahora (tope STREAM_MAX)
        self.suscripcion, self.salud_servicios = Suscripcion(self), SaludServicios(self)
        self.acciones = Acciones(self)

    # --- web de trabajo (M9a) ---
    def _token_web(self):
        """web.token: 32 bytes aleatorios en hex, creado la primera vez y reutilizado (fuera de git, ADR-0010)."""
        ruta = os.path.join(self.dir, "web.token")
        try:
            with open(ruta, encoding="utf-8") as f:
                token = f.read().strip()
            if re.fullmatch(r"[0-9a-f]{64}", token):
                if not permisos.es_privado(ruta):        # uno de antes, 0644 o con el ACL heredado: se reescribe igual
                    permisos.escribe_privado(ruta, token + "\n", tmp=f"{ruta}.{os.getpid()}.tmp")
                return token
        except OSError:
            pass
        token = secrets.token_hex(32)
        # Nace ya solo para este usuario (0600, o en Windows un ACL sin herencia), sin ventana (issue #6 y #15).
        permisos.escribe_privado(ruta, token + "\n", tmp=f"{ruta}.{os.getpid()}.tmp")
        return token

    def token_valido(self, dado):
        return bool(self.web_token) and hmac.compare_digest((dado or "").encode("utf-8"), self.web_token.encode("utf-8"))

    def a_la_web(self, evento, datos=None):
        """Un mensaje para los clientes de /v1/stream: `vista` (se calcula al enviarlo) o `eventos` (tal cual)."""
        with self.web_cambio:
            self.web_seq += 1
            self.web_cola.append((self.web_seq, evento, datos))
            self.web_cambio.notify_all()

    def web_esperar(self, visto, espera):
        """(seq, mensajes posteriores a `visto`), esperando como mucho `espera` s a que haya alguno."""
        with self.web_cambio:
            if self.web_seq == visto:
                self.web_cambio.wait(espera)
            return self.web_seq, [(e, d) for s, e, d in self.web_cola if s > visto]

    def vista_web(self):
        """El cuerpo de /v1/vista y del evento `vista` (api.md §4); None sin estado.json todavía."""
        with self.lock:
            estado, caido, desde = self.estado, self.relay_caido_desde, self.relay_ultimo_bueno
        if estado is None:
            return None
        ahora = self.ahora()
        return {"servido_en": ahora, "persona": self.persona, "relay": {"conectado": caido is None, "desde": desde},
                "vista": proyeccion.vista(estado, ahora=ahora, umbral_viejo_s=self.umbral_viejo_s)}

    def accion(self, ruta, cuerpo):
        """Anotar y Reclamar (K-95, acciones.py), ya pasadas las comprobaciones de seguridad. Un fallo inesperado no tumba
        al demonio: 502 con el motivo en una línea."""
        try:
            return self.acciones(ruta, cuerpo)
        except Exception as ex:  # constitución VIII
            self.log(f"acción {ruta}: error: {ex!r}")
            return 502, {"error": f"{type(ex).__name__}: {ex}"[:200]}

    def mensaje_relay(self, evento, datos, ident=None):
        """Un mensaje del SSE del relay (lo llama Suscripcion en su hilo)."""
        if evento == "eventos":
            self.a_la_web("eventos", datos.encode("utf-8"))
        with self.lock:
            self.en_stream = True
            self.relay_ultimo_bueno = self.ahora()
            cambio = self.relay_caido_desde is not None
            self.relay_caido_desde = None
            if evento == "estado":
                try:
                    estado = json.loads(datos)
                except ValueError:
                    estado = None
                if isinstance(estado, dict):
                    self.estado = estado
                    self.etag = f'"{ident}"' if ident else None
                    self._escribe("estado.json", json.dumps(estado, ensure_ascii=False))
                    cambio = True
            if cambio:
                self.md_pendiente = True
                self.a_la_web("vista")

    def corte_relay(self):
        """El stream del relay se ha cortado (o no conecta): el ciclo vuelve al sondeo enseguida. `relay.conectado` es
        false desde el corte hasta el primer mensaje nuevo."""
        with self.lock:
            estaba, self.en_stream = self.en_stream, False
            self.ultimo_estado = -1e18
            if estaba and self.relay_caido_desde is None:
                self.relay_caido_desde = self.ahora()
                self.md_pendiente = True
                self.a_la_web("vista")

    def ciclo_servicios(self):
        eventos = self.salud_servicios.ciclo()
        with self.lock:
            for e in eventos:
                if self.esquema.valido(e):
                    self.cola.append(e)
                else:
                    self.invalidos += 1

    # --- posiciones ---
    def _ruta_pos(self):
        return os.path.join(self.dir, "posiciones.json")

    def _cargar_posiciones(self):
        try:
            with open(self._ruta_pos(), encoding="utf-8") as f:
                p = json.load(f)
            return p if isinstance(p, dict) else {}
        except (OSError, ValueError):
            return {}

    def _guardar_posiciones(self):
        tmp = self._ruta_pos() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.posiciones, f)
        os.replace(tmp, self._ruta_pos())

    # --- lectura ---
    def _abrir(self, ruta):
        """Un fichero visto por primera vez: se normaliza hasta la posición guardada solo para recuperar el estado del
        normalizador (la tarea de cada worker); lo que va detrás se enviará."""
        nombre = os.path.basename(ruta)
        f = self.ficheros[nombre] = Fichero(ruta, Normalizador(self.ctx))
        pos = self.posiciones.get(nombre, {})
        hasta = pos.get("bytes", 0)
        if hasta:
            with open(ruta, "rb") as fh:
                datos = fh.read(hasta)
            for linea in datos.split(b"\n")[:-1] if datos.endswith(b"\n") else datos.split(b"\n"):
                f.leido_linea += 1
                self._procesar(f, linea, f.leido_linea, enviar=False)
            f.leido_bytes = hasta
        return f

    def _procesar(self, f, linea, n, enviar=True):
        try:
            crudo = json.loads(linea.decode("utf-8"))
            if not isinstance(crudo, dict):
                raise ValueError
        except ValueError:
            self.corruptas += 1
            return []
        self._actor(crudo, f.nz)
        try:
            eventos = f.nz.eventos(crudo, n)
        except Exception:  # una línea rara no para al demonio: cuenta como rota
            self.corruptas += 1
            return []
        for e in eventos:
            if e["tipo"] == "fusion.aprobada" and e.get("datos", {}).get("sha"):
                self.fusiones.add(e["datos"]["sha"])
        if not enviar:
            return []
        buenos = []
        for e in eventos:
            if self.esquema.valido(e):
                buenos.append(e)
            else:
                self.invalidos += 1
        return buenos

    def _actor(self, crudo, nz):
        """Lo que va en el latido: actores abiertos con su última señal (cualquier línea de hook cuenta)."""
        sesion, agente = crudo.get("session_id"), crudo.get("agent_id")
        if not sesion or not crudo.get("ts"):
            return
        a = self.actores.setdefault((sesion, agente), {"cerrado": False})
        a["ultima"] = crudo["ts"]
        a["papel"] = nz.papel(crudo.get("agent_type"))
        if crudo.get("tipo") == "compuerta":
            a["papel"] = "worker"
        if crudo.get("cwd") and "worktree" not in a:
            top, principal = self.ctx.raices(crudo["cwd"])
            a["worktree"] = relativa(top, principal)
        if agente and nz.tarea_de_agente.get(agente):
            a["tarea"] = nz.tarea_de_agente[agente]
        tipo = crudo.get("tipo")
        a["cerrado"] = (tipo == "SessionEnd" and not agente) or (tipo == "SubagentStop" and bool(agente))

    def leer(self):
        """Lee lo nuevo de todos los JSONL. No consume la última línea si no acaba en salto (api.md §4)."""
        nuevos = []
        for ruta in sorted(glob.glob(os.path.join(self.dir, "eventos", "*.jsonl"))):
            nombre = os.path.basename(ruta)
            f = self.ficheros.get(nombre) or self._abrir(ruta)
            try:
                with open(ruta, "rb") as fh:
                    fh.seek(f.leido_bytes)
                    datos = fh.read()
            except OSError:
                continue
            fin = datos.rfind(b"\n")
            if fin < 0:
                continue
            pos = f.leido_bytes
            for linea in datos[:fin].split(b"\n"):
                pos += len(linea) + 1
                f.leido_linea += 1
                eventos = self._procesar(f, linea, f.leido_linea)
                f.lineas.append([pos, f.leido_linea, {e["id"] for e in eventos}])
                nuevos += eventos
            f.leido_bytes = pos
            self.ultimo_nuevo = self.reloj()
        nuevos.sort(key=lambda e: (fecha(e["ts"]), e["id"]))
        self.cola += nuevos
        self._confirmar(set())
        return len(nuevos)

    def _confirmar(self, ids):
        """Avanza la posición de cada fichero hasta la última línea cuyos eventos ha confirmado el relay."""
        cambio = False
        for nombre, f in self.ficheros.items():
            for entrada in f.lineas:
                entrada[2] -= ids
            while f.lineas and not f.lineas[0][2]:
                b, n, _ = f.lineas.popleft()
                self.posiciones[nombre] = {"bytes": b, "linea": n}
                cambio = True
        if cambio:
            self._guardar_posiciones()
        if ids:
            self.git.confirmar(ids)

    # --- relay ---
    def _relay(self):
        def leer(nombre):
            try:
                with open(os.path.join(self.dir, nombre), encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                return ""
        url = leer("relay.url") or conf(os.path.join(self.principal, ".hackathon", "os.md"), "relay")
        token = leer("token")
        if not url or "<" in url or not token:
            return None, None
        return url.rstrip("/"), token

    def _post(self, url, token, ruta, cuerpo):
        req = urllib.request.Request(url + ruta, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            datos = r.read()
            return json.loads(datos) if datos else None

    def enviar(self):
        url, token = self._relay()
        if not url:
            self.relay_estado = "sin token"
            return
        if self.reloj() < self.espera_hasta:
            return
        try:
            while self.cola:
                lote = self.cola[:LOTE_MAX]
                self._post(url, token, "/v1/eventos", {"eventos": lote})
                del self.cola[:len(lote)]
                self._confirmar({e["id"] for e in lote})
            if self.reloj() - self.ultimo_latido >= LATIDO_S:
                self._post(url, token, "/v1/latido", self.latido())
                self.ultimo_latido = self.reloj()
            if self.relay_estado != "ok":
                self.log(f"relay {url}: ok")
            self.relay_estado, self.espera = "ok", 1
        except (OSError, ValueError) as ex:
            if self.relay_estado == "ok" or self.relay_estado == "sin token":
                self.relay_estado = f"caído desde {self.ahora()}"
                self.log(f"relay {url}: {ex!r}")
            self.espera_hasta = self.reloj() + self.espera
            self.espera = min(self.espera * 2, ESPERA_MAX_S)

    def abiertos(self):
        ahora = fecha(self.ahora())
        return {k: a for k, a in self.actores.items()
                if not a["cerrado"] and ahora - fecha(a["ultima"]) <= timedelta(seconds=TTL_S)}

    def latido(self):
        actores = []
        for (sesion, agente), a in self.abiertos().items():
            x = {"papel": a["papel"], "sesion": sesion, "ultima_senal": a["ultima"]}
            if agente:
                x["agente"] = agente
            for k in ("worktree", "tarea"):
                if a.get(k) is not None:
                    x[k] = a[k]
            actores.append(x)
        return {"persona": self.persona, "actores": actores, "lineas_corruptas": self.corruptas}

    # --- vida ---
    def debe_apagarse(self):
        return self.reloj() - self.ultimo_nuevo >= self.apagado_s and not self.abiertos()

    def salud(self):
        return (f"hk-os {self.comun}\npendientes: {len(self.cola)}\nlineas_corruptas: {self.corruptas}\n"
                f"invalidos: {self.invalidos}\nrelay: {self.relay_estado}\nwip: {self.wip.salud}\n")

    def log(self, texto):
        ruta = os.path.join(self.dir, "agente.log")
        try:
            if os.path.getsize(ruta) > LOG_MAX:
                os.replace(ruta, ruta + ".1")
        except OSError:
            pass
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(f"{self.ahora()} [{os.getpid()}] {texto}\n")
        except OSError:
            pass

    # --- proyección (M8f) ---
    def recibir_estado(self):
        """Cada ESTADO_S, `GET /v1/estado` con If-None-Match (la alternativa de P15 al SSE: un 304 no cuesta nada).
        Devuelve True si llegó uno nuevo. Con el stream del relay vivo (M9a), no sondea: el estado llega por ahí."""
        if self.en_stream or self.reloj() - self.ultimo_estado < ESTADO_S:
            return False
        self.ultimo_estado = self.reloj()
        url, token = self._relay()
        if not url:
            return False
        cabeceras = {"Authorization": f"Bearer {token}"}
        if self.etag:
            cabeceras["If-None-Match"] = self.etag
        try:
            with urllib.request.urlopen(urllib.request.Request(url + "/v1/estado", headers=cabeceras), timeout=5) as r:
                estado = json.loads(r.read())
                self.etag = r.headers.get("ETag")
        except urllib.error.HTTPError as ex:
            if ex.code == 304:
                self.relay_caido_desde, self.relay_ultimo_bueno = None, self.ahora()
                return False
            self.relay_caido_desde = self.relay_caido_desde or self.ahora()
            return False
        except (OSError, ValueError):
            self.relay_caido_desde = self.relay_caido_desde or self.ahora()
            return False
        self.relay_caido_desde, self.relay_ultimo_bueno = None, self.ahora()
        self.estado = estado
        self._escribe("estado.json", json.dumps(estado, ensure_ascii=False))
        return True

    def escribir_md(self, nuevo):
        """estado-equipo.md (api.md §6) al llegar un estado nuevo, al caer o volver el relay, y cada MD_S (las horas y
        lo «viejo» cambian con el tiempo; las firmas, no)."""
        if self.estado is None or not (nuevo or self.reloj() - self.ultimo_md >= MD_S):
            return
        self.ultimo_md = self.reloj()
        v = proyeccion.vista(self.estado, ahora=self.ahora(), umbral_viejo_s=self.umbral_viejo_s)
        relay = ("viejo", self.relay_caido_desde) if self.relay_caido_desde else None
        texto = proyeccion.markdown(v, self.persona, os.path.join(self.dir, "estado.json").replace("\\", "/"),
                                    tz=self.tz or datetime.now().astimezone().tzinfo, epoch=int(self.reloj()), relay=relay,
                                    avisos_locales=[self.wip.aviso] if self.wip.aviso else None)
        self._escribe("estado-equipo.md", texto)
        # M8g: las reservas de las demás personas, para el aviso de reserva.sh (solo builtins de bash).
        self._escribe("reservas.tsv", proyeccion.reservas_tsv(v, self.persona, self.tz or datetime.now().astimezone().tzinfo))

    def _escribe(self, nombre, texto):
        """Escritura atómica: quien lee (sesion.sh, delta.sh, el MCP) nunca ve un fichero a medias. Los secretos, con
        permisos.escribe_privado."""
        ruta = os.path.join(self.dir, nombre)
        tmp = f"{ruta}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.replace(tmp, ruta)

    def latir_vivo(self):
        """agente.vivo = puerto y hora (época), renovada cada LATIDO_S. delta.sh da por muerto un demonio cuya hora
        tiene más de 60 s, aunque el fichero siga ahí (murió sin borrarlo), y lo relanza."""
        if self.puerto is None or self.reloj() - self.ultimo_vivo < LATIDO_S:
            return
        self.ultimo_vivo = self.reloj()
        self._escribe("agente.vivo", f"{self.puerto}\n{int(self.reloj())}\n")

    def ciclo(self):
        with self.lock:
            self.latir_vivo()
            self.leer()
            for e in self.git.ciclo():
                if self.esquema.valido(e):
                    self.cola.append(e)
                else:
                    self.invalidos += 1
            self.enviar()
            caido = self.relay_caido_desde
            nuevo = self.recibir_estado()
            cambio = nuevo or caido != self.relay_caido_desde
            if cambio and self.web_nueva:
                self.a_la_web("vista")
            self.escribir_md(cambio or self.md_pendiente)     # md_pendiente: lo que trajo el stream del relay
            self.md_pendiente = False


def manejador(agente):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "hk-os-agente"
        sys_version = ""
        timeout = SOCKET_S

        def log_message(self, *args):
            pass

        def _responde(self, codigo, datos=b"", tipo=None, cabeceras=()):
            self.send_response(codigo)
            if tipo:
                self.send_header("Content-Type", tipo)
            for k, v in cabeceras:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            if datos:
                self.wfile.write(datos)

        def _json(self, codigo, obj):
            self._responde(codigo, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8",
                           [("Cache-Control", "no-store")])

        def _local(self):
            """Reglas comunes de M9a (ADR-0010): solo con `web_nueva: sí` (si no, 404, como en M8h); `Host` y, si viene,
            `Origin` de 127.0.0.1 o localhost con este puerto (403 contra DNS rebinding y otras páginas)."""
            if not agente.web_nueva:
                self._responde(404)
                return False
            puerto = self.server.server_address[1]
            locales = {f"127.0.0.1:{puerto}", f"localhost:{puerto}"}
            origen = self.headers.get("Origin")
            if (self.headers.get("Host") or "").lower() not in locales or (
                    origen is not None and origen.lower() not in {"http://" + h for h in locales}):
                self._json(403, {"error": "origen"})
                return False
            return True

        def _con_token(self, consulta):
            """El token, solo en X-HK-Token. Uno en la query (t=, token=) no vale nunca, ni con la cabecera buena."""
            q = urllib.parse.parse_qs(consulta, keep_blank_values=True)
            if "t" in q or "token" in q or not agente.token_valido(self.headers.get("X-HK-Token")):
                self._json(401, {"error": "token"})
                return False
            return True

        def _estatico(self, ruta):
            """El compilado de hkos/web/nueva/: index.html en / y lo que exista en assets/, sin subcarpetas."""
            if ruta == "/":
                fichero, tipo = os.path.join(WEB_NUEVA, "index.html"), "text/html; charset=utf-8"
            else:
                m = re.fullmatch(r"/assets/([A-Za-z0-9][A-Za-z0-9._-]*)", ruta)
                tipo = m and TIPOS_WEB.get(os.path.splitext(m.group(1))[1].lower())
                if not tipo:
                    self._responde(404)
                    return
                fichero = os.path.join(WEB_NUEVA, "assets", m.group(1))
            try:
                with open(fichero, "rb") as f:
                    datos = f.read()
            except OSError:
                self._responde(404)
                return
            cabeceras = [("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
                         ("Referrer-Policy", "no-referrer")]
            if ruta == "/":
                cabeceras.append(("Content-Security-Policy", CSP_WEB))
            self._responde(200, datos, tipo, cabeceras)

        def _cerrado(self):
            """Si el cliente de /v1/stream se ha ido: el socket se puede leer y da EOF (o un error). Lo que mande de
            más no lo cierra."""
            try:
                return bool(select.select([self.connection], [], [], 0)[0]) and not self.connection.recv(
                    1, socket.MSG_PEEK)
            except (OSError, ValueError):
                return True

        def _stream(self):
            """SSE para la web (api.md §4): `vista` al conectar y cada vez que cambia; `eventos` tal como llegan del
            relay; `ping` cada 20 s sin nada más, y con él otra `vista`: `servido_en` y lo «viejo» cambian con el
            tiempo, y la web tiene que decir lo mismo que /v1/vista y estado-equipo.md (issue #6, ADR-0009). Como mucho
            STREAM_MAX clientes a la vez (429 al siguiente). El hueco de una pestaña cerrada se libera en CIERRE_S, no
            con el siguiente ping (issue #15)."""
            with agente.web_cambio:
                lleno = agente.web_clientes >= STREAM_MAX
                if not lleno:
                    agente.web_clientes += 1
            if lleno:
                self._json(429, {"error": "demasiados clientes"})
                return
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                visto, _ = agente.web_esperar(-1, 0)

                def vista():
                    cuerpo = agente.vista_web()
                    if cuerpo is not None:
                        self.wfile.write(b"event: vista\ndata: " + json.dumps(cuerpo, ensure_ascii=False, separators=(
                            ",", ":")).encode("utf-8") + b"\n\n")
                vista()
                self.wfile.flush()
                while True:
                    fin = time.monotonic() + PING_S
                    while True:                 # issue #15: el hueco de una pestaña cerrada no espera al ping
                        visto, nuevos = agente.web_esperar(visto, max(0, min(CIERRE_S, fin - time.monotonic())))
                        if nuevos or time.monotonic() >= fin:
                            break
                        if self._cerrado():
                            return
                    if not nuevos:
                        vista()
                        self.wfile.write(b"event: ping\ndata: \n\n")
                    hecha = False
                    for evento, datos in nuevos:
                        if evento == "vista" and not hecha:        # varias seguidas: con la última basta
                            vista()
                            hecha = True
                        elif evento == "eventos":
                            self.wfile.write(b"event: eventos\ndata: " + datos + b"\n\n")
                    self.wfile.flush()
            except OSError:
                return
            finally:
                with agente.web_cambio:
                    agente.web_clientes -= 1

        def do_GET(self):
            if self.path == "/salud":
                self._responde(200, agente.salud().encode("utf-8"), "text/plain; charset=utf-8")
                return
            if not self._local():
                return
            partes = urllib.parse.urlsplit(self.path)
            ruta = partes.path
            if ruta == "/" or ruta.startswith("/assets/"):
                self._estatico(ruta)
            elif ruta in ("/v1/vista", "/v1/stream"):
                if not self._con_token(partes.query):
                    return
                if ruta == "/v1/stream":
                    self._stream()
                    return
                cuerpo = agente.vista_web()
                if cuerpo is None:
                    self._json(503, {"error": "sin estado"})
                else:
                    self._json(200, cuerpo)
            else:
                self._json(404, {"error": "ruta"})

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = -1
            # Leído antes de cualquier respuesta (en Windows, cerrar sin leer da un RST); lo grande, sin guardarlo.
            try:
                datos = self.rfile.read(n) if 0 <= n <= 16 * ACCION_MAX else None
            except TimeoutError:                            # un cuerpo que no llega en SOCKET_S (issue #6)
                self.close_connection = True
                self._json(408, {"error": "cuerpo"})
                return
            if datos is not None and n > ACCION_MAX:
                datos = None
            if not self._local():
                return
            partes = urllib.parse.urlsplit(self.path)
            if partes.path not in ACCIONES:
                self._json(404, {"error": "ruta"})
                return
            # Primero el tipo: un formulario (text/plain, sin la cabecera del token) sale con 415, no con 401.
            if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
                self._json(415, {"error": "Content-Type"})
                return
            if not self._con_token(partes.query):
                return
            if n > ACCION_MAX:
                self._json(413, {"error": "cuerpo"})
                return
            try:
                if datos is None:
                    raise ValueError
                cuerpo = json.loads(datos.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._json(400, {"error": "el cuerpo no es JSON", "campo": None})
                return
            codigo, obj = agente.accion(partes.path, cuerpo)
            self._json(codigo, obj)

        def do_OPTIONS(self):
            """Ningún preflight se autoriza: 405 y ninguna cabecera Access-Control-* (ADR-0010)."""
            self._responde(405, cabeceras=[("Allow", "GET, POST")])

    return Manejador


def desacoplar():
    """Para los sistemas sin setsid (macOS): doble fork y sesión propia, para sobrevivir al hook que lo lanzó."""
    if not hasattr(os, "fork"):
        return
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    nulo = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(nulo, fd)


def main(argv=None):
    p = argparse.ArgumentParser(description="Demonio local del Hackathon OS (api.md §4)")
    p.add_argument("--repo", required=True, help="copia principal del clon")
    p.add_argument("--persona", required=True, help="usuario de GitHub de la persona del clon (hk_yo)")
    p.add_argument("--puerto", type=int, required=True)
    p.add_argument("--apagado-min", type=float)
    p.add_argument("--desacoplar", action="store_true")
    a = p.parse_args(argv)
    if a.desacoplar:
        desacoplar()
    agente = Agente(a.repo, a.persona, a.apagado_min)
    try:
        servidor = Servidor(("127.0.0.1", a.puerto), manejador(agente))
    except OSError:
        return 0                     # ya hay otro (o el puerto es de otro programa): el arranque lo distingue por /salud
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True).start()
    # agente.vivo: el arranque solo conecta directamente si existe (en Windows, conectar a un puerto cerrado tarda ≈2 s).
    # Lleva la hora, renovada en cada latido: delta.sh no se fía de un fichero huérfano (M8f).
    agente.puerto = a.puerto
    vivo = agente.vivo
    agente.latir_vivo()
    agente.log(f"arranca en 127.0.0.1:{a.puerto} para {agente.persona} ({agente.comun}); "
               f"apagado tras {agente.apagado_s / 60:g} min")
    parar = threading.Event()

    def publicar():
        """Nivel 2 (M8g): en su hilo, para que un push lento no frene los eventos."""
        while not parar.is_set():
            try:
                agente.wip.ciclo()
            except Exception as ex:  # la publicación no tumba al demonio
                agente.log(f"wip: error: {ex!r}")
            parar.wait(5)
    threading.Thread(target=publicar, daemon=True).start()
    if agente.web_nueva:
        def comprobar_servicios():
            """M9a: puerto y salud de los servicios propios, en su hilo (una consulta puede tardar 2,5 s)."""
            while not parar.is_set():
                try:
                    agente.ciclo_servicios()
                except Exception as ex:  # la salud de un servicio no tumba al demonio
                    agente.log(f"servicios: error: {ex!r}")
                parar.wait(1)
        threading.Thread(target=agente.suscripcion.correr, args=(parar,), daemon=True).start()
        threading.Thread(target=comprobar_servicios, daemon=True).start()
        agente.log(f"web de trabajo: http://127.0.0.1:{a.puerto}/ (se abre con hk-os web)")
    try:
        while True:
            try:
                agente.ciclo()
            except Exception as ex:  # el demonio no se cae por un ciclo malo (constitución VIII)
                agente.log(f"error en el ciclo: {ex!r}")
            if agente.debe_apagarse():
                agente.log("sin eventos ni sesiones activas: se apaga")
                break
            time.sleep(CICLO_S)
    finally:
        parar.set()
        servidor.shutdown()
        servidor.server_close()
        try:
            os.remove(vivo)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
