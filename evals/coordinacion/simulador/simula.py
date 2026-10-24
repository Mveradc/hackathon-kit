# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Simulador de equipo (M8b): reproduce un guion de eventos normalizados y cambios en GitHub, calcula estado.json con
hkos/modelo.py y lo compara con lo esperado del guion (docs/hackathon-os/simulador.md).

En M8b trabaja con eventos ya normalizados; las entradas crudas de hooks, los repos y gh-falso.sh llegan en M8c y M8e.
Uso: uv run --no-project evals/coordinacion/simulador/simula.py <guion.json> [--salida estado.json]
Sale con 1 si algún punto de control no coincide.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path.insert(0, os.path.join(KIT, "hkos"))
import contratos as contratos_mod  # noqa: E402
from estados import iso  # noqa: E402
from modelo import calcular  # noqa: E402

INICIO = "2026-09-18T17:00:00Z"     # vie 18 sep, 19:00 en Madrid: empieza el reto 03
CAMPOS_EVENTO = ("tarea", "rutas", "datos")


def carga(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def montar(guion, base):
    """Del guion abreviado a (tareas, personas, issues, eventos completos)."""
    t0 = datetime.fromisoformat(guion.get("inicio", INICIO).replace("Z", "+00:00"))
    ts = lambda s: iso(t0 + timedelta(seconds=s))
    plan = carga(os.path.join(base, guion["tareas"]))
    tareas, personas = plan["tareas"], guion.get("personas", plan["personas"])
    # «Compilar el plan» (M8e): un issue por tarea, creado en t=0.
    issues = {t["id"]: {"creado_en": ts(0), "numero": 100 + i, "acciones": []} for i, t in enumerate(tareas)}
    eventos, contador = [], {}
    for p in guion["pasos"]:
        if "github" in p:
            a = {"accion": p["github"], "por": p["por"], "ts": ts(p["t"])}
            if p.get("a"):
                a["a"] = p["a"]
            issues[p["tarea"]]["acciones"].append(a)
            continue
        actor = {"persona": p["persona"], "papel": p["papel"]}
        for k in ("sesion", "agente", "worktree"):
            if k in p:
                actor[k] = p[k]
        clave = p.get("sesion") or p["persona"]
        contador[clave] = contador.get(clave, 0) + 1
        e = {"v": 1, "id": p.get("id", f"{clave}-{contador[clave]}"), "ts": ts(p["t"]), "actor": actor,
             "tipo": p["tipo"], "fuente": p["fuente"]}
        for k in CAMPOS_EVENTO:
            if k in p:
                e[k] = p[k]
        eventos.append(e)
    return tareas, personas, issues, eventos, ts


def contratos_de(guion, base):
    """M8g: los bloques con dueño de un guion con `contratos` ({contratos, autoridad}: ficheros junto al guion)."""
    c = guion.get("contratos")
    if not c:
        return None
    leer = lambda n: open(os.path.join(base, n), encoding="utf-8").read()
    return contratos_mod.duenos(leer(c["contratos"]), leer(c["autoridad"]))[0]


def conflictos_de(guion, ts, tras):
    """M11 (G15): los `conflictos` del nivel 2 que tendría el Calculo del relay a `tras`, o None si el guion no trae.
    El guion da lo que sale en cada ciclo, `{t, pares: [{personas, rutas, rutas_2b?}]}`; como el Calculo, `desde`
    (y `desde_2b`) es el primer ciclo desde el que ese par tiene seguidas las mismas `rutas` (`rutas_2b`). Un par sin
    `rutas` lleva en `desde` la hora de `desde_2b` (modelo.calcular filtra por `desde`)."""
    if "conflictos" not in guion:
        return None
    ciclos = [c for c in guion["conflictos"] if c["t"] <= tras]
    desde, salida = {}, []
    for i, ciclo in enumerate(ciclos):
        vivos = {}
        for par in ciclo["pares"]:
            k = tuple(sorted(par["personas"]))
            for campo in ("rutas", "rutas_2b"):
                if campo not in par:
                    continue
                rutas = sorted(par[campo])
                previo = desde.get((k, campo))
                vivos[(k, campo)] = previo if rutas and previo and previo[0] == rutas else (rutas, ts(ciclo["t"]))
        desde = {k: x for k, x in vivos.items() if x[0]}
        if i == len(ciclos) - 1:
            for par in ciclo["pares"]:
                k = tuple(sorted(par["personas"]))
                c = {"personas": list(k), "rutas": sorted(par["rutas"])}
                if "rutas_2b" in par:
                    c["rutas_2b"] = sorted(par["rutas_2b"])
                    c["desde_2b"] = desde.get((k, "rutas_2b"), (None, ts(ciclo["t"])))[1]
                c["desde"] = desde[(k, "rutas")][1] if (k, "rutas") in desde else c.get("desde_2b", ts(ciclo["t"]))
                if c["rutas"] or c.get("rutas_2b"):
                    salida.append(c)
    return salida


def comparar(estado, esperado):
    """Lista de diferencias entre estado.json y los campos que el guion fija en un punto de control."""
    dif = []
    tareas = {t["id"]: t for t in estado["tareas"]}
    for tid, valor in esperado.get("tareas", {}).items():
        real = tareas[tid]["estado"]["valor"]
        if real != valor:
            dif.append(f"{tid}: {real}, se esperaba {valor}")
    for tid, valor in esperado.get("declarado", {}).items():
        d = tareas[tid]["declarado"]
        real = d["valor"] if d else None
        if real != valor:
            dif.append(f"{tid} declarado: {real}, se esperaba {valor}")
    for tid, lista in esperado.get("cumplidas_por_cierre", {}).items():
        real = tareas[tid].get("cumplidas_por_cierre", [])
        if real != lista:
            dif.append(f"{tid} cumplidas_por_cierre: {real}, se esperaba {lista}")
    for tid, sha in esperado.get("fusion", {}).items():
        if tareas[tid].get("fusion") != sha:
            dif.append(f"{tid} fusión: {tareas[tid].get('fusion')}, se esperaba {sha}")
    activos = {p["persona"]: sum(a["activo"] for a in p["actores"]) for p in estado["personas"]}
    for persona, n in esperado.get("activos", {}).items():
        if activos.get(persona) != n:
            dif.append(f"{persona}: {activos.get(persona)} actores activos, se esperaban {n}")
    if "sin_tarea" in esperado and len(estado.get("sin_tarea", [])) != esperado["sin_tarea"]:
        dif.append(f"sin_tarea: {len(estado.get('sin_tarea', []))}, se esperaban {esperado['sin_tarea']}")
    if "colisiones" in esperado:                # M8g: sin observado_en, que depende del paso del tiempo
        real = sorted(({k: c[k] for k in ("id", "nivel", "gravedad", "personas", "rutas", "contrato") if k in c}
                       for c in estado.get("colisiones", [])), key=lambda c: c["id"])
        if real != sorted(esperado["colisiones"], key=lambda c: c["id"]):
            dif.append(f"colisiones: {real}, se esperaban {esperado['colisiones']}")
    for cid, cuando in esperado.get("observado_en", {}).items():     # M11 (G15): desde y desde_2b
        real = next((c["observado_en"] for c in estado.get("colisiones", []) if c["id"] == cid), None)
        if real != cuando:
            dif.append(f"{cid} observado_en: {real}, se esperaba {cuando}")
    if "reservas" in esperado:
        real = sorted([r["persona"], r["rutas"]] for r in estado.get("reservas", []))
        if real != sorted(esperado["reservas"]):
            dif.append(f"reservas: {real}, se esperaban {esperado['reservas']}")
    if "discrepancias" in esperado:
        real = {}
        for d in estado.get("discrepancias", []):
            real[d["tipo"]] = real.get(d["tipo"], 0) + d["veces"]
        if real != esperado["discrepancias"]:
            dif.append(f"discrepancias: {real}, se esperaban {esperado['discrepancias']}")
    return dif


def ejecutar(ruta, valida_evento=None, valida_estado=None):
    """Corre un guion. Devuelve (diferencias por punto de control, último estado.json)."""
    guion = carga(ruta)
    tareas, personas, issues, eventos, ts = montar(guion, AQUI)
    contratos = contratos_de(guion, AQUI)
    resultado, estado = [], None
    for e in eventos:
        if valida_evento:
            valida_evento(e)
    for punto in guion["esperado"]:
        estado = calcular(tareas, issues, eventos, personas, ts(punto["tras"]), guion.get("umbral_parada_s", 1200),
                          contratos=contratos, conflictos=conflictos_de(guion, ts, punto["tras"]))
        if valida_estado:
            valida_estado(estado)
        resultado.append((punto["tras"], comparar(estado, punto)))
    return resultado, estado


def main():
    args = sys.argv[1:]
    salida = None
    if "--salida" in args:
        i = args.index("--salida")
        salida = args[i + 1]
        del args[i:i + 2]
    resultado, estado = ejecutar(args[0])
    fallos = 0
    for tras, dif in resultado:
        print(f"t={tras:>6} s  " + ("OK" if not dif else "FALLA: " + "; ".join(dif)))
        fallos += bool(dif)
    if salida:
        with open(salida, "w", encoding="utf-8", newline="\n") as f:
            json.dump(estado, f, ensure_ascii=False, indent=1)
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
