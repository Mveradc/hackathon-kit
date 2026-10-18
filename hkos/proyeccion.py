"""Proyección del Hackathon OS (M8f, ADR-0006): estado.json → vista → web, estado-equipo.md y MCP. Puro, sin E/S.

Las tres vistas salen de aquí (constitución IV):
  - vista(estado, ahora): lo que pinta la web (el relay la sirve en /v1/vista y por SSE) y de lo que salen las otras dos;
  - markdown(vista, persona): estado-equipo.md (api.md §6), que escribe el demonio y leen sesion.sh y delta.sh;
  - firmas(vista, persona): una huella por sección, solo de lo que importa a la persona (sin horas), para delta.sh;
  - reservas_tsv(vista, persona): las reservas de las demás personas, para el aviso de reserva.sh (M8g).
El texto que viene del plan o de los issues (títulos, novedades) es dato: va entre «» y con su autor (constitución V).
"""
import hashlib
import json
import unicodedata
from datetime import timezone

from estados import fecha

ETIQUETAS = {"pendiente": "pendiente", "lista": "lista", "reclamada": "reclamada", "en_curso": "en curso",
             "parada": "parada", "en_revision": "en revisión", "integrada": "integrada (sin subir)",
             "no_cerrada": "no cerrada", "publicada": "publicada", "cerrada": "cerrada"}
COLUMNAS = {"haciendo": ("en_curso", "parada", "no_cerrada", "en_revision", "reclamada"),
            "hecho": ("integrada", "publicada", "cerrada"),
            "falta": ("lista", "pendiente")}
COLUMNA = {e: c for c, estados in COLUMNAS.items() for e in estados}
ORDEN = {e: i for i, e in enumerate(COLUMNAS["haciendo"] + COLUMNAS["hecho"] + COLUMNAS["falta"])}
# «Tu trabajo»: lo abierto de la persona, primero lo que tiene entre manos; publicada y cerrada ya no son trabajo.
TRABAJO = ("en_curso", "parada", "no_cerrada", "en_revision", "reclamada", "integrada", "lista", "pendiente")
CUMPLEN = {"publicada", "cerrada"}
PRESENCIA_VIEJA_S = 180                 # R-12: presencia con más de 3 minutos
FUENTE_VIEJA_S = 300                    # R-12: GitHub o relay con más de 5 (umbral_viejo_s de os.md)
NOVEDADES_MAX = 5
LINEA_MAX = 160                         # api.md §6
RESUMEN_MAX = 200                       # caracteres del resumen de una novedad (estado.schema.json)
SEP, SALTO = chr(9), chr(10)            # reservas.tsv: tabulador entre campos, una ruta por línea
ZWJ = "\u200d"


def _edad(ts, ahora):
    return max(0, int((fecha(ahora) - fecha(ts)).total_seconds()))


def vista(estado, ahora=None, umbral_viejo_s=FUENTE_VIEJA_S):
    """La vista del equipo, sin persona. `ahora` (por defecto, generado_en) solo decide qué está «viejo»."""
    ahora = ahora or estado["generado_en"]
    tareas = {t["id"]: t for t in estado["tareas"]}
    nombres = {p["persona"]: p["nombre"] for p in estado["personas"]}

    def tarjeta(t):
        e = t["estado"]
        x = {"id": t["id"], "titulo": t["titulo"], "dueno": t["dueno"], "estado": e["valor"],
             "etiqueta": ETIQUETAS[e["valor"]], "fuente": e["fuente"], "observado_en": e["observado_en"],
             "depende_de": list(t.get("depende_de", [])), "bloquea_a": [], "espera": []}
        if t.get("bloque"):
            x["bloque"] = t["bloque"]
        if t.get("issue"):
            x["issue"] = t["issue"]
        if t.get("declarado"):
            x["declarado"] = t["declarado"]["valor"]
        if e.get("declarado"):                 # M9a: el estado mismo es declarado (reclamada desde la web o el MCP)
            x["estado_declarado"] = True
        if t.get("cumplidas_por_cierre"):
            x["cumplidas_por_cierre"] = list(t["cumplidas_por_cierre"])
        if e["valor"] == "pendiente":
            for d in x["depende_de"]:
                dep = tareas.get(d)
                if dep is None:
                    x["espera"].append({"id": d, "dueno": None, "estado": "no existe"})
                elif dep["estado"]["valor"] not in CUMPLEN and d not in x.get("cumplidas_por_cierre", []):
                    x["espera"].append({"id": d, "dueno": dep["dueno"], "estado": dep["estado"]["valor"]})
        return x

    tarjetas = {tid: tarjeta(t) for tid, t in tareas.items()}
    for t in tarjetas.values():
        for d in t["depende_de"]:
            if d in tarjetas:
                tarjetas[d]["bloquea_a"].append(t["id"])
    columnas = {c: [] for c in COLUMNAS}
    for t in sorted(tarjetas.values(), key=lambda t: (ORDEN[t["estado"]], t["id"])):
        columnas[COLUMNA[t["estado"]]].append(t)

    personas = []
    for p in estado["personas"]:
        activos = [a for a in p["actores"] if a["activo"]]
        papeles = {}
        for a in activos:
            papeles[a["papel"]] = papeles.get(a["papel"], 0) + 1
        ultima = max((a["ultimo_latido"] for a in p["actores"]), key=fecha, default=None)
        haciendo = [t["id"] for t in columnas["haciendo"] if t["dueno"] == p["persona"]]
        x = {"persona": p["persona"], "nombre": p["nombre"], "activos": len(activos), "papeles": papeles,
             "haciendo": haciendo, "ultima_senal": ultima}
        x["viejo"] = ultima is None or _edad(ultima, ahora) > PRESENCIA_VIEJA_S
        personas.append(x)

    fuentes = {}
    for k, d in sorted(estado.get("fuentes", {}).items()):
        # `no` (M8h, modo sin GitHub): no hay sondeo que pueda envejecer; la hora es la del commit del plan.
        sin = k == "github" and d["valor"] == "no"
        fuentes[k] = {"valor": d["valor"], "observado_en": d["observado_en"],
                      "viejo": not sin and (d["valor"] != "ok" or _edad(d["observado_en"], ahora) > umbral_viejo_s)}
    colisiones = sorted(estado.get("colisiones", []), key=lambda c: (c["gravedad"] != "rojo", c["id"]))
    novedades = sorted(estado.get("novedades", []), key=lambda n: fecha(n["observado_en"]), reverse=True)
    salida = {"v": 1, "generado_en": estado["generado_en"], "ahora": ahora, "fuentes": fuentes,
              "umbrales": {"presencia_s": PRESENCIA_VIEJA_S, "fuente_s": umbral_viejo_s},
              "columnas": columnas, "colisiones": [dict(c) for c in colisiones],
              "sin_tarea": sorted(estado.get("sin_tarea", []), key=lambda s: fecha(s["observado_en"]), reverse=True),
              "personas": personas, "nombres": nombres, "novedades": novedades[:NOVEDADES_MAX],
              "reservas": sorted(estado.get("reservas", []), key=lambda r: (r["hasta"], r.get("id", "")))}
    if estado.get("servicios"):                # M9a (ADR-0011): tal cual; la persona lo filtra servicios_de()
        salida["servicios"] = s = json.loads(json.dumps(estado["servicios"]))
        # Decisión 1 del PR #13. Lo de git lleva la hora del commit de servicios.md: su antigüedad la dice fuentes.git.
        def viejo(d):
            return _edad(d["observado_en"], ahora) > umbral_viejo_s
        for x in s["lista"]:
            if x.get("comprobado"):
                x["comprobado"]["viejo"] = viejo(x["comprobado"])
        for x in s["conexiones"]:
            if x.get("resultado"):
                x["resultado"]["viejo"] = viejo(x["resultado"])
        for d in s["desajustes"]:
            d["viejo"] = d["fuente"] != "git" and viejo(d)
    return salida


# --- vistas de una persona ---

def trabajo(v, persona):
    """Tarjetas abiertas de la persona, en el orden de TRABAJO."""
    todas = [t for c in v["columnas"].values() for t in c if t["dueno"] == persona and t["estado"] in TRABAJO]
    return sorted(todas, key=lambda t: (TRABAJO.index(t["estado"]), t["id"]))


def colisiones_de(v, persona):
    return [c for c in v["colisiones"] if persona in c["personas"]]


def reservas_de_otros(v, persona):
    """Las reservas vigentes de las demás personas (M8g): las que pueden avisar a esta."""
    return [r for r in v.get("reservas", []) if r["persona"] != persona]


def servicios_de(v, persona):
    """Lo de servicios que afecta a la persona (api.md §6, M9a), en el orden de la sección: lo que no cuadra (sus
    servicios y las conexiones de las que es un extremo; lo del fichero entero, a todos), lo que espera su confirmación
    (filas sin confirmar y propuestas) y una línea, para todos, con el código fuera de cualquier servicio.
    [{grupo, texto, clave, observado_en, fuente, viejo}]: `texto` sin hora; `clave` es lo que firma (sin horas ni
    `viejo`: el paso del tiempo no es un cambio)."""
    s = v.get("servicios")
    if not s:
        return []
    no_cuadra, sin_confirmar, fuera = [], [], []
    for d in s["desajustes"]:
        x = {"observado_en": d["observado_en"], "fuente": d["fuente"], "viejo": bool(d.get("viejo"))}
        if d["tipo"] == "codigo_fuera":
            rutas = d.get("rutas", [])
            mas = f" y {len(rutas) - 2} más" if len(rutas) > 2 else ""
            fuera.append(dict(x, grupo="fuera de servicios", texto=" y ".join(rutas[:2]) if len(rutas) <= 2
                              else ", ".join(rutas[:2]) + mas, clave=["codigo_fuera", sorted(rutas)]))
        elif persona in d.get("personas", []) or not d.get("personas"):
            no_cuadra.append(dict(x, grupo="no cuadra", texto=d["detalle"], clave=[d["tipo"], d.get("clave"), d["detalle"]]))
    filas = [("servicio", f"«{x['nombre']}»", x) for x in s["lista"]] + \
            [("conexión", f"«{x['de']} → {x['a']}»", x) for x in s["conexiones"]]
    for tipo, nombre, x in filas:
        c = x["confirmacion"]
        if c["valor"] == "sin_confirmar" and persona in c["faltan"]:
            por = ", ".join("@" + p for p in c["por"]) or "nadie del equipo conocido"
            sin_confirmar.append({"grupo": "sin confirmar", "texto": f"{tipo} {nombre} · cambio de {por}",
                                  "clave": ["fila", x["clave"]], "observado_en": c["observado_en"], "fuente": c["fuente"],
                                  "viejo": False})
    for p in s["propuestas"]:
        if persona in p.get("duenos", []) and p.get("autor_git") != persona:
            c = p["campos"]
            nombre = f"servicio «{c.get('nombre') or ''}»" if p["tipo"] == "servicio" else \
                f"conexión «{c.get('de') or ''} → {c.get('a') or ''}»"
            sin_confirmar.append({"grupo": "sin confirmar", "texto": f"propuesta de {nombre} · de {autor_propuesta(p)}",
                                  "clave": ["propuesta", p["clave"]], "observado_en": p["observado_en"], "fuente": "git",
                                  "viejo": False})
    return no_cuadra + sin_confirmar + fuera


def autor_propuesta(p):
    """Quién propone (constitución II): la persona del commit; sin ella, el Autor de la fila, como declarado
    (decisión 3A del PR #13)."""
    if p.get("autor_git"):
        return f"@{p['autor_git']}"
    return f"{p['autor_declarado']} (declarado)" if p.get("autor_declarado") else "sin autor"


