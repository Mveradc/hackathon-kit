# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""G13 (vista de jurado, R-35) y G14 (ruta crítica, R-36) de M10: los guiones se cargan y lo que tiene que salir
(guiones/g13/hechos.json y guiones/g14/hechos.json) es coherente con sus entradas.

No usa la vista ni sus nombres de campo (los fija K-101/K-105): comprueba los hechos contra
  - el motor de estados de verdad (simula.ejecutar y modelo.calcular), con cada evento y cada estado.json validados
    contra los esquemas de docs/hackathon-os/contratos/;
  - las entradas: criterios.md, plan.md y pitch.md (G13); equipo.md, plan.md y «## Descansos» (G14);
  - para el veredicto de la ruta, una cota con la franja del plan (ADR-0013, R4 A) y el ritmo por persona (R5 A,
    N = 3) en cuatro variantes (descansos restados o no; filas que no cuentan dentro del reparto de la franja o no): un
    «a tiempo» tiene que salir con el ritmo más lento medido en las cuatro, y un «no llega», con el más rápido en las
    cuatro. Así el veredicto no depende de cómo K-102 fije esos detalles.
G14 tiene dos ramas con las mismas entradas: G14.json («inicio» y «mitad bien») y G14r.json («mitad con riesgo»).

Uso: uv run --no-project evals/coordinacion/simulador/g13_g14.py   (0 OK · 1 falla)
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path[:0] = [os.path.join(KIT, "hkos"), AQUI]
from compilar import leer_plan  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import ATRIBUIBLES, fecha  # noqa: E402
from modelo import atribuir, calcular  # noqa: E402
from simula import carga, ejecutar, montar  # noqa: E402

MADRID = timezone(timedelta(hours=2))      # Europe/Madrid en septiembre (CEST): sin tzdata en Windows, fija
UMBRAL_SENALES = timedelta(seconds=1200)   # sin señales: más que el umbral de parada sin nada atribuido
MARGEN = timedelta(hours=2)                # «a tiempo»: el extremo lento del rango, como poco 2 h antes de la entrega
N_MIN = 3
HECHAS = ("publicada", "cerrada")
ETIQUETA = re.compile(r"\(criterios: (\d{4}-\d\d-\d\d \d\d:\d\d)(?: · ([^)]+))?\)")
CABECERA = re.compile(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+) \((.+)\)$")
CORRIGE = re.compile(r"corrige la nota del (\d{4}-\d\d-\d\d \d\d:\d\d)")
DIAS = {"vie": 18, "sáb": 19, "dom": 20}  # el fin de semana del reto 03 (vie 18 sep 2026)
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
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local(cita):
    return datetime.strptime(cita, "%Y-%m-%d %H:%M").replace(tzinfo=MADRID)


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
    """(estado.json, eventos atribuidos hasta `ahora`, eventos montados, tareas) de un guion."""
    tareas, personas, issues, eventos, _ = montar(guion, AQUI)
    estado = calcular(tareas, issues, eventos, personas, ahora, guion.get("umbral_parada_s", 1200))
    t = fecha(ahora)
    hasta = {k: dict(v, acciones=[a for a in v["acciones"] if fecha(a["ts"]) <= t]) for k, v in issues.items()}
    atribuidos, _, _ = atribuir(tareas, hasta, [e for e in eventos if fecha(e["ts"]) <= t],
                                {p["persona"] for p in personas})
    return estado, atribuidos, eventos, tareas


def iguales_tareas(json_tareas, plan_tareas):
    campos = ("id", "titulo", "bloque", "dueno", "depende_de")
    return [{k: t[k] for k in campos} for t in json_tareas] == [{k: t[k] for k in campos} for t in plan_tareas]


def tabla_plan(rel):
    return json.loads(texto(rel))["personas"]


