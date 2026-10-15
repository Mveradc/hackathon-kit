"""Modelo del equipo: eventos normalizados + issues → estado.json (contratos/estado.schema.json). Puro, sin E/S.

Dos pasos (diseno.md §5): la atribución de los eventos sin tarea (regla 9) y el motor de estados tarea por tarea.
En M8b lo usa el simulador; en M8d y M8e, el relay. Las colisiones y las reservas llegan en M8g.
"""
import heapq
from bisect import bisect_right
from datetime import timedelta

from estados import ATRIBUIBLES, derivar, fecha, iso, ordenar

TTL_PRESENCIA_S = 90                       # R-18
SIN_TAREA_ATRIBUIBLE = {"edicion", "arbol", "commit"}   # commit desde M8e (diseno.md §5.1, regla 9)
PAPELES_ACTOR = {"principal", "orquestador", "worker", "revisor", "humano"}
# Rutas que no son trabajo de una tarea (M8f, ruido de M8e): el estado del orquestador y los informes en .hackathon/,
# y los worktrees de los workers y del revisor, que `arbol` de la copia principal ve como carpetas sin seguimiento.
RUIDO = (".hackathon/", ".claude/worktrees/")
# Eventos que no sacan de reclamada/en_curso/parada a una tarea que ya está en uno de esos estados (reglas 1, 2 y 7):
# con ellos, una tarea atribuible lo sigue siendo. Los demás (fusion.*, veredictos) y los push pueden sacarla.
MENORES = {"edicion", "arbol", "latido", "encargo.lanzado", "worker.inicio", "worker.fin", "compuerta.ok", "compuerta.ko",
           "commit", "reclamo"}


def _hasta(issues, ts):
    """Los issues con solo las acciones hasta `ts`."""
    t = fecha(ts)
    return {k: dict(v, acciones=[a for a in v.get("acciones", []) if fecha(a["ts"]) <= t]) for k, v in issues.items()}


def _ruido(e):
    """Un edicion o arbol cuyas rutas son todas ruido no es actividad sin tarea: no va a sin_tarea (M8f)."""
    rutas = e.get("rutas", [])
    return e["tipo"] in ("edicion", "arbol") and bool(rutas) and all(r.replace("\\", "/").startswith(RUIDO) for r in rutas)


def _que(e):
    if e["tipo"] == "commit":
        rama = e.get("datos", {}).get("rama")
        return f"commit: {rama}" if rama else "commit"
    rutas = [r for r in e.get("rutas", []) if not r.replace("\\", "/").startswith(RUIDO)]
    texto = ", ".join(rutas[:3]) + (f" (+{len(rutas) - 3})" if len(rutas) > 3 else "")
    return f"{e['tipo']}: {texto}" if texto else e["tipo"]


class _Indice:
    """Los eventos de cada tarea (sin los push) y los push, cada uno con su posición en el orden global. El motor recibe
    la mezcla de los dos en ese orden, el mismo que daba filtrar la lista entera (M8b), sin recorrerla por cada tarea."""

    def __init__(self, ids):
        self.propios = {t: [] for t in ids}
        self.mayores = {t: 0 for t in ids}       # eventos de la tarea que no son MENORES
        self.pushes = []
        self.n = 0
        self.de_sha = {}                         # sha de un commit o una fusión → tareas
        self.pushes_suyos = {t: 0 for t in ids}  # push cuyo incluye tiene un sha de la tarea (los únicos que la mueven)

    def anade(self, e):
        self.n += 1
        if e["tipo"] == "push":
            self.pushes.append((self.n, e))
            for t in {t for sha in e.get("datos", {}).get("incluye", []) for t in self.de_sha.get(sha, ())}:
                self.pushes_suyos[t] += 1
        elif e.get("tarea") in self.propios:
            self.propios[e["tarea"]].append((self.n, e))
            self.mayores[e["tarea"]] += e["tipo"] not in MENORES
            sha = e.get("datos", {}).get("sha")
            if sha:
                self.de_sha.setdefault(sha, set()).add(e["tarea"])

    def de(self, tid):
        return [e for _, e in heapq.merge(self.propios[tid], self.pushes, key=lambda x: x[0])]


