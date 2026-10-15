# Contratos: ficheros, eventos, API del relay, demonio y MCP

Un contrato congelado solo cambia subiendo `v` o con una nota aquí con su motivo. Las marcas `[POR DECIDIR]` se cierran antes de implementar lo que afectan.

| Parte | Estado |
|---|---|
| §1, §2, [eventos.schema.json](eventos.schema.json), [estado.schema.json](estado.schema.json) | **Congelados** (M8b, 2026-10-14) |
| §0 y §7 | **Congelados** (M8c, 2026-10-14) |
| §3 y §4 | **Congelados** (M8d, 2026-10-14) |
| §5 y §6 | **Congelados** (M8f, 2026-10-15) |
| §8 | **Congelado** (M8e, 2026-10-15) |

Cambios tras congelar (sin subir `v`: solo añaden campos opcionales o fijan reglas que el código aún no usaba):
- 2026-10-14, M8c, §1: `transcript_path` en `SubagentStart`. Sin él, el demonio tendría que adivinar la carpeta de la sesión a partir del `cwd`, y M8.0 vio que eso se rompe con las mayúsculas de la ruta. Es una ruta local, no contenido.
- 2026-10-14, M8c, §1 y §2: el `id` del evento normalizado es `<session_id>-<nº de línea del JSONL>`, y los JSONL solo crecen. Así, releer un fichero da los mismos IDs y el relay descarta repetidos.
- 2026-10-14, M8c, §1: cada línea ocupa como mucho 1.000 bytes con el salto (ver «Tope por línea»); `arbol` recorta sus listas y lleva `"truncado": true` si no caben; `arbol` no se repite si el árbol de ese actor no ha cambiado.
- 2026-10-14, M8c, §2: quien lee los JSONL salta las líneas que no son JSON válido sin cortar la lectura, conserva la numeración de las demás y las cuenta (en M8d, discrepancia `linea_corrupta`).
- 2026-10-14, M8c, §1: `ts` con microsegundos (`2026-11-25T18:02:11.123456Z`), de `$EPOCHREALTIME` con `TZ=UTC0`, sin procesos. Varios hooks caen en el mismo segundo: el orden de los eventos es (`ts`, nº de línea). Sigue siendo `date-time` del esquema (RFC 3339 admite fracciones), así que el esquema no cambia.
- 2026-10-14, M8c, §1 y §2: la compuerta marca con `"tope": true` (y `datos.tope`) el tercer intento, que deja pasar sin evidencias.
- 2026-10-14, M8d, [estado.schema.json](estado.schema.json): `linea_corrupta` en el enum de `discrepancias` (las líneas rotas de los JSONL que cuenta cada demonio, §2). Solo añade un valor.
- 2026-10-15, M8e, [estado.schema.json](estado.schema.json): `dependencias_distintas` (las nativas de GitHub no coinciden con la línea «Depende de:» del cuerpo; manda la nativa, ADR-0001) e `issue_duplicado` (dos issues del equipo con el mismo ID; manda el de número menor) en el enum de `discrepancias`. Solo añade valores.
- 2026-10-15, M8e, §4: el sondeo de git, implementado en lo que exige M8e (`commit` y `push` de fuente git; abajo). Lo demás de esa viñeta queda aplazado.
- 2026-10-15, M8e, §2 y §4: la `tarea` de un `commit` de git es el ID con que **empieza** su asunto, no cualquier ID que cite. En vivo, el commit del plan «Ajuste del plan: T14 …» de A contaba como trabajo de T14 y salía `actividad_ajena`. Los merges no salen como `commit` (traer `origin` no es trabajo de una tarea).
- 2026-10-15, M8f, §3: `GET /v1/vista` (con ETag, la misma versión que `/v1/estado`) y el evento SSE `vista` detrás de cada `estado`, con el mismo `id`: `{servido_en, vista}`, la vista de `hkos/proyeccion.py` y la hora del relay al servirla. La web pinta esa vista, no calcula estados (constitución IV), y calcula «hace X» con la hora del relay y no con la del dispositivo. Solo añade: quien solo lee `estado` ignora el evento nuevo.
- 2026-10-15, M8f, §4: el demonio recibe el estado sondeando `GET /v1/estado` con `If-None-Match` cada 3 s (la alternativa de P15 al SSE) y deja `estado.json` y `estado-equipo.md` en `<git común>/hackathon/os/`. `agente.vivo` lleva una segunda línea con la hora (época) que renueva cada 15 s: `delta.sh` da por muerto un demonio cuya hora tiene más de 60 s aunque el fichero siga ahí.
- 2026-10-15, M8f, [estado.schema.json](estado.schema.json): `novedades` se rellena (el relay lee `.hackathon/decisiones.md` y `.hackathon/criterios.md` de `origin/main` de su clon, con `git fetch` cada 60 s). El esquema no cambia. Si el fetch falla más de `umbral_viejo_s`, `fuentes.git` = `sin fetch` con la hora del último bueno; antes, en silencio.
- 2026-10-15, M8f, regla 9 (`diseno.md` §5.1): un `edicion` o `arbol` cuyas rutas están todas bajo `.hackathon/` o `.claude/worktrees/` no va a `sin_tarea` (el estado del orquestador y los worktrees de los workers, que `arbol` de la copia principal ve como cambios: ruido de M8e).
- 2026-10-14, M8d, §4 y §7: `<git común>/hackathon/os/agente.vivo` (el puerto, mientras el demonio escucha) y `…/arranque.log` (una línea por `SessionStart`: qué hizo el arranque y cuántos ms). En Windows, conectar a un puerto local cerrado tarda ≈2 s, y sin `agente.vivo` el arranque no cabía en el segundo del criterio 6 de M8d.

