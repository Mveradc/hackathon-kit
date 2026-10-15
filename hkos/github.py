"""GitHub para el Hackathon OS (M8e, K-51 y api.md §8): cliente HTTP, issues `hk-tarea` → tareas del motor, sondeo con
ETag y la cuenta de escrituras del equipo. Solo biblioteca estándar (ADR-0005).

El token es el de `gh auth token` (respeta GH_CONFIG_DIR y GH_TOKEN). La base es inyectable: las pruebas usan un
GitHub falso (hkos/pruebas/github_falso.py). El contenido de los issues es dato: de aquí solo salen IDs, dueños,
dependencias, números, autores y horas; nunca texto que se inyecte en una sesión.
"""
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
ETIQUETA = "hk-tarea"
MARCADOR = re.compile(r"<!--\s*hk-tarea\s+id=(T\d{2,3})\s+hash=([0-9a-f]{12})(?:\s+plan=([0-9a-f]{7,40}))?\s*-->")
DEPENDE = re.compile(r"^Depende de:[ \t]*(.*)$", re.M)
DUENO_SIN = re.compile(r"^\*\*Dueño:\*\*[ \t]*([^@\s][^(\n]*?)[ \t]*\(sin GitHub\)", re.M)
BLOQUE = re.compile(r"^\*\*Bloque:\*\*[ \t]*(.*?)[ \t]*·", re.M)
ID = re.compile(r"\bT\d{2,3}\b")
# Eventos que deja una escritura. De una dependencia nativa, GitHub deja `blocked_by_added` en un issue y
# `blocking_added` en el otro (misma petición): se cuenta el primero (comprobado en el sandbox, M8e).
EVENTOS_ESCRITURA = {"assigned", "unassigned", "closed", "reopened", "labeled", "unlabeled", "renamed",
                     "blocked_by_added", "blocked_by_removed"}
MARGEN_S = 10                                    # GitHub fecha las etiquetas de una creación hasta ~2 s después
VENTANA = timedelta(hours=1)
TOPE_HORA = 60                                   # R-30


def fecha(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def token_de_gh():
    """El token de la sesión de gh de esta persona. None si gh no está o no tiene sesión."""
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    t = r.stdout.strip()
    return t if r.returncode == 0 and t else None


class Limitado(Exception):
    """GitHub limita (403/429 de límite) o no responde: reintentar no antes de `hasta` (segundos de época)."""

    def __init__(self, motivo, hasta):
        super().__init__(motivo)
        self.motivo, self.hasta = motivo, hasta


class ErrorGitHub(Exception):
    def __init__(self, codigo, datos):
        super().__init__(f"HTTP {codigo}: {str(datos)[:200]}")
        self.codigo, self.datos = codigo, datos


class Cliente:
    def __init__(self, repo, token, base=API, reloj=time.time):
        self.repo, self.token, self.base, self.reloj = repo, token, base.rstrip("/"), reloj
        self.escrituras = []                      # (hora, método, ruta) de lo que escribe este cliente

    def pedir(self, metodo, ruta, cuerpo=None, etag=None):
        """(código, datos, cabeceras). 304 da datos None. 403/429 de límite → Limitado; otros errores → ErrorGitHub."""
        url = ruta if ruta.startswith("http") else f"{self.base}{ruta}"
        h = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "hackathon-kit-os"}
        if etag:
            h["If-None-Match"] = etag
        datos = None
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode("utf-8")
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=datos, headers=h, method=metodo)
        if metodo != "GET":
            self.escrituras.append((self.reloj(), metodo, ruta))
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                texto = r.read()
                return r.status, (json.loads(texto) if texto else None), r.headers
        except urllib.error.HTTPError as ex:
            if ex.code == 304:
                return 304, None, ex.headers
            texto = ex.read()
            try:
                d = json.loads(texto) if texto else None
            except ValueError:
                d = texto[:200]
            limite = ex.code == 429 or (ex.code == 403 and (ex.headers.get("X-RateLimit-Remaining") == "0"
                                                            or "rate limit" in str(d).lower()))
            if limite:
                espera = ex.headers.get("Retry-After")
                if espera and espera.isdigit():
                    hasta = self.reloj() + int(espera)
                elif (ex.headers.get("X-RateLimit-Reset") or "").isdigit():
                    hasta = float(ex.headers["X-RateLimit-Reset"])
                else:
                    hasta = self.reloj() + 60
                raise Limitado(f"HTTP {ex.code}", hasta)
            raise ErrorGitHub(ex.code, d)
        except (urllib.error.URLError, OSError) as ex:
            raise Limitado(f"sin respuesta: {ex}", self.reloj() + 30)

    def lista(self, ruta, etag=None, paginas=10):
        """GET paginado (Link rel=next). (código, elementos, etag de la primera página). 304 → (304, None, etag)."""
        codigo, datos, h = self.pedir("GET", ruta, etag=etag)
        if codigo == 304:
            return 304, None, etag
        salida, nuevo, siguiente = list(datos or []), h.get("ETag"), _siguiente(h)
        while siguiente and paginas > 1:
            _, datos, h = self.pedir("GET", siguiente)
            salida += datos or []
            siguiente, paginas = _siguiente(h), paginas - 1
        return codigo, salida, nuevo


