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
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import timedelta
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esquema import Esquema  # noqa: E402
from estados import fecha  # noqa: E402
from normaliza import Contexto, Normalizador, relativa  # noqa: E402
from red import Servidor, ahora_iso, conf  # noqa: E402

CICLO_S = 1
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
        self.lock = threading.Lock()

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
                f"invalidos: {self.invalidos}\nrelay: {self.relay_estado}\n")

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

    def ciclo(self):
        with self.lock:
            self.leer()
            self.enviar()


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
    vivo = os.path.join(agente.dir, "agente.vivo")
    with open(vivo, "w", encoding="utf-8") as f:
        f.write(f"{a.puerto}\n")
    agente.log(f"arranca en 127.0.0.1:{a.puerto} para {agente.persona} ({agente.comun}); "
               f"apagado tras {agente.apagado_s / 60:g} min")
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
        servidor.shutdown()
        servidor.server_close()
        try:
            os.remove(vivo)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
