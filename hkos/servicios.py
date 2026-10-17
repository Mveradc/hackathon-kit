"""Servicios del equipo (M9a, ADR-0011, api.md §10): .hackathon/servicios.md → `servicios` de estado.json. Puro, sin E/S.

- leer(texto): las cuatro tablas (Servicios, Conexiones y sus Propuestas), «Fuera de servicios:» y lo mal formado.
- confirmaciones(versiones, sha_persona): quién añadió cada fila (por su clave) en la historia del fichero. La persona
  de un commit sale solo de los eventos `commit` de los demonios (sha → persona), nunca del autor de git: un sha
  desconocido (rebase, squash, un merge) no confirma nada.
- calcular(…): el bloque `servicios` de estado.json (estado.schema.json), con la confirmación y los desajustes.
«Confirmada» = hecha desde el portátil del dueño (o de los dos dueños, en una conexión), no decidida por una persona.
Lo que hay en el fichero (nombres, comandos, contratos) es dato del equipo: el OS nunca ejecuta Arranque ni Prueba.
"""
import hashlib
import json
import re

import contratos

SERVICIOS, CONEXIONES = "## Servicios", "## Conexiones"
PROP_SERVICIOS, PROP_CONEXIONES = "## Propuestas de servicios", "## Propuestas de conexiones"
COLUMNAS_S = ("Nombre", "Carpeta", "Puerto", "Arranque", "Salud", "Dueño")
CAMPOS_S = ("nombre", "carpeta", "puerto", "arranque", "salud", "dueno")
COLUMNAS_C = ("De", "A", "Contrato", "Prueba")
CAMPOS_C = ("de", "a", "contrato", "prueba")
AUTORIA = ("Autor", "Hora")
TABLAS = {   # título → (tipo, es propuesta, columnas, campos)
    SERVICIOS: ("servicio", False, COLUMNAS_S, CAMPOS_S),
    CONEXIONES: ("conexion", False, COLUMNAS_C, CAMPOS_C),
    PROP_SERVICIOS: ("servicio", True, COLUMNAS_S + AUTORIA, CAMPOS_S),
    PROP_CONEXIONES: ("conexion", True, COLUMNAS_C + AUTORIA, CAMPOS_C),
}
NOMBRE_TABLA = {SERVICIOS: "Servicios", CONEXIONES: "Conexiones", PROP_SERVICIOS: "Propuestas de servicios",
                PROP_CONEXIONES: "Propuestas de conexiones"}
FUERA = "fuera de servicios:"
SIEMPRE_FUERA = (".hackathon/", ".claude/", ".github/")
NOMBRE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
SALUD = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/?-]*$")
USUARIO = re.compile(r"^@([A-Za-z0-9-]+)$")
HORA = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
SEPARADOR = re.compile(r"^:?-{3,}:?$")
TEXTO_MAX = 300
RUTAS_MAX = 50


def decodificar(datos):
    """Bytes del fichero → texto, tolerando BOM y UTF-16 (como hk_leer)."""
    if datos.startswith((b"\xff\xfe", b"\xfe\xff")):
        return datos.decode("utf-16")
    return datos.decode("utf-8-sig", errors="replace")


def _celdas(linea):
    partes = re.split(r"(?<!\\)\|", linea.strip())
    if partes and partes[0].strip() == "":
        partes = partes[1:]
    if partes and partes[-1].strip() == "":
        partes = partes[:-1]
    return [p.strip().replace("\\|", "|") for p in partes]


def _valor(celda):
    """Celda normalizada: recortada, sin las comillas invertidas de alrededor; vacía o «—» es None."""
    c = celda.strip()
    if len(c) >= 2 and c.startswith("`") and c.endswith("`"):
        c = c[1:-1].strip()
    return None if c in ("", "—", "-") else c


