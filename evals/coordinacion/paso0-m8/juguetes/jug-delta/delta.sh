#!/usr/bin/env bash
# P16: inyecta ~1.000 caracteres distintos en cada turno, con un código único (CLAVE-<n>) para ver si el modelo lo recuerda después.
cat >/dev/null
f="${HK_P16:-$HOME/hk-p16}/contador"; mkdir -p "$(dirname "$f")"
n=$(( $(cat "$f" 2>/dev/null || echo 0) + 1 )); echo $n > "$f"
relleno=$(printf 'Estado del equipo, linea de relleno %02d para medir tokens. ' $(seq 1 16))
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Delta %d del OS. CLAVE-%d-%s. %s"}}\n' "$n" "$n" "$RANDOM" "$relleno"