# =========================================================================================================== G13
def leer_notas(md):
    notas, actual = [], None
    for linea in md.split("\n"):
        m = CABECERA.match(linea)
        if m:
            actual = {"cabecera": linea, "cita": m.group(1), "quien": m.group(2), "papel": m.group(3), "campos": {}}
            notas.append(actual)
        elif actual and linea.startswith("- ") and ":" in linea:
            k, v = linea[2:].split(":", 1)
            actual["campos"][k] = v.strip()
    return notas


def casan(cita, quien, notas):
    return [i for i, n in enumerate(notas) if n["cita"] == cita and (quien is None or n["quien"].startswith(quien))]


def citas(md, notas, por_fila):
    """{índice de nota: [tareas]} (por_fila) o {índice} de las etiquetas de un fichero. Una cita que casa con más de
    una nota o con ninguna se devuelve aparte."""
    enlaces, malas = {}, []
    for linea in md.split("\n"):
        fila = re.match(r"^\| (T\d{2,3}) \|", linea)
        for m in ETIQUETA.finditer(linea):
            c = casan(m.group(1), m.group(2), notas)
            if len(c) != 1:
                malas.append((m.group(0), len(c)))
                continue
            if por_fila and fila:
                enlaces.setdefault(c[0], []).append(fila.group(1))
            elif not por_fila:
                enlaces.setdefault(c[0], [])
    return enlaces, malas


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


def g13(cambia=None):
    guion = correr("G13", "guiones/G13.json")
    hechos = carga(os.path.join(AQUI, guion["hechos"]))
    if cambia:
        cambia(hechos)
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
    mismo = [ids[j] if (j := next((k for k, m in enumerate(notas) if k != i and m["cita"] == n["cita"]), None)) is not None
             else None for i, n in enumerate(notas)]
    comprueba("G13: dos notas en el mismo minuto, de personas distintas", mismo == [h["mismo_minuto_que"] for h in hn]
              and sum(x is not None for x in mismo) == 2)
    corrige = []
    for n in notas:
        m = CORRIGE.search(n["campos"].get("Qué dijo", ""))
        c = casan(m.group(1), None, notas) if m else []
        corrige.append(ids[c[0]] if len(c) == 1 else None)
    comprueba("G13: una nota corrige a otra (y la cita casa con una sola)", corrige == [h["corrige"] for h in hn]
              and sum(x is not None for x in corrige) == 1)
    comprueba("G13: una nota de fuerza «dato» y una con texto imperativo",
              [n["campos"]["Fuerza"] for n in notas].count("dato") == 1
              and [bool(re.match(r"«(Haced|Haz|Poned|Olvidaos)", n["campos"]["Qué dijo"])) for n in notas]
              == [h["texto_imperativo"] for h in hn])

    en_plan, malas_plan = citas(plan_md, notas, True)
    en_pitch, malas_pitch = citas(pitch_md, notas, False)
    comprueba("G13: cada etiqueta del plan y del pitch casa con una sola nota", not malas_plan and not malas_pitch,
              f"{malas_plan} {malas_pitch}")
    comprueba("G13: la cita sin «· quién» del minuto repetido casaría con dos notas (por eso el plan lleva «· quién»)",
              len(casan(notas[ids.index("N2")]["cita"], None, notas)) == 2)
    comprueba("G13: qué tareas citan cada nota y si la cita el pitch, como en los hechos",
              all(sorted(en_plan.get(i, [])) == sorted(h["citada_en_plan"]) and (i in en_pitch) == h["citada_en_pitch"]
                  for i, h in enumerate(hn)))
    comprueba("G13: una nota de fuerza «dato» recogida solo en el pitch",
              any(h["fuerza"] == "dato" and h["citada_en_pitch"] and not h["citada_en_plan"] for h in hn))

    desde_plan = fecha(hechos["entradas"]["plan.md"]["en_main_desde"])
    desde_pitch = fecha(hechos["entradas"]["pitch.md"]["en_main_desde"])
    for mo in hechos["momentos"]:
        ahora = mo["ahora"]
        estado, atribuidos, eventos, _ = foto(guion, ahora)
        tareas = {t["id"]: t for t in estado["tareas"]}
        comprueba(f"G13 {mo['nombre']}: el plan con etiquetas y el pitch ya están en main",
                  desde_plan <= fecha(ahora) and desde_pitch <= fecha(ahora))
        comprueba(f"G13 {mo['nombre']}: el estado de las tareas de los hechos es el del motor",
                  all(tareas[k]["estado"]["valor"] == v for k, v in mo["tareas"].items()))
        presentes = [i for i, h in enumerate(hn) if fecha(h["en_main_desde"]) <= fecha(ahora)]
        comprueba(f"G13 {mo['nombre']}: las notas de los hechos son las que están en main ({len(presentes)})",
                  sorted(mo["notas"]) == sorted(ids[i] for i in presentes))
        for i in presentes:
            h, esperado = hn[i], mo["notas"][ids[i]]
            real = nota_en(i, notas, ids, presentes, en_plan, en_pitch, tareas, eventos, atribuidos, ahora)
            dif = {k: (real[k], esperado.get(k)) for k in real if real[k] != esperado.get(k)}
            comprueba(f"G13 {mo['nombre']}, {ids[i]} ({h['cita']} · {h['quien']}): {esperado['estado']}", not dif, str(dif))
            comprueba(f"G13 {mo['nombre']}, {ids[i]}: nunca «cubierta» sin la evidencia de todas sus tareas",
                      esperado["estado"] != "cubierta" or len(esperado["evidencia"]) == len(esperado["tareas"]) > 0)
    c = hechos["sin_senales"]["persona-c"]
    _, atribuidos, _, _ = foto(guion, hechos["momentos"][-1]["ahora"])
    ultimo = max(e["ts"] for e in atribuidos if e["actor"]["persona"] == "persona-c" and e.get("tarea"))
    comprueba("G13: persona-c no da señales desde la hora de los hechos", ultimo == c["desde"], ultimo)