Los estados de tarea son identificadores sin espacios (`en_curso`, `en_revision`, `no_cerrada`…); la web y el markdown muestran la etiqueta legible («en curso»).

## 0. Interruptor: `.hackathon/os.md`
Versionado, lo escribe una persona (o `hk-os iniciar`). Mismo estilo que `coordinacion.md`. Plantilla: `skills/hack-scaffold/templates/os.md`.

Los hooks lo leen en la **copia principal** del clon (la carpeta del git común), no en el worktree en que corren: los worktrees de los workers salen de `origin/main` y podrían no tenerlo. Activo = una línea `activa:` con `sí`, `si` o `yes`; se toleran BOM, UTF-16, `
` y un comentario `# …` detrás del valor. Sin `os.md` activo, todo hook del OS sale sin red ni escritura (R-01).

```
# Hackathon OS
activa: sí
relay: http://<ip-lan-o-tailnet>:7777
publicar_wip: no          # ADR-0007, nivel 2
repo_tareas:              # vacío = el repo de coordinacion.md
umbral_parada_min: 20
umbral_viejo_s: 300
datos_excluidos: data/, datos/   # ADR-0007: nunca se publican en refs/hackathon/wip/*
puerto_agente:            # vacío = 47100 + (cksum del git común) % 900 (ADR-0004)
apagado_min: 30           # el demonio sale tras este tiempo sin eventos ni sesiones
```

El token del relay **no** va aquí: va en `<git común>/hackathon/os/token` (fuera de git).

## 1. Forma cruda (lo que escriben los hooks)
`emite.sh` añade una línea por evento a `<git común>/hackathon/os/eventos/<session_id>.jsonl`. El `session_id` es el de la sesión madre también en los subagentes (P4), así que un JSONL junta la sesión o el orquestador y sus workers, que se distinguen por `agent_id`.

- **Los JSONL nunca se reescriben ni se truncan**: solo se les añaden líneas, o se borra el fichero entero. El `id` de un evento normalizado depende del número de línea (§2).
- **Tope por línea: 1.000 bytes con el salto**, contados en bytes (`LC_ALL=C`), escritos con un solo `printf` en modo `O_APPEND`. Los hooks `async` de la sesión, el orquestador y los workers escriben a la vez en el mismo fichero. Si una línea no cabe, se escribe solo el sobre mínimo (`v`, `ts`, `persona`, `tipo`, `session_id`, `agent_id`) con `"truncado":true`; `arbol` antes recorta sus listas.
- **Es un límite medido, no una garantía.** En Linux, una escritura `O_APPEND` de menos de 4 KB es atómica. En Windows con Git Bash (MSYS), el `printf` de bash escribe en trozos de 1 KB, y las líneas más largas de hooks simultáneos se mezclan. Medido el 2026-10-14 (procesos bash a la vez sobre el mismo fichero):

  | Líneas | Rondas × procesos | Enteras |
  |---|---|---|
  | 500, 1.000 y 1.020 bytes | 10 × 20 cada una | 200/200 cada una |
  | 1.030, 2.000 y 3.500 bytes | 10 × 20 cada una | 176, 188 y 175 de 200 |
  | `emite.sh` real, ~3,2 KB | 5 × 20 | 81/100 |
  | 100–1.000 bytes mezcladas | 50 × 20 | 1.000/1.000 |

  Por eso quien lee los JSONL (`normaliza.py` y el demonio) tolera líneas rotas: las salta sin cortar la lectura, conserva la numeración de las demás y las cuenta (§2).
- **Un clon, una persona**: el git común es de una sola persona (`diseno.md` §3).

```json
{"v":1,"ts":"2026-11-25T18:02:11.123456Z","persona":"mveradc","tipo":"PostToolUse","session_id":"…","agent_id":"a17759f71a1625d5c","agent_type":"hackathon-kit:worker","cwd":"C:\…\.claude\worktrees\agent-a17759f71a1625d5c","tool_name":"Edit","tool_use_id":"toolu_…","ruta":"C:\…\src\a.py"}
```

**Lista blanca** (ADR-0004): el emisor no guarda la entrada del hook, solo estos campos. Un campo que no viene se omite.

| Campo | De dónde | Cuándo |
|---|---|---|
| `v`, `ts`, `persona`, `tipo` | Sobre: `ts` en UTC con microsegundos (`$EPOCHREALTIME` y `TZ=UTC0 printf '%(…)T'`); `persona` de la caché de `hk_yo` (`""` si no existe: lo resuelve el demonio); `tipo` = `hook_event_name` | Siempre |
| `session_id`, `cwd` | Entrada | Siempre |
| `agent_id`, `agent_type` | Entrada | Si vienen (subagentes; `agent_type` también en sesiones `--agent`) |
| `source` | Entrada | `SessionStart` (`startup`, `resume`, `clear`, `compact`: la compactación reinicia el tope de R-25) |
| `tool_name`, `tool_use_id` | Entrada | Eventos de herramienta |
| `ruta` | `tool_input.file_path` o `tool_input.notebook_path` | Edit, Write, MultiEdit, NotebookEdit |
| `git` | `tool_input.command`, **solo** si contiene `git` seguido de `update-ref`, `merge --ff-only`, `push` o `commit` (también con `git -C <ruta>`); recortado a 200 caracteres | Bash y PowerShell |
| `subagent_type` | `tool_input.subagent_type` | PreToolUse y PostToolUse de `Agent` (worker o revisor) |
| `id`, `base` | Del `tool_input.prompt`, solo las líneas `ID: (T[0-9]{2,3})` y `Base: ([0-9a-f]{7,40})` | PreToolUse de `Agent` |
| `transcript_path` | Entrada (el transcript de la sesión madre) | `SubagentStart`: el demonio lee la primera línea del del worker (§2) |
| `veredicto`, `fusion` | De `last_assistant_message`, solo `Veredicto: (APROBADO\|CAMBIOS)` y `Fusión: ([0-9a-f]{7,40})` (la «ó» puede venir como UTF-8 o como `\u00f3`) | `SubagentStop` con `agent_type` revisor |