def _siguiente(h):
    m = re.search(r'<([^>]+)>;\s*rel="next"', h.get("Link") or "")
    return m.group(1) if m else None


# --- de issues a tareas (api.md §8; E59 y E60 de diseno.md §5.2) ---

def _disc(tipo, persona, detalle, ts, tarea=None):
    d = {"tipo": tipo, "detalle": detalle[:300], "ts": ts}
    if persona:
        d["persona"] = persona
    if tarea:
        d["tarea"] = tarea
    return d


def tareas_de_issues(issues, equipo):
    """Issues `hk-tarea` (JSON de la API) → (tareas, issues del motor, {número: ID}, discrepancias sin agrupar).

    Solo cuentan los issues con marcador cuyo autor está en el equipo (R-31); uno de fuera da `fuera_del_equipo` y no
    define nada. Un issue cerrado como `not_planned` es una tarea quitada del plan: no está en las tareas. Con dos
    issues del equipo para el mismo ID, manda el de número menor (`issue_duplicado`)."""
    tareas, motor, numeros, disc, vistas, quitadas = [], {}, {}, [], set(), set()
    for i in sorted(issues, key=lambda i: i["number"]):
        if "pull_request" in i:
            continue
        m = MARCADOR.search(i.get("body") or "")
        if not m:
            continue
        tid, autor = m.group(1), (i.get("user") or {}).get("login", "").lower()
        ts = i.get("created_at") or ""
        if autor not in equipo:
            disc.append(_disc("fuera_del_equipo", autor, f"issue #{i['number']} con el marcador de {tid} abierto por "
                              f"@{autor}, que no está en coordinacion.md: no define ninguna tarea", ts, tid))
            continue
        if tid in vistas or tid in quitadas:
            disc.append(_disc("issue_duplicado", autor, f"issue #{i['number']} repite {tid}: manda el de número menor", ts, tid))
            continue
        if i.get("state") == "closed" and i.get("state_reason") == "not_planned":
            quitadas.add(tid)
            numeros[i["number"]] = tid
            continue
        vistas.add(tid)
        cuerpo = i.get("body") or ""
        etiquetas = [l["name"] if isinstance(l, dict) else l for l in i.get("labels", [])]
        dueno = next((l[len(ETIQUETA) + 1:].lower() for l in etiquetas if l.startswith(ETIQUETA + ":")), None)
        if not dueno:
            s = DUENO_SIN.search(cuerpo)
            dueno = s.group(1).strip() if s else "?"
        d = DEPENDE.search(cuerpo)
        titulo = re.sub(rf"^{tid}\s*·\s*", "", i.get("title") or "")
        t = {"id": tid, "titulo": titulo, "dueno": dueno, "depende_de": ID.findall(d.group(1)) if d else []}
        b = BLOQUE.search(cuerpo)
        if b and b.group(1).strip() not in ("", "—"):
            t["bloque"] = b.group(1).strip()
        tareas.append(t)
        motor[tid] = {"creado_en": ts, "numero": i["number"], "acciones": []}
        numeros[i["number"]] = tid
    tareas.sort(key=lambda t: int(t["id"][1:]))
    return tareas, motor, numeros, disc


def acciones_de_eventos(eventos, numeros):
    """Eventos de issue del repo → {ID: [acciones del motor]} (asignar, cerrar, reabrir), con su actor."""
    salida = {}
    for e in sorted(eventos, key=lambda e: (e.get("created_at", ""), e.get("id", 0))):
        tid = numeros.get((e.get("issue") or {}).get("number"))
        if not tid:
            continue
        por = ((e.get("actor") or {}).get("login") or "").lower()
        tipo = e.get("event")
        if tipo == "assigned":
            a = {"accion": "asignar", "por": por, "a": ((e.get("assignee") or {}).get("login") or "").lower()}
        elif tipo == "closed":
            a = {"accion": "cerrar", "por": por}
        elif tipo == "reopened":
            a = {"accion": "reabrir", "por": por}
        else:
            continue
        a["ts"] = e["created_at"]
        salida.setdefault(tid, []).append(a)
    return salida


