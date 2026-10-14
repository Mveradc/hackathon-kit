# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterio 3 de M8b: los guiones G1–G4 corren de principio a fin, cada evento valida contra eventos.schema.json y
cada estado.json contra estado.schema.json, y coinciden con lo esperado de cada guion.

jsonschema solo hace falta aquí (el OS no depende de él):
  uv run --no-project --with "jsonschema[format-nongpl]" evals/coordinacion/simulador/prueba_simulador.py
Sale con 1 si algo falla. Sin jsonschema, o con uno sin Draft 2020-12 y su comprobador de formatos (3.2, 4.0), se salta.
"""
import json
import os
import sys
import tempfile

try:
    import jsonschema
except ImportError:
    jsonschema = None

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path.insert(0, AQUI)
from simula import carga, ejecutar  # noqa: E402

CONTRATOS = os.path.join(KIT, "docs", "hackathon-os", "contratos")
GUIONES = ["G1", "G2", "G3", "G4"]


def validador(nombre):
    esquema = carga(os.path.join(CONTRATOS, nombre))
    jsonschema.Draft202012Validator.check_schema(esquema)
    return jsonschema.Draft202012Validator(esquema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER).validate


def main():
    # Draft202012Validator llega en la 4.0; su FORMAT_CHECKER, después.
    if not hasattr(getattr(jsonschema, "Draft202012Validator", None), "FORMAT_CHECKER"):
        print('SALTADA: sin jsonschema con Draft 2020-12; lanzar con uv run --with "jsonschema[format-nongpl]"')
        sys.exit(0)
    ev, es = validador("eventos.schema.json"), validador("estado.schema.json")
    fallos = 0
    for g in GUIONES:
        ruta = os.path.join(AQUI, "guiones", f"{g}.json")
        try:
            resultado, _ = ejecutar(ruta, ev, es)
        except jsonschema.ValidationError as e:
            print(f"{g}: NO VALIDA: {e.message} en {list(e.absolute_path)}")
            fallos += 1
            continue
        malos = [(t, d) for t, d in resultado if d]
        print(f"{g}: {len(resultado) - len(malos)}/{len(resultado)} puntos de control" + ("" if not malos else f" · FALLA {malos}"))
        fallos += bool(malos)

    # Control: con una expectativa cambiada, el simulador tiene que fallar.
    guion = carga(os.path.join(AQUI, "guiones", "G3.json"))
    guion["esperado"][-1]["tareas"]["T16"] = "integrada"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(guion, f)
    try:
        resultado, _ = ejecutar(f.name, ev, es)
    finally:
        os.unlink(f.name)
    detecta = bool(resultado[-1][1])
    print("control (G3 con T16 «integrada» al final): " + ("lo detecta" if detecta else "NO lo detecta"))
    fallos += not detecta

    print("OK" if not fallos else f"{fallos} fallo(s)")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
