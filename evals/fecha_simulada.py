"""Fecha simulada para las evaluaciones: solo la usa el arnés de evals/, nunca el flujo normal del kit.

Los retos de evals/ son de ediciones pasadas, así que la fecha real de generación siempre cae fuera
del evento y /hack-check lo marca, con razón, como bloqueante de trabajo previo. Este script sustituye
la fecha de la línea «Repositorio generado el …» de «Fechas» en el CLAUDE.md por una fecha dentro del
evento, y deja constancia en .m4/fecha-simulada.txt (fuera del alcance de los comandos del kit), que
el montaje del revisor copia para que el revisor use esa fecha como «hoy».

Uso:
    python evals/fecha_simulada.py <carpeta> "2026-06-12 19:30 (UTC-5)"
"""

import re
import sys
from pathlib import Path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    carpeta, fecha = Path(sys.argv[1]), sys.argv[2]
    cm = carpeta / "CLAUDE.md"
    t = cm.read_text(encoding="utf-8")
    nuevo, n = re.subn(r"(Repositorio generado el )(.+?)(, con el evento ya empezado)", rf"\g<1>{fecha}\g<3>", t)
    if n != 1:
        sys.exit(f"{cm}: se esperaba una línea «Repositorio generado el …, con el evento ya empezado» y hay {n}")
    cm.write_text(nuevo, encoding="utf-8")
    (carpeta / ".m4").mkdir(exist_ok=True)
    (carpeta / ".m4/fecha-simulada.txt").write_text(fecha + "\n", encoding="utf-8")
    print(f"{cm}: fecha de generación simulada → {fecha}")


if __name__ == "__main__":
    main()
