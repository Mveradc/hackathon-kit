# ADR-0010 · Seguridad de las acciones desde la web

Estado: **aceptada** (2026-10-17, por el usuario al abrir M9a). Amplía el principio V y ADR-0008.

## Contexto
Hasta M8h la web era de solo lectura y la servía el relay con el token del equipo. M9a añade dos acciones (Anotar y Reclamar) que escriben en git y en GitHub con la identidad de una persona y que pueden abrir un turno en su sesión de Claude Code. Si una acción pudiera llegar por el relay, cualquiera con el token del equipo podría poner a trabajar al Claude de otra persona. Si el demonio aceptara peticiones de cualquier página, una web cualquiera abierta en el navegador podría disparar acciones (CSRF) o leer el estado (DNS rebinding).

## Decisión
- **Quién sirve la web nueva:** el demonio de cada persona, en `127.0.0.1:<puerto_agente>` (el mismo puerto de `api.md` §4). La abre `hk-os web`. El relay no cambia: sigue sirviendo la web clásica de solo lectura en `GET /`, que es el respaldo, y **no tiene rutas de acción**.
- **Token local:** aleatorio (32 bytes), creado por el demonio la primera vez en `<git común>/hackathon/os/web.token` (fuera de git, como el del relay). Va en el fragmento de la URL (`/#t=<token>`), que el navegador no envía.
  - **No se rota:** se reutiliza en cada arranque (`Agente._token_web`, `api.md` §4) y vale hasta que alguien borre `web.token`; así las pestañas abiertas siguen tras reiniciar el demonio. Con el reto y respuesta en `/salud` (decisión 7 del PR #13, que llega en su PR de código), `hk-os web` ya no manda el token a un impostor que escuche en el puerto, que es por lo que se propuso rotarlo (issue #15, hallazgo 4). Riesgo aceptado: un token que se filtre por otra vía (una copia de `web.token` o de `web.html`) sigue valiendo hasta que se borre el fichero (2026-10-18, decisión 8C del usuario en el PR #13).
  - Nada más leerlo, la página lo quita de la URL (`history.replaceState`) y lo guarda **solo en memoria de la pestaña** (ni `localStorage`, ni `sessionStorage`, ni cookies). Al recargar, se vuelve a abrir con `hk-os web`.
  - Lo manda en la cabecera `X-HK-Token` en cada petición de datos (`GET /v1/vista`, `GET /v1/stream`) y de acción. **Nunca en la query** (quedaría en registros y en el historial).
  - `/v1/stream` es SSE, pero `EventSource` no admite cabeceras: la web lo lee con `fetch` y un `ReadableStream`, como la web clásica lee el del relay. Si el stream se corta, vuelve a conectar con espera creciente y, mientras, pide `/v1/vista`.
  - Para leer un solo `/v1/stream` por navegador y origen (`api.md` §4, «Cómo lee la web»), el cerrojo de `navigator.locks` y el `BroadcastChannel` entre pestañas llevan en el nombre la huella SHA-256 del token (`hk-os-stream-<huella>`), no el token, y por el canal no viaja el token. El token sigue solo en la memoria de cada pestaña, y solo comparten stream las que tienen el mismo (tras congelar, 2026-10-17, PR #17, issue #15).
- **Cada acción** (`POST /v1/anotar`, `POST /v1/reclamar`) solo se acepta si:
  - lleva `Content-Type: application/json` (si no, `415`) y la cabecera `X-HK-Token` con el token local, comparado en tiempo constante (si no, `401`). Una cabecera propia y ese tipo de contenido obligan al navegador a mandar antes un `OPTIONS` (preflight CORS), que el demonio nunca autoriza: ninguna otra página puede mandar la petición;
  - el `Host` es `127.0.0.1:<puerto>` o `localhost:<puerto>` (si no, `403`, contra DNS rebinding); lo mismo para las rutas de datos;
  - el `Origin`, si viene, es `http://127.0.0.1:<puerto>` o `http://localhost:<puerto>` (si no, `403`).
- **Sin cabeceras CORS** en ninguna respuesta. El demonio sigue escuchando solo en `127.0.0.1`.
- **Nunca por el relay.** Una acción solo va de la web de una persona a **su** demonio. Lo que viaja después es lo de siempre: el commit y el push (Anotar), la asignación del issue y el evento `reclamo` (Reclamar).
- **Lo que llega a la sesión es fijo.** Reclamar deja una línea en `<git común>/hackathon/os/acciones.jsonl` con solo el ID validado (`^T\d+$`); el monitor la convierte en un texto fijo del kit. El título de la tarea y el contenido de los issues no van en ese texto (principio V).
- **Anotar no toca la copia de trabajo ni el índice de la persona.** Es la misma técnica que `publicar_wip` (`api.md` §4):
  - `git fetch` y, con un índice temporal (`GIT_INDEX_FILE`), `read-tree origin/main`;
  - la nota se añade al final de `.hackathon/criterios.md` de `origin/main` (y `merge=union` a `.gitattributes` si falta);
  - `commit-tree -p origin/main`, con la identidad de git de la persona y sin coautoría;
  - `git push origin <sha>:refs/heads/main`.

  Si el push se rechaza (alguien subió antes), repite **una vez** todo lo anterior sobre el `origin/main` nuevo. Si vuelve a fallar, no hace nada más y lo dice en la web, con el motivo. **Nunca** hace un merge, un rebase ni un checkout en la copia de la persona. Los mismos `git` sin preguntas que `publicar_wip` (`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`…).
- **Entradas validadas por el demonio:** Anotar acepta solo los campos de la plantilla de `criterios.md`, con listas cerradas (papel y fuerza), en una sola línea, sin `#` al principio y con un máximo de 500 caracteres por campo. Reclamar solo acepta una tarea que existe, está libre y no es de otro dueño según el plan (`api.md` §5).
- **Declarado, no derivado** (principio II): `reclamo` lleva la fuente `web` y la vista lo pinta como declarado. Cada escritura a GitHub desde la web cuenta para el tope de R-30, con un tope propio por persona y hora en el demonio.

## Alternativas descartadas
- **Acciones por el relay con el token del equipo:** cualquiera del equipo, o quien tenga el token, podría actuar como otra persona y abrir turnos en su sesión.
- **Token en una cookie `SameSite=Strict`:** menos código en la web, pero más reglas en el demonio (poner y renovar la cookie, cookies de `127.0.0.1` compartidas entre puertos); la cabecera propia ya obliga al preflight.
- **Sin token, solo `Origin` y `Host`:** un programa local o una extensión del navegador podrían mandar peticiones sin `Origin`.

## Riesgos aceptados
- Quien tenga acceso al portátil (y por tanto a `web.token`) puede usar las acciones: es la misma persona, como con su `gh`.
- La URL con el token puede quedar en el historial del navegador de esa persona hasta que la página la limpia (la primera carga).
- Si `main` está protegida en GitHub, Anotar no puede subir: lo dice en la web y la nota se hace con `/hack-note`.
