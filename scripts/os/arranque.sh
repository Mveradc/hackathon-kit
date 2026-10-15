#!/usr/bin/env bash
# Arranque del demonio del Hackathon OS (M8d, api.md §4 y ADR-0004). Lo llama sesion.sh en SessionStart, ya con la
# coordinación activa. Sin os.md activo sale sin hacer nada. Si un demonio de este clon responde en su puerto, no hace
# nada; si nadie escucha, lo lanza desacoplado de la sesión y vuelve. Si el puerto es de otro programa o no hay uv,
# imprime una línea de aviso, una sola vez por sesión (lo anota en entregado/<session_id>), y no lo reintenta.
# Uso: arranque.sh <session_id> <persona>
# En las pruebas, HKOS_LANZAR=<fichero> escribe ahí el lanzamiento en vez de hacerlo; HKOS_SIN_SETSID=1 fuerza el
# camino de los sistemas sin setsid (macOS).
. "$(dirname "$0")/comun.sh"
sesion=$1 persona=$2
if (( BASH_VERSINFO[0] < 5 )); then   # M8h: el bash 3.2 de macOS; una vez por sesión, sin lanzar nada
  os_md_activo || exit 0
  [[ $sesion =~ ^[A-Za-z0-9_-]+$ ]] || exit 0
  marca=$OS_COMUN/hackathon/os/entregado/$sesion
  [[ -f $marca ]] && grep -x bash_viejo "$marca" >/dev/null 2>&1 && exit 0
  { mkdir -p "${marca%/*}" && echo bash_viejo >> "$marca"; } 2>/dev/null
  echo "Hackathon OS: este bash es el $BASH_VERSION y el OS necesita bash 5 o más (en macOS: brew install bash). Sigue apagado en este portátil; el kit funciona como siempre."
  exit 0
fi
os_activo || exit 0
[[ $sesion =~ ^[A-Za-z0-9_-]+$ ]] || sesion=
[[ $persona =~ ^[a-z0-9-]+$ ]] || exit 0
kit=$(cd "$(dirname "$0")/../.." && pwd)
dir=$OS_COMUN/hackathon/os
marca=$dir/entregado/$sesion
# Diagnóstico: una línea por SessionStart en os/arranque.log (qué hizo y cuánto tardó), sin red ni contexto.
t0=${EPOCHREALTIME/[.,]/} resultado=nada
registra() {
  local t=${EPOCHREALTIME/[.,]/} ts
  TZ=UTC0 printf -v ts '%(%Y-%m-%dT%H:%M:%S)T' -1
  { mkdir -p "$dir" && printf '%sZ %s %s %d ms\n' "$ts" "${sesion:--}" "$resultado" $(( (t - t0) / 1000 )) >> "$dir/arranque.log"; } 2>/dev/null
}
trap registra EXIT
if [[ -n $sesion && -f $marca ]]; then
  while IFS= read -r l; do [[ $l == puerto_ocupado || $l == sin_uv ]] && { resultado=ya_avisado; exit 0; }; done < "$marca"
fi
avisa() {   # una vez por sesión
  resultado=$1
  [[ -n $sesion ]] && { mkdir -p "$dir/entregado" && printf '%s\n' "$1" >> "$marca"; } 2>/dev/null
  printf '%s\n' "$2"
}

# Sin rutas de MSYS en los argumentos de git.exe: con MSYS_NO_PATHCONV=1 heredado no las entiende.
comun=$(cd "$OS_PRINCIPAL" && git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
puerto=
while IFS= read -r l || [[ -n $l ]]; do
  [[ ${l%$'\r'} =~ ^puerto_agente:[[:space:]]*([0-9]+) ]] && { puerto=${BASH_REMATCH[1]}; break; }
done < "$OS_PRINCIPAL/.hackathon/os.md" 2>/dev/null
if [[ -z $puerto ]]; then
  suma=$(printf '%s' "$comun" | cksum) && puerto=$(( 47100 + ${suma%% *} % 900 ))
fi
case $OSTYPE in msys*|cygwin*) win=1 ;; *) win= ;; esac
vivo=$dir/agente.vivo   # lo escribe el demonio al conseguir el puerto y lo borra al salir