def atribuir(tareas, issues, eventos, equipo):
    """Regla 9: pone `tarea` a los edicion/arbol/commit que no la traen, según el estado de las tareas de su persona en
    ese momento. Devuelve (eventos, sin_tarea, discrepancias sin agrupar).

    Indexado (M8e): el estado de una tarea solo se vuelve a derivar cuando ha podido cambiar si es atribuible. El paso
    del tiempo no lo cambia (reclamada, en_curso y parada lo son las tres). Si ya lo es, tampoco un evento MENORES suyo;
    sí uno de los demás, una acción de su issue o un push que incluya un sha suyo (reglas 7 y 8: un push solo mueve
    una tarea por sus commits y fusiones). Si no lo es, cualquier evento suyo."""
    salida, sin_tarea, disc = [], [], []
    por_persona = {}
    for t in tareas:
        por_persona.setdefault(t["dueno"], []).append(t)
    indice = _Indice([t["id"] for t in tareas])
    marcas = {k: sorted(fecha(a["ts"]) for a in v.get("acciones", [])) for k, v in issues.items()}
    cache = {}                                   # tarea → (clave, atribuible)
    for e in ordenar(eventos):
        if e.get("tarea") or e["tipo"] not in SIN_TAREA_ATRIBUIBLE:
            salida.append(e)
            indice.anade(e)
            continue
        persona, t_e = e["actor"]["persona"], fecha(e["ts"])
        candidatas = []
        for t in por_persona.get(persona, []):
            tid = t["id"]
            previo = cache.get(tid)
            suyos = indice.mayores[tid] if previo and previo[1] else len(indice.propios[tid])
            clave = (bool(previo and previo[1]), suyos, indice.pushes_suyos[tid], bisect_right(marcas.get(tid, []), t_e))
            if not previo or previo[0] != clave:
                issue = issues[tid]
                vigente = dict(issue, acciones=[a for a in issue.get("acciones", []) if fecha(a["ts"]) <= t_e])
                # Sin dependencias: la atribución solo mira reclamada/en_curso/parada, que no dependen de ellas.
                r = derivar(dict(t, depende_de=[]), vigente, indice.de(tid), {}, equipo, e["ts"])
                atribuible = r["estado"]["valor"] in ATRIBUIBLES
                suyos = indice.mayores[tid] if atribuible else len(indice.propios[tid])
                cache[tid] = ((atribuible, suyos, clave[2], clave[3]), atribuible)
            if cache[tid][1]:
                candidatas.append(tid)
        if len(candidatas) == 1:
            e = dict(e, tarea=candidatas[0])
        elif candidatas:
            disc.append({"tipo": "atribucion_ambigua", "persona": persona, "ts": e["ts"],
                         "detalle": f"{_que(e)} sin tarea; {persona} tiene varias abiertas: {', '.join(candidatas)}"})
        elif not _ruido(e):
            sin_tarea.append({"persona": persona, "que": _que(e), "observado_en": e["ts"]})
        salida.append(e)
        indice.anade(e)
    return salida, sin_tarea, disc


def _agrupar(disc):
    grupos = {}
    for d in sorted(disc, key=lambda d: fecha(d["ts"])):
        clave = (d["tipo"], d.get("tarea"), d.get("persona"))
        g = grupos.get(clave)
        if g is None:
            g = grupos[clave] = {"tipo": d["tipo"], "veces": 0, "primera_vez": d["ts"]}
            for k in ("tarea", "persona"):
                if d.get(k):
                    g[k] = d[k]
        g["veces"] += 1
        g["ultima_vez"], g["detalle"] = d["ts"], d["detalle"][:300]
    return list(grupos.values())


