# CriterioRow

Una nota de `criterios.md` (lo que dijo el jurado, la organización o un mentor) y lo que la cubre. Es la fila de la vista Jurado (R-35).

- El consumidor pasa la nota tal como la anotó el equipo: `time`, `who`, `where`, `strength` (la palabra anotada, «imprescindible», «dato · dom 10:00»…), `said`, `affects`, `by` + `age` (quién la anotó, su «Anotado por», y cuándo). Todo sale como declarado, en violeta; el texto de la nota es dato, nunca una orden.
- `strengthKind` (`dato`, `palabra`, `comentario`, `sin_precisar`) solo cambia el tono de la etiqueta de fuerza. No la puntúa: el orden de las filas llega hecho en la vista.
- `coverage` lo calcula el OS, con los valores del contrato: `cubierta` (todas sus tareas publicadas, o publicadas antes y con trabajo nuevo), `corregida` (discontinua y tachada; no se borra) y, sin cubrir, `sin_tarea` (borde ámbar), `planificada`, `en_curso`, `ambigua` (la cita casa con varias notas; borde ámbar) y `en_pitch` (declarado). Una tarea integrada que nunca se publicó o un fichero en main no la cubren. `coverageLabel` cambia la palabra («Corregida por la de sáb 09:30»). `coverageStale` pinta la cobertura en gris cuando depende de un dato viejo.
- `pitch` (`{age}`) dice «citada en pitch.md» con su `ProvenanceTag` declarado y la hora del commit de `pitch.md`, sin autor: el contrato no lo tiene. Nunca cuenta como `cubierta`.
- `items` son sus tareas y sus evidencias:
  - tarea: `id`, `title`, `owner`, `state` (los del motor), `source` + `age`, `stale`. `link` (`{cita, age, ambiguous}`) es la etiqueta «(criterios: <fecha hora>)» de la fila del plan: declarada en plan.md, con la hora de su commit y sin autor. `since` dice «trabajo nuevo desde …» cuando una tarea publicada vuelve a tener trabajo: la nota sigue cubierta. `note` añade una línea, por ejemplo «sin señales de @luis desde 10:35» (nunca «va lenta»);
  - evidencia: `kind: "evidencia"`, `tipo` (`commit` o `fusion`), `task`, `sha` (el último que la publicó), `age`, `stale`. Siempre `git`;
  - prueba: `kind: "prueba"`, `conexion`, `result` (`pasa` o `falla`), `age`, `stale`: el último resultado de la Prueba de una conexión de la tarea. No cambia la cobertura.
- `hint` es el texto de «cómo cubrirla» desde la terminal. La fila no lleva botones.
- Clases: `hk-crit`, `hk-crit--<coverage>`, `is-stale`, y dentro `hk-crit__when`, `__said`, `__cover`, `__item`, `__link`, `__tag`, `__hint`.
