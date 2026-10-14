"""Modelo del equipo: eventos normalizados + issues → estado.json (contratos/estado.schema.json). Puro, sin E/S.

Dos pasos (diseno.md §5): la atribución de los eventos sin tarea (regla 9) y el motor de estados tarea por tarea.
En M8b lo usa el simulador; en M8d y M8e, el relay. Las colisiones y las reservas llegan en M8g.
"""
from datetime import timedelta

from estados import ATRIBUIBLES, derivar, fecha, iso, ordenar

TTL_PRESENCIA_S = 90                       # R-18
SIN_TAREA_ATRIBUIBLE = {"edicion", "arbol"}
PAPELES_ACTOR = {"principal", "orquestador", "worker", "revisor", "humano"}


def _hasta(issues, ts):
    """Los issues con solo las acciones hasta `ts`."""
    t = fecha(ts)
    return {k: dict(v, acciones=[a for a in v.get("acciones", []) if fecha(a["ts"]) <= t]) for k, v in issues.items()}


def _que(e):
    rutas = e.get("rutas", [])
    texto = ", ".join(rutas[:3]) + (f" (+{len(rutas) - 3})" if len(rutas) > 3 else "")
    return f"{e['tipo']}: {texto}" if texto else e["tipo"]


def atribuir(tareas, issues, eventos, equipo):
    """Regla 9: pone `tarea` a los edicion/arbol que no la traen, según el estado de las tareas de su persona en ese
    momento. Devuelve (eventos, sin_tarea, discrepancias sin agrupar)."""
    salida, sin_tarea, disc = [], [], []
    for e in ordenar(eventos):
        if e.get("tarea") or e["tipo"] not in SIN_TAREA_ATRIBUIBLE:
            salida.append(e)
            continue
        persona = e["actor"]["persona"]
        suyas = [t for t in tareas if t["dueno"] == persona]
        vigentes = _hasta(issues, e["ts"])
        candidatas = []
        for t in suyas:
            # Sin dependencias: la atribución solo mira reclamada/en_curso/parada, que no dependen de ellas.
            r = derivar(dict(t, depende_de=[]), vigentes[t["id"]], [x for x in salida if x.get("tarea") == t["id"] or x["tipo"] == "push"],
                        {}, equipo, e["ts"])
            if r["estado"]["valor"] in ATRIBUIBLES:
                candidatas.append(t["id"])
        if len(candidatas) == 1:
            salida.append(dict(e, tarea=candidatas[0]))
        else:
            salida.append(e)
            if candidatas:
                disc.append({"tipo": "atribucion_ambigua", "persona": persona, "ts": e["ts"],
                             "detalle": f"{_que(e)} sin tarea; {persona} tiene varias abiertas: {', '.join(candidatas)}"})
            else:
                sin_tarea.append({"persona": persona, "que": _que(e), "observado_en": e["ts"]})
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


def calcular(tareas, issues, eventos, personas, ahora, umbral_parada_s=1200):
    """estado.json a `ahora` con los eventos e issues observados hasta entonces.

    tareas: [{id, titulo, bloque?, dueno, depende_de}]; issues: {ID: {creado_en, numero?, acciones}};
    personas: [{persona, nombre}] de coordinacion.md (el equipo).
    """
    t_ahora = fecha(ahora)
    equipo = {p["persona"] for p in personas}
    eventos = [e for e in eventos if fecha(e["ts"]) <= t_ahora]
    issues = _hasta(issues, ahora)
    eventos, sin_tarea, disc = atribuir(tareas, issues, eventos, equipo)

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
        propios = [e for e in eventos if e.get("tarea") == tid or e["tipo"] == "push"]
        resultados[tid] = derivar(t, issues[tid], propios, deps, equipo, ahora, umbral_parada_s)
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

    return {"v": 1, "generado_en": iso(t_ahora), "fuentes": {},
            "personas": _personas(personas, eventos, ahora), "tareas": salida_tareas,
            "sin_tarea": list(ultimo_sin_tarea.values()), "discrepancias": _agrupar(disc), "colisiones": []}
