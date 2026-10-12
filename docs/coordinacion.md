# Coordinación entre agentes del equipo (M6–M7)

## Decidido
- Problema: en HackSpain, las preguntas entre piezas iban Claude → persona → persona → Claude. Objetivo: que solo lleguen a humanos las decisiones de diseño, producto o pitch.
- Canal: GitHub Issues vía `gh`. Nada de agent teams, cross-session messaging, channels ni MCP compartido (no cruzan cuentas o son experimentales).
- Matriz de autoridad (autoridad.md) generada por /hack-plan, con tres niveles.
- Protocolo: etiquetas hk:para-<handle> y tipo; cabecera con id, salto y max_saltos; escalado a humanos tras dos intercambios sin acuerdo; quien pregunta no se bloquea y anota su suposición provisional en su fichero de estado; los acuerdos van a decisiones.md (append-only, con enlace al issue).
- Escucha: monitor de plugin sin plazo (`monitors/monitors.json`, arranca con la sesión) como vía principal; el script solo imprime cuando hay novedades (el silencio no cuesta tokens) y no termina nunca: un monitor que sale, aunque sea sin imprimir, genera un aviso y un turno del modelo (comprobado el 2026-10-11). Si la coordinación no está activa, duerme y la vuelve a mirar cada minuto. Paso 0 (plugin de juguete, Windows con Git Bash, 2026-10-11): el hook SessionStart y los monitores arrancan al iniciar y al reanudar (`--continue`, `source=resume`); corren en el directorio del proyecto; heredan el entorno de la sesión (`GH_TOKEN`), pero no `CLAUDE_PLUGIN_ROOT`, que se pasa como argumento; una línea impresa por el monitor abre un turno sin intervención; un fichero escrito con `echo >` de PowerShell 5.1 llega en UTF-16 (`��hola`), así que los scripts leen `.hackathon/` tolerando UTF-16 y BOM. Es experimental: si cambia o falla, el respaldo es la herramienta Monitor rearmada desde SessionStart, aceptando un turno cada ≤30 min. Hook SessionStart para reinyectar estado y buzón. asyncRewake descartado: crea un proceso por turno y se corta en el timeout. El criterio «30 min de silencio sin ningún turno» se mantiene.
- Hallazgos de la documentación (2026-10-11): el campo `when` de un monitor de plugin admite un solo disparador (`always`, por defecto, o `on-skill-invoke:<skill>`), así que arranca con la sesión; los monitores de plugin solo funcionan en sesión interactiva (nunca en `-p`) y no reciben `userConfig` (ni `${user_config.*}` ni `CLAUDE_PLUGIN_OPTION_*`); al desactivar el plugin a mitad de sesión no se paran. La herramienta Monitor tiene un plazo de 5 min por defecto y 30 como máximo, no se restaura al reanudar y en Windows necesita Git Bash. Los agentes de plugin ignoran `hooks`, `mcpServers`, `permissionMode` e `initialPrompt`: el PreToolUse del orquestador de M7 irá en `hooks/hooks.json` filtrando por `agent_type`.
- Confirmación del dueño: un comentario suyo, sin cabecera, cuyo cuerpo es exactamente `hk confirmo` (sin «/»: Git Bash convierte `/hk …` en una ruta de Windows al pasarlo a `gh`). Los scripts no publican esa marca.
- Estado por persona en ficheros propios, para evitar conflictos de merge.
- Coordinación opcional dentro del mismo plugin.
- M6b: criterios.md (solo lo escriben humanos; fuente, qué dijeron y a qué afecta) + /hack-note, que avisa a todos por issue; /hack-pitch y /hack-check comprueban la cobertura.
- M7: orquestador por persona con Opus 5.5, sin editar código (hook PreToolUse); workers Sonnet 5.5 en worktrees (máximo 2); revisor independiente que vuelve a ejecutar los tests; scout Haiku 5.5; modos construcción/iteración; reinicio en frío desde ficheros; compuerta SubagentStop sobre el resumen con evidencias. Concretado en «M7» (más abajo): sin modos.

- Hallazgos de la prueba de M6a (2026-10-11): en Windows, al cerrar una sesión, Claude Code mata el `bash -c` que lanzó el monitor pero no al monitor (queda huérfano), así que el script comprueba en cada vuelta que su padre vive; Claude Code genera por su cuenta un `away_summary` unos 3 min después del último turno, ajeno al plugin; los tokens fine-grained no llegan a repos personales de otra cuenta.

