# Contratos: ficheros, eventos, API del relay, demonio y MCP

Un contrato congelado solo cambia subiendo `v` o con una nota aquí con su motivo. Las marcas `[POR DECIDIR]` se cierran antes de implementar lo que afectan.

| Parte | Estado |
|---|---|
| §1, §2, [eventos.schema.json](eventos.schema.json), [estado.schema.json](estado.schema.json) | **Congelados** (M8b, 2026-10-14) |
| §3–§5 | Estables; se congelan al abrir M8d |
| §0 y §7 | Estables; se congelan al abrir M8c |
| §6 | Estable; se congela al abrir M8f |

Los estados de tarea son identificadores sin espacios (`en_curso`, `en_revision`, `no_cerrada`…); la web y el markdown muestran la etiqueta legible («en curso»).

## 0. Interruptor: `.hackathon/os.md`
Versionado, lo escribe una persona (o `hk-os iniciar`). Mismo estilo que `coordinacion.md`.

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

```json
{"v":1,"ts":"2026-11-25T18:02:11Z","persona":"mveradc","tipo":"PostToolUse","session_id":"…","agent_id":"a17759f71a1625d5c","agent_type":"hackathon-kit:worker","cwd":"C:\…\.claude\worktrees\agent-a17759f71a1625d5c","tool_name":"Edit","tool_use_id":"toolu_…","ruta":"C:\…\src\a.py"}
```

**Lista blanca** (ADR-0004): el emisor no guarda la entrada del hook, solo estos campos. Un campo que no viene se omite.

| Campo | De dónde | Cuándo |
|---|---|---|
| `v`, `ts`, `persona`, `tipo` | Sobre: `ts` en UTC (`TZ=UTC0 printf '%(…)T'`); `persona` de la caché de `hk_yo` (`""` si no existe: lo resuelve el demonio); `tipo` = `hook_event_name` | Siempre |
| `session_id`, `cwd` | Entrada | Siempre |
| `agent_id`, `agent_type` | Entrada | Si vienen (subagentes; `agent_type` también en sesiones `--agent`) |
| `source` | Entrada | `SessionStart` (`startup`, `resume`, `clear`, `compact`: la compactación reinicia el tope de R-25) |
| `tool_name`, `tool_use_id` | Entrada | Eventos de herramienta |
| `ruta` | `tool_input.file_path` o `tool_input.notebook_path` | Edit, Write, MultiEdit, NotebookEdit |
| `git` | `tool_input.command`, **solo** si contiene `git` seguido de `update-ref`, `merge --ff-only`, `push` o `commit` (también con `git -C <ruta>`); recortado a 200 caracteres | Bash y PowerShell |
| `subagent_type` | `tool_input.subagent_type` | PreToolUse y PostToolUse de `Agent` (worker o revisor) |
| `id`, `base` | Del `tool_input.prompt`, solo las líneas `ID: (T[0-9]{2,3})` y `Base: ([0-9a-f]{7,40})` | PreToolUse de `Agent` |
| `veredicto`, `fusion` | De `last_assistant_message`, solo `Veredicto: (APROBADO\|CAMBIOS)` y `Fusión: ([0-9a-f]{7,40})` (la «ó» puede venir como UTF-8 o como `\u00f3`) | `SubagentStop` con `agent_type` revisor |