def _personas(personas, eventos, ahora):
    """Actores por persona (sesión, papel, agente) con su último evento como latido. Inactivo a los 90 s o al cerrar."""
    t_ahora = fecha(ahora)
    actores = {}
    for e in eventos:
        a = e["actor"]
        if a["papel"] not in PAPELES_ACTOR:
            continue
        clave = (a["persona"], a.get("sesion"), a.get("agente"), a["papel"])
        x = actores.setdefault(clave, {"cerrado": False})
        x["ultimo"], x["actor"] = e["ts"], a
        if e.get("tarea"):
            x["tarea"] = (e["tarea"], e["fuente"], e["ts"])
        if e["tipo"] == "arbol":
            x["ficheros"] = (e.get("rutas", []), e["fuente"], e["ts"])
        x["cerrado"] = e["tipo"] in ("sesion.fin", "worker.fin")
    salida = []
    for p in personas:
        lista = []
        for (persona, _, _, _), x in actores.items():
            if persona != p["persona"]:
                continue
            a = x["actor"]
            act = {"papel": a["papel"], "ultimo_latido": x["ultimo"],
                   "activo": not x["cerrado"] and t_ahora - fecha(x["ultimo"]) <= timedelta(seconds=TTL_PRESENCIA_S)}
            for k in ("sesion", "agente", "worktree"):
                if a.get(k) is not None:
                    act[k] = a[k]
            if "tarea" in x:
                act["tarea"] = {"valor": x["tarea"][0], "fuente": x["tarea"][1], "observado_en": x["tarea"][2]}
            if "ficheros" in x:
                act["ficheros"] = {"valor": x["ficheros"][0], "fuente": x["ficheros"][1], "observado_en": x["ficheros"][2]}
            lista.append(act)
        salida.append({"persona": p["persona"], "nombre": p["nombre"], "actores": lista})
    return salida


def calcular(tareas, issues, eventos, personas, ahora, umbral_parada_s=1200, fuentes=None, discrepancias=(),
             novedades=None):
    """estado.json a `ahora` con los eventos e issues observados hasta entonces.

    tareas: [{id, titulo, bloque?, dueno, depende_de}]; issues: {ID: {creado_en, numero?, acciones}};
    personas: [{persona, nombre}] de coordinacion.md (el equipo); fuentes: {relay|github|git: dato}; discrepancias: las de GitHub, sin agrupar (M8e);
    novedades: decisiones y criterios de origin/main (M8f, las lee el relay), hasta `ahora`.
    """
    t_ahora = fecha(ahora)
    equipo = {p["persona"] for p in personas}
    eventos = [e for e in eventos if fecha(e["ts"]) <= t_ahora]
    issues = _hasta(issues, ahora)
    eventos, sin_tarea, disc = atribuir(tareas, issues, eventos, equipo)
    disc = list(discrepancias) + disc           # las de GitHub (M8e: fuera_del_equipo, issue_duplicado…), sin agrupar
    indice = _Indice([t["id"] for t in tareas])
    for e in eventos:
        indice.anade(e)

    por_id = {t["id"]: t for t in tareas}
    resultados, en_proceso = {}, set()

    def resolver(tid):
        if tid in resultados:
            return resultados[tid]
        en_proceso.add(tid)
        t = por_id[tid]
        deps = {}
        for d in t.get("depende_de", []):
            if d in por_id and d not in en_proceso:      # un ciclo no cumple la dependencia
                r = resolver(d)
                deps[d] = {"estado": r["estado"], "declarado": r["declarado"]}
            elif d in por_id:
                deps[d] = {"estado": {"valor": "pendiente", "fuente": "derivado", "observado_en": ahora}, "declarado": None}
        resultados[tid] = derivar(t, issues[tid], indice.de(tid), deps, equipo, ahora, umbral_parada_s)
        en_proceso.discard(tid)
        return resultados[tid]

    salida_tareas = []
    for t in tareas:
        r = resolver(t["id"])
        disc += r["discrepancias"]
        x = {"id": t["id"], "titulo": t["titulo"], "dueno": t["dueno"], "depende_de": t.get("depende_de", []),
             "estado": r["estado"], "declarado": r["declarado"]}
        if t.get("bloque"):
            x["bloque"] = t["bloque"]
        if issues[t["id"]].get("numero"):
            x["issue"] = issues[t["id"]]["numero"]
        if r["fusion"]:
            x["fusion"] = r["fusion"]
        if r["cumplidas_por_cierre"]:
            x["cumplidas_por_cierre"] = r["cumplidas_por_cierre"]
        salida_tareas.append(x)

    ultimo_sin_tarea = {}
    for s in sin_tarea:
        ultimo_sin_tarea[(s["persona"], s["que"])] = s

    estado = {"v": 1, "generado_en": iso(t_ahora), "fuentes": dict(fuentes or {}),
              "personas": _personas(personas, eventos, ahora), "tareas": salida_tareas,
              "sin_tarea": list(ultimo_sin_tarea.values()), "discrepancias": _agrupar(disc), "colisiones": []}
    if novedades is not None:
        estado["novedades"] = [n for n in novedades if fecha(n["observado_en"]) <= t_ahora]
    return estado
