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
servicios_de]}}. Y tablas.json, las tablas ETIQUETAS y TRABAJO de proyeccion.py que la web repite.

Uso (desde hkos/web-src): uv run --no-project scripts/vistas_ejemplo.py   → test/vistas/*.json
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(AQUI)
KIT = os.path.dirname(os.path.dirname(WEB))
SIM = os.path.join(KIT, "evals", "coordinacion", "simulador")
sys.path[:0] = [os.path.join(KIT, "hkos"), SIM]
import proyeccion  # noqa: E402
import relay as relay_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from fixture import estado_5x20  # noqa: E402
import g12  # noqa: E402
from igualdad import SondeoFijo  # noqa: E402
from simula import carga, contratos_de, montar  # noqa: E402

SALIDA = os.path.join(WEB, "test", "vistas")
ESQUEMA = Esquema("estado.schema.json")


def respuesta(estado, persona):
    err = ESQUEMA.error(estado)
    if err is not None:
        raise SystemExit(f"estado que no valida contra estado.schema.json: {err}")
    ahora = estado["generado_en"]
    v = proyeccion.vista(estado, ahora)
    return {"servido_en": ahora, "persona": persona, "relay": {"conectado": True, "desde": ahora}, "vista": v,
            "esperado": {p["persona"]: {"trabajo": [t["id"] for t in proyeccion.trabajo(v, p["persona"])],
                                        "servicios": [x["clave"] for x in proyeccion.servicios_de(v, p["persona"])]}
                         for p in v["personas"]}}


def escribe(fichero, datos):
    with open(os.path.join(SALIDA, fichero), "w", encoding="utf-8", newline="\n") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")


def guarda(nombre, casos):
    escribe(f"{nombre}.json", {"nombre": nombre, "casos": casos})
    print(f"{nombre}: {len(casos)} casos")


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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
