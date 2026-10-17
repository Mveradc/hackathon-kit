"""Las dos acciones de la web de trabajo (M9a, K-95; api.md §4, ADR-0010): Anotar y Reclamar. Las llama el demonio
(agente.py) desde `POST /v1/anotar` y `POST /v1/reclamar`, ya pasadas las comprobaciones de seguridad (Host, Origin,
token, JSON, tamaño). Cada una devuelve (código HTTP, cuerpo JSON). Sin modelo y solo con la biblioteca estándar.

- Anotar añade la nota a `.hackathon/criterios.md` de origin/main con un índice temporal (`nota.index`), commit-tree y
  push, sin tocar la copia ni el índice de la persona. Si el push se rechaza, repite una vez sobre el origin/main nuevo.
- Reclamar asigna el issue con el gh de la persona (si hay GitHub), emite `reclamo` (fuente web) y deja una línea en
  `acciones.jsonl` para el monitor (escucha.sh), que abre un turno con un texto fijo del kit.
"""
import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import unicodedata
from datetime import datetime

from colisiones_merge import ENTORNO, SIN_CREDENCIALES
from estados import fecha
from red import conf

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTILLA = os.path.join(KIT, "skills", "hack-note", "templates", "criterios.md")
CRITERIOS = ".hackathon/criterios.md"
UNION = ".hackathon/criterios.md merge=union"
PAPELES = {"jurado": "jurado", "mentor": "mentor", "organizacion": "organización"}
FUERZAS = ("dato", "obligatorio", "se valora", "nos gustaría ver", "comentario suelto", "sin precisar")
CAMPOS = {"papel", "quien", "que_dijo", "literal", "fuerza", "donde"}
TAREA = re.compile(r"^T[0-9]{2,3}$")
LIBRES = ("lista", "pendiente")
TOPE_HORA = 10                   # reclamos por persona y hora (api.md §4)
VENTANA_S = 600                  # lo que el monitor entrega (10 min): un reclamo repetido dentro, 409
ETIQUETA = {"en_curso": "en curso", "en_revision": "en revisión", "no_cerrada": "no cerrada"}
MARGEN_RELOJ_S = 300             # un reclamo con la hora en el futuro más allá de esto (reloj atrasado después) no cuenta
PLAZO_GIT, PLAZO_GH = 60, 30     # segundos; pasado el plazo se mata el árbol de procesos entero
GH = ["gh"]
FALLIDO = "reclamo_fallido"      # línea de acciones.jsonl de un `gh issue edit` que falló: sin id, el monitor no la lee
REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$")
# Además de Cc: los invisibles de dirección (LRM, RLM, ALM, incrustaciones, aislamientos) y de formato (BOM, espacios
# de anchura cero, separadores invisibles, anotaciones interlineales).
CONTROL = re.compile(r"[\u061c\u200b\u200e\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\ufff9-\ufffb]")
# Las comillas de las vistas (constitución V: una nota no puede cerrar las suyas en estado-equipo.md), también escritas
# como entidad HTML, y el HTML: un `<!--` o una etiqueta esconderían en GitHub lo que viene detrás.
COMILLAS = re.compile(r"[«»]|&(?:laquo|raquo|#0*171|#0*187|#x0*ab|#x0*bb);", re.I)
ETIQUETA_HTML = re.compile(r"<[A-Za-z/!?][^<>]*>|<(?=[A-Za-z/!?])")


