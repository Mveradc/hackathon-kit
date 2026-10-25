# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Vistas de ejemplo con git o la ruta viejos, para que Vitest compare la web con estado-equipo.md (restos de la 0.6.0,
punto 1; issue #77, A7; constitución IV).

Desde el PR #79, una línea «jurado» o «ruta» vieja del md lleva la hora del último dato bueno (`fuentes.git.observado_en`
en el jurado y `dato_mas_viejo` en la ruta), no la del cálculo, y el md lleva `> Git (remoto del equipo): sin leer desde
HH:MM …` cuando la vista dice desde cuándo no se lee el remoto. Cada caso es lo que serviría el demonio en GET /v1/vista
({servido_en, persona, relay, vista}, con la vista entera de proyeccion.vista) más `md`: por zona (UTC y Europe/Madrid),
las líneas «> Git» y las de «## Jurado y ruta» que escribe proyeccion.markdown. Los casos, los de las pruebas de A7 y
de la parte B del issue #77 (test_proyeccion_m10.Md): git «sin leer jurado y ruta» (los dos bloques viejos), la ruta
vieja por GitHub con git al día, todo al día y servicios «sin leer servicios» sin M10.

Uso (desde hkos/web-src): uv run --no-project scripts/vistas_viejo.py   → test/vistas/viejo/viejo.json. También lo
escribe scripts/vistas_ejemplo.py, al final, para que el CI web lo compruebe con las demás vistas de ejemplo.
"""
import json
import os
import sys
from datetime import timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.dirname(AQUI)
KIT = os.path.dirname(os.path.dirname(WEB))
sys.path[:0] = [os.path.join(KIT, "hkos"), os.path.join(KIT, "hkos", "pruebas"),
                os.path.join(KIT, "evals", "coordinacion", "simulador")]
import lecturas  # noqa: E402
import proyeccion  # noqa: E402
from fixture import estado_5x20  # noqa: E402
from test_proyeccion import con_servicios  # noqa: E402
from test_proyeccion_m10 import con_m10  # noqa: E402

PERSONA = "persona-b"
ZONAS = {"UTC": timezone.utc, "Europe/Madrid": lecturas.zona("Europe/Madrid")}   # sin tzdata (Windows), la de lecturas


def fuentes(e, ahora, git, github=None):
    e["fuentes"]["relay"]["observado_en"] = ahora
    e["fuentes"]["github"] = github or dict(e["fuentes"]["github"], observado_en=ahora)
    e["fuentes"]["git"] = git
    return e


def casos():
    ahora = "2026-09-19T11:00:00Z"
    sin_leer = {"valor": "sin leer jurado y ruta", "fuente": "git", "observado_en": "2026-09-19T07:30:00Z"}
    al_dia = {"valor": "ok", "fuente": "git", "observado_en": ahora}
    yield "git sin leer: jurado y ruta viejos", fuentes(con_m10(estado_5x20()), ahora, sin_leer), ahora
    yield "ruta vieja por GitHub, git al día", fuentes(
        con_m10(estado_5x20(), con_jurado=False), ahora, al_dia,
        {"valor": "limitado", "fuente": "github", "observado_en": "2026-09-19T09:10:00Z"}), ahora
    yield "todo al día", fuentes(con_m10(estado_5x20()), ahora, al_dia), ahora
    ahora = "2026-11-20T10:30:00Z"
    e = con_servicios()
    e["fuentes"]["git"] = {"valor": "sin leer servicios", "fuente": "git", "observado_en": "2026-11-20T09:00:00Z"}
    yield "servicios sin leer, sin M10", e, ahora


def main():
    salida = []
    for nombre, e, ahora in casos():
        v = proyeccion.vista(e, ahora=ahora)
        md = {}
        for zona, tz in ZONAS.items():
            lineas = proyeccion.markdown(v, PERSONA, "x", tz=tz).splitlines()
            jr = lineas[lineas.index("## Jurado y ruta") + 1:lineas.index("## Novedades")] \
                if "## Jurado y ruta" in lineas else []
            md[zona] = {"git": [x for x in lineas if x.startswith("> Git (remoto del equipo)")], "jurado_y_ruta": jr}
        salida.append({"nombre": nombre, "servido_en": ahora, "persona": PERSONA,
                       "relay": {"conectado": True, "desde": ahora}, "vista": v, "md": md})
    d = os.path.join(WEB, "test", "vistas", "viejo")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "viejo.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"casos": salida}, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
