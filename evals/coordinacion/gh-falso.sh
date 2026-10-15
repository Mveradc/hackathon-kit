#!/usr/bin/env bash
# Solo para el arnés (M6a, criterio 7): simula que GitHub limita las peticiones.
# Uso: HK_GH=evals/coordinacion/gh-falso.sh y, mientras exista el fichero $HK_FALSO (por defecto
# .hackathon-gh-falso en el directorio actual) con «403» o «429», cada llamada falla con ese código.
# Sin el fichero, pasa la llamada al gh real.
f=${HK_FALSO:-.hackathon-gh-falso}
if [ -s "$f" ]; then
  echo "$(date '+%T') gh-falso: HTTP $(cat "$f")" >> "${HK_FALSO_LOG:-/dev/null}"
  echo "gh: API rate limit exceeded (HTTP $(cat "$f"))" >&2
  exit 1
fi
exec gh "$@"
