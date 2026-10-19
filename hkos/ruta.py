"""Ruta crítica del Hackathon OS (M10, R-36, ADR-0013; api.md §11.4): el bloque `ruta` de la vista. Función pura, sin
E/S, sin red, sin git y sin reloj propio (`ahora` es un parámetro), como el motor de estados.

calcular(ruta, tareas, ahora, …) recibe lo que el relay deja en estado.json (`ruta`: equipo, zona, inicio, entrega,
otras_entregas, hitos y descansos; `tareas[]` con hasta, franja, orden_plan, historia, depende_de, dueno, estado y
declarado) y devuelve el bloque con la forma de `$defs/vista_ruta` de estado.schema.json. firma(bloque) es lo que firma
el md (`ruta:`): solo el veredicto.

Reglas (ADR-0013): el objetivo es la entrega de equipo.md (las otras, al lado, sin quitar la estimación); el grafo, con
`depende_de` y la cadena de cada persona (orden del plan, inferida); el ritmo, por persona, desde 3 medidas; con menos,
solo hechos y «n de 3»; un rango y un veredicto de cuatro valores, nunca una sola hora; «sin plazo» nunca es «a tiempo»;
«sin señales» nunca es «va lenta»; los descansos no cuentan; el rojo, solo para hechos.
"""
import math
import re
from datetime import timedelta, timezone

from estados import fecha, iso

MINIMO = 3                                  # base.minimo: fijo en el contrato (decisión 7A), no se configura
HECHAS = {"publicada", "cerrada"}
# Con trabajo empezado: lo ya trabajado (desde primera_senal, sin descansos) se descuenta de lo que le queda.
EMPEZADAS = {"en_curso", "parada", "no_cerrada", "en_revision", "integrada"}
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
GRAVEDAD = {"rojo": 0, "ambar": 1, "gris": 2}
LEGIBLE = {"a_tiempo": "a tiempo", "justo": "justo", "no_llega": "no llega"}
RESUMEN_MAX = 160
DESFASE = re.compile(r"^(?:UTC)?([+-])(\d{1,2})(?::?(\d\d))?$")


def _v(d):
    return (d or {}).get("valor")


def fuera_de_entrega(t):
    """Decisión 8B: `condicional` si el título empieza por «Si », `si_da_tiempo` si lleva [SI DA TIEMPO] (sin
    distinguir mayúsculas); None si cuenta para la entrega."""
    titulo = " ".join(t.get("titulo", "").split()).casefold()
    if titulo.startswith("si "):
        return "condicional"
    if "[si da tiempo]" in titulo:
        return "si_da_tiempo"
    return None


def cerrada_a_mano(t):
    return _v(t.get("declarado")) == "cerrada" and t["estado"]["valor"] not in HECHAS


def hecha(t):
    """Hecha para la ruta: publicada o cerrada; una cerrada a mano (⚑) cuenta, pero no se mide."""
    return t["estado"]["valor"] in HECHAS or cerrada_a_mano(t)


def _junta(intervalos):
    salida = []
    for a, b in sorted(intervalos):
        if salida and a <= salida[-1][1]:
            salida[-1] = (salida[-1][0], max(salida[-1][1], b))
        else:
            salida.append((a, b))
    return salida


def _solape(a, b, pausas):
    """Segundos de [a, b) que caen en los descansos (ya juntados)."""
    return sum(max(0.0, (min(b, y) - max(a, x)).total_seconds()) for x, y in pausas)


def _avanza(t, segundos, pausas):
    """La hora a la que acaban `segundos` de trabajo empezados en t, saltando los descansos."""
    for a, b in pausas:
        if b <= t:
            continue
        if a > t:
            hueco = (a - t).total_seconds()
            if segundos <= hueco:
                break
            segundos -= hueco
        t = max(t, b)
    return t + timedelta(seconds=segundos)


def _es_de(descanso, persona, nombre):
    quien = descanso.get("persona")
    if quien is None:
        return True
    quien = quien.strip().lstrip("@").casefold()
    return quien == "todos" or quien == persona.casefold() or (nombre is not None and quien == nombre.casefold())