def nota_en(i, notas, ids, presentes, en_plan, en_pitch, tareas, eventos, atribuidos, ahora):
    """Lo que la nota `i` tiene que decir con las reglas de los hechos (J3 A, J4 A, J5 B, J6 B)."""
    suyas = en_plan.get(i, [])
    estados = {tid: tareas[tid]["estado"]["valor"] for tid in suyas}
    evidencia, nuevo = [], []
    for tid in suyas:
        pubs = publicaciones(eventos, tid, ahora)
        if pubs:
            ts, sha = pubs[-1]
            evidencia.append({"tarea": tid, "sha": sha, "observado_en": ts})
            if estados[tid] not in HECHAS:      # J6 B: trabajo nuevo desde la primera señal tras publicar
                nuevo += [e["ts"] for e in atribuidos if e.get("tarea") == tid and fecha(e["ts"]) > fecha(ts)][:1]
            elif estados[tid] == "publicada" and tareas[tid]["estado"]["observado_en"] != ts:
                evidencia[-1]["observado_en"] = None    # el motor y el push no coinciden: que falle
    publicada = {e["tarea"] for e in evidencia}
    corregida = [ids[j] for j in presentes if j > i
                 and (m := CORRIGE.search(notas[j]["campos"].get("Qué dijo", ""))) and m.group(1) == notas[i]["cita"]]
    if corregida:
        valor = "corregida"
    elif suyas and all(t in publicada or estados[t] in HECHAS for t in suyas):
        valor = "cubierta"
    elif suyas and any(t in publicada or estados[t] not in ("lista", "pendiente", "reclamada") for t in suyas):
        valor = "en_curso"
    elif suyas:
        valor = "planificada"
    else:
        valor = "recogida_en_pitch" if i in en_pitch else "sin_cubrir"
    return {"estado": valor, "tareas": estados, "evidencia": evidencia,
            "trabajo_nuevo_desde": min(nuevo) if nuevo else None,
            "cerradas_a_mano": [t for t in suyas if (tareas[t]["declarado"] or {}).get("valor") == "cerrada"],
            "corregida_por": corregida[0] if corregida else None, "tambien_en_pitch": i in en_pitch}


