# TaskCard

Una tarea del plan con su estado derivado, su dueño y su procedencia.

- El consumidor pasa `id`, `title`, `owner`, `state` (los del motor: pendiente, reclamada, en_curso, en_revision, integrada, publicada, cerrada, parada, no_cerrada, fallo), y `source` + `age`.
- `stale` cuando la fuente está vieja: la tarjeta pasa a discontinua y gris aunque el estado sea bueno.
- `declaredBy` + `source="declarado"` cuando el estado lo puso alguien a mano; se ve distinto de lo derivado.
- `action` lleva un `Button` (por ejemplo «Reclamar» en las pendientes sin dueño).