def _huella(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()[:12]


def huella_prueba(prueba):
    """`comando_sha` de una Prueba (api.md §1): sha256 del comando normalizado, 12 hex."""
    return hashlib.sha256(prueba.encode("utf-8")).hexdigest()[:12]


def _puerto(v):
    if v is not None and v.isdigit() and 1 <= int(v) <= 65535:
        return int(v)
    return None


def _invalidos(tipo, campos):
    """Los campos que no valen, con el motivo («Salud «http://x» no es una ruta»)."""
    malos = []
    if tipo == "servicio":
        if not campos["nombre"] or not NOMBRE.match(campos["nombre"]):
            malos.append(f"Nombre «{campos['nombre'] or ''}» no vale")
        c = campos["carpeta"]
        if not c or not c.endswith("/") or c.startswith("/") or ".." in c.split("/") or "\\" in c:
            malos.append(f"Carpeta «{c or ''}» no es una carpeta relativa acabada en /")
        if campos["puerto"] is not None and _puerto(campos["puerto"]) is None:
            malos.append(f"Puerto «{campos['puerto']}» no es un número de 1 a 65535")
        s = campos["salud"]
        if s is not None and (not SALUD.match(s) or ".." in s or s.startswith("//")):
            malos.append(f"Salud «{s}» no es una ruta que empieza por /")
        if campos["dueno"] is not None and not USUARIO.match(campos["dueno"]):
            malos.append(f"Dueño «{campos['dueno']}» no es un @usuario")
        largos = ("arranque",)
    else:
        for k, col in (("de", "De"), ("a", "A")):
            if not campos[k] or not NOMBRE.match(campos[k]):
                malos.append(f"{col} «{campos[k] or ''}» no es un nombre de servicio")
        largos = ("contrato", "prueba")
    for k in largos:
        if campos[k] is not None and len(campos[k]) > TEXTO_MAX:
            malos.append(f"{k} de más de {TEXTO_MAX} caracteres")
    return malos


def clave(tipo, campos):
    """Clave de una fila (api.md §10): sus campos normalizados en el orden de su tabla (el puerto, como número)."""
    orden = CAMPOS_S if tipo == "servicio" else CAMPOS_C
    valores = [campos[k] for k in orden]
    if tipo == "servicio":
        p = _puerto(campos["puerto"])
        valores[2] = p if p is not None else campos["puerto"]
    return _huella(valores)


def leer(texto):
    """{filas, fuera, errores}. Cada fila: {tabla, tipo, propuesta, campos, clave, invalidos, linea, autor, hora}.
    `errores`: lo que hace el fichero «mal formado» (cabecera distinta, número de celdas, nombre repetido)."""
    filas, fuera, errores = [], [], []
    tabla, cabecera = None, False
    for n, linea in enumerate((texto or "").splitlines(), 1):
        l = linea.strip()
        if l.startswith("## "):
            tabla = l if l in TABLAS else None
            cabecera = False
            continue
        if l.lower().startswith(FUERA):
            for r in l[len(FUERA):].split(","):
                r = r.strip().strip("`").strip().replace("\\", "/")
                while r.startswith("./"):
                    r = r[2:]
                if r:
                    fuera.append(r)
            continue
        if tabla is None or not l.startswith("|"):
            continue
        tipo, propuesta, columnas, campos_t = TABLAS[tabla]
        celdas = _celdas(l)
        if not cabecera:
            cabecera = True
            if [c.lower() for c in celdas] != [c.lower() for c in columnas]:
                errores.append((n, f"la cabecera de «{NOMBRE_TABLA[tabla]}» no es {' | '.join(columnas)}"))
                tabla = None
            continue
        if all(SEPARADOR.match(c) for c in celdas if c):
            continue
        if len(celdas) != len(columnas):
            errores.append((n, f"fila de «{NOMBRE_TABLA[tabla]}» con {len(celdas)} celdas en vez de {len(columnas)}"))
            continue
        valores = [_valor(c) for c in celdas]
        campos = dict(zip(campos_t, valores))
        autor, hora = (valores[-2], valores[-1]) if propuesta else (None, None)
        invalidos = _invalidos(tipo, campos)
        if propuesta:
            if autor is not None and not USUARIO.match(autor):
                invalidos.append(f"Autor «{autor}» no es un @usuario")
            if hora is not None and not HORA.match(hora):
                invalidos.append(f"Hora «{hora}» no es AAAA-MM-DD HH:MM")
        filas.append({"tabla": tabla, "tipo": tipo, "propuesta": propuesta, "campos": campos,
                      "clave": clave(tipo, campos), "invalidos": invalidos, "linea": n, "autor": autor, "hora": hora})
    vistos = set()
    for f in filas:
        if f["tabla"] == SERVICIOS and f["campos"]["nombre"]:
            if f["campos"]["nombre"] in vistos:
                errores.append((f["linea"], f"servicio «{f['campos']['nombre']}» repetido"))
            vistos.add(f["campos"]["nombre"])
    return {"filas": filas, "fuera": fuera, "errores": errores}


def _conjunto(texto):
    return {(f["tabla"], f["clave"]) for f in leer(texto)["filas"]}


def personas_de_commits(eventos):
    """{sha: persona} de los eventos `commit` (los emite el sondeo de git de cada demonio con su persona, también los
    de sus workers, rama `worktree-agent-*`). Solo esto atribuye un commit: nunca el autor de git."""
    salida = {}
    for e in eventos:
        sha = (e.get("datos") or {}).get("sha")
        if e.get("tipo") == "commit" and sha:
            salida[sha] = e["actor"]["persona"]
    return salida


def confirmaciones(versiones, sha_persona):
    """Quién añadió cada fila. `versiones`: [{sha, textos_padres: [texto o None por padre]}, texto] de la más vieja a
    la más nueva (los commits que tocan el fichero). Una fila «añadida» en un commit es un (tabla, clave) que está en
    su versión y en la de ninguno de sus padres; mover una propuesta a su tabla es añadirla en la tabla nueva.
    → (por: {clave: set de personas}, autor: {(tabla, clave): persona o None, el último que la añadió},
       inicial: set de claves del commit que creó el fichero)."""
    por, autor, inicial = {}, {}, None
    for v in versiones:
        actual = _conjunto(v["texto"])
        padres = v.get("textos_padres") or []
        if inicial is None and all(t is None for t in padres):
            inicial = {c for _, c in actual}
        antes = set().union(*(_conjunto(t) for t in padres if t is not None))
        persona = sha_persona.get(v["sha"])
        for tabla, c in actual - antes:
            autor[(tabla, c)] = persona
            if persona:
                por.setdefault(c, set()).add(persona)
    return por, autor, inicial or set()


def _bajo(ruta, base):
    r, b = ruta.lower(), base.lower()
    return r.startswith(b) if b.endswith("/") else r == b


def _dueno_autoridad(carpeta, secs):
    """La persona cuyas carpetas de autoridad.md contienen la carpeta (gana el prefijo más largo); None si ninguna o
    si empatan dos personas."""
    if not carpeta:
        return None
    mejor = [(len(c), s["persona"]) for s in secs if s["persona"] for c in s["carpetas"]
             if contratos._bajo(carpeta.rstrip("/"), c)]
    if not mejor:
        return None
    largo = max(n for n, _ in mejor)
    personas = {p for n, p in mejor if n == largo}
    return personas.pop() if len(personas) == 1 else None


def _usuario(v):
    m = USUARIO.match(v or "")
    return m.group(1).lower() if m else None


def calcular(texto, versiones, sha_persona, texto_autoridad, texto_contratos, rutas, comprobados, pruebas,
             observado_en, rutas_observado_en=None):
    """El bloque `servicios` de estado.json.
    - texto: servicios.md de origin/main; versiones y sha_persona: los de confirmaciones();
    - rutas: ficheros de origin/main y de los últimos `arbol` (para «código fuera de cualquier servicio»);
    - comprobados: {clave: dato} del último servicio.estado; pruebas: {comando_sha: dato} del último `prueba`;
    - observado_en: hora del commit de servicios.md en origin/main."""
    leido = leer(texto)
    por, autor, inicial = confirmaciones(versiones, sha_persona)
    secs = contratos.secciones(texto_autoridad)
    titulos = {contratos.normal(b["nombre"]) for b in contratos.bloques(texto_contratos)}
    desajustes = []

    def desajuste(tipo, detalle, personas=(), clave_=None, rutas_=None, ts=None, fuente="git"):
        d = {"tipo": tipo, "detalle": detalle[:TEXTO_MAX], "observado_en": ts or observado_en, "fuente": fuente,
             "personas": sorted(set(personas))}
        if clave_:
            d["clave"] = clave_
        if rutas_ is not None:
            d["rutas"] = rutas_
        desajustes.append(d)

    # ¿Hay reparto? autoridad.md (lo genera /hack-plan) con al menos una persona. Antes, una fila sin dueño no es un
    # desajuste: solo se confirma si viene de /hack-scaffold.
    reparto = any(s["persona"] for s in secs)

    def confirmacion(c, duenos, bloqueada):
        faltan = [] if bloqueada else [d for d in duenos if d not in por.get(c, set())]
        de_scaffold = c in inicial
        vale = not bloqueada and (bool(duenos) and (not faltan or de_scaffold) or not reparto and de_scaffold)
        return {"valor": "confirmada" if vale else "sin_confirmar", "por": sorted(por.get(c, set())),
                "faltan": [] if vale else faltan, "de_scaffold": de_scaffold, "fuente": "git",
                "observado_en": observado_en}

    for n, detalle in leido["errores"]:
        desajuste("formato_invalido", f"línea {n}: {detalle}")

    filas = leido["filas"]
    servicios = [f for f in filas if f["tabla"] == SERVICIOS]
    duenos_de = {f["campos"]["nombre"]: _dueno_autoridad(f["campos"]["carpeta"], secs) for f in servicios}
    lista = []
    for f in servicios:
        c, k = f["campos"], f["clave"]
        dueno = duenos_de[c["nombre"]]
        for motivo in f["invalidos"]:
            desajuste("formato_invalido", f"«{c['nombre'] or ''}» (línea {f['linea']}): {motivo}", [dueno] if dueno
                      else [], k)
        if dueno is None and not reparto:
            distinto = False                 # «sin dueño» hasta que /hack-plan reparta
        else:
            distinto = dueno is None or (c["dueno"] is not None and _usuario(c["dueno"]) != dueno)   # «—»: autoridad.md
        if dueno is None and reparto:
            desajuste("dueno_distinto", f"«{c['nombre'] or ''}»: ninguna persona de autoridad.md tiene «{c['carpeta'] or ''}»",
                      [], k)
        elif distinto:
            desajuste("dueno_distinto", f"«{c['nombre']}»: Dueño «{c['dueno'] or '—'}», pero autoridad.md da "
                      f"«{c['carpeta']}» a @{dueno}", [dueno], k)
        conf = confirmacion(k, [dueno] if dueno else [], distinto)
        comprobado = comprobados.get(k)
        puerto = _puerto(c["puerto"])
        if conf["valor"] == "confirmada" and puerto is not None and not f["invalidos"] and comprobado:
            v = comprobado.get("valor") or {}
            if v.get("escucha") is False:
                desajuste("puerto_sin_respuesta", f"«{c['nombre']}» :{puerto} declarado, no responde", [dueno], k,
                          ts=comprobado["observado_en"], fuente=comprobado["fuente"])
            elif c["salud"] is not None and not (isinstance(v.get("salud"), int) and 200 <= v["salud"] < 300):
                codigo = v.get("salud")
                desajuste("salud_falla", f"«{c['nombre']}» :{puerto}{c['salud']} responde "
                          f"{codigo if codigo is not None else 'nada'}", [dueno], k, ts=comprobado["observado_en"],
                          fuente=comprobado["fuente"])
        lista.append({"clave": k, "nombre": (c["nombre"] or "")[:40], "carpeta": (c["carpeta"] or "")[:TEXTO_MAX],
                      "puerto": puerto, "arranque": c["arranque"], "salud": c["salud"], "dueno": c["dueno"],
                      "dueno_autoridad": dueno, "confirmacion": conf, "comprobado": comprobado})

    conexiones = []
    for f in (f for f in filas if f["tabla"] == CONEXIONES):
        c, k = f["campos"], f["clave"]
        extremos = [duenos_de.get(c["de"]), duenos_de.get(c["a"])]
        duenos = sorted({d for d in extremos if d})
        nombre = f"{c['de'] or ''} → {c['a'] or ''}"
        for motivo in f["invalidos"]:
            desajuste("formato_invalido", f"conexión «{nombre}» (línea {f['linea']}): {motivo}", duenos, k)
        sin_extremo = [x for x in (c["de"], c["a"]) if x not in duenos_de]
        for x in sin_extremo:
            desajuste("formato_invalido", f"conexión «{nombre}»: «{x or ''}» no está en Servicios", duenos, k)
        if c["contrato"] is None or contratos.normal(c["contrato"]) not in titulos:
            desajuste("contrato_inexistente", f"conexión «{nombre}»: el contrato «{c['contrato'] or '—'}» no está en "
                      "docs/contratos.md", duenos, k)
        bloqueada = bool(sin_extremo) or (None in extremos and reparto)
        conf = confirmacion(k, duenos, bloqueada)
        resultado = pruebas.get(huella_prueba(c["prueba"])) if c["prueba"] else None
        if resultado and resultado.get("valor") == "falla":
            desajuste("prueba_falla", f"contrato «{c['contrato'] or nombre}»: la prueba falla", duenos, k,
                      ts=resultado["observado_en"], fuente=resultado["fuente"])
        conexiones.append({"clave": k, "de": (c["de"] or "")[:40], "a": (c["a"] or "")[:40],
                           "contrato": c["contrato"], "prueba": c["prueba"], "duenos": duenos,
                           "confirmacion": conf, "resultado": resultado})

    propuestas = []
    for f in (f for f in filas if f["propuesta"]):
        campos = dict(f["campos"])
        if f["tipo"] == "servicio":
            campos["puerto"] = _puerto(campos["puerto"])
        for motivo in f["invalidos"]:
            desajuste("formato_invalido", f"propuesta de la línea {f['linea']}: {motivo}")
        propuestas.append({"tipo": f["tipo"], "clave": f["clave"], "campos": campos, "autor_declarado": f["autor"],
                           "hora_declarada": f["hora"], "autor_git": autor.get((f["tabla"], f["clave"])),
                           "observado_en": observado_en})

    fuera = list(SIEMPRE_FUERA) + [r for r in leido["fuera"] if r not in SIEMPRE_FUERA]
    carpetas = [s["carpeta"] for s in lista if s["carpeta"].endswith("/")]
    if carpetas:
        sueltas = sorted({r for r in rutas
                          if not any(_bajo(r, b) for b in carpetas + fuera)
                          and not ("/" not in r and r.startswith("."))})
        if sueltas:
            desajuste("codigo_fuera", f"{len(sueltas)} fichero{'s' if len(sueltas) != 1 else ''} fuera de todo "
                      "servicio", (), None, sueltas[:RUTAS_MAX], ts=rutas_observado_en)

    return {"fichero": {"valor": "mal formado" if leido["errores"] else "ok", "fuente": "git",
                        "observado_en": observado_en},
            "lista": lista, "conexiones": conexiones, "propuestas": propuestas, "fuera": fuera,
            "desajustes": desajustes}