## Criterios de validación de M6a
- Una pregunta llega a la otra sesión en ≤ 3 min sin intervención humana; quien pregunta sigue trabajando.
- Una pregunta de implementación se resuelve entre agentes y queda en decisiones.md.
- Un cambio de contrato espera la confirmación del dueño desde su usuario.
- Un desacuerdo forzado escala en el tercer intercambio; un bucle provocado se corta en max_saltos.
- 30 min de silencio sin ningún turno del modelo.
- Matar la sesión y reanudarla recupera estado y buzón.
- Ante un 403/429 simulado, backoff sin inundar la conversación.
- Con la coordinación desactivada, la cadena 0.1.0 se comporta igual (repetir comprobar.py con un reto).
- En las pruebas, desactivar la mensajería nativa entre sesiones para que no falsee el resultado.

## M6b: criterios del jurado (decidido el 2026-10-12)
- Dos partes que se validan por separado: **M6b-1**, el registro y la cobertura, sin coordinación; **M6b-2**, el aviso por issue.
- `.hackathon/criterios.md`: solo se añade (`merge=union` en `.gitattributes`); cada nota con fecha y hora, quién lo dijo y su papel, dónde, qué dijo (literal o marcado como paráfrasis), fuerza (la palabra que usó, o `sin precisar`), a qué afecta y quién la anotó. Las notas se citan por su fecha y hora: `(criterios: <fecha hora>)`.
- `/hack-note`: solo lo lanza una persona (`disable-model-invocation`), así que el registro solo lo escriben humanos. Pregunta lo que falte, nunca sube la fuerza, no toca otros ficheros y da en una línea el comando de commit y push (no lo ejecuta). Funciona sin coordinación.
- `/hack-pitch` recoge las notas que le afectan; `/hack-check` las usa como fuente (después del enunciado) y añade la sección «Criterios del jurado»: dónde se recoge cada nota y si choca con el enunciado. Nadie elige entre una nota y el enunciado: lo decide el equipo.
- M6b-2: `buzon.sh avisar` abre un issue de tipo `nota` con la etiqueta `hk:para-todos`; el monitor lo trata como dirigido a todos menos a quien lo escribe; el agente que lo recibe solo avisa a su persona (con `git pull`), nunca escribe en `criterios.md`.
- Commit: `/hack-note` y `/hack-decide` terminan con el comando exacto de commit y push para que lo lance la persona.

## Criterios de validación de M6b-1
- Una nota completa queda en `criterios.md` con sus palabras y su fuerza tal cual; no se toca ningún otro fichero salvo `.gitattributes`.
- Sin papel de quien lo dijo, en `-p` no escribe nada y dice qué falta.
- Una fuerza débil («estaría bien») no sube a «se valora» ni a «obligatorio», ni en la nota ni en el pitch.
- Una nota que choca con el enunciado se señala en `/hack-note` y en `/hack-check`, sin cambiar ninguno de los dos.
- `/hack-pitch` recoge las notas que le afectan, con `(criterios: …)` y su misma fuerza.
- `/hack-check` informa de una nota anotada después del pitch como no recogida.
- Sin `criterios.md`, la cadena 0.2.0 se comporta igual (`comprobar.py` con un reto).
- Con un reto real de `evals/` (03).

## Criterios de validación de M6b-2
Sandbox de M6a (`../hk-sandbox`, sesión A como @Mveradc; `../hk-sandbox-B`, sesión B como @hk-persona-b).
1. Una nota de A con `/hack-note` llega a la sesión B en ≤ 3 min sin intervención; el monitor de A no le avisa de su propia nota.
2. B se la cuenta a su persona (quién, qué, fuerza, qué le afecta, `git pull`), sin escribir en `criterios.md` ni comentar en el issue.
3. El issue queda cerrado, con las etiquetas `hk:tipo-nota` y `hk:para-todos`, y `buzon.sh leer` no lo lista.
4. Una nota de alguien que no está en la tabla de `coordinacion.md` (simulado en B quitando a A de su tabla) no se presenta como del equipo.
5. Sin la coordinación activa, `/hack-note` no llama a `gh` ni lo menciona (prueba interactiva de M6b-1 en `../prueba-m6b-03`, sin `coordinacion.md`).

## M7: orquestador (decidido el 2026-10-12)
- Idea: Opus se encarga de las tareas que `plan.md` asigna a su persona, las parte en encargos y se los da a workers más baratos. Así gasta menos y no se llena de contexto. Sin «modos»: el orquestador hace siempre lo mismo y, si una tarea es pequeña, lanza un solo worker.
- Tres partes que se validan por separado con el reto 03: **M7a**, orquestador y workers; **M7b**, el revisor y la compuerta SubagentStop con evidencias; **M7c**, el scout (`haiku`), el reinicio en frío desde `.hackathon/`, el hook que impide a un agente publicar `hk confirmo` y la publicación de v0.3.0.
- Hallazgos de la documentación (2026-10-12): el orquestador es la sesión principal (`claude --agent hackathon-kit:orquestador`) y limita sus subagentes con `tools: Agent(worker)`; los hooks reciben `agent_type` en la sesión `--agent` y dentro de cada subagente; `isolation: worktree` crea la rama desde la rama por defecto, no desde HEAD; SubagentStop con exit 2 impide que el subagente pare (M7b, con tope de reintentos).

