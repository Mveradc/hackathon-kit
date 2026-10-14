#!/usr/bin/env bash
# P13 de M8.0. Lanza un «demonio» (bash que escribe un latido cada 5 s) si no está vivo y se queda dormido sin imprimir.
# Registro en ~/hk-p13/: lanzador.log (arranques y salida del monitor), latido.log (lo escribe el demonio), demonio.pid.
d="$HOME/hk-p13"; mkdir -p "$d"
echo "$(date +%T) monitor arranca (pid $$, cwd $PWD)" >> "$d/lanzador.log"
trap 'echo "$(date +%T) monitor recibe señal de salida" >> "$d/lanzador.log"' EXIT
vivo() { [ -f "$d/demonio.pid" ] && kill -0 "$(cat "$d/demonio.pid")" 2>/dev/null; }
if vivo; then
  echo "$(date +%T) demonio ya vivo (pid $(cat "$d/demonio.pid")): no lanzo otro" >> "$d/lanzador.log"
else
  nohup bash -c 'while :; do echo "$(date +%T) latido pid $$" >> "'"$d"'/latido.log"; sleep 5; done' >/dev/null 2>&1 &
  echo $! > "$d/demonio.pid"
  echo "$(date +%T) demonio lanzado (pid $!)" >> "$d/lanzador.log"
fi
while :; do sleep 60; done   # como escucha.sh: un monitor que sale abre un turno
