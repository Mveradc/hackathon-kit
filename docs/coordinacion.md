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

## Anexo: informe de investigación (11-10-2026)
[pegar el informe]