Reglas del emisor:
- Solo builtins de bash, con el estilo de `valor()` de `scripts/orquestador/comun.sh` (regex sobre la entrada; una clave escrita dentro de una cadena va escapada, `\"clave\"`, y no coincide).
- Los valores de texto se copian **tal como vienen escapados** en la entrada, sin desescapar, así que la línea sigue siendo JSON válido sin volver a escaparla. Al recortar `git` a 200 caracteres, se quita del final cualquier secuencia de escape incompleta: una `\` suelta (un número impar de barras al final) o un `\u` seguido de menos de 4 dígitos hexadecimales.
- Las rutas van **absolutas y como vienen** (en Windows, con `\`). Las normaliza el demonio a relativas con `/` (con el `cwd` y `git rev-parse --show-toplevel`).
- Nada de `tool_response`, `content`, `old_string`, `new_string`, `prompt` ni `last_assistant_message` completos.

Otros productores de forma cruda:
- `arbol.sh` (`PostToolBatch`, `Stop`, `SubagentStop`) escribe `{"v":1,"ts":…,"persona":…,"tipo":"arbol","session_id":…,"agent_id":…,"cwd":"…","base":"<sha de origin/main>","porcelain":["M src/a.py","?? b.txt"],"diff":["src/a.py","src/c.py"]}`.
- `compuerta.sh` escribe `{"v":1,…,"tipo":"compuerta","resultado":"ok|ko","agent_id":"…","motivos":[…]}`.

## 2. Evento normalizado
Esquema: [eventos.schema.json](eventos.schema.json). Correspondencia con la forma cruda:

| Forma cruda | Evento normalizado |
|---|---|
| `SessionStart` | `sesion.inicio` |
| `SessionEnd` | `sesion.fin` |
| `PostToolUse` con `tool_name` Edit/Write/MultiEdit/NotebookEdit | `edicion`, `rutas` = `ruta`, relativa y con `/` |
| `arbol` | `arbol`, `rutas` = unión de `porcelain` y `diff` |
| `PreToolUse` `Agent` del orquestador con `subagent_type` worker | `encargo.lanzado`, `tarea` = `id`, `datos.base` = `base` |
| `SubagentStart` / `SubagentStop` worker | `worker.inicio` / `worker.fin`. `SubagentStart` no trae el prompt (P3): el demonio toma `ID:` y `Base:` de la primera línea del transcript del worker, `<dir de la sesión>/<session_id>/subagents/agent-<agent_id>.jsonl`, y no lee nada más de él. Es un formato interno de Claude Code: si cambia, la tarea del worker queda sin asignar hasta su `fusion.creada` |
| `compuerta` | `compuerta.ok` / `compuerta.ko` con `datos.motivos` |
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
| `POST /v1/eventos` | Lote de eventos normalizados (≤ 200). Idempotente por `id`. | `{"aceptados":n,"repetidos":m}` |
| `POST /v1/latido` | `{persona, actores:[{papel,sesion,agente,worktree,tarea,ficheros}]}`. Cada 15 s por demonio. | `204` |
| `GET /v1/estado` | Último `estado.json`. Admite `If-None-Match`. | `200` + `ETag`, o `304` |
| `GET /v1/stream` | SSE. Evento `estado` con el `estado.json` completo cuando cambia; `ping` cada 20 s. | `text/event-stream` |
| `POST /v1/reservas` | `{rutas, ttl_s, modo}` en nombre de `persona`/`actor`. | `{"id":…,"hasta":…}` |
| `DELETE /v1/reservas/{id}` | Libera. | `204` |
| `GET /` | Web de solo lectura (HTML estático que abre `/v1/stream`). El token va en el fragmento (`/#t=<token>`) y no se envía al servidor en la carga. | HTML |

Errores: `401` sin token; `400` con `{"error":…,"campo":…}` si un evento no valida; nunca `500` por un evento malo (se descarta y se registra).

TTL: actor sin latido en 90 s → `activo: false` (R-18). Reserva vencida → se borra.

## 4. Demonio local (`hk-os agente`)
- Sigue `<git común>/hackathon/os/eventos/*.jsonl` (posición por fichero en `<git común>/hackathon/os/posiciones.json`).
- Cada 15 s: `git worktree list --porcelain`; por worktree, `git status --porcelain` y `git diff --name-only <origin/main>...HEAD`; `git for-each-ref refs/hackathon/`; si hay `origin`, `git fetch --quiet` cada 60 s y `git merge-base --is-ancestor` de las fusiones aprobadas.
- Con `publicar_wip: sí`: cada 60 s, commit del árbol con un índice temporal (`GIT_INDEX_FILE`, `add -A`, exclusiones de ADR-0007, `write-tree`, `commit-tree -p HEAD`; `HEAD` si no hay cambios) y `git push --force origin <sha>:refs/hackathon/wip/<persona>` **solo** si cambió el sha.
- Escribe `<git común>/hackathon/os/estado-equipo.md` (formato §6) y `estado.json` local cada vez que recibe uno del relay.
- Sin relay: sigue con lo local y marca `fuentes.relay` como viejo.
- Lo lanza `SessionStart` (`sesion.sh`, detrás del interruptor) si nadie responde en su puerto, desacoplado de la sesión. En Windows, con `Start-Process` de PowerShell (ADR-0004). Siempre con `uv run --no-project` (ADR-0005).
- **Bloqueo: el puerto.** Escucha en `127.0.0.1:<puerto>` (`puerto_agente:` de `os.md`, o `47100 + (cksum del git común) % 900`). Si el `bind` falla, sale. `GET /salud` responde `hk-os <ruta del git común>` en texto plano, sin token (solo escucha en `127.0.0.1`); el arranque solo da por vivo un demonio que responde eso con su mismo git común.
- **Puerto ocupado por otro programa** (el puerto acepta conexiones, pero `/salud` no responde con nuestro git común): `SessionStart` no lanza el demonio y lo avisa **una vez**: «el puerto N está ocupado por otro programa; pon `puerto_agente:` en `.hackathon/os.md`». A la persona, con `systemMessage`; al modelo, en una línea factual. Anota `puerto_ocupado` en `entregado/<session_id>` para no volver a intentarlo ni a avisar en esa sesión. Los eventos siguen esperando en disco.
- **Apagado:** sale tras `apagado_min` sin eventos nuevos en los JSONL y sin ninguna sesión activa (sin `sesion.inicio` abierto por un `sesion.fin` o por el TTL de 90 s).

