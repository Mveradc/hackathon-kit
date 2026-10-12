#!/usr/bin/env bash
# PreToolUse (M7a): el orquestador no edita código. Solo actúa si la sesión es la del agente
# orquestador (`agent_type`); en cualquier otra sesión o subagente sale al instante sin hacer nada.
# Es una red bajo el prompt, no una barrera infranqueable. Solo bash: jq no viene con Git Bash.

entrada=$(cat)
[[ $entrada =~ \"agent_type\"[[:space:]]*:[[:space:]]*\"(hackathon-kit:)?orquestador\" ]] || exit 0

negar() {
  echo "Orquestador: $1 Tú no editas código: encárgaselo a un worker. Solo puedes escribir en .hackathon/." >&2
  exit 2
}

# Valor de una clave de texto de tool_input, sin desescapar más que \" \\ y \n.
valor() {
  local re='"'$1'"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
  [[ $entrada =~ $re ]] || return 1
  local v=${BASH_REMATCH[1]}
  v=${v//\\\\/$'\x1d'}; v=${v//\\\"/\"}; v=${v//\\n/$'\n'}; v=${v//$'\x1d'/\\}
  printf '%s' "$v"
}

[[ $entrada =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"([^\"]*)\" ]] || exit 0
herramienta=${BASH_REMATCH[1]}

case $herramienta in
  Edit|Write|NotebookEdit|MultiEdit)
    ruta=$(valor file_path || valor notebook_path)
    ruta=${ruta//\\//}
    case $ruta in
      *..*) negar "ruta con «..»: $ruta." ;;
      .hackathon/*|*/.hackathon/*) exit 0 ;;
      *) negar "$herramienta sobre $ruta." ;;
    esac ;;
  PowerShell)
    negar "PowerShell no está entre tus herramientas; usa Bash para leer y para git." ;;
  Bash)
    cmd=$(valor command) || exit 0
    # Redirecciones que no escriben ficheros: a /dev/null y entre descriptores.
    limpio=$(printf '%s' "$cmd" | sed -E 's/[0-9&]?>>?[[:space:]]*\/dev\/null//g; s/[0-9]?>&[0-9-]//g')
    [[ $limpio == *'>'* ]] && negar "redirección a fichero en «$cmd» (si es un «>» dentro de un texto, reescríbelo sin él)."
    p='(^|[;&|(`[:space:]])'
    for patron in \
      "${p}tee([[:space:]]|$)" "${p}rm([[:space:]]|$)" "${p}mv([[:space:]]|$)" "${p}cp([[:space:]]|$)" \
      "${p}sed([[:space:]][^|;&]*)?[[:space:]](-[a-zA-Z]*i|--in-place)" "${p}(truncate|dd|install|patch)([[:space:]]|$)" \
      "git([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+|[[:space:]]+-[^[:space:]]+)*[[:space:]]+(add|commit|stash|apply|restore|push|am|cherry-pick|rebase|clean)([[:space:]]|$)" \
      "git[[:space:]].*checkout([[:space:]].*)?[[:space:]]--([[:space:]]|$)" \
      "git[[:space:]].*reset[[:space:]].*--hard" "git[[:space:]].*branch[[:space:]].*-D" \
      "git[[:space:]].*worktree[[:space:]]+remove[[:space:]].*(-f|--force)"; do
      [[ $cmd =~ $patron ]] && negar "comando no permitido en «$cmd»."
    done
    exit 0 ;;
esac
exit 0
