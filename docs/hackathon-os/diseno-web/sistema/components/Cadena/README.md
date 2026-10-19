# Cadena

La cadena de tareas más larga hasta la entrega, en una línea de tiempo. Es el centro de la vista Ruta crítica (R-36).

- El consumidor pasa `rows` ya ordenadas y las posiciones ya calculadas por el OS, en la escala de `min`–`max` (en las pantallas, horas desde el inicio del evento). El componente solo las coloca: no suma, no estima y no mueve nada con el reloj.
- Solo tareas abiertas que cuentan para la entrega: lo hecho no está en la cadena, ni lo que empieza por «Si …» o lleva [SI DA TIEMPO].
- Cada fila: `id`, `title`, `owner`, `franja` (la del plan, ya formateada: «sáb 02:30 → 11:00 · con T07»), `from`–`to`, `est` (el tramo estimado que le queda a una tarea en curso), `deadline` (su «Hasta»), `note` y `kind`:
  - `curso` (cian), `prevista` (discontinua: es una estimación);
  - `plazo_pasado` (rojo): **un hecho**, su «Hasta» ya pasó y no está hecha. El rojo es solo para esto;
  - `no_llega` (ámbar): **una estimación**, acaba después de la entrega. Nunca en rojo;
  - `vieja` (gris discontinua): depende de un dato viejo o de alguien sin señales («sin señales de @luis desde 10:35»; nunca «va lenta»).
- `marks`: líneas verticales en todas las filas. `ahora` (cian), `entrega` (la de equipo.md, contra la que se mide el margen) y `hito` (la congelación y los demás hitos del plan, todos iguales y sin previsión).
- `end` es la fila «Fin previsto»: `from`–`to` es el rango (el fin con el ritmo más rápido y con el más lento medidos), `tone` (`ok`, `wait`, `idle`), `label` y `range` en texto. Nunca una sola hora: no hay centro. Sin estimación, no se pasa.
- `layout="cajas"`: sin barras. Cada tarea es una caja con su franja «declarado · plan», para cuando no hay ritmo real (menos de 3 tareas medidas por persona) y unas barras parecerían una previsión. Los `children` van debajo (en la pantalla, la suma de franjas en un recuadro violeta).
- La leyenda sale sola con lo que se usa; `legend={false}` la quita.
- Clases: `hk-chain`, `hk-chain--cajas`, y dentro `hk-chain__grid`, `__lane`, `__bar--<kind>`, `__deadline` (`is-past`), `__mark--<kind>`, `__range--<tone>`, `__legend`, `__box`.