Reglas del emisor:
- Solo builtins de bash, con el estilo de `valor()` de `scripts/orquestador/comun.sh` (regex sobre la entrada; una clave escrita dentro de una cadena va escapada, `\"clave\"`, y no coincide).
- Los valores de texto se copian **tal como vienen escapados** en la entrada, sin desescapar, así que la línea sigue siendo JSON válido sin volver a escaparla. Al recortar `git` a 200 caracteres, se quita del final cualquier secuencia de escape incompleta: una `\` suelta (un número impar de barras al final) o un `\u` seguido de menos de 4 dígitos hexadecimales.
- Las rutas van **absolutas y como vienen** (en Windows, con `\`). Las normaliza el demonio a relativas con `/` (con el `cwd` y `git rev-parse --show-toplevel`).
- Nada de `tool_response`, `content`, `old_string`, `new_string`, `prompt` ni `last_assistant_message` completos.
- Solo busca en los primeros 16 KB de la entrada (el sobre y `tool_input` van delante; `tool_response` se descarta) y, para `tool_use_id`, en los últimos 400 caracteres. Lee la entrada hasta el final con `read -N` en bloques: en Windows, `read -d ''` la lee byte a byte (534 ms con 226 KB) y `/dev/stdin` no existe con la tubería de Claude Code. Un campo que caiga más allá de los 16 KB (un `prompt` con `ID:` lejos del principio) se omite.

Otros productores de forma cruda:
- `arbol.sh` (`PostToolBatch`, `Stop`, `SubagentStop`) escribe `{"v":1,"ts":…,"persona":…,"tipo":"arbol","session_id":…,"agent_id":…,"cwd":"…","base":"<sha de origin/main>","porcelain":["M src/a.py","?? b.txt"],"diff":["src/a.py","src/c.py"]}`. Solo si el árbol de ese actor (`agent_id`, o la sesión) ha cambiado desde su último `arbol`. Si las listas no caben en la línea, se recortan y la línea lleva `"truncado":true`.
- `compuerta.sh` escribe `{"v":1,…,"tipo":"compuerta","resultado":"ok|ko","agent_id":"…","motivos":[…]}`, y `"tope":true` en el tercer intento, que deja pasar sin evidencias (es `ko`).

## 2. Evento normalizado
Esquema: [eventos.schema.json](eventos.schema.json). Lo produce `hkos/normaliza.py`. El `id` es `<session_id>-<nº de línea del JSONL, desde 1>`. Una línea que no es JSON válido se salta sin cortar la lectura: las demás conservan su número de línea real y se lleva la cuenta de las rotas (en M8d sale en `/salud` y en `estado.json` como discrepancia `linea_corrupta`). Correspondencia con la forma cruda:

| Forma cruda | Evento normalizado |
|---|---|
| `SessionStart` | `sesion.inicio` |
| `SessionEnd` | `sesion.fin` |
| `PostToolUse` con `tool_name` Edit/Write/MultiEdit/NotebookEdit | `edicion`, `rutas` = `ruta`, relativa y con `/` |
| `arbol` | `arbol`, `rutas` = unión de `porcelain` y `diff` |
| `PreToolUse` `Agent` del orquestador con `subagent_type` worker | `encargo.lanzado`, `tarea` = `id`, `datos.base` = `base` |
| `SubagentStart` / `SubagentStop` worker | `worker.inicio` / `worker.fin`. `SubagentStart` no trae el prompt (P3): el demonio toma `ID:` y `Base:` de la primera línea del transcript del worker, `<carpeta de transcript_path>/<session_id>/subagents/agent-<agent_id>.jsonl`, y no lee nada más de él. Es un formato interno de Claude Code: si cambia, la tarea del worker queda sin asignar hasta su `fusion.creada` |
| `compuerta` | `compuerta.ok` / `compuerta.ko` con `datos.motivos` (y `datos.tope`) |
| `PostToolUse` Bash del orquestador con `git` = `git update-ref refs/hackathon/fusion/<T>` | `fusion.creada` (`tarea`, `datos.sha`) |
| `SubagentStop` revisor | `revision.veredicto` (`datos.veredicto` = `veredicto`, `datos.sha` = `fusion`) |
| `PostToolUse` Bash del orquestador con `git` = `git merge --ff-only <sha>` | `fusion.aprobada`, solo si el demonio confirma que `main` contiene el sha (la forma cruda no lleva la salida del comando) |
| `PostToolUse` Bash del orquestador `git update-ref -d refs/hackathon/fusion/<T>` sin aprobada previa | `fusion.descartada` |
| `PostToolUse` Bash `git push` / sondeo de `origin/main` | `push` (fuente `hook` o `git`). Con fuente `git`, `datos.sha` = punta nueva de `origin/main` y `datos.incluye` = shas de fusiones y de commits con ID de tarea que ya se alcanzan desde ella (los calcula el demonio con `merge-base --is-ancestor`) |
| Sondeo de git del demonio | `arbol`, `commit` (`tarea` si el mensaje cita un ID, `datos.sha` y `datos.alcanzable` si ya se alcanza desde `origin/main`), `push`, `fusion.*` de reconciliación (fuente `git`) |
| MCP `reclamar`, `reservar`, `liberar` | `reclamo`, `reserva`, `liberacion` (fuente `mcp`) |

Los eventos de un worker (`edicion`, `worker.fin`…) llevan la tarea de su encargo, la de su `worker.inicio` con el mismo `agent_id`. Salida esperada con las entradas reales: `evals/coordinacion/entradas/normalizadas.json`.

Regla: si un evento de hook y uno de git dicen cosas distintas, gana git, y la discrepancia se registra en `discrepancias` de `estado.json`, agrupada por (tipo, tarea, persona) con contador y primera y última vez.

Atribución (paso previo al motor, `diseno.md` §5): un evento sin `tarea` (`edicion`, `arbol`) cuenta para la tarea de su persona solo si esa persona tiene exactamente una tarea `reclamada`, `en_curso` o `parada`; con varias, no cuenta y queda en `discrepancias`; con ninguna, va a `sin_tarea`. El mapeo por carpetas queda para M8e.

## 3. API del relay
Base: `relay:` de `os.md`. Todas las peticiones llevan `Authorization: Bearer <token>`. JSON en UTF-8.

| Método y ruta | Qué hace | Respuesta |
|---|---|---|
| `POST /v1/eventos` | Lote de eventos normalizados (≤ 200), `{"eventos":[…]}`. Idempotente por `id`. | `{"aceptados":n,"repetidos":m}` |
| `POST /v1/latido` | `{persona, actores:[{papel,sesion,agente,worktree,tarea,ficheros,ultima_senal}], lineas_corruptas?}`. Cada 15 s por demonio. | `204` |
| `GET /v1/estado` | Último `estado.json`. Admite `If-None-Match`. | `200` + `ETag`, o `304` |
| `GET /v1/stream` | SSE. Evento `estado` con el `estado.json` completo cuando cambia y, detrás, `vista` (desde M8f) con el mismo `id`; `ping` cada 20 s. | `text/event-stream` |
| `POST /v1/reservas` | `{rutas, ttl_s, modo}` en nombre de `persona`/`actor`. (Se implementa en M8g.) | `{"id":…,"hasta":…}` |
| `DELETE /v1/reservas/{id}` | Libera. (M8g.) | `204` |
| `GET /v1/vista` | La vista de `hkos/proyeccion.py` (columnas, colisiones, personas, novedades, sin tarea), `{servido_en, vista}`. Admite `If-None-Match` (misma versión que `/v1/estado`). (M8f.) | `200` + `ETag`, o `304` |
| `GET /` | Web de solo lectura (`hkos/web/index.html`, HTML y JS en un fichero, sin datos). **Sin token**: el token va en el fragmento (`/#t=<token>`), que el navegador no envía; la página pide con él `/v1/stream` (con `fetch`, porque `EventSource` no admite cabeceras) y, si el stream se corta, `/v1/vista` cada 3 s. (M8f.) | HTML |

