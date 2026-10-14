#!/usr/bin/env bash
# Emisor de prueba (no es el del OS): una línea JSON por evento, sin parsear la entrada.
d="${HK_EVENTOS:-$HOME/hk-p6}"; mkdir -p "$d"; e=$(tr -d '\r\n')
s=${e#*\"session_id\":\"}; s=${s%%\"*}
printf '{"v":1,"ts":"%s","persona":"","tipo":"%s","entrada":%s}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$e" >> "$d/${s:-sin-sesion}.jsonl"
