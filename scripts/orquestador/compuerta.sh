#!/usr/bin/env bash
# Compuerta de evidencias (M7b): rechaza el informe final de un worker sin evidencias. Desde la v0.3.1,
# el informe puede ir en un fichero de <git común>/hackathon/informes/ (línea «Informe: <ruta>»).
# PreToolUse sobre SubagentHandback (el informe va en tool_input.message) y, de respaldo,
# SubagentStop (last_assistant_message) para el worker que termina sin SubagentHandback.
# Solo actúa con el agente worker del kit; en cualquier otro caso sale al instante.
# Tope: 2 rechazos por agent_id; al tercero deja pasar y el orquestador no fusiona sin evidencias.
# M8c (K-33): con el Hackathon OS activo, cada decisión deja su línea «compuerta» (api.md §1); no cambia la decisión.

source "$(dirname "$0")/comun.sh"
source "$(dirname "$0")/../os/comun.sh"
es_agente worker || exit 0

evento=$(valor hook_event_name) || exit 0
id=$(valor agent_id) || id=sin-id
comun=$(git rev-parse --git-common-dir 2>/dev/null) || exit 0
dir="$comun/hackathon/compuerta"; mkdir -p "$dir" || exit 0

case $evento in
  PreToolUse)
    [[ $entrada =~ \"tool_name\"[[:space:]]*:[[:space:]]*\"SubagentHandback\" ]] || exit 0
    informe=$(valor message) || exit 0 ;;
  SubagentStop)
    [ -e "$dir/$id.entregado" ] && exit 0      # ya entregó por SubagentHandback
    [[ $entrada =~ \"stop_hook_active\"[[:space:]]*:[[:space:]]*true ]] && exit 0   # ya se le pidió seguir una vez
    # Claude Code también lanza agentes internos (sin transcript) que heredan el agent_type: solo
    # cuenta un subagente con transcript cuyo .meta.json diga que es el worker (prueba de M7b).
    t=$(valor agent_transcript_path) || exit 0
    t=${t//\\//}; meta="${t%.jsonl}.meta.json"
    [ -f "$t" ] && grep -E '"agentType"[[:space:]]*:[[:space:]]*"(hackathon-kit:)?worker"' "$meta" >/dev/null 2>&1 || exit 0
    informe=$(valor last_assistant_message) || exit 0 ;;
  *) exit 0 ;;
esac
informe=${informe//$'\r'/}

# v0.3.1: el worker puede dejar el informe completo en un fichero y entregar una sola línea con
# «Informe: <ruta>». Solo vale una ruta dentro de <git común>/hackathon/informes/.
motivos=()
if [[ $informe =~ Informe:[[:space:]]*([^$'\n']+) ]]; then
  ruta=$(printf '%s' "${BASH_REMATCH[1]}" | tr -d '`' | sed 's/[[:space:]]*$//'); ruta=${ruta//\\//}
  # macOS no trae `realpath -m`: con la carpeta del fichero, si existe, y `pwd -P` (también resuelve /var → /private/var).
  abs_bash() { local d=${1%/*} b=${1##*/}; [[ $1 == /* ]] || d=$PWD/$d
    if [ -d "$d" ]; then printf '%s/%s' "$(cd "$d" && pwd -P)" "$b"; else printf '%s' "$1"; fi; }
  abs() { if command -v cygpath >/dev/null; then cygpath -m -a "$1" 2>/dev/null; else realpath -m "$1" 2>/dev/null || abs_bash "$1"; fi; }
  carpeta=$(abs "$comun/hackathon/informes")
  if [[ $ruta == *..* ]]; then
    motivos+=("la ruta del informe «$ruta» lleva «..»")
  elif ! [[ $(abs "$ruta") == "$carpeta"/* ]]; then
    motivos+=("el informe tiene que estar en $carpeta/, no en «$ruta»")
  elif [ ! -f "$ruta" ]; then
    motivos+=("el informe «$ruta» no existe")
  else
    informe=$(tr -d '\r' < "$ruta")
  fi
fi

campo() { printf '%s\n' "$informe" | sed -nE "s/^[[:space:]*-]*$1:[[:space:]]*//p" | head -1; }

[ ${#motivos[@]} -eq 0 ] && for c in Rama Base Worktree Estado 'Ficheros tocados' 'Preparación' 'Comprobación'; do
  printf '%s\n' "$informe" | grep -E "^[[:space:]*-]*$c:" >/dev/null || motivos+=("falta la línea «$c:»")
done

estado=$(campo Estado)
if [[ ${#motivos[@]} -eq 0 && $estado == hecho* ]]; then
  # Salida de la comprobación: alguna línea no vacía entre «Comprobación:» y «Pendiente o dudas:».
  salida=$(printf '%s\n' "$informe" | sed -nE '/^[[:space:]*-]*Comprobación:/,/^[[:space:]*-]*Pendiente/{/Comprobación:|Pendiente/d;p;}' | grep -v '^[[:space:]`]*$')
  [ -n "$salida" ] || motivos+=("no hay salida de la comprobación debajo de «Comprobación:» (copia las últimas líneas que imprimió)")

  rama=$(campo Rama); rama=${rama%% *}
  base=$(campo Base); base=${base%% *}
  wt=$(campo Worktree); wt=${wt//\\//}; wt=${wt%% (*}
  if ! git -C "$wt" rev-parse --git-dir >/dev/null 2>&1; then
    motivos+=("el worktree «$wt» no existe o no es un repositorio")
  elif ! git -C "$wt" rev-parse -q --verify "$base^{commit}" >/dev/null; then
    motivos+=("la base «$base» no es un commit")
  elif ! git -C "$wt" rev-parse -q --verify "$rama^{commit}" >/dev/null; then
    motivos+=("la rama «$rama» no existe")
  else
    [ "$(git -C "$wt" rev-list --count "$base..$rama")" -gt 0 ] || motivos+=("la rama «$rama» no tiene commits por encima de la base: haz commit")
    ficheros=$(campo 'Ficheros tocados')
    while IFS= read -r f; do
      [ -n "$f" ] && [[ $ficheros != *"$f"* ]] && motivos+=("«$f» está en el diff y no en «Ficheros tocados:»")
    done < <(git -C "$wt" diff --name-only "$base..$rama")
    [ -z "$(git -C "$wt" status --porcelain)" ] || motivos+=("el worktree tiene cambios sin commitear (git status --porcelain no está vacío)")
  fi
fi

if [ ${#motivos[@]} -eq 0 ]; then
  [ "$evento" = PreToolUse ] && : > "$dir/$id.entregado"
  os_compuerta ok ""
  exit 0
fi

n=$(( $(cat "$dir/$id.rechazos" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$dir/$id.rechazos"
if [ "$n" -gt 2 ]; then
  [ "$evento" = PreToolUse ] && : > "$dir/$id.entregado"
  os_compuerta ko tope "${motivos[@]}"
  exit 0      # tope: deja pasar; el orquestador no fusiona un informe sin evidencias
fi
os_compuerta ko "" "${motivos[@]}"

{
  echo "Compuerta (intento $n de 2): el informe no trae evidencias suficientes."
  printf -- '- %s\n' "${motivos[@]}"
  echo "Corrígelo (o completa el trabajo) y vuelve a entregarlo: el informe completo con el formato de «Informe» en tu fichero de hackathon/informes/ y, como respuesta, la línea «Estado · Rama · Informe: <ruta>». No inventes salidas: copia las que viste."
} >&2
exit 2
