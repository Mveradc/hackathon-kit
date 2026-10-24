"""Modelo del equipo: eventos normalizados + issues → estado.json (contratos/estado.schema.json). Puro, sin E/S.

Dos pasos (diseno.md §5): la atribución de los eventos sin tarea (regla 9) y el motor de estados tarea por tarea.
En M8b lo usa el simulador; en M8d y M8e, el relay. Desde M8g, también las colisiones y las reservas (colisiones.py).
"""
import heapq
from bisect import bisect_right
from datetime import timedelta

import colisiones
from estados import ACTIVIDAD, ATRIBUIBLES, derivar, fecha, iso, ordenar

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


def _sin_commit(e):
    """Las rutas de un edicion o arbol que no tienen commit. Las de un `arbol` que solo salen del diff contra
    origin/main (`datos.solo_diff`, las últimas) ya cuentan por su `commit`: lo integrado en main local antes del push
    no es actividad sin tarea (ruido de M8e)."""
    rutas = e.get("rutas", [])
    n = e.get("datos", {}).get("solo_diff", 0) if e["tipo"] == "arbol" else 0
    return rutas[:len(rutas) - n] if n else rutas


def _ruido(e):
    """Un edicion o arbol cuyas rutas sin commit son todas ruido (o ninguna, si tenía alguna con commit) no es
    actividad sin tarea: no va a sin_tarea (M8f)."""
    rutas = _sin_commit(e)
    if e["tipo"] == "arbol" and not rutas and e.get("rutas"):
        return True
    return e["tipo"] in ("edicion", "arbol") and bool(rutas) and all(r.replace("\\", "/").startswith(RUIDO) for r in rutas)


def _que(e):
    if e["tipo"] == "commit":
        rama = e.get("datos", {}).get("rama")
        return f"commit: {rama}" if rama else "commit"
    rutas = [r for r in _sin_commit(e) if not r.replace("\\", "/").startswith(RUIDO)]
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
        # El `arbol` del demonio (al cambiar origin/main, también por el push de otra persona) solo cuenta para las
        # colisiones: no es actividad de nadie, ni va a sin_tarea.
        if e.get("tarea") or e["tipo"] not in SIN_TAREA_ATRIBUIBLE or e["actor"]["papel"] == "demonio":
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


def _visto(conflicto, t_ahora):
    """Un conflicto del nivel 2 cuenta a `t_ahora` si ya se veía: la más antigua de `desde` y `desde_2b` (M11: la que
    no sea None) no es posterior."""
    horas = [fecha(d) for d in (conflicto.get("desde"), conflicto.get("desde_2b")) if d]
    return bool(horas) and min(horas) <= t_ahora


