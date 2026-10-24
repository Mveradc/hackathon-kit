"""Colisiones y reservas del Hackathon OS (M8g, ADR-0007, diseno.md §7). Puro, sin E/S: lo llama modelo.calcular.

- Nivel 1 (amarillo, R-19): dos personas distintas con cambios sin fusionar en el mismo fichero. Los ficheros de cada
  persona salen de sus eventos: por cada árbol en que trabaja (la copia principal o el worktree de un worker), las
  rutas de su último `arbol` más las de los `edicion` posteriores. El de un worker deja de contar con su `worker.fin`.
  El `arbol` de la copia principal también lo emite el demonio al cambiar origin/main (fuente git): así, un push desde
  la terminal saca los ficheros subidos sin esperar a la siguiente herramienta de la sesión.
- Nivel 2 (rojo, R-20): los conflictos de `git merge-tree` entre las refs de trabajo en curso (los calcula
  colisiones_merge.py en el relay; aquí llegan hechos). Un fichero en conflicto entre dos personas deja de salir en su
  amarillo.
- Nivel 2b (amarillo, R-34, M11, ADR-0014): con `fusion_estructural: sí` en el relay, las rutas del conflicto que
  Mergiraf resuelve llegan aparte (`rutas_2b`, desde `desde_2b`) y salen como `2b:<a>+<b>`. También tapan el nivel 1.
  Sin `rutas_2b` (el interruptor apagado), todo como en la 0.5.0.
- Nivel 3 (rojo, R-21): contrato tocado por quien no es su dueño (contratos.py).
- Reservas (R-22): eventos `reserva` y `liberacion`; vencen con `ts + ttl_s`.
Dentro de una persona no hay colisiones (criterio 6 de M8g): el orquestador ya serializa a sus workers.
"""
from datetime import timedelta

from contratos import nivel3
from estados import fecha, iso, ordenar

RUIDO = (".claude/worktrees/",)          # los worktrees de los workers, que `arbol` de la copia principal ve sin seguimiento


def ruta_limpia(r):
    """Ruta de un evento → (clave, ruta) o None. Clave sin mayúsculas (Windows y la herramienta Edit no respetan la
    grafía de git); las entradas de carpeta («?? web/») no son un fichero: lo nuevo dentro llega por su `edicion`."""
    r = (r or "").replace("\\", "/").strip()
    while r.startswith("./"):
        r = r[2:]
    if not r or r.endswith("/") or r.lower().startswith(RUIDO):
        return None
    return r.lower(), r


def ruta_reserva(r):
    """Ruta de una reserva: relativa, con «/»; una carpeta acaba en «/» (reserva todo lo que hay debajo)."""
    r = (r or "").replace("\\", "/").strip()
    while r.startswith("./"):
        r = r[2:]
    return r or None


def ficheros(eventos, equipo):
    """{persona: {"rutas": {clave: (ruta, desde)}, "contratos": {nombre: desde}}}: lo que cada persona del equipo tiene
    cambiado ahora, con la hora en que entró cada cosa (sigue contando desde entonces mientras no salga)."""
    arboles = {}                            # (persona, clave del árbol) → {"rutas": {...}, "contratos": {...}}
    for e in ordenar(eventos):
        persona = e["actor"]["persona"]
        if persona not in equipo:
            continue
        agente = e["actor"].get("agente")
        if e["actor"]["papel"] == "worker" and agente:
            arbol = ("worker", agente)
        else:
            arbol = ("arbol", (e["actor"].get("worktree") or "").lower())
        clave = (persona, arbol)
        if e["tipo"] == "worker.fin" and agente:
            arboles.pop((persona, ("worker", agente)), None)
            continue
        if e["tipo"] == "arbol":
            antes = arboles.get(clave, {"rutas": {}, "contratos": {}})
            rutas = {}
            for r in e.get("rutas", []):
                x = ruta_limpia(r)
                if x:
                    rutas[x[0]] = antes["rutas"].get(x[0], (x[1], e["ts"]))
            contratos = {n: antes["contratos"].get(n, e["ts"]) for n in e.get("datos", {}).get("contratos", []) if n}
            # El `arbol` del demonio (fuente git, al cambiar origin/main) no saca los bloques tocados: se quedan los
            # del último `arbol` mientras docs/contratos.md siga cambiado.
            if e["fuente"] == "git" and "contratos" not in e.get("datos", {}) and "docs/contratos.md" in rutas:
                contratos = dict(antes["contratos"])
            arboles[clave] = {"rutas": rutas, "contratos": contratos}
        elif e["tipo"] == "edicion":
            a = arboles.setdefault(clave, {"rutas": {}, "contratos": {}})
            for r in e.get("rutas", []):
                x = ruta_limpia(r)
                if x and x[0] not in a["rutas"]:
                    a["rutas"][x[0]] = (x[1], e["ts"])
    salida = {}
    for (persona, _), a in arboles.items():
        p = salida.setdefault(persona, {"rutas": {}, "contratos": {}})
        for k, (ruta, desde) in a["rutas"].items():
            if k not in p["rutas"] or fecha(desde) < fecha(p["rutas"][k][1]):
                p["rutas"][k] = (ruta, desde)
        for n, desde in a["contratos"].items():
            if n not in p["contratos"] or fecha(desde) < fecha(p["contratos"][n]):
                p["contratos"][n] = desde
    return salida