def _zona(ruta):
    """La zona de las horas del resumen: el desfase de la entrega (o del inicio) de equipo.md, que el relay resuelve
    con su zona; si no, la zona si es un desfase; si no, UTC. Sin zoneinfo: sin tzdata (Windows) daría otra salida."""
    for d in (ruta.get("entrega"), ruta.get("inicio")):
        if d and d.get("valor"):
            return fecha(d["valor"]).tzinfo
    m = DESFASE.match(str(_v(ruta.get("zona")) or "").strip())
    if m:
        signo = 1 if m.group(1) == "+" else -1
        return timezone(signo * timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0)))
    return timezone.utc


def _ciclo(ids, sucesoras):
    """El primer ciclo del grafo (DFS en orden de ID), empezando por su ID menor y con él repetido al final."""
    color = {}
    for raiz in ids:
        if raiz in color:
            continue
        color[raiz], camino, pila = 1, [raiz], [iter(sorted(sucesoras[raiz]))]
        while pila:
            for m in pila[-1]:
                if color.get(m) == 1:
                    c = camino[camino.index(m):]
                    i = c.index(min(c))
                    c = c[i:] + c[:i]
                    return c + [c[0]]
                if m not in color:
                    color[m] = 1
                    camino.append(m)
                    pila.append(iter(sorted(sucesoras[m])))
                    break
            else:
                color[camino.pop()] = 2
                pila.pop()
    return None


