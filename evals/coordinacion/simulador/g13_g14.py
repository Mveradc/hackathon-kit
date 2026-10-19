# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""G13 (vista de jurado, R-35) y G14 (ruta crítica, R-36) de M10: los guiones se cargan y lo que tiene que salir
(guiones/g13/hechos.json, guiones/g14/hechos.json y los casos de guiones/g13/casos.json y guiones/g14/casos.json) es lo
que dan las reglas del contrato con esas entradas.

Las reglas son las de api.md §11.2–§11.4 (ADR-0012 y ADR-0013) con las decisiones del usuario sobre el issue #46,
escritas aquí otra vez, sin importar hkos/jurado.py ni hkos/ruta.py (que es lo que esto valida):
  - jurado: una cita casa por «fecha hora» y, si lleva «· quién», por ese quién; con varias notas, enlace ambiguo; con
    ninguna, sin_nota. Hecha = publicada, cerrada sin ⚑, o con historia.hecha_en y ahora en curso, parada, no cerrada,
    en revisión o integrada (J6 B; también parada y no cerrada). Cobertura: cubierta (todas sus tareas firmes hechas,
    J4 A), declarada (planificada si ninguna ha empezado; si no, en curso), ambigua, en_pitch o sin_tarea. «Sin
    cubrir» = todo lo que no es cubierta ni está corregido, con su desglose; en `cuenta`, «ambiguas» es un grupo aparte
    (no cuenta en «sin tarea») y entra en sin_cubrir_por_fuerza. La evidencia es tareas[].evidencia, {valor, tipo,
    fuente, observado_en}: el último sha publicado, con la hora de esa publicación. Orden: sin cubrir por fuerza (dato,
    «obligatorio», «se valora», «nos gustaría ver», otra palabra, comentario, sin precisar) y hora; después las cubiertas
    y al final las corregidas, por hora;
  - ruta: manda «Entrega:» de equipo.md (las otras, al lado, no quitan la estimación; con dos horas, manda la primera y
    la otra va al lado, decisión 5); el grafo, con depende_de y el orden del plan de cada persona (R3 B); la franja, del
    Hasta anterior al suyo, menos los descansos de esa persona dentro, repartida entre las filas que comparten el Hasta;
    el ritmo, por persona con 3 medidas; una tarea sin plazo sale aparte y se estima el resto (decisión 1), y
    `sin_plazo` solo es motivo si ninguna abierta que cuenta tiene franja; riesgos por estimación = las que acaban
    (fin_tarde) después de la entrega, {tarea, tipo, fin_tarde, dueno, en_cadena, viejo}, la más tardía primero; la
    cadena, solo con tareas abiertas; un plazo pasado arrastra a sus sucesoras abiertas, directas o no; en el resumen,
    «plazo pasado» va antes que «sin contar…» y «otra entrega…».
Del motor de verdad solo se toman los estados (modelo.calcular, con cada evento y estado validados contra los esquemas de
docs/hackathon-os/contratos/) y la historia de cada tarea (modelo.historias, la de §11.2).
G14 tiene dos ramas con las mismas entradas: G14.json («inicio» y «mitad bien») y G14r.json («mitad con riesgo»).