def sanear(texto):
    """Una sola línea (api.md §4): saltos y tabuladores a un espacio, espacios repetidos a uno, sin caracteres de
    control ni invisibles, sin «», sin HTML y sin `#` ni `>` al principio (no abre un título ni una cita)."""
    t = "".join(" " if c in "\r\n\t\v\f\x85\u2028\u2029" else c for c in texto)
    t = CONTROL.sub("", "".join(c for c in t if unicodedata.category(c) != "Cc"))
    previo = None
    while previo != t:                     # hasta que no quede nada: quitar «<b>» de «<<b>!--» deja otro «<!--»
        previo, t = t, ETIQUETA_HTML.sub("", COMILLAS.sub("", t))
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^[#>\s]+", "", t)


def validar_nota(cuerpo):
    """(nota saneada, None) o (None, (campo, error)). Solo los campos de la plantilla, con sus listas y longitudes."""
    if not isinstance(cuerpo, dict):
        return None, (None, "el cuerpo no es un objeto")
    for k in cuerpo:
        if k not in CAMPOS:
            return None, (k, "campo de más")
    if cuerpo.get("papel") not in PAPELES:
        return None, ("papel", "jurado, mentor u organizacion")
    if cuerpo.get("fuerza") not in FUERZAS:
        return None, ("fuerza", "fuera de la lista")
    if not isinstance(cuerpo.get("literal"), bool):
        return None, ("literal", "tiene que ser true o false")
    nota = {"papel": cuerpo["papel"], "fuerza": cuerpo["fuerza"], "literal": cuerpo["literal"]}
    for k, minimo, maximo in (("que_dijo", 1, 500), ("quien", 0, 80), ("donde", 0, 80)):
        v = cuerpo.get(k)
        if v is None and minimo == 0:
            v = ""
        if not isinstance(v, str):
            return None, (k, "tiene que ser texto")
        v = sanear(v)
        if not minimo <= len(v) <= maximo:
            return None, (k, f"de {minimo} a {maximo} caracteres" if minimo else f"{maximo} caracteres como mucho")
        nota[k] = v
    return nota, None


def texto_nota(n, persona, cuando):
    """La nota con el formato de la plantilla de /hack-note (api.md §4)."""
    dijo = f"«{n['que_dijo']}»" if n["literal"] else f"(paráfrasis) {n['que_dijo']}"
    return (f"## {cuando:%Y-%m-%d %H:%M} · {n['quien'] or '—'} ({PAPELES[n['papel']]})\n"
            f"- Dónde: {n['donde'] or '—'}\n"
            f"- Qué dijo: {dijo}\n"
            f"- Fuerza: {n['fuerza']}\n"
            f"- Afecta a: — (anotada desde la web; la revisa /hack-check)\n"
            f"- Anotado por: @{persona}\n")


def anadir(original, texto, en_blanco=True):
    """`texto` al final de `original` (bytes), con una línea en blanco delante, respetando la codificación (UTF-8, con
    o sin BOM, o UTF-16 LE o BE con su BOM) y los finales de línea del fichero: solo se añaden líneas, para que
    merge=union funcione."""
    bom, cod, errores = b"", "utf-8", "surrogateescape"
    for marca, utf16 in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")):
        if original.startswith(marca):
            bom, cod, errores = marca, utf16, "replace"
    previo = original[len(bom):].decode(cod, errores)
    salto = "\r\n" if "\r\n" in previo else "\n"
    cola = previo.rstrip("\r\n")
    if cola:
        cola += salto * (2 if en_blanco else 1)
    return bom + (cola + texto.replace("\n", salto)).encode(cod, errores)


def matar_arbol(p):
    """El proceso y todo lo que lanzó (git-remote-https, ssh, un helper…): taskkill /T en Windows; en Linux y macOS, su
    grupo de procesos (lo crea `ejecutar`)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        else:
            os.killpg(p.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        p.kill()
        p.wait(timeout=15)
    except (OSError, subprocess.SubprocessError):
        pass


def ejecutar(args, entrada=None, env=None, plazo=60):
    """(código, stdout, stderr) en bytes. La entrada y las salidas van por ficheros temporales y no por tuberías: así
    nada espera a que un nieto que siga vivo las cierre (en Windows, `run(timeout=…)` mataba git y se quedaba esperando
    a git-remote-https). Pasado el plazo, mata el árbol entero y lanza TimeoutExpired."""
    with tempfile.TemporaryFile() as fin, tempfile.TemporaryFile() as fout, tempfile.TemporaryFile() as ferr:
        if entrada is not None:
            fin.write(entrada)
            fin.seek(0)
        p = subprocess.Popen(args, stdin=fin if entrada is not None else subprocess.DEVNULL, stdout=fout, stderr=ferr,
                             env=env, start_new_session=os.name != "nt")
        try:
            codigo = p.wait(timeout=plazo)
        except BaseException:
            matar_arbol(p)
            raise
        fout.seek(0)
        ferr.seek(0)
        return codigo, fout.read(), ferr.read()


def gh_real(args):
    """(código, salida, error) del gh de la persona, sin preguntas."""
    try:
        c, out, err = ejecutar([*GH, *args], plazo=PLAZO_GH,
                               env=dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1"))
    except subprocess.TimeoutExpired:
        return 1, "", f"sin respuesta en {PLAZO_GH} s"
    except (OSError, subprocess.SubprocessError) as ex:
        return 1, "", str(ex)
    return c, out.decode("utf-8", "replace").strip(), err.decode("utf-8", "replace").strip()


def primera_linea(texto, defecto):
    for l in (texto or "").splitlines():
        if l.strip():
            return l.strip()[:200]
    return defecto


# El resumen de la línea «!» del push --porcelain cuando otro subió antes: `[rejected] (fetch first | non-fast-forward)`
# lo ve el cliente; si los dos pushes llegan a la vez, el remoto da `[remote rejected] (failed to update ref)` (el
# «cannot lock ref … is at X but expected Y» va solo por stderr), `(failed to lock)` en gits viejos, o `(cannot lock
# ref …)` / `(incorrect old value provided)`. Un hook que rechaza da `[remote rejected] (… hook declined)`: no es una
# carrera, aunque imprima «[rejected]» por stderr (que no se mira). Como «failed to update ref» también sale con el
# disco del remoto lleno, el reintento comprueba que origin/main se movió de verdad.
CARRERA = re.compile(r"^\[rejected\]|^\[remote rejected\] \((?:failed to (?:update ref|lock)|cannot lock ref|"
                     r"incorrect old value)")


def rechazo(porcelain, ref="refs/heads/main"):
    """El resumen («[rejected] (fetch first)») de la línea «!» de `ref` en la salida de push --porcelain, o None."""
    for l in porcelain.splitlines():
        partes = l.split("\t")
        if len(partes) >= 3 and partes[0] == "!" and partes[1].endswith(":" + ref):
            return "\t".join(partes[2:]).strip()[:200]
    return None


class Rechazado(Exception):
    """El push no es un avance rápido: alguien subió antes. `base`: el origin/main sobre el que se hizo el commit."""

    def __init__(self, motivo, base):
        super().__init__(motivo)
        self.motivo, self.base = motivo, base


class FalloGit(Exception):
    pass


class Acciones:
    def __init__(self, ag, gh=gh_real):
        self.ag, self.gh = ag, gh
        self.indice = os.path.join(ag.dir, "nota.index")
        self.registro = os.path.join(ag.dir, "acciones.jsonl")
        self.os_md = os.path.join(ag.principal, ".hackathon", "os.md")
        self.cerrojo = threading.Lock()          # una acción a la vez: nota.index y el tope son de todas
        self.login = None                        # `gh api user`, comprobado una vez
        self.antes_del_push = None               # para las pruebas: lo que pasa entre el commit y el push
        self.plazo = PLAZO_GIT

    def __call__(self, ruta, cuerpo):
        with self.cerrojo:
            if ruta == "/v1/anotar":
                return self.anotar(cuerpo)
            return self.reclamar(cuerpo)

    # --- Anotar ---
    def _git(self, *args, entrada=None, indice=False):
        env = dict(os.environ, **ENTORNO)
        if indice:
            env["GIT_INDEX_FILE"] = self.indice
        try:
            c, out, err = ejecutar(["git", *SIN_CREDENCIALES, "-C", self.ag.principal, *args], entrada=entrada,
                                   env=env, plazo=self.plazo)
        except subprocess.TimeoutExpired:
            raise FalloGit(f"git {args[0]}: sin respuesta en {self.plazo} s")
        except (OSError, subprocess.SubprocessError) as ex:
            raise FalloGit(f"git {args[0]}: {ex}")
        return c, out, err.decode("utf-8", "replace")

    def _ok(self, *args, **kw):
        c, out, err = self._git(*args, **kw)
        if c != 0:
            raise FalloGit(f"git {args[0]}: {primera_linea(err, f'sale con {c}')}")
        return out.decode("utf-8", "replace").strip()

    def _fichero(self, ruta):
        """El contenido de `ruta` en origin/main, o None si no está."""
        c, out, _ = self._git("cat-file", "blob", f"refs/remotes/origin/main:{ruta}")
        return out if c == 0 else None

    def _escribir(self, ruta, datos):
        sha = self._ok("hash-object", "-w", "--stdin", entrada=datos)
        self._ok("update-index", "--add", "--cacheinfo", f"100644,{sha},{ruta}", indice=True)

    def _intento(self, nota, mensaje, antes=None):
        """Un intento entero (pasos 1–6 de api.md §4). El sha subido; Rechazado si el push no es un avance rápido.
        `antes`: el rechazo del intento anterior; si origin/main no se ha movido desde él, no era una carrera."""
        self._ok("fetch", "--quiet", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
        base = self._ok("rev-parse", "--verify", "-q", "refs/remotes/origin/main^{commit}")
        if antes and base == antes.base:
            raise FalloGit(f"git push: {antes.motivo}")
        try:
            os.remove(self.indice)
        except OSError:
            pass
        self._ok("read-tree", base, indice=True)
        original = self._fichero(CRITERIOS)
        if original is None:
            with open(PLANTILLA, "rb") as f:
                original = f.read()
        self._escribir(CRITERIOS, anadir(original, nota))
        atributos = self._fichero(".gitattributes") or b""
        lineas = atributos.decode("utf-8", "replace").splitlines()
        if not any(l.split() == UNION.split() for l in lineas):
            self._escribir(".gitattributes", anadir(atributos, UNION + "\n", en_blanco=False))
        arbol = self._ok("write-tree", indice=True)
        sha = self._ok("commit-tree", arbol, "-p", base, "-m", mensaje)
        if self.antes_del_push:
            self.antes_del_push()
        c, out, err = self._git("push", "--no-verify", "--porcelain", "origin", f"{sha}:refs/heads/main")
        if c != 0:
            motivo = rechazo(out.decode("utf-8", "replace"))
            if motivo and CARRERA.search(motivo):
                raise Rechazado(motivo, base)
            raise FalloGit("git push: " + primera_linea(err, motivo or f"sale con {c}"))
        return sha

    def anotar(self, cuerpo):
        n, error = validar_nota(cuerpo)
        if error:
            return 400, {"error": error[1], "campo": error[0]}
        tz = self.ag.tz or datetime.now().astimezone().tzinfo
        nota = texto_nota(n, self.ag.persona, fecha(self.ag.ahora()).astimezone(tz))
        mensaje = f"Criterio: {PAPELES[n['papel']]} · {n['que_dijo'][:50]}"
        try:
            try:
                sha = self._intento(nota, mensaje)
            except Rechazado as primero:
                try:
                    sha = self._intento(nota, mensaje, primero)   # una vez, sobre el origin/main nuevo
                except Rechazado as ex:
                    self.ag.log(f"anotar: push rechazado dos veces ({ex})")
                    return 409, {"error": "otra nota se subió a la vez, también al reintentar"}
        except FalloGit as ex:
            self.ag.log(f"anotar: {ex}")
            return 502, {"error": str(ex)}
        finally:
            try:
                os.remove(self.indice)
            except OSError:
                pass
        self.ag.log(f"anotar: {sha[:12]} en origin/main")
        return 200, {"ok": True, "sha": sha}

    # --- Reclamar ---
    def _reclamos(self):
        """[(ts, tarea, tipo)] de acciones.jsonl: los reclamos y los `gh issue edit` que fallaron (cuentan para el
        tope, R-30, pero no para la ventana: volver a probar no es repetir un reclamo)."""
        salida = []
        try:
            with open(self.registro, encoding="utf-8", errors="replace") as f:
                for l in f:
                    try:
                        d = json.loads(l)
                        if d.get("tipo") in ("reclamo", FALLIDO):
                            salida.append((fecha(d["ts"]), d.get("tarea"), d["tipo"]))
                    except (ValueError, KeyError, TypeError, AttributeError):
                        continue
        except OSError:
            pass
        return salida

    def _repo(self):
        return conf(self.os_md, "repo_tareas") or conf(os.path.join(self.ag.principal, ".hackathon", "coordinacion.md"),
                                                      "repo")

    def reclamar(self, cuerpo):
        if not isinstance(cuerpo, dict) or set(cuerpo) != {"tarea"}:
            return 400, {"error": "solo {\"tarea\": \"Txx\"}", "campo": "tarea"}
        tid = cuerpo["tarea"]
        if not isinstance(tid, str) or not TAREA.match(tid):
            return 400, {"error": "una tarea es T y 2 o 3 cifras", "campo": "tarea"}
        with self.ag.lock:
            estado = self.ag.estado
        if estado is None:
            return 503, {"error": "sin estado"}
        t = next((x for x in estado.get("tareas", []) if x.get("id") == tid), None)
        if t is None:
            return 404, {"error": f"{tid} no existe", "campo": "tarea"}
        dueno = (t.get("dueno") or "").lstrip("@").lower()
        if dueno and dueno != self.ag.persona:
            return 409, {"error": f"es de @{dueno} según el plan"}
        valor = (t.get("estado") or {}).get("valor")
        if valor not in LIBRES or t.get("declarado"):
            return 409, {"error": f"está {ETIQUETA.get(valor, valor or 'sin estado')}" if valor not in LIBRES
                         else "ya está declarada"}
        ahora = fecha(self.ag.ahora())
        reclamos = self._reclamos()

        def dentro(ts, segundos):
            """Hace menos de `segundos`. Uno con la hora en el futuro (el reloj iba adelantado y lo corrigió NTP) cuenta
            solo hasta MARGEN_RELOJ_S: si no, contaría siempre, porque `ahora - ts` negativo es menor que todo."""
            return -MARGEN_RELOJ_S <= (ahora - ts).total_seconds() < segundos
        if any(tarea == tid and tipo == "reclamo" and dentro(ts, VENTANA_S) for ts, tarea, tipo in reclamos):
            return 409, {"error": "ya la has reclamado hace un momento"}
        if sum(1 for ts, _, _ in reclamos if dentro(ts, 3600)) >= TOPE_HORA:
            return 429, {"error": f"{TOPE_HORA} reclamos por hora"}
        issue = None
        if conf(self.os_md, "github").lower() != "no" and isinstance(t.get("issue"), int):
            repo = self._repo()
            if not repo or "<" in repo:
                return 502, {"error": "no hay repo de tareas en os.md ni en coordinacion.md"}
            if not REPO.match(repo) or repo.split("/")[1] in (".", ".."):
                return 502, {"error": "el repo de tareas no tiene la forma dueño/repo"}
            if self.login is None:
                c, out, err = self.gh(["api", "user"])
                try:
                    login = json.loads(out)["login"] if c == 0 else None
                except (ValueError, TypeError, KeyError):
                    login = None
                if not isinstance(login, str) or not login:
                    return 502, {"error": "gh api user: " + primera_linea(err, f"sale con {c}" if c else "sin login")}
                self.login = login.strip().lower()
            if self.login != self.ag.persona:
                return 409, {"error": f"tu gh es @{self.login}, no @{self.ag.persona}"}
            c, _, err = self.gh(["issue", "edit", str(t["issue"]), "--repo", repo, "--add-assignee", "@me"])
            if c != 0:
                self._registrar({"tipo": FALLIDO, "tarea": tid, "ts": self.ag.ahora()})
                return 502, {"error": "gh issue edit: " + primera_linea(err, f"sale con {c}")}
            issue = t["issue"]
        ts = self.ag.ahora()
        e = {"v": 1, "id": f"web-{self.ag.persona}-reclamo-{tid}-{int(self.ag.reloj() * 1000)}", "ts": ts,
             "actor": {"persona": self.ag.persona, "papel": "humano"}, "tipo": "reclamo", "fuente": "web", "tarea": tid}
        with self.ag.lock:
            if self.ag.esquema.valido(e):
                self.ag.cola.append(e)
            else:
                self.ag.invalidos += 1
        self._registrar({"id": e["id"], "tipo": "reclamo", "tarea": tid, "ts": ts})
        self.ag.log(f"reclamar: {tid}" + (f" (issue #{issue})" if issue else " (sin GitHub: solo el evento)"))
        return 200, {"ok": True, "issue": issue}

    def _registrar(self, d):
        linea = json.dumps(d, separators=(",", ":")) + "\n"
        fd = os.open(self.registro, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o600)
        try:
            os.write(fd, linea.encode("utf-8"))  # una sola escritura en modo append: el monitor nunca ve media línea
        finally:
            os.close(fd)
