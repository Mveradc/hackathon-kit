#!/usr/bin/env bash
# Guarda la entrada del hook tal cual: <dir>/<n>-<evento>.json
d="${HK_CAPTURAS:-$HOME/hk-capturas}"; mkdir -p "$d"; ev="$1"
n=$(date +%s%N)
cat > "$d/$n-$ev.json"
exit 0
