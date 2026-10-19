# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Vistas de ejemplo para los tests de la web (ADR-0009, criterio 3 de M9a).

Con el mismo montaje que evals/coordinacion/simulador/igualdad.py (relay de verdad, sondeo fijo con las tareas del
reto 03), calcula el estado de cada punto de control de G1–G6, el estado sintético de 5 personas y 20 tareas y G12
(servicios), comprueba que cada estado valida contra estado.schema.json y deja, por caso, lo que serviría el demonio en
GET /v1/vista (api.md §4): {servido_en, persona, relay, vista}. La web solo pinta eso.

Para que los tests de la web no se comparen consigo mismos, cada caso lleva también `esperado`, lo que calcula
proyeccion.py para cada persona de la vista: {persona: {trabajo: [ids en el orden de TRABAJO], servicios: [claves de
servicios_de]}}; y `antiguedades`, la antigüedad en segundos que da proyeccion.py (la de `viejo` y del MCP) de cada
`observado_en` de la vista respecto de `servido_en`: {observado_en: segundos}. Y tablas.json, las tablas ETIQUETAS y
TRABAJO de proyeccion.py que la web repite.

M10 (K-106; R-35, R-36, ADR-0012, ADR-0013; api.md §11): en test/vistas/m10/, los bloques `jurado` y `ruta` de la vista
que pinta la web, cada uno validado contra $defs/vista_jurado y $defs/vista_ruta:
- ejemplo.json: la vista de ejemplo de api.md §11.6, tal cual (se lee del contrato);
- G13.json y G14.json: los momentos de G13 y de G14, con la vista entera que da proyeccion.vista con el relay de verdad
  y sus interruptores, como en igualdad.py y g13_g14.py (evals/coordinacion/simulador/m10.py: los ficheros de cada
  guion en un repo de git con su historia). G13, solo con vista_jurado; G14, solo con ruta_critica. De la vista, solo los bloques.
Cada caso lleva `antiguedades` (como arriba, más la de `ruta.dato_mas_viejo`) y `horas`: cada hora de cada bloque
escrita en la zona con que la enseña la web, {bloque: {hora: {hm, dia, fecha}}}: la `zona` del bloque (issue #56 para
la ruta, #63 para el jurado: el nombre IANA de equipo.md o el desfase) y, sin ella, como ruta.py en el resumen (el
desfase de la entrega; sin ella, el de las notas; si no, UTC).

