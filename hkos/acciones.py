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
import subprocess
import threading
import unicodedata
from datetime import datetime, timedelta

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
CONTROL = re.compile(r"[\u202a-\u202e\u2066-\u2069]")       # además de Cc: los de dirección del texto


def sanear(texto):
    """Una sola línea (api.md §4): saltos y tabuladores a un espacio, espacios repetidos a uno, sin caracteres de
    control y sin `#` ni `>` al principio (no abre un título ni una cita en criterios.md)."""
    t = "".join(" " if c in "\r\n\t\v\f\x85\u2028\u2029" else c for c in texto)
    t = CONTROL.sub("", "".join(c for c in t if unicodedata.category(c) != "Cc"))
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
    o sin BOM, o UTF-16) y los finales de línea del fichero: solo se añaden líneas, para que merge=union funcione."""
    utf16 = original.startswith((b"\xff\xfe", b"\xfe\xff"))
    cod, errores = ("utf-16", "replace") if utf16 else ("utf-8", "surrogateescape")
    previo = original.decode(cod, errores)
    salto = "\r\n" if "\r\n" in previo else "\n"
    cola = previo.rstrip("\r\n")
    if cola:
        cola += salto * (2 if en_blanco else 1)
    return (cola + texto.replace("\n", salto)).encode(cod, errores)


def gh_real(args):
    """(código, salida, error) del gh de la persona, sin preguntas."""
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                           env=dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1"))
    except (OSError, subprocess.SubprocessError) as ex:
        return 1, "", str(ex)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def primera_linea(texto, defecto):
    for l in (texto or "").splitlines():
        if l.strip():
            return l.strip()[:200]
    return defecto


class Rechazado(Exception):
    """El push no es un avance rápido: alguien subió antes."""


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
            r = subprocess.run(["git", *SIN_CREDENCIALES, "-C", self.ag.principal, *args], input=entrada,
                               capture_output=True, env=env, timeout=60)
        except (OSError, subprocess.SubprocessError) as ex:
            raise FalloGit(f"git {args[0]}: {ex}")
        return r.returncode, r.stdout, r.stderr.decode("utf-8", "replace")

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

    def _intento(self, nota, mensaje):
        """Un intento entero (pasos 1–6 de api.md §4). El sha subido; Rechazado si el push no es un avance rápido."""
        self._ok("fetch", "--quiet", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
        base = self._ok("rev-parse", "--verify", "-q", "refs/remotes/origin/main^{commit}")
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
            texto = out.decode("utf-8", "replace") + err
            if "[rejected]" in texto:
                raise Rechazado(primera_linea(err, "rechazado"))
            raise FalloGit("git push: " + primera_linea(err, primera_linea(out.decode("utf-8", "replace"), f"sale con {c}")))
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
            except Rechazado:
                try:
                    sha = self._intento(nota, mensaje)   # una vez, sobre el origin/main nuevo
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
        """[(ts, tarea)] de los reclamos de acciones.jsonl."""
        salida = []
        try:
            with open(self.registro, encoding="utf-8", errors="replace") as f:
                for l in f:
                    try:
                        d = json.loads(l)
                        if d.get("tipo") == "reclamo":
                            salida.append((fecha(d["ts"]), d.get("tarea")))
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
        if any(tarea == tid and ahora - ts < timedelta(seconds=VENTANA_S) for ts, tarea in reclamos):
            return 409, {"error": "ya la has reclamado hace un momento"}
        if sum(1 for ts, _ in reclamos if ahora - ts < timedelta(hours=1)) >= TOPE_HORA:
            return 429, {"error": f"{TOPE_HORA} reclamos por hora"}
        issue = None
        if conf(self.os_md, "github").lower() != "no" and isinstance(t.get("issue"), int):
            repo = self._repo()
            if not repo or "<" in repo:
                return 502, {"error": "no hay repo de tareas en os.md ni en coordinacion.md"}
            if self.login is None:
                c, out, err = self.gh(["api", "user", "--jq", ".login"])
                if c != 0 or not out:
                    return 502, {"error": "gh api user: " + primera_linea(err, f"sale con {c}")}
                self.login = out.strip().lower()
            if self.login != self.ag.persona:
                return 409, {"error": f"tu gh es @{self.login}, no @{self.ag.persona}"}
            c, _, err = self.gh(["issue", "edit", str(t["issue"]), "--repo", repo, "--add-assignee", "@me"])
            if c != 0:
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
        linea = json.dumps({"id": e["id"], "tipo": "reclamo", "tarea": tid, "ts": ts}, separators=(",", ":")) + "\n"
        fd = os.open(self.registro, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o600)
        try:
            os.write(fd, linea.encode("utf-8"))  # una sola escritura en modo append: el monitor nunca ve media línea
        finally:
            os.close(fd)
        self.ag.log(f"reclamar: {tid}" + (f" (issue #{issue})" if issue else " (sin GitHub: solo el evento)"))
        return 200, {"ok": True, "issue": issue}
