<!--
Plantilla de .hackathon/servicios.md (solo con la coordinación activa). Es el mapa de lo que se pone en marcha y de
cómo se habla entre sí; lo pinta la vista de servicios de la web del Hackathon OS (M9a) y lo lee hkos/servicios.py
(formato en docs/hackathon-os/contratos/api.md §10). El OS nunca ejecuta «Arranque» ni «Prueba»: solo comprueba el
puerto y la salud de lo confirmado, y lee el resultado de la Prueba cuando alguien la corre.
- Un servicio por pieza que el plan pone en marcha o que guarda código propio (web, API, motor, almacén…). La Carpeta
  sale de la estructura que crea este comando. El Dueño, «—»: el reparto lo hace /hack-plan después, y manda
  .hackathon/autoridad.md (ponlo solo si .hackathon/equipo.md ya asigna esa carpeta a una persona con usuario de
  GitHub en coordinacion.md).
- Una conexión por cada bloque «<pieza> → <pieza>» de docs/contratos.md. «Contrato» es el título exacto del bloque.
- Puerto, Salud, Arranque y Prueba solo si salen del stack, del CLAUDE.md o del README que genera este comando; si no,
  «—». Nunca inventes un puerto ni un comando. Salud es una ruta que empieza por «/» (sin http:// ni host).
- «Fuera de servicios»: las carpetas y ficheros que no son de ninguna pieza (documentación, README, CLAUDE.md…).
- Las dos tablas de propuestas se dejan vacías: son para lo que un agente quiera añadir sin ser de su persona.
Quita estos comentarios al generar.
-->
# Servicios

Qué se pone en marcha, dónde vive, de quién es y cómo se habla entre sí. Un servicio lo confirma su dueño; una conexión, los dueños de sus dos extremos (`.hackathon/autoridad.md`). Si quieres cambiar algo que no es tuyo, escríbelo en Propuestas.

Fuera de servicios: <carpetas y ficheros que no son de ninguna pieza, separados por comas, p. ej. docs/, README.md, CLAUDE.md>

## Servicios
| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |
|---|---|---|---|---|---|
| <nombre corto en minúsculas> | <carpeta/> | <puerto o —> | `<comando de arranque>` o — | </ruta de salud> o — | — o @<usuario> |

## Conexiones
| De | A | Contrato | Prueba |
|---|---|---|---|
| <servicio que consume> | <servicio que produce> | <título exacto del bloque de docs/contratos.md> | `<comando que prueba el contrato>` o — |

## Propuestas de servicios
| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño | Autor | Hora |
|---|---|---|---|---|---|---|---|

## Propuestas de conexiones
| De | A | Contrato | Prueba | Autor | Hora |
|---|---|---|---|---|---|