# =========================================================================================================== G14
def filas(md):
    """[(tid, persona, Hasta crudo, título)] de «## Por persona», en el orden del plan."""
    salida, persona = [], None
    for linea in md.split("\n"):
        m = re.match(r"^### Persona ([A-Z]) ·", linea)
        if m:
            persona = "persona-" + m.group(1).lower()
        m = re.match(r"^\| (T\d{2,3}) \|(.*)\|$", linea)
        if m:
            c = [x.strip() for x in m.group(2).split("|")]
            salida.append((m.group(1), persona, c[0], c[2]))
    return salida


def campo(md, nombre):
    m = re.search(rf"^- {nombre}: (.+)$", md, re.M)
    return m.group(1).strip() if m else None


def hora_equipo(valor):
    m = re.fullmatch(r"(\d{4}-\d\d-\d\d \d\d:\d\d) \(Europe/Madrid\)", valor or "")
    return local(m.group(1)) if m else None


def resolver(hasta, inicio):
    """(datetime o None, motivo) de un Hasta ya heredado (R2 A)."""
    m = re.fullmatch(r"H\+(\d+)", hasta)
    if m or re.fullmatch(r"(vie|sáb|dom) \d\d:\d\d", hasta):
        if inicio is None:
            return None, "sin Inicio"
        if m:
            return inicio + timedelta(hours=int(m.group(1))), None
        dia, hm = hasta.split()
        return datetime(2026, 9, DIAS[dia], *map(int, hm.split(":")), tzinfo=MADRID), None
    return None, "plazo sin resolver"


def plazos(fs, inicio):
    out, persona, previo, de = {}, None, None, None
    for tid, p, h, _ in fs:
        if p != persona:
            persona, previo, de = p, None, None
        if h:
            previo, de = h, tid
        valor, motivo = resolver(previo, inicio)
        out[tid] = {"hasta": h, "efectivo": previo, "heredado_de": None if h else de,
                    "valor": z(valor) if valor else None, "motivo": motivo}
    return out


def no_cuentan(fs):
    return {tid: "empieza por «Si …»" if tit.startswith("Si ") else "lleva [SI DA TIEMPO]"
            for tid, _, _, tit in fs if tit.startswith("Si ") or "[SI DA TIEMPO]" in tit}


def descansos(md, inicio):
    """[(texto, [personas], desde, hasta)] de «## Descansos»; sin Inicio, sin horas."""
    sec = md.split("## Descansos", 1)[1] if "## Descansos" in md else ""
    salida = []
    for m in re.finditer(r"^\| ((vie|sáb|dom) (\d\d:\d\d)–(?:(vie|sáb|dom) )?(\d\d:\d\d)) \| (.+?) \|$", sec, re.M):
        ps = ["persona-" + x[-1].lower() for x in re.findall(r"Persona [A-Z]", m.group(6))]
        if inicio is None:
            salida.append((m.group(1), ps, None, None))
            continue
        a = datetime(2026, 9, DIAS[m.group(2)], *map(int, m.group(3).split(":")), tzinfo=MADRID)
        b = datetime(2026, 9, DIAS[m.group(4) or m.group(2)], *map(int, m.group(5).split(":")), tzinfo=MADRID)
        salida.append((m.group(1), ps, a, b))
    return salida


def solape(a, b, pausas):
    return sum((min(b, y) - max(a, x) for x, y in pausas if min(b, y) > max(a, x)), timedelta())


def avanzar(t, trabajo, pausas):
    for a, b in sorted(pausas):
        if b <= t:
            continue
        if a > t:
            if trabajo <= a - t:
                return t + trabajo
            trabajo -= a - t
        t = max(t, b)
    return t + trabajo