def escrituras_del_equipo(issues, eventos, comentarios, equipo, ahora, compilador=()):
    """Escrituras a GitHub del equipo sobre issues `hk-tarea` en la hora anterior a `ahora` (R-30), contadas desde lo
    que GitHub muestra a todos, no desde cada clon. Una petición puede dejar varios eventos, y GitHub los fecha con
    hasta un par de segundos de diferencia (comprobado en el sandbox, M8e), así que se agrupa con un margen de
    MARGEN_S segundos:
    - una creación cuenta una, con las etiquetas que pone su autor en ese margen;
    - una edición de etiquetas o título (`labeled`, `unlabeled`, `renamed` del mismo actor e issue, dentro del margen)
      cuenta una;
    - cada asignación, cierre, reapertura o dependencia nativa cuenta una, y cada comentario, uno;
    - una edición del cuerpo no deja evento: si el `updated_at` de un issue cae en la ventana sin otra escritura de
      ese issue dentro del margen, cuenta una más.
    `compilador` añade lo que un cliente sepa y GitHub no muestre (hoy, nada)."""
    desde = ahora - VENTANA
    nums = {i["number"] for i in issues if "pull_request" not in i}
    creadas, ediciones, total = {}, [], 0
    marcas = {}                                  # issue → horas de las escrituras contadas

    def dentro(actor, ts):
        return actor in equipo and ts and fecha(ts) > desde

    def marca(n, t):
        marcas.setdefault(n, []).append(t)
    for i in issues:
        autor = (i.get("user") or {}).get("login", "").lower()
        if i["number"] in nums and dentro(autor, i.get("created_at", "")):
            creadas[i["number"]] = (autor, fecha(i["created_at"]))
            total += 1
            marca(i["number"], fecha(i["created_at"]))
    for e in sorted(eventos, key=lambda e: e.get("created_at", "")):
        n, tipo = (e.get("issue") or {}).get("number"), e.get("event")
        actor, ts = ((e.get("actor") or {}).get("login") or "").lower(), e.get("created_at", "")
        if n not in nums or tipo not in EVENTOS_ESCRITURA or not dentro(actor, ts):
            continue
        t = fecha(ts)
        if tipo in ("labeled", "unlabeled", "renamed"):
            c = creadas.get(n)
            if c and c[0] == actor and 0 <= (t - c[1]).total_seconds() <= MARGEN_S:
                continue
            if any(a == actor and m == n and abs((t - x).total_seconds()) <= MARGEN_S for a, m, x in ediciones):
                continue
            ediciones.append((actor, n, t))
        total += 1
        marca(n, t)
    for c in comentarios:
        n, autor = _numero_de_url(c.get("issue_url", "")), ((c.get("user") or {}).get("login") or "").lower()
        if n in nums and dentro(autor, c.get("created_at", "")):
            total += 1
            marca(n, fecha(c["created_at"]))
    for i in issues:
        u = i.get("updated_at", "")
        if i["number"] in nums and u and fecha(u) > desde:
            t = fecha(u)
            if not any(abs((t - x).total_seconds()) <= MARGEN_S for x in marcas.get(i["number"], [])):
                total += 1
    return total + sum(1 for t in compilador if t > desde.timestamp())


def _numero_de_url(url):
    m = re.search(r"/issues/(\d+)$", url or "")
    return int(m.group(1)) if m else None