### M7a
- `agents/orquestador.md` (`model: opus`): lee `plan.md`, `equipo.md`, `docs/contratos.md` y `decisiones.md`/`criterios.md` si existen; pregunta a qué persona representa si no lo sabe; toma sus filas en orden y, para cada una, escribe encargos (objetivo, ficheros que puede tocar, contratos que aplican, comando que demuestra que está hecho). Como máximo dos workers a la vez y nunca dos sobre los mismos ficheros. No lee código entero: se guía por los resúmenes de los workers y por `git diff --stat`. Anota su avance en `.hackathon/estado/<persona>.md`.
- `agents/worker.md` (`model: sonnet`, `isolation: worktree`): hace un encargo, ejecuta el comando de comprobación, hace commit en su rama y devuelve un resumen con la rama, los ficheros tocados, los comandos ejecutados y su salida, y lo que no ha podido hacer.
- Antes de lanzar workers, el orquestador comprueba que el árbol está limpio y que lo que necesitan está en la rama por defecto; si no, para y se lo dice a su persona (no hace commit del trabajo de la persona). Hace `git pull` de la rama por defecto antes de lanzar workers y antes de cada fusión. Los worktrees de subagentes salen de la rama por defecto **del remoto** (`worktree.baseRef: "fresh"`; del HEAD local solo sin remoto), así que cada encargo lleva `Base: <sha del HEAD local>` y el worker empieza con `git merge --ff-only <Base>`: ve las fusiones sin subir sin push entre encargos (segunda pasada, 2026-10-12; descartados `worktree.baseRef: "head"`, ruta protegida y global, y pedir push antes de cada encargo dependiente). Al acabar un worker, fusiona su rama con `git merge --no-ff`; si hay conflicto, aborta la fusión y se lo cuenta a la persona. Tras una fusión correcta, elimina el worktree y la rama del worker (`git worktree remove`, `git branch -d`). El push lo hace la persona en M7a: el orquestador se lo indica al terminar (en M7b se decide si se automatiza).
- Cada encargo incluye el comando de preparación del entorno del worktree (dependencias) y declara los ficheros compartidos que toca (manifiestos, lockfiles, punto de entrada); si dos encargos comparten alguno, se lanzan en serie.
- Hook PreToolUse en `hooks/hooks.json` (`scripts/orquestador/solo-orquestar.sh`): si `agent_type` no es el orquestador, sale al instante. Si lo es, niega Edit/Write/NotebookEdit fuera de `.hackathon/` y, en Bash, las redirecciones a ficheros, `tee`, `sed -i`, `rm`, `mv`, `cp`, `git add`, `git commit`, `git stash`, `git apply`, `git checkout -- …`, `git restore`, `git reset --hard`, `git branch -D`, `git worktree remove --force` y `git push`. Deja `git pull`, `git merge`, `git merge --abort`, `git worktree remove`, `git branch -d`, `git status/diff/log`, los tests y `gh`. No es infranqueable: es una red bajo el prompt. Sin la herramienta PowerShell en su `tools` (y el hook la niega). El estado del orquestador (`.hackathon/estado/<persona>.md`) no cuenta como árbol sucio.
- Sin coordinación: funciona igual. Con la coordinación activa, el buzón queda para M7c (no se prueba en M7a).

### Criterios de validación de M7a
Carpeta nueva `../prueba-m7a-03`, con la cadena del reto 03 hasta `/hack-plan` y el scaffolding arrancando.
1. `claude --plugin-dir <ruta> --agent hackathon-kit:orquestador` toma las filas de una persona de `plan.md` y lanza workers Sonnet, cada uno en su worktree, nunca más de dos a la vez.
2. Cada worker devuelve el resumen pedido y su comando de comprobación pasa también después de fusionar en la rama por defecto.
3. Si se le pide al orquestador que corrija una línea de código, el hook lo niega (con Edit y con `echo >`/`sed -i` por Bash); en `.hackathon/` sí puede escribir; `git merge` funciona.
4. Con el árbol sucio, no lanza workers y lo dice.
5. Se anota el uso de contexto del orquestador (`/context`) al terminar un bloque del plan, para compararlo en M7b.
6. Sin `--agent`, el hook no hace nada (una sesión normal edita código sin avisos) y `claude plugin validate .` pasa.
7. Al terminar la prueba no quedan worktrees ni ramas de workers (`git worktree list`, `git branch`), y el orquestador ha indicado a la persona que haga push.

Se anota también cuánto tarda y cuesta por worker la preparación del entorno del worktree.

