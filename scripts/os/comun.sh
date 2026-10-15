# shellcheck shell=bash
# Común a los hooks del Hackathon OS (M8c). Se carga con `source`. Solo builtins de bash: corre en cada
# herramienta de cada sesión y subagente (ADR-0004, ≤ 50 ms por llamada en Windows), así que nada de procesos
# hijos en el camino habitual. Sin `.hackathon/os.md` activo, `os_activo` falla y el hook sale sin escribir.
# Un clon, una persona (diseno.md §3): interruptor, persona y eventos viven en el git común.

# Del git común y la copia principal, sin lanzar git: sube desde $PWD hasta el primer .git. En un worktree,
# .git es un fichero con «gitdir: <git común>/worktrees/<nombre>», y ese directorio tiene «commondir».
# OS_TOP: la raíz del árbol en que se está (la copia principal o el worktree).
os_raiz() {
  local d=${PWD//\\//} linea gd c
  while :; do
    if [[ -d $d/.git ]]; then
      OS_COMUN=$d/.git OS_GITDIR=$d/.git OS_TOP=$d
      break
    elif [[ -f $d/.git ]]; then
      OS_TOP=$d
      IFS= read -r linea < "$d/.git" || return 1
      gd=${linea#gitdir: }; gd=${gd%$'\r'}; gd=${gd//\\//}
      [[ $gd == /* || $gd == [A-Za-z]:* ]] || gd=$d/$gd
      OS_COMUN=$gd OS_GITDIR=$gd
      if [[ -f $gd/commondir ]]; then
        IFS= read -r c < "$gd/commondir"; c=${c%$'\r'}; c=${c//\\//}
        if [[ $c == /* || $c == [A-Za-z]:* ]]; then
          OS_COMUN=$c
        else
          while [[ $c == ../* || $c == .. ]]; do OS_COMUN=${OS_COMUN%/*}; c=${c#..}; c=${c#/}; done
          [[ -n $c && $c != . ]] && OS_COMUN=$OS_COMUN/$c
        fi
      fi
      break
    fi
    [[ $d == */* ]] || return 1
    d=${d%/*}
    [[ -n $d ]] || return 1
  done
  OS_COMUN=${OS_COMUN%/}
  OS_PRINCIPAL=${OS_COMUN%/.git}
}

# Sha de una ref (refs/remotes/origin/main…) en el git común, suelta o en packed-refs: OS_V. Sin lanzar git.
os_ref() {
  local l
  if [[ -f $OS_COMUN/$1 ]]; then
    IFS= read -r OS_V < "$OS_COMUN/$1"; OS_V=${OS_V%$'\r'}
  else
    [[ -f $OS_COMUN/packed-refs ]] || return 1
    OS_V=
    while IFS= read -r l; do [[ $l == *" $1" ]] && { OS_V=${l%% *}; break; }; done < "$OS_COMUN/packed-refs"
  fi
  [[ $OS_V =~ ^[0-9a-f]{40}$ ]]
}

# Sha de HEAD del árbol en que se está (copia principal o worktree): OS_HEAD. Sin lanzar git.
os_head() {
  local l
  IFS= read -r l < "$OS_GITDIR/HEAD" || return 1
  l=${l%$'\r'}
  if [[ $l == "ref: "* ]]; then os_ref "${l#ref: }" || return 1; OS_HEAD=$OS_V; else OS_HEAD=$l; fi
  [[ $OS_HEAD =~ ^[0-9a-f]{40}$ ]]
}

# ¿Está activo el OS? `activa: sí|si|yes` en .hackathon/os.md de la copia principal (api.md §0).
# Tolera BOM, \r, un comentario detrás y UTF-16 (read descarta los NUL; «sí» queda como «s\xed»).
os_activo() {
  os_raiz || return 1
  local f=$OS_PRINCIPAL/.hackathon/os.md l LC_ALL=C
  [[ -f $f ]] || return 1
  while IFS= read -r l || [[ -n $l ]]; do
    l=${l//$'\r'/}; l=${l#$'\xef\xbb\xbf'}; l=${l#$'\xff\xfe'}; l=${l#$'\xfe\xff'}
    [[ $l =~ ^activa:[[:space:]]*([^#[:space:]]*) ]] || continue
    case ${BASH_REMATCH[1]} in [Ss]í|[Ss]Í|[Ss][Ii]|[Yy][Ee][Ss]|[Ss]$'\xed'|[Ss]$'\xcd') return 0 ;; esac
    return 1
  done < "$f" 2>/dev/null
  return 1
}

# Persona: la caché de hk_yo en el git común (la deja sesion.sh en la copia principal). Si no hay ninguna o
# no coinciden, «»: la resuelve el demonio (api.md §1).
os_persona() {
  local f p uno=
  OS_PERSONA=
  for f in "$OS_COMUN"/hackathon/yo-*; do
    [[ -f $f && $f != *.tmp ]] || continue
    IFS= read -r p < "$f" || [[ -n $p ]] || continue
    p=${p//$'\r'/}; p=${p,,}
    [[ -z $uno || $uno == "$p" ]] || return 0
    uno=$p
  done
  [[ $uno =~ ^[a-z0-9-]+$ ]] && OS_PERSONA=$uno
  return 0
}

# Valor crudo (tal como viene escapado en el JSON) de una clave de texto: OS_V. Busca en $2 o en $entrada.
os_crudo() {
  local re='"'$1'"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'
  [[ ${2-$entrada} =~ $re ]] || return 1
  OS_V=${BASH_REMATCH[1]}
}

# Como os_crudo, pero sin exigir las comillas del final: el principio de un valor que puede seguir más allá de
# OS_CABEZA (el prompt de Agent, el comando de Bash). Solo para buscar dentro, no para copiarlo tal cual.
os_crudo_ini() {
  local re='"'$1'"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)'
  [[ ${2-$entrada} =~ $re ]] || return 1
  OS_V=${BASH_REMATCH[1]}
}

# Texto propio (no de la entrada) a cadena JSON, sin comillas: OS_V.
os_json() {
  local v=$1
  v=${v//\\/\\\\}; v=${v//\"/\\\"}; v=${v//$'\t'/\\t}; v=${v//$'\n'/\\n}; v=${v//$'\r'/}
  while [[ $v =~ [[:cntrl:]] ]]; do v=${v//"${BASH_REMATCH[0]}"/}; done
  OS_V=$v
}

# Bytes de una cadena, contados con LC_ALL=C (para el tope por línea).
os_bytes() { local LC_ALL=C; OS_N=${#1}; }
# Tope por línea: 1.000 bytes con el salto (api.md §1). Medido en Windows con Git Bash: el printf de bash
# escribe en trozos de 1 KB y, por encima, las líneas de hooks simultáneos se mezclan. Es un límite medido, no una garantía.
OS_TOPE=1000

# Sobre común de toda línea cruda: OS_SOBRE = v, ts, persona, tipo, session_id, agent_id, agent_type, cwd.
# OS_MINIMO, sin agent_type ni cwd y con "truncado":true, por si la línea no cabe en el tope.
os_sobre() {
  # ts en UTC con microsegundos, sin procesos: $EPOCHREALTIME (bash 5). El orden de los eventos es (ts, nº de línea).
  local ts e=$EPOCHREALTIME
  TZ=UTC0 printf -v ts '%(%Y-%m-%dT%H:%M:%S)T' "${e%[.,]*}"
  ts+=.${e#*[.,]}Z
  os_persona
  OS_SOBRE='{"v":1,"ts":"'$ts'","persona":"'$OS_PERSONA'","tipo":"'$1'","session_id":"'$OS_SESION'"'
  [[ $OS_CABEZA =~ \"agent_id\"[[:space:]]*:[[:space:]]*\"([A-Za-z0-9_-]{1,100})\" ]] && OS_SOBRE+=',"agent_id":"'${BASH_REMATCH[1]}'"'
  OS_MINIMO=$OS_SOBRE',"truncado":true}'
  local k
  for k in agent_type cwd; do
    os_crudo "$k" "$OS_CABEZA" && OS_SOBRE+=',"'$k'":"'$OS_V'"'
  done
}

# Lee la entrada del hook: `entrada` = sus primeros 16 KB y OS_COLA = sus últimos 400 caracteres. Lee hasta el
# final (Claude Code no se queda escribiendo en una tubería cerrada), pero sin guardarlo todo. Medido en Windows
# con la tubería nativa de Claude Code y 226 KB de entrada: `read -d ''` lee byte a byte (534 ms); `read -N`, en
# bloque (≈0 ms); `$(cat)` cuesta un proceso (26 ms); /dev/stdin no existe.
os_leer() {
  local t previo= ultimo=
  IFS= read -r -N 16384 entrada
  if (( ${#entrada} == 16384 )); then
    while IFS= read -r -N 16384 t; [[ -n $t ]]; do previo=$ultimo ultimo=$t; (( ${#t} == 16384 )) || break; done
    OS_COLA=$previo$ultimo
  else
    OS_COLA=$entrada
  fi
  (( ${#OS_COLA} > 400 )) && OS_COLA=${OS_COLA: -400}
  return 0
}

# Prepara la entrada: OS_SESION validado, OS_CABEZA y OS_COLA. Una entrada puede traer ficheros enteros (content de
# Write, tool_response de Edit o Read): las regex sobre cientos de KB cuestan decenas de ms en Windows. Por eso se
# busca solo en los primeros 16 KB (el sobre y tool_input, que van delante, y sin tool_response) y, para
# tool_use_id, que puede ir detrás de tool_response, en los últimos 400 caracteres.
os_entrada() {
  OS_CABEZA=${entrada:0:16384}
  OS_CABEZA=${OS_CABEZA%%\"tool_response\"*}
  if [[ -z ${OS_COLA+x} ]]; then
    if (( ${#entrada} > 400 )); then OS_COLA=${entrada: -400}; else OS_COLA=$entrada; fi
  fi
  os_crudo session_id "$OS_CABEZA" || return 1
  [[ $OS_V =~ ^[A-Za-z0-9_-]+$ ]] || return 1
  OS_SESION=$OS_V
}

# Añade una línea al JSONL de la sesión en una sola escritura (api.md §1: ≤ 1.000 bytes con el salto, O_APPEND;
# el fichero nunca se reescribe).
os_escribe() {
  local dir=$OS_COMUN/hackathon/os/eventos
  os_bytes "$1"
  (( OS_N + 1 <= OS_TOPE )) || return 1
  [[ -d $dir ]] || mkdir -p "$dir" 2>/dev/null || return 1
  printf '%s\n' "$1" >> "$dir/$OS_SESION.jsonl"
}

# Línea de la compuerta (K-33): os_compuerta ok|ko [tope] [motivo…]. Usa $entrada de orquestador/comun.sh.
os_compuerta() {
  os_activo && os_entrada || return 0
  local resultado=$1 tope=$2 m lista= linea LC_ALL=C.UTF-8   # el recorte cuenta caracteres: no parte una «ó»
  shift 2
  for m in "$@"; do
    os_json "${m:0:300}"
    lista+=${lista:+,}'"'$OS_V'"'
  done
  os_sobre compuerta
  linea=$OS_SOBRE',"resultado":"'$resultado'"'
  [[ $tope == tope ]] && linea+=',"tope":true'
  linea+=',"motivos":['$lista']}'
  os_escribe "$linea" || os_escribe "${OS_MINIMO%\}}"',"resultado":"'$resultado'","motivos":[]}'
  return 0
}