Uso (desde hkos/web-src): uv run --no-project scripts/vistas_ejemplo.py   → test/vistas/*.json y test/vistas/m10/*.json
"""
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(AQUI)
KIT = os.path.dirname(os.path.dirname(WEB))
SIM = os.path.join(KIT, "evals", "coordinacion", "simulador")
sys.path[:0] = [os.path.join(KIT, "hkos"), SIM]
import lecturas  # noqa: E402
import m10  # noqa: E402
import proyeccion  # noqa: E402
import relay as relay_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from fixture import estado_5x20  # noqa: E402
import g12  # noqa: E402
from igualdad import SondeoFijo  # noqa: E402
from simula import carga, contratos_de, montar  # noqa: E402

SALIDA = os.path.join(WEB, "test", "vistas")
SALIDA_M10 = os.path.join(SALIDA, "m10")
ESQUEMA = Esquema("estado.schema.json")
API = os.path.join(KIT, "docs", "hackathon-os", "contratos", "api.md")
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")          # los de ruta.DIAS
HORA_ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d(:\d\d(\.\d+)?)?(Z|[+-]\d\d:\d\d)$")


def observados(x):
    """Todos los `observado_en` de la vista, a cualquier profundidad."""
    if isinstance(x, dict):
        if isinstance(x.get("observado_en"), str):
            yield x["observado_en"]
        for y in x.values():
            yield from observados(y)
    elif isinstance(x, list):
        for y in x:
            yield from observados(y)


def respuesta(estado, persona):
    err = ESQUEMA.error(estado)
    if err is not None:
        raise SystemExit(f"estado que no valida contra estado.schema.json: {err}")
    ahora = estado["generado_en"]
    v = proyeccion.vista(estado, ahora)
    return {"servido_en": ahora, "persona": persona, "relay": {"conectado": True, "desde": ahora}, "vista": v,
            "esperado": {p["persona"]: {"trabajo": [t["id"] for t in proyeccion.trabajo(v, p["persona"])],
                                        "servicios": [x["clave"] for x in proyeccion.servicios_de(v, p["persona"])]}
                         for p in v["personas"]},
            "antiguedades": {o: proyeccion._edad(o, ahora) for o in sorted(set(observados(v)))}}


def escribe(fichero, datos, carpeta=SALIDA):
    with open(os.path.join(carpeta, fichero), "w", encoding="utf-8", newline="\n") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")


def guarda(nombre, casos, carpeta=SALIDA):
    escribe(f"{nombre}.json", {"nombre": nombre, "casos": casos}, carpeta)
    print(f"{nombre}: {len(casos)} casos")


# --- M10: jurado y ruta (K-106) ---

def horas_de(x):
    """Todas las horas ISO 8601 de un bloque, a cualquier profundidad (no las citas «AAAA-MM-DD HH:MM» de las notas)."""
    if isinstance(x, dict):
        for y in x.values():
            yield from horas_de(y)
    elif isinstance(x, list):
        for y in x:
            yield from horas_de(y)
    elif isinstance(x, str) and HORA_ISO.match(x):
        yield x


def zona_m10(vista):
    """La zona en que la web enseña las horas de los bloques: la de ruta._zona (el desfase de la entrega de equipo.md,
    con el que se escribe el resumen); sin entrega, el de la primera nota con hora; si no, UTC."""
    obj = (vista.get("ruta") or {}).get("objetivo") or {}
    notas = [x["nota"]["hora"] for x in (vista.get("jurado") or {}).get("notas", []) if x["nota"].get("hora")]
    for h in [obj.get("valor")] + notas:
        if h:
            return datetime.fromisoformat(h.replace("Z", "+00:00")).tzinfo
    return timezone.utc


def zona_de(vista, bloque):
    """La zona de las horas de un bloque (issue #56 la ruta, #63 el jurado): su `zona.valor`, un desfase ±HH:MM o un
    nombre IANA (con lecturas.zona, la que usa el relay); sin ella o si no se resuelve, zona_m10."""
    valor = ((vista.get(bloque) or {}).get("zona") or {}).get("valor")
    m = re.fullmatch(r"([+-])(\d\d):(\d\d)", valor or "")
    if m:
        return timezone((1 if m.group(1) == "+" else -1) * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    return (valor and lecturas.zona(valor)) or zona_m10(vista)


def escritas(bloque, tz):
    """{hora: {hm, dia, fecha}} de cada hora ISO del bloque, en la zona tz."""
    salida = {}
    for h in sorted(set(horas_de(bloque))):
        d = datetime.fromisoformat(h.replace("Z", "+00:00")).astimezone(tz)
        salida[h] = {"hm": d.strftime("%H:%M"), "dia": f"{DIAS[d.weekday()]} {d.strftime('%H:%M')}",
                     "fecha": f"{DIAS[d.weekday()]} {d.day} · {d.strftime('%H:%M')}"}
    return salida


def caso_m10(vista, ahora, persona, **extra):
    """Lo que serviría el demonio con los bloques de M10 en la vista, validados contra el esquema, con las antigüedades
    y las horas de Python para comprobar la web sin pasar por su formato."""
    for clave, defs in (("jurado", "vista_jurado"), ("ruta", "vista_ruta")):
        if clave in vista:
            err = ESQUEMA._error({"$ref": f"#/$defs/{defs}"}, vista[clave], clave)
            if err is not None:
                raise SystemExit(f"bloque `{clave}` que no valida contra $defs/{defs}: {err}")
    zonas = {k: zona_de(vista, k) for k in ("jurado", "ruta")}
    horas = {k: escritas(vista[k], zonas[k]) for k in ("jurado", "ruta") if k in vista}
    edades = set(observados(vista)) | {x for x in [(vista.get("ruta") or {}).get("dato_mas_viejo")] if x}
    return dict({"servido_en": ahora, "persona": persona, "relay": {"conectado": True, "desde": ahora}, "vista": vista,
                 "antiguedades": {o: proyeccion._edad(o, ahora) for o in sorted(edades)},
                 "horas": horas}, **extra)


def ejemplo_api():
    """La vista de ejemplo de api.md §11.6, tal cual."""
    with open(API, encoding="utf-8") as f:
        md = f.read()
    seccion = md[md.index("### 11.6 Vista de ejemplo"):]
    m = re.search(r"```json\r?\n(.*?)\r?\n```", seccion, re.S)
    v = json.loads(m.group(1))
    return caso_m10(v, v["jurado"]["observado_en"], "ana")


def momentos_m10(tmp):
    """G13 y G14 con el relay de verdad (m10.py) y proyeccion.vista, como vivo_g13 y vivo_g14 de g13_g14.py: cada
    momento de sus hechos, G13 solo con vista_jurado y G14 solo con ruta_critica (con las tareas del plan en main)."""
    g13 = carga(os.path.join(SIM, "guiones", "G13.json"))
    h13 = carga(os.path.join(SIM, g13["hechos"]))
    casos13 = []
    for mo in h13["momentos"]:
        r = m10.relay(tmp, g13, m10.versiones_g13(g13, h13, mo["ahora"]), mo["ahora"], ruta=False)
        casos13.append(caso_m10(bloques(m10.vista(r)), mo["ahora"], r.personas[0]["persona"], momento=mo["nombre"]))
    h14 = carga(os.path.join(SIM, "guiones", "g14", "hechos.json"))
    casos14 = []
    for mo in h14["momentos"]:
        g14 = carga(os.path.join(SIM, "guiones", mo["guion"]))
        versiones = m10.versiones_g14(h14, mo["ahora"])
        plan = [f["plan.md"] for _, f in versiones if "plan.md" in f][-1]
        r = m10.relay(tmp, g14, versiones, mo["ahora"], jurado=False, tareas=m10.tareas_del_plan(g14, plan))
        casos14.append(caso_m10(bloques(m10.vista(r)), mo["ahora"], r.personas[0]["persona"], momento=mo["nombre"]))
    return casos13, casos14


def bloques(v):
    """De la vista, solo los bloques de M10 (lo que pintan Jurado y Ruta crítica)."""
    return {k: v[k] for k in ("jurado", "ruta") if k in v}


def main():
    os.makedirs(SALIDA, exist_ok=True)
    escribe("tablas.json", {"ETIQUETAS": proyeccion.ETIQUETAS, "TRABAJO": list(proyeccion.TRABAJO)})
    tmp = tempfile.mkdtemp(prefix="hk-vistas-")
    try:
        for g in ("G1", "G2", "G3", "G4", "G5", "G6"):
            guion = carga(os.path.join(SIM, "guiones", f"{g}.json"))
            tareas, personas, issues, eventos, ts = montar(guion, SIM)
            contratos = contratos_de(guion, SIM)
            casos = []
            for punto in guion["esperado"]:
                ahora = ts(punto["tras"])
                visto = datetime.fromisoformat(ahora.replace("Z", "+00:00")).timestamp()
                r = relay_mod.Relay(os.path.join(tmp, f"relay-{g}-{punto['tras']}"), personas, ahora=lambda a=ahora: a,
                                    sondeo=SondeoFijo(tareas, issues, visto),
                                    umbral_parada_s=guion.get("umbral_parada_s", 1200), contratos=contratos)
                vistos = [e for e in eventos if e["ts"] <= ahora]
                for i in range(0, len(vistos), 200):
                    r.recibir({"eventos": vistos[i:i + 200]})
                r.recalcular()
                casos.append(dict(respuesta(r.estado, personas[0]["persona"]), tras=punto["tras"]))
            guarda(g, casos)
        e = estado_5x20()
        guarda("5x20", [respuesta(e, p["persona"]) for p in e["personas"][:2]])
        repo_g12, eventos = g12.montar(tmp)
        nov = relay_mod.Novedades(repo_g12, 300, web_nueva=True)
        nov.sondear()
        visto = datetime.fromisoformat(g12.AHORA.replace("Z", "+00:00")).timestamp()
        r = relay_mod.Relay(os.path.join(tmp, "relay-g12"), g12.PERSONAS, ahora=lambda: g12.AHORA,
                            sondeo=SondeoFijo(g12.TAREAS, g12.ISSUES, visto), novedades=nov, web_nueva=True)
        r.recibir({"eventos": eventos})
        r.recalcular()
        if not r.estado.get("servicios"):
            raise SystemExit("G12 sin servicios en el estado")
        guarda("G12", [respuesta(r.estado, p["persona"]) for p in g12.PERSONAS])
        os.makedirs(SALIDA_M10, exist_ok=True)
        guarda("ejemplo", [ejemplo_api()], SALIDA_M10)
        g13, g14 = momentos_m10(tmp)
        guarda("G13", g13, SALIDA_M10)
        guarda("G14", g14, SALIDA_M10)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