def calcular(tareas, issues, eventos, personas, ahora, umbral_parada_s=1200, fuentes=None, discrepancias=(),
             novedades=None, contratos=None, conflictos=None):
    """estado.json a `ahora` con los eventos e issues observados hasta entonces.

    tareas: [{id, titulo, bloque?, dueno, depende_de}]; issues: {ID: {creado_en, numero?, acciones}};
    personas: [{persona, nombre}] de coordinacion.md (el equipo); fuentes: {relay|github|git: dato}; discrepancias: las de GitHub, sin agrupar (M8e);
    novedades: decisiones y criterios de origin/main (M8f, las lee el relay), hasta `ahora`;
    contratos: bloques de docs/contratos.md con su dueño (contratos.duenos, M8g); conflictos: los de merge-tree entre
    las refs de trabajo en curso (colisiones_merge.py, M8g), [{personas, rutas, desde}]; con el nivel 2b (M11,
    ADR-0014), [{personas, rutas, rutas_2b, desde, desde_2b}], con `desde` o `desde_2b` a None si su lista está vacía.
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
    estado["colisiones"], reservas = colisiones.calcular(eventos, personas, ahora, contratos,
                                                         [c for c in conflictos or [] if _visto(c, t_ahora)])
    if reservas or any(e["tipo"] in ("reserva", "liberacion") for e in eventos):
        estado["reservas"] = reservas
    if novedades is not None:
        estado["novedades"] = [n for n in novedades if fecha(n["observado_en"]) <= t_ahora]
    return estado


# Eventos que pueden cambiar la fase de una tarea que ya la tiene (estados.derivar, reglas 2 a 7); con la fase vacía
# (lista, pendiente, reclamada), cualquier actividad la pone en curso (regla 1).
CAMBIAN_FASE = {"encargo.lanzado", "fusion.creada", "revision.veredicto", "fusion.descartada", "fusion.aprobada", "commit"}
HECHAS = {"publicada", "cerrada"}          # una `cerrada` derivada; la cerrada a mano va en `declarado`, no aquí
SIN_FASE = {None, "lista", "pendiente", "reclamada"}


def _ultima_senal(lista, con_id):
    """La hora del último evento de la tarea que cuenta como trabajo suyo (#56, punto 2): un commit con su ID (`con_id`:
    los ids de los eventos que ya traían tarea antes de la regla 9) o una edición atribuida a ella sin ambigüedad (las
    ambiguas no llevan tarea, así que no están en su lista). Ni latidos, ni push, ni acciones del issue, ni commits sin
    ID. None si no hay ninguno."""
    horas = [e["ts"] for e in lista if e["tipo"] == "edicion" or (e["tipo"] == "commit" and e["id"] in con_id)]
    return max(horas, key=fecha) if horas else None


def _historia_tarea(t, issue, lista, equipo, umbral_parada_s, con_id=frozenset()):
    """La historia de una tarea (api.md §11.2): el motor de estados (derivar, el de calcular) en cada evento que puede
    cambiar su estado, con los eventos ya atribuidos hasta ese evento. Solo se recalcula en los eventos que pueden
    llevarla a en_curso o a hecha: la primera actividad, los de CAMBIAN_FASE y los push que incluyen por primera vez un
    sha suyo (regla 8). Las dependencias no cambian ninguno de esos pasos (solo lista frente a pendiente).
    `lista`: sus eventos y los push de git que incluyen algún sha suyo (los demás no la mueven), en orden.

    Devuelve (historia, evidencia): evidencia es {valor: sha, tipo: commit | fusion, fuente, observado_en} del commit
    con ID o de la fusión que la publicó la última vez, con la hora de esa publicación (ADR-0012, decisión 6B)."""
    t = dict(t, depende_de=[])
    acciones = sorted(issue.get("acciones", []), key=lambda a: fecha(a["ts"]))
    primera = hecha = nuevo = evidencia = None
    previo, hecha_ahora, shas, incluidos, commits = None, False, set(), set(), []
    for k, e in enumerate(lista):
        d = e.get("datos") or {}
        if e["tipo"] == "push":
            nuevos = set(d.get("incluye", [])) & (shas - incluidos)
            incluidos |= set(d.get("incluye", [])) & shas
            if not nuevos or hecha_ahora:
                continue
        else:
            if d.get("sha"):
                shas.add(d["sha"])
                if e["tipo"] == "commit":
                    commits.append(d["sha"])
            if e["tipo"] not in ACTIVIDAD or (previo not in SIN_FASE and e["tipo"] not in CAMBIAN_FASE):
                continue
        vigente = dict(issue, acciones=[a for a in acciones if fecha(a["ts"]) <= fecha(e["ts"])])
        r = derivar(t, vigente, lista[:k + 1], {}, equipo, e["ts"], umbral_parada_s)
        valor = r["estado"]["valor"]
        if valor == "en_curso":
            primera = primera or e["ts"]
            if hecha and nuevo is None:                  # trabajo nuevo desde la última vez que estuvo hecha
                nuevo = e["ts"]
        if valor in HECHAS and not hecha_ahora:
            hecha, nuevo = hecha or e["ts"], None
            incluye = set(d.get("incluye", []))
            commit = next((s for s in reversed(commits) if s in incluye), None)
            if e["tipo"] == "commit" and d.get("sha"):
                sha, tipo = d["sha"], "commit"
            elif r["fusion"] and (r["fusion"] in incluye or not commit):
                sha, tipo = r["fusion"], "fusion"
            else:
                sha, tipo = commit, "commit"
            if sha:
                evidencia = {"valor": sha, "tipo": tipo, "fuente": e["fuente"] if e["fuente"] in ("git", "github") else "git",
                             "observado_en": e["ts"]}
        hecha_ahora, previo = valor in HECHAS, valor
    ultimo = max([e["ts"] for e in lista] + [a["ts"] for a in acciones] + [issue["creado_en"]], key=fecha)
    return ({"primera_senal": primera, "hecha_en": hecha, "trabajo_nuevo_desde": None if hecha_ahora else nuevo,
             "ultima_senal": _ultima_senal(lista, con_id), "fuente": "derivado", "observado_en": ultimo}, evidencia)


def historias(tareas, issues, eventos, personas, ahora, umbral_parada_s=1200, cache=None):
    """M10 (api.md §11.2; ADR-0012, decisión 6B; ADR-0013, decisión 5A): {ID: (historia, evidencia)} de cada tarea, con
    los eventos del registro (sin latidos: no se guardan) y las acciones de GitHub hasta `ahora`. La atribución es la
    de calcular (regla 9, que solo mira el pasado de cada evento), así que cada paso es el que daría calcular a esa
    hora. `cache` (un dict que guarda quien llama) evita volver a derivar las tareas cuyos eventos no han cambiado."""
    t_ahora = fecha(ahora)
    equipo = {p["persona"] for p in personas}
    eventos = [e for e in eventos if e["tipo"] != "latido" and fecha(e["ts"]) <= t_ahora]
    issues = _hasta(issues, ahora)
    con_id = {e["id"] for e in eventos if e.get("tarea")}         # antes de la regla 9: para historia.ultima_senal
    eventos, _, _ = atribuir(tareas, issues, eventos, equipo)
    indice = _Indice([t["id"] for t in tareas])
    for e in eventos:
        indice.anade(e)
    pushes = [(n, e, set((e.get("datos") or {}).get("incluye", []))) for n, e in indice.pushes if e["fuente"] == "git"]
    salida, nueva = {}, {}
    for t in tareas:
        propios, issue = indice.propios[t["id"]], issues[t["id"]]
        shas = {(e.get("datos") or {}).get("sha") for _, e in propios} - {None}
        lista = [e for _, e in heapq.merge(propios, [(n, e) for n, e, inc in pushes if inc & shas], key=lambda x: x[0])]
        clave = (t["id"], t["dueno"], tuple(e["id"] for e in lista), issue["creado_en"],
                 tuple((a["accion"], a["ts"], a["por"], a.get("a")) for a in issue["acciones"]))
        nueva[clave] = (cache or {}).get(clave) or _historia_tarea(t, issue, lista, equipo, umbral_parada_s, con_id)
        salida[t["id"]] = nueva[clave]
    if cache is not None:
        cache.clear()
        cache.update(nueva)
    return salida