# Un demonio vivo responde /salud con su git común en la primera línea (api.md §4); otra cosa es otro programa.
salud() {
  printf 'GET /salud HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n' >&3
  local l propio=
  while IFS= read -r -t 2 l <&3; do
    l=${l%$'\r'}
    if [[ $l == "hk-os "* ]]; then
      [[ ${l,,} == "hk-os ${comun,,}" ]] && propio=1
      break
    fi
  done
  exec 3<&-
  [[ -n $propio ]] && { resultado=vivo; exit 0; }
  avisa puerto_ocupado "Hackathon OS: el puerto $puerto está ocupado por otro programa; pon puerto_agente: en .hackathon/os.md. El demonio no se ha lanzado; los eventos esperan en disco."
  exit 0
}
# En Windows, conectar a un puerto local cerrado tarda ≈2 s (el sistema reintenta). Por eso allí solo se conecta
# directamente si el demonio ha dejado agente.vivo; si no, el sondeo (con un tope de 0,1 s) lo hace el mismo
# PowerShell que lo lanza. En Linux y macOS el rechazo es inmediato.
if [[ -z $win || -f $vivo ]] && { exec 3<>"/dev/tcp/127.0.0.1/$puerto"; } 2>/dev/null; then
  salud
fi

if ! command -v uv >/dev/null 2>&1; then
  avisa sin_uv "Hackathon OS: uv no está instalado, así que el demonio no se ha lanzado; los eventos esperan en disco (instalación: docs/hackathon-os/adr/0005-lenguaje-del-demonio-y-relay.md)."
  exit 0
fi

script=$kit/hkos/agente.py repo=$OS_PRINCIPAL
if [[ -n $win ]]; then
  # /c/x → C:/x, sin lanzar cygpath.
  [[ $script =~ ^/([A-Za-z])/(.*)$ ]] && script=${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}
  [[ $repo =~ ^/([A-Za-z])/(.*)$ ]] && repo=${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}
  # Otras rutas de MSYS (/tmp/… es la carpeta TEMP de Windows): PowerShell y uv no las entienden y el demonio no
  # arrancaba (M8h). cygpath cuesta un proceso, pero solo aquí, al lanzar.
  [[ $script == /* ]] && script=$(cygpath -m "$script" 2>/dev/null || printf '%s' "$script")
  [[ $repo == /* ]] && repo=$(cygpath -m "$repo" 2>/dev/null || printf '%s' "$repo")
fi
argumentos=(run --no-project "$script" --repo "$repo" --persona "$persona" --puerto "$puerto")

anota() { printf '%s\n' "${argumentos[*]}" >> "$HKOS_LANZAR"; }   # pruebas: lo que se lanzaría
if [[ -n $win ]]; then
  # Un hijo con nohup … & muere al acabar el hook (M8.0); Start-Process sobrevive al hook y a la salida de -p.
  # PowerShell 5.1 no entrecomilla los elementos de -ArgumentList: va una sola cadena con las comillas puestas. El
  # guion llega por la entrada estándar (-Command -), para no depender de cómo pasa Git Bash las comillas.
  q="'"
  lista="run --no-project \"$script\" --repo \"$repo\" --persona $persona --puerto $puerto"
  lanza="Start-Process -WindowStyle Hidden -WorkingDirectory '${repo//$q/$q$q}' -FilePath uv -ArgumentList '${lista//$q/$q$q}'"
  [[ -n $HKOS_LANZAR ]] && lanza="'lanzaria'"
  r=$(printf '%s\n' \
    "\$c = New-Object Net.Sockets.TcpClient; \$ok = \$false" \
    "try { \$ok = \$c.ConnectAsync('127.0.0.1', $puerto).Wait(100) } catch {} finally { \$c.Close() }" \
    "if (\$ok) { 'escucha' } else { $lanza }" \
    | powershell.exe -NoProfile -NonInteractive -Command - 2>/dev/null)
  if [[ $r == *escucha* ]] && { exec 3<>"/dev/tcp/127.0.0.1/$puerto"; } 2>/dev/null; then
    salud
  fi
  [[ $r == *lanzaria* ]] && anota
  resultado=lanzado
elif [[ -n $HKOS_LANZAR ]]; then
  anota
elif [[ -z $HKOS_SIN_SETSID ]] && command -v setsid >/dev/null 2>&1; then
  ( cd "$repo" && setsid -f nohup uv "${argumentos[@]}" >/dev/null 2>&1 </dev/null )
  resultado=lanzado_setsid
else
  # Sin setsid (macOS): el propio demonio se desacopla al arrancar (fork y os.setsid()).
  ( cd "$repo" && nohup uv "${argumentos[@]}" --desacoplar >/dev/null 2>&1 </dev/null & )
  resultado=lanzado_desacoplar
fi
exit 0