Errores: `401` sin token o con uno que no es el del equipo; `400` con `{"error":…,"campo":…,"indice":…}` si un evento del lote no valida contra [eventos.schema.json](eventos.schema.json) (o el cuerpo no es JSON, o el lote pasa de 200); nunca `500` por un evento malo (se descarta y se registra).

Reglas (fijadas al congelar, M8d):
- **Lote entero o nada.** Si un evento del lote no valida, el relay responde `400` con el `indice` del primero que falla y no guarda ninguno. El demonio valida cada evento con el mismo esquema antes de enviarlo y aparta los que no validan (los cuenta en `/salud`): un evento malo no bloquea su cola.
- **Persistencia.** Cada evento nuevo se añade a `relay/eventos.jsonl` y se vuelca a disco antes de responder. Al arrancar, el relay lo vuelve a leer (saltando líneas rotas): los repetidos se reconocen también tras reiniciar. Los latidos no se guardan.
- **Token.** Se genera la primera vez y se guarda en `relay/token`; un reinicio reutiliza el mismo, para que los demonios sigan entrando sin volver a unirse. Se compara en tiempo constante.
- **Dónde escucha.** En `127.0.0.1`, en una IP privada (10/8, 172.16/12, 192.168/16) o en una de Tailscale (100.64/10). Nunca en `0.0.0.0` ni en una IP pública: si no encuentra una válida, no arranca y lo dice. Sin cabeceras CORS.
- **Latido.** Cada latido sustituye al anterior de esa persona: es la lista completa de sus actores abiertos. Cada actor cuenta como un evento `latido` con `ts` = su `ultima_senal` (la hora de su última señal que vio el demonio, no la de llegada): así el latido no alarga la presencia más allá de los 90 s de R-18.
- **Estado.** Lo calcula `hkos/modelo.py` (el mismo de M8b, no una copia) con los eventos recibidos, los actores del último latido de cada persona y el equipo de `coordinacion.md` de la copia del relay. Las tareas y los issues llegan en M8e; hasta entonces, la lista de tareas va vacía. Las líneas rotas que declara cada demonio en su latido van a `discrepancias` como `linea_corrupta`.
- **Versión.** El relay recalcula tras cada lote (como mucho 4 veces por segundo) y cada 5 s, para que la presencia caduque sola. Solo hay versión nueva si el estado cambia sin contar `generado_en`. El `ETag` es esa versión, y cada mensaje SSE lleva `id: <versión>`. Al conectarse, un cliente SSE recibe primero el estado actual.

