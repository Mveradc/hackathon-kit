# ADR-0001 · Estado duradero en GitHub Issues, mismo repo, etiquetas `hk-tarea`

Estado: **aceptada** (2026-10-14, tras el Paso 0 de M8.0; hallazgos P7 y P8 en `docs/coordinacion.md`).

## Contexto
El estado duradero (tareas, dependencias, asignación, cierre) tiene que verlo todo el equipo sin depender de que alguien haga commit y push de `.hackathon/`. El kit ya usa GitHub Issues para el buzón (`labels=hk`, cabecera `<!-- hk … -->`), con `gh`, backoff y filtrado por la tabla de `coordinacion.md`. Los límites secundarios de GitHub (80 escrituras/min y 500/h por usuario) impiden poner ahí nada efímero.

## Decisión
- Cada tarea del plan es un issue en el **mismo repo** de la coordinación, con la etiqueta `hk-tarea`, `hk-tarea:<usuario>` para el dueño y un marcador oculto `<!-- hk-tarea id=T07 hash=<hash de la fila> -->`.
- **No** llevan la etiqueta `hk`: el monitor y `buzon.sh` consultan `labels=hk` y GitHub filtra por coincidencia exacta de etiqueta, así que el buzón no las ve (comprobado en M8.0, P7: un issue con `hk-tarea` y `hk:para-<usuario>` pero sin `hk` no sale ni en `buzon.sh leer` ni en la consulta del monitor).
- **Dependencias: la relación nativa es la fuente** (`gh issue create --blocked-by`, `gh issue edit --add-blocked-by`; comprobado con gh 2.101 en un repo personal privado, P8). «Lista» sale de la misma consulta de la lista de issues: `issue_dependencies_summary.blocked_by` cuenta solo los bloqueos **abiertos** (pasa a 0 al cerrar el bloqueante), así que no hace falta una petición por tarea. La consulta lleva `If-None-Match` con el ETag anterior: sin cambios, GitHub responde `304`.
- El compilador escribe además una línea `Depende de: T03, T05` en el cuerpo, como copia legible para personas y para el modo sin GitHub (M8h). Si las dos no coinciden, manda la nativa y la discrepancia se registra.
- `plan.md` sigue siendo lo que escriben las personas y `/hack-plan`. `hk-os compilar` lo lleva a issues de forma idempotente (crea lo que falta, actualiza lo que cambió por hash, nunca borra: una tarea quitada del plan se cierra con comentario). El **estado** de una tarea (asignación, cierre) vive en el issue; su **definición**, en `plan.md`.
- Escritura a GitHub solo para cambios duraderos: compilar, reclamar, cerrar, comentar fusión publicada. Tope de R-30: 60 escrituras/h para todo el equipo.

## Alternativas descartadas
- **Mismas etiquetas que el buzón**: el monitor trataría cada tarea como mensaje.
- **Repo separado de coordinación**: doble invitación y doble acceso para cada persona; solo tiene sentido si las bases exigen un repo de entrega limpio. Queda como opción de configuración (`repo_tareas:` en `os.md`), no como defecto.
- **Issue types y sub-issues**: los tipos solo existen en organizaciones; el kit funciona con repos personales.
- **plan.md como única fuente**: el estado solo viaja con commit y push; es justo el problema.
- **Ida y vuelta completa plan ↔ issues**: dos documentos editables a la vez. Fuera de la v1.

## Consecuencias
- Hace falta un ID estable por tarea (ADR-0002).
- El jurado verá issues `hk-tarea` si mira el repo: son legibles por personas (título = tarea, cuerpo = comprobación y dueño).
