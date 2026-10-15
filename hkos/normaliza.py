"""Normalizador del Hackathon OS (M8c, K-34): forma cruda de los hooks (api.md §1) → eventos normalizados (§2).

Lo que necesita del mundo (git, transcripts) se lo da un Contexto, para probarlo sin repos reales; el demonio de
M8d usará el contexto por defecto, que llama a git. Lleva estado entre líneas: la tarea de cada worker (por su
agent_id) y la de cada fusión (por su sha).
El id de cada evento es <session_id>-<nº de línea del JSONL>; si una línea da varios (un comando con varias
operaciones git), los siguientes llevan «.2», «.3»…
"""
import json
import os
import re
import subprocess

EDICION = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
PAPELES = {"orquestador", "worker", "revisor"}
PERSONA = re.compile(r"^[a-z0-9-]+$")
# ID: y Base: al principio de una línea del prompt (en el transcript, también justo tras las comillas del texto).
ID_TAREA = re.compile(r'(?:^|[\n"])[*\s]*ID:[*\s]*(T\d{2,3})(?!\d)')
BASE = re.compile(r'(?:^|[\n"])[*\s]*Base:[*\s]*`?([0-9a-f]{7,40})(?![0-9a-f])')
SHA = re.compile(r"^[0-9a-f]{7,40}$")
# Operaciones git del orquestador en el campo `git` (api.md §2), en el orden en que aparecen en el comando.
GIT = re.compile(r"""(?:^|[^\w-])git(?:\s+-C\s+(?:"[^"]*"|'[^']*'|\S+))?\s+(?:
    update-ref\s+-d\s+refs/hackathon/fusion/(?P<borra>T\d{2,3})(?!\d)
  | update-ref\s+refs/hackathon/fusion/(?P<crea>T\d{2,3})(?!\d)(?:\s+(?P<crea_sha>[0-9a-f]{7,40})(?![0-9a-f]))?
  | merge\s+--ff-only\s+(?P<ff>[0-9a-f]{7,40})(?![0-9a-f])
  | (?P<push>push)(?![\w-])(?!.*--dry-run)
)""", re.X)


def _barras(ruta):
    return ruta.replace("\\", "/").rstrip("/")


def relativa(ruta, raiz):
    """Ruta absoluta → relativa a `raiz`, con «/» (sin distinguir mayúsculas, como Windows)."""
    r, b = _barras(ruta), _barras(raiz)
    if r.lower() == b.lower():
        return ""
    if r.lower().startswith(b.lower() + "/"):
        return r[len(b) + 1:]
    return r


class Contexto:
    """Lo que el normalizador pregunta fuera. Por defecto, a git y al disco (el demonio)."""

    def __init__(self, persona="", papeles=None, raices=None, contiene=None, ref=None, primera_linea=None):
        self.persona = persona                     # si la línea no la trae (api.md §1: la resuelve el demonio)
        self.papeles = papeles or {}               # agent_type → papel, además de hackathon-kit:<papel>
        self._raices, self._contiene, self._ref, self._primera = raices, contiene, ref, primera_linea

    def _git(self, cwd, *args):
        try:
            r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    def raices(self, cwd):
        """(raíz del árbol de cwd, copia principal del clon)."""
        if self._raices:
            return self._raices(cwd)
        top = self._git(cwd, "rev-parse", "--show-toplevel")
        comun = self._git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if top and comun and _barras(comun).endswith("/.git"):
            return top, os.path.dirname(_barras(comun))
        # Sin git (el worktree de un worker ya borrado al normalizar): los worktrees de subagente viven en
        # <copia principal>/.claude/worktrees/<nombre>.
        c = _barras(cwd)
        i = c.lower().find("/.claude/worktrees/")
        if i >= 0:
            nombre = c[i + len("/.claude/worktrees/"):].split("/")[0]
            return f"{c[:i]}/.claude/worktrees/{nombre}", c[:i]
        return top or c, top or c

    def contiene(self, cwd, sha):
        """¿La rama de la copia principal contiene el sha? (fusion.aprobada solo si git lo confirma)."""
        if self._contiene:
            return self._contiene(cwd, sha)
        return self._git(cwd, "merge-base", "--is-ancestor", sha, "HEAD") is not None

    def ref(self, cwd, nombre):
        if self._ref:
            return self._ref(cwd, nombre)
        return self._git(cwd, "rev-parse", "-q", "--verify", nombre)

    def primera_linea(self, ruta):
        if self._primera:
            return self._primera(ruta)
        try:
            with open(ruta, encoding="utf-8", errors="replace") as f:
                return f.readline()
        except OSError:
            return None


class Normalizador:
    def __init__(self, ctx=None):
        self.ctx = ctx or Contexto()
        self.tarea_de_agente = {}     # agent_id → tarea (de su worker.inicio)
        self.tarea_de_fusion = {}     # sha → tarea (de fusion.creada)
        self.fusion_de_tarea = {}     # tarea → sha de la fusión en revisión
        self.aprobadas = set()        # tareas con fusion.aprobada desde su última fusion.creada
        self.lineas_corruptas = 0     # líneas que no son JSON válido (normalizar_fichero)

    def papel(self, agent_type):
        if not agent_type:
            return "principal"
        if agent_type in self.ctx.papeles:
            return self.ctx.papeles[agent_type]
        nombre = agent_type.split(":")[-1]
        return nombre if nombre in PAPELES else "principal"

    def eventos(self, crudo, n):
        """Eventos normalizados de una línea cruda (dict) que es la n-ésima (desde 1) de su JSONL."""
        sesion = crudo.get("session_id", "")
        tipo = crudo.get("tipo")
        papel = self.papel(crudo.get("agent_type"))
        cwd = crudo.get("cwd", "")
        top, principal = self.ctx.raices(cwd)
        persona = (crudo.get("persona") or self.ctx.persona).lower()
        actor = {"persona": persona if PERSONA.match(persona) else "desconocida", "sesion": sesion, "papel": papel,
                 "worktree": relativa(top, principal)}
        agente = crudo.get("agent_id")
        if agente:
            actor["agente"] = agente
        salida = []

        def ev(t, fuente="hook", tarea=None, rutas=None, datos=None):
            e = {"v": 1, "id": f"{sesion}-{n}" + (f".{len(salida) + 1}" if salida else ""), "ts": crudo["ts"],
                 "actor": dict(actor), "tipo": t, "fuente": fuente}
            tarea = tarea or (self.tarea_de_agente.get(agente) if agente else None)
            if tarea:
                e["tarea"] = tarea
            if rutas is not None:
                e["rutas"] = rutas
            if datos:
                e["datos"] = datos
            salida.append(e)

        if tipo == "SessionStart" and not agente:
            ev("sesion.inicio", datos={"source": crudo["source"]} if crudo.get("source") else None)
        elif tipo == "SessionEnd" and not agente:
            ev("sesion.fin")
        elif tipo == "SubagentStart" and papel == "worker":
            tarea, base = self._encargo_del_worker(crudo)
            if tarea:
                self.tarea_de_agente[agente] = tarea
            ev("worker.inicio", tarea=tarea, datos={"base": base} if base else None)
        elif tipo == "SubagentStop" and papel == "worker":
            ev("worker.fin")
        elif tipo == "SubagentStop" and papel == "revisor" and crudo.get("veredicto"):
            sha = crudo.get("fusion")
            datos = {"veredicto": crudo["veredicto"]}
            if sha:
                datos["sha"] = sha
            ev("revision.veredicto", tarea=self.tarea_de_fusion.get(sha), datos=datos)
        elif tipo == "PreToolUse" and crudo.get("tool_name") == "Agent" and papel == "orquestador" \
                and self.papel(crudo.get("subagent_type")) == "worker":
            ev("encargo.lanzado", tarea=crudo.get("id"), datos={"base": crudo["base"]} if crudo.get("base") else None)
        elif tipo == "PostToolUse" and crudo.get("tool_name") in EDICION and crudo.get("ruta"):
            ev("edicion", rutas=[relativa(crudo["ruta"], top)])
        elif tipo == "PostToolUse" and crudo.get("git"):
            self._git(crudo, papel, cwd, ev)
        elif tipo == "arbol":
            rutas = []
            for linea in crudo.get("porcelain", []):
                ruta = linea[3:].split(" -> ")[-1].strip('"')
                if ruta and ruta not in rutas:
                    rutas.append(ruta)
            for ruta in crudo.get("diff", []):
                if ruta not in rutas:
                    rutas.append(ruta)
            datos = {k: crudo[k] for k in ("base", "truncado") if crudo.get(k)}
            if isinstance(crudo.get("contratos"), list):          # M8g: bloques de docs/contratos.md tocados
                contratos = [str(c)[:120] for c in crudo["contratos"] if c][:5]
                if contratos:
                    datos["contratos"] = contratos
            ev("arbol", rutas=rutas, datos=datos)
        elif tipo == "compuerta":
            datos = {"motivos": [m[:300] for m in crudo.get("motivos", [])]}
            if crudo.get("tope"):
                datos["tope"] = True
            actor["papel"] = "worker"
            ev("compuerta.ok" if crudo.get("resultado") == "ok" else "compuerta.ko", fuente="compuerta", datos=datos)
        return salida

    def _encargo_del_worker(self, crudo):
        """ID: y Base: de la primera línea del transcript del worker (P3); nada más de él."""
        t, sesion, agente = crudo.get("transcript_path"), crudo.get("session_id"), crudo.get("agent_id")
        if not (t and sesion and agente):
            return None, None
        ruta = f"{os.path.dirname(_barras(t))}/{sesion}/subagents/agent-{agente}.jsonl"
        linea = self.ctx.primera_linea(ruta)
        if not linea:
            return None, None
        try:
            texto = json.dumps(json.loads(linea), ensure_ascii=False)
            texto = texto.replace("\\n", "\n")
        except ValueError:
            texto = linea
        m, b = ID_TAREA.search(texto), BASE.search(texto)
        return (m.group(1) if m else None), (b.group(1) if b else None)

    def _git(self, crudo, papel, cwd, ev):
        for m in GIT.finditer(crudo["git"]):
            if m.group("push"):
                ev("push")
            elif papel != "orquestador":
                continue
            elif m.group("crea"):
                tarea = m.group("crea")
                sha = m.group("crea_sha") or self.ctx.ref(cwd, f"refs/hackathon/fusion/{tarea}")
                if sha and SHA.match(sha):
                    self.tarea_de_fusion[sha] = tarea
                    self.fusion_de_tarea[tarea] = sha
                self.aprobadas.discard(tarea)
                ev("fusion.creada", tarea=tarea, datos={"sha": sha} if sha and SHA.match(sha) else None)
            elif m.group("ff"):
                sha = m.group("ff")
                tarea = self._tarea_de_sha(sha)
                if tarea and self.ctx.contiene(cwd, sha):
                    self.aprobadas.add(tarea)
                    ev("fusion.aprobada", fuente="git", tarea=tarea, datos={"sha": self.fusion_de_tarea.get(tarea, sha)})
            elif m.group("borra"):
                tarea = m.group("borra")
                if tarea not in self.aprobadas:
                    sha = self.fusion_de_tarea.get(tarea)
                    ev("fusion.descartada", tarea=tarea, datos={"sha": sha} if sha else None)
                self.aprobadas.discard(tarea)
                self.fusion_de_tarea.pop(tarea, None)

    def _tarea_de_sha(self, sha):
        """La tarea de una fusión por su sha, también si el comando lo abrevia."""
        for completo, tarea in self.tarea_de_fusion.items():
            if completo.startswith(sha) or sha.startswith(completo):
                return tarea
        return None


def normalizar_fichero(ruta, ctx=None, normalizador=None):
    """Todos los eventos de un JSONL crudo, en orden.

    El tope de 1.000 bytes por línea es medido, no garantizado (api.md §1): una línea que no es JSON válido (o no es
    un objeto, o no es UTF-8) se salta sin cortar la lectura, las demás conservan su número de línea real (el id) y
    se cuenta en `normalizador.lineas_corruptas` (en M8d, discrepancia «linea_corrupta»)."""
    nz = normalizador or Normalizador(ctx)
    salida = []
    with open(ruta, "rb") as f:
        for n, linea in enumerate(f, 1):
            try:
                crudo = json.loads(linea.decode("utf-8"))
                if not isinstance(crudo, dict):
                    raise ValueError("no es un objeto")
            except ValueError:
                nz.lineas_corruptas += 1
                continue
            salida += nz.eventos(crudo, n)
    return salida
