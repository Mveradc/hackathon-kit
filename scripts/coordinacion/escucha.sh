#!/usr/bin/env bash
# Monitor del buzón (M6a). Lo arranca Claude Code con la sesión (monitors/monitors.json).
# No termina mientras viva su sesión: un monitor que sale genera un aviso y un turno del modelo.
# Mientras la coordinación no esté activa, duerme sin imprimir ni llamar a gh.
# Con ella activa, imprime una línea por novedad y nada más (el silencio no cuesta tokens).

. "$(dirname "$0")/comun.sh"

en_backoff=0
en_error=0

# Error que no es de límite (sin acceso al repo, token sin permisos…): un solo aviso hasta que se arregle.
aviso_error() {
  [ $en_error -eq 1 ] && return
  en_error=1
  echo "hk · buzón: no puedo leer $HK_REPO como @$HK_YO ($(head -1 "$HK_ESTADO/ultimo-error" | tr -d '\r')). ¿Tiene acceso esa cuenta? Sigo reintentando sin más avisos."
}

fin_error() {
  [ $en_error -eq 0 ] && return
  en_error=0
  echo "hk · buzón: ya puedo leer $HK_REPO"
}

sondear() {
  local desde ahora vistos lineas rc
  vistos="$HK_ESTADO/vistos"; touch "$vistos"
  desde=$(cat "$HK_ESTADO/cursor" 2>/dev/null || date -u -d '-1 day' +%Y-%m-%dT%H:%M:%SZ)
  ahora=$(date -u -d '-90 seconds' +%Y-%m-%dT%H:%M:%SZ)   # solape: lo repetido lo quita «vistos»

  # Issues tocados desde el cursor, también cerrados (una respuesta y un cierre pueden caer entre dos sondeos).
  lineas=$(hk_gh api "repos/$HK_REPO/issues?labels=hk&state=all&since=$desde&per_page=100" --jq "$HK_JQ"'
    .[] | select(.pull_request | not)
    | [.number, cab("de"), para, (([.labels[].name | select(startswith("hk:tipo-")) | ltrimstr("hk:tipo-")] | first) // ""),
       (.title | ltrimstr("[hk] ") | gsub("[\t\r\n«»]"; " ") | .[0:70]), .state] | fila' 2>"$HK_ESTADO/ultimo-error"); rc=$?
  [ $rc -eq 75 ] && { aviso_backoff; return; }
  if [ $rc -ne 0 ]; then aviso_error; return; fi
  fin_backoff; fin_error

  local n de para tipo titulo estado comentarios fallo=0
  while IFS="$HK_SEP" read -r n de para tipo titulo estado; do
    [ -n "$n" ] || continue
    [ "$para" = "$HK_YO" ] || [ "$de" = "$HK_YO" ] || continue
    if [ "$para" = "$HK_YO" ] && [ "$estado" = open ] && ! grep -qx "i:$n" "$vistos"; then
      echo "i:$n" >> "$vistos"
      echo "hk #$n · pregunta de @$de ($tipo) · «$titulo» · atiende con /hack-inbox"
    fi
    comentarios=$(hk_gh api "repos/$HK_REPO/issues/$n/comments?since=$desde&per_page=100" --jq "$HK_JQ"'
      .[] | [.id, (.user.login | ascii_downcase), cab("tipo"), cab("de"),
             ((.body // "") | gsub("[\r\n\t]+"; " ") | gsub("^ +| +$"; "") | ascii_downcase)] | fila' 2>/dev/null) || { fallo=1; continue; }
    local id autor ctipo cde cuerpo que
    while IFS="$HK_SEP" read -r id autor ctipo cde cuerpo; do
      [ -n "$id" ] || continue
      grep -qx "c:$id" "$vistos" && continue
      echo "c:$id" >> "$vistos"
      if [ -n "$ctipo" ]; then
        [ "$cde" = "$HK_YO" ] && continue                      # lo publicó mi agente
        que="$ctipo de @$cde"
      elif [ "$cuerpo" = "$HK_CONFIRMO" ]; then
        que="confirmación de @$autor"
      else
        que="comentario de la persona @$autor"
      fi
      echo "hk #$n · $que · «$titulo» · atiende con /hack-inbox"
    done <<< "$comentarios"
  done <<< "$lineas"

  [ $fallo -eq 0 ] && echo "$ahora" > "$HK_ESTADO/cursor"   # si algo falló, se repite (sin duplicar avisos)
}

aviso_backoff() {
  [ $en_backoff -eq 1 ] && return
  en_backoff=1
  echo "hk · buzón: GitHub limita o no responde; reintento en $(hk_espera) s (sin más avisos hasta que se recupere)"
}

fin_backoff() {
  [ $en_backoff -eq 0 ] && return
  en_backoff=0
  echo "hk · buzón: GitHub responde de nuevo"
}

# Al cerrar la sesión, Claude Code mata al proceso que lanzó el monitor, pero en Windows (Git Bash) el
# monitor sobrevive, huérfano: seguiría consultando GitHub y se quedaría avisos que no llegan a nadie
# (prueba de M6a, 2026-10-11). Si el padre ya no existe, la sesión ha terminado: salir no cuesta turnos.
padre=$PPID

while :; do
  kill -0 "$padre" 2>/dev/null || exit 0
  if hk_activa; then
    sondear
    sleep "$(hk_sondeo)"
  else
    sleep 60
  fi
done
