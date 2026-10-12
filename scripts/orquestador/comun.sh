# shellcheck shell=bash
# Común a los hooks del orquestador (M7). Se carga con `source` y lee la entrada del hook en $entrada.
# Solo bash: jq no viene con Git Bash.

entrada=$(cat)

# Valor de una clave de texto de la entrada, sin desescapar más que \" \\ \n \t y \uXXXX.
valor() {
  local re='"'$1'"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
  [[ $entrada =~ $re ]] || return 1
  local v=${BASH_REMATCH[1]} u='\\u([0-9a-fA-F]{4})' c
  v=${v//\\\\/$'\x1d'}; v=${v//\\\"/\"}; v=${v//\\n/$'\n'}; v=${v//\\t/$'\t'}; v=${v//\\r/}
  while [[ $v =~ $u ]]; do
    LC_ALL=C.UTF-8 printf -v c "\\u${BASH_REMATCH[1]}"
    v=${v//"${BASH_REMATCH[0]}"/$c}
  done
  v=${v//$'\x1d'/\\}
  printf '%s' "$v"
}

# ¿Es la sesión o el subagente uno de estos agentes del kit? `es_agente orquestador|revisor`
es_agente() {
  local re='"agent_type"[[:space:]]*:[[:space:]]*"(hackathon-kit:)?('$1')"'
  [[ $entrada =~ $re ]] && agente=${BASH_REMATCH[2]}
}
