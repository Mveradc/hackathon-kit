"""Vista de jurado (M10, R-35, ADR-0012, api.md §11.3): el bloque `jurado` de la vista. Puro: sin E/S, sin red, sin
git y sin reloj propio (`ahora` es un parámetro).

bloque(jurado, tareas, ahora, …) recibe lo que el relay deja en `estado.json` (K-104, `estado.schema.json`): `jurado`
(fichero, notas con su clave, pitch) y `tareas[]` (estado, declarado, criterios, conexiones, evidencia, fusion,
historia), y devuelve `$defs/vista_jurado`, ya ordenado, con su `cuenta` y su `resumen`.
- Nunca «cubierta» porque algo lo declare: una `cerrada` a mano (⚑), el pitch o una etiqueta ambigua no cubren.
- La evidencia se enseña siempre que exista; la Prueba es evidencia, no condición (decisión 4A).
- El texto de las notas es dato (constitución V): sale tal cual, sin interpretarlo.
"""
import copy

from estados import fecha

FUENTE_VIEJA_S = 300                                   # umbral_viejo_s por defecto, el de proyeccion
SIGUE_HECHA = ("en_curso", "en_revision", "integrada")  # decisión 6B: publicada antes, con trabajo nuevo
PALABRAS = ("obligatorio", "se valora", "nos gustaría ver")
LINEA_MAX = 160                                        # api.md §6
DE_FUENTE = {"git": "git", "github": "github"}         # fuente de una tarjeta → vista.fuentes; lo demás llega por el relay


def _norma(texto):
    return " ".join((texto or "").split()).casefold()


def _edad(ts, ahora):
    return (fecha(ahora) - fecha(ts)).total_seconds()


def _cuando(nota):
    """Por hora (o por cita, si no hay zona): la más antigua primero."""
    return (0, fecha(nota["hora"])) if nota.get("hora") else (1, nota["cita"])


def rango_fuerza(f):
    """dato, «obligatorio», «se valora», «nos gustaría ver», otra palabra, comentario suelto, sin precisar."""
    if f["tipo"] != "palabra":
        return {"dato": 0, "comentario": 5}.get(f["tipo"], 6)
    t = _norma(f["texto"])
    return 1 + PALABRAS.index(t) if t in PALABRAS else 4


def casan(cita, notas):
    """Las notas de esa «fecha hora» y, si la cita lleva «· quién», de ese quién (sin mayúsculas ni espacios de más)."""
    hora, _, quien = cita.partition(" · ")
    return [n for n in notas if n["cita"] == hora.strip() and (not quien.strip() or _norma(n["quien"]) == _norma(quien))]


def hecha(t):
    """publicada; cerrada no declarada; o publicada antes (historia.hecha_en) y ahora con trabajo nuevo (decisión 6B)."""
    e = t["estado"]
    if e["valor"] == "publicada" or (e["valor"] == "cerrada" and not e.get("declarado") and not t.get("declarado")):
        return True
    return e["valor"] in SIGUE_HECHA and bool((t.get("historia") or {}).get("hecha_en"))


def _viejas(fuentes, ahora, umbral):
    """{relay|github|git: viejo}: el `viejo` de vista.fuentes si viene; si no, la misma regla que proyeccion.vista."""
    salida = {}
    for k, d in (fuentes or {}).items():
        salida[k] = bool(d["viejo"]) if "viejo" in d else not (k == "github" and d["valor"] == "no") and (
            d["valor"] != "ok" or _edad(d["observado_en"], ahora) > umbral)
    return salida


def _tarjeta(t, tarjetas, viejas):
    if tarjetas and t["id"] in tarjetas:
        x = copy.deepcopy(tarjetas[t["id"]])
    else:
        from proyeccion import ETIQUETAS      # aquí y no arriba: proyeccion importa este módulo
        e = t["estado"]
        x = {"id": t["id"], "titulo": t["titulo"], "dueno": t["dueno"], "estado": e["valor"],
             "etiqueta": ETIQUETAS[e["valor"]], "fuente": e["fuente"], "observado_en": e["observado_en"]}
        if t.get("declarado"):
            x["declarado"] = t["declarado"]["valor"]
        if e.get("declarado"):
            x["estado_declarado"] = True
    x["viejo"] = viejas.get(DE_FUENTE.get(x["fuente"], "relay"), False)
    return x


def _evidencias(t, conexiones, viejas, ahora, umbral):
    """El commit o la fusión que la publicó y el último resultado de la Prueba de cada conexión suya."""
    salida = []
    if t.get("evidencia"):
        e, h = t["estado"], t.get("historia") or {}
        # La hora de la publicación que dejó esa evidencia: la del estado si sigue publicada (si se publicó otra vez,
        # la de la última); si no, historia.hecha_en.
        hora = e["observado_en"] if e["valor"] == "publicada" else h.get("hecha_en") or e["observado_en"]
        salida.append({"tipo": "fusion" if t.get("fusion") == t["evidencia"] else "commit", "tarea": t["id"],
                       "valor": t["evidencia"][:60], "fuente": "git", "observado_en": hora,
                       "viejo": viejas.get("git", False)})
    for clave in (t.get("conexiones") or {}).get("valor") or []:
        r = (conexiones.get(clave) or {}).get("resultado")
        if r:
            salida.append({"tipo": "prueba", "tarea": t["id"], "valor": r["valor"], "conexion": clave,
                           "fuente": r["fuente"], "observado_en": r["observado_en"],
                           "viejo": _edad(r["observado_en"], ahora) > umbral})
    return salida


def _resumen(fichero, cuenta):
    from proyeccion import corta
    if fichero == "sin fichero":
        return "jurado: sin criterios.md en main"
    if not cuenta["notas"]:
        return "jurado: sin notas en criterios.md"
    fuerte = cuenta["sin_cubrir_por_fuerza"][:1]
    partes = [f"{cuenta['sin_cubrir']} sin cubrir" + "".join(f" ({f['n']} «{f['texto']}»)" for f in fuerte)]
    if cuenta["ambiguas"]:
        partes.append(f"{cuenta['ambiguas']} ambigua" + "s" * (cuenta["ambiguas"] != 1))
    if cuenta["en_pitch"]:
        partes.append(f"{cuenta['en_pitch']} en el pitch")
    partes.append(f"{cuenta['cubiertas']} cubierta" + "s" * (cuenta["cubiertas"] != 1) + f" de {cuenta['notas']}")
    return corta("jurado: " + " · ".join(partes), LINEA_MAX)


