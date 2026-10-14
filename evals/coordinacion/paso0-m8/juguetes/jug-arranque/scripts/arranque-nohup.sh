#!/usr/bin/env bash
# SessionStart: si nadie escucha en el puerto, lanza el demonio en segundo plano y vuelve al instante.
cat >/dev/null
P=47199; d="$HOME/hk-arranque"; mkdir -p "$d"
if (exec 3<>/dev/tcp/127.0.0.1/$P) 2>/dev/null; then echo "$(date +%T) hook: demonio ya vivo" >> "$d/log"; exit 0; fi
nohup uv run --no-project "$CLAUDE_PLUGIN_ROOT/scripts/demonio.py" $P "${HK_INACTIVO:-40}" "$d/log" >/dev/null 2>&1 &
echo "$(date +%T) hook: demonio lanzado" >> "$d/log"
