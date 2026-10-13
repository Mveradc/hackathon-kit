# Preguntas abiertas (Paso 0, M8.0)

Lo que la documentación no deja claro o no he podido comprobar. Se responde con un plugin de juguete (como el Paso 0 de M6a) antes de cerrar los ADR que dependen de ello. Cada respuesta va a `docs/coordinacion.md`, «Hallazgos M8.0», con fecha y cómo se comprobó.

| # | Pregunta | Afecta a | Cómo comprobarlo | Si la respuesta es «no» |
|---|---|---|---|---|
| P1 | ¿Una sesión `claude --agent hackathon-kit:orquestador` ve los servidores MCP del plugin? ¿Y sus subagentes worker? | ADR-0006, R-27 | Plugin de juguete con `.mcp.json` y un agente; listar herramientas en ambos | El orquestador consulta `estado-equipo.md` por Read; el MCP queda para sesiones normales |
| P2 | ¿Qué trae `tool_input` en PreToolUse de la herramienta `Agent`? (¿`prompt`, `subagent_type`?) | §6 del diseño, `encargo.lanzado` | Hook que vuelca su entrada | Usar `SubagentStart` + el estado del orquestador (`estado/<u>.orquestador.md`) para el ID |
| P3 | ¿Qué trae `SubagentStart` (y si incluye el prompt o el `cwd` del worktree)? | `worker.inicio` | Hook que vuelca su entrada | Tomar el worktree del primer evento de herramienta del worker |
| P4 | En un worker con `isolation: worktree`, ¿`cwd` de sus hooks es la raíz del worktree? | R-16, actores | Hook que vuelca `cwd` en un worker | Deducirlo de `file_path` de sus ediciones y de `git worktree list` |
| P5 | ¿Qué trae `PostToolBatch`? ¿Se dispara en subagentes? | `arbol.sh` | Hook que vuelca su entrada en sesión y en worker | Solo `Stop` y `SubagentStop` |
| P6 | ¿Cuánto cuesta un hook `command` con `async: true` en Windows con Git Bash? ¿Hay límite de hooks async concurrentes? ¿Qué pasa con ellos al cerrar la sesión? | Constitución X, M8c | Sesión de 50 herramientas con y sin el hook, cronometrada | Emitir solo en `PostToolBatch`/`Stop`, no en cada `PostToolUse` |
| P7 | ¿El filtro `labels=hk` de la API de GitHub excluye issues con `hk-tarea` pero sin `hk`? | ADR-0001, R-07 | Sandbox: crear uno y ejecutar `buzon.sh leer` y el monitor | Renombrar a `tarea-hk` o similar |
| P8 | ¿`gh issue create --blocked-by` / dependencias nativas en la versión de `gh` del equipo y en repos personales? | ADR-0001 | `gh --version` y prueba en el sandbox | Solo la línea `Depende de:` en el cuerpo |
| P9 | ¿`git stash create` deja intactos el árbol y el índice en Windows, también con ficheros sin seguimiento? (Por defecto no los incluye.) | ADR-0007, nivel 2 | Prueba con ficheros modificados, añadidos al índice y sin seguimiento; `git status` antes y después | Para no seguidos, árbol temporal con `GIT_INDEX_FILE` aparte |
| P10 | ¿Push forzado a `refs/hackathon/wip/*` permitido en un repo personal sin reglas? ¿Lo bloquea alguna protección por defecto? | ADR-0007 | Sandbox | Nivel 2 solo entre ramas ya subidas |
| P11 | ¿Git ≥ 2.38 en los portátiles del equipo (para `merge-tree --write-tree`)? | ADR-0007 | `git --version` (el entorno Linux de pruebas tiene 2.34) | El nivel 2 lo calcula solo el relay, que debe tener Git ≥ 2.38 |
| P12 | ¿Mergiraf se puede ejecutar sobre tres versiones de un fichero fuera de una fusión de git y devuelve si quedan conflictos? | R-34 | `mergiraf merge base izq der` con un caso | 2b queda fuera |
| P13 | ¿Puede un monitor de plugin lanzar un proceso hijo de larga duración (el demonio) sin que Claude Code lo considere terminado? | ADR-0004 | Monitor de juguete que lanza `sleep` en segundo plano y sigue | La persona arranca `hk-os agente` a mano (una línea en el guion de arranque) |
| P14 | ¿Qué runtime cumple el criterio de ADR-0005 en un Windows limpio? | ADR-0005 | Instalar y arrancar un servidor SSE de 50 líneas con cada opción | — |
| P15 | ¿SSE atraviesa Tailscale y la red de un evento (proxy, portal cautivo) sin cortes? ¿Hace falta `ping` cada 20 s? | ADR-0003 | Dos portátiles en una red pública con Tailscale, 30 min | Sondeo de `GET /v1/estado` con ETag cada 3 s |
| P16 | ¿`additionalContext` de `UserPromptSubmit` se acumula en el contexto en cada turno o solo el último? | R-25, coste | Sesión de 20 turnos con deltas; `/context` | Deltas solo cuando hay cambios rojos; el resto, por MCP bajo demanda |
