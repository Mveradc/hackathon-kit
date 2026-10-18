#!/usr/bin/env bash
# Hook del Hackathon OS (M9a, K-96; api.md §1; ADR-0011): si el comando de un Bash es exactamente la Prueba de una
# conexión de .hackathon/servicios.md, una línea `prueba` con su huella (nunca el comando) y si pasó o falló.
# PostToolUse → pasa; PostToolUseFailure → falla, con el código de «Exit code N» (Paso 0 de M9a); con is_interrupt o
# en segundo plano (run_in_background o backgroundTaskId), nada. El OS nunca ejecuta la Prueba: solo mira lo que la
# sesión ya ha corrido. Sin OS activo, sin `web_nueva: sí` o sin servicios.md, sale sin leer la entrada. Solo
# builtins, salvo el sha256 cuando hay coincidencia.

LC_ALL=C.UTF-8
d=${0//\\//}
source "${d%/*}/comun.sh"
os_activo || exit 0
os_web_nueva || exit 0
servicios=$OS_PRINCIPAL/.hackathon/servicios.md
[[ -f $servicios ]] || exit 0
os_leer
os_entrada || exit 0
os_crudo hook_event_name "$OS_CABEZA" || exit 0
case $OS_V in
  PostToolUse) resultado=pasa ;;
  PostToolUseFailure) resultado=falla ;;
  *) exit 0 ;;
