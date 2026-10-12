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
- M7: orquestador por persona con Opus 5.5, sin editar código (hook PreToolUse); workers Sonnet 5.5 en worktrees (máximo 2); revisor independiente que vuelve a ejecutar los tests; scout Haiku 5.5; modos construcción/iteración; reinicio en frío desde ficheros; compuerta SubagentStop sobre el resumen con evidencias.

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

## Anexo: informe de investigación (11-10-2026)
[pegar el informe]