def bloque(jurado, tareas, ahora, fuentes=None, servicios=None, umbral_viejo_s=FUENTE_VIEJA_S, tarjetas=None):
    """El bloque `jurado` de la vista ($defs/vista_jurado).

    jurado, tareas, servicios: los de estado.json; fuentes: las de estado.json o las de la vista (con `viejo`);
    tarjetas: {id: tarjeta de proyeccion.vista}, para que la tarjeta sea la misma que en el resto de la vista (sin
    ellas, se hace una con los campos de §6); ahora: ISO 8601, la hora del cálculo."""
    notas = jurado["notas"]
    viejas = _viejas(fuentes, ahora, umbral_viejo_s)
    conexiones = {c["clave"]: c for c in (servicios or {}).get("conexiones", [])}

    enlaces, sin_nota = {n["clave"]: {} for n in notas}, []
    for t in sorted(tareas, key=lambda t: t["id"]):
        c = t.get("criterios")
        for cita in (c or {}).get("valor") or []:
            casa = casan(cita, notas)
            if not casa:
                sin_nota.append({"tarea": t["id"], "cita": cita, "fuente": c["fuente"],
                                 "observado_en": c["observado_en"], "declarado": True})
            for n in casa:
                antes = enlaces[n["clave"]].get(t["id"])
                if antes is None or (antes[2] and len(casa) == 1):    # un enlace firme gana a uno ambiguo
                    enlaces[n["clave"]][t["id"]] = (t, cita, len(casa) > 1, c)

    pitch = jurado.get("pitch")
    en_pitch = set()
    for cita in (pitch or {}).get("valor") or []:
        casa = casan(cita, notas)
        if len(casa) == 1:
            en_pitch.add(casa[0]["clave"])

    corregida = {}
    for n in sorted(notas, key=_cuando):       # si varias corrigen la misma, cuenta la última
        casa = [m for m in casan(n["corrige"], notas) if m["clave"] != n["clave"]] if n.get("corrige") else []
        if len(casa) == 1 and _cuando(casa[0]) <= _cuando(n):
            corregida[casa[0]["clave"]] = n["clave"]

    salida = []
    for n in notas:
        es = list(enlaces[n["clave"]].values())
        firmes = [t for t, _, ambiguo, _ in es if not ambiguo]
        if firmes:
            valor = "cubierta" if all(hecha(t) for t in firmes) else "declarada"
        elif es:
            valor = "ambigua"
        else:
            valor = "en_pitch" if n["clave"] in en_pitch else "sin_tarea"
        filas = [{"tarjeta": _tarjeta(t, tarjetas, viejas),
                  "enlace": {"cita": cita, "ambiguo": ambiguo, "donde": "plan.md", "fuente": c["fuente"],
                             "observado_en": c["observado_en"], "declarado": True}} for t, cita, ambiguo, c in es]
        evidencias = [e for t, _, _, _ in es for e in _evidencias(t, conexiones, viejas, ahora, umbral_viejo_s)]
        # La hora del estado de sus tareas (como en la vista de ejemplo de §11.6); sin tareas, la del pitch o la nota.
        horas = [f["tarjeta"]["observado_en"] for f in filas] or [
            pitch["observado_en"] if valor == "en_pitch" else n["observado_en"]]
        nuevo = [t["historia"]["trabajo_nuevo_desde"] for t in firmes
                 if t["estado"]["valor"] in SIGUE_HECHA and hecha(t) and t["historia"].get("trabajo_nuevo_desde")]
        salida.append({
            "nota": copy.deepcopy(n),
            "cobertura": {"valor": valor, "fuente": "derivado", "observado_en": max(horas, key=fecha),
                          "viejo": any(f["tarjeta"]["viejo"] for f in filas)
                          or any(e["viejo"] for e in evidencias if e["tipo"] != "prueba")},
            "corregida_por": corregida.get(n["clave"]),
            "trabajo_nuevo_desde": min(nuevo, key=fecha) if nuevo else None,
            "tareas": filas,
            "evidencias": evidencias,
            "pitch": {"fuente": pitch["fuente"], "observado_en": pitch["observado_en"], "declarado": True}
            if n["clave"] in en_pitch else None})

    def orden(x):
        grupo = 2 if x["corregida_por"] else 1 if x["cobertura"]["valor"] == "cubierta" else 0
        return grupo, rango_fuerza(x["nota"]["fuerza"]) if grupo == 0 else 0, _cuando(x["nota"]), x["nota"]["clave"]
    salida.sort(key=orden)

    vivas = [x for x in salida if not x["corregida_por"]]
    sin_cubrir = [x for x in vivas if x["cobertura"]["valor"] != "cubierta"]
    por_fuerza = {}
    for x in sin_cubrir:                       # ya en orden de fuerza
        f = x["nota"]["fuerza"]
        por_fuerza.setdefault((rango_fuerza(f), _norma(f["texto"])), {"texto": f["texto"], "n": 0})["n"] += 1

    def cuantas(valor):
        return sum(x["cobertura"]["valor"] == valor for x in vivas)
    cuenta = {"notas": len(salida), "sin_cubrir": len(sin_cubrir), "sin_tarea": cuantas("sin_tarea"),
              "ambiguas": cuantas("ambigua"), "declaradas": cuantas("declarada"), "en_pitch": cuantas("en_pitch"),
              "cubiertas": cuantas("cubierta"), "corregidas": len(salida) - len(vivas),
              "sin_cubrir_por_fuerza": [por_fuerza[k] for k in sorted(por_fuerza, key=lambda k: k[0])]}
    fichero = (jurado.get("fichero") or {}).get("valor")
    resultado = {"observado_en": ahora, "fuente": "derivado", "viejo": viejas.get("git", False)}
    if fichero in ("ok", "sin fichero", "mal formado"):
        resultado["fichero"] = fichero
    resultado.update(cuenta=cuenta, notas=salida, sin_nota=sin_nota, resumen=_resumen(fichero, cuenta))
    return resultado
