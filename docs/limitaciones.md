# Limitaciones conocidas

Salen de la validación de M4 con cinco retos reales (`evals/rubrica.md`, resultados en `evals/resultados/criterio.md`). Lo generado es un punto de partida: el equipo tiene que leerlo y decidir. El README resume las cuatro más importantes: trabajo previo prohibido, `/hack-check` y revisión humana, coherencia del plan tras el check y enunciados por URL.

- **Eventos que prohíben el trabajo previo.** Si las bases exigen que «el código, diseño y otras piezas de trabajo» se creen durante el evento, preparar el repositorio, el plan o el pitch antes puede descalificar al equipo. `/hack-scaffold` lo detecta en el análisis, avisa y solo genera si confirmas que el evento ya ha empezado. `/hack-check` comprueba que la fecha de generación caiga dentro del evento. Generar solo el contexto (CLAUDE.md, reglas) no lo resuelve: la norma incluye «otras piezas de trabajo». En esos eventos, lanza `/hack-scaffold`, `/hack-plan` y `/hack-pitch` al empezar.
- **Ejecuta siempre `/hack-check` al final.** Sin él, la cadena da por ciertas cosas que el enunciado no dice: inferencias, ambigüedades resueltas o datos de conocimiento propio. El check rebaja o quita lo que no tiene respaldo, comprueba las causas de descalificación y propone filas del plan. Aun así, no decide por el equipo: el calendario, el reparto, las ausencias y las preguntas a la organización hay que revisarlos y cerrarlos.
- **Coherencia del plan tras `/hack-check`.** Cuando el check añade filas al plan (por ejemplo, el plan B de una ausencia o una tarea para una condición de descalificación), no actualiza el resto: los descansos, las dependencias o los repliegues pueden seguir diciendo lo contrario. Después de aplicarlo, revisa que el plan sea coherente.
- **El resultado es «en parte».** En los cinco retos, un revisor independiente concluyó que el equipo empieza antes y mejor solo en parte. Lo que más se echa en falta:
  - contratos entre piezas internas sin todos sus campos (`docs/contratos.md` recoge bien la entrega y los datos);
  - choques de calendario que hay que resolver a mano;
  - un reparto que no siempre encaja con los perfiles de `equipo.md`.
- **Enfoques.** La tabla comparativa de `/hack-approaches` no siempre coincide con el texto de cada enfoque. Antes de elegir, lee el texto.
- **Pitch.** Algunas preguntas del jurado las responden personas que en `equipo.md` dicen que no presentan, y no todas atacan el punto débil del enfoque elegido. Repasa quién responde.
- **Estimaciones de horas.** Las horas de los enfoques y del plan son orientativas, no salen de ningún dato.
- **Fuerza de los requisitos.** El análisis a veces endurece detalles menores (un «preferible» que suena a obligatorio). `/hack-check` corrige lo que afecta a las reglas, el plan y el pitch, pero no toca el análisis.
- **Enunciados por URL.** Con una URL, el análisis trabaja sobre un resumen de la página, no sobre el texto literal. El comando avisa; pega el texto si puedes.
- **Elegir enfoque por chat.** Si eliges escribiendo en lugar de con el selector, guardar `decision.md` pide permiso (en una sesión interactiva) o falla (en `claude -p`).
- **Permisos en `.claude/`.** Claude Code pide permiso para escribir en `.claude/` (reglas y guías). `/hack-scaffold` avisa antes; elige permitirlo durante la sesión.
- **En `claude -p`**, los comandos que preguntan se paran sin sobrescribir, y `/hack-plan` devuelve la sección `## Dueños` en lugar de editar el CLAUDE.md.
- **Ficheros en UTF-16.** Si el directorio ya tiene ficheros en UTF-16 (por ejemplo, de `Out-File` de Windows PowerShell 5.1), al sobrescribirlos conservan esa codificación. La verificación del arranque lo detecta en los ficheros que usa; revisa el resto.
- **Firmware:** con un stack de hardware (por ejemplo, ESP32 con PlatformIO), `/hack-scaffold` solo verifica que el firmware compila. El hola mundo en la placa (serie, radio) no se puede comprobar sin el hardware conectado; el comando lo dice en el resumen y en el README del proyecto, y deja el modo de flasheo para hacerlo a mano.
- **Coordinación entre agentes (desde la v0.2.0, opcional).** Depende de los monitores de plugin, una funcionalidad experimental de Claude Code que puede cambiar, y no funciona en `claude -p`: solo en sesión interactiva.
- **Coste.** La cadena completa cuesta unos 4–5 USD por reto (4,7 USD en los retos 02 y 03 con la v0.1.0; `/hack-check` es el paso más caro, unos 1,5 USD).
