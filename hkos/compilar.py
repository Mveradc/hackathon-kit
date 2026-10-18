# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""hk-os compilar (M8e, K-50; api.md §8 y ADR-0001): lleva las tareas de .hackathon/plan.md a issues `hk-tarea` del
repo de la coordinación, de forma idempotente. Crea lo que falta, edita lo que cambió (por hash de la fila), cierra
como `not_planned` lo que se quitó del plan y ajusta las dependencias nativas. Sin cambios, no escribe nada.

Lo lanza cualquiera de la tabla de coordinacion.md, con el OS activo y el plan commiteado e igual al de origin/main.
La compilación inicial va a ≤ 1 escritura/s y está exenta del tope de R-30; una recompilación respeta el tope del
equipo (60/h), contado desde GitHub.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github  # noqa: E402
from red import conf, equipo, leer_texto  # noqa: E402

FILA = re.compile(r"^\|\s*(T\d{2,3})\s*\|(.*)\|\s*$")
# «- T05 espera a T03 y T04: …», «- **T21 espera a T36**: …», «- T16 espera a T06–T08: …» (formatos de /hack-plan).
ESPERA = re.compile(r"^\s*-\s*\**\s*(T\d{2,3})\s+espera\s+a\s+([^:*\n]+)", re.M)
RANGO = re.compile(r"T(\d{2,3})\s*[–-]\s*T(\d{2,3})")
PERSONA = re.compile(r"^###\s+(.+?)\s+·")
PIE = "_Generado por hk-os compilar desde .hackathon/plan.md: la definición se cambia en el plan, no aquí._"


class PlanMalo(Exception):
    pass


def leer_plan(texto, tabla):
    """plan.md → tareas [{id, titulo, nombre, dueno, bloque, hasta, comprobacion, depende_de}].

    tabla: [{persona, nombre}] de coordinacion.md. Una persona sin GitHub en la tabla da dueño = su nombre («C»).
    En las filas, las celdas vacías de Hasta y Bloque heredan las de la fila de arriba (formato de /hack-plan)."""
    usuarios = {p["nombre"].lower(): p["persona"] for p in tabla}
    tareas, vistas, nombre, en_personas = [], set(), None, False
    hasta = bloque = ""
    for linea in texto.splitlines():
        if linea.startswith("## "):
            en_personas = linea.strip().lower() == "## por persona"
            continue
        if not en_personas:
            continue
        m = PERSONA.match(linea)
        if m:
            nombre, hasta, bloque = m.group(1).strip(), "", ""
            continue
        m = FILA.match(linea)
        if not m:
            continue
        if not nombre:
            raise PlanMalo(f"la fila de {m.group(1)} no está bajo ninguna persona («### <Nombre> · …»)")
        celdas = [c.strip() for c in m.group(2).split("|")]
        if len(celdas) != 4:
            raise PlanMalo(f"{m.group(1)}: se esperan 5 columnas (ID, Hasta, Bloque, Tarea, Cómo se comprueba)")
        tid = m.group(1)
        if tid in vistas:
            raise PlanMalo(f"{tid} aparece dos veces en el plan")
        vistas.add(tid)
        hasta = celdas[0] or hasta
        bloque = celdas[1] or bloque
        tareas.append({"id": tid, "titulo": celdas[2], "nombre": nombre,
                       "dueno": usuarios.get(nombre.lower(), nombre), "bloque": bloque, "hasta": hasta,
                       "comprobacion": celdas[3], "depende_de": []})
    por_id = {t["id"]: t for t in tareas}
    for m in ESPERA.finditer(texto):
        if m.group(1) in por_id:
            texto, deps = m.group(2), []
            for ini, fin in RANGO.findall(texto):
                ancho = len(ini)
                deps += [f"T{n:0{ancho}d}" for n in range(int(ini), int(fin) + 1)]
            deps += re.findall(r"T\d{2,3}", RANGO.sub("", texto))
            for d in deps:
                if d not in por_id[m.group(1)]["depende_de"]:
                    por_id[m.group(1)]["depende_de"].append(d)
    if not tareas:
        raise PlanMalo("no hay ninguna fila con ID en «## Por persona»")
    return tareas


