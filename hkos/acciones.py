"""Las dos acciones de la web de trabajo (M9a, K-95; api.md §4, ADR-0010): Anotar y Reclamar. Las llama el demonio
(agente.py) desde `POST /v1/anotar` y `POST /v1/reclamar`, ya pasadas las comprobaciones de seguridad (Host, Origin,
token, JSON, tamaño). Cada una devuelve (código HTTP, cuerpo JSON). Sin modelo y solo con la biblioteca estándar.

- Anotar añade la nota a `.hackathon/criterios.md` de origin/main con un índice temporal (`nota.index`), commit-tree y
  push, sin tocar la copia ni el índice de la persona. Si el push se rechaza, repite una vez sobre el origin/main nuevo
  (si aún no se ha movido, espera un poco a que el otro push acabe). Un push sin informe que sí entró da 200, y
  repetir una nota que ya está en origin/main (misma persona, mismo texto, hace un momento) no la duplica. Cada nota
  que entra deja una línea `nota` en `acciones.jsonl`: con 30 en la última hora, 429 (decisión 12A del PR #13).
- Las dos esperan a otra acción en curso 5 s como mucho; después, 503 «ocupado» (decisión 13B del PR #13).
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
import time
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
TOPE_NOTAS_HORA = 30             # notas de Anotar por persona y hora (decisión 12A del PR #13)
NOTA_SUBIDA = "nota"             # línea de acciones.jsonl de cada nota que entra en main: sin id, el monitor no la lee
VENTANA_S = 600                  # lo que el monitor entrega (10 min): un reclamo repetido dentro, 409
ETIQUETA = {"en_curso": "en curso", "en_revision": "en revisión", "no_cerrada": "no cerrada"}
MARGEN_RELOJ_S = 300             # un reclamo o una nota con la hora en el futuro más allá de esto (reloj atrasado
                                 # después) no cuenta
PLAZO_GIT, PLAZO_GH = 60, 30     # segundos; pasado el plazo se mata el árbol de procesos entero
ESPERAS_BASE, ESPERA_BASE_S = 3, 1   # push rechazado y origin/main sin moverse: otro push puede tener main.lock aún
# Un push sin informe: cuánto se sigue mirando si entró (el remoto puede actualizar main después: un pre-receive lento
# ya tiene el pack y sigue aunque el cliente muera) y cada cuánto (issue #27).
SUBIO_S, SUBIO_ESPERA_S = 10, 1.5
REPETIDA_S = 600                 # la misma nota de la misma persona en origin/main hace menos de esto: no se repite
CERROJO_S = 5                    # ninguna acción espera más que esto a otra en curso (un Anotar colgado): 503
GH = ["gh"]
FALLIDO = "reclamo_fallido"      # línea de acciones.jsonl de un `gh issue edit` que falló: sin id, el monitor no la lee
# Si es True, solo cuenta para el tope un `gh issue edit` que GitHub rechazó (`GraphQL: …` o `HTTP 4xx`); un plazo
# vencido, un 5xx o un error de red no (con GitHub caído, diez clics no dejan a nadie una hora en 429). Falso hasta que
# lo decidan los contratos (api.md §4, R-30): la salida de gh no es una interfaz estable, y GitHub también da por GraphQL
# fallos suyos («Something went wrong while executing your query»). Formatos: HTTPError y GraphQLError de go-gh.
FALLIDO_SOLO_RECHAZO = False
RECHAZO_GH = re.compile(r"(?:^|: )(?:GraphQL: |HTTP 4[0-9]{2}\b)", re.M)
REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$")
# Además de Cc, Cf (formato: dirección, BOM, anchura cero, etiquetas U+E00xx…) salvo el ZWJ de los emojis y el ZWNJ
# (en persa o hindi cambia cómo se escribe la palabra; decisión 16B del PR #13), y Cs (un surrogate suelto de
# `json.loads` se codificaría como bytes crudos: `\udcc2\udcbb` llegaría a main como «»»). Más los invisibles que no
# son Cf: el CGJ, los rellenos de hangul y las etiquetas sin asignar.
QUITAR = {"Cc", "Cf", "Cs"}
QUEDAN = "\u200c\u200d"          # ZWNJ y ZWJ
INVISIBLES = re.compile("[\u034f\u115f\u1160\u3164\U000e0000-\U000e007f]")
# Las comillas de las vistas (constitución V: una nota no puede cerrar las suyas en estado-equipo.md), también escritas
# como entidad HTML.
COMILLAS = re.compile(r"[«»]|&(?:laquo|raquo|#0*171|#0*187|#x0*ab|#x0*bb);", re.I)
# El HTML: un `<!--` o una etiqueta esconderían en GitHub lo que viene detrás. CommonMark solo ve HTML (etiquetas,
# comentarios, declaraciones, `<?`) cuando a `<` le sigue una letra ASCII, `/`, `!` o `?`: ese `<` pasa a ser `‹`
# (U+2039, sin descomposición NFKC y distinto de «»), y el texto se queda entero (`a‹b y c>d`). Un autoenlace
# (`<https://…>`, sin espacios ni `<>` dentro) se deja: CommonMark lo mira antes que el HTML y no esconde nada.
HTML = re.compile(r"(<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*>)|<(?=[A-Za-z/!?])")


def sanear(texto):
    """Una sola línea (api.md §4): saltos y tabuladores a un espacio, espacios repetidos a uno, sin caracteres de
    control ni invisibles, sin «», sin HTML y sin `#` ni `>` al principio (no abre un título ni una cita)."""
    t = "".join(" " if c in "\r\n\t\v\f\x85\u2028\u2029" else c for c in texto)
    t = INVISIBLES.sub("", "".join(c for c in t if c in QUEDAN or unicodedata.category(c) not in QUITAR))
    previo = None
    while previo != t:                     # hasta que no quede nada: quitar «» de «<«!--» deja otro «<!--»
        previo, t = t, HTML.sub(lambda m: m.group(1) or "\u2039", COMILLAS.sub("", t))
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^[#>\s]+", "", t)


def reciente(ahora, ts, segundos):
    """`ts` es de hace menos de `segundos`. Uno con la hora en el futuro (el reloj iba adelantado y lo corrigió NTP)
    cuenta solo hasta MARGEN_RELOJ_S: si no, contaría siempre, porque `ahora - ts` negativo es menor que todo."""
    return -MARGEN_RELOJ_S <= (ahora - ts).total_seconds() < segundos


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


def codificacion(original):
    """(BOM, codificación, errores) de un fichero en bytes: UTF-8 (con o sin BOM) o UTF-16 LE o BE con su BOM."""
    for marca, utf16 in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")):
        if original.startswith(marca):
            return marca, utf16, "replace"
    return b"", "utf-8", "surrogateescape"


CABECERA = re.compile(r"## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.*)")


def ya_anotada(original, texto, cuando):
    """True si `original` (criterios.md en bytes) ya tiene `texto` (la nota de texto_nota, con «Anotado por») con una
    hora a menos de REPETIDA_S de `cuando`: lo mismo, de la misma persona, hace un momento. Es lo que pasa al repetir
    un Anotar que dio 502 aunque la nota sí entró (un push sin informe, la red cortada al comprobarlo; issue #27)."""
    bom, cod, errores = codificacion(original)
    lineas = original[len(bom):].decode(cod, errores).replace("\r\n", "\n").split("\n")
    nueva = texto.rstrip("\n").split("\n")
    m = CABECERA.fullmatch(nueva[0])
    buscado = [m.group(2), *nueva[1:]]
    for i, linea in enumerate(lineas):
        c = CABECERA.fullmatch(linea)
        if not c or [c.group(2), *lineas[i + 1:i + len(nueva)]] != buscado:
            continue
        hora = datetime.strptime(c.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=cuando.tzinfo)
        if abs((cuando.replace(second=0, microsecond=0) - hora).total_seconds()) < REPETIDA_S:
            return True
    return False


def anadir(original, texto, en_blanco=True):
    """`texto` al final de `original` (bytes), con una línea en blanco delante, respetando la codificación (UTF-8, con
    o sin BOM, o UTF-16 LE o BE con su BOM) y los finales de línea del fichero: solo se añaden líneas, para que
    merge=union funcione. `texto` va en estricto: de la nota nunca sale un byte que no sea UTF-8 (o UTF-16) válido."""
    bom, cod, errores = codificacion(original)
    previo = original[len(bom):].decode(cod, errores)
    salto = "\r\n" if "\r\n" in previo else "\n"
    cola = previo.rstrip("\r\n")
    if cola:
        cola += salto * (2 if en_blanco else 1)
    return bom + cola.encode(cod, errores) + texto.replace("\n", salto).encode(cod)


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _Basicos(ctypes.Structure):                      # JOBOBJECT_BASIC_LIMIT_INFORMATION
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _Limites(ctypes.Structure):                      # JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        _fields_ = [("BasicLimitInformation", _Basicos), ("IoInfo", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
    _k32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    _k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _k32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _ntdll = ctypes.WinDLL("ntdll")
    _ntdll.NtResumeProcess.restype = ctypes.c_long
    _ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
    CREATE_SUSPENDED, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, JobObjectExtendedLimitInformation = 0x4, 0x2000, 9


def crear_trabajo():
    """Un Job Object de Windows que mata a todos sus procesos al cerrarlo, o None. Lo que lance un proceso del trabajo
    entra en él, aunque su padre ya haya salido (los hijos de fork de MSYS: el `sh` de un helper, un ProxyCommand…),
    que es justo lo que `taskkill /T`, que sigue ParentProcessId, no veía (issue #18)."""
    trabajo = _k32.CreateJobObjectW(None, None)
    if not trabajo:
        return None
    limites = _Limites()
    limites.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not _k32.SetInformationJobObject(trabajo, JobObjectExtendedLimitInformation, ctypes.byref(limites),
                                        ctypes.sizeof(limites)):
        _k32.CloseHandle(trabajo)
        return None
    return trabajo


def matar_arbol(p, trabajo=None):
    """El proceso y todo lo que lanzó (git-remote-https, ssh, un helper…): en Windows, su Job Object (si no se pudo
    crear, taskkill /T); en Linux y macOS, su grupo de procesos (lo crea `ejecutar`)."""
    try:
        if trabajo:
            _k32.TerminateJobObject(trabajo, 1)
        elif os.name == "nt":
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
    a git-remote-https). Pasado el plazo, mata el árbol entero y lanza TimeoutExpired. En Windows, el proceso nace
    suspendido, entra en su Job Object y solo entonces arranca: ningún hijo nace fuera; al cerrar el trabajo, lo que
    quede vivo muere también."""
    trabajo = crear_trabajo() if os.name == "nt" else None
    try:
        with tempfile.TemporaryFile() as fin, tempfile.TemporaryFile() as fout, tempfile.TemporaryFile() as ferr:
            if entrada is not None:
                fin.write(entrada)
                fin.seek(0)
            p = subprocess.Popen(args, stdin=fin if entrada is not None else subprocess.DEVNULL, stdout=fout,
                                 stderr=ferr, env=env, start_new_session=os.name != "nt",
                                 creationflags=CREATE_SUSPENDED if trabajo else 0)
            try:
                if trabajo:
                    if not _k32.AssignProcessToJobObject(trabajo, int(p._handle)):
                        _k32.CloseHandle(trabajo)
                        trabajo = None                  # sin trabajo (no debería pasar desde Windows 8): taskkill /T
                    if _ntdll.NtResumeProcess(int(p._handle)) != 0:
                        raise OSError("no se pudo arrancar el proceso suspendido")
                codigo = p.wait(timeout=plazo)
            except BaseException:
                matar_arbol(p, trabajo)
                raise
            fout.seek(0)
            ferr.seek(0)
            return codigo, fout.read(), ferr.read()
    finally:
        if trabajo:
            _k32.CloseHandle(trabajo)


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
# lo ve el cliente; si los dos pushes llegan a la vez, el remoto da `[remote rejected] …`: `(failed to update ref)` en
# git 2.49 (el «cannot lock ref … is at X but expected Y» va solo por stderr), `(incorrect old value provided)` en 2.56,
# `(reference already exists)` en 2.56 si el otro tiene cogido main.lock, `(failed to lock)` en gits viejos o
# `(cannot lock ref …)`. Un hook que rechaza da `[remote rejected] (… hook declined)`: no es una carrera, aunque
# imprima «[rejected]» por stderr (que no se mira). Como los del remoto también salen con su disco lleno o un main.lock
# huérfano, el reintento comprueba que origin/main se movió de verdad.
CARRERA = re.compile(r"^\[rejected\]|^\[remote rejected\] \((?:failed to (?:update ref|lock)|cannot lock ref|"
                     r"incorrect old value|reference already exists)")


def rechazo(porcelain, ref="refs/heads/main"):
    """El resumen («[rejected] (fetch first)») de la línea «!» de `ref` en la salida de push --porcelain, o None."""
    for l in porcelain.splitlines():
        partes = l.split("\t")
        if len(partes) >= 3 and partes[0] == "!" and partes[1].endswith(":" + ref):
            return "\t".join(partes[2:]).strip()[:200]
    return None


class Rechazado(Exception):
    """El push no es un avance rápido: alguien subió antes. `base`: el origin/main sobre el que se hizo el commit."""

    def __init__(self, motivo, base, detalle):
        super().__init__(motivo)
        self.motivo, self.base, self.detalle = motivo, base, detalle


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
        if not self.cerrojo.acquire(timeout=CERROJO_S):   # un Anotar colgado: «ocupado», no esperar sin más (13B)
            return 503, {"error": "ocupado"}
        try:
            return self.anotar(cuerpo) if ruta == "/v1/anotar" else self.reclamar(cuerpo)
        finally:
            self.cerrojo.release()

    # --- Anotar ---
    def _git(self, *args, entrada=None, indice=False, plazo=None):
        env = dict(os.environ, **ENTORNO)
        if indice:
            env["GIT_INDEX_FILE"] = self.indice
        plazo = plazo or self.plazo
        try:
            c, out, err = ejecutar(["git", *SIN_CREDENCIALES, "-C", self.ag.principal, *args], entrada=entrada,
                                   env=env, plazo=plazo)
        except subprocess.TimeoutExpired:
            raise FalloGit(f"git {args[0]}: sin respuesta en {plazo} s")
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

    def _fetch(self, plazo=None):
        self._ok("fetch", "--quiet", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main", plazo=plazo)
        return self._ok("rev-parse", "--verify", "-q", "refs/remotes/origin/main^{commit}")

    def _base(self, antes):
        """El origin/main sobre el que hacer el commit. `antes`: el rechazo del intento anterior. Si origin/main no se
        ha movido desde él, puede que el otro push aún tenga main.lock (un hook reference-transaction, un fsync lento):
        espera ESPERA_BASE_S y vuelve a mirar, ESPERAS_BASE veces como mucho y sin pasar del plazo. Si sigue igual, no
        era una carrera (un main.lock huérfano, el disco del remoto lleno): FalloGit con el motivo del rechazo."""
        for vuelta in range(ESPERAS_BASE + 1):
            base = self._fetch()
            if not antes or base != antes.base:
                return base
            if vuelta == ESPERAS_BASE or time.monotonic() + ESPERA_BASE_S > self.limite:
                raise FalloGit(f"git push: {antes.detalle}")
            time.sleep(ESPERA_BASE_S)

    def _subio(self, sha, base, insistir=True):
        """Un push que falló (plazo vencido, red cortada, un post-receive lento): ¿entró el commit? Así un 502 nunca
        invita a repetir una nota que ya está en main (issue #18). Sin informe (`insistir`), mira varias veces durante
        SUBIO_S: el remoto puede actualizar main después del primer fetch (un pre-receive lento) y el fetch puede fallar
        por la red (issue #27). Deja de mirar si origin/main se ha movido a otra cosa sin el commit: ya no puede entrar."""
        fin = time.monotonic() + SUBIO_S
        while True:
            try:
                punta = self._fetch(plazo=max(1, min(self.plazo, int(fin - time.monotonic()))))
                if self._git("merge-base", "--is-ancestor", sha, "refs/remotes/origin/main")[0] == 0:
                    return True
                if punta != base:
                    return False
            except FalloGit as ex:
                self.ag.log(f"anotar: ¿entró el push? {ex}")
            if not insistir or time.monotonic() + SUBIO_ESPERA_S >= fin:
                return False
            time.sleep(SUBIO_ESPERA_S)

    def _intento(self, nota, cuando, mensaje, antes=None):
        """Un intento entero (pasos 1–6 de api.md §4). (sha subido, True); Rechazado si el push no es un avance rápido.
        Si la misma nota ya está en origin/main (un intento anterior que dio 502 pero entró), (origin/main, False), sin
        repetirla."""
        base = self._base(antes)
        try:
            os.remove(self.indice)
        except OSError:
            pass
        self._ok("read-tree", base, indice=True)
        original = self._fichero(CRITERIOS)
        if original is None:
            with open(PLANTILLA, "rb") as f:              # con LF, como manda .gitattributes, sea cual sea la copia
                original = f.read().replace(b"\r\n", b"\n")
        elif ya_anotada(original, nota, cuando):
            self.ag.log(f"anotar: la misma nota ya está en origin/main ({base[:12]}); no se repite")
            return base, False
        self._escribir(CRITERIOS, anadir(original, nota))
        atributos = self._fichero(".gitattributes") or b""
        lineas = atributos.decode("utf-8", "replace").splitlines()
        if not any(l.split() == UNION.split() for l in lineas):
            self._escribir(".gitattributes", anadir(atributos, UNION + "\n", en_blanco=False))
        arbol = self._ok("write-tree", indice=True)
        sha = self._ok("commit-tree", arbol, "-p", base, "-m", mensaje)
        if self.antes_del_push:
            self.antes_del_push()
        try:
            c, out, err = self._git("push", "--no-verify", "--porcelain", "origin", f"{sha}:refs/heads/main")
        except FalloGit:
            if self._subio(sha, base):
                return sha, True
            raise
        if c != 0:
            motivo = rechazo(out.decode("utf-8", "replace"))
            if motivo and CARRERA.search(motivo):
                raise Rechazado(motivo, base, primera_linea(err, motivo))
            if self._subio(sha, base, insistir=not motivo):    # con informe del remoto (un hook), basta con mirar una vez
                return sha, True
            raise FalloGit("git push: " + primera_linea(err, motivo or f"sale con {c}"))
        return sha, True

    def anotar(self, cuerpo):
        n, error = validar_nota(cuerpo)
        if error:
            return 400, {"error": error[1], "campo": error[0]}
        ahora = fecha(self.ag.ahora())
        if sum(1 for ts, _, _ in self._registro(NOTA_SUBIDA) if reciente(ahora, ts, 3600)) >= TOPE_NOTAS_HORA:
            return 429, {"error": f"{TOPE_NOTAS_HORA} notas por hora"}
        tz = self.ag.tz or datetime.now().astimezone().tzinfo
        cuando = ahora.astimezone(tz)
        nota = texto_nota(n, self.ag.persona, cuando)
        mensaje = f"Criterio: {PAPELES[n['papel']]} · {n['que_dijo'][:50]}"
        self.limite = time.monotonic() + self.plazo      # las esperas del reintento no pasan de aquí
        try:
            try:
                sha, subida = self._intento(nota, cuando, mensaje)
            except Rechazado as primero:
                try:
                    sha, subida = self._intento(nota, cuando, mensaje, primero)   # una vez, sobre el origin/main nuevo
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
        if subida:                                       # una nota que ya estaba no sube nada: no cuenta para el tope
            try:
                self._registrar({"tipo": NOTA_SUBIDA, "sha": sha, "ts": self.ag.ahora()})
            except OSError as ex:                        # la nota ya está en main: un 502 invitaría a repetirla
                self.ag.log(f"anotar: no se ha podido apuntar en acciones.jsonl: {ex}")
        self.ag.log(f"anotar: {sha[:12]} en origin/main")
        return 200, {"ok": True, "sha": sha}

    def _registro(self, *tipos):
        """[(ts, tarea, tipo)] de las líneas de acciones.jsonl con esos tipos: para Reclamar, los reclamos y los `gh
        issue edit` que fallaron (cuentan para el tope, R-30, pero no para la ventana: volver a probar no es repetir un
        reclamo); para Anotar, las notas que entraron en main."""
        salida = []
        try:
            with open(self.registro, encoding="utf-8", errors="replace") as f:
                for l in f:
                    try:
                        d = json.loads(l)
                        if d.get("tipo") in tipos:
                            salida.append((fecha(d["ts"]), d.get("tarea"), d["tipo"]))
                    except (ValueError, KeyError, TypeError, AttributeError):
                        continue
        except OSError:
            pass
        return salida

    # --- Reclamar ---
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
        reclamos = self._registro("reclamo", FALLIDO)
        if any(tarea == tid and tipo == "reclamo" and reciente(ahora, ts, VENTANA_S) for ts, tarea, tipo in reclamos):
            return 409, {"error": "ya la has reclamado hace un momento"}
        if sum(1 for ts, _, _ in reclamos if reciente(ahora, ts, 3600)) >= TOPE_HORA:
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
                if not FALLIDO_SOLO_RECHAZO or RECHAZO_GH.search(err or ""):
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