def franjas(fs, pl, inicio, pausas, restar, con_nc, nc):
    """R4 A: del Hasta de la fila anterior de la persona (o del inicio) al de esta; las filas que heredan se reparten
    la franja del bloque. Variantes: descansos restados o no; filas que no cuentan dentro del reparto o no."""
    out, i = {}, 0
    while i < len(fs):
        tid, p = fs[i][0], fs[i][1]
        if i == 0 or fs[i - 1][1] != p:
            previo = inicio
        j = i + 1
        while j < len(fs) and fs[j][1] == p and not fs[j][2]:
            j += 1
        bloque = [f[0] for f in fs[i:j]]
        fin = pl[tid]["valor"] and fecha(pl[tid]["valor"])
        miembros = [b for b in bloque if con_nc or b not in nc]
        if fin is None or previo is None:
            out.update({b: None for b in bloque})
        else:
            dur = (fin - previo) - (solape(previo, fin, pausas[p]) if restar else timedelta())
            out.update({b: dur / len(miembros) if b in miembros else None for b in bloque})
            previo = fin
        i = j
    return out


def estimar(fs, est, fr, ritmo, pausas, primera, deps, ahora, restar, descontar, nc):
    """Hora de fin de cada tarea que cuenta: cada persona hace las suyas en el orden del plan, después de sus
    dependencias, a su ritmo y saltando sus descansos (si `restar`). `descontar`: lo ya trabajado en las empezadas."""
    fs = [f for f in fs if f[0] not in nc]
    fin, previa, ultima = {}, {}, {}
    for tid, p, _, _ in fs:
        previa[tid], ultima[p] = ultima.get(p), tid

    def termina(tid):
        if tid not in fin:
            if est[tid] in HECHAS:
                fin[tid] = ahora
            else:
                p = next(f[1] for f in fs if f[0] == tid)
                antes = [termina(x) for x in [previa[tid]] + deps[tid] if x]
                inicio = max([ahora] + antes)
                trabajo = (fr[tid] or timedelta()) * ritmo[p]
                if descontar and tid in primera and est[tid] not in ("lista", "pendiente", "reclamada"):
                    trabajo = max(timedelta(), trabajo - (ahora - primera[tid]))
                fin[tid] = avanzar(inicio, trabajo, pausas[p] if restar else [])
        return fin[tid]
    for tid, _, _, _ in fs:
        termina(tid)
    return fin


def g14(cambia=None):
    bien, riesgo = correr("G14 (rama bien)", "guiones/G14.json"), correr("G14r (rama riesgo)", "guiones/G14r.json")
    hechos = carga(os.path.join(AQUI, bien["hechos"]))
    if cambia:
        cambia(hechos)
    comprueba("G14: las dos ramas tienen las mismas tareas, entradas y hechos",
              bien["tareas"] == riesgo["tareas"] and bien["entradas"] == riesgo["entradas"]
              and bien["hechos"] == riesgo["hechos"])
    tabla = json.loads(texto(bien["tareas"]))
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
    comprueba("G14: plan-2 mezcla H+N (lo ya hecho) y día y hora; plan-1 tiene una fila «Si …» y plan-2, un [SI DA TIEMPO]",
              any(re.fullmatch(r"H\+\d+", h) for _, _, h, _ in f2) and any(re.fullmatch(r"(vie|sáb|dom) \d\d:\d\d", h)
                                                                       for _, _, h, _ in f2)
              and list(no_cuentan(f1)) == ["T10"] and list(no_cuentan(f2)) == ["T10", "T18"])
    comprueba("G14: «## Descansos» con 5 turnos en las dos versiones", len(descansos(p1, None)) == len(descansos(p2, None)) == 5)
    comprueba("G14: equipo-1 con «Inicio: por confirmar» y equipo-2 con Inicio; las dos con la misma Entrega y su zona",
              campo(e1, "Inicio") == "por confirmar" and hora_equipo(campo(e2, "Inicio")) is not None
              and campo(e1, "Entrega") == campo(e2, "Entrega") and hora_equipo(campo(e1, "Entrega")) is not None)
    hitos = [re.match(r"^\| ([^|]+?) \|", ln).group(1) for p in (p1, p2) for ln in p.split("\n")
             if ln.startswith("|") and "Entrega final" in ln]
    m = re.fullmatch(r"(vie|sáb|dom) (\d+) sep (\d\d):(\d\d)", hitos[0])
    entrega = hora_equipo(campo(e1, "Entrega"))
    hito = datetime(2026, 9, int(m.group(2)), int(m.group(3)), int(m.group(4)), tzinfo=MADRID)
    comprueba(f"G14: la fila Entrega de Hitos («{hitos[0]}») no coincide con equipo.md, en las dos versiones",
              len(set(hitos)) == 1 and hito != entrega)
    deps = {t["id"]: t["depende_de"] for t in tabla["tareas"]}
    duenos = {t["id"]: t["dueno"] for t in tabla["tareas"]}
    guiones = {"G14.json": bien, "G14r.json": riesgo}
    for mo in hechos["momentos"]:
        momento_g14(mo, guiones[mo["guion"]], hechos, entrega, hito, deps, duenos)