def huella(t):
    """Hash de la fila canónica (api.md §8): 12 hex."""
    canon = [t["id"], t["titulo"], t["dueno"], t["bloque"], t["hasta"], t["comprobacion"], sorted(t["depende_de"])]
    return hashlib.sha256(json.dumps(canon, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def con_github(t, tabla):
    return any(p["persona"] == t["dueno"] for p in tabla)


def titulo(t):
    return f"{t['id']} · {t['titulo']}"


def cuerpo(t, plan_sha, tabla):
    dueno = f"@{t['dueno']} ({t['nombre']})" if con_github(t, tabla) else f"{t['nombre']} (sin GitHub)"
    lineas = [f"<!-- hk-tarea id={t['id']} hash={huella(t)} plan={plan_sha} -->",
              f"**Dueño:** {dueno}",
              f"**Bloque:** {t['bloque'] or '—'} · **Hasta:** {t['hasta'] or '—'}",
              f"**Cómo se comprueba:** {t['comprobacion']}"]
    if t["depende_de"]:
        lineas.append(f"Depende de: {', '.join(t['depende_de'])}")
    lineas += ["", PIE]
    return "\n".join(lineas) + "\n"


def etiquetas(t, tabla):
    return [github.ETIQUETA] + ([f"{github.ETIQUETA}:{t['dueno']}"] if con_github(t, tabla) else [])


class Compilador:
    def __init__(self, cliente, tabla, plan_sha, registro=None, reloj=time.time, dormir=time.sleep, salida=print):
        self.c, self.tabla, self.plan_sha = cliente, tabla, plan_sha
        self.equipo = {p["persona"] for p in tabla}
        self.registro, self.reloj, self.dormir, self.salida = registro, reloj, dormir, salida
        self.escritas, self.pendientes = 0, 0
        self.inicial = False
        self.disponibles = None

    # --- escrituras con ritmo y tope ---
    def _escribe(self, metodo, ruta, cuerpo=None, que=""):
        if self.disponibles is not None and self.escritas >= self.disponibles:
            self.pendientes += 1
            return None
        if self.escritas:
            self.dormir(1.0)                     # ≤ 1 escritura/s (límite secundario de GitHub: 80/min)
        _, datos, _ = self.c.pedir(metodo, ruta, cuerpo)
        self.escritas += 1
        if self.registro:
            with open(self.registro, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": self.reloj(), "metodo": metodo, "que": que}) + "\n")
        return datos

    def compilar(self, tareas):
        r = f"/repos/{self.c.repo}"
        _, issues, _ = self.c.lista(f"{r}/issues?labels={github.ETIQUETA}&state=all&per_page=100", paginas=50)
        propios = {}                             # ID → issue del equipo (el de número menor)
        for i in sorted(issues, key=lambda i: i["number"]):
            m = github.MARCADOR.search(i.get("body") or "")
            if m and (i.get("user") or {}).get("login", "").lower() in self.equipo and m.group(1) not in propios:
                propios[m.group(1)] = i
        self.inicial = not propios
        if not self.inicial:                     # R-30: el tope es del equipo y se cuenta desde GitHub
            _, eventos, _ = self.c.lista(f"{r}/issues/events?per_page=100", paginas=3)
            _, comentarios, _ = self.c.lista(f"{r}/issues/comments?sort=created&direction=desc&per_page=100", paginas=1)
            # Las dependencias nativas dejan evento (blocked_by_added), así que todo sale de GitHub.
            usados = github.escrituras_del_equipo(issues, eventos, comentarios, self.equipo,
                                                  datetime.fromtimestamp(self.reloj(), timezone.utc))
            self.disponibles = max(0, github.TOPE_HORA - usados)
            self.salida(f"Escrituras del equipo en la última hora: {usados} de {github.TOPE_HORA}.")
        else:
            self.salida("Compilación inicial: exenta del tope de R-30, a ≤ 1 escritura/s.")
        resumen = {"creadas": [], "editadas": [], "reabiertas": [], "cerradas": [], "sin_cambios": [], "dependencias": 0}
        if self.inicial:
            self._etiquetas(tareas)
        por_id = {}
        for t in tareas:                         # 1) crear y editar
            i = propios.get(t["id"])
            if i is None:
                i = self._escribe("POST", f"{r}/issues", {"title": titulo(t), "body": cuerpo(t, self.plan_sha, self.tabla),
                                                          "labels": etiquetas(t, self.tabla)}, "crear")
                if i:
                    resumen["creadas"].append(t["id"])
            else:
                m = github.MARCADOR.search(i.get("body") or "")
                quitada = i.get("state") == "closed" and i.get("state_reason") == "not_planned"
                if m.group(2) != huella(t) or quitada:
                    cambio = {"title": titulo(t), "body": cuerpo(t, self.plan_sha, self.tabla), "labels": etiquetas(t, self.tabla)}
                    if quitada:
                        cambio["state"] = "open"
                    if self._escribe("PATCH", f"{r}/issues/{i['number']}", cambio, "editar") is not None:
                        resumen["reabiertas" if quitada else "editadas"].append(t["id"])
                else:
                    resumen["sin_cambios"].append(t["id"])
            if i:
                por_id[t["id"]] = i
        for t in tareas:                         # 2) dependencias nativas
            i = por_id.get(t["id"])
            if not i:
                continue
            quiero = {d for d in t["depende_de"] if d in por_id}
            total = (i.get("issue_dependencies_summary") or {}).get("total_blocked_by", 0)
            if not quiero and not total:
                continue
            _, actuales, _ = self.c.lista(f"{r}/issues/{i['number']}/dependencies/blocked_by?per_page=100")
            tengo = {}
            for b in actuales or []:
                m = github.MARCADOR.search(b.get("body") or "")
                if m:
                    tengo[m.group(1)] = b
            for d in sorted(quiero - set(tengo)):
                if self._escribe("POST", f"{r}/issues/{i['number']}/dependencies/blocked_by",
                                 {"issue_id": por_id[d]["id"]}, "dependencia") is not None:
                    resumen["dependencias"] += 1
            for d in sorted(set(tengo) - quiero):
                if self._escribe("DELETE", f"{r}/issues/{i['number']}/dependencies/blocked_by/{tengo[d]['id']}",
                                 que="dependencia") is not None:
                    resumen["dependencias"] += 1
        ids = {t["id"] for t in tareas}           # 3) quitadas del plan
        for tid, i in sorted(propios.items()):
            if tid in ids or i.get("state") == "closed":       # una tarea ya cerrada (hecha o quitada) se queda así
                continue
            if self.disponibles is not None and self.escritas + 2 > self.disponibles:
                self.pendientes += 2
                continue
            self._escribe("POST", f"{r}/issues/{i['number']}/comments",
                          {"body": f"Quitada del plan en {self.plan_sha} (`hk-os compilar`)."}, "comentar")
            self._escribe("PATCH", f"{r}/issues/{i['number']}", {"state": "closed", "state_reason": "not_planned"}, "cerrar")
            resumen["cerradas"].append(tid)
        resumen["escrituras"], resumen["pendientes"] = self.escritas, self.pendientes
        return resumen

    def _etiquetas(self, tareas):
        """En la compilación inicial, que existan las etiquetas (GitHub las crea solas al usarlas, pero sin color fijo)."""
        nombres = sorted({l for t in tareas for l in etiquetas(t, self.tabla)})
        for n in nombres:
            try:
                self.c.pedir("GET", f"/repos/{self.c.repo}/labels/{n.replace(':', '%3A')}")
            except github.ErrorGitHub as ex:
                if ex.codigo != 404:
                    raise
                self._escribe("POST", f"/repos/{self.c.repo}/labels", {"name": n, "color": "c5def5",
                              "description": "Tarea del plan (hackathon-kit, Hackathon OS)"}, "etiqueta")


def sin_github(os_md):
    """Modo sin GitHub (M8h, K-80; api.md §0): `github: no` en os.md."""
    return conf(os_md, "github").lower() in ("no", "false")


def tareas_de_plan(texto, tabla, ts):
    """Modo sin GitHub: plan.md → lo mismo que github.tareas_de_issues (tareas, issues del motor, números,
    discrepancias). Sin issues, no hay asignación ni cierre: `reclamada` y `cerrada` no salen, y lo que hace avanzar una
    tarea son sus señales (actividad, commits con su ID, push). `ts` es la hora del commit del plan; la fuente, `git`."""
    tareas, motor = [], {}
    for t in leer_plan(texto, tabla):
        x = {"id": t["id"], "titulo": t["titulo"], "dueno": t["dueno"], "depende_de": list(t["depende_de"])}
        if t["bloque"] and t["bloque"] != "—":
            x["bloque"] = t["bloque"]
        tareas.append(x)
        motor[t["id"]] = {"creado_en": ts, "acciones": [], "fuente": "git"}
    tareas.sort(key=lambda t: int(t["id"][1:]))
    return tareas, motor, {}, []


class SondeoPlan:
    """Fuente de tareas del relay en el modo sin GitHub (M8h, K-80; api.md §3): lee .hackathon/plan.md de origin/main
    del clon del relay (el fetch es el de las novedades, cada 60 s) con la misma interfaz que github.Sondeo. No escribe
    nada ni usa la red. Un plan mal formado no borra las tareas: se queda el último bueno y se avisa una vez."""
    fuente = "git"
    REF = "origin/main"

    def __init__(self, repo, tabla, git=None, aviso=None):
        self.repo, self.tabla = repo, tabla
        self.git = git or (lambda *a: _git(repo, *a))
        self.aviso = aviso or (lambda s: None)
        self.blob, self.malo, self.texto, self.ts = None, None, None, None
        self.estado, self.ultimo_ok = "no", None

    def sondear(self):
        """True si cambió el plan de origin/main."""
        blob = self.git("rev-parse", f"{self.REF}:.hackathon/plan.md")
        if not blob or blob == self.blob or blob == self.malo:
            return False
        texto = self.git("show", f"{self.REF}:.hackathon/plan.md")
        ct = self.git("log", "-1", "--format=%ct", self.REF, "--", ".hackathon/plan.md")
        try:
            ts = github.iso(datetime.fromtimestamp(int(ct), timezone.utc))
            leer_plan(texto or "", self.tabla)
        except (PlanMalo, TypeError, ValueError) as ex:
            self.malo = blob
            self.aviso(f"Sin GitHub: el plan.md de {self.REF} está mal formado ({ex}); sigo con el anterior.")
            return False
        self.blob, self.malo, self.texto, self.ts = blob, None, texto, ts
        self.ultimo_ok = int(ct)
        return True

    def resultado(self, ahora=None):
        if self.texto is None:
            return [], {}, [], 0
        tareas, motor, _, disc = tareas_de_plan(self.texto, self.tabla, self.ts)
        return tareas, motor, disc, 0


# Sin diálogos de credenciales (como el demonio y `hk-os unir`): con varias cuentas de GitHub en el Git Credential
# Manager de Windows, cada fetch del relay abría «Select an account». Mejor que falle y se vea «sin fetch».
SIN_DIALOGOS = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": "", "SSH_ASKPASS": "",
                "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}
GIT_SIN_DIALOGOS = ["git", "-c", "credential.interactive=false"]


def entorno_sin_dialogos():
    return dict(os.environ, **SIN_DIALOGOS)


def _git(cwd, *args):
    r = subprocess.run([*GIT_SIN_DIALOGOS, "-C", cwd, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, env=entorno_sin_dialogos())
    return r.stdout.strip() if r.returncode == 0 else None


def main(argv=None, cwd=".", salida=print):
    """`hk-os compilar [--seco]`. 0 bien; 1 no se puede (con el motivo); 2 plan mal formado."""
    argv = sys.argv[1:] if argv is None else argv
    seco = "--seco" in argv
    comun = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not comun:
        salida("hk-os compilar: no es un repo de git.")
        return 1
    principal = comun[:-len("/.git")] if comun.endswith("/.git") else cwd
    os_md, coord = os.path.join(principal, ".hackathon", "os.md"), os.path.join(principal, ".hackathon", "coordinacion.md")
    if conf(os_md, "activa").lower() not in ("sí", "si", "yes"):
        salida("hk-os compilar: el Hackathon OS no está activo (.hackathon/os.md). No se ha hecho nada.")
        return 1
    if conf(coord, "activa").lower() not in ("sí", "si", "yes"):
        salida("hk-os compilar: la coordinación no está activa (.hackathon/coordinacion.md). No se ha hecho nada.")
        return 1
    if sin_github(os_md):
        salida("hk-os compilar: modo sin GitHub (github: no en os.md): las tareas salen de .hackathon/plan.md de "
               "origin/main; no hay nada que compilar.")
        return 0
    repo = conf(os_md, "repo_tareas") or conf(coord, "repo")
    tabla = equipo(coord)
    if not repo or "<" in repo or not tabla:
        salida("hk-os compilar: falta el repo o la tabla de personas en coordinacion.md.")
        return 1
    # El plan, commiteado e igual al de origin/main: nadie compila un plan viejo o a medias.
    if _git(principal, "status", "--porcelain", "--", ".hackathon/plan.md"):
        salida("hk-os compilar: .hackathon/plan.md tiene cambios sin commitear. Haz commit y push antes de compilar.")
        return 1
    _git(principal, "fetch", "--quiet", "origin")
    local, remoto = _git(principal, "rev-parse", "HEAD:.hackathon/plan.md"), _git(principal, "rev-parse", "origin/main:.hackathon/plan.md")
    if not local or local != remoto:
        salida("hk-os compilar: el plan de tu copia no es el de origin/main. Sube tu plan o trae el de origin antes de compilar.")
        return 1
    try:
        tareas = leer_plan(leer_texto(os.path.join(principal, ".hackathon", "plan.md")), tabla)
    except PlanMalo as ex:
        salida(f"hk-os compilar: plan mal formado: {ex}. No se ha escrito nada.")
        return 2
    token = github.token_de_gh()
    if not token:
        salida("hk-os compilar: gh no tiene sesión (gh auth login).")
        return 1
    cliente = github.Cliente(repo, token, base=os.environ.get("HKOS_GITHUB_API", github.API))
    _, yo, _ = cliente.pedir("GET", "/user")
    yo = (yo or {}).get("login", "").lower()
    if yo not in {p["persona"] for p in tabla}:
        salida(f"hk-os compilar: @{yo} no está en la tabla de coordinacion.md.")
        return 1
    if seco:
        for t in tareas:
            salida(f"{t['id']} · {t['dueno']} · {huella(t)} · depende de {', '.join(t['depende_de']) or '—'} · {t['titulo']}")
        salida(f"{len(tareas)} tareas leídas; --seco: no se ha escrito nada.")
        return 0
    registro = os.path.join(comun, "hackathon", "os", "escrituras.jsonl")
    os.makedirs(os.path.dirname(registro), exist_ok=True)
    comp = Compilador(cliente, tabla, local[:12], registro=registro, salida=salida)
    try:
        r = comp.compilar(tareas)
    except github.Limitado as ex:
        salida(f"hk-os compilar: GitHub limita o no responde ({ex.motivo}); {comp.escritas} escrituras hechas. "
               "Vuelve a compilar más tarde: sigue donde se quedó.")
        return 1
    salida(f"Creadas {len(r['creadas'])}, editadas {len(r['editadas'])}, reabiertas {len(r['reabiertas'])}, "
           f"cerradas {len(r['cerradas'])}, sin cambios {len(r['sin_cambios'])}, dependencias {r['dependencias']}; "
           f"{r['escrituras']} escrituras." + (f" Pendientes por el tope de R-30: {r['pendientes']}; vuelve a compilar "
                                               "más tarde." if r["pendientes"] else ""))
    for k in ("creadas", "editadas", "reabiertas", "cerradas"):
        if r[k]:
            salida(f"  {k}: {', '.join(r[k])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
