# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Relay del Hackathon OS (M8d, api.md §3): recibe eventos y latidos de los demonios, calcula estado.json con
modelo.py y lo sirve por GET /v1/estado y por SSE. Desde M8e, sondea GitHub (las tareas `hk-tarea`, api.md §8) con
el gh de quien coordina. Desde M8f, sirve la web de solo lectura (`GET /`), la vista de proyeccion.py (`GET /v1/vista`
y el evento SSE `vista`) y las novedades (decisiones y criterios de origin/main). Solo biblioteca estándar (ADR-0005).

Desde M8g, las colisiones (colisiones.py: niveles 1 y 3 en modelo.calcular, nivel 2 con colisiones_merge.Calculo si
os.md tiene `publicar_wip: sí`) y las reservas (`POST /v1/reservas`, `DELETE /v1/reservas/{id}`).

Uso normal: `hk-os relay` (cli.py). Directo, para pruebas:
  uv run --no-project hkos/relay.py --dir <carpeta> --equipo <coordinacion.md> [--ip 127.0.0.1] [--puerto 7777]
"""
import argparse
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colisiones_merge  # noqa: E402
import compilar  # noqa: E402
import contratos as contratos_mod  # noqa: E402
import github  # noqa: E402
import proyeccion  # noqa: E402
import servicios as servicios_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha, iso  # noqa: E402
from modelo import calcular  # noqa: E402
from red import Servidor, ahora_iso, conf, equipo, web_nueva  # noqa: E402

LOTE_MAX = 200
CUERPO_MAX = 2 * 1024 * 1024
RECALCULO_MIN_S = 0.25          # como mucho 4 recálculos por segundo
RECALCULO_RELOJ_S = 5           # y uno cada 5 s, para que la presencia caduque sola (R-18)
PING_S = 20
SONDEO_GITHUB_S = 30            # api.md §8
NOVEDADES_S = 60                # git fetch y lectura de decisiones y criterios (M8f)
SERVICIOS = ".hackathon/servicios.md"   # M9a (api.md §10)
SERVICIOS_COMMITS = 200         # historia de servicios.md que se mira (api.md §3)
REINTENTO_TOPE = 16             # vueltas, como mucho, entre dos intentos de leer una versión que falla
RUTAS_MAX = 5000                # ficheros de origin/main para «código fuera de cualquier servicio»
RECIENTES_MAX = 1000            # eventos guardados para el SSE `eventos` (M9a)
EVENTOS_SSE_MAX = 200           # por mensaje (api.md §3)
RESUMEN_MAX, AUTOR_MAX = 200, 60        # caracteres del resumen y del autor de una novedad (estado.schema.json)
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")
TAILNET = ipaddress.ip_network("100.64.0.0/10")
PRIVADAS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
FALLO = object()                # una lectura de git que falló (Novedades._en)


class Invalido(Exception):
    def __init__(self, error, campo=None, indice=None):
        super().__init__(error)
        self.error, self.campo, self.indice = error, campo, indice


def ip_permitida(ip):
    """R-32: 127.0.0.1, LAN privada o Tailscale. Nunca 0.0.0.0 ni una IP pública."""
    try:
        d = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return d.version == 4 and (d.is_loopback or d in TAILNET or any(d in n for n in PRIVADAS))


def ip_de_lan():
    """La IP de la interfaz de la ruta por defecto (no envía nada: connect de UDP solo elige la interfaz)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def iso_us(t):
    """Segundos de época → ISO 8601 en UTC."""
    return iso(datetime.fromtimestamp(t, timezone.utc))