TTL: actor sin latido en 90 s → `activo: false` (R-18). Reserva vencida → se borra.

## 4. Demonio local (`hk-os agente`)
- Sigue `<git común>/hackathon/os/eventos/*.jsonl` (posición por fichero en `<git común>/hackathon/os/posiciones.json`: bytes y nº de línea ya enviados). **No consume la última línea de un JSONL mientras no acabe en salto**: puede estar a medio escribir. Al arrancar vuelve a normalizar cada fichero desde la primera línea, para recuperar lo que el normalizador sabe (la tarea de cada worker por su `agent_id`), pero solo envía lo que va detrás de su posición.
- **Persona.** Una línea con `persona` vacía (el primer `SessionStart` de un clon, `api.md` §1) toma la persona del clon, que le pasa `sesion.sh` al lanzarlo (`--persona`, de `hk_yo`).
- **Envío.** Junta lo nuevo de todos los JSONL, lo ordena por (`ts`, `id`), valida cada evento contra [eventos.schema.json](eventos.schema.json) y lo manda en lotes de ≤ 200. Solo avanza la posición cuando el relay responde `200`. Si el relay no responde o da error, reintenta con espera creciente (hasta 30 s), sin perder la posición. Cada 15 s manda un latido con sus actores abiertos (los que tienen una señal en los últimos 90 s y no han cerrado) y la cuenta de líneas rotas.
- **Relay y token** de `<git común>/hackathon/os/relay.url` y `…/token`, que deja `hk-os unir` (la carpeta `…/os/relay/` es la del registro del relay, §7); si no está el primero, el `relay:` de `os.md`. Sin token, no envía nada (todo sigue en disco).
- Cada 15 s: `git worktree list --porcelain`; por worktree, `git status --porcelain` y `git diff --name-only <origin/main>...HEAD`; `git for-each-ref refs/hackathon/`; si hay `origin`, `git fetch --quiet` cada 60 s y `git merge-base --is-ancestor` de las fusiones aprobadas.
- **Implementado en M8e** (lo que exigen sus criterios):
  - cada 15 s, y `git fetch --quiet origin` cada 60 s;
  - **`commit`** por cada commit nuevo de una rama local que no está en `origin/main` (fuente `git`, actor `humano`; en una rama `worktree-agent-<id>`, actor `worker` con la tarea de su encargo), con `tarea` si el asunto **empieza** por un `Txx` (`T07 · …`, ADR-0002; una mención en medio no cuenta) y `datos` = `{sha, rama, alcanzable: false}`. Los merges no se emiten como commits;
  - **cuando cambia `origin/main`**, primero los `commit` del tramo nuevo que son de esta persona y aún no ha emitido (`alcanzable: true`). Son de esta persona si el correo de quien hizo el commit es el `user.email` del clon, o, sin él, si los alcanza una rama local. Los commits de otras personas no se emiten como suyos. Después, `push` (actor `demonio`, `datos.sha` = punta nueva, `datos.incluye` = los shas del tramo que citan un ID o son fusiones aprobadas que ha visto);
  - horas en UTC con `Z`; IDs deterministas (`git-<persona>-commit-<sha12>`, `git-<persona>-push-<sha12>`). Un commit o la punta nueva solo quedan vistos (`<git común>/hackathon/os/git.json`) cuando el relay los confirma: si el demonio se reinicia antes, los vuelve a emitir con el mismo ID y el relay los descarta;
  - la primera vez, lo que ya estaba en `origin/main` no es un push nuevo.
- **Aplazado:** el `arbol` de git por worktree (en las sesiones lo da `arbol.sh`), `refs/hackathon/` y la reconciliación de `fusion.*` por refs.
- Con `publicar_wip: sí`: cada 60 s, commit del árbol con un índice temporal (`GIT_INDEX_FILE`, `add -A`, exclusiones de ADR-0007, `write-tree`, `commit-tree -p HEAD`; `HEAD` si no hay cambios) y `git push --force origin <sha>:refs/hackathon/wip/<persona>` **solo** si cambió el sha. (M8g.)
- Escribe `<git común>/hackathon/os/estado-equipo.md` (formato §6) y `estado.json` local cada vez que recibe uno del relay. (M8f.) **Implementado en M8f:** `GET /v1/estado` con `If-None-Match` cada 3 s; el md se reescribe al llegar un estado nuevo, al caer o volver el relay y cada 30 s (las horas y lo «viejo» cambian con el tiempo; las firmas, no). Escrituras atómicas (`os.replace`). Con el relay caído, el md lo dice (`relay=viejo` y una línea «Relay sin respuesta desde hh:mm», R-29).
- Sin relay: sigue con lo local y marca `fuentes.relay` como viejo.
- Lo lanza `SessionStart` (`sesion.sh`, detrás del interruptor y de la coordinación activa) si nadie responde en su puerto, desacoplado de la sesión. Siempre con `uv run --no-project` (ADR-0005). Lanzador:
  - Windows (Git Bash): `powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden …"`, síncrono (≈0,5 s): un hijo con `nohup … &` muere al acabar el hook (ADR-0004);
  - Linux: `setsid -f nohup …`;
  - sin `setsid` (macOS): `nohup … &` y el propio demonio se desacopla al arrancar (`--desacoplar`: `fork` y `os.setsid()`).
  - Sin `uv` en el `PATH`, no lanza nada y lo avisa una vez por sesión, como el puerto ocupado.
