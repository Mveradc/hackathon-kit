#!/usr/bin/env bash
# PreToolUse (M7c): ningún agente publica «hk confirmo» con gh, porque es la firma de una persona.
# Sin la coordinación activada en .hackathon/coordinacion.md, sale al instante (sin llamar a gh).
# Es una red, no una garantía: el agente usa el gh de su persona y puede rodearla (docs/limitaciones.md).

dir=$(cd "$(dirname "$0")" && pwd)
source "$dir/../orquestador/comun.sh"     # lee la entrada del hook en $entrada; valor()
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
. "$dir/comun.sh"
hk_conf_activa || exit 0

[[ $entrada =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"(Bash|PowerShell)\" ]] || exit 0
cmd=$(valor command) || exit 0
[[ $cmd =~ (^|[^[:alnum:]_./-])gh(\.exe)?[[:space:]] ]] || exit 0   # solo si llama a gh

# ¿Contiene la marca? Sin distinguir mayúsculas y juntando los espacios.
con_marca() { tr '[:upper:]\r\n\t' '[:lower:]   ' | tr -s ' ' | grep -F "$HK_CONFIRMO" >/dev/null; }

negar() {
  echo "Coordinación: $1 «$HK_CONFIRMO» solo lo escribe el dueño, desde su usuario de GitHub. Pídeselo a tu persona: en la web o con \`! gh issue comment <n> --body \"$HK_CONFIRMO\"\`." >&2
  exit 2
}

printf '%s' "$cmd" | con_marca && negar "el comando de gh lleva la marca (se niega aunque solo lea, para no tener que distinguir lecturas de escrituras)."

# Ficheros que gh publica: --body-file F, -F F (issue comment), --input F, campo=@F o @F (gh api).
donde=$(valor cwd); donde=${donde//\\//}   # las rutas relativas, desde donde corre el comando
set -f; sig=
for t in $(printf '%s' "$cmd" | tr "\"'" '  '); do
  case $t in
    --body-file|-F|--input) sig=1; continue ;;
    --body-file=*|--input=*) f=${t#*=} ;;
    *=@*) f=${t#*=@} ;;
    @*) f=${t#@} ;;
    *) [ -n "$sig" ] && f=$t || { sig=; continue; } ;;
  esac
  sig=
  f=${f//\\//}
  case $f in /*|[A-Za-z]:/*) ;; *) [ -n "$donde" ] && f="$donde/$f" ;; esac
  [ -f "$f" ] && hk_leer "$f" | con_marca && negar "el fichero «$f» que publica gh lleva la marca."
done
exit 0