class Sondeo:
    """Sondeo del relay (api.md §8): tres consultas con If-None-Match cada 30 s y, si hace falta, las dependencias
    nativas de algún issue. No escribe nada. `resultado()` da lo que necesita modelo.calcular()."""

    def __init__(self, cliente, equipo, reloj=time.time):
        self.c, self.equipo, self.reloj = cliente, set(equipo), reloj
        self.etags, self.issues, self.eventos, self.comentarios = {}, [], {}, {}
        self.deps = {}                           # número → (updated_at, [IDs nativos])
        self.estado, self.ultimo_ok, self.hasta = "sin respuesta", None, 0
        self.respuestas = {"200": 0, "304": 0}

    def _get(self, clave, ruta, paginas=10):
        codigo, datos, etag = self.c.lista(ruta, self.etags.get(clave), paginas)
        self.respuestas[str(codigo) if codigo == 304 else "200"] += 1
        if codigo != 304:
            self.etags[clave] = etag
        return datos

    def sondear(self):
        """Una vuelta. Devuelve True si algo cambió. Con GitHub limitando, no pregunta hasta que pase la espera."""
        if self.reloj() < self.hasta:
            return False
        r = f"/repos/{self.c.repo}"
        try:
            cambio = False
            d = self._get("issues", f"{r}/issues?labels={ETIQUETA}&state=all&per_page=100")
            if d is not None:
                self.issues, cambio = d, True
            # Eventos de todo el repo (también del buzón): una página con ETag; si todos son nuevos, se sigue.
            d = self._get("eventos", f"{r}/issues/events?per_page=100", paginas=1 if self.eventos else 10)
            if d is not None:
                nuevos = [e for e in d if e["id"] not in self.eventos]
                if self.eventos and len(nuevos) == len(d) and d:
                    _, mas, _ = self.c.lista(f"{r}/issues/events?per_page=100&page=2", None, 9)
                    nuevos += [e for e in mas if e["id"] not in self.eventos]
                for e in nuevos:
                    self.eventos[e["id"]] = e
                cambio |= bool(nuevos)
            d = self._get("comentarios", f"{r}/issues/comments?sort=created&direction=desc&per_page=100", paginas=1)
            if d is not None:
                for c in d:
                    self.comentarios[c["id"]] = c
                cambio = True
            cambio |= self._dependencias()
            self.estado, self.ultimo_ok = "ok", self.reloj()
            return cambio
        except Limitado as ex:
            self.estado, self.hasta = ("limitado" if "HTTP" in ex.motivo else "sin respuesta"), ex.hasta
            return False
        except ErrorGitHub:
            self.estado, self.hasta = "sin respuesta", self.reloj() + 30
            return False

    def _dependencias(self):
        """Las nativas de un issue, solo si su total_blocked_by no cuadra con «Depende de:» o si cambió su updated_at."""
        cambio = False
        for i in self.issues:
            if "pull_request" in i or not MARCADOR.search(i.get("body") or ""):
                continue
            d = DEPENDE.search(i.get("body") or "")
            del_cuerpo = ID.findall(d.group(1)) if d else []
            total = (i.get("issue_dependencies_summary") or {}).get("total_blocked_by")
            previo = self.deps.get(i["number"])
            if previo and previo[0] == i.get("updated_at") and total == len(previo[1]):
                continue
            if not previo and total == len(del_cuerpo) and not total:
                self.deps[i["number"]] = (i.get("updated_at"), [])
                continue
            _, datos, _ = self.c.pedir("GET", f"/repos/{self.c.repo}/issues/{i['number']}/dependencies/blocked_by?per_page=100")
            nativos = []
            for b in datos or []:
                m = MARCADOR.search(b.get("body") or "")
                if m:
                    nativos.append(m.group(1))
            self.deps[i["number"]] = (i.get("updated_at"), nativos)
            cambio = True
        return cambio

    def resultado(self, ahora=None):
        """(tareas, issues del motor, discrepancias sin agrupar, escrituras del equipo en la última hora).

        Trabaja sobre copias: el hilo del sondeo puede estar añadiendo eventos a la vez (list() de un dict no suelta
        el GIL en CPython)."""
        issues, eventos, comentarios, deps = list(self.issues), list(self.eventos.values()), list(self.comentarios.values()), dict(self.deps)
        tareas, motor, numeros, disc = tareas_de_issues(issues, self.equipo)
        actualizado = {i["number"]: i.get("updated_at", "") for i in issues}
        for t in tareas:                          # manda la nativa (ADR-0001), con discrepancia
            n = motor[t["id"]]["numero"]
            if n in deps and sorted(deps[n][1]) != sorted(t["depende_de"]):
                disc.append(_disc("dependencias_distintas", None, f"{t['id']}: el cuerpo dice {', '.join(t['depende_de']) or 'nada'}"
                                  f" y GitHub {', '.join(deps[n][1]) or 'nada'}; manda GitHub", actualizado.get(n, ""), t["id"]))
                t["depende_de"] = list(deps[n][1])
        for tid, acciones in acciones_de_eventos(eventos, numeros).items():
            if tid in motor:
                motor[tid]["acciones"] = acciones
        for c in comentarios:
            n = _numero_de_url(c.get("issue_url", ""))
            autor = ((c.get("user") or {}).get("login") or "").lower()
            if n in numeros and autor not in self.equipo:
                disc.append(_disc("fuera_del_equipo", autor, f"comentario en el issue #{n} ({numeros[n]}) de @{autor}, que no "
                                  "está en coordinacion.md: no cambia ningún estado", c.get("created_at", ""), numeros[n]))
        ahora = ahora or datetime.fromtimestamp(self.reloj(), timezone.utc)
        escrituras = escrituras_del_equipo(issues, eventos, comentarios, self.equipo, ahora)
        return tareas, motor, disc, escrituras

    def a_disco(self):
        return {"issues": self.issues, "eventos": list(self.eventos.values()), "comentarios": list(self.comentarios.values()),
                "deps": {str(k): v for k, v in self.deps.items()}, "ultimo_ok": self.ultimo_ok}

    def de_disco(self, d):
        self.issues = d.get("issues", [])
        self.eventos = {e["id"]: e for e in d.get("eventos", [])}
        self.comentarios = {c["id"]: c for c in d.get("comentarios", [])}
        self.deps = {int(k): tuple(v) for k, v in d.get("deps", {}).items()}
        self.ultimo_ok = d.get("ultimo_ok")
