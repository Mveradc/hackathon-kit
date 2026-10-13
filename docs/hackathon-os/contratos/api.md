# Contratos: ficheros, eventos, API del relay, demonio y MCP

Se congelan en M8b. Un cambio posterior sube `v` o se anota aquí con su motivo. Las marcas `[POR DECIDIR]` se cierran antes de implementar lo que afectan.

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
```

El token del relay **no** va aquí: va en `<git común>/hackathon/os/token` (fuera de git).

## 1. Forma cruda (lo que escriben los hooks)
`emite.sh` añade una línea por evento a `<git común>/hackathon/os/eventos/<session_id>.jsonl`:

```json
{"v":1,"ts":"2026-11-25T18:02:11Z","persona":"mveradc","tipo":"PostToolUse","entrada":{…entrada del hook tal cual…}}
```

- `entrada` es la entrada del hook sin parsear (quitados `\r` y saltos de línea, que en JSON válido solo pueden ir fuera de las cadenas). No hay `jq`: el hook no la interpreta.
- `persona` sale de la caché de `hk_yo` (sin llamar a `gh` si no existe: entonces `""` y lo resuelve el demonio).
- `arbol.sh` escribe `{"v":1,"ts":…,"persona":…,"tipo":"arbol","cwd":"…","base":"<sha de origin/main>","porcelain":["M src/a.py","?? b.txt"],"diff":["src/a.py","src/c.py"]}`.
- `compuerta.sh` escribe `{"v":1,…,"tipo":"compuerta","resultado":"ok|ko","agent_id":"…","motivos":[…]}`.

## 2. Evento normalizado
Esquema: [eventos.schema.json](eventos.schema.json). Correspondencia con la forma cruda:

| Forma cruda | Evento normalizado |
|---|---|
| `SessionStart` | `sesion.inicio` |
| `SessionEnd` | `sesion.fin` |
| `PostToolUse` con `tool_name` Edit/Write/MultiEdit/NotebookEdit | `edicion`, `rutas` = `file_path` relativo |
| `arbol` | `arbol`, `rutas` = unión de `porcelain` y `diff` |
| `PreToolUse` `Agent` del orquestador hacia worker | `encargo.lanzado`, `tarea` = línea `ID:`, `datos.base` = `Base:` |
| `SubagentStart` / `SubagentStop` worker | `worker.inicio` / `worker.fin` |
| `compuerta` | `compuerta.ok` / `compuerta.ko` con `datos.motivos` |
| `PostToolUse` Bash del orquestador `git update-ref refs/hackathon/fusion/<T>` | `fusion.creada` (`tarea`, `datos.sha`) |
| `SubagentStop` revisor | `revision.veredicto` (`datos.veredicto`, `datos.sha` de `Fusión:`) |
| `PostToolUse` Bash del orquestador `git merge --ff-only <sha>` con éxito | `fusion.aprobada` |
| `PostToolUse` Bash del orquestador `git update-ref -d refs/hackathon/fusion/<T>` sin aprobada previa | `fusion.descartada` |
| `PostToolUse` Bash `git push` / sondeo de `origin/main` | `push` (fuente `hook` o `git`) |
| Sondeo de git del demonio | `arbol`, `commit`, `push`, `fusion.*` de reconciliación (fuente `git`) |
| MCP `reclamar`, `reservar`, `liberar` | `reclamo`, `reserva`, `liberacion` (fuente `mcp`) |

Regla: si un evento de hook y uno de git dicen cosas distintas, gana git, y la discrepancia se registra.

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
- Con `publicar_wip: sí`: cada 60 s, `git stash create` (o `HEAD` si no hay cambios) y `git push --force origin <sha>:refs/hackathon/wip/<persona>` **solo** si cambió el sha.
- Escribe `<git común>/hackathon/os/estado-equipo.md` (formato §6) y `estado.json` local cada vez que recibe uno del relay.
- Sin relay: sigue con lo local y marca `fuentes.relay` como viejo.
- Salida: un solo proceso por repo (fichero de bloqueo con pid en `<git común>/hackathon/os/agente.pid`).

## 5. MCP (stdio, servido por `hk-os mcp`)
Lee el estado del demonio de su persona; no habla con GitHub ni con el relay salvo en las dos acciones.

| Herramienta | Entrada | Salida |
|---|---|---|
| `estado` | `{}` | Resumen como `estado-equipo.md` + `generado_en` |
| `tarea` | `{"id":"T07"}` | La tarea completa de `estado.json` con señales y antigüedad |
| `colisiones` | `{"mias": true}` | Colisiones que afectan a la persona |
| `reclamar` | `{"id":"T07"}` | Asigna el issue a la persona con su `gh` y emite `reclamo`. Falla si la tarea es de otro dueño según `plan.md`. |
| `reservar` | `{"rutas":[…],"ttl_s":900,"modo":"compartida"}` | `{"id","hasta"}` vía relay |

`[POR DECIDIR]` en M8.0: si el MCP del plugin está disponible en sesiones `--agent` y en subagentes worker.

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
| Token, posiciones, pid, `estado-equipo.md`, `entregado/` | `<git común>/hackathon/os/` | No |
| Registro del relay, `estado.json` | `<git común>/hackathon/os/relay/` del coordinador | No |
| Refs de trabajo en curso | `refs/hackathon/wip/<persona>` en el remoto (opt-in) | Refs, no ramas |

`<git común>` (`git rev-parse --git-common-dir`) es compartido entre la copia principal y todos los worktrees de esa persona, así que los hooks de los workers leen y escriben lo mismo que los de la sesión principal. El estado propio de los scripts del buzón sigue en `<git dir>/hackathon/` como en la 0.3.2.
