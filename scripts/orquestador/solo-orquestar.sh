#!/usr/bin/env bash
# PreToolUse (M7): el orquestador y el revisor no editan código. Solo actúa si la sesión o el subagente
# es uno de los dos (`agent_type`); en cualquier otro caso sale al instante sin hacer nada.
# Es una red bajo el prompt, no una barrera infranqueable.

source "$(dirname "$0")/comun.sh"
es_agente 'orquestador|revisor' || exit 0

negar() {
  if [ "$agente" = revisor ]; then
    echo "Revisor: $1 Tú no editas nada: revisa y ejecuta la comprobación en tu worktree de revisión." >&2
  else
    echo "Orquestador: $1 Tú no editas código: encárgaselo a un worker. Solo puedes escribir en .hackathon/." >&2
  fi
  exit 2
}

[[ $entrada =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"([^\"]*)\" ]] || exit 0
herramienta=${BASH_REMATCH[1]}

case $herramienta in
  Edit|Write|NotebookEdit|MultiEdit)
    [ "$agente" = revisor ] && negar "$herramienta no está entre tus herramientas."
    ruta=$(valor file_path || valor notebook_path)
    ruta=${ruta//\\//}
    case $ruta in
      *..*) negar "ruta con «..»: $ruta." ;;
      .hackathon/*|*/.hackathon/*) exit 0 ;;
      *) negar "$herramienta sobre $ruta." ;;
    esac ;;
  PowerShell)
    negar "PowerShell no está entre tus herramientas; usa Bash." ;;
  Bash)
    cmd=$(valor command) || exit 0
    # Redirecciones que no escriben ficheros: a /dev/null y entre descriptores.
    limpio=$(printf '%s' "$cmd" | sed -E 's/[0-9&]?>>?[[:space:]]*\/dev\/null//g; s/[0-9]?>&[0-9-]//g')
    [[ $limpio == *'>'* ]] && negar "redirección a fichero en «$cmd» (si es un «>» dentro de un texto, reescríbelo sin él)."
    p='(^|[;&|(`[:space:]])'
    for patron in \
      "${p}tee([[:space:]]|$)" "${p}rm([[:space:]]|$)" "${p}mv([[:space:]]|$)" "${p}cp([[:space:]]|$)" \
      "${p}sed([[:space:]][^|;&]*)?[[:space:]](-[a-zA-Z]*i|--in-place)" "${p}(truncate|dd|install|patch)([[:space:]]|$)" \
      "git([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+|[[:space:]]+-[^[:space:]]+)*[[:space:]]+(add|commit|stash|apply|restore|am|cherry-pick|rebase|clean)([[:space:]]|$)" \
      "git[[:space:]].*checkout([[:space:]].*)?[[:space:]]--([[:space:]]|$)" \
      "git[[:space:]].*reset[[:space:]].*--hard" "git[[:space:]].*branch[[:space:]].*-D" \
      "git[[:space:]].*worktree[[:space:]]+remove[[:space:]].*(-f|--force)"; do
      [[ $cmd =~ $patron ]] && negar "comando no permitido en «$cmd»."
    done
    # Push: solo el orquestador y nunca forzado ni borrando ramas (M7b; las condiciones, en su prompt).
    es_push='git([[:space:]]+-[^[:space:]]+)*[[:space:]]+push([[:space:]]|$)'
    forzado='push.*([[:space:]](-f|--force|--force-with-lease|--force-if-includes|--delete|-d|--mirror|--all|--prune|--tags)([[:space:]=]|$)|[[:space:]:][+][^[:space:]]|[[:space:]]:[^[:space:]])'
    if [[ $cmd =~ $es_push ]]; then
      [ "$agente" = revisor ] && negar "comando no permitido en «$cmd»."
      [[ $cmd =~ $forzado ]] && negar "push forzado o que borra ramas en «$cmd»."
    fi
    # El revisor no fusiona ni cambia ramas: solo crea y borra su worktree de revisión.
    if [ "$agente" = revisor ]; then
      for patron in "git[[:space:]].*(merge|pull|branch[[:space:]]+-d|checkout|switch|reset)([[:space:]]|$)"; do
        [[ $cmd =~ $patron ]] && negar "comando no permitido en «$cmd»."
      done
    fi
    exit 0 ;;
esac
exit 0
