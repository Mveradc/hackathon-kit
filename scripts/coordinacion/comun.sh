# shellcheck shell=bash
# Común a los scripts de coordinación entre agentes (M6a). Se carga con `source`.
# Solo bash y gh (el filtrado, con `gh --jq`): jq no viene con Git Bash.
# Se ejecuta en el directorio del proyecto (el de la sesión de Claude Code).

HK_GH=${HK_GH:-gh}                 # en las pruebas, evals/coordinacion/gh-falso.sh
HK_CONF=.hackathon/coordinacion.md
HK_CONFIRMO='hk confirmo'          # sin «/»: Git Bash convierte «/hk …» en una ruta de Windows

# Cabecera de un mensaje: bloque «<!-- hk … -->» al principio del cuerpo.
HK_JQ='def hdr: ((.body // "") | capture("^<!-- hk\r?\n(?s:(?<h>.*?))\r?\n-->").h) // "";
def cab($k): (hdr | capture("(?m)^" + $k + ": *(?<v>[^ \r\n]*)").v) // "";
def para: ([.labels[]?.name | select(startswith("hk:para-")) | ltrimstr("hk:para-")] | first) // "";
def fila: map(tostring) | join("\u001f");'
# Separador de filas: no es espacio en blanco, así que «read» no junta los campos vacíos (con tabulador, sí).
HK_SEP=$'\x1f'

# Imprime un fichero en UTF-8 aunque esté en UTF-16 o con BOM (PowerShell 5.1), sin \r.
hk_leer() {
  [ -f "$1" ] || return 1
  case $(head -c2 "$1" | od -An -tx1 | tr -d ' \n') in
    fffe) iconv -f UTF-16LE -t UTF-8 "$1" ;;
    feff) iconv -f UTF-16BE -t UTF-8 "$1" ;;
    *) cat "$1" ;;
  esac | sed '1s/^\xEF\xBB\xBF//' | tr -d '\r'
}

hk_minus() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
hk_handle() { hk_minus "${1#@}"; }

# Valor de una línea «clave: valor» de coordinacion.md.
hk_conf() { hk_leer "$HK_CONF" | sed -n "s/^$1:[[:space:]]*//p" | head -1 | sed 's/[[:space:]]*$//'; }

# Filas «Persona<TAB>handle» de la tabla de coordinacion.md.
hk_personas() {
  hk_leer "$HK_CONF" | grep '^|' | awk -F'|' '{
    p=$2; h=$3; gsub(/^[ \t]+|[ \t]+$/, "", p); gsub(/^[ \t@]+|[ \t]+$/, "", h)
    if (p == "" || p == "Persona" || p ~ /^-+$/ || h ~ /^-+$/ || h == "—") next   # «—»: no usa la coordinación
    print p "\t" tolower(h) }'
}

hk_estado_dir() {
  local g; g=$(git rev-parse --git-dir 2>/dev/null) || return 1
  HK_ESTADO="$g/hackathon"; mkdir -p "$HK_ESTADO"
}

# Lo que dice el fichero, sin llamar a gh: existe, «activa: sí», sin marcadores y con repo.
hk_conf_activa() {
  [ -f "$HK_CONF" ] || return 1
  case $(hk_minus "$(hk_conf activa)") in sí|si|yes) ;; *) return 1 ;; esac
  HK_REPO=$(hk_conf repo)
  case $HK_REPO in ''|*'<'*) return 1 ;; esac
  hk_personas | grep -q '<' && return 1
  [ -n "$(hk_personas)" ] || return 1
  hk_estado_dir
}

# Quién soy: el usuario de la sesión de gh (GH_TOKEN o keyring), en caché por token.
hk_yo() {
  local clave cache
  clave=$(printf '%s' "${GH_TOKEN:-keyring}" | cksum | cut -d' ' -f1)
  cache="$HK_ESTADO/yo-$clave"
  if [ ! -s "$cache" ]; then
    hk_gh api user --jq .login > "$cache.tmp" 2>/dev/null && mv "$cache.tmp" "$cache" || { rm -f "$cache.tmp"; return 1; }
  fi
  HK_YO=$(hk_minus "$(cat "$cache")")
}

# Activa del todo: fichero correcto y yo en la tabla. Deja HK_REPO, HK_YO y HK_ESTADO.
hk_activa() {
  hk_conf_activa || return 1
  hk_yo || return 1
  hk_personas | cut -f2 | grep -qx "$HK_YO"
}

hk_max_saltos() { local m; m=$(hk_conf max_saltos); case $m in ''|*[!0-9]*) echo 4 ;; *) echo "$m" ;; esac; }
hk_sondeo() { local s; s=$(hk_conf sondeo_segundos); case $s in ''|*[!0-9]*) echo 60 ;; *) echo "$s" ;; esac; }

# gh con backoff ante límites (403/429), errores 5xx y de red. Devuelve 75 mientras toca esperar.
hk_gh() {
  local ahora hasta espera err salida rc
  ahora=$(date +%s)
  hasta=$(cat "$HK_ESTADO/backoff_hasta" 2>/dev/null || echo 0)
  [ "$ahora" -lt "$hasta" ] && return 75
  err=$(mktemp)
  salida=$("$HK_GH" "$@" 2>"$err"); rc=$?
  if [ $rc -ne 0 ] && grep -qiE 'HTTP (403|429|5[0-9][0-9])|rate limit|timed? ?out|could not resolve|connection' "$err"; then
    espera=$(cat "$HK_ESTADO/backoff_s" 2>/dev/null || echo 15)
    espera=$((espera * 2)); [ "$espera" -gt 600 ] && espera=600
    echo "$espera" > "$HK_ESTADO/backoff_s"
    echo $((ahora + espera)) > "$HK_ESTADO/backoff_hasta"
    rm -f "$err"; return 75
  fi
  [ $rc -eq 0 ] && rm -f "$HK_ESTADO/backoff_s" "$HK_ESTADO/backoff_hasta"
  [ $rc -ne 0 ] && cat "$err" >&2; rm -f "$err"
  [ -n "$salida" ] && printf '%s\n' "$salida"
  return $rc
}

hk_espera() { echo $(( $(cat "$HK_ESTADO/backoff_hasta" 2>/dev/null || date +%s) - $(date +%s) )); }

# Cabecera: hk_cabecera <id> <de> <para> <tipo> <nivel> <dueño> <salto> <max_saltos>
hk_cabecera() {
  printf '<!-- hk\nid: %s\nde: %s\npara: %s\ntipo: %s\nnivel: %s\ndueno: %s\nsalto: %s\nmax_saltos: %s\n-->\n' "$@"
}

# Los agentes nunca publican la confirmación de una persona (una línea que sea solo la marca).
# Además, todo lo que publica buzon.sh lleva cabecera, y una confirmación válida no la lleva.
hk_sin_confirmo() {
  if hk_leer "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -qixF "$HK_CONFIRMO"; then
    echo "Rechazado: «$HK_CONFIRMO» solo lo escribe el dueño, desde su usuario de GitHub." >&2
    return 2
  fi
}
