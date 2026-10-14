# ADR-0004 · Hooks que escriben ficheros; un demonio local que agrega

Estado: **aceptada** (2026-10-14, tras el Paso 0 de M8.0; hallazgos P2–P6 y P13 en `docs/coordinacion.md`).

## Contexto
Los hooks se ejecutan en cada llamada a herramienta de cada sesión y subagente. Tienen que ser baratos, portables (bash, sin `jq`) y no fallar sin red. Claude Code ofrece hooks `http`, pero la documentación no dice que su `url` admita variables (el puerto o la IP del relay cambian) ni que puedan ser `async`. Los procesos de monitor no reciben `CLAUDE_PLUGIN_OPTION_*` y solo existen en sesión interactiva.

Medido en M8.0 (Windows, Git Bash):
- Un emisor de una línea cuesta ≈110 ms por llamada con `tr`, `date` y `mkdir`, y ≈37 ms solo con builtins (bash vacío: 34 ms).
- En una sesión de 50 herramientas, el hook síncrono añade unos 7 s fuera del API y el `async`, nada.
- Las entradas de los hooks llevan contenido: `tool_input` de Write (`content`), de Edit (`old_string`/`new_string`), de Bash (el comando, con heredocs) y de Agent (el `prompt`); `tool_response` de Read y de Edit (el fichero entero), y `last_assistant_message`.
- Con `async`, el `SessionEnd` se pierde en `-p` (en interactivo llega).
- El hijo que lanza un monitor sobrevive al cierre de la sesión. El que lanza un hook con `nohup … &` muere al terminar el hook, antes de arrancar. El que se lanza con `Start-Process` de PowerShell sobrevive incluso a la salida de `-p`.

## Decisión
- **Emisión.** Los hooks del OS son `command` con `async: true`, salvo `SessionEnd`, que es síncrono (≈37 ms una vez por sesión). Cada hook añade **una línea** a `<git común>/hackathon/os/eventos/<session_id>.jsonl`. Sin red, sin `gh`.
- **Emisor solo con builtins de bash** (sin `tr`, `date` ni `mkdir` por llamada; la hora, con `TZ=UTC0 printf '%(…)T'`). Umbral de M8c: ≤ 50 ms por llamada en Windows y ≤ +1 s fuera del API en una sesión de 50 herramientas.
- **Lista blanca, no la entrada entera.** El emisor no guarda la entrada del hook: copia solo los campos de `api.md` §1, con el estilo de `valor()` de `scripts/orquestador/comun.sh`. Del comando de Bash, solo las operaciones git que interesan; del prompt de Agent, solo `ID:` y `Base:`; del mensaje final del revisor, solo `Veredicto:` y `Fusión:`. Ningún contenido de ficheros llega al JSONL.
- **Matchers.** `PreToolUse` y `PostToolUse` solo sobre `Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|Agent`; nunca sobre Read, Grep o Glob. Además: `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `Stop` y `PostToolBatch` (`arbol.sh`).
- **Un demonio local por persona y repo** (`hk-os agente`), Python con `uv run` (ADR-0005). Lee los JSONL, sondea git y habla con el relay.
- **Arranque: lo lanza `SessionStart`** (en `sesion.sh`, detrás del interruptor), en sesión interactiva y en `-p`. Si nadie escucha en su puerto, lo lanza desacoplado y vuelve al instante. En Windows, con `powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden …"`, porque `nohup … &` muere al acabar el hook. Unos 0,5 s, solo cuando no está vivo. En macOS y Linux, `nohup setsid … &` (por comprobar en M8d). El monitor no lanza el demonio: un solo mecanismo para los dos modos.
- **Respaldo:** si el demonio no arranca, los eventos esperan en disco y se envían cuando haya uno, porque el demonio lee desde su posición guardada.
- **Un solo demonio, con bloqueo propio: un puerto local.** El demonio escucha en `127.0.0.1:<puerto>`, con `puerto_agente:` de `os.md` o, si no está, `47100 + (cksum del git común) % 900`. Si el `bind` falla, ya hay otro y sale. Comprobar si vive es conectar al puerto (`/dev/tcp` en bash), no `kill -0` sobre un pid: P13 mostró que el pid de Git Bash y el de Windows no coinciden. El sistema operativo libera el puerto aunque el proceso muera mal.
- **Se apaga solo:** sale cuando lleva `apagado_min` (30 por defecto) sin eventos nuevos y sin ninguna sesión activa. Nadie lo para (P13: el `trap EXIT` del monitor no se ejecuta).
- El mismo código sirve el **MCP stdio** del plugin (`.mcp.json`, `hk-os mcp`), que solo lee el estado del demonio desde `estado-equipo.md` o `estado.json` locales.

## Alternativas descartadas
- **Hook `http` directo al relay**: depende de la red en cada llamada, URL fija y sin `async` documentado.
- **Hook que hace POST con `curl`**: red en cada llamada; en Windows, más lento.
- **Que el monitor actual haga de demonio**: está escrito en bash con `gh`; agregar, seguir ficheros y servir SSE en bash no es razonable.
- **Que el monitor lance el demonio**: funciona en interactivo (P13), pero en `-p` no hay monitores. `SessionStart` cubre los dos modos.
- **Guardar la entrada del hook sin parsear**: lleva código y crece con cada Edit de un fichero grande.
- **Bloqueo por fichero de pid y `kill -0`**: en Windows, el pid de Git Bash no es el del proceso nativo.

## Consecuencias
- Si el demonio no corre, no se pierde nada: los eventos esperan en disco.
- Hay que rotar o limitar los JSONL (por sesión, se borran al cerrar el relay o tras 48 h).
- Un demonio puede quedar vivo hasta `apagado_min` después de la última sesión. Es intencionado.
- Un programa ajeno, o el demonio de otro repo, podría ocupar el puerto. Por eso el arranque no se fía solo de que el puerto esté abierto: pide `GET /salud` y comprueba que responde `hk-os` con el mismo git común (`api.md` §4). Si responde otra cosa, no lanza nada y `SessionStart` lo avisa una vez por sesión («el puerto N está ocupado por otro programa; pon `puerto_agente:` en `.hackathon/os.md`»), sin volver a intentarlo en esa sesión (`api.md` §4).