def _huella(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def firmas(v, persona):
    """Una huella por sección que delta.sh compara con lo entregado (R-25). Sin horas: el paso del tiempo no es un
    cambio. «Tu trabajo» incluye de quién espera cada tarea pendiente y en qué estado, para que una dependencia que
    pasa a `parada` llegue como cambio. «Equipo» (la presencia de los demás) no tiene firma: nunca abre un delta."""
    salida = {
        "trabajo": _huella([[t["id"], t["estado"], t.get("declarado"), t.get("cumplidas_por_cierre", []),
                             [[e["id"], e["dueno"], e["estado"]] for e in t["espera"]]]
                            + (["declarado"] if t.get("estado_declarado") else []) for t in trabajo(v, persona)]),
        "colisiones": _huella([[c["id"], c["nivel"], c["gravedad"], sorted(c["personas"]), sorted(c["rutas"]),
                                c.get("contrato")] for c in colisiones_de(v, persona)]),
        "novedades": _huella([[n.get("tipo"), n.get("resumen"), n.get("autor"), n["observado_en"]] for n in v["novedades"]]),
        "reservas": _huella([[sorted(r["rutas"]), r["persona"], r["modo"]] for r in reservas_de_otros(v, persona)]),
    }
    if v.get("servicios"):                     # M9a: solo con servicios en el estado
        salida["servicios"] = _huella([x["clave"] for x in servicios_de(v, persona)])
    return salida


def _hora(ts, tz):
    return fecha(ts).astimezone(tz).strftime("%H:%M")


def _pega(antes, c):
    """¿Va c en el mismo grafema que `antes` (el que se está formando)? UAX #29 simplificado, con unicodedata: detrás
    de un ZWJ, una marca combinante (con los selectores de variante), un modificador de tono, una etiqueta (U+E0020–
    E007F) o el segundo indicador regional de un par no hay corte."""
    o = ord(c)
    return (antes[-1] == ZWJ or c == ZWJ or unicodedata.category(c) in ("Mn", "Mc", "Me") or 0x1F3FB <= o <= 0x1F3FF
            or 0xE0020 <= o <= 0xE007F or (len(antes) == 1 and _regional(antes) and _regional(c)))


def _regional(c):
    return 0x1F1E6 <= ord(c) <= 0x1F1FF


def grafemas(texto):
    """Los grafemas de texto, uno a uno (issue #23: ningún recorte los parte)."""
    actual = ""
    for c in texto:
        if actual and _pega(actual, c):
            actual += c
            continue
        if actual:
            yield actual
        actual = c
    if actual:
        yield actual


def corta(texto, n, marca="…"):
    """texto en n caracteres como mucho (con la marca, si se corta), sin partir grafemas."""
    if len(texto) <= n:
        return texto
    salida, largo = [], len(marca)
    for g in grafemas(texto[:n + 1]):      # el grafema que pasa de n no cabe, aunque siga más allá
        if largo + len(g) > n:
            break
        salida.append(g)
        largo += len(g)
    return "".join(salida) + marca


def _abiertas(texto):
    """Las « que quedan sin cerrar (una » de más no cuenta)."""
    prof = 0
    for c in texto:
        if c == "«":
            prof += 1
        elif c == "»" and prof:
            prof -= 1
    return prof


def equilibra(texto, n):
    """El resumen de una novedad tal como lo enseñan todas las vistas (issue #23). Lo calcula el relay, en origen, y la
    web y el md lo pintan igual entre «» y con su autor detrás (constitución IV y V, ADR-0009): espacios normalizados,
    sin » sueltas (una » sin su « se quita), cada « abierta cerrada al final y en n caracteres como mucho, contando esos
    cierres y sin partir grafemas."""
    salida, prof = [], 0
    for c in " ".join(texto.split()):
        if c == "»":
            if not prof:
                continue
            prof -= 1
        elif c == "«":
            prof += 1
        salida.append(c)
    texto = " ".join("".join(salida).split())
    corte, m = corta(texto, n, ""), n
    while len(corte) + _abiertas(corte) > n:
        m -= 1
        corte = corta(texto, m, "")
    return corte + "»" * _abiertas(corte)


def _linea(texto):
    return corta(" ".join(texto.split()), LINEA_MAX)


def _entrecomilla(texto, n):
    """«texto», recortado a n caracteres antes de entrecomillarlo, sin partir grafemas. El texto ya llega equilibrado
    del relay (equilibra), así que solo se recorta: cada « que el recorte deja abierta se cierra antes de la » de fuera
    y el texto no se lleva dentro lo que va detrás, como el autor (constitución V, nota del PR #16)."""
    corte = corta(" ".join(texto.split()), n)
    return "«" + corte + "»" * _abiertas(corte) + "»"


def _cuando(x, ahora, tz, vieja_s=None):
    viejo = vieja_s is not None and _edad(x["observado_en"], ahora) > vieja_s
    return f"{_hora(x['observado_en'], tz)} · {x['fuente']}" + (" · viejo" if viejo else "")


def lineas_tarea(t, v, tz):
    """Una línea de «Tu trabajo»: «T07 «…» · en curso (18:40 · hook) · bloquea a T09»."""
    declarado = " · declarado" if t.get("estado_declarado") else ""
    texto = f"{t['id']} «{corta(t['titulo'], 70)}» · {t['etiqueta']} ({_cuando(t, v['ahora'], tz)}{declarado})"
    if t.get("declarado"):
        texto += f" · ⚑ {ETIQUETAS.get(t['declarado'], t['declarado'])} a mano"
    for d in t.get("cumplidas_por_cierre", []):
        texto += f" · ⚑ {d} cerrada a mano"
    if t["espera"]:
        texto += " · espera a " + ", ".join(
            f"{e['id']} ({'@' + e['dueno'] + ', ' if e['dueno'] else ''}{ETIQUETAS.get(e['estado'], e['estado'])})"
            for e in t["espera"])
    if t["bloquea_a"]:
        texto += " · bloquea a " + ", ".join(t["bloquea_a"])
    return "- " + _linea(texto)


def linea_colision(c, tz):
    que = f" · contrato «{corta(c['contrato'], 40)}»" if c.get("contrato") else ""
    rutas = ", ".join(c["rutas"][:3]) + (f" (+{len(c['rutas']) - 3})" if len(c["rutas"]) > 3 else "")
    personas = ", ".join("@" + p for p in c["personas"])
    return "- " + _linea(f"{c['gravedad'].upper()} · nivel {c['nivel']}{que} · {rutas} · {personas} "
                         f"({_hora(c['observado_en'], tz)})")


def linea_reserva(r, tz):
    rutas = ", ".join(f"«{x}»" for x in r["rutas"][:4]) + (f" (+{len(r['rutas']) - 4})" if len(r["rutas"]) > 4 else "")
    return "- " + _linea(f"{rutas} · @{r['persona']} · hasta {_hora(r['hasta'], tz)} · {r['modo']}")


def reservas_tsv(v, persona, tz):
    """reservas.tsv (M8g, api.md §7): una línea por ruta reservada por otra persona, para reserva.sh, que solo usa
    builtins de bash: id, ruta, persona, hasta (época), hasta (HH:MM) y modo, separados por tabuladores."""
    lineas = []
    for r in reservas_de_otros(v, persona):
        hasta = fecha(r["hasta"])
        for ruta in r["rutas"]:
            campos = [r.get("id", ""), ruta, r["persona"], str(int(hasta.timestamp())), _hora(r["hasta"], tz), r["modo"]]
            lineas.append(SEP.join(c.replace(SEP, " ").replace(SALTO, " ") for c in campos))
    return "".join(l + SALTO for l in lineas)


def linea_servicio(x, tz):
    """«- no cuadra · «datos» :8001 declarado, no responde (18:40 · demonio)» (api.md §6, M9a), con «· viejo» detrás
    de la fuente si lo es (decisión 1 del PR #13)."""
    viejo = " · viejo" if x.get("viejo") else ""
    return "- " + _linea(f"{x['grupo']} · {x['texto']} ({_hora(x['observado_en'], tz)} · {x['fuente']}{viejo})")


def linea_novedad(n, tz):
    tipo = {"decision": "decisión", "criterio": "criterio", "escalado": "escalado"}.get(n.get("tipo"), n.get("tipo", ""))
    cabeza = " ".join(f"{_hora(n['observado_en'], tz)} · {tipo} ·".split()) + " "
    autor = f" ({' '.join(n['autor'].split())})" if n.get("autor") else ""
    # El resumen se recorta (110 como mucho) para que la línea entera, con sus comillas y el autor, quepa en LINEA_MAX:
    # si la cortara _linea, se perdería la » de fuera y el autor. Antes, equilibra: el relay ya lo hace, y esto es la red
    # por si el relay es viejo (decisión 17B del PR #13; con uno nuevo no cambia nada, es idempotente).
    resumen = equilibra(n.get("resumen", ""), RESUMEN_MAX)
    sitio, largo = LINEA_MAX - len(cabeza) - len(autor), 110
    cita = _entrecomilla(resumen, largo)
    while len(cita) > sitio and largo > 1:
        largo -= 1
        cita = _entrecomilla(resumen, largo)
    return "- " + _linea(cabeza + cita + autor)


def linea_persona(p, v, tz):
    partes = [f"@{p['persona']} ({p['nombre']})"]
    if p["haciendo"]:
        partes.append(", ".join(f"{tid} {_etiqueta_de(v, tid)}" for tid in p["haciendo"][:4]))
    if p["activos"]:
        sesiones = sum(n for papel, n in p["papeles"].items() if papel not in ("worker", "revisor"))
        partes.append(f"{sesiones} sesión" + ("" if sesiones == 1 else "es"))
        if p["papeles"].get("worker"):
            partes.append(f"{p['papeles']['worker']} worker" + ("" if p["papeles"]["worker"] == 1 else "s"))
        partes.append(f"última señal {_hora(p['ultima_senal'], tz)}")
    elif p["ultima_senal"]:
        partes.append(f"sin sesión desde {_hora(p['ultima_senal'], tz)}")
    else:
        partes.append("sin sesión")
    return "- " + _linea(" · ".join(partes))


def _etiqueta_de(v, tid):
    for c in v["columnas"].values():
        for t in c:
            if t["id"] == tid:
                return t["etiqueta"]
    return ""


def avisos(v, tz):
    """Fuentes viejas (R-12, R-29): una línea cada una, antes de las secciones."""
    salida = []
    for k, d in v["fuentes"].items():
        if k == "github" and d["valor"] == "no":
            salida.append(f"> Sin GitHub: las tareas salen de plan.md de main ({_hora(d['observado_en'], tz)}); "
                          "sin asignar ni cerrar issues.")
        elif d["viejo"] and k != "git":
            nombre = {"relay": "Relay (lo efímero: presencia, ficheros)", "github": "GitHub (tareas)"}.get(k, k)
            salida.append(f"> {nombre}: sin datos nuevos desde {_hora(d['observado_en'], tz)} ({d['valor']}).")
    return salida


def markdown(v, persona, ruta_detalle, tz=None, epoch=None, relay=None, avisos_locales=None):
    """estado-equipo.md de una persona (api.md §6). `relay` = (estado, desde) si el demonio no llega al relay: el md
    lo dice aunque estado.json no lo sepa (es la última copia que recibió). `epoch` = cuándo se escribió (para que
    sesion.sh sepa si el demonio sigue vivo). `avisos_locales`: líneas «>» del demonio que no están en estado.json (M8g:
    por qué no publica el trabajo en curso)."""
    tz = tz or timezone.utc
    f = firmas(v, persona)
    relay_ok = "ok" if relay is None else "viejo"
    github = v["fuentes"].get("github")
    cabecera = (f"<!-- hk-os v1 persona={persona} generado_en={v['generado_en']} hora={_hora(v['ahora'], tz)} "
                f"epoch={epoch if epoch is not None else int(fecha(v['ahora']).timestamp())} relay={relay_ok} "
                f"github={'no' if github and github['valor'] == 'no' else 'viejo' if github and github['viejo'] else 'ok'} "
                f"firmas=trabajo:{f['trabajo']},colisiones:{f['colisiones']},novedades:{f['novedades']},"
                f"reservas:{f['reservas']}" + (f",servicios:{f['servicios']}" if "servicios" in f else "") + " -->")
    lineas = [cabecera]
    if relay is not None:
        lineas.append(f"> Relay sin respuesta desde {_hora(relay[1], tz)}: lo efímero (presencia, ficheros) puede estar viejo.")
    lineas += avisos(v, tz)
    lineas += [_linea(a) for a in avisos_locales or []]
    lineas.append("## Tu trabajo")
    lineas += [lineas_tarea(t, v, tz) for t in trabajo(v, persona)] or ["- nada abierto"]
    lineas.append("## Colisiones que te afectan")
    lineas += [linea_colision(c, tz) for c in colisiones_de(v, persona)] or ["- ninguna"]
    lineas.append("## Reservas")
    lineas += [linea_reserva(r, tz) for r in reservas_de_otros(v, persona)] or ["- ninguna"]
    if v.get("servicios"):                     # M9a (api.md §6)
        lineas.append("## Servicios")
        lineas += [linea_servicio(x, tz) for x in servicios_de(v, persona)] or ["- todo cuadra"]
    lineas.append("## Novedades")
    lineas += [linea_novedad(n, tz) for n in v["novedades"]] or ["- ninguna"]
    lineas.append("## Equipo")
    lineas += [linea_persona(p, v, tz) for p in v["personas"] if p["persona"] != persona] or ["- nadie más"]
    lineas.append("## Detalle")
    lineas.append(f"Ruta: {ruta_detalle}")
    return "\n".join(lineas) + "\n"


def tarea(estado, v, tid):
    """Lo que devuelve el MCP `tarea`: la tarea de estado.json, su columna y su antigüedad."""
    for t in estado["tareas"]:
        if t["id"] == tid:
            return {"tarea": t, "columna": COLUMNA[t["estado"]["valor"]],
                    "antiguedad_s": _edad(t["estado"]["observado_en"], v["ahora"]),
                    "generado_en": v["generado_en"]}
    return None


def con_hora(v, servido_en):
    """El cuerpo de /v1/vista y del evento SSE `vista`: la vista y la hora del relay al servirla, con la que la web
    calcula «hace X» sin fiarse del reloj del dispositivo."""
    return {"servido_en": servido_en, "vista": v}