def vigente(versiones, ahora):
    return [v["fichero"] for v in versiones if fecha(v["en_main_desde"]) <= fecha(ahora)][-1]


def momento_g14(mo, guion, hechos, entrega, hito, deps, duenos):
    nombre, ahora_s = f"G14 «{mo['nombre']}»", mo["ahora"]
    ahora = fecha(ahora_s)
    eq, pl_rel = vigente(hechos["entradas"]["equipo.md"], ahora_s), vigente(hechos["entradas"]["plan.md"], ahora_s)
    comprueba(f"{nombre}: equipo.md y plan.md, los que están en main a esa hora", (eq, pl_rel) == (mo["equipo.md"], mo["plan.md"]))
    md_eq, md_plan = texto(eq), texto(pl_rel)
    inicio = hora_equipo(campo(md_eq, "Inicio"))
    fs = filas(md_plan)
    estado, atribuidos, _, _ = foto(guion, ahora_s)
    est = {t["id"]: t["estado"]["valor"] for t in estado["tareas"]}
    comprueba(f"{nombre}: los estados de las 28 tareas son los del motor", est == mo["tareas"],
              str({k: (v, mo["tareas"].get(k)) for k, v in est.items() if v != mo["tareas"].get(k)}))
    comprueba(f"{nombre}: Inicio ({campo(md_eq, 'Inicio')}) y Entrega de equipo.md, con la discrepancia de Hitos al lado",
              mo["inicio"] == {"texto": campo(md_eq, "Inicio"), "valor": z(inicio) if inicio else None}
              and mo["entrega"]["valor"] == z(entrega) and mo["entrega"]["texto"] == campo(md_eq, "Entrega")
              and [d["valor"] for d in mo["entrega"]["discrepancias"]] == [z(hito)]
              and not mo["entrega"]["bloquea_estimacion"])
    pl = plazos(fs, inicio)
    comprueba(f"{nombre}: el plazo de cada tarea (resuelto, heredado o con su motivo)", pl == mo["plazos"],
              str({k: (v, mo["plazos"].get(k)) for k, v in pl.items() if v != mo["plazos"].get(k)}))
    nc = no_cuentan(fs)
    comprueba(f"{nombre}: no cuentan {sorted(nc)}", nc == mo["no_cuentan"])
    sin_plazo = {t: x["motivo"] for t, x in pl.items() if x["valor"] is None and est[t] not in HECHAS and t not in nc}
    comprueba(f"{nombre}: «sin plazo» ({len(sin_plazo)}), ni a tiempo ni atrasadas", sin_plazo == mo["sin_plazo"]
              and not set(sin_plazo) & set(mo["en_riesgo"]))
    vencidos = {t: {"plazo": x["valor"], "estado": est[t]} for t, x in pl.items()
                if x["valor"] and fecha(x["valor"]) < ahora and est[t] not in HECHAS and t not in nc}
    comprueba(f"{nombre}: plazos vencidos {sorted(vencidos)}", vencidos == mo["plazos_vencidos"])
    ds = descansos(md_plan, inicio)
    comprueba(f"{nombre}: descansos {'resueltos' if inicio else 'sin resolver (sin Inicio)'}",
              [(d["texto"], d["personas"], d["desde"], d["hasta"]) for d in mo["descansos"]["filas"]]
              == [(a, b, z(c) if c else None, z(d) if d else None) for a, b, c, d in ds]
              and mo["descansos"]["resueltos"] == (inicio is not None))
    pausas = {p: [(c, d) for _, ps, c, d in ds if c and p in ps] for p in ("persona-a", "persona-b", "persona-c")}

    primera = {}
    for e in atribuidos:
        if e.get("tarea") and e["actor"]["persona"] == duenos.get(e["tarea"]):
            primera.setdefault(e["tarea"], fecha(e["ts"]))
    obs = {t["id"]: fecha(t["estado"]["observado_en"]) for t in estado["tareas"]}
    base = {p: [{"tarea": t, "primera_senal": z(primera[t]), "publicada_en": z(obs[t])}
                for t, _, _, _ in sorted(fs) if duenos[t] == p and est[t] in HECHAS] for p in pausas}
    comprueba(f"{nombre}: la base (tareas hechas, primera señal y publicación) de cada persona",
              all(mo["base"][p]["hechas"] == base[p] and mo["base"][p]["n"] == len(base[p]) for p in base),
              str({p: [x["tarea"] for x in b] for p, b in base.items()}))
    pocos = any(len(b) < N_MIN for b in base.values())
    comprueba(f"{nombre}: {'sin cifra (pocos datos, n de 3)' if pocos else 'hay cifra (n ≥ 3 por persona)'}",
              mo["cifra"]["hay"] == (not pocos) and (mo["veredicto"] == "sin_estimacion") == pocos)

    sin = {}
    for p in pausas:
        suyos = [fecha(e["ts"]) for e in atribuidos if e.get("tarea") and e["actor"]["persona"] == p]
        if suyos and ahora - max(suyos) > UMBRAL_SENALES:
            amb = sum(d["veces"] for d in estado["discrepancias"] if d["tipo"] == "atribucion_ambigua" and d.get("persona") == p)
            sin[p] = {"desde": z(max(suyos)), "discrepancias": {"atribucion_ambigua": amb} if amb else {},
                      "sin_tarea": sum(s["persona"] == p for s in estado["sin_tarea"]),
                      "tareas_abiertas": {t: est[t] for t in est if duenos[t] == p and est[t] in ATRIBUIBLES}}
    comprueba(f"{nombre}: sin señales {sorted(sin) or '—'}", {p: {k: v for k, v in x.items() if k != "no_es"}
                                                              for p, x in mo["sin_senales"].items()} == sin, str(sin))
    abiertas = {t for x in sin.values() for t in x["tareas_abiertas"]}
    comprueba(f"{nombre}: lo de quien no da señales no está en riesgo por lentitud",
              not any("estimacion" in mo["en_riesgo"].get(t, []) for t in abiertas))
    riesgo = mo["en_riesgo"]
    comprueba(f"{nombre}: cada plazo vencido está en riesgo por eso, y cada «espera a» es una dependencia vencida o en riesgo",
              all("plazo_vencido" in riesgo.get(t, []) for t in vencidos)
              and all(m.split()[1] in deps[t] and m.split()[1] in riesgo for t, ms in riesgo.items() for m in ms
                      if m.startswith("espera_a")))
    if pocos:
        comprueba(f"{nombre}: sin estimación, nada en riesgo por estimación",
                  not any("estimacion" in ms for ms in riesgo.values()))
        return
    pendientes = [t for t, _, _, _ in fs if est[t] not in HECHAS and t not in nc and pl[t]["valor"]]
    lento_ok, rapido_tarde, por_tarea = True, True, {t: [True, True] for t in pendientes}
    for restar in (True, False):
        for con_nc in (True, False):
            fr = franjas(fs, pl, inicio, pausas, restar, con_nc, nc)
            r = {p: [(obs[x["tarea"]] - primera[x["tarea"]]) / fr[x["tarea"]] for x in base[p] if fr[x["tarea"]]]
                 for p in base}
            lento = estimar(fs, est, fr, {p: max(v) for p, v in r.items()}, pausas, primera, deps, ahora, restar, False, nc)
            rapido = estimar(fs, est, fr, {p: min(v) for p, v in r.items()}, pausas, primera, deps, ahora, restar, True, nc)
            lento_ok &= all(lento[t] <= entrega - MARGEN for t in pendientes)
            rapido_tarde &= any(rapido[t] > entrega for t in pendientes)
            for t in pendientes:
                por_tarea[t][0] &= rapido[t] > entrega          # tarde hasta con el ritmo más rápido
                por_tarea[t][1] &= lento[t] <= entrega          # a tiempo hasta con el más lento
    esperado = mo["veredicto"]
    comprueba(f"{nombre}: veredicto «{esperado}» en las cuatro variantes de la cota",
              (esperado == "a_tiempo" and lento_ok) or (esperado == "no_llega" and rapido_tarde))
    comprueba(f"{nombre}: lo que está en riesgo por estimación acaba tarde con cualquier ritmo medido "
              f"({sorted(t for t, m in riesgo.items() if 'estimacion' in m) or '—'})",
              all(por_tarea[t][0] for t, ms in riesgo.items() if "estimacion" in ms))
    fuera = [t for t in pendientes if t not in riesgo]
    comprueba(f"{nombre}: lo que no está en riesgo llega con el ritmo más lento medido ({len(fuera)} tareas)",
              all(por_tarea[t][1] for t in fuera), str([t for t in fuera if not por_tarea[t][1]]))