def calcular(ruta, tareas, ahora, personas=(), fuentes=None, tarjetas=None, umbral_parada_s=1200):
    """El bloque `ruta` de la vista ($defs/vista_ruta).

    ruta: el bloque `ruta` de estado.json. tareas: `tareas[]` de estado.json. ahora: ISO 8601.
    personas: `vista["personas"]` ({persona, nombre?, ultima_senal}). fuentes: `vista["fuentes"]` ({k: {valor,
    observado_en, viejo}}). tarjetas: {ID: tarjeta de la vista (api.md §6)}; sin ella, una mínima. umbral_parada_s: el
    `umbral_parada_min` de os.md, en segundos (para «sin señales»)."""
    from proyeccion import ETIQUETAS, corta     # aquí: proyeccion importa este módulo
    t_ahora, fuentes, tarjetas = fecha(ahora), fuentes or {}, tarjetas or {}
    nombres = {p["persona"]: p.get("nombre") for p in personas}
    senales = {p["persona"]: p.get("ultima_senal") for p in personas}
    descansos = list(ruta.get("descansos", []))
    usables = [d for d in descansos if d.get("desde") and d.get("hasta")]
    cache_pausas = {}

    def pausas(persona):
        if persona not in cache_pausas:
            cache_pausas[persona] = _junta([(fecha(d["desde"]), fecha(d["hasta"])) for d in usables
                                            if _es_de(d, persona, nombres.get(persona))])
        return cache_pausas[persona]

    def viejo_de(fuente):
        return bool(fuentes.get(fuente if fuente in ("github", "git") else "relay", {}).get("viejo"))

    def tarjeta(t):
        x = dict(tarjetas[t["id"]]) if t["id"] in tarjetas else {
            "id": t["id"], "titulo": t["titulo"], "dueno": t["dueno"], "estado": t["estado"]["valor"],
            "etiqueta": ETIQUETAS[t["estado"]["valor"]], "fuente": t["estado"]["fuente"],
            "observado_en": t["estado"]["observado_en"]}
        x["viejo"] = viejo_de(t["estado"]["fuente"])
        return x

    # --- qué cuenta (decisión 8B) y el grafo (decisión 3B) ---
    fuera, cuentan = [], {}
    for t in tareas:
        motivo = fuera_de_entrega(t)
        if motivo:
            fuera.append({"tarea": t["id"], "motivo": motivo})
        else:
            cuentan[t["id"]] = t
    ids = sorted(cuentan)
    abiertas = {k for k, t in cuentan.items() if not hecha(t)}
    previas = {k: {} for k in ids}                 # B → {A: por}: A va antes que B
    for k in ids:
        for d in cuentan[k].get("depende_de", []):
            if d in cuentan:
                previas[k][d] = "depende_de"
    filas = {}
    for k in ids:
        orden = _v(cuentan[k].get("orden_plan"))
        if isinstance(orden, int) and not isinstance(orden, bool):
            filas.setdefault(cuentan[k]["dueno"], []).append((orden, k))
    for suyas in filas.values():
        suyas.sort()
        for (_, a), (_, b) in zip(suyas, suyas[1:]):
            previas[b].setdefault(a, "orden_del_plan")
    sucesoras = {k: [] for k in ids}
    for b in ids:
        for a in previas[b]:
            sucesoras[a].append(b)

    # --- medidas y ritmo (decisión 5A) ---
    medidas = {}
    for t in tareas:
        h, fr = t.get("historia") or {}, _v(t.get("franja"))
        if t["estado"]["valor"] in HECHAS and not t.get("declarado") and h.get("primera_senal") and h.get("hecha_en") \
                and fr:
            a, b = fecha(h["primera_senal"]), fecha(h["hecha_en"])
            seg = (b - a).total_seconds() - _solape(a, b, pausas(t["dueno"]))
            ritmo = max(1, math.floor(100 * seg / 60 / fr["min"] + 0.5))
            medidas.setdefault(t["dueno"], []).append((ritmo, h["hecha_en"]))
    duenos_abiertos = {cuentan[k]["dueno"] for k in abiertas}
    base_personas = []
    for p in sorted(set(medidas) | {t["dueno"] for t in cuentan.values()}):
        rs = [r for r, _ in medidas.get(p, [])]
        hay = len(rs) >= MINIMO
        base_personas.append({"persona": p, "n": len(rs), "ritmo_min": min(rs) if hay else None,
                              "ritmo_max": max(rs) if hay else None, "fuente": "derivado", "observado_en": ahora})
    ritmos = {b["persona"]: (b["ritmo_min"], b["ritmo_max"]) for b in base_personas}
    hechas_en = [h for ms in medidas.values() for _, h in ms]

    # --- veredicto sin estimación: sus motivos, en orden ---
    motivos = []
    entrega = ruta.get("entrega")
    equipo_ok = _v(ruta.get("equipo")) == "ok"
    objetivo = dict(entrega) if entrega and equipo_ok else None
    t_entrega = fecha(objetivo["valor"]) if objetivo and objetivo.get("valor") else None
    if t_entrega is None:
        motivos.append("entrega_doble" if objetivo and objetivo.get("motivo") == "dos_horas" else "sin_entrega")
    ciclo = _ciclo(ids, sucesoras)
    if ciclo:
        motivos.append("ciclo")
    sin_plazo = []
    for k in ids:
        t = cuentan[k]
        if k in abiertas and not _v(t.get("franja")):
            hasta = t.get("hasta") or {}
            motivo = (hasta.get("motivo") or "vacio") if not hasta.get("valor") else \
                ((t.get("franja") or {}).get("motivo") or "sin_plazo")
            sin_plazo.append({"tarea": k, "motivo": motivo})
    if sin_plazo:
        motivos.append("sin_plazo")
    pocos = [b for b in base_personas if b["n"] < MINIMO and b["persona"] in duenos_abiertos]
    if pocos:
        motivos.append("pocos_datos")

    # --- estimación: cada tarea abierta, tras sus previas abiertas, al ritmo de su dueño y saltando descansos ---
    fin, estimacion = {}, None

    def termina(k):
        if k not in fin:
            t = cuentan[k]
            p, h, fr = t["dueno"], t.get("historia") or {}, _v(t["franja"])
            antes = [termina(a) for a in previas[k] if a in abiertas]
            trabajado = 0.0
            if t["estado"]["valor"] in EMPEZADAS and h.get("primera_senal") and fecha(h["primera_senal"]) < t_ahora:
                a = fecha(h["primera_senal"])
                trabajado = (t_ahora - a).total_seconds() - _solape(a, t_ahora, pausas(p))
            par = []
            for i, ritmo in enumerate(ritmos[p]):
                seg = max(0, math.ceil(fr["min"] * 60 * ritmo / 100 - trabajado))
                par.append(_avanza(max([t_ahora] + [x[i] for x in antes]), seg, pausas(p)))
            fin[k] = tuple(par)
        return fin[k]

    if not motivos:
        for k in ids:
            if k in abiertas:
                termina(k)
        temprano = max([f[0] for f in fin.values()], default=t_ahora)
        tarde = max([f[1] for f in fin.values()], default=t_ahora)
        estimacion = {"temprano": iso(temprano), "tarde": iso(tarde),
                      "margen_min": math.floor((t_entrega - tarde).total_seconds() / 60),
                      "margen_max": math.floor((t_entrega - temprano).total_seconds() / 60)}
        valor = "a_tiempo" if tarde <= t_entrega else "justo" if temprano <= t_entrega else "no_llega"
    else:
        valor = "sin_estimacion"
    gravedad = {"a_tiempo": "ninguna", "justo": "ambar", "no_llega": "ambar"}.get(valor, "gris")

    # --- hechos, con o sin estimación ---
    def arrastra(k):
        vistas, pila = set(), list(sucesoras[k])
        while pila:
            m = pila.pop()
            if m not in vistas:
                vistas.add(m)
                pila.extend(sucesoras[m])
        return sorted((vistas & abiertas) - {k})

    hechos = []
    for k in ids:
        t = cuentan[k]
        if k not in abiertas:
            continue
        plazo = _v(t.get("hasta"))
        comun = {"tarea": k, "persona": t["dueno"], "plazo": plazo, "fuente": "derivado", "observado_en": ahora,
                 "viejo": viejo_de(t["estado"]["fuente"])}
        if plazo and fecha(plazo) < t_ahora:
            hechos.append(dict(comun, tipo="plazo_pasado", gravedad="rojo", arrastra=arrastra(k)))
        if t["estado"]["valor"] in ("parada", "no_cerrada"):
            hechos.append(dict(comun, tipo=t["estado"]["valor"], gravedad="ambar"))
    for p in sorted(duenos_abiertos):
        ultima = senales.get(p)
        callada = ultima is None or (t_ahora - fecha(ultima)).total_seconds() > umbral_parada_s
        if callada and not any(a <= t_ahora < b for a, b in pausas(p)):
            hechos.append({"tipo": "sin_senales", "gravedad": "gris", "persona": p, "desde": ultima,
                           "fuente": "derivado", "observado_en": ahora, "viejo": viejo_de("relay")})
    if ciclo:
        hechos.append({"tipo": "ciclo", "gravedad": "gris", "ciclo": ciclo, "fuente": "derivado",
                       "observado_en": ahora, "viejo": viejo_de("git")})
    hechos.sort(key=lambda x: (GRAVEDAD[x["gravedad"]], x.get("plazo") is None,
                               fecha(x["plazo"]) if x.get("plazo") else t_ahora, x.get("tarea", ""),
                               x.get("persona", "")))

    # --- cadena: la que lleva al fin más tardío (o, sin estimación, al Hasta resuelto más tardío) ---
    if estimacion:
        def clave(k):
            return fin[k][1]
        candidatas = [k for k in ids if k in abiertas]
    else:
        def clave(k):
            v = _v(cuentan[k].get("hasta"))
            return (v is not None, fecha(v) if v else t_ahora)
        candidatas = [k for k in ids if k in abiertas and _v(cuentan[k].get("hasta"))]
    eslabones = []
    actual = max(candidatas, key=clave, default=None)
    while actual is not None and actual not in eslabones:      # con un ciclo, se para al volver a una
        eslabones.append(actual)
        antes = sorted(a for a in previas[actual] if a in abiertas)
        actual = max(antes, key=clave, default=None)
    eslabones.reverse()
    cadena = []
    for i, k in enumerate(eslabones):
        t = cuentan[k]
        cadena.append({
            "tarjeta": tarjeta(t), "por": "inicio" if i == 0 else previas[k][eslabones[i - 1]],
            "hasta": t.get("hasta") or {"valor": None, "texto": None, "motivo": "vacio", "fuente": "git",
                                        "observado_en": ahora, "declarado": True},
            "franja": t.get("franja") or {"valor": None, "motivo": "sin_plazo", "fuente": "derivado",
                                          "observado_en": ahora, "declarado": True},
            "fin_temprano": iso(fin[k][0]) if estimacion else None,
            "fin_tarde": iso(fin[k][1]) if estimacion else None})

    # --- lo declarado, al lado ---
    otras = [o for o in ruta.get("otras_entregas", [])
             if t_entrega is None or not o.get("valor") or fecha(o["valor"]) != t_entrega]
    hitos = [{"hito": h, "pasado": bool(h.get("valor")) and fecha(h["valor"]) < t_ahora}
             for h in ruta.get("hitos", [])]
    leidas = [d for d in fuentes.values() if d.get("valor") != "no"]     # sin GitHub (M8h) no envejece
    dato_mas_viejo = min((d["observado_en"] for d in leidas), key=fecha, default=None)

    # --- resumen (decisión 7B) ---
    tz = _zona(ruta)

    def hm(x):
        return fecha(x).astimezone(tz).strftime("%H:%M")

    def dia_hm(x):
        d = fecha(x).astimezone(tz)
        return f"{DIAS[d.weekday()]} {d.strftime('%H:%M')}"

    if estimacion:
        resumen = f"ruta: estimación {LEGIBLE[valor]} · fin {hm(estimacion['temprano'])}–{hm(estimacion['tarde'])} · " \
                  f"entrega {dia_hm(objetivo['valor'])}" + (" (confirmar)" if objetivo.get("confirmar") else "")
    else:
        primero = motivos[0]
        por = {"sin_entrega": "sin hora de entrega", "entrega_doble": "dos horas de entrega",
               "ciclo": "ciclo " + " → ".join(ciclo or []),
               "sin_plazo": "sin plazo: " + ", ".join(x["tarea"] for x in sin_plazo),
               "pocos_datos": "pocos datos: " + ", ".join(f"@{b['persona']} {b['n']} de {MINIMO}" for b in pocos)}
        resumen = f"ruta: sin estimación ({por[primero]})"
    if otras:
        resumen += f" · otra entrega: {otras[0].get('texto') or '—'} ({otras[0]['donde']})"
    pasados = [x for x in hechos if x["tipo"] == "plazo_pasado"]
    if pasados:
        resumen += f" · {pasados[0]['tarea']}: plazo pasado {hm(pasados[0]['plazo'])}" + \
                   (f" y {len(pasados) - 1} más" if len(pasados) > 1 else "")

    return {
        "observado_en": ahora, "fuente": "derivado", "viejo": any(d.get("viejo") for d in leidas),
        "dato_mas_viejo": dato_mas_viejo, "objetivo": objetivo, "otras_entregas": otras,
        "veredicto": {"valor": valor, "motivos": motivos, "gravedad": gravedad, "fuente": "derivado",
                      "observado_en": ahora},
        "estimacion": estimacion,
        "base": {"minimo": MINIMO, "desde": min(hechas_en, key=fecha, default=None), "personas": base_personas},
        "hechos": hechos, "cadena": cadena, "sin_plazo": sin_plazo, "fuera_de_entrega": fuera, "hitos": hitos,
        "descansos": descansos, "resumen": corta(" ".join(resumen.split()), RESUMEN_MAX)}


def firma(bloque):
    """Lo que firma `ruta:` en la cabecera del md (api.md §6, decisión 10A): solo el veredicto. La hora estimada, el
    margen o un hecho que cambian sin cambiar el veredicto no abren un delta."""
    return bloque["veredicto"]["valor"]
