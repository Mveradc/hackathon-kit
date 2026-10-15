#!/usr/bin/env bash
# M8h: lo que se puede comprobar del Hackathon OS en macOS sin Claude Code (lo lanza .github/workflows/macos-m8h.yml en
# un runner macos-latest). Con el bash de Homebrew: bin/hk-os, el alias de git del .mcp.json, el lanzador sin setsid
# (nohup + --desacoplar: el demonio sobrevive al hook, responde /salud, deja agente.vivo y se apaga solo). Con el
# /bin/bash 3.2 de serie: los hooks del OS no fallan ni escriben, y arranque.sh avisa una vez.
# Uso: bash evals/coordinacion/macos.sh <bash 5> (0 OK · 1 falla)
set -u
B5=${1:-bash}
KIT=$(cd "$(dirname "$0")/../.." && pwd)
fallos=0
ok() { echo "OK    $1"; }
mal() { echo "FALLO $1"; fallos=$((fallos + 1)); }
comprueba() { if eval "$2"; then ok "$1"; else mal "$1"; fi; }

echo "bash 5: $("$B5" --version | head -1)"
echo "bash de serie: $(/bin/bash --version | head -1)"
command -v setsid >/dev/null && echo "ojo: hay setsid" || echo "sin setsid (lo normal en macOS)"

# --- bin/hk-os ---
comprueba "bin/hk-os --help" '"$KIT/bin/hk-os" --help | grep -q "hk-os unir"'

# --- el alias del .mcp.json, con el bash 5 primero en el PATH (como en una sesión con Homebrew) ---
d=$(mktemp -d); cd "$d"; git init -q -b main r; cd r
git config user.email m@example.com; git config user.name m
msgs='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"p","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
mcp() { printf '%s\n' "$msgs" | CLAUDE_PLUGIN_ROOT=$KIT PATH="$(dirname "$B5"):$PATH" git -c "alias.hk-os-mcp=!bash \"\${CLAUDE_PLUGIN_ROOT}/scripts/os/mcp.sh\"" hk-os-mcp; }
comprueba "MCP con el OS apagado: initialize y ninguna herramienta" 'mcp | grep -q "\"tools\":\[\]"'
mkdir -p .hackathon
printf 'activa: sí\npuerto_agente: 47321\napagado_min: 1\n' > .hackathon/os.md
comprueba "MCP con el OS activo: uv run hkos/mcp.py con sus herramientas" 'mcp | grep -q "\"name\": \"estado\""'

# --- el lanzador sin setsid ---
printf 'x\n' > a.txt; git add -A; git commit -qm inicio
"$B5" "$KIT/scripts/os/arranque.sh" s-mac persona-a; echo "arranque.sh: $(tail -1 .git/hackathon/os/arranque.log)"
comprueba "arranque.sh lanza con nohup + --desacoplar" 'grep -q "lanzado_desacoplar" .git/hackathon/os/arranque.log'
for _ in $(seq 1 30); do [ -f .git/hackathon/os/agente.vivo ] && break; sleep 1; done
comprueba "el demonio sigue vivo al acabar el hook y deja agente.vivo" '[ -f .git/hackathon/os/agente.vivo ]'
comprueba "responde /salud con su git común" 'curl -s http://127.0.0.1:47321/salud | head -1 | grep -q "^hk-os "'
"$B5" "$KIT/scripts/os/arranque.sh" s-mac2 persona-a
comprueba "un segundo SessionStart lo encuentra y no lanza otro" 'tail -1 .git/hackathon/os/arranque.log | grep -q " vivo "'
echo "esperando a que se apague solo (apagado_min: 1)…"
for _ in $(seq 1 150); do [ -f .git/hackathon/os/agente.vivo ] || break; sleep 1; done
comprueba "se apaga solo y borra agente.vivo" '[ ! -f .git/hackathon/os/agente.vivo ] && ! curl -s -m 2 http://127.0.0.1:47321/salud >/dev/null'

# --- el bash 3.2 de serie: el OS se queda apagado, sin errores ---
entrada='{"hook_event_name":"SessionStart","session_id":"s32","source":"startup","cwd":"'"$PWD"'"}'
rm -rf .git/hackathon/os/eventos
for s in emite.sh arbol.sh delta.sh reserva.sh; do
  salida=$(printf '%s' "$entrada" | /bin/bash "$KIT/scripts/os/$s" 2>&1); rc=$?
  comprueba "bash 3.2: $s sale con 0 y sin salida" '[ $rc -eq 0 ] && [ -z "$salida" ]'
done
comprueba "bash 3.2: no escribe eventos" '[ ! -d .git/hackathon/os/eventos ]'
aviso=$(/bin/bash "$KIT/scripts/os/arranque.sh" s32 persona-a)
comprueba "bash 3.2: arranque.sh avisa de bash 5 y no lanza nada" '[[ $aviso == *"bash 5"* ]] && ! grep -q s32 .git/hackathon/os/arranque.log'
otra=$(/bin/bash "$KIT/scripts/os/arranque.sh" s32 persona-a)
comprueba "bash 3.2: el aviso sale una vez por sesión" '[ -z "$otra" ]'
cd /; rm -rf "$d"
echo "$fallos fallos"
[ $fallos -eq 0 ]
