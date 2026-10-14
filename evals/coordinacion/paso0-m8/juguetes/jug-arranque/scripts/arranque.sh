#!/usr/bin/env bash
# SessionStart: si nadie escucha en el puerto, lanza el demonio con Start-Process (con nohup muere al acabar el hook: ver arranque-nohup.sh) y vuelve.
cat >/dev/null
P=47199; d="$HOME/hk-arranque"; mkdir -p "$d"
if (exec 3<>/dev/tcp/127.0.0.1/$P) 2>/dev/null; then echo "$(date +%T) hook: demonio ya vivo" >> "$d/log"; exit 0; fi
powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath uv -ArgumentList @('run','--no-project','$(cygpath -w "$CLAUDE_PLUGIN_ROOT/scripts/demonio.py")','$P','${HK_INACTIVO:-40}','$(cygpath -w "$d/log")')"
echo "$(date +%T) hook: demonio lanzado" >> "$d/log"
