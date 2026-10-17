# Panel

Contenedor de cristal oscuro para cada bloque de la vista: tareas, colisiones, el grafo.

- Pon el título en `title` (sale en `label`, mayúsculas) y la cifra o la hora en `meta`.
- `tone="wait"` o `tone="fail"` hace latir el borde con `glow-wait` / `glow-fail`. Úsalo solo cuando algo del panel necesita acción o ha fallado, nunca para destacar.
- Un panel no anida otro panel.