def _git(repo, *args, timeout=30):
    """Sin objetos de reemplazo (`git replace`): un commit «sin padres» por un reemplazo parecería crear servicios.md
    y añadir todas sus filas (issue #18, ADR-0011). Lo mismo en Novedades._texto."""
    try:
        r = subprocess.run(["git", "--no-replace-objects", "-C", repo, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


DECISION = re.compile(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d) ([+-]\d{4}) · \[#(\d+)\]\([^)]*\) · @([\w-]+) ↔ @([\w-]+) · "
                      r"nivel: [^·]*· (.+)$")
CRITERIO = re.compile(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+)$")


def _con_lo_dicho(resumen, dijo, n=RESUMEN_MAX):
    """«<resumen>: <lo que dijo>» en n caracteres como mucho. Unas palabras literales («…») se cortan por dentro, para
    no perder la » de fuera (nota del PR #17); si no cabe ni una letra entre las comillas, solo el resumen. Lo demás lo
    recorta proyeccion.equilibra, sin partir grafemas."""
    entero = f"{resumen}: {dijo}"
    if len(entero) <= n or len(dijo) < 2 or dijo[0] != "«" or dijo[-1] != "»":
        return entero
    cabe = n - len(resumen) - 4
    return f"{resumen}: «{proyeccion.corta(dijo[1:-1], cabe, '')}»" if cabe > 0 else resumen


def orden_unir(url, token):
    """La orden que cada persona copia. Un token nuevo nunca empieza por «-» (Relay._token); uno viejo que sí, va
    detrás de «--», para que argparse no lo tome por una opción (PR #24)."""
    return f"hk-os unir {url} {'-- ' if token.startswith('-') else ''}{token}"


def novedades_de(decisiones, criterios, tz=None):
    """Las entradas de decisiones.md (las escribe `buzon.sh acordar`) y de criterios.md (`/hack-note`) como
    `novedades` de estado.json. Su texto es dato: el resumen va recortado y las vistas lo entrecomillan con su autor.
    Las comillas del resumen se equilibran aquí, en origen (proyeccion.equilibra, issue #23): la web lo pinta tal cual,
    y el md, igual."""
    tz = tz or datetime.now().astimezone().tzinfo
    salida = []
    for linea in decisiones.splitlines():
        m = DECISION.match(linea.strip())
        if m:
            cuando = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M %z")
            salida.append({"tipo": "decision", "resumen": f"#{m.group(3)}: {m.group(6).strip()}",
                           "autor": f"@{m.group(4)} ↔ @{m.group(5)}", "observado_en": iso(cuando)})
    nota = None
    for linea in criterios.splitlines() + ["## fin"]:
        linea = linea.strip()
        if linea.startswith("## "):
            if nota:
                salida.append(nota)
            m = CRITERIO.match(linea)
            nota = None
            if m:
                cuando = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=tz)
                nota = {"tipo": "criterio", "resumen": proyeccion.equilibra(m.group(2), RESUMEN_MAX),
                        "observado_en": iso(cuando)}
        elif nota and linea.startswith("- Qué dijo:"):
            dijo = proyeccion.equilibra(linea[len("- Qué dijo:"):], RESUMEN_MAX)
            nota["resumen"] = _con_lo_dicho(nota["resumen"], dijo)
        elif nota and linea.startswith("- Anotado por:"):
            autor = linea[len("- Anotado por:"):].strip()
            if autor and autor != "—":
                nota["autor"] = proyeccion.corta(autor, AUTOR_MAX, "")
    for n in salida:
        n["resumen"] = proyeccion.equilibra(n["resumen"], RESUMEN_MAX)
    return salida


class Novedades:
    """Decisiones y criterios de origin/main del clon del relay (M8f), para que todos vean lo mismo (constitución IV).
    `git fetch` cada NOVEDADES_S: si falla (red, refs bloqueadas por un `git pull` de la persona), en silencio, y se
    reintenta en la vuelta siguiente. Solo si dura más de `umbral_s` se refleja en fuentes.git.
    Desde M8g, también los contratos de docs/contratos.md con su dueño de .hackathon/autoridad.md (nivel 3): un bloque
    sin dueño, o con más de una candidata, se dice una vez por `aviso`.
    Desde M9a, con `web_nueva`, lo que necesita servicios.calcular de origin/main (api.md §3): servicios.md, su historia
    (cada versión con la de sus padres; un sha ya leído no se vuelve a leer), autoridad.md, contratos.md y los ficheros.
    Si no se puede leer, se queda lo último bueno; una versión que falla se reintenta tras 1, 2, 4… vueltas (issue #18)."""

    def __init__(self, repo, umbral_s=300, reloj=time.time, git=_git, aviso=None, web_nueva=False):
        self.repo, self.umbral_s, self.reloj, self.git = repo, umbral_s, reloj, git
        self.lista, self.ultimo_ok, self.fallando = [], None, False
        self.contratos, self.aviso, self._avisados = [], aviso, set()
        self.web_nueva, self.servicios, self._versiones, self._crea = web_nueva, None, {}, (None, None)
        self._vuelta, self._fallos = 0, {}       # sha → (fallos seguidos, vuelta del próximo intento)
        self.servicios_ok, self.servicios_fallando = None, False   # la última lectura buena de servicios.md

    def _leer(self, ruta):
        for ref in ("refs/remotes/origin/main", "HEAD"):
            if self.git(self.repo, "rev-parse", "--verify", "-q", ref) is not None:
                return self.git(self.repo, "show", f"{ref}:{ruta}") or ""
        return ""

    def _texto(self, ref, ruta):
        """El fichero en `ref`, tolerando BOM y UTF-16 (servicios.decodificar); None si no existe."""
        try:
            r = subprocess.run(["git", "--no-replace-objects", "-C", self.repo, "show", f"{ref}:{ruta}"],
                               capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return servicios_mod.decodificar(r.stdout) if r.returncode == 0 else None

    def _en(self, ref):
        """servicios.md en `ref`: su texto, None si no está, o FALLO si no se ha podido leer (un fallo no es «no
        estaba»: así contaría todas las filas como añadidas en el commit siguiente, ADR-0011)."""
        esta = self.git(self.repo, "ls-tree", "--name-only", ref, SERVICIOS)
        if esta is None:
            return FALLO
        if not esta.strip():
            return None
        texto = self._texto(ref, SERVICIOS)
        return FALLO if texto is None else texto

    def _version(self, sha):
        """La versión de `sha` con la de sus padres reales, o None si falló alguna lectura: no se guarda en la caché y
        se vuelve a leer más adelante (_leer_servicios: tras 1, 2, 4… vueltas, hasta REINTENTO_TOPE). Mientras, la
        versión no está en la lista y no confirma nada."""
        padres = self.git(self.repo, "log", "-1", "--format=%P", sha)
        if padres is None:
            return None
        textos, texto = [self._en(p) for p in padres.split()], self._en(sha)
        if texto is FALLO or any(t is FALLO for t in textos):
            return None
        return {"sha": sha, "textos_padres": textos, "texto": texto or ""}

    def _bordes(self):
        """Los commits del borde de un clon superficial (git no tiene sus padres: `%P` sale vacío y parecerían crear
        el fichero con todas sus filas). set() si el clon es completo; None si no se sabe. Con `info/grafts`, también
        None: un commit injertado sin padres sería un borde que no está en `shallow` (issue #18)."""
        grafts = (self.git(self.repo, "rev-parse", "--git-path", "info/grafts") or "").strip()
        if not grafts or os.path.exists(os.path.join(self.repo, grafts)):
            return None
        superficial = (self.git(self.repo, "rev-parse", "--is-shallow-repository") or "").strip()
        if superficial == "false":
            return set()
        ruta = (self.git(self.repo, "rev-parse", "--git-path", "shallow") or "").strip()
        if superficial != "true" or not ruta:
            return None
        try:
            with open(os.path.join(self.repo, ruta), encoding="utf-8") as f:
                return set(f.read().split())
        except OSError:
            return None

    def _creacion(self, ref):
        """El sha del commit que creó servicios.md, solo si se sabe con certeza; si no, None (y ninguna fila es de
        /hack-scaffold, ADR-0011). Sin la simplificación de historia de `git log` (un merge que deja el fichero igual
        al de una rama esconde la otra) ni rename: en toda la historia de `ref` tiene que haber un único commit en el
        que el fichero está y no está en ninguno de sus padres, con como mucho un padre y sin venir de un renombrado.
        Dos (una rama sin ancestro común con el scaffold, un fichero borrado y vuelto a crear) ya son la duda."""
        punta = self.git(self.repo, "rev-parse", "--verify", "-q", ref)
        if punta is not None and self._crea[0] == punta:
            return self._crea[1]
        self._crea = (punta, self._nacimiento(ref))
        return self._crea[1]

    def _nacimiento(self, ref):
        log = self.git(self.repo, "log", "--full-history", "-m", "--no-renames", "--diff-filter=A", "--format=%H",
                       ref, "--", SERVICIOS)
        if log is None:
            return None
        nacen = []
        for sha in dict.fromkeys(log.split()):            # con -m, un merge sale una vez por padre
            padres = self.git(self.repo, "log", "-1", "--format=%P", sha)
            if padres is None:
                return None
            padres = padres.split()
            if all(self.git(self.repo, "cat-file", "-e", f"{p}:{SERVICIOS}") is None for p in padres):
                nacen.append((sha, padres))
        if len(nacen) != 1 or len(nacen[0][1]) > 1:
            return None
        sha, padres = nacen[0]
        if padres:
            cambios = self.git(self.repo, "diff-tree", "-r", "-M", "--name-status", "--no-commit-id", padres[0], sha)
            if cambios is None or any(l.startswith("R") and l.split("\t")[-1] == SERVICIOS for l in cambios.splitlines()):
                return None
        return sha

    def _leer_servicios(self, autoridad, contratos):
        """Lo de origin/main que necesita servicios.calcular, None sin servicios.md, o FALLO si no se ha podido leer
        (quien llama se queda con lo último bueno: un fallo no es «ya no está»)."""
        self._vuelta += 1
        ref = next((r for r in ("refs/remotes/origin/main", "HEAD")
                    if self.git(self.repo, "rev-parse", "--verify", "-q", r) is not None), None)
        texto = self._en(ref) if ref else FALLO
        if texto is None or texto is FALLO:
            return texto
        log = self.git(self.repo, "log", "--full-history", "--reverse", "-n", str(SERVICIOS_COMMITS), "--format=%H %ct",
                       ref, "--", SERVICIOS)
        if log is None:
            return FALLO
        # En un clon superficial (o si no se sabe si lo es) no hay creación conocida, y las versiones del borde no se
        # leen: sin sus padres, todas sus filas saldrían añadidas por la persona de ese commit (ADR-0011).
        bordes = self._bordes()
        crea = self._creacion(ref) if bordes == set() else None
        versiones, cuando = [], None
        for linea in log.splitlines():
            partes = linea.split()
            if len(partes) != 2:
                continue
            sha, cuando = partes
            if bordes is None or sha in bordes:
                continue
            if sha not in self._versiones:
                veces, proxima = self._fallos.get(sha, (0, 0))
                if self._vuelta < proxima:
                    continue
                version = self._version(sha)
                if version is None:
                    self._fallos[sha] = (veces + 1, self._vuelta + min(2 ** veces, REINTENTO_TOPE))
                    continue
                self._fallos.pop(sha, None)
                self._versiones[sha] = version
            versiones.append(dict(self._versiones[sha], crea=sha == crea))
        en_log = {linea.split()[0] for linea in log.splitlines() if linea.strip()}
        self._fallos = {s: f for s, f in self._fallos.items() if s in en_log}
        rutas = (self.git(self.repo, "ls-tree", "-r", "--name-only", ref) or "").splitlines()[:RUTAS_MAX]
        return {"texto": texto, "versiones": versiones, "rutas": rutas, "autoridad": autoridad, "contratos": contratos,
                "observado_en": iso_us(float(cuando)) if cuando else iso_us(self.reloj())}

    def sondear(self):
        """True si cambió la lista o el estado del fetch."""
        antes = (self.lista, self.fallando, self.contratos, self.servicios)
        if self.git(self.repo, "fetch", "--quiet", "origin", timeout=20) is None:
            self.fallando = True
        else:
            self.fallando, self.ultimo_ok = False, self.reloj()
        if self.ultimo_ok is None:
            self.ultimo_ok = self.reloj()        # sin un fetch bueno aún, el plazo cuenta desde el arranque
        self.lista = novedades_de(self._leer(".hackathon/decisiones.md"), self._leer(".hackathon/criterios.md"))
        texto_contratos, texto_autoridad = self._leer("docs/contratos.md"), self._leer(".hackathon/autoridad.md")
        self.contratos, avisos = contratos_mod.duenos(texto_contratos, texto_autoridad)
        for a in avisos:
            if a not in self._avisados and self.aviso:
                self._avisados.add(a)
                self.aviso(f"Nivel 3: {a}.")
        if self.web_nueva:
            leido = self._leer_servicios(texto_autoridad, texto_contratos)
            self.servicios_fallando = leido is FALLO
            if leido is not FALLO:
                self.servicios, self.servicios_ok = leido, self.reloj()
            elif self.servicios_ok is None:
                self.servicios_ok = self.reloj()  # sin una lectura buena aún, el plazo cuenta desde el arranque
        return (self.lista, self.fallando, self.contratos, self.servicios) != antes

    def fuente(self):
        """El dato de fuentes.git si el fetch lleva fallando más de umbral_s, o si servicios.md de la punta lleva más de
        umbral_s sin poderse leer (decisión 15B del PR #13: el bloque `servicios` es el último bueno); None si no."""
        if self.fallando and self.reloj() - self.ultimo_ok > self.umbral_s:
            return {"valor": "sin fetch", "fuente": "git", "observado_en": iso_us(self.ultimo_ok)}
        if self.servicios_fallando and self.reloj() - self.servicios_ok > self.umbral_s:
            return {"valor": "sin leer servicios", "fuente": "git", "observado_en": iso_us(self.servicios_ok)}
        return None


class Relay:
    """El estado del relay, sin HTTP. `ahora` se puede inyectar en las pruebas."""

    def __init__(self, carpeta, personas, ahora=ahora_iso, sondeo=None, umbral_parada_s=1200, novedades=None,
                 umbral_viejo_s=300, contratos=None, wip=None, web_nueva=False):
        self.carpeta, self.personas, self.ahora = carpeta, personas, ahora
        # M9a (api.md §3), solo con `web_nueva`: los metadatos de los últimos eventos para el SSE `eventos`
        # ((seq, {id, tipo, persona, papel, ts})), el pulso de GitHub y la caché de las confirmaciones de servicios.
        self.web_nueva, self.seq, self.recientes = web_nueva, 0, []
        self._pulso_github, self._conf_clave, self._conf = False, None, None
        self.sondeo, self.umbral_parada_s = sondeo, umbral_parada_s
        self.novedades, self.umbral_viejo_s = novedades, umbral_viejo_s
        # M8g: los contratos con dueño (fijos en las pruebas; si no, los de `novedades`) y el nivel 2 (Calculo).
        self.contratos, self.wip = contratos, wip
        os.makedirs(carpeta, exist_ok=True)
        self.esquema = Esquema("eventos.schema.json")
        self.token = self._token()
        self.eventos, self.ids = [], set()
        self.latidos = {}             # persona → [eventos latido] (el último latido sustituye al anterior)
        self.corruptas = {}           # persona → {veces, primera_vez, ultima_vez}
        self.descartados = 0
        self.lock = threading.Lock()
        self.cambio = threading.Condition(self.lock)
        self.sucio = threading.Event()
        self.version, self.estado, self.texto, self._huella = 0, None, b"", None
        self.vista = None
        self._cargar()
        if self.sondeo and hasattr(self.sondeo, "de_disco"):   # sin GitHub al arrancar, el último estado conocido (VIII)
            try:
                with open(os.path.join(carpeta, "github.json"), encoding="utf-8") as f:
                    self.sondeo.de_disco(json.load(f))
            except (OSError, ValueError):
                pass
        self.recalcular()

    # --- persistencia ---
    def _token(self):
        ruta = os.path.join(self.carpeta, "token")
        try:
            with open(ruta, encoding="utf-8") as f:
                t = f.read().strip()
            if t:
                return t
        except OSError:
            pass
        t = secrets.token_urlsafe(24)
        while t.startswith("-"):           # 1 de cada 64: `hk-os unir <url> -…` lo tomaría por una opción (PR #24)
            t = secrets.token_urlsafe(24)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(t + "\n")
        return t

    def _cargar(self):
        """Relee eventos.jsonl al arrancar, saltando líneas rotas: los repetidos se reconocen tras reiniciar."""
        try:
            f = open(os.path.join(self.carpeta, "eventos.jsonl"), "rb")
        except OSError:
            return
        with f:
            for linea in f:
                try:
                    e = json.loads(linea.decode("utf-8"))
                except ValueError:
                    continue
                if isinstance(e, dict) and e.get("id") and e["id"] not in self.ids:
                    self.ids.add(e["id"])
                    self.eventos.append(e)

    # --- entradas ---
    def recibir(self, cuerpo):
        """POST /v1/eventos. Lote entero o nada: si un evento no valida, Invalido con su índice y no se guarda nada."""
        if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("eventos"), list):
            raise Invalido("se espera {\"eventos\": [...]}", "eventos")
        lote = cuerpo["eventos"]
        if len(lote) > LOTE_MAX:
            raise Invalido(f"más de {LOTE_MAX} eventos en el lote", "eventos")
        for i, e in enumerate(lote):
            err = self.esquema.error(e)
            if err:
                self.descartados += 1
                raise Invalido(err[1], err[0] or "/", i)
        nuevos = self._anadir(lote)
        return {"aceptados": len(nuevos), "repetidos": len(lote) - len(nuevos)}

    def _anadir(self, lote):
        """Guarda en disco (antes de responder) y en memoria los eventos del lote que no ha visto."""
        with self.lock:
            nuevos, vistos = [], set()
            for e in lote:
                if e["id"] in self.ids or e["id"] in vistos:
                    continue
                vistos.add(e["id"])
                nuevos.append(e)
            if nuevos:
                datos = b"".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
                                 for e in nuevos)
                with open(os.path.join(self.carpeta, "eventos.jsonl"), "ab") as f:
                    f.write(datos)
                    f.flush()
                    os.fsync(f.fileno())
                self.ids |= vistos
                self.eventos += nuevos
                if self.web_nueva:
                    for e in nuevos:
                        self._reciente({"id": e["id"], "tipo": e["tipo"], "persona": e["actor"]["persona"],
                                        "papel": e["actor"]["papel"], "ts": e["ts"]})
                    self.cambio.notify_all()
        if nuevos:
            self.sucio.set()
        return nuevos

    def _reciente(self, meta):
        """Un evento para el SSE `eventos` (M9a). Con self.lock tomado."""
        self.seq += 1
        self.recientes.append((self.seq, meta))
        if len(self.recientes) > RECIENTES_MAX:
            del self.recientes[:len(self.recientes) - RECIENTES_MAX]

    def recientes_desde(self, seq):
        """(última seq, [metadatos] posteriores a `seq`, recortados): lo que aún no ha recibido un cliente. Con self.lock."""
        nuevos = [m for s, m in self.recientes if s > seq]
        return self.seq, nuevos[-EVENTOS_SSE_MAX:], max(0, len(nuevos) - EVENTOS_SSE_MAX)

    # --- reservas (M8g, api.md §3) ---
    def reservar(self, cuerpo):
        """POST /v1/reservas: `{persona, actor?, rutas, ttl_s, modo}` → evento `reserva` con la hora del relay (así
        caduca con un solo reloj). Devuelve {id, hasta}. Las rutas: relativas a la raíz del repo, con «/»."""
        if not isinstance(cuerpo, dict):
            raise Invalido("se espera un objeto")
        persona = cuerpo.get("persona")
        if not isinstance(persona, str) or persona.lower() not in {p["persona"] for p in self.personas}:
            raise Invalido("persona fuera de la tabla de coordinacion.md", "persona")
        rutas = cuerpo.get("rutas")
        if not isinstance(rutas, list) or not 1 <= len(rutas) <= 50:
            raise Invalido("rutas: de 1 a 50", "rutas")
        limpias = []
        for i, r in enumerate(rutas):
            r = r.replace("\\", "/").strip() if isinstance(r, str) else ""
            while r.startswith("./"):
                r = r[2:]
            if not r or len(r) > 300 or r.startswith("/") or re.match(r"^[A-Za-z]:", r) or ".." in r.split("/"):
                raise Invalido("ruta no relativa al repo", "rutas", i)
            limpias.append(r)
        ttl = cuerpo.get("ttl_s", 900)
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not 30 <= ttl <= 7200:
            raise Invalido("ttl_s: entero de 30 a 7200", "ttl_s")
        modo = cuerpo.get("modo", "compartida")
        if modo not in ("exclusiva", "compartida"):
            raise Invalido("modo: exclusiva o compartida", "modo")
        ts = self.ahora()
        actor = {"persona": persona.lower(), "papel": "principal"}
        if isinstance(cuerpo.get("actor"), str) and cuerpo["actor"]:
            actor["sesion"] = cuerpo["actor"][:100]
        e = {"v": 1, "id": f"reserva-{secrets.token_hex(6)}", "ts": ts, "actor": actor, "tipo": "reserva",
             "rutas": limpias, "fuente": "mcp", "datos": {"ttl_s": ttl, "modo": modo}}
        err = self.esquema.error(e)
        if err:
            raise Invalido(err[1], err[0])
        self._anadir([e])
        return {"id": e["id"], "hasta": iso(fecha(ts) + timedelta(seconds=ttl))}

    def liberar(self, rid, persona):
        """DELETE /v1/reservas/{id}?persona=…: solo quien reservó. False si no existe o no es suya."""
        with self.lock:
            r = next((e for e in self.eventos if e["id"] == rid and e["tipo"] == "reserva"), None)
        if r is None or r["actor"]["persona"] != (persona or "").lower():
            return False
        e = {"v": 1, "id": f"liberacion-{rid}", "ts": self.ahora(), "actor": dict(r["actor"]), "tipo": "liberacion",
             "fuente": "mcp", "datos": {"reserva": rid}}
        self._anadir([e])
        return True

    def latido(self, cuerpo):
        """POST /v1/latido: la lista completa de actores abiertos de una persona, cada uno con su última señal."""
        if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("persona"), str):
            raise Invalido("falta persona", "persona")
        persona = cuerpo["persona"]
        actores = cuerpo.get("actores", [])
        if not isinstance(actores, list):
            raise Invalido("actores debe ser una lista", "actores")
        eventos = []
        for i, a in enumerate(actores):
            if not isinstance(a, dict):
                raise Invalido("actor mal formado", "actores", i)
            actor = {"persona": persona, "papel": a.get("papel")}
            for k in ("sesion", "agente", "worktree"):
                if a.get(k) is not None:
                    actor[k] = a[k]
            e = {"v": 1, "id": f"latido-{persona}-{i}", "ts": a.get("ultima_senal"), "actor": actor,
                 "tipo": "latido", "fuente": "hook"}
            if a.get("tarea"):
                e["tarea"] = a["tarea"]
            err = self.esquema.error(e)
            if err:
                raise Invalido(err[1], f"actores/{i}{err[0]}", i)
            eventos.append(e)
        n = cuerpo.get("lineas_corruptas", 0)
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise Invalido("lineas_corruptas debe ser un entero ≥ 0", "lineas_corruptas")
        with self.lock:
            self.latidos[persona] = eventos
            if n:
                ahora = self.ahora()
                c = self.corruptas.setdefault(persona, {"veces": 0, "primera_vez": ahora})
                if c["veces"] != n:
                    c["veces"], c["ultima_vez"] = n, ahora
        self.sucio.set()

    # --- estado ---
    def recalcular(self):
        with self.lock:
            eventos = list(self.eventos)
            for lista in self.latidos.values():
                eventos += lista
            corruptas = {p: dict(c) for p, c in self.corruptas.items()}
        ahora = self.ahora()
        # Un portátil con el reloj adelantado no debe quedar invisible hasta que el del relay lo alcance.
        if eventos:
            ultimo = max(eventos, key=lambda e: fecha(e["ts"]))["ts"]
            if fecha(ultimo) > fecha(ahora):
                ahora = ultimo
        fuentes = {"relay": {"valor": "ok", "fuente": "derivado", "observado_en": ahora}}
        tareas, issues, disc = [], {}, []
        if self.sondeo:
            with self.lock:
                tareas, issues, disc, escrituras = self.sondeo.resultado(fecha(ahora))
                visto = self.sondeo.ultimo_ok
                # Con `github: no` (M8h), las tareas salen de plan.md: valor «no», fuente git y la hora del commit del plan.
                fuentes["github"] = {"valor": self.sondeo.estado, "fuente": getattr(self.sondeo, "fuente", "github"),
                                     "observado_en": iso_us(visto) if visto else ahora}
            if escrituras >= github.TOPE_HORA:
                print(f"relay: {escrituras} escrituras del equipo a GitHub en la última hora (tope {github.TOPE_HORA}, R-30)",
                      file=sys.stderr, flush=True)
        de_git = [e["ts"] for e in eventos if e.get("fuente") == "git"]
        if de_git:
            fuentes["git"] = {"valor": "ok", "fuente": "git", "observado_en": max(de_git, key=fecha)}
        novedades, contratos, conflictos = None, self.contratos, None
        if self.novedades:
            with self.lock:
                novedades = list(self.novedades.lista)
                sin_fetch = self.novedades.fuente()
                if contratos is None:
                    contratos = list(self.novedades.contratos)
            if sin_fetch:
                fuentes["git"] = sin_fetch
        if self.wip:
            with self.lock:
                conflictos = list(self.wip.conflictos)
        estado = calcular(tareas, issues, eventos, self.personas, ahora, self.umbral_parada_s, fuentes, disc, novedades,
                          contratos=contratos, conflictos=conflictos)
        for p, c in sorted(corruptas.items()):
            estado["discrepancias"].append({"tipo": "linea_corrupta", "persona": p, "veces": c["veces"],
                                            "primera_vez": c["primera_vez"], "ultima_vez": c.get("ultima_vez", c["primera_vez"]),
                                            "detalle": f"{c['veces']} líneas rotas en los JSONL de {p}"})
        if self.web_nueva and self.novedades:          # M9a: servicios (api.md §3, ADR-0011)
            with self.lock:
                leido = self.novedades.servicios
            if leido:
                estado["servicios"] = self._servicios(leido, eventos)
        # Sin la hora del cálculo ni la del relay: solo hay versión nueva (y SSE) si cambia algo de verdad.
        sin_hora = dict(estado, generado_en=None, fuentes={k: v for k, v in estado["fuentes"].items() if k != "relay"})
        # M8h: un sondeo bueno de GitHub sin cambios solo mueve la hora de fuentes.github. No es una versión nueva
        # (ni un SSE) hasta que esa hora avanza un tercio de umbral_viejo_s: así nada se ve «viejo» sin serlo.
        gh, pub = estado["fuentes"].get("github"), (self.estado or {}).get("fuentes", {}).get("github")
        if gh and pub and gh["valor"] == pub["valor"] == "ok" and gh["fuente"] == pub["fuente"] and \
                (fecha(gh["observado_en"]) - fecha(pub["observado_en"])).total_seconds() < self.umbral_viejo_s / 3:
            sin_hora["fuentes"] = dict(sin_hora["fuentes"], github=pub)
        huella = hashlib.sha256(json.dumps(sin_hora, sort_keys=True).encode("utf-8")).hexdigest()
        with self.cambio:
            if huella != self._huella:
                self._huella = huella
                self.version += 1
                self.estado = estado
                self.texto = json.dumps(estado, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.vista = proyeccion.vista(estado, umbral_viejo_s=self.umbral_viejo_s)
                if self.web_nueva and self._pulso_github:   # M9a: el sondeo trajo un cambio que saca versión
                    self._pulso_github = False
                    self._reciente({"id": f"github-{self.version}", "tipo": "github.sondeo", "persona": None,
                                    "papel": None, "ts": estado["generado_en"]})
                self.cambio.notify_all()
            else:
                self._pulso_github = False         # un cambio de GitHub que no cambia el estado no es un paquete

    def _servicios(self, leido, eventos):
        """El bloque `servicios` (servicios.calcular) con lo leído de origin/main y los eventos del registro: la persona
        de cada commit, la última comprobación de cada demonio por clave, el último resultado de cada Prueba y las rutas
        del último `arbol` de cada actor."""
        sha_persona = servicios_mod.personas_de_commits(eventos)
        shas = tuple(v["sha"] for v in leido["versiones"])
        clave = (shas, tuple(v.get("crea") for v in leido["versiones"]), tuple(sha_persona.get(s) for s in shas))
        if clave != self._conf_clave:
            self._conf_clave, self._conf = clave, servicios_mod.confirmaciones(leido["versiones"], sha_persona)
        comprobados, pruebas, arboles = {}, {}, {}
        for e in sorted(eventos, key=lambda e: fecha(e["ts"])):
            d, actor = e.get("datos") or {}, e["actor"]
            if e["tipo"] == "servicio.estado" and d.get("clave"):
                comprobados.setdefault(d["clave"], {})[actor["persona"]] = {
                    "valor": {"escucha": d.get("escucha"), "salud": d.get("salud")}, "fuente": "demonio",
                    "observado_en": e["ts"]}
            elif e["tipo"] == "prueba" and d.get("comando_sha") and d.get("resultado"):
                pruebas[d["comando_sha"]] = {"valor": d["resultado"], "fuente": "hook", "observado_en": e["ts"]}
            elif e["tipo"] == "arbol":
                arboles[(actor["persona"], actor.get("sesion"), actor.get("agente"))] = (e.get("rutas") or [], e["ts"])
        rutas, ts_rutas = set(leido["rutas"]), leido["observado_en"]
        for rs, ts in arboles.values():
            rutas.update(rs)
            ts_rutas = max(ts_rutas, ts, key=fecha)
        return servicios_mod.calcular(leido["texto"], leido["versiones"], sha_persona, leido["autoridad"],
                                      leido["contratos"], sorted(rutas), comprobados, pruebas, leido["observado_en"],
                                      ts_rutas, confirmado=self._conf)

    def bucle(self, parar):
        """Recalcula tras cada lote (como mucho cada RECALCULO_MIN_S) y cada RECALCULO_RELOJ_S."""
        while not parar.is_set():
            self.sucio.wait(RECALCULO_RELOJ_S)
            self.sucio.clear()
            try:
                self.recalcular()
            except Exception as ex:  # un fallo de cálculo no tumba el relay
                print(f"relay: error al recalcular: {ex!r}", file=sys.stderr, flush=True)
            parar.wait(RECALCULO_MIN_S)

    def bucle_github(self, parar):
        """Sondeo de GitHub cada SONDEO_GITHUB_S (api.md §8). Guarda la instantánea para arrancar sin GitHub."""
        while not parar.is_set():
            try:
                with self.lock:
                    estado_antes = self.sondeo.estado
                cambio = self.sondeo.sondear()
                if cambio and hasattr(self.sondeo, "a_disco"):
                    with self.lock:
                        foto = self.sondeo.a_disco()
                    tmp = os.path.join(self.carpeta, "github.json.tmp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(foto, f)
                    os.replace(tmp, os.path.join(self.carpeta, "github.json"))
                if cambio and self.web_nueva:
                    with self.lock:
                        self._pulso_github = True
                if cambio or self.sondeo.estado != estado_antes:
                    self.sucio.set()
            except Exception as ex:  # el sondeo no tumba el relay
                print(f"relay: error al sondear GitHub: {ex!r}", file=sys.stderr, flush=True)
            parar.wait(SONDEO_GITHUB_S)

    def bucle_novedades(self, parar):
        """Decisiones y criterios de origin/main cada NOVEDADES_S (M8f)."""
        while not parar.is_set():
            try:
                if self.novedades.sondear():
                    self.sucio.set()
            except Exception as ex:  # las novedades no tumban el relay
                print(f"relay: error al leer las novedades: {ex!r}", file=sys.stderr, flush=True)
            parar.wait(NOVEDADES_S)

    def bucle_wip(self, parar):
        """Nivel 2 (M8g): refs de trabajo en curso y merge-tree por pares cada colisiones_merge.Calculo.CADA_S."""
        while not parar.is_set():
            try:
                if self.wip.sondear():
                    self.sucio.set()
            except Exception as ex:  # el nivel 2 no tumba el relay
                print(f"relay: error en el nivel 2: {ex!r}", file=sys.stderr, flush=True)
            parar.wait(colisiones_merge.Calculo.CADA_S)

    def actual(self):
        with self.lock:
            return self.version, self.texto

    def vista_servida(self):
        """(versión, cuerpo de /v1/vista): la vista y la hora del relay al servirla, con la que la web calcula «hace X»
        sin fiarse del reloj del dispositivo."""
        with self.lock:
            version, v = self.version, self.vista
        cuerpo = proyeccion.con_hora(v, self.ahora())
        return version, json.dumps(cuerpo, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def manejador(relay):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "hk-os-relay"
        sys_version = ""

        def log_message(self, *args):
            pass

        def _json(self, codigo, obj=None, cabeceras=()):
            datos = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            if obj is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            for k, v in cabeceras:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            if datos:
                self.wfile.write(datos)

        def _autorizado(self):
            dado = self.headers.get("Authorization", "")
            if hmac.compare_digest(dado.encode("utf-8"), f"Bearer {relay.token}".encode("utf-8")):
                return True
            self._json(401, {"error": "token"})
            return False

        def _cuerpo(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise Invalido("Content-Length no válido")
            if n > CUERPO_MAX:
                raise Invalido("cuerpo demasiado grande")
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise Invalido("el cuerpo no es JSON")

        def do_POST(self):
            if not self._autorizado():
                return
            try:
                if self.path == "/v1/eventos":
                    self._json(200, relay.recibir(self._cuerpo()))
                elif self.path == "/v1/latido":
                    relay.latido(self._cuerpo())
                    self._json(204)
                elif self.path == "/v1/reservas":
                    self._json(200, relay.reservar(self._cuerpo()))
                else:
                    self._json(404, {"error": "ruta"})
            except Invalido as ex:
                err = {"error": ex.error, "campo": ex.campo}
                if ex.indice is not None:
                    err["indice"] = ex.indice
                self._json(400, err)

        def do_DELETE(self):
            """DELETE /v1/reservas/{id}?persona=<usuario> (M8g): solo quien reservó la libera."""
            if not self._autorizado():
                return
            ruta, _, consulta = self.path.partition("?")
            m = re.fullmatch(r"/v1/reservas/([A-Za-z0-9_-]{1,80})", ruta)
            if not m:
                self._json(404, {"error": "ruta"})
                return
            persona = dict(x.partition("=")[::2] for x in consulta.split("&") if x).get("persona", "")
            if relay.liberar(m.group(1), persona):
                self._json(204)
            else:
                self._json(404, {"error": "reserva", "campo": "id"})

        def _web(self):
            """La web de solo lectura (api.md §3): HTML estático, sin datos. El token va en el fragmento (#t=…), que
            el navegador no envía; los datos se piden con él a /v1/stream y /v1/vista."""
            try:
                with open(WEB, "rb") as f:
                    datos = f.read()
            except OSError:
                self._json(404, {"error": "web"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                self._web()
                return
            if not self._autorizado():
                return
            if self.path == "/v1/vista":
                version, texto = relay.vista_servida()
                etiqueta = f'"{version}"'
                if self.headers.get("If-None-Match") == etiqueta:
                    self._json(304, cabeceras=[("ETag", etiqueta)])
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("ETag", etiqueta)
                self.send_header("Content-Length", str(len(texto)))
                self.end_headers()
                self.wfile.write(texto)
            elif self.path == "/v1/estado":
                version, texto = relay.actual()
                etiqueta = f'"{version}"'
                if self.headers.get("If-None-Match") == etiqueta:
                    self._json(304, cabeceras=[("ETag", etiqueta)])
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("ETag", etiqueta)
                self.send_header("Content-Length", str(len(texto)))
                self.end_headers()
                self.wfile.write(texto)
            elif self.path == "/v1/stream":
                self._stream()
            else:
                self._json(404, {"error": "ruta"})

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            enviada = None
            with relay.lock:
                visto = relay.seq          # M9a: un cliente nuevo no recibe los eventos de antes (api.md §3)
            try:
                while True:
                    with relay.cambio:
                        if relay.version == enviada and relay.seq == visto:
                            relay.cambio.wait(PING_S)
                        version, texto = relay.version, relay.texto
                        visto, nuevos, recortados = relay.recientes_desde(visto)
                    escrito = False
                    if version != enviada:
                        self.wfile.write(b"id: %d\nevent: estado\ndata: " % version + texto + b"\n\n")
                        _, vista = relay.vista_servida()
                        self.wfile.write(b"id: %d\nevent: vista\ndata: " % version + vista + b"\n\n")
                        enviada, escrito = version, True
                    if nuevos:
                        cuerpo = {"eventos": nuevos}
                        if recortados:
                            cuerpo["recortados"] = recortados
                        self.wfile.write(b"event: eventos\ndata: " + json.dumps(cuerpo, ensure_ascii=False, separators=(
                            ",", ":")).encode("utf-8") + b"\n\n")
                        escrito = True
                    if not escrito:
                        self.wfile.write(b"event: ping\ndata: \n\n")
                    self.wfile.flush()
            except OSError:
                return

    return Manejador


def sondeo_de(os_md, equipo_md, personas, aviso):
    """El sondeo de GitHub del relay: repo de `repo_tareas:` (os.md) o `repo:` (coordinacion.md) y el gh de quien
    coordina. Sin repo o sin sesión de gh, el relay sigue sin GitHub (constitución VIII) y lo dice."""
    repo = (conf(os_md, "repo_tareas") if os_md else "") or conf(equipo_md, "repo")
    if not repo or "<" in repo:
        aviso("Sin GitHub: no hay repo en coordinacion.md ni repo_tareas en os.md.")
        return None
    token = github.token_de_gh()
    if not token:
        aviso("Sin GitHub: gh no tiene sesión en este portátil (gh auth login).")
        return None
    cliente = github.Cliente(repo, token, base=os.environ.get("HKOS_GITHUB_API", github.API))
    return github.Sondeo(cliente, {p["persona"] for p in personas})


def servir(carpeta, equipo_md, ip, puerto, aviso=print, os_md=None, con_github=True):
    if not ip_permitida(ip):
        raise SystemExit(f"hk-os relay: {ip} no es 127.0.0.1, una IP privada de LAN ni una de Tailscale; "
                         "el relay no escucha ahí (R-32). Indica otra con --ip.")
    personas = equipo(equipo_md)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(equipo_md)))
    es_repo = _git(repo, "rev-parse", "--git-dir") is not None
    if os_md and compilar.sin_github(os_md):        # M8h, K-80: las tareas, de plan.md de origin/main
        sondeo = compilar.SondeoPlan(repo, personas, aviso=aviso) if es_repo else None
    else:
        sondeo = sondeo_de(os_md, equipo_md, personas, aviso) if con_github else None
    try:
        umbral = 60 * float(conf(os_md, "umbral_parada_min") or 20) if os_md else 1200
    except ValueError:
        umbral = 1200
    try:
        viejo = float(conf(os_md, "umbral_viejo_s") or 300) if os_md else 300
    except ValueError:
        viejo = 300
    nueva = web_nueva(os_md)                        # M9a: SSE `eventos` y `servicios` (api.md §0 y §3)
    novedades = Novedades(repo, viejo, aviso=aviso, web_nueva=nueva) if es_repo else None
    wip = None
    if es_repo and os_md and colisiones_merge.modo_publicar(conf(os_md, "publicar_wip"))[0]:
        wip = colisiones_merge.Calculo(repo, {p["persona"] for p in personas}, aviso=aviso)
        wip = wip if wip.activo else None
    relay = Relay(carpeta, personas, sondeo=sondeo, umbral_parada_s=umbral, novedades=novedades, umbral_viejo_s=viejo,
                  wip=wip, web_nueva=nueva)
    if nueva:
        aviso("Web de trabajo (web_nueva: sí): SSE `eventos` y servicios de .hackathon/servicios.md.")
    servidor = Servidor((ip, puerto), manejador(relay))
    parar = threading.Event()
    threading.Thread(target=relay.bucle, args=(parar,), daemon=True).start()
    if sondeo:
        threading.Thread(target=relay.bucle_github, args=(parar,), daemon=True).start()
        if isinstance(sondeo, compilar.SondeoPlan):
            aviso(f"Sin GitHub (github: no): las tareas salen de .hackathon/plan.md de origin/main, cada {SONDEO_GITHUB_S} s.")
        else:
            aviso(f"Sondeo de GitHub: {sondeo.c.repo}, cada {SONDEO_GITHUB_S} s.")
    if novedades:
        threading.Thread(target=relay.bucle_novedades, args=(parar,), daemon=True).start()
    if wip:
        threading.Thread(target=relay.bucle_wip, args=(parar,), daemon=True).start()
        aviso(f"Nivel 2 (publicar_wip): merge-tree de refs/hackathon/wip/* cada {colisiones_merge.Calculo.CADA_S} s.")
    url = f"http://{ip}:{servidor.server_address[1]}"
    aviso(f"Relay del Hackathon OS en {url} ({len(personas)} personas en coordinacion.md, "
          f"{len(relay.eventos)} eventos guardados).")
    aviso(f"Token: {relay.token}")
    aviso(f"Cada persona, en su clon: {orden_unir(url, relay.token)}")
    aviso(f"Web (solo lectura, desde un navegador de la misma red): {url}/#t={relay.token}")
    try:
        servidor.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        servidor.server_close()


def main(argv=None):
    p = argparse.ArgumentParser(description="Relay del Hackathon OS (api.md §3)")
    p.add_argument("--dir", required=True, help="carpeta del registro y del token (<git común>/hackathon/os/relay)")
    p.add_argument("--equipo", required=True, help="ruta de .hackathon/coordinacion.md")
    p.add_argument("--ip", help="IP de escucha (por defecto, la de la LAN)")
    p.add_argument("--puerto", type=int, default=7777)
    p.add_argument("--os", help="ruta de .hackathon/os.md (repo_tareas, umbral_parada_min)")
    p.add_argument("--sin-github", action="store_true", help="no sondear GitHub")
    a = p.parse_args(argv)
    ip = a.ip or ip_de_lan()
    if not ip:
        raise SystemExit("hk-os relay: no encuentro la IP de la LAN; indícala con --ip.")
    servir(a.dir, a.equipo, ip, a.puerto, aviso=lambda s: print(s, flush=True), os_md=a.os, con_github=not a.sin_github)


if __name__ == "__main__":
    main()