## 5. MCP (stdio, servido por `hk-os mcp`)
Lee el estado del demonio de su persona; no habla con GitHub ni con el relay salvo en las dos acciones.

| Herramienta | Entrada | Salida |
|---|---|---|
| `estado` | `{}` | Resumen como `estado-equipo.md` + `generado_en` |
| `tarea` | `{"id":"T07"}` | La tarea completa de `estado.json` con señales y antigüedad |
| `colisiones` | `{"mias": true}` | Colisiones que afectan a la persona |
| `reclamar` | `{"id":"T07"}` | Asigna el issue a la persona con su `gh` y emite `reclamo`. Falla si la tarea es de otro dueño según `plan.md`. |
| `reservar` | `{"rutas":[…],"ttl_s":900,"modo":"compartida"}` | `{"id","hasta"}` vía relay |

Disponibilidad (M8.0, P1): en sesiones normales, como herramientas diferidas. En `--agent hackathon-kit:orquestador`, porque su `tools:` nombra el servidor entero (`mcp__plugin_hackathon-kit_<servidor>`). El worker y el revisor no lo tienen (ADR-0006).

## 6. `estado-equipo.md` (lo que leen los hooks de inyección)
Generado. Secciones en este orden y con estos títulos, para que `sesion.sh` y `delta.sh` puedan recortar por sección sin parsear Markdown complejo:

```
<!-- hk-os v1 generado_en=… relay=ok|viejo github=ok|viejo -->
## Tu trabajo
- T07 «…» · en curso (hace 2 min · hook) · bloquea a T09
## Colisiones que te afectan
- ROJO · contrato «API de eventos» · src/api/eventos.py · @ana edita (hace 1 min · git)
## Novedades
- 18:40 · decisión #12 · «…» (@luis)
## Equipo
- @ana · T03 en curso · 2 workers · hace 30 s
- @luis · sin sesión desde 18:12
## Detalle
Ruta: <ruta absoluta de estado.json>
```

Cada línea, como mucho 160 caracteres. `sesion.sh` inyecta las secciones en orden hasta 2.500 caracteres (R-24). `delta.sh` compara un hash por sección.

## 7. Ficheros y dónde viven

| Fichero | Dónde | Versionado |
|---|---|---|
| `os.md` | `.hackathon/` | Sí |
| Eventos crudos | `<git común>/hackathon/os/eventos/` | No |
| Token, posiciones, `estado-equipo.md`, `entregado/` (hash y caracteres inyectados por sesión, R-25) | `<git común>/hackathon/os/` | No |
| Registro del relay, `estado.json` | `<git común>/hackathon/os/relay/` del coordinador | No |
| Refs de trabajo en curso | `refs/hackathon/wip/<persona>` en el remoto (opt-in) | Refs, no ramas |

`<git común>` (`git rev-parse --git-common-dir`) es compartido entre la copia principal y todos los worktrees de esa persona, así que los hooks de los workers leen y escriben lo mismo que los de la sesión principal. El estado propio de los scripts del buzón sigue en `<git dir>/hackathon/` como en la 0.3.2.
