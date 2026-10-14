#!/usr/bin/env bash
# Hook del Hackathon OS (M8c, K-31): una línea por evento en <git común>/hackathon/os/eventos/<session_id>.jsonl,
# solo con la lista blanca de api.md §1 y copiando los valores tal como vienen escapados. Solo builtins de bash.
# Sin .hackathon/os.md activo en la copia principal, sale sin leer la entrada ni escribir nada.
# Eventos: SessionStart, SessionEnd, SubagentStart, SubagentStop y Pre/PostToolUse de las herramientas de ADR-0004.

LC_ALL=C.UTF-8   # ${v:0:200} cuenta caracteres: el recorte no parte una «ó»
d=${0//\\//}
source "${d%/*}/comun.sh"
os_activo || exit 0
os_leer
os_entrada || exit 0
os_crudo hook_event_name "$OS_CABEZA" || exit 0
evento=$OS_V
os_sobre "$evento"
linea=$OS_SOBRE

case $evento in
  SessionStart)
    os_crudo source "$OS_CABEZA" && linea+=',"source":"'$OS_V'"' ;;
  SubagentStart)
    os_crudo transcript_path "$OS_CABEZA" && linea+=',"transcript_path":"'$OS_V'"' ;;
  SubagentStop)
    if [[ $OS_CABEZA =~ \"agent_type\"[[:space:]]*:[[:space:]]*\"([^\"]*:)?revisor\" ]] && os_crudo last_assistant_message; then
      msg=$OS_V
      [[ $msg =~ Veredicto:[*[:space:]]*(APROBADO|CAMBIOS) ]] && linea+=',"veredicto":"'${BASH_REMATCH[1]}'"'
      [[ $msg =~ Fusi(ó|\\u00f3)n:[*[:space:]]*\`?([0-9a-f]{7,40}) ]] && linea+=',"fusion":"'${BASH_REMATCH[2]}'"'
    fi ;;
  PreToolUse|PostToolUse)
    os_crudo tool_name "$OS_CABEZA" || exit 0
    herramienta=$OS_V
    linea+=',"tool_name":"'$herramienta'"'
    # tool_use_id puede ir detrás de tool_response (y de un tool_input grande): al final o en la cabeza.
    [[ $OS_COLA =~ \"tool_use_id\"[[:space:]]*:[[:space:]]*\"([A-Za-z0-9_-]+)\" || $OS_CABEZA =~ \"tool_use_id\"[[:space:]]*:[[:space:]]*\"([A-Za-z0-9_-]+)\" ]] && linea+=',"tool_use_id":"'${BASH_REMATCH[1]}'"'
    case $herramienta in
      Edit|Write|MultiEdit|NotebookEdit)
        { os_crudo file_path "$OS_CABEZA" || os_crudo notebook_path "$OS_CABEZA"; } && linea+=',"ruta":"'$OS_V'"' ;;
      Bash|PowerShell)
        # Solo los comandos con git update-ref, merge --ff-only, push o commit (también con git -C <ruta>).
        # En la entrada cruda, un salto de línea es «\n» y unas comillas, «\"».
        re='(^|[^[:alnum:]_-]|\\n|\\t)git([[:space:]]+-C[[:space:]]+(\\"[^\\]*\\"|[^[:space:]]+))?[[:space:]]+(update-ref|merge[[:space:]]+--ff-only|push|commit)([^[:alnum:]_-]|$)'
        if os_crudo_ini command "$OS_CABEZA" && [[ $OS_V =~ $re ]]; then
          v=${OS_V:0:200}
          # Sin escapes a medias al final: un «\u» con menos de 4 dígitos o una «\» suelta (impar).
          if [[ $v =~ (\\+)u[0-9a-fA-F]{0,3}$ ]] && (( ${#BASH_REMATCH[1]} % 2 == 1 )); then
            v=${v:0:${#v}-${#BASH_REMATCH[0]}+${#BASH_REMATCH[1]}-1}
          fi
          if [[ $v =~ (\\+)$ ]] && (( ${#BASH_REMATCH[1]} % 2 == 1 )); then v=${v%?}; fi
          linea+=',"git":"'$v'"'
        fi ;;
      Agent)
        os_crudo subagent_type "$OS_CABEZA" && linea+=',"subagent_type":"'$OS_V'"'
        if [[ $evento == PreToolUse ]] && os_crudo_ini prompt "$OS_CABEZA"; then
          p=$OS_V
          [[ $p =~ (^|\\n)[*[:space:]]*ID:[*[:space:]]*(T[0-9]{2,3})([^0-9]|$) ]] && linea+=',"id":"'${BASH_REMATCH[2]}'"'
          [[ $p =~ (^|\\n)[*[:space:]]*Base:[*[:space:]]*\`?([0-9a-f]{7,40})([^0-9a-f]|$) ]] && linea+=',"base":"'${BASH_REMATCH[2]}'"'
        fi ;;
    esac ;;
  SessionEnd) ;;
  *) exit 0 ;;
esac

os_escribe "$linea}" || os_escribe "$OS_MINIMO"
exit 0
