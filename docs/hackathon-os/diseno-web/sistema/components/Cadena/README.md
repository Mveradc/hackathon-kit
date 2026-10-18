# Cadena

La cadena de tareas más larga hasta la entrega, en una línea de tiempo. Es el centro de la vista Ruta crítica (R-36).

- El consumidor pasa `rows` ya ordenadas y las posiciones ya calculadas por el OS, en la escala de `min`–`max` (en las pantallas, horas desde el inicio del evento). El componente solo las coloca: no suma, no estima y no mueve nada con el reloj.
- Cada fila: `id`, `title`, `owner`, `franja` (la del plan, ya formateada: «sáb 02:30 → 11:00 · con T07»), `from`–`to`, `est` (el tramo estimado que le queda a una tarea en curso), `deadline` (su «Hasta»), `note` y `kind`:
  - `hecha` (verde, fina), `curso` (cian), `prevista` (discontinua: es una estimación);
  - `plazo_pasado` (rojo): **un hecho**, su «Hasta» ya pasó y no está hecha. El rojo es solo para esto;
  - `no_llega` (ámbar): **una estimación**, acaba después de la entrega. Nunca en rojo;
  - `vieja` (gris discontinua): depende de un dato viejo o de alguien sin señales («sin señales de @luis desde 10:35»; nunca «va lenta»).
- `marks`: líneas verticales en todas las filas. `ahora` (cian), `entrega` (contra lo que se mide el margen) y `hito` (la congelación y los demás hitos del plan, todos iguales).
- `end` es la fila «Fin previsto»: `from`–`to` es el rango, `at` el centro, `tone` (`ok`, `wait`, `idle`), `label` y `range` en texto. Sin estimación, no se pasa.
- `layout="cajas"`: sin barras. Cada tarea es una caja con su franja «declarado · plan», para cuando no hay ritmo real (menos de 3 tareas hechas por persona) y unas barras parecerían una previsión. Los `children` van debajo (en la pantalla, la suma de franjas en un recuadro violeta).
- La leyenda sale sola con lo que se usa; `legend={false}` la quita.
- Clases: `hk-chain`, `hk-chain--cajas`, y dentro `hk-chain__grid`, `__lane`, `__bar--<kind>`, `__deadline` (`is-past`), `__mark--<kind>`, `__range`, `__central--<tone>`, `__legend`, `__box`.
