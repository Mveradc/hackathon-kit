#!/usr/bin/env bash
# Hook del Hackathon OS (M8c, K-32): en PostToolBatch, Stop y SubagentStop, la línea «arbol» de api.md §1 con lo
# que git ve cambiado en el árbol del actor (también lo que cambió Bash: sed, generadores, instalaciones).
# Solo si el árbol de ese actor (agent_id, o la sesión) ha cambiado desde su último arbol. Las listas se recortan
# para que la línea quepa en el tope de 1.000 bytes ("truncado":true).
# Sin .hackathon/os.md activo en la copia principal, sale sin leer la entrada ni escribir nada.

LC_ALL=C.UTF-8
d=${0//\\//}
source "${d%/*}/comun.sh"
os_activo || exit 0
os_leer
os_entrada || exit 0
os_crudo cwd "$OS_CABEZA" || exit 0
cwd=${OS_V//\\\\/\\}
actor=sesion
os_crudo agent_id "$OS_CABEZA" && [[ $OS_V =~ ^[A-Za-z0-9_-]+$ ]] && actor=$OS_V

# Cada git cuesta unos 40 ms en Windows: origin/main y HEAD se leen de las refs, y el diff solo se pide si HEAD
# se ha separado de origin/main.
cd "$cwd" 2>/dev/null && os_raiz || exit 0
porcelain=$(git -c core.quotepath=false status --porcelain 2>/dev/null) || exit 0
base= diff=
os_ref refs/remotes/origin/main && base=$OS_V
if [[ -n $base ]] && ! { os_head && [[ $OS_HEAD == "$base" ]]; }; then
  diff=$(git diff --name-only "$base...HEAD" 2>/dev/null)
fi

# ¿Ha cambiado desde el último arbol de este actor?
dir=$OS_COMUN/hackathon/os/arbol
firma=$base$'\n'$porcelain$'\n--\n'$diff
previa=
[[ -f $dir/$OS_SESION-$actor ]] && IFS= read -r -d '' previa < "$dir/$OS_SESION-$actor"
[[ $previa == "$firma" ]] && exit 0
[[ -d $dir ]] || mkdir -p "$dir" 2>/dev/null || exit 0
printf '%s' "$firma" > "$dir/$OS_SESION-$actor"

os_sobre arbol
linea=$OS_SOBRE
[[ -n $base ]] && linea+=',"base":"'$base'"'
truncado=
# Añade a la lista mientras quepa (deja sitio para cerrar la línea).
lista() {
  local nombre=$1 texto=$2 l items=
  while IFS= read -r l; do
    [[ -n $l ]] || continue
    os_json "$l"
    os_bytes "$linea,\"$nombre\":[$items,\"$OS_V\"],\"diff\":[],\"truncado\":true}"
    if (( OS_N + 1 > OS_TOPE )); then truncado=1; break; fi
    items+=${items:+,}'"'$OS_V'"'
  done <<< "$texto"
  linea+=',"'$nombre'":['$items']'
}
lista porcelain "$porcelain"
lista diff "$diff"
[[ -n $truncado ]] && linea+=',"truncado":true'
os_escribe "$linea}" || os_escribe "$OS_MINIMO"
exit 0
