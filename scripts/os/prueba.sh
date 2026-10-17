#!/usr/bin/env bash
# Hook del Hackathon OS (M9a, K-96; api.md §1; ADR-0011): si el comando de un Bash es exactamente la Prueba de una
# conexión de .hackathon/servicios.md, una línea `prueba` con su huella (nunca el comando) y si pasó o falló.
# PostToolUse → pasa; PostToolUseFailure → falla, con el código de «Exit code N» (Paso 0 de M9a). El OS nunca ejecuta
# la Prueba: solo mira lo que la sesión ya ha corrido. Sin OS activo, sin `web_nueva: sí` o sin servicios.md, sale sin
# leer la entrada. Solo builtins, salvo el sha256 cuando hay coincidencia.

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