def pon(ruta, valor):
    """Un cambio en los hechos: `ruta` es una lista de claves e índices; el último recibe `valor` (None: se borra)."""
    def cambia(h):
        for k in ruta[:-1]:
            h = h[k]
        if valor is None:
            del h[ruta[-1]]
        else:
            h[ruta[-1]] = valor
    return cambia


CONTROLES = [
    ("G13 M2: N2 sin «trabajo nuevo desde»", g13, ["momentos", 1, "notas", "N2", "trabajo_nuevo_desde"], ""),
    ("G13 M3: N6 «cubierta» con T23 solo reclamada", g13, ["momentos", 2, "notas", "N6", "estado"], "cubierta"),
    ("G13 M2: N5 sin corregir", g13, ["momentos", 1, "notas", "N5", "corregida_por"], ""),
    ("G13 M1: N4 sin la ⚑ de T20", g13, ["momentos", 0, "notas", "N4", "cerradas_a_mano"], []),
    ("G14 inicio: T20 con plazo", g14, ["momentos", 0, "sin_plazo", "T20"], None),
    ("G14 inicio: cifra con pocos datos", g14, ["momentos", 0, "cifra", "hay"], True),
    ("G14 mitad bien: «no llega»", g14, ["momentos", 1, "veredicto"], "no_llega"),
    ("G14 mitad con riesgo: «a tiempo»", g14, ["momentos", 2, "veredicto"], "a_tiempo"),
    ("G14 mitad con riesgo: T25 (sin señales) en riesgo por estimación", g14, ["momentos", 2, "en_riesgo", "T25"],
     ["estimacion"]),
    ("G14 mitad con riesgo: T26 en riesgo por estimación", g14, ["momentos", 2, "en_riesgo", "T26"], ["estimacion"]),
    ("G14 mitad con riesgo: persona-c con señales", g14, ["momentos", 2, "sin_senales", "persona-c"], None),
    ("G14 mitad con riesgo: la discrepancia de la entrega bloquea", g14,
     ["momentos", 2, "entrega", "bloquea_estimacion"], True),
]


def main():
    global fallos, callado
    g13()
    g14()
    print()
    for nombre, funcion, ruta, valor in CONTROLES:     # con un hecho cambiado, tiene que fallar
        antes, callado = fallos, True
        funcion(pon(ruta, valor))
        detecta, fallos, callado = fallos > antes, antes, False
        comprueba(f"control ({nombre}): lo detecta", detecta)
    print(f"\n{fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
