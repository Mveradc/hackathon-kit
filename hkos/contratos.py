"""Nivel 3 de colisiones (M8g, R-21, ADR-0007): un contrato de docs/contratos.md tocado por quien no es su dueño. Puro.

- Bloques: cada `## <nombre>` de docs/contratos.md con su línea `Vive en: a, b` (M8a).
- Dueño, de .hackathon/autoridad.md (las secciones `### <Nombre> (@usuario) · \\`carpetas\\``):
    1. la persona con una fila «`docs/contratos.md`: <x>» cuyo <x> coincide con el nombre del bloque (normalizados:
       minúsculas, sin puntuación; vale que uno contenga al otro);
    2. si no hay fila, la persona cuyas carpetas contienen las rutas de `Vive en:` (gana el prefijo más largo).
  Con más de una candidata, o con ninguna, el bloque no tiene dueño y no da nivel 3 (el relay lo dice una vez).
- Tocar el contrato: tener cambiada una ruta de `Vive en:`, o traer su nombre en `datos.contratos` de un `arbol`
  (los títulos `##` de docs/contratos.md que tocan los cambios, M8g). Avisa al dueño, a quien lo toca y al resto del
  equipo (los consumidores, decisión del usuario en M8g).
El texto de los dos ficheros es dato: solo se usan nombres, rutas y usuarios.
"""
import re

from estados import fecha

CONTRATOS = "docs/contratos.md"
SECCION = re.compile(r"^###\s+(.+?)\s*\(([^)]*)\)\s*(?:·\s*(.*))?$")
USUARIO = re.compile(r"@([A-Za-z0-9-]+)")


def normal(texto):
    """Nombre comparable: minúsculas, sin puntuación ni flechas, espacios simples."""
    return " ".join(re.sub(r"[^\w]+", " ", texto.lower()).split())


def _rutas(texto):
    salida = []
    for r in texto.split(","):
        r = r.strip().strip("`").strip().replace("\\", "/")
        while r.startswith("./"):
            r = r[2:]
        if r and "fuera del repo" not in r.lower() and r.lower() != CONTRATOS and "<" not in r:
            salida.append(r)
    return salida


def bloques(texto):
    """[{nombre, rutas}] de docs/contratos.md. Un bloque sin «Vive en:» va con rutas vacías (solo se toca por título)."""
    salida, actual, en_codigo = [], None, False
    for linea in (texto or "").splitlines():
        l = linea.strip()
        if l.startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        if linea.startswith("## "):
            actual = {"nombre": linea[3:].strip(), "rutas": []}
            salida.append(actual)
        elif actual is not None and l.lower().startswith("vive en:"):
            actual["rutas"] += _rutas(l[len("vive en:"):])
    return salida


def secciones(texto):
    """[{nombre, persona|None, carpetas, filas}] de autoridad.md: una por `### Persona (@usuario) · carpetas`.
    `filas`: el texto tras «docs/contratos.md:» de su tabla."""
    salida, actual = [], None
    for linea in (texto or "").splitlines():
        if linea.startswith("## "):
            actual = None
            continue
        m = SECCION.match(linea.strip()) if linea.startswith("### ") else None
        if m:
            u = USUARIO.search(m.group(2))
            actual = {"nombre": m.group(1).strip(), "persona": u.group(1).lower() if u else None,
                      "carpetas": _rutas(m.group(3) or ""), "filas": []}
            salida.append(actual)
        elif actual is not None and linea.lstrip().startswith("|"):
            celda = linea.strip().strip("|").split("|")[0]
            plana = celda.replace("`", "")
            i = plana.lower().find(CONTRATOS + ":")
            if i >= 0:
                actual["filas"].append(plana[i + len(CONTRATOS) + 1:].strip())
    return salida


def _bajo(ruta, base):
    r, b = ruta.lower().rstrip("/"), base.lower().rstrip("/")
    return r == b or r.startswith(b + "/")


def duenos(texto_contratos, texto_autoridad):
    """([{nombre, rutas, dueno, con_github}], avisos): los bloques con dueño y una línea por bloque que se queda sin él."""
    secs = secciones(texto_autoridad)
    con_dueno, avisos = [], []
    for b in bloques(texto_contratos):
        n = normal(b["nombre"])
        por_fila = {id(s): s for s in secs for f in s["filas"] if f and (normal(f) in n or n in normal(f))}
        candidatas = list(por_fila.values())
        como = "por su fila en autoridad.md"
        if not candidatas and b["rutas"]:
            de_ruta = []
            for r in b["rutas"]:
                mejor = [(len(c), s) for s in secs for c in s["carpetas"] if _bajo(r, c)]
                if not mejor:
                    de_ruta = []
                    break
                largo = max(x[0] for x in mejor)
                de_ruta += [s for l, s in mejor if l == largo]
            candidatas = list({id(s): s for s in de_ruta}.values())
            como = "por las carpetas de autoridad.md"
        if len(candidatas) != 1:
            que = "más de una persona" if candidatas else "ninguna persona"
            avisos.append(f"contrato «{b['nombre'][:60]}»: {que} como dueña ({como}); sin nivel 3 para él")
            continue
        s = candidatas[0]
        con_dueno.append({"nombre": b["nombre"], "rutas": b["rutas"], "dueno": s["persona"] or s["nombre"],
                          "con_github": s["persona"] is not None})
    return con_dueno, avisos


def nivel3(contratos, conjuntos, equipo):
    """Colisiones rojas de nivel 3. `conjuntos`: los de colisiones.ficheros; `equipo`: usuarios de coordinacion.md."""
    salida = []
    for c in contratos:
        n = normal(c["nombre"])
        for persona in sorted(conjuntos):
            if persona == c["dueno"] or persona not in equipo:
                continue
            p = conjuntos[persona]
            tocadas = {ruta: desde for ruta, desde in p["rutas"].values() if any(_bajo(ruta, v) for v in c["rutas"])}
            for nombre, desde in p["contratos"].items():
                if normal(nombre) == n:
                    tocadas[CONTRATOS] = min(desde, tocadas.get(CONTRATOS, desde), key=fecha)
            if not tocadas:
                continue
            avisar = [persona] + ([c["dueno"]] if c["con_github"] and c["dueno"] in equipo else [])
            avisar += sorted(x for x in equipo if x not in avisar)
            salida.append({"id": f"3:{n}:{persona}", "nivel": "3", "gravedad": "rojo", "personas": avisar,
                           "rutas": sorted(tocadas, key=str.lower), "contrato": c["nombre"][:120],
                           "observado_en": max(tocadas.values(), key=fecha)})
    return salida
