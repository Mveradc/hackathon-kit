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
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colisiones_merge import Publicador  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha  # noqa: E402
import proyeccion  # noqa: E402
from normaliza import Contexto, Normalizador, relativa  # noqa: E402
from red import Servidor, ahora_iso, conf  # noqa: E402

CICLO_S = 1
ESTADO_S = 3                     # M8f: GET /v1/estado con ETag (P15)
MD_S = 30                        # M8f: estado-equipo.md se reescribe al menos cada 30 s (horas y «viejo»)
LATIDO_S = 15
TTL_S = 90                       # R-18: una sesión sin señales deja de estar activa
LOTE_MAX = 200
ESPERA_MAX_S = 30
LOG_MAX = 1024 * 1024


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


class SondeoGit:
    """Sondeo de git del demonio (api.md §4, M8e): commits nuevos de las ramas locales y cambios de origin/main, como
    eventos de fuente git. Lo que pide M8e: `commit` (con la tarea si el mensaje cita un ID, o la del encargo en una
    rama de worker) y `push` (con `incluye`), para que una tarea llegue a `publicada` y una rama sin ID salga en
    `sin_tarea`. Un commit o la punta nueva solo quedan vistos cuando el relay los confirma: si el demonio se reinicia
    antes, se vuelven a emitir con el mismo ID y el relay los descarta. El `arbol` de git por worktree y la
    reconciliación de `fusion.*` por refs quedan para más adelante."""
    CADA_S, FETCH_S, MAX_VISTOS = 15, 60, 5000

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
        self.correo = None                       # user.email del clon, para saber qué commits son de esta persona
        self.ultimo = self.ultimo_fetch = -1e18

    def _git(self, *args):
        try:
            r = subprocess.run(["git", "-C", self.ag.principal, *args], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    def _log(self, rango, *mas):
        """[(sha, hora en UTC, correo de quien hizo el commit, asunto)] del más viejo al más nuevo; None si git no puede
        (punta desconocida)."""
        t = self._git("log", "--reverse", "--format=%H%x1f%cI%x1f%ce%x1f%s", *mas, rango)
        if t is None:
            return None
        salida = []
        for l in t.splitlines():
            if l.count("\x1f") == 3:
                sha, ts, correo, asunto = l.split("\x1f", 3)
                ts = datetime.fromisoformat(ts).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                salida.append((sha, ts, correo.lower(), asunto))
        return salida

    def _propio(self, sha, correo):
        """¿Es de esta persona un commit que llega por origin/main? Por el correo del clon (`user.email`); sin él, si lo
        alcanza una rama local. Un commit de otra persona entra en el `incluye` del push, pero no como commit suyo."""
        if self.correo is None:
            self.correo = (self._git("config", "user.email") or "").lower()
        if self.correo:
            return correo == self.correo
        return bool(self._git("for-each-ref", "--contains", sha, "--format=%(refname)", "refs/heads"))

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
        eventos = []
        for rama in (self._git("for-each-ref", "--format=%(refname:short)", "refs/heads") or "").split():
            for sha, ts, _, asunto in self._log(f"refs/remotes/origin/main..refs/heads/{rama}", "--no-merges") or []:
                if sha not in self._vistos and not self._en_espera(sha):
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
            for sha, ts, correo, asunto in tramo:
                if sha not in self._vistos and not self._en_espera(sha) and sha not in merges and self._propio(sha, correo):
                    eventos.append(self._commit(sha, ts, asunto, "origin/main", True))
            incluye = [sha for sha, _, _, asunto in tramo if ID_EN_MENSAJE.search(asunto) or sha in self.ag.fusiones]
            e = {"v": 1, "id": f"git-{self.ag.persona}-push-{punta[:12]}", "ts": self.ag.ahora(),
                 "actor": {"persona": self.ag.persona, "papel": "demonio"}, "tipo": "push", "fuente": "git",
                 "datos": {"sha": punta, "incluye": incluye}}
            self.pendientes[e["id"]] = ("push", punta)
            eventos.append(e)
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
        Devuelve True si llegó uno nuevo."""
        if self.reloj() - self.ultimo_estado < ESTADO_S:
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
                self.relay_caido_desde = None
                return False
            self.relay_caido_desde = self.relay_caido_desde or self.ahora()
            return False
        except (OSError, ValueError):
            self.relay_caido_desde = self.relay_caido_desde or self.ahora()
            return False
        self.relay_caido_desde = None
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
        """Escritura atómica: quien lee (sesion.sh, delta.sh, el MCP) nunca ve un fichero a medias."""
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
            self.escribir_md(nuevo or caido != self.relay_caido_desde)


def manejador(agente):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "hk-os-agente"
        sys_version = ""

        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path != "/salud":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            datos = agente.salud().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

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
