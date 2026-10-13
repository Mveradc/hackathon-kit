# Changelog

## 0.3.2 — 2026-10-13

- `/hack-approaches` evalúa el encaje de cada enfoque con el equipo si existe `.hackathon/equipo.md`: quién cubre cada pieza, los huecos, las ausencias que chocan con una fase crítica y quién puede defenderlo, en unas 60 palabras por enfoque, más una fila en la tabla. El orden lo asegura: primero guarda los enfoques, sacados solo del reto, y después lee `equipo.md` y añade el encaje sin tocar lo ya escrito.

## 0.3.1 — 2026-10-13

- `/hack-scaffold` genera `.claude/settings.json` con `attribution` vacía: los commits y PR que haga Claude (también los workers y el orquestador) no llevan su coautoría. Si las bases piden declarar el uso de IA, no la quita y lo avisa. `/hack-analyze` recoge lo que digan las bases sobre el uso de IA, y `/hack-check` comprueba que la declaración que pidan tenga tarea con dueño (y avisa si `settings.json` oculta la atribución).
- Orquestador: el worker deja su informe completo en `<git común>/hackathon/informes/<rama>.md` y devuelve una sola línea; la compuerta lee ese fichero (solo dentro de esa carpeta). El orquestador lee solo su sección del plan y lo que necesita de los contratos. En una sesión de dos bloques, su contexto final baja de 68–74 k a 58 k.

## 0.3.0 — 2026-10-13

Orquestador por persona (experimental) y criterios del jurado.

- Nuevo agente `orquestador` (Opus), que se lanza con `claude --agent hackathon-kit:orquestador`: toma las tareas de una persona en `.hackathon/plan.md`, las parte en encargos y se los da a workers (Sonnet), como mucho dos a la vez y cada uno en su worktree. Él no edita código: un hook se lo impide.
- Un revisor independiente (Sonnet) revisa cada fusión en un worktree propio y vuelve a ejecutar la comprobación sin ver el informe del worker. La fusión se hace fuera de la rama de la persona y la rama solo avanza (en rápido) hasta una fusión aprobada; con CAMBIOS, se relanza una vez y, si vuelve a fallar, la tarea queda sin cerrar y la rama no ha cambiado.
- Una compuerta rechaza los informes de los workers sin evidencias (salida de la comprobación, commits, ficheros declarados, árbol limpio).
- El orquestador sube sus fusiones aprobadas (sin forzar), nunca commits de la persona.
- Reinicio en frío: si la sesión se corta, el orquestador retoma desde `.hackathon/estado/` sin repetir lo fusionado, vuelve a revisar la fusión pendiente y propone qué hacer con el trabajo huérfano sin borrarlo. Al terminar cada bloque, recomienda reiniciarlo, porque su contexto crece con cada encargo.
- La coordinación entre agentes y el orquestador se marcan como experimentales en el README: se han validado en un sandbox con una persona simulando al equipo, todavía no con un equipo real.
- Con la coordinación activa, un hook impide a cualquier agente publicar `hk confirmo` con `gh` (una red, no una garantía: ver limitaciones).
- Nuevo comando `/hack-note`: anota en `.hackathon/criterios.md` lo que dicen el jurado, los mentores o la organización durante el evento (quién, sus palabras y su fuerza). `/hack-pitch` lo recoge y `/hack-check` lo usa como fuente e informa de las notas sin recoger o que chocan con el enunciado.
- `/hack-decide` termina con el comando exacto de commit y push para compartir el acuerdo.
- Con la coordinación activa, cada nota de `/hack-note` se avisa a todo el equipo por un issue (`hk:para-todos`); el agente que la recibe se la cuenta a su persona, sin escribir en `criterios.md`. `buzon.sh ver` dice si quien abrió el issue está en la tabla del equipo.
- Validado con el reto 03: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md) (M6b y M7).

## 0.2.0 — 2026-10-11

Coordinación entre agentes, opcional.

- Nuevos comandos `/hack-ask`, `/hack-inbox` y `/hack-decide`: los agentes de cada persona se preguntan por GitHub Issues, con cabecera de saltos, escalado a las personas, deduplicación y backoff.
- Monitor de plugin que escucha el buzón sin coste de tokens mientras no hay novedades, y hook de inicio que reinyecta el estado propio y el buzón.
- `/hack-scaffold` pregunta si activarla (`.hackathon/coordinacion.md`, plantilla de issue, `.gitattributes`) y `/hack-plan` genera `.hackathon/autoridad.md`.
- Sin la coordinación activada, la cadena se comporta como en la 0.1.0.
- Validado con dos sesiones en dos worktrees de un repo sandbox y dos cuentas de GitHub: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md).

## 0.1.0 — 2026-10-10

Primera versión pública.

- Seis comandos: `/hack-analyze`, `/hack-approaches`, `/hack-scaffold`, `/hack-plan`, `/hack-pitch` y `/hack-check`, con el estado compartido en `.hackathon/`.
- Ejemplos de salida de dos retos reales en `skills/*/examples/`.
- Validado con seis retos (cinco reales y uno sintético) y una rúbrica de comprobaciones automáticas y de criterio (`evals/`).
- Limitaciones conocidas: [docs/limitaciones.md](docs/limitaciones.md).
