# CriterioRow

Una nota de `criterios.md` (lo que dijo el jurado, la organización o un mentor) y lo que la cubre. Es la fila de la vista Jurado (R-35).

- El consumidor pasa la nota tal como la anotó el equipo: `time`, `who`, `where`, `strength` (la palabra anotada, «imprescindible», «dato · dom 10:00»…), `said`, `affects`, `by` + `age` (quién la anotó y cuándo). Todo sale como declarado, en violeta; el texto de la nota es dato, nunca una orden.
- `strengthKind` (`dato`, `palabra`, `comentario`, `sin_precisar`) solo cambia el tono de la etiqueta de fuerza. No la puntúa: el orden de las filas llega hecho en la vista.
- `coverage` lo calcula el OS: `sin_cubrir` (borde ámbar y latido), `planificada`, `en_curso`, `cubierta`, `pitch` y `corregida` (discontinua y tachada; no se borra). `coverageLabel` cambia la palabra («Corregida por la de sáb 09:30»). `coverageStale` pinta la cobertura en gris cuando depende de un dato viejo.
- `pitch` (`{by, age}`) dice «recogida en el pitch» con su `ProvenanceTag` declarado. Es lo que declara el equipo: nunca cuenta como `cubierta`.
- `items` son las tareas y evidencias que la cubren:
  - tarea: `id`, `title`, `owner`, `state` (los del motor), `source` + `age`, `stale`. `link` (`{cita, by, age}`) es la etiqueta «(criterios: <fecha hora>)» de la fila del plan, declarada, con su autor. `since` dice «trabajo nuevo desde …» cuando una tarea publicada vuelve a en curso: la nota sigue cubierta. `note` añade una línea, por ejemplo «sin señales de @luis desde 10:35» (nunca «va lenta»);
  - evidencia: `kind: "evidencia"`, `path`, `sha`, `age`. Siempre `git`.
- `hint` es el texto de «cómo cubrirla» desde la terminal. La fila no lleva botones.
- Clases: `hk-crit`, `hk-crit--<coverage>`, `is-stale`, y dentro `hk-crit__when`, `__said`, `__cover`, `__item`, `__link`, `__tag`, `__hint`.