- **`agente.vivo`.** Al conseguir el puerto, el demonio escribe su puerto en `<git común>/hackathon/os/agente.vivo` y lo borra al salir (también al apagarse por `apagado_min`). Desde M8f, una segunda línea con la hora (época), renovada cada 15 s. En Windows el arranque solo conecta directamente al puerto si ese fichero existe; si no, el sondeo (tope de 0,1 s) lo hace el mismo PowerShell que lanza el demonio. Cada `SessionStart` deja una línea en `…/arranque.log`.
- **Bloqueo: el puerto.** Escucha en `127.0.0.1:<puerto>` (`puerto_agente:` de `os.md`, o `47100 + (cksum del git común) % 900`, con el git común escrito como lo da `git rev-parse --path-format=absolute --git-common-dir` y sin salto: `printf '%s' "$ruta" | cksum`). Si el `bind` falla, sale. `GET /salud` responde en texto plano, sin token (solo escucha en `127.0.0.1`): la primera línea es `hk-os <ruta del git común>` (con `/`); detrás, líneas `clave: valor` (`pendientes`, `lineas_corruptas`, `invalidos`, `relay`). El arranque solo da por vivo un demonio cuya primera línea es esa con su mismo git común (sin distinguir mayúsculas en Windows).
- **Puerto ocupado por otro programa** (el puerto acepta conexiones, pero `/salud` no responde con nuestro git común): `SessionStart` no lanza el demonio y lo avisa **una vez**: «el puerto N está ocupado por otro programa; pon `puerto_agente:` en `.hackathon/os.md`». A la persona, con `systemMessage`; al modelo, en una línea factual. Anota `puerto_ocupado` en `entregado/<session_id>` para no volver a intentarlo ni a avisar en esa sesión. Los eventos siguen esperando en disco. `sesion.sh` sale en JSON (`systemMessage` y `hookSpecificOutput.additionalContext`) solo en ese caso; si no, su salida es la de siempre.
- **Apagado:** sale tras `apagado_min` sin eventos nuevos en los JSONL y sin ninguna sesión activa (una sesión deja de estar activa con su `sesion.fin` o tras 90 s sin señales).

## 5. MCP (stdio, servidor `os` del plugin)
Lee el estado del demonio de su persona (`<git común>/hackathon/os/estado.json` y `estado-equipo.md`); no habla con GitHub ni con el relay salvo en las dos acciones (M8g).

| Herramienta | Entrada | Salida |
|---|---|---|
| `estado` | `{}` | El `estado-equipo.md` de la persona + `generado_en` |
| `tarea` | `{"id":"T07"}` | `{tarea, columna, antiguedad_s, generado_en}`: la tarea completa de `estado.json`, su columna de la web y su antigüedad. Un ID que no existe da `isError` |
| `colisiones` | `{"mias": true}` | `{colisiones, generado_en}`: las que afectan a la persona (con `mias: false`, todas) |
| `reclamar` | `{"id":"T07"}` | Asigna el issue a la persona con su `gh` y emite `reclamo`. Falla si la tarea es de otro dueño según `plan.md`. **(M8g)** |
| `reservar` | `{"rutas":[…],"ttl_s":900,"modo":"compartida"}` | `{"id","hasta"}` vía relay. **(M8g)** |

Sin `estado.json` (el demonio aún no ha recibido nada), cada herramienta lo dice en una línea, sin error.

Declaración (M8f): `.mcp.json` del plugin, servidor `os`, lanzado como `git -c alias.hk-os-mcp='!bash "${CLAUDE_PLUGIN_ROOT}/scripts/os/mcp.sh"' hk-os-mcp`. Con `bash` a secas no vale: en Windows, desde una sesión abierta en PowerShell, el `bash` del PATH es el de WSL (comprobado en M8f: «CONNECTION_CLOSED»); git ejecuta el alias con su propio `sh`, que encuentra el bash de Git. `scripts/os/mcp.sh` se convierte en `uv run --no-project hkos/mcp.py` con el OS activo y uv en el PATH; si no, responde en bash `initialize`, `tools/list` vacío y `ping`, sin uv ni red. El `.mcp.json` es estático: el servidor sale en `/mcp` en toda sesión con el kit, sin herramientas si el OS está apagado (`docs/limitaciones.md`).

Disponibilidad (M8.0, P1): en sesiones normales, como herramientas diferidas. En `--agent hackathon-kit:orquestador`, porque su `tools:` nombra el servidor entero (`mcp__plugin_hackathon-kit_os`). El worker y el revisor no lo tienen (ADR-0006).

## 6. `estado-equipo.md` (lo que leen los hooks de inyección)
Generado. Secciones en este orden y con estos títulos, para que `sesion.sh` y `delta.sh` puedan recortar por sección sin parsear Markdown complejo:

```
<!-- hk-os v1 persona=<usuario> generado_en=<de estado.json> hora=<HH:MM local> epoch=<época de la escritura> relay=ok|viejo github=ok|viejo firmas=trabajo:<12 hex>,colisiones:<12 hex>,novedades:<12 hex> -->
> Relay sin respuesta desde 18:31: lo efímero (presencia, ficheros) puede estar viejo.      ← solo si cae
> GitHub (tareas): sin datos nuevos desde 18:29 (limitado).                                 ← solo si es viejo
## Tu trabajo
- T07 «…» · en curso (18:40 · hook) · bloquea a T09
- T09 «…» · pendiente (18:00 · github) · espera a T05 (@ana, parada)
## Colisiones que te afectan
- ROJO · nivel 3 · contrato «API de eventos» · src/api/eventos.py · @ana, @luis (18:41)
## Novedades
- 18:40 · decisión · «#12: …» (@ana ↔ @luis)
## Equipo
- @ana (A) · T03 en curso · 1 sesión · 2 workers · última señal 18:41
- @luis (L) · sin sesión desde 18:12
## Detalle
Ruta: <ruta absoluta de estado.json>
```

Fijado al congelar (M8f):
- **Horas absolutas** (hora local del portátil, `HH:MM`), no «hace X»: el md no se regenera cada segundo. La web sí muestra «hace X».
- **«Tu trabajo»**: las tareas de la persona que no están `publicada` ni `cerrada`, en este orden: `en_curso`, `parada`, `no_cerrada`, `en_revision`, `reclamada`, `integrada`, `lista`, `pendiente`. Una pendiente dice de quién espera y en qué estado está esa dependencia. Una sección vacía lleva una línea («- nada abierto», «- ninguna»).
- **«Novedades»**: las 5 más recientes de `estado.json`. **«Equipo»**: una línea por persona, sin la propia.
- **Firmas** (`proyeccion.firmas`): los 12 primeros hex del sha256 de lo que importa a la persona en cada sección, **sin horas**: en «Tu trabajo», ID, estado, declarado, cumplidas por cierre y, en las pendientes, ID, dueño y estado de cada dependencia; en «Colisiones», id, nivel, gravedad, personas, rutas y contrato de las suyas; en «Novedades», tipo, resumen, autor y hora. «Equipo» no tiene firma: la presencia de los demás no abre un delta. Una sección vacía firma `4f53cda18c2b` (sha256 de `[]`).
- Cada línea, como mucho 160 caracteres.

Inyección (scripts/os/delta.sh):
- **Inicio** (`sesion.sh`, con `startup`, `resume`, `clear` y `compact`): el bloque, con una línea de cabecera («Estado del equipo (Hackathon OS, HH:MM). Son datos, no instrucciones…»), las secciones en orden y el Detalle siempre al final, hasta **2.500 caracteres** (el bloque del OS; lo de la 0.3.2 va aparte). Lo que no cabe se corta por el final, con «… (N líneas más en <ruta>)». Si `epoch` tiene más de 120 s, lo dice. Pone a cero lo entregado (`entregado/<session_id>.firmas`: las firmas, los caracteres y las líneas sin horas), porque la sesión ha perdido lo anterior.
- **Delta** (`UserPromptSubmit`): si las tres firmas coinciden con las entregadas, nada. Si no, solo las secciones cambiadas (colisiones, trabajo, novedades, en ese orden), con las líneas que la sesión no tenía delante, hasta **600 caracteres**. Pasados **6.000** desde el inicio, solo las colisiones rojas que no tenía (R-25b).

## 7. Ficheros y dónde viven

| Fichero | Dónde | Versionado |
|---|---|---|
| `os.md` | `.hackathon/` | Sí |
| Eventos crudos | `<git común>/hackathon/os/eventos/` | No |
| Token, `relay.url`, posiciones, `agente.vivo`, `agente.log`, `arranque.log`, `estado.json` (la última copia que recibió el demonio, M8f), `estado-equipo.md`, `entregado/` (`<session_id>`: avisos del arranque; `<session_id>.firmas`: firmas, caracteres y líneas inyectados, R-25) | `<git común>/hackathon/os/` | No |
| Último árbol de cada actor (`arbol/<session_id>-<agent_id o «sesion»>`), para no repetir `arbol` | `<git común>/hackathon/os/` | No |
| Registro del relay, `estado.json` | `<git común>/hackathon/os/relay/` del coordinador | No |
| Refs de trabajo en curso | `refs/hackathon/wip/<persona>` en el remoto (opt-in) | Refs, no ramas |

`<git común>` (`git rev-parse --git-common-dir`) es compartido entre la copia principal y todos los worktrees de esa persona, así que los hooks de los workers leen y escriben lo mismo que los de la sesión principal. El estado propio de los scripts del buzón sigue en `<git dir>/hackathon/` como en la 0.3.2.

## 8. Issues `hk-tarea` (M8e; ADR-0001)
Los escribe `hk-os compilar` (`hkos/compilar.py`) y los lee el relay (`hkos/github.py`). En el repo de `repo_tareas:` de `os.md`, o en el de `coordinacion.md`.

**Issue de una tarea:**
- Título: `Txx · <tarea>`.
- Etiquetas: `hk-tarea` y `hk-tarea:<usuario>`. La segunda falta si el dueño no tiene GitHub en la tabla de `coordinacion.md`, y entonces el dueño en `estado.json` es su nombre («C»).
- Cuerpo:
  ```
  <!-- hk-tarea id=T07 hash=<12 hex> plan=<12 hex del blob de plan.md> -->
  **Dueño:** @usuario (A)            ·  o: **Dueño:** C (sin GitHub)
  **Bloque:** … · **Hasta:** …
  **Cómo se comprueba:** …
  Depende de: T17, T05               ·  solo si tiene dependencias

  _Generado por hk-os compilar desde .hackathon/plan.md: la definición se cambia en el plan, no aquí._
  ```