esac
os_crudo tool_name "$OS_CABEZA" && [[ $OS_V == Bash ]] || exit 0
[[ $OS_CABEZA =~ \"is_interrupt\"[[:space:]]*:[[:space:]]*true ]] && exit 0
os_crudo command "$OS_CABEZA" || exit 0
comando=$OS_V   # tal como viene escapado en la entrada
comando=${comando#"${comando%%[![:space:]]*}"}; comando=${comando%"${comando##*[![:space:]]}"}
[[ -n $comando ]] || exit 0

# Las Pruebas de «## Conexiones» (api.md §10): cuarta celda de cada fila, sin la cabecera ni la línea de guiones.
uno=$'\x01' encontrada=
seccion= cabecera=
while IFS= read -r l || [[ -n $l ]]; do
  l=${l//$'\r'/}; l=${l#$'\xef\xbb\xbf'}
  if [[ $l == '## '* ]]; then
    seccion=${l%"${l##*[![:space:]]}"}; cabecera=; continue
  fi
  [[ $seccion == '## Conexiones' && $l == '|'* ]] || continue
  if [[ -z $cabecera ]]; then cabecera=1; continue; fi
  l=${l//\\|/$uno}
  IFS='|' read -r -a celdas <<< "$l"
  p=${celdas[4]-}
  p=${p#"${p%%[![:space:]]*}"}; p=${p%"${p##*[![:space:]]}"}
  [[ $p == '`'*'`' && ${#p} -ge 2 ]] && { p=${p:1:${#p}-2}; p=${p#"${p%%[![:space:]]*}"}; p=${p%"${p##*[![:space:]]}"}; }
  p=${p//$uno/|}
  [[ -z $p || $p == '—' || $p == '-' || $p =~ ^:?-{3,}:?$ ]] && continue
  e=${p//\\/\\\\}; e=${e//\"/\\\"}
  if [[ $e == "$comando" ]]; then encontrada=$p; break; fi
done < "$servicios" 2>/dev/null
[[ -n $encontrada ]] || exit 0

# En segundo plano, PostToolUse llega al arrancar el proceso, no al terminar: no dice si la Prueba pasó (issue #2, 8).
# Lo dicen tool_input.run_in_background (true, o la cadena "true") o, si el comando ya corría y se pasó a segundo
# plano (Ctrl+B), solo tool_response.backgroundTaskId (issue #15, 5 y 13). OS_CABEZA corta antes de tool_response y
# una regex no sabe de qué objeto es una clave: aquí, ya con una Prueba encontrada, se recorre `entrada` (los primeros
# 16 KB) como JSON, token a token, con las claves y las cadenas sin escapes (\u005f). Si tool_response no cabe en los
# 16 KB, backgroundTaskId se busca también en OS_COLA. Sin procesos. Cada token se busca en una ventana del principio
# (512 caracteres, ×4 si no cabe): la regex de MSYS recorre todo el texto aunque vaya anclada.
# Issue #23 (hallazgo 19): como JSON.parse, con una clave repetida vale la última (también tool_input o tool_response
# enteros), y el comando que cuenta es tool_input.command. Si tool_input no es un objeto (una lista, por ejemplo) o su
# command no es la Prueba encontrada, tampoco se escribe nada: ante la duda, ni «pasa» ni «falla».
descartar() {
  local s=$entrada pila= k1= clave= valor= t v w n fondo= tarea= tipo= orden= entera=
  local rp='^[[:space:]]*([][{}:,])' rs='^[[:space:]]*"([^"\\]*(\\.[^"\\]*)*)"' rl='^[[:space:]]*([A-Za-z0-9.+-]+)'
  while :; do
    n=512 t=
    while :; do
      w=${s:0:n}
      if [[ $w =~ $rp ]]; then t=${BASH_REMATCH[1]}
      elif [[ $w =~ $rs ]]; then t=s v=${BASH_REMATCH[1]}
      elif [[ $w =~ $rl ]] && (( ${#BASH_REMATCH[0]} < ${#w} || ${#w} == ${#s} )); then t=l v=${BASH_REMATCH[1]}
      fi
      [[ -n $t ]] || (( n >= ${#s} )) && break
      n=$((n * 4))
    done
    [[ -n $t ]] || break
    s=${s:${#BASH_REMATCH[0]}}
    case $t in
      '{'|'[')
        if [[ $pila == '{' && -n $valor ]]; then
          k1=$clave
          case $k1 in tool_input) tipo=$t fondo= orden= ;; tool_response) tarea= ;; esac
        fi
        pila+=$t valor= ;;
      '}'|']') pila=${pila%?}; [[ -n $pila ]] || { entera=1; break; }; [[ $pila == '{' ]] && k1= ;;
      :) valor=1 ;;
      ,) valor= ;;
      *)
        # JSON no tiene \c ni \x: %b solo resuelve \u, \\ y los de control (\/ va aparte). Las cadenas de los valores,
        # solo si importan: un stdout de 16 KB no se toca.
        if [[ -z $valor ]]; then [[ $t == s && $pila == *'{' ]] && printf -v clave '%b' "${v//'\/'//}"; continue; fi
        valor=
        if [[ $pila == '{' ]]; then   # un valor suelto en el primer nivel
          case $clave in tool_input) tipo=$t fondo= orden= ;; tool_response) tarea= ;; esac
          continue
        fi
        [[ $pila == '{{' ]] || continue
        case $k1/$clave in
          tool_input/run_in_background) [[ $t == s ]] && printf -v v '%b' "${v//'\/'//}"; fondo=; [[ $v == true ]] && fondo=1 ;;
          tool_input/command)   # crudo y sin espacios a los lados, como $comando
            orden=
            if [[ $t == s ]]; then v=${v#"${v%%[![:space:]]*}"}; v=${v%"${v##*[![:space:]]}"}; [[ $v == "$comando" ]] && orden=1; fi ;;
          tool_response/backgroundTaskId) tarea=; [[ -n $v && ! ( $t == l && ( $v == null || $v == false ) ) ]] && tarea=1 ;;
        esac ;;
    esac
  done
  [[ $tipo == '{' && -n $orden && -z $fondo && -z $tarea ]] || return 0
  [[ -z $entera && $OS_COLA =~ \"backgroundTaskId\"[[:space:]]*:[[:space:]]*\"[^\"] ]]
}
descartar && exit 0

if command -v sha256sum >/dev/null 2>&1; then
  huella=$(printf '%s' "$encontrada" | sha256sum)
else
  huella=$(printf '%s' "$encontrada" | shasum -a 256)   # macOS
fi
huella=${huella:0:12}
[[ $huella =~ ^[0-9a-f]{12}$ ]] || exit 0

os_sobre prueba
linea=$OS_SOBRE',"comando_sha":"'$huella'","resultado":"'$resultado'"'
if [[ $resultado == falla ]] && os_crudo error "$OS_CABEZA" && [[ $OS_V =~ ^Exit\ code\ ([0-9]{1,5}) ]]; then
  linea+=',"codigo":'$((10#${BASH_REMATCH[1]}))
fi
os_escribe "$linea}" || os_escribe "$OS_MINIMO"
exit 0