Uso: uv run --no-project evals/coordinacion/simulador/g13_g14.py   (0 OK · 1 falla)
"""
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path[:0] = [os.path.join(KIT, "hkos"), AQUI]
from compilar import leer_plan  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import ATRIBUIBLES, fecha  # noqa: E402
from modelo import atribuir, calcular, historias  # noqa: E402
from proyeccion import corta  # noqa: E402
from simula import carga, ejecutar, montar  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")   # en una consola cp1252, «≥» o «→» no cortan la salida

MADRID = timezone(timedelta(hours=2))      # Europe/Madrid en septiembre (CEST): sin tzdata en Windows, fija
ZONAS = {"europe/madrid": MADRID}
UMBRAL_SENALES = timedelta(seconds=1200)   # umbral_parada_min por defecto
MINIMO = 3                                 # base.minimo, fijo
HECHAS = ("publicada", "cerrada")
SIGUE_HECHA = ("en_curso", "parada", "no_cerrada", "en_revision", "integrada")
SIN_EMPEZAR = ("lista", "pendiente", "reclamada")
FUERZAS = ("obligatorio", "se valora", "nos gustaría ver")
DIAS = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
DIAS_R = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")   # los del resumen
LEGIBLE = {"a_tiempo": "a tiempo", "justo": "justo", "no_llega": "no llega"}
RESUMEN_MAX = 120                          # §11.3 y §11.4 (M17), por grafemas
MOTIVOS = ("sin_entrega", "ciclo", "sin_plazo", "pocos_datos")   # sin entrega_doble (decisión 5 del #46)
CAMPOS_RIESGO = {"tarea", "tipo", "fin_tarde", "dueno", "en_cadena", "viejo"}
CAMPOS_CUENTA = {"notas", "corregidas", "cubiertas", "sin_cubrir", "sin_tarea", "ambiguas", "planificadas", "en_curso",
                 "en_pitch", "sin_cubrir_por_fuerza"}
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
# Los motivos de un plazo en las palabras de g14/hechos.json (los del contrato van en motivo_contrato).
TEXTO_MOTIVO = {"relativo_sin_inicio": "sin Inicio", "sin_inicio": "sin Inicio", "por_confirmar": "plazo sin resolver",
                "vacio": "vacío", "sin_zona": "sin zona", "formato": "formato", "orden": "franja al revés"}
FUERA = {"condicional": "empieza por «Si …»", "si_da_tiempo": "lleva [SI DA TIEMPO]"}
CABECERA = re.compile(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+) \((.+)\)$")
CORRIGE = re.compile(r"corrige la nota del (\d{4}-\d\d-\d\d \d\d:\d\d(?: · [^,.;»)]+)?)")
ETIQUETA = re.compile(r"\(criterios: ([^)]+)\)")
fallos, callado = 0, False


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    if not callado:
        print(("OK    " if ok else "FALLO ") + nombre + ("" if ok or not detalle else f"\n        {detalle}"))


def texto(rel):
    with open(os.path.join(AQUI, rel), encoding="utf-8") as f:
        return f.read()


def z(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def local(cita):
    return datetime.strptime(cita, "%Y-%m-%d %H:%M").replace(tzinfo=MADRID)


def plano(s):
    """Sin tildes, en minúsculas y con los espacios juntos."""
    s = unicodedata.normalize("NFD", s or "")
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").casefold().split())


def difiere(a, b, ruta=""):
    """Las diferencias de `a` con `b`, recorriendo las claves de `a` (las de más en `b` no cuentan)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in a for d in difiere(a[k], b.get(k), f"{ruta}.{k}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in difiere(x, y, f"{ruta}[{i}]")]
    return [] if a == b else [f"{ruta or '·'}: {a!r} ≠ {b!r}"]


def reemplaza(md, cambios, nombre):
    """Aplica los cambios [de, a, veces] de un caso: cada `de` tiene que salir `veces` veces (1 si no se dice)."""
    for c in cambios:
        de, a, veces = c[0], c[1], c[2] if len(c) > 2 else 1
        if md.count(de) != veces:
            raise ValueError(f"{nombre}: «{de}» sale {md.count(de)} veces, no {veces}")
        md = md.replace(de, a)
    return md


def correr(nombre, rel):
    """simula.ejecutar con los esquemas: (guion, todos los puntos de control bien)."""
    ev, es = Esquema("eventos.schema.json"), Esquema("estado.schema.json")
    malos = []

    def valida(esquema):
        def f(x):
            err = esquema.error(x)
            if err:
                malos.append(err)
        return f
    resultado, _ = ejecutar(os.path.join(AQUI, rel), valida(ev), valida(es))
    dif = [(t, d) for t, d in resultado if d]
    comprueba(f"{nombre}: se carga, eventos y estados validan contra los esquemas y el motor da lo esperado en "
              f"{len(resultado)} momentos", not dif and not malos, f"{dif} {malos[:3]}")
    return carga(os.path.join(AQUI, rel))


def foto(guion, ahora):
    """Lo que el relay tendría a `ahora`: estado.json, los eventos atribuidos, todos los eventos, las tareas y la
    historia de cada tarea ({ID: (historia, evidencia)}; evidencia = {valor, tipo, fuente, observado_en} o None)."""
    tareas, personas, issues, eventos, _ = montar(guion, AQUI)
    estado = calcular(tareas, issues, eventos, personas, ahora, guion.get("umbral_parada_s", 1200))
    t = fecha(ahora)
    hasta = {k: dict(v, acciones=[a for a in v["acciones"] if fecha(a["ts"]) <= t]) for k, v in issues.items()}
    atribuidos, _, _ = atribuir(tareas, hasta, [e for e in eventos if fecha(e["ts"]) <= t],
                                {p["persona"] for p in personas})
    return {"estado": estado, "atribuidos": atribuidos, "eventos": eventos, "tareas": tareas,
            "historias": historias(tareas, issues, eventos, personas, ahora)}


def iguales_tareas(json_tareas, plan_tareas):
    campos = ("id", "titulo", "bloque", "dueno", "depende_de")
    return [{k: t[k] for k in campos} for t in json_tareas] == [{k: t[k] for k in campos} for t in plan_tareas]


def seccion(md, titulo):
    m = re.search(rf"^## {re.escape(titulo)}[ \t]*$(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(1) if m else ""


def celdas(linea):
    return [c.strip() for c in linea.strip().strip("|").split("|")]


# =========================================================================================================== G13
def leer_notas(md):
    notas, actual = [], None
    for linea in md.split("\n"):
        m = CABECERA.match(linea)
        if m:
            actual = {"cabecera": linea, "cita": m.group(1), "quien": m.group(2), "papel": m.group(3), "campos": {},
                      "lineas": {}}
            notas.append(actual)
        elif actual and linea.startswith("- ") and ":" in linea:
            k, v = linea[2:].split(":", 1)
            actual["campos"][k] = v.strip()
            actual["lineas"][k] = linea.strip()
    for n in notas:
        m = CORRIGE.search(n["campos"].get("Qué dijo", ""))
        n["corrige"] = m.group(1).strip() if m else None
        n["clave"] = hashlib.sha256("\n".join([n["cabecera"].strip(), n["lineas"].get("Qué dijo", ""),
                                               n["lineas"].get("Anotado por", "")]).encode("utf-8")).hexdigest()[:12]
    return notas


def casan(cita, notas, presentes):
    """§11.3: las notas en main de esa «fecha hora» y, si la cita lleva «· quién», de ese quién."""
    hora, _, quien = cita.partition(" · ")
    return [i for i in presentes if notas[i]["cita"] == hora.strip()
            and (not quien.strip() or plano(notas[i]["quien"]) == plano(quien))]


def rango_fuerza(f):
    t = plano(f.strip("«»"))
    if t == "dato":
        return 0
    if t in FUERZAS:
        return 1 + FUERZAS.index(t)
    return {"comentario suelto": 5, "sin precisar": 6, "": 6}.get(t, 4)


def filas_plan(md):
    """{ID: (Cómo se comprueba, [citas de su etiqueta])} de las filas de «## Por persona»."""
    salida = {}
    for linea in seccion(md, "Por persona").split("\n"):
        if re.match(r"^\| T\d{2,3} \|", linea):
            c = celdas(linea)
            m = ETIQUETA.search(c[-1])
            salida[c[0]] = (c[-1], [x.strip() for x in m.group(1).split(",")] if m else [])
    return salida


def conexiones(md):
    """[(clave legible, Prueba normalizada)] de «## Conexiones» de servicios.md (§10)."""
    salida = []
    for linea in seccion(md, "Conexiones").split("\n"):
        if linea.startswith("|") and not re.match(r"^\|\s*-", linea):
            c = celdas(linea)
            if len(c) == 4 and c[0] != "De":
                salida.append((f"{c[0]} → {c[1]}", c[3].strip().strip("`").strip()))
    return salida


def publicaciones(eventos, tid, ahora):
    """[(ts, sha)] de los push de git que publican un commit con el ID de `tid`, hasta `ahora`."""
    shas = [e["datos"]["sha"] for e in eventos if e["tipo"] == "commit" and e.get("tarea") == tid]
    salida = []
    for e in eventos:
        if e["tipo"] == "push" and e["fuente"] == "git" and fecha(e["ts"]) <= fecha(ahora):
            suyos = [s for s in e["datos"].get("incluye", []) if s in shas]
            if suyos:
                salida.append((e["ts"], suyos[-1]))
    return salida


def jurado(notas, ids, presentes, plan, pitch_citas, f, ahora, pruebas=None):
    """Lo que la vista de jurado tiene que decir (en la forma de g13/hechos.json) con las reglas del contrato.
    plan: {ID: (Cómo se comprueba, [citas])}; f: foto(); pruebas: {ID: [{conexion, resultado, observado_en}]}."""
    tareas = {t["id"]: t for t in f["estado"]["tareas"]}
    estados = {k: t["estado"]["valor"] for k, t in tareas.items()}
    decl = {k: (t["declarado"] or {}).get("valor") for k, t in tareas.items()}
    hist = {k: h for k, (h, _) in f["historias"].items()}

    def hecha(t):
        return estados[t] == "publicada" or (estados[t] == "cerrada" and decl[t] != "cerrada") or (
            bool(hist[t]["hecha_en"]) and estados[t] in SIGUE_HECHA)

    def evidencia(t):
        """§11.2 y §11.3: el último sha publicado y la hora de esa publicación ({tarea, sha, observado_en}, como en los
        hechos), cruzado con tareas[].evidencia de modelo.historias, que es un objeto {valor, tipo, fuente,
        observado_en}: aquí, un commit con ID publicado por un push de git."""
        pubs, ev = publicaciones(f["eventos"], t, ahora), f["historias"][t][1]
        if not pubs and not ev:
            return None
        ts, sha = pubs[-1] if pubs else (None, None)
        bien = isinstance(ev, dict) and (ev["valor"], ev["tipo"], ev["fuente"], ev["observado_en"]) == (
            sha, "commit", "git", ts) and (estados[t] != "publicada" or tareas[t]["estado"]["observado_en"] == ts)
        return {"tarea": t, "sha": sha, "observado_en": ts if bien else None}   # si no casan con el motor, que falle

    enlaces, sin_nota = {i: {} for i in presentes}, []
    for tid in sorted(plan):
        for cita in plan[tid][1]:
            casa = casan(cita, notas, presentes)
            if not casa:
                sin_nota.append({"tarea": tid, "cita": cita})
            for i in casa:
                enlaces[i][tid] = enlaces[i].get(tid, True) and len(casa) > 1     # uno firme gana a uno ambiguo
    en_pitch = set()
    for cita in pitch_citas:
        casa = casan(cita, notas, presentes)
        if len(casa) == 1:
            en_pitch.add(casa[0])
    corregida = {}
    for j in sorted(presentes, key=lambda k: notas[k]["cita"]):
        if notas[j]["corrige"]:
            casa = [i for i in casan(notas[j]["corrige"], notas, presentes) if i != j]
            if len(casa) == 1 and notas[casa[0]]["cita"] <= notas[j]["cita"]:
                corregida[casa[0]] = j

    salida, valor = {}, {}
    for i in presentes:
        suyas = sorted(enlaces[i])
        firmes = [t for t in suyas if not enlaces[i][t]]
        if firmes:
            v = "cubierta" if all(hecha(t) for t in firmes) else \
                "planificada" if all(estados[t] in SIN_EMPEZAR for t in firmes) else "en_curso"
        else:
            v = "ambigua" if suyas else "en_pitch" if i in en_pitch else "sin_tarea"
        valor[i] = v
        nuevo = [hist[t]["trabajo_nuevo_desde"] for t in firmes
                 if estados[t] in SIGUE_HECHA and hecha(t) and hist[t]["trabajo_nuevo_desde"]]
        x = {"estado": "corregida" if i in corregida else v, "tareas": {t: estados[t] for t in suyas},
             "evidencia": [e for t in suyas if (e := evidencia(t))],
             "trabajo_nuevo_desde": min(nuevo, key=fecha) if nuevo else None,
             "cerradas_a_mano": [t for t in suyas if decl[t] == "cerrada"],
             "corregida_por": ids[corregida[i]] if i in corregida else None, "tambien_en_pitch": i in en_pitch}
        if len(firmes) < len(suyas):
            x["ambiguas"] = [t for t in suyas if enlaces[i][t]]
        prs = [dict(p, tarea=t) for t in suyas for p in (pruebas or {}).get(t, [])]
        if prs:
            x["pruebas"] = prs
        salida[ids[i]] = x

    def orden(i):
        grupo = 2 if i in corregida else 1 if valor[i] == "cubierta" else 0
        return grupo, rango_fuerza(notas[i]["campos"].get("Fuerza", "")) if grupo == 0 else 0, notas[i]["cita"], \
            notas[i]["clave"]
    vivas = [i for i in presentes if i not in corregida]
    sin = [i for i in sorted(vivas, key=orden) if valor[i] != "cubierta"]
    por_fuerza = {}
    for i in sin:
        fz = notas[i]["campos"].get("Fuerza", "sin precisar")
        por_fuerza.setdefault(rango_fuerza(fz) if rango_fuerza(fz) != 4 else (4, plano(fz)), {"texto": fz, "n": 0})["n"] += 1
    cuantas = lambda v: sum(valor[i] == v for i in vivas)      # noqa: E731
    cuenta = {"notas": len(presentes), "sin_cubrir": len(sin), "sin_tarea": cuantas("sin_tarea"),
              "planificadas": cuantas("planificada"), "en_curso": cuantas("en_curso"), "en_pitch": cuantas("en_pitch"),
              "ambiguas": cuantas("ambigua"), "cubiertas": cuantas("cubierta"), "corregidas": len(corregida),
              "sin_cubrir_por_fuerza": list(por_fuerza.values())}
    return {"tareas": {t: estados[t] for t in sorted({t for x in salida.values() for t in x["tareas"]})},
            "notas": salida, "orden": [ids[i] for i in sorted(presentes, key=orden)], "cuenta": cuenta,
            "sin_nota": sin_nota}


def g13(cambia=None):
    guion = correr("G13", "guiones/G13.json")
    datos = {"hechos": carga(os.path.join(AQUI, guion["hechos"])), "casos": carga(os.path.join(AQUI, "guiones/g13/casos.json"))}
    if cambia:
        cambia(datos)
    hechos, casos = datos["hechos"], datos["casos"]
    ent = guion["entradas"]
    plan_md, crit_md, pitch_md = texto(ent["plan.md"]), texto(ent["criterios.md"]), texto(ent["pitch.md"])
    tabla = json.loads(texto(guion["tareas"]))
    comprueba("G13: tareas.json es lo que compilar.leer_plan lee de plan.md",
              iguales_tareas(tabla["tareas"], leer_plan(plan_md, tabla["personas"])))
    ejemplo = open(os.path.join(KIT, hechos["entradas"]["plan.md"]["antes"]), encoding="utf-8").read()
    comprueba("G13: plan.md sin las etiquetas «(criterios: …)» es el plan de ejemplo del reto 03",
              re.sub(r" \(criterios: [^)]*\)", "", plan_md) == ejemplo)

    notas = leer_notas(crit_md)
    hn = hechos["notas"]
    comprueba(f"G13: criterios.md tiene las {len(hn)} notas de los hechos, en orden, con cabecera, fuerza y «Anotado por»",
              len(notas) == len(hn) == 8 and all(
                  n["cabecera"] == h["cabecera"] and n["campos"].get("Fuerza") == h["fuerza"]
                  and n["campos"].get("Anotado por") == h["anotado_por"] and n["quien"] == h["quien"]
                  and n["papel"] == h["papel"] and z(local(n["cita"])) == h["cuando"] for n, h in zip(notas, hn)))
    origen = ["Anotar" if n["campos"].get("Anotado por", "").startswith("@")
              and n["campos"].get("Afecta a", "").startswith("— (anotada desde la web") else "/hack-note" for n in notas]
    comprueba("G13: las de Anotar (con @ y «anotada desde la web») y las de /hack-note, como dicen los hechos",
              origen == [h["origen"] for h in hn] and {"Anotar", "/hack-note"} <= set(origen))
    ids = [h["id"] for h in hn]
    todas = list(range(len(notas)))
    mismo = [ids[j] if (j := next((k for k, m in enumerate(notas) if k != i and m["cita"] == n["cita"]), None)) is not None
             else None for i, n in enumerate(notas)]
    comprueba("G13: dos notas en el mismo minuto, de personas distintas", mismo == [h["mismo_minuto_que"] for h in hn]
              and sum(x is not None for x in mismo) == 2)
    corrige = [ids[c[0]] if n["corrige"] and len(c := casan(n["corrige"], notas, todas)) == 1 else None for n in notas]
    comprueba("G13: una nota corrige a otra (y la cita casa con una sola)", corrige == [h["corrige"] for h in hn]
              and sum(x is not None for x in corrige) == 1)
    comprueba("G13: una nota de fuerza «dato» y una con texto imperativo",
              [n["campos"]["Fuerza"] for n in notas].count("dato") == 1
              and [bool(re.match(r"«(Haced|Haz|Poned|Olvidaos)", n["campos"]["Qué dijo"])) for n in notas]
              == [h["texto_imperativo"] for h in hn])
    plan = filas_plan(plan_md)
    pitch_citas = [c.strip() for m in ETIQUETA.finditer(pitch_md) for c in m.group(1).split(",")]
    comprueba("G13: qué tareas citan cada nota y si la cita el pitch, como en los hechos",
              all(sorted(t for t, (_, cs) in plan.items() for c in cs if i in casan(c, notas, todas))
                  == sorted(h["citada_en_plan"]) and any(i in casan(c, notas, todas) for c in pitch_citas)
                  == h["citada_en_pitch"] for i, h in enumerate(hn)))
    comprueba("G13: la cita sin «· quién» del minuto repetido casaría con dos notas (por eso el plan lleva «· quién»)",
              len(casan(notas[ids.index("N2")]["cita"], notas, todas)) == 2)
    comprueba("G13: una nota de fuerza «dato» recogida solo en el pitch",
              any(h["fuerza"] == "dato" and h["citada_en_pitch"] and not h["citada_en_plan"] for h in hn))

    desde_plan = fecha(hechos["entradas"]["plan.md"]["en_main_desde"])
    desde_pitch = fecha(hechos["entradas"]["pitch.md"]["en_main_desde"])
    momentos = {}
    for mo in hechos["momentos"]:
        ahora = mo["ahora"]
        f = foto(guion, ahora)
        momentos[mo["nombre"]] = (mo, f)
        comprueba(f"G13 {mo['nombre']}: el plan con etiquetas y el pitch ya están en main",
                  desde_plan <= fecha(ahora) and desde_pitch <= fecha(ahora))
        presentes = [i for i, h in enumerate(hn) if fecha(h["en_main_desde"]) <= fecha(ahora)]
        comprueba(f"G13 {mo['nombre']}: las notas de los hechos son las que están en main ({len(presentes)})",
                  sorted(mo["notas"]) == sorted(ids[i] for i in presentes))
        real = jurado(notas, ids, presentes, plan, pitch_citas, f, ahora)
        comprueba(f"G13 {mo['nombre']}: el estado de las tareas de los hechos es el del motor",
                  not difiere(real["tareas"], mo["tareas"]), difiere(real["tareas"], mo["tareas"]))
        for nid in sorted(real["notas"], key=ids.index):
            esperado, h = mo["notas"][nid], hn[ids.index(nid)]
            dif = difiere(real["notas"][nid], esperado)
            comprueba(f"G13 {mo['nombre']}, {nid} ({h['cita']} · {h['quien']}): {esperado['estado']}", not dif, dif)
            comprueba(f"G13 {mo['nombre']}, {nid}: nunca «cubierta» sin la evidencia de todas sus tareas",
                      esperado["estado"] != "cubierta" or len(esperado["evidencia"]) == len(esperado["tareas"]) > 0)
        for k in ("orden", "cuenta", "sin_nota"):
            dif = difiere(real[k], mo[k])
            comprueba(f"G13 {mo['nombre']}: {k} {real[k] if k == 'orden' else ''}".rstrip(), not dif, dif)
        cuenta_g13(f"G13 {mo['nombre']}", mo["cuenta"])
    c = hechos["sin_senales"]["persona-c"]
    f = momentos[hechos["momentos"][-1]["nombre"]][1]
    ultimo = max(e["ts"] for e in f["atribuidos"] if e["actor"]["persona"] == "persona-c" and e.get("tarea"))
    comprueba("G13: persona-c no da señales desde la hora de los hechos", ultimo == c["desde"], ultimo)

    for caso in casos["casos"]:
        mo, f = momentos[caso["base"]]
        nombre = f"G13 caso «{caso['id']}» ({caso['base']})"
        md_plan = reemplaza(plan_md, caso.get("plan.md", []), nombre)
        md_crit = reemplaza(crit_md, caso.get("criterios.md", []), nombre)
        n2 = leer_notas(md_crit)
        ids2 = ids + [f"N{k + 1}" for k in range(len(ids), len(n2))]
        presentes = [i for i in range(len(n2)) if i >= len(hn) or fecha(hn[i]["en_main_desde"]) <= fecha(mo["ahora"])]
        plan2 = filas_plan(md_plan)
        pruebas = {}
        for clave, prueba in conexiones(caso.get("servicios.md", "")):
            r = caso["resultados"][prueba]
            for tid, (como, _) in plan2.items():
                if prueba and prueba in como:
                    pruebas.setdefault(tid, []).append({"conexion": clave, "resultado": r["resultado"],
                                                        "observado_en": r["observado_en"]})
        real = jurado(n2, ids2, presentes, plan2, pitch_citas, f, mo["ahora"], pruebas)
        dif = difiere(caso["espera"], real)
        comprueba(f"{nombre}: {caso['que']}", not dif, dif)
        if "cuenta" in caso["espera"]:
            cuenta_g13(nombre, caso["espera"]["cuenta"])


def cuenta_g13(nombre, cuenta):
    """§11.3 (ajuste 2): las claves de `cuenta` son las del contrato, con «ambiguas» como grupo aparte (una ambigua no
    cuenta en «sin tarea»), y «sin cubrir» es la suma de los cinco grupos y la de su desglose por fuerza."""
    comprueba(f"{nombre}: cuenta con las claves del contrato y «ambiguas» aparte; «sin cubrir» ({cuenta.get('sin_cubrir')})"
              " = sin tarea + ambiguas + planificadas + en curso + en el pitch = su desglose por fuerza",
              set(cuenta) == CAMPOS_CUENTA and cuenta["sin_cubrir"] == sum(
                  cuenta[k] for k in ("sin_tarea", "ambiguas", "planificadas", "en_curso", "en_pitch"))
              == cuenta["notas"] - cuenta["cubiertas"] - cuenta["corregidas"]
              == sum(x["n"] for x in cuenta["sin_cubrir_por_fuerza"]), cuenta)


# =========================================================================================================== G14
def campo(md, nombre):
    m = re.search(rf"^- {nombre}:(.*)$", seccion(md, "Hackathon"), re.M)
    return m.group(1).strip() if m else None


HHMM = re.compile(r"(?<![\d:])(\d{1,2}):(\d\d)(?![\d:])")
DESFASE = re.compile(r"(?:(?<=\s)|(?<=\()|^)(?:UTC)?([+-])(\d{1,2})(?::?(\d\d))?(?=\)|\s|$)")
IANA = re.compile(r"\b([A-Za-z]+/[A-Za-z_]+)\b")


def fecha_de(t, anio):
    m = re.search(r"\b(\d{4})-(\d\d)-(\d\d)\b", t)
    if m:
        return int(m[1]), int(m[2]), int(m[3])
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t)
    if m:
        return int(m[3]), int(m[2]), int(m[1])
    m = re.search(r"\b(\d{1,2}) de (\w+)(?: de (\d{4}))?", plano(t))
    if m and m[2][:3] in MESES:
        return int(m[3] or anio), MESES.index(m[2][:3]) + 1, int(m[1])
    return None


def hora_declarada(linea, anio=2026, varias=False):
    """§11.2, `- Inicio:` y `- Entrega:`: (valor, motivo, confirmar, zona, [otras horas]). «Dos horas» son dos HH:MM
    distintas que no son el desfase de una zona («10:00 (cierre 11:00)»); «2026-09-20 10:00 (UTC+02:00)» es una sola.
    En `Entrega:` (`varias`), manda la primera y las demás van a la lista, el mismo día o el siguiente (decisión 5 del
    #46, ajuste 5 de ADR-0013: no hay `entrega_doble`); en `Inicio:`, `dos_horas` (como hkos/lecturas.py)."""
    if linea is None or linea.strip() in ("", "—") or "<" in linea:
        return None, "sin_dato", False, None, []
    confirmar = "(confirmar)" in linea
    t = linea.replace("(confirmar)", " ")
    if plano(t) == "por confirmar":
        return None, "por_confirmar", confirmar, None, []
    zona = None
    m = IANA.search(t)
    if m:
        zona = ZONAS.get(m.group(1).casefold())
        t = t.replace(m.group(0), " ")
    m = DESFASE.search(t)
    if m:
        zona = timezone((1 if m[1] == "+" else -1) * timedelta(hours=int(m[2]), minutes=int(m[3] or 0)))
        t = t[:m.start()] + " " + t[m.end():]
    horas, dia = list(dict.fromkeys((int(h), int(m)) for h, m in HHMM.findall(t))), fecha_de(t, anio)
    if len(horas) > 1 and not varias:
        return None, "dos_horas", confirmar, zona, []
    if not horas or dia is None:
        return None, "formato", confirmar, zona, []
    if zona is None:
        return None, "sin_zona", confirmar, None, []
    valor = datetime(*dia, *horas[0], tzinfo=zona)
    otras = [datetime(*dia, *h, tzinfo=zona) for h in horas[1:]]
    return valor, None, confirmar, zona, [o if o >= valor else o + timedelta(days=1) for o in otras]


def resolver(hasta, inicio, zona, anterior, anio=2026):
    """§11.2, un Hasta (o la hora de un hito o de un descanso): (datetime o None, motivo)."""
    t = " ".join((hasta or "").split())
    if t in ("", "—"):
        return None, "vacio"
    if "por confirmar" in plano(t) or "?" in t:
        return None, "por_confirmar"
    m = re.fullmatch(r"H\+(\d+)(?::(\d\d))?", t)
    if m:
        return (inicio + timedelta(hours=int(m[1]), minutes=int(m[2] or 0)), None) if inicio else (None, "relativo_sin_inicio")
    m = re.fullmatch(r"(?:(\S+) (?:(\d{1,2}) (\S+) )?)?(\d{1,2}):(\d\d)", t)
    if not m or int(m[4]) > 23 or int(m[5]) > 59:
        return None, "formato"
    dia = DIAS.index(plano(m[1]).rstrip(".")[:3]) if m[1] and plano(m[1]).rstrip(".")[:3] in DIAS else None
    if m[1] and dia is None:
        return None, "formato"
    if zona is None:
        return None, "sin_zona"
    hm = (int(m[4]), int(m[5]))
    if m[2]:
        mes = plano(m[3]).rstrip(".")[:3]
        if mes not in MESES:
            return None, "formato"
        d = datetime(inicio.year if inicio else anio, MESES.index(mes) + 1, int(m[2]), *hm, tzinfo=zona)
        return (d, None) if d.weekday() == dia else (None, "formato")
    if inicio is None:
        return None, "sin_inicio"
    base = inicio.astimezone(zona)
    if dia is not None:
        d = base + timedelta(days=(dia - base.weekday()) % 7)
        return datetime(d.year, d.month, d.day, *hm, tzinfo=zona), None
    ref = anterior.astimezone(zona) if anterior else base
    d = datetime(ref.year, ref.month, ref.day, *hm, tzinfo=zona)
    return (d + timedelta(days=1) if d < ref else d), None


def filas(md):
    """[(ID, persona, Hasta crudo, título)] de «## Por persona», en el orden del plan."""
    salida, persona = [], None
    for linea in seccion(md, "Por persona").split("\n"):
        m = re.match(r"^### Persona ([A-Z]) ·", linea)
        if m:
            persona = "persona-" + m.group(1).lower()
        m = re.match(r"^\| (T\d{2,3}) \|(.*)\|$", linea)
        if m:
            c = [x.strip() for x in m.group(2).split("|")]
            salida.append((m.group(1), persona, c[0], c[2]))
    return salida


def quienes(txt, personas):
    if plano(txt) == "todos":
        return list(personas)
    return ["persona-" + x.lower() for x in re.findall(r"Persona ([A-Z])", txt)] + re.findall(r"@([\w-]+)", txt)


TRAMO = re.compile(r"(\S+ \d{1,2}:\d\d)\s*[–—-]\s*(\S+ )?(\d{1,2}:\d\d)")


def descansos(md, inicio, zona, personas):
    """«## Descansos», en tabla (| turno | quién |) o en lista (- quién: turno), con varias personas o «Todos»:
    [{texto, personas, desde, hasta, motivo}], cada turno resuelto como un Hasta (el final, al día siguiente si queda
    antes)."""
    salida = []
    for linea in seccion(md, "Descansos").split("\n"):
        c = celdas(linea) if linea.startswith("|") else []
        if len(c) == 2 and TRAMO.fullmatch(c[0]):
            tramo, quien = c[0], c[1]
        elif (m := re.match(r"^- ([^:]+): (.+)$", linea.strip())):
            quien, tramo = m[1], m[2].strip()
        else:
            continue
        x = {"texto": tramo, "personas": quienes(quien, personas), "desde": None, "hasta": None, "motivo": None}
        m = TRAMO.fullmatch(tramo)
        if not m:
            x["motivo"] = "formato"
        else:
            a, motivo = resolver(m[1], inicio, zona, None)
            if a is None:
                x["motivo"] = motivo
            else:
                b, _ = resolver((m[2] or m[1].split()[0] + " ") + m[3], inicio, zona, None)
                if not m[2] and b < a:
                    b += timedelta(days=1)
                x["desde"], x["hasta"] = a, b
        salida.append(x)
    return salida


def junta(intervalos):
    salida = []
    for a, b in sorted(intervalos):
        if salida and a <= salida[-1][1]:
            salida[-1] = (salida[-1][0], max(salida[-1][1], b))
        else:
            salida.append((a, b))
    return salida


def solape(a, b, pausas):
    return sum(max(0.0, (min(b, y) - max(a, x)).total_seconds()) for x, y in pausas)


def avanza(t, segundos, pausas):
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


def leer_entradas(md_eq, md_plan, personas):
    """Lo que el relay leería de equipo.md y plan.md (§11.2), con los descansos restados de la franja."""
    ini_txt, ent_txt = campo(md_eq, "Inicio"), campo(md_eq, "Entrega")
    inicio, ini_motivo, _, z1, _ = hora_declarada(ini_txt)
    entrega, ent_motivo, confirmar, z2, segundas = hora_declarada(ent_txt, varias=True)
    zona = z1 or z2
    fs = filas(md_plan)
    ds = descansos(md_plan, inicio, zona, personas)
    pausas = {p: junta([(d["desde"], d["hasta"]) for d in ds if d["desde"] and p in d["personas"]]) for p in personas}
    plazos, persona = {}, None
    for tid, p, h, _ in fs:
        if p != persona:
            persona, efectivo, de, anterior = p, "", None, None
        if h:
            efectivo, de = h, tid
        valor, motivo = resolver(efectivo, inicio, zona, anterior)
        anterior = valor or anterior
        plazos[tid] = {"hasta": h, "efectivo": efectivo, "heredado_de": None if h else de, "valor": valor,
                       "motivo": motivo}
    franjas, i = {}, 0
    while i < len(fs):
        tid, p = fs[i][0], fs[i][1]
        if i == 0 or fs[i - 1][1] != p:
            desde = inicio
        j = i + 1
        while j < len(fs) and fs[j][1] == p and plazos[fs[j][0]]["efectivo"] == plazos[tid]["efectivo"]:
            j += 1
        v = plazos[tid]["valor"]
        if v is None:
            fr = (None, "sin_plazo")
        elif desde is None:
            fr = (None, "sin_inicio")
        elif v <= desde:
            fr = (None, "orden")
        else:
            seg = (v - desde).total_seconds() - solape(desde, v, pausas[p])
            fr = ({"desde": desde, "hasta": v, "compartida": j - i, "min": math.ceil(seg / 60 / (j - i))}, None)
        for f in fs[i:j]:
            franjas[f[0]] = fr
        desde = v or desde
        i = j
    otras = [{"texto": ent_txt, "valor": o, "donde": "equipo.md"} for o in segundas]
    for linea in seccion(md_plan, "Hitos del equipo").split("\n"):
        c = celdas(linea) if linea.startswith("|") else []
        if len(c) > 1 and re.search(r"\bentrega\b", plano(c[1])):        # «entregables» no
            otras.append({"texto": c[0], "valor": resolver(c[0], inicio, zona, None)[0], "donde": "plan.md"})
    return {"inicio": {"texto": ini_txt, "valor": inicio, "motivo": ini_motivo},
            "entrega": {"texto": ent_txt, "valor": entrega, "motivo": ent_motivo, "confirmar": confirmar},
            "otras": otras, "filas": fs, "plazos": plazos, "franjas": franjas, "descansos": ds, "pausas": pausas}


def ciclo(ids, sucesoras):
    """El primer ciclo (en orden de ID), empezando por su ID menor y con él repetido al final."""
    color, camino = {}, []

    def visita(n):
        color[n] = 1
        camino.append(n)
        for m in sucesoras[n]:
            if color.get(m) == 1:
                c = camino[camino.index(m):]
                k = c.index(min(c))
                return c[k:] + c[:k] + [min(c)]
            if m not in color and (r := visita(m)):
                return r
        color[n] = 2
        camino.pop()
        return None
    for n in sorted(ids):
        if n not in color and (r := visita(n)):
            return r
    return None


def ruta(lr, f, deps, duenos, ahora_s, con_orden=True):
    """Lo que la ruta crítica tiene que decir (en la forma de g14/hechos.json) con las reglas del contrato."""
    ahora = fecha(ahora_s)
    est = {t["id"]: t["estado"]["valor"] for t in f["estado"]["tareas"]}
    decl = {t["id"]: (t["declarado"] or {}).get("valor") for t in f["estado"]["tareas"]}
    hist = {k: h for k, (h, _) in f["historias"].items()}
    fs, plazos, franjas, pausas = lr["filas"], lr["plazos"], lr["franjas"], lr["pausas"]
    entrega = lr["entrega"]["valor"]
    fuera = {}
    for tid, _, _, tit in fs:
        if plano(tit).startswith("si "):
            fuera[tid] = "condicional"
        elif "[si da tiempo]" in plano(tit):
            fuera[tid] = "si_da_tiempo"
    cuentan = [t for t, _, _, _ in fs if t not in fuera]
    abiertas = [t for t in cuentan if est[t] not in HECHAS]
    previas = {t: {d: "depende_de" for d in deps[t] if d in cuentan} for t in cuentan}
    if con_orden:
        suyas = {}
        for t in cuentan:
            suyas.setdefault(duenos[t], []).append(t)
        for lista in suyas.values():
            for a, b in zip(lista, lista[1:]):
                previas[b].setdefault(a, "orden_del_plan")
    sucesoras = {t: sorted(b for b in cuentan if t in previas[b]) for t in cuentan}

    medidas = {}
    for tid, p, _, _ in fs:
        h, fr = hist[tid], franjas[tid][0]
        if est[tid] in HECHAS and not decl[tid] and h["primera_senal"] and h["hecha_en"] and fr:
            a, b = fecha(h["primera_senal"]), fecha(h["hecha_en"])
            seg = (b - a).total_seconds() - solape(a, b, pausas[p])
            medidas.setdefault(p, []).append((tid, max(1, math.floor(100 * seg / 60 / fr["min"] + 0.5))))
    personas = sorted(pausas)
    ritmos = {p: (min(r for _, r in medidas[p]), max(r for _, r in medidas[p]))
              for p in personas if len(medidas.get(p, [])) >= MINIMO}

    sin_plazo = {t: plazos[t]["motivo"] if plazos[t]["valor"] is None else franjas[t][1]
                 for t in abiertas if franjas[t][0] is None}
    con_franja = [t for t in abiertas if t not in sin_plazo]
    motivos = []
    if entrega is None:                        # dos horas en «Entrega:» no llegan aquí: manda la primera
        motivos.append("sin_entrega")
    c = ciclo(cuentan, sucesoras)
    if c:
        motivos.append("ciclo")
    if abiertas and not con_franja:            # solo si ninguna abierta que cuenta tiene franja («inicio»)
        motivos.append("sin_plazo")
    pocos = [p for p in personas if p not in ritmos and any(duenos[t] == p for t in abiertas)]
    if pocos:
        motivos.append("pocos_datos")

    fin = {}

    def termina(t):
        if t not in fin:
            p, h, fr = duenos[t], hist[t], franjas[t][0]
            antes = [termina(a) for a in previas[t] if a in con_franja]
            trabajado = 0.0
            if est[t] in SIGUE_HECHA and h["primera_senal"] and fecha(h["primera_senal"]) < ahora:
                a = fecha(h["primera_senal"])
                trabajado = (ahora - a).total_seconds() - solape(a, ahora, pausas[p])
            fin[t] = tuple(avanza(max([ahora] + [x[i] for x in antes]),
                                  max(0, math.ceil(fr["min"] * 60 * r / 100 - trabajado)), pausas[p])
                           for i, r in enumerate(ritmos[p]))
        return fin[t]
    rango, riesgos = None, []
    if not motivos:
        for t in con_franja:
            termina(t)
        temprano, tarde = max(x[0] for x in fin.values()), max(x[1] for x in fin.values())
        rango = {"temprano": z(temprano), "tarde": z(tarde),
                 "margen_min": math.floor((entrega - tarde).total_seconds() / 60),
                 "margen_max": math.floor((entrega - temprano).total_seconds() / 60)}
        veredicto = "a_tiempo" if tarde <= entrega else "justo" if temprano <= entrega else "no_llega"
        riesgos = sorted((t for t in con_franja if fin[t][1] > entrega), key=lambda t: (-fin[t][1].timestamp(), t))
    else:
        veredicto = "sin_estimacion"

    def arrastra(t):
        vistas, pila = set(), list(sucesoras[t])
        while pila:
            m = pila.pop()
            if m not in vistas:
                vistas.add(m)
                pila.extend(sucesoras[m])
        return sorted((vistas & set(abiertas)) - {t})
    vencidos = {t: {"plazo": z(plazos[t]["valor"]), "estado": est[t], "arrastra": arrastra(t)}
                for t in abiertas if plazos[t]["valor"] and plazos[t]["valor"] < ahora}
    en_riesgo = {}
    for t in sorted(vencidos):
        en_riesgo.setdefault(t, []).append("plazo_vencido")
    for t in sorted(vencidos):
        for m in vencidos[t]["arrastra"]:
            en_riesgo.setdefault(m, []).append(f"arrastrada_por {t}")
    for t in sorted(riesgos):
        en_riesgo.setdefault(t, []).append("estimacion")

    if rango:
        clave, cand = (lambda t: fin[t][1]), con_franja
    else:
        clave, cand = (lambda t: plazos[t]["valor"]), [t for t in abiertas if plazos[t]["valor"]]
    eslabones, actual = [], max(sorted(cand), key=clave, default=None)
    while actual is not None and actual not in eslabones:
        eslabones.append(actual)
        actual = max(sorted(a for a in previas[actual] if a in cand), key=clave, default=None)
    eslabones.reverse()
    cadena = [{"tarea": t, "por": "inicio" if i == 0 else previas[t][eslabones[i - 1]],
               "fin_temprano": z(fin[t][0]) if rango else None, "fin_tarde": z(fin[t][1]) if rango else None}
              for i, t in enumerate(eslabones)]
    # §11.4 (ajuste 3): {tarea, tipo, fin_tarde, dueno, en_cadena, viejo}, la más tardía primero; sin fin_temprano.
    # `viejo` es el de su tarjeta: con las fuentes frescas de los momentos, false (caso_g14 lo pone con el relay caído).
    riesgos = [{"tarea": t, "tipo": "estimacion", "fin_tarde": z(fin[t][1]), "dueno": duenos[t],
                "en_cadena": t in eslabones, "viejo": False} for t in riesgos]

    base = {}
    for p in personas:
        hechas = []
        for t, _ in medidas.get(p, []):
            primera = next((e["ts"] for e in f["atribuidos"] if e.get("tarea") == t and e["actor"]["persona"] == p), None)
            hechas.append({"tarea": t, "primera_senal": primera, "publicada_en": hist[t]["hecha_en"]})
        base[p] = {"n": len(hechas), "hechas": hechas,
                   "ritmo": {"min": ritmos[p][0], "max": ritmos[p][1]} if p in ritmos else None}

    sin = {}
    for p in personas:
        suyos = [fecha(e["ts"]) for e in f["atribuidos"] if e.get("tarea") and e["actor"]["persona"] == p]
        descansa = any(a <= ahora < b for a, b in pausas[p])
        if suyos and ahora - max(suyos) > UMBRAL_SENALES and not descansa and any(duenos[t] == p for t in abiertas):
            amb = sum(d["veces"] for d in f["estado"]["discrepancias"] if d["tipo"] == "atribucion_ambigua" and d.get("persona") == p)
            sin[p] = {"desde": z(max(suyos)), "discrepancias": {"atribucion_ambigua": amb} if amb else {},
                      "sin_tarea": sum(s["persona"] == p for s in f["estado"]["sin_tarea"]),
                      "tareas_abiertas": {t: est[t] for t in est if duenos[t] == p and est[t] in ATRIBUIBLES}}

    ent = lr["entrega"]
    otras = [{"texto": o["texto"], "valor": z(o["valor"]), "donde": o["donde"]} for o in lr["otras"]
             if not o["valor"] or o["valor"] != entrega]

    # §11.4, resumen (decisión 7B), con el orden que decidió el usuario: «plazo pasado» va antes que «sin contar…» y
    # «otra entrega…». Horas con la zona de la entrega (o del inicio).
    tz = (entrega or lr["inicio"]["valor"] or ahora).tzinfo

    def hm(d):
        return d.astimezone(tz).strftime("%H:%M")
    if rango:
        resumen = f"ruta: estimación {LEGIBLE[veredicto]} · fin {hm(temprano)}–{hm(tarde)} · entrega " \
                  f"{DIAS_R[entrega.astimezone(tz).weekday()]} {hm(entrega)}" + (" (confirmar)" if ent["confirmar"] else "")
    else:
        por = {"sin_entrega": "sin hora de entrega", "ciclo": "ciclo " + " → ".join(c or []),
               "sin_plazo": "sin plazo: " + ", ".join(sorted(sin_plazo)),
               "pocos_datos": "pocos datos: " + ", ".join(f"@{p} {len(medidas.get(p, []))} de {MINIMO}" for p in pocos)}
        resumen = f"ruta: sin estimación ({por[motivos[0]]})"
    pasados = sorted(vencidos, key=lambda t: (plazos[t]["valor"], t))
    if pasados:
        resumen += f" · {pasados[0]}: plazo pasado {hm(plazos[pasados[0]]['valor'])}" + \
                   (f" y {len(pasados) - 1} más" if len(pasados) > 1 else "")
    if rango and sin_plazo:
        resumen += f" · sin contar {', '.join(sorted(sin_plazo))} (sin plazo)"
    if otras:
        resumen += f" · otra entrega: {otras[0]['texto']} ({otras[0]['donde']})"
    return {
        "inicio": {"texto": lr["inicio"]["texto"], "valor": z(lr["inicio"]["valor"])},
        "entrega": {"texto": ent["texto"], "valor": z(entrega), "motivo": ent["motivo"], "confirmar": ent["confirmar"],
                    "discrepancias": otras, "bloquea_estimacion": False},
        "veredicto": veredicto,
        "cifra": {"hay": rango is not None, "motivos": motivos, "rango": rango},
        "base": base,
        "plazos": {t: {"hasta": x["hasta"], "efectivo": x["efectivo"], "heredado_de": x["heredado_de"],
                       "valor": z(x["valor"]), "motivo": TEXTO_MOTIVO.get(x["motivo"]), "motivo_contrato": x["motivo"]}
                   for t, x in plazos.items()},
        "sin_plazo": {t: TEXTO_MOTIVO[m] for t, m in sin_plazo.items()},
        "no_cuentan": {t: FUERA[m] for t, m in fuera.items()},
        "plazos_vencidos": vencidos, "en_riesgo": en_riesgo, "riesgos": riesgos, "sin_senales": sin,
        "ciclo": c,
        "descansos": {"resueltos": all(d["desde"] for d in lr["descansos"]),
                      "filas": [{"texto": d["texto"], "personas": d["personas"], "desde": z(d["desde"]),
                                 "hasta": z(d["hasta"])} for d in lr["descansos"]]},
        "tareas": est, "cadena": cadena, "resumen": corta(" ".join(resumen.split()), RESUMEN_MAX)}


def g14(cambia=None):
    bien, riesgo = correr("G14 (rama bien)", "guiones/G14.json"), correr("G14r (rama riesgo)", "guiones/G14r.json")
    datos = {"hechos": carga(os.path.join(AQUI, bien["hechos"])), "casos": carga(os.path.join(AQUI, "guiones/g14/casos.json"))}
    if cambia:
        cambia(datos)
    hechos, casos = datos["hechos"], datos["casos"]
    comprueba("G14: las dos ramas tienen las mismas tareas, entradas y hechos",
              bien["tareas"] == riesgo["tareas"] and bien["entradas"] == riesgo["entradas"]
              and bien["hechos"] == riesgo["hechos"])
    tabla = json.loads(texto(bien["tareas"]))
    personas = [p["persona"] for p in tabla["personas"]]
    p1, p2 = (texto(f["fichero"]) for f in hechos["entradas"]["plan.md"])
    e1, e2 = (texto(f["fichero"]) for f in hechos["entradas"]["equipo.md"])
    l1, l2 = leer_plan(p1, tabla["personas"]), leer_plan(p2, tabla["personas"])
    comprueba("G14: tareas.json es lo que compilar.leer_plan lee de plan-1.md", iguales_tareas(tabla["tareas"], l1))
    comprueba("G14: el ajuste (plan-2.md) no cambia IDs, dueños, bloques ni dependencias, y solo T18 cambia de título",
              [(t["id"], t["dueno"], t["bloque"], t["depende_de"]) for t in l1]
              == [(t["id"], t["dueno"], t["bloque"], t["depende_de"]) for t in l2]
              and [t["id"] for t, u in zip(l1, l2) if t["titulo"] != u["titulo"]] == ["T18"])
    f1, f2 = filas(p1), filas(p2)
    comprueba("G14: plan-1 solo con H+N, celdas vacías que heredan y una «hora por confirmar»",
              all(re.fullmatch(r"H\+\d+", h) or h in ("", "hora por confirmar") for _, _, h, _ in f1)
              and any(not h for _, _, h, _ in f1) and [h for _, _, h, _ in f1].count("hora por confirmar") == 1)
    comprueba("G14: plan-2 mezcla H+N (lo ya hecho) y día y hora",
              any(re.fullmatch(r"H\+\d+", h) for _, _, h, _ in f2)
              and any(re.fullmatch(r"(vie|sáb|dom) \d\d:\d\d", h) for _, _, h, _ in f2))
    comprueba("G14: «## Descansos» con 5 turnos (uno de dos personas) en las dos versiones",
              [len(descansos(p, None, MADRID, personas)) for p in (p1, p2)] == [5, 5]
              and [len(d["personas"]) for d in descansos(p2, None, MADRID, personas)].count(2) == 1)
    comprueba("G14: equipo-1 con «Inicio: por confirmar» y equipo-2 con Inicio; las dos con la misma Entrega y su zona",
              campo(e1, "Inicio") == "por confirmar" and hora_declarada(campo(e2, "Inicio"))[0] is not None
              and campo(e1, "Entrega") == campo(e2, "Entrega") and hora_declarada(campo(e1, "Entrega"))[0] is not None)
    deps = {t["id"]: t["depende_de"] for t in tabla["tareas"]}
    duenos = {t["id"]: t["dueno"] for t in tabla["tareas"]}
    guiones = {"G14.json": bien, "G14r.json": riesgo}
    fotos = {}
    for mo in hechos["momentos"]:
        fotos[mo["nombre"]] = momento_g14(mo, guiones[mo["guion"]], hechos, deps, duenos, personas)
    for caso in casos["casos"]:
        caso_g14(caso, next(m for m in hechos["momentos"] if m["nombre"] == caso["base"]), guiones, fotos, deps,
                 duenos, personas)


def reglas(nombre, esperado, real):
    """Lo que los hechos (o la espera de un caso) tienen que cumplir por forma, además de casar con `real`: así un hecho
    con un campo de más o con un motivo que ya no existe también falla."""
    cifra = esperado.get("cifra") or {}
    if "motivos" in cifra:
        comprueba(f"{nombre}: los motivos son del contrato y de las decisiones (sin «entrega_doble»; «sin_plazo» solo si "
                  "ninguna tarea abierta que cuenta tiene franja)",
                  set(cifra["motivos"]) <= set(MOTIVOS) and ("sin_plazo" in cifra["motivos"]) == (
                      "sin_plazo" in real["cifra"]["motivos"]), cifra["motivos"])
    if "riesgos" in esperado:
        fin = [r.get("fin_tarde") for r in esperado["riesgos"]]
        comprueba(f"{nombre}: riesgos con {{tarea, tipo, fin_tarde, dueno, en_cadena, viejo}} (sin fin_temprano), la más "
                  "tardía primero", all(set(r) == CAMPOS_RIESGO for r in esperado["riesgos"])
                  and all(fecha(a) >= fecha(b) for a, b in zip(fin, fin[1:])), esperado["riesgos"][:2])
    if "resumen" in esperado:
        r = esperado["resumen"]
        pos = {k: r.find(k) for k in ("plazo pasado", "sin contar", "otra entrega")}
        comprueba(f"{nombre}: en el resumen, «plazo pasado» va antes que «sin contar…» y «otra entrega…» "
                  f"({len(r)} de {RESUMEN_MAX})", len(r) <= RESUMEN_MAX and (pos["plazo pasado"] < 0 or all(
                      v < 0 or pos["plazo pasado"] < v for v in (pos["sin contar"], pos["otra entrega"]))), r)


def vigente(versiones, ahora):
    return [v["fichero"] for v in versiones if fecha(v["en_main_desde"]) <= fecha(ahora)][-1]


def momento_g14(mo, guion, hechos, deps, duenos, personas):
    nombre, ahora_s = f"G14 «{mo['nombre']}»", mo["ahora"]
    eq, pl = vigente(hechos["entradas"]["equipo.md"], ahora_s), vigente(hechos["entradas"]["plan.md"], ahora_s)
    comprueba(f"{nombre}: equipo.md y plan.md, los que están en main a esa hora", (eq, pl) == (mo["equipo.md"], mo["plan.md"]))
    f = foto(guion, ahora_s)
    lr = leer_entradas(texto(eq), texto(pl), personas)
    real = ruta(lr, f, deps, duenos, ahora_s)
    for k, que in (("tareas", "los estados de las 28 tareas son los del motor"),
                   ("inicio", "Inicio de equipo.md"),
                   ("entrega", "Entrega de equipo.md, con la discrepancia de Hitos al lado (no quita la estimación)"),
                   ("plazos", "el plazo de cada tarea (resuelto, heredado o con su motivo)"),
                   ("no_cuentan", "lo que no cuenta para la entrega (R8 B)"),
                   ("sin_plazo", "«sin plazo», aparte: ni a tiempo ni atrasadas, y no quitan la estimación del resto"),
                   ("descansos", "descansos (turnos con varias personas)"),
                   ("base", "la base de cada persona (tareas medidas, con franja, y su ritmo en % de la franja)"),
                   ("cifra", f"cifra: {mo['cifra'].get('motivos') or mo['cifra'].get('rango')}"),
                   ("veredicto", f"veredicto «{mo['veredicto']}»"),
                   ("plazos_vencidos", "plazos vencidos y lo que arrastran, por depende_de y por el orden del plan (R3 B)"),
                   ("riesgos", "lo que pone la entrega en riesgo por estimación"),
                   ("en_riesgo", "en riesgo, con su motivo"),
                   ("sin_senales", "sin señales"),
                   ("cadena", "la cadena, solo con tareas abiertas"),
                   ("resumen", f"resumen «{mo.get('resumen')}»")):
        esperado = mo.get(k)
        if k == "sin_senales":
            esperado = {p: {c: v for c, v in x.items() if c != "no_es"} for p, x in esperado.items()}
        dif = difiere(real[k], esperado)
        comprueba(f"{nombre}: {que}", not dif, dif[:6])
    reglas(nombre, mo, real)
    if "sin_orden_del_plan" in mo:
        otra = ruta(lr, f, deps, duenos, ahora_s, con_orden=False)
        esperado = mo["sin_orden_del_plan"]
        comprueba(f"{nombre}: con solo depende_de saldría «{esperado['veredicto']}»: la cadena de cada persona cambia el "
                  "veredicto", otra["veredicto"] == esperado["veredicto"] != real["veredicto"]
                  and not difiere(otra["cifra"]["rango"], esperado["rango"]))
    comprueba(f"{nombre}: nada «sin plazo» en riesgo por estimación, ni nada de quien no da señales",
              not set(real["sin_plazo"]) & {r["tarea"] for r in real["riesgos"]}
              and not {t for x in real["sin_senales"].values() for t in x["tareas_abiertas"]} & {r["tarea"] for r in real["riesgos"]})
    comprueba(f"{nombre}: la cadena no tiene tareas hechas ni fuera de la entrega",
              all(real["tareas"][e["tarea"]] not in HECHAS and e["tarea"] not in real["no_cuentan"] for e in real["cadena"]))
    return f


def caso_g14(caso, mo, guiones, fotos, deps, duenos, personas):
    nombre = f"G14 caso «{caso['id']}» ({caso['base']})"
    ahora = caso.get("ahora", mo["ahora"])
    f = foto(guiones[mo["guion"]], caso["estado_a"]) if "estado_a" in caso else fotos[mo["nombre"]]
    md_eq = reemplaza(texto(mo["equipo.md"]), caso.get("equipo.md", []), nombre)
    md_plan = reemplaza(texto(mo["plan.md"]), caso.get("plan.md", []), nombre)
    lr = leer_entradas(md_eq, md_plan, personas)
    if caso.get("relee_plan"):
        deps = {t["id"]: t["depende_de"] for t in leer_plan(md_plan, json.loads(texto(guiones[mo["guion"]]["tareas"]))["personas"])}
    real = ruta(lr, f, deps, duenos, ahora)
    real["sin_orden_del_plan"] = {k: v for k, v in ruta(lr, f, deps, duenos, ahora, con_orden=False).items()
                                  if k in ("veredicto", "cifra", "cadena")}
    leidas = {"relay": caso.get("relay_leido_en", ahora), "git": ahora, "github": ahora}
    real["dato_mas_viejo"] = min(leidas.values(), key=fecha)
    real["viejo"] = fecha(ahora) - fecha(real["dato_mas_viejo"]) > timedelta(seconds=300)
    for r in real["riesgos"]:
        r["viejo"] = real["viejo"]                   # el de su tarjeta: todas vienen del relay
    dif = difiere(caso["espera"], real)
    comprueba(f"{nombre}: {caso['que']}", not dif, dif[:6])
    reglas(nombre, caso["espera"], real)


# ===================================================================================================== controles
def pon(ruta_, valor):
    """Un cambio en los hechos o los casos: `ruta_` es una lista de claves e índices; el último recibe `valor` (None:
    se borra; una función: se le aplica al valor que había)."""
    def cambia(h):
        for k in ruta_[:-1]:
            h = h[k]
        if valor is None:
            del h[ruta_[-1]]
        else:
            h[ruta_[-1]] = valor(h[ruta_[-1]]) if callable(valor) else valor
    return cambia


M = ["hechos", "momentos"]
CONTROLES = [
    ("G13 M2: N2 sin «trabajo nuevo desde»", g13, M + [1, "notas", "N2", "trabajo_nuevo_desde"], ""),
    ("G13 M3: N6 «cubierta» con T23 solo reclamada", g13, M + [2, "notas", "N6", "estado"], "cubierta"),
    ("G13 M2: N5 sin corregir", g13, M + [1, "notas", "N5", "corregida_por"], ""),
    ("G13 M1: N4 sin la ⚑ de T20", g13, M + [0, "notas", "N4", "cerradas_a_mano"], []),
    ("G13 M1: N1 (solo en el pitch) como «sin tarea» (A2)", g13, M + [0, "notas", "N1", "estado"], "sin_tarea"),
    ("G13 M1: «sin cubrir» sin las declaradas ni la del pitch (A2)", g13, M + [0, "cuenta", "sin_cubrir"], 0),
    ("G13 M3: la evidencia de T11, el primer sha (M6)", g13, M + [2, "notas", "N2", "evidencia", 0, "sha"], "111c0de"),
    ("G13 M3: la evidencia de T11 con la hora de la primera publicación, no la de la última (punto 1)", g13,
     M + [2, "notas", "N2", "evidencia", 0, "observado_en"], "2026-09-18T21:20:00Z"),
    ("G13 M3: la evidencia de T11 como sha suelto, sin su hora (punto 1)", g13,
     M + [2, "notas", "N2", "evidencia", 0], "112c0de"),
    ("G13 M2b: T11 parada pierde la evidencia de su última publicación (punto 1)", g13,
     M + [3, "notas", "N2", "evidencia"], []),
    ("G13 caso ambigua: la ambigua contada como «sin tarea» (punto 5)", g13, ["casos", "casos", 0, "espera", "cuenta"],
     lambda c: dict(c, ambiguas=0, sin_tarea=c["sin_tarea"] + 1)),
    ("G13 caso ambigua: la ambigua fuera del desglose por fuerza (punto 5)", g13,
     ["casos", "casos", 0, "espera", "cuenta", "sin_cubrir_por_fuerza", 2, "n"], 1),
    ("G13 M1: cuenta sin el grupo «ambiguas» (punto 5)", g13, M + [0, "cuenta", "ambiguas"], None),
    ("G13 T11 parada: N2 deja de estar cubierta (M7)", g13, M + [3, "notas", "N2", "estado"], "en_curso"),
    ("G13 M2: orden con N3 antes que N6", g13, M + [1, "orden"], ["N1", "N4", "N3", "N6", "N7", "N8", "N2", "N5"]),
    ("G13 caso ambigua: N3 «en curso»", g13, ["casos", "casos", 0, "espera", "notas", "N3", "estado"], "en_curso"),
    ("G13 caso Prueba que falla: la nota deja de estar cubierta", g13,
     ["casos", "casos", 2, "espera", "notas", "N2", "estado"], "en_curso"),
    ("G14 inicio: T20 con plazo", g14, M + [0, "sin_plazo", "T20"], None),
    ("G14 inicio: cifra con pocos datos", g14, M + [0, "cifra", "hay"], True),
    ("G14 inicio: T01 y T02 medidas sin franja (M1)", g14, M + [0, "base", "persona-a", "n"], 2),
    ("G14 mitad bien: T28 sin plazo quita la estimación (A3)", g14, M + [1, "veredicto"], "sin_estimacion"),
    ("G14 mitad con riesgo: «a tiempo»", g14, M + [2, "veredicto"], "a_tiempo"),
    ("G14 mitad con riesgo: T04 solo arrastra a T05 (A4)", g14, M + [2, "plazos_vencidos", "T04", "arrastra"], ["T05"]),
    ("G14 mitad con riesgo: persona-c con señales", g14, M + [2, "sin_senales", "persona-c"], None),
    ("G14 mitad con riesgo: la discrepancia de la entrega bloquea", g14, M + [2, "entrega", "bloquea_estimacion"], True),
    ("G14 mitad con riesgo: la cadena empieza en T03, ya hecha (M16)", g14, M + [2, "cadena", 0, "tarea"], "T03"),
    ("G14 caso dos horas: sin estimación (punto 2)", g14, ["casos", "casos", 2, "espera", "veredicto"], "sin_estimacion"),
    ("G14 caso dos horas: con el motivo «entrega_doble» (punto 2)", g14, ["casos", "casos", 2, "espera", "cifra", "motivos"],
     ["entrega_doble"]),
    ("G14 caso dos horas: manda la segunda (11:00) (punto 2)", g14, ["casos", "casos", 2, "espera", "entrega", "valor"],
     "2026-09-20T09:00:00Z"),
    ("G14 caso dos horas: la segunda no va a otras entregas (punto 2)", g14,
     ["casos", "casos", 2, "espera", "entrega", "discrepancias"], lambda d: d[1:]),
    ("G14 inicio: sin «sin_plazo» aunque ninguna abierta tenga franja (punto 3)", g14, M + [0, "cifra", "motivos"],
     ["pocos_datos"]),
    ("G14 mitad bien: «sin_plazo» como motivo con T28 (punto 3)", g14, M + [1, "cifra", "motivos"], ["sin_plazo"]),
    ("G14 mitad con riesgo: resumen con «plazo pasado» al final (punto 3)", g14, M + [2, "resumen"],
     "ruta: estimación no llega · fin 09:32–09:32 · entrega dom 10:00 · sin contar T28 (sin plazo) · T04: plazo pasado "
     "23:00 y 3 más"),
    ("G14 mitad con riesgo: riesgos de la más temprana a la más tardía (punto 4)", g14, M + [2, "riesgos"],
     lambda r: r[::-1]),
    ("G14 mitad con riesgo: riesgos con fin_temprano (punto 4)", g14, M + [2, "riesgos", 0],
     lambda r: dict(r, fin_temprano=r["fin_tarde"])),
    ("G14 mitad con riesgo: T09 fuera de la cadena (punto 4)", g14, M + [2, "riesgos", 0, "en_cadena"], False),
    ("G14 mitad con riesgo: T19 de otra persona (punto 4)", g14, M + [2, "riesgos", 1, "dueno"], "persona-a"),
    ("G14 caso descanso de Todos: sin efecto en el rango", g14, ["casos", "casos", 7, "espera", "cifra", "rango", "tarde"],
     "2026-09-19T16:52:18Z"),
]


def main():
    global fallos, callado
    g13()
    g14()
    print()
    for nombre, funcion, ruta_, valor in CONTROLES:     # con un hecho cambiado, tiene que fallar
        antes, callado = fallos, True
        try:
            funcion(pon(ruta_, valor))
        except (KeyError, IndexError, TypeError):
            fallos += 1
        detecta, fallos, callado = fallos > antes, antes, False
        comprueba(f"control ({nombre}): lo detecta", detecta)
    print(f"\n{fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