def nivel1(conjuntos, conflictos=()):
    """Una colisión amarilla por conjunto de personas que comparten ficheros. Un fichero en conflicto de nivel 2 entre
    exactamente esas personas no sale aquí (ya sale en rojo, o en el amarillo del nivel 2b)."""
    tapadas = {(frozenset(c["personas"]), r.lower()) for c in conflictos for r in c["rutas"] + c.get("rutas_2b", [])}
    por_ruta = {}
    for persona, p in conjuntos.items():
        for k, (ruta, desde) in p["rutas"].items():
            por_ruta.setdefault(k, {})[persona] = (ruta, desde)
    grupos = {}
    for k, quien in por_ruta.items():
        if len(quien) < 2:
            continue
        personas = frozenset(quien)
        if (personas, k) in tapadas:
            continue
        ruta = min(r for r, _ in quien.values())                 # una grafía estable si las dos difieren
        entro = max((d for _, d in quien.values()), key=fecha)   # cuando la tuvieron todas
        g = grupos.setdefault(personas, {})
        g[ruta] = entro
    salida = []
    for personas, rutas in grupos.items():
        orden = sorted(personas)
        salida.append({"id": "1:" + "+".join(orden), "nivel": "1", "gravedad": "amarillo", "personas": orden,
                       "rutas": sorted(rutas, key=str.lower), "observado_en": max(rutas.values(), key=fecha)})
    return salida


def nivel2(conflictos):
    """Los conflictos de merge-tree (colisiones_merge.py) como colisiones: [{personas, rutas, rutas_2b?, desde,
    desde_2b?}]. Por par, `2:` rojo con `rutas` y, con 2b (M11), `2b:` amarillo con `rutas_2b`, cada una solo si tiene
    rutas. Sin `rutas_2b`, la roja sale siempre, como en la 0.5.0."""
    salida = []
    for c in conflictos:
        orden = sorted(c["personas"])
        if c["rutas"] or "rutas_2b" not in c:
            salida.append({"id": "2:" + "+".join(orden), "nivel": "2", "gravedad": "rojo", "personas": orden,
                           "rutas": sorted(c["rutas"], key=str.lower), "observado_en": c["desde"]})
        if c.get("rutas_2b"):
            salida.append({"id": "2b:" + "+".join(orden), "nivel": "2b", "gravedad": "amarillo", "personas": orden,
                           "rutas": sorted(c["rutas_2b"], key=str.lower), "observado_en": c["desde_2b"]})
    return salida


def reservas(eventos, equipo, ahora):
    """Reservas vigentes a `ahora`: `reserva` no liberada y con ts + ttl_s > ahora. Las de fuera del equipo no cuentan."""
    t_ahora, vivas = fecha(ahora), {}
    for e in ordenar(eventos):
        if fecha(e["ts"]) > t_ahora or e["actor"]["persona"] not in equipo:
            continue
        d = e.get("datos", {})
        if e["tipo"] == "reserva":
            hasta = fecha(e["ts"]) + timedelta(seconds=int(d.get("ttl_s", 900)))
            r = {"id": e["id"], "rutas": [x for x in (ruta_reserva(r) for r in e.get("rutas", [])) if x],
                 "persona": e["actor"]["persona"], "hasta": iso(hasta), "modo": d.get("modo", "compartida")}
            if e["actor"].get("sesion"):
                r["actor"] = e["actor"]["sesion"]
            vivas[e["id"]] = r
        elif e["tipo"] == "liberacion":
            v = vivas.get(d.get("reserva"))
            if v and v["persona"] == e["actor"]["persona"]:      # solo libera quien reservó
                del vivas[d["reserva"]]
    return sorted((r for r in vivas.values() if fecha(r["hasta"]) > t_ahora), key=lambda r: (r["hasta"], r["id"]))


def calcular(eventos, personas, ahora, contratos=None, conflictos=None):
    """(colisiones, reservas) de estado.json. `contratos`: los bloques con dueño de contratos.duenos (el relay los lee
    de origin/main); `conflictos`: los de merge-tree [{personas, rutas, desde}] y, con 2b (M11), también `rutas_2b` y
    `desde_2b`."""
    equipo = {p["persona"] for p in personas}
    conjuntos = ficheros(eventos, equipo)
    conflictos = [c for c in (conflictos or []) if len(set(c["personas"]) & equipo) == 2]
    colisiones = nivel2(conflictos) + nivel1(conjuntos, conflictos)
    if contratos:
        colisiones += nivel3(contratos, conjuntos, [p["persona"] for p in personas])
    colisiones.sort(key=lambda c: c["id"])
    return colisiones, reservas(eventos, equipo, ahora)