### M7b (decidido el 2026-10-12)
- **Compuerta** (`scripts/orquestador/compuerta.sh`, común con `solo-orquestar.sh` en `comun.sh`): los workers entregan su informe con la herramienta `SubagentHandback`, así que la compuerta principal es un PreToolUse sobre ella (`tool_input.message`); SubagentStop (`last_assistant_message`) es el respaldo para el worker que termina sin ella y respeta `stop_hook_active`. Solo actúa con `agent_type` worker. Exige las líneas del resumen y, con `Estado: hecho`, salida de la comprobación, commits por encima de `Base`, todos los ficheros del diff declarados y el worktree limpio. Rechaza con exit 2 y el motivo; tope de 2 rechazos por `agent_id` (contador en `$(git rev-parse --git-common-dir)/hackathon/compuerta/`); al tercero deja pasar y el orquestador no fusiona sin evidencias.
- **Revisor** (`agents/revisor.md`, Sonnet, `tools: Read, Grep, Glob, Bash`): revisa lo fusionado en un worktree propio (`git worktree add --detach .claude/worktrees/revision-<sha8> <fusión>`), prepara allí el entorno, lee el diff de la fusión, busca trampas, vuelve a ejecutar la comprobación y borra el worktree desde la copia de la persona (en Windows no se borra la carpeta en la que está la shell). No recibe el resumen del worker. Devuelve `Veredicto: APROBADO | CAMBIOS` con motivo y salidas. El hook `solo-orquestar.sh` se le aplica también: sin Edit/Write, redirecciones, commit, push, merge, checkout ni `worktree remove --force`.
- **Orquestador**: fusiona, anota los shas, lanza el revisor y limpia el worker. No ejecuta la comprobación en la copia de la persona ni instala nada en ella (lo hace el revisor en su worktree). Con CAMBIOS relanza el encargo una vez con el motivo; con un segundo CAMBIOS para, deja la tarea «no cerrada» con el sha de antes y el comando para deshacer (lo ejecuta la persona) y no recomienda push. `git status` muestra `?? .claude/worktrees/` mientras hay worktrees de workers o revisores: no cuenta como árbol sucio.
- **Push** (decidido con los datos de la pasada honesta, ver `evals/coordinacion/prueba.md`): lo hace el orquestador. Regla: el orquestador hace `git push` (sin `--force`) solo si todas las fusiones desde el último push están APROBADAS, `git pull --ff-only` pasa y todos los commits de `origin/main..main` son fusiones suyas anotadas o están en `<fusión>^1..<fusión>^2` (el autor no sirve: todos firman con el mismo usuario de git). Si hay un commit de la persona, se lo dice y no hace push. El hook le permite `git push` y le niega forzarlo o borrar ramas; al revisor, cualquier push.
- **SubagentStop**: Claude Code lanza agentes internos (sin transcript) cuyo SubagentStop llega con el `agent_type` del worker; la compuerta solo actúa si existe el transcript y su `.meta.json` dice `worker`.
- **Coste**: por tarea, tokens del worker y del revisor desde `subagents/agent-*.jsonl`, pasados a USD con los precios vigentes.

### Criterios de validación de M7b
Carpeta `../prueba-m7b-03`, copia de `../prueba-m7a-03` con remoto local nuevo y un segundo clon para «A».
1. Compuerta con entradas simuladas (`evals/coordinacion/prueba_hooks.py`): rechaza, con su motivo, informes sin salida de comprobación, rama sin commits, ficheros sin declarar o worktree sucio; al tercer intento deja pasar; con otro `agent_type` no hace nada.
2. Pasada honesta (B, bloque «Navegación»): el revisor crea su worktree en el sha de la fusión, prepara el entorno, ejecuta la comprobación, da APROBADO y borra el worktree, sin que la persona instale nada. Mientras revisa, B tiene un cambio sin commitear ajeno a la tarea: el revisor no lo ve ni lo toca, y sigue ahí al terminar.
3. El revisor no puede editar: el hook le niega Edit y las redirecciones, y le deja `git worktree add --detach` y `git worktree remove`.
4. Fallo inducido (copia del plugin en el scratchpad con un worker del mismo nombre que rompe la comprobación y dice que pasa): el revisor da CAMBIOS con motivo, el orquestador relanza una vez, el revisor vuelve a dar CAMBIOS, se avisa a la persona, la tarea queda «no cerrada» en `estado/B.md` y no se recomienda push.
5. Push: decisión anotada con los datos de la pasada 2. Si se adopta: con un commit de la persona por delante del remoto, el orquestador no hace push y lo dice; solo con fusiones suyas aprobadas, hace push tras el pull.
6. Coste: USD del revisor frente al del worker por tarea; contexto del orquestador al terminar el bloque frente a M7a (35–45 k).
7. Regresión: sin `--agent`, ningún hook hace nada; `claude plugin validate .` pasa.

## Anexo: informe de investigación (11-10-2026)
[pegar el informe]