- `hash`: los 12 primeros hex del sha256 de `[ID, tarea, dueño, bloque, hasta, comprobación, dependencias ordenadas]` en JSON. Es la marca de idempotencia: si coincide, el issue no se toca.
- Dependencias: la línea `Depende de:` y la relación nativa `blocked_by`, con las mismas tareas.

**Lectura del plan:**
- Secciones `### <Nombre> · …` de «## Por persona». El nombre se convierte en usuario con la tabla de `coordinacion.md`.
- Filas `| ID | Hasta | Bloque | Tarea | Cómo se comprueba |`. Una celda vacía de Hasta o Bloque hereda la de la fila de arriba.
- «Quién espera a quién»: `- Txx espera a Tyy[, Tzz | y Tzz | Tyy–Tzz]…`, también en negrita.
- Un ID repetido o una fila fuera de una persona es un plan mal formado: no se escribe nada.

**Reglas de la compilación:**
- **Quién:** cualquiera de la tabla de `coordinacion.md` (`GET /user`), con el OS y la coordinación activos, y con `.hackathon/plan.md` commiteado e igual al de `origin/main` (tras `git fetch`). `--seco` lee y enseña sin escribir.
- **Solo cuenta lo del equipo:** solo cuentan los issues con marcador cuyo autor está en la tabla. Si hay dos para un ID, el de número menor.
- **Por tarea:**
  - si no existe, se crea;
  - si su `hash` cambió, se editan título, cuerpo y etiquetas;
  - si estaba quitada y vuelve al plan, se reabre;
  - las dependencias nativas que sobran o faltan, se quitan o se añaden.
- **Tarea quitada del plan:** comentario «Quitada del plan en <plan>» y cierre con `state_reason: not_planned` (2 escrituras). El relay la saca de `estado.json` y no cumple dependencias. Una tarea ya cerrada que sale del plan se queda como está.
- **Ritmo y tope (R-30):**
  - la compilación inicial (el repo no tenía ningún issue del equipo con marcador) va a ≤ 1 escritura/s y está exenta del tope;
  - una recompilación lee antes la cuenta del equipo y escribe solo lo que cabe en 60 por hora. Dice cuánto queda pendiente, y la siguiente compilación sigue donde se quedó.

**Cuenta de escrituras del equipo** (`github.escrituras_del_equipo`): sale de lo que GitHub muestra a todos, no de cada clon, y la usan el relay y el compilador. En la última hora, sobre issues `hk-tarea` y de cuentas de la tabla:
- una creación cuenta 1, con las etiquetas que pone su autor (GitHub las fecha hasta ~2 s después; margen de 10 s);
- una edición de etiquetas o título (`labeled`, `unlabeled`, `renamed` del mismo actor e issue, dentro del margen) cuenta 1;
- cada `assigned`, `unassigned`, `closed`, `reopened`, `blocked_by_added` y `blocked_by_removed` cuenta 1 (`blocking_added` es la otra cara de la misma petición y no se cuenta);
- cada comentario cuenta 1;
- una edición del cuerpo no deja evento: un `updated_at` en la ventana sin otra escritura de ese issue dentro del margen cuenta 1.
- Crear una etiqueta en el repo no es una escritura sobre un issue y no se cuenta.

**Sondeo del relay:**
- Cada 30 s, con el `gh` de quien coordina y `If-None-Match` en cada consulta (un 304 no gasta cuota):
  1. `GET /issues?labels=hk-tarea&state=all&per_page=100`: definición y estado de las tareas;
  2. `GET /issues/events?per_page=100`: `assigned`, `closed`, `reopened` con su actor, que son las acciones del motor. Es la lista de todo el repo, que también trae el buzón: se filtra por número;
  3. `GET /issues/comments?sort=created&direction=desc&per_page=100`: solo para marcar los comentarios de fuera.
- **Dependencias nativas:** se piden las de un issue (`/issues/{n}/dependencies/blocked_by`) cuando su `total_blocked_by` no cuadra con lo último visto o con su línea, o cuando cambia su `updated_at`. Manda la nativa, con `dependencias_distintas`.
- **Backoff:** ante 403/429 de límite, `Retry-After` o `X-RateLimit-Reset`; sin respuesta, 30 s. Mientras dura, no pregunta.
- **Arranque:** la última instantánea, en `<git común>/hackathon/os/relay/github.json`, para arrancar sin GitHub.
- **Lo de fuera de la tabla no cambia ningún estado** (R-31):
  - un issue `hk-tarea` de fuera no define tareas;
  - una asignación, un cierre o una reapertura de fuera se ignoran;
  - un comentario de fuera solo se anota.
  Los tres salen como `fuera_del_equipo`, con autor, número y tarea, nunca con su texto.
- **Fuentes en `estado.json`:**
  - `fuentes.github` = estado del sondeo (`ok`, `limitado` o `sin respuesta`) y hora del último sondeo bueno;
  - `fuentes.git` = hora del último evento de fuente git;
  - `fuentes.relay` = hora del cálculo (no cuenta para la versión ni para el SSE).
  Marcar «viejo» en las vistas es de M8f.

