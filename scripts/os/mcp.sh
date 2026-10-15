#!/usr/bin/env bash
# Servidor MCP del Hackathon OS (M8f, K-63, api.md §5), declarado en .mcp.json del plugin. El .mcp.json es estático:
# el servidor arranca en toda sesión con el kit, también con el OS apagado. Por eso este envoltorio:
#   - con .hackathon/os.md activo y uv en el PATH, se convierte en hkos/mcp.py (estado, tarea, colisiones);
#   - si no, responde él mismo en bash, sin uv ni red: `initialize`, `tools/list` vacío y `ping`. El modelo no ve
#     ninguna herramienta; en /mcp el servidor sale conectado y sin herramientas (docs/limitaciones.md).
# .mcp.json lo lanza con un alias de git (`git -c alias.hk-os-mcp='!bash …' hk-os-mcp`) y no con `bash` a secas: en
# Windows, el `bash` del PATH de una sesión abierta desde PowerShell es el de WSL, que no entiende C:/… (M8f). Git
# ejecuta el alias con su propio sh, que encuentra el bash de Git; en macOS y Linux es el bash del sistema.
d=${0//\\//}
source "${d%/*}/comun.sh"
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null
if os_activo && command -v uv >/dev/null 2>&1; then
  kit=${d%/scripts/os/*} repo=$OS_PRINCIPAL
  script=$kit/hkos/mcp.py
  # /c/x → C:/x para el Python de Windows, sin lanzar cygpath.
  [[ $script =~ ^/([A-Za-z])/(.*)$ ]] && script=${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}
  [[ $repo =~ ^/([A-Za-z])/(.*)$ ]] && repo=${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}
  exec uv run --no-project --quiet "$script" --repo "$repo"
fi

while IFS= read -r l || [[ -n $l ]]; do
  [[ $l =~ \"method\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || continue
  metodo=${BASH_REMATCH[1]}
  # Sin "id" es una notificación (notifications/initialized…): no lleva respuesta.
  [[ $l =~ \"id\"[[:space:]]*:[[:space:]]*(-?[0-9]+|\"([^\"\\]|\\.)*\") ]] || continue
  id=${BASH_REMATCH[1]}
  case $metodo in
    initialize)
      v=2025-06-18
      [[ $l =~ \"protocolVersion\"[[:space:]]*:[[:space:]]*\"([0-9-]+)\" ]] && v=${BASH_REMATCH[1]}
      printf '{"jsonrpc":"2.0","id":%s,"result":{"protocolVersion":"%s","capabilities":{"tools":{}},"serverInfo":{"name":"hk-os","version":"1"}}}\n' "$id" "$v" ;;
    tools/list)
      printf '{"jsonrpc":"2.0","id":%s,"result":{"tools":[]}}\n' "$id" ;;
    ping)
      printf '{"jsonrpc":"2.0","id":%s,"result":{}}\n' "$id" ;;
    *)
      printf '{"jsonrpc":"2.0","id":%s,"error":{"code":-32601,"message":"Hackathon OS apagado"}}\n' "$id" ;;
  esac
done
exit 0
