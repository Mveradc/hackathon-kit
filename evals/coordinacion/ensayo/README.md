# Ensayo con el equipo real (M8h, fase 2: K-83 y criterio 4)

**Qué se mide.** Si el Hackathon OS reduce las preguntas en voz alta («¿quién está con…?», «¿está en main?», «¿vamos a chocar?»), cuántas colisiones avisa antes de fusionar y cuántas se le escapan, y si algún estado sale mal sin explicación. **Criterio 4:** ningún estado incorrecto sin explicación, y menos preguntas en voz alta con el OS que en el control.

**Cómo.** El mismo equipo y el mismo reto en dos bloques: primero 60 minutos sin OS (control) y después al menos 3 horas con él. Las tasas se comparan por persona y hora. HackSpain sirve como referencia secundaria (pregunta 6 del cuestionario). Con 3–5 personas y fases distintas del reto, el resultado es una **tendencia, no una estadística**: el informe lo dirá así. Hay una variante sin control, el [ensayo realista](#ensayo-realista-sin-control), para hacerlo como sería en la hackathon.

## Qué hace falta
- **3–5 personas**, cada una con su portátil y su cuenta de GitHub, y lo de «El día antes» de [`docs/hackathon-os/arranque.md`](../../../docs/hackathon-os/arranque.md) hecho, con el kit instalado desde la versión que tenga la fase 1 de M8h (`main` tras su commit).
- **Un repo privado nuevo** para el ensayo, con todas las personas invitadas (no el sandbox de las pruebas ni el repo del kit).
- **Papeles:**
  - quien **coordina** (relay y `hk-os compilar`);
  - quien **observa** (puede ser la misma persona; rellena [`hoja.md`](hoja.md), impresa o en su portátil);
  - el resto programa: a cada una, [`persona.md`](persona.md) (una página con lo suyo, del día antes al cierre).
  Cada persona apunta sus propias preguntas en voz alta en la tabla 1 de la hoja, o se las dice a quien observa.
- **Reto 03** (`evals/retos/03-xray-embat-real.md`, solo en local: pasadlo por el chat del equipo). En el ensayo realista, también otro reto real (por ejemplo, el de un evento al que os vais a presentar; el previsto es el 07, GA2MODEL).

## El día
| Bloque | Duración | Qué se hace | Qué se apunta |
|---|---|---|---|
| 0 · Cadena del kit | 30–40 min | Quien coordina: `/hack-analyze`, `/hack-approaches` (el equipo elige), `/hack-scaffold` (con la coordinación activa: `coordinacion.md` con todas las personas), `equipo.md` y `/hack-plan`. Commit y push. Cada persona clona | Nada (no cuenta). Hora de fin |
| 1 · **Control** | 60 min | Trabajo normal con el kit como en la 0.3.2: buzón y orquestador sí, OS **apagado** (sin `os.md`, o con `activa: no`) | Tabla 1 (preguntas), tabla 3 (colisiones que salen) |
| Arranque del OS | ≤ 10 min | [`arranque.md`](../../../docs/hackathon-os/arranque.md), «Los 10 minutos», cronometrado | Cabecera: minutos y hora en que todos salen en la web. Desfases de reloj. Incidencias |
| 2 · **Con el OS** | ≥ 3 h | Trabajo normal. La web abierta en algún sitio visible (una pantalla o el portátil de quien observa). Si queréis probar el nivel 2, `publicar_wip: sí` en `os.md` (lee su aviso antes) | Todas las tablas |
| Cierre | 15 min | Cada persona: [`cuestionario.md`](cuestionario.md) y `hk-os recoger`; los zips, a quien analiza (por un canal privado, no al repo) | — |

Mientras dura el bloque 2, **no expliquéis el OS** a quien pregunta en voz alta: apuntad la pregunta y, si el OS ya lo decía, marcadlo en la última columna. Cerrad las sesiones de Claude Code como lo haríais normalmente (unas con `/exit`, otras cerrando la terminal): el ensayo mide también si se pierde el aviso de fin de sesión.

## Ensayo realista (sin control)
El día entero como sería en la hackathon: desde el enunciado, con el OS desde que hay plan y con las tareas de verdad, sin un bloque cortado a los 60 minutos. Sirve también de ensayo general de un evento al que el equipo se va a presentar. **El previsto:** 2–3 personas, cada una en su portátil, con el reto 07 (GA2MODEL, `evals/retos/07-ga2model-tecnicas-reunidas-real.md`, solo en local como el 03) y la **web nueva** (M9a).

**La web nueva.** Con `web_nueva: sí` en `.hackathon/os.md`, cada persona abre con `hk-os web` la web de **su** demonio (`docs/hackathon-os/contratos/api.md` §4, ADR-0010):
- cuatro vistas (cabina, que es la de entrada; red; tablero; servicios) y dos acciones, **Anotar** (una nota a `criterios.md` de `main`) y **Reclamar** (asignarse una tarea libre);
- solo funciona en el portátil de esa persona: el demonio escucha en `127.0.0.1` y el token va en el fragmento de la URL y después solo en la memoria de la pestaña. En otro dispositivo no carga, y al recargar se vuelve a abrir con `hk-os web`;
- la pantalla común (si la hay), con la web clásica del relay, de solo lectura, que se sirve siempre y es el respaldo;
- `.hackathon/servicios.md` lo genera `/hack-scaffold` con la coordinación activa (ADR-0011) y es lo que pinta la vista de servicios.

| Bloque | Duración | Qué se hace | Qué se apunta |
|---|---|---|---|
| 0 · Cadena del kit | 30–40 min, **cronometrado** | Como en el ensayo completo, desde el enunciado: `/hack-analyze`, `/hack-approaches` (el equipo elige), `/hack-scaffold` con la coordinación activa (deja también `servicios.md`), `equipo.md` y `/hack-plan`. Commit y push. Cada persona clona | Cabecera: de cuándo a cuándo (la promesa del kit es menos de 30 min) |
| Arranque del OS | ≤ 10 min, cronometrado | [`arranque.md`](../../../docs/hackathon-os/arranque.md), «Los 10 minutos», con dos cambios: en el minuto 0–2, el commit de `os.md` lleva también `web_nueva: sí` (antes de lanzar el relay, que lo lee al arrancar), y el `git pull` del 4–7 lo trae a cada clon antes de abrir la sesión (el demonio también lo lee al arrancar: sin él, hay que cerrarlo y volver a abrir); en el 9–10, cada persona abre **su** web con `hk-os web` en lugar de la del relay (lo de cada persona, en [`persona.md`](persona.md)). Quien coordina pone la web del relay en la pantalla común | Cabecera (también la hora a la que cada persona tiene su web abierta), desfases e incidencias |
| Con el OS | lo que dure el trabajo (≥ 2 h para que haya colisiones) | Trabajo normal, cada persona con su web. Las tareas se reclaman con Reclamar y se cierran en GitHub; lo que diga el jurado o un mentor, con Anotar. Las tablas 1–8, todas con «2» en la columna de bloque | Todas las tablas. La 7, lo que se sigue haciendo fuera de la web y qué botón habría hecho falta; la 8, si la vista de servicios cuadra con lo que hay |
| Cierre | 15 min | Igual que en el completo (el cuestionario trae las preguntas de la web nueva, 7–11) | — |

**Qué se pierde: la comparación con el control.** Sin el bloque 1 no se puede medir «menos preguntas con el OS que en el control» (criterio 4). Queda:
- las preguntas por persona y hora con el OS y la columna «¿Lo decía el OS?» de la tabla 1, que dice si la respuesta ya estaba en la web;
- la pregunta 6 del cuestionario (HackSpain), que pasa a ser la única referencia de antes;
- intacto, el resto del criterio 4: ningún estado incorrecto sin explicación.

Si M8h se cierra con este ensayo, el criterio 4 de `hitos.md` se reformula: lo decide el usuario.

**Con 2 personas** vale como ensayo reducido: las preguntas en voz alta, las colisiones entre dos, el arranque y las idas a la terminal sí se miden; el ruido del nivel 3 con un equipo grande, no. Lo que no necesita a otra persona (colisiones de cada nivel, un tercer o cuarto compañero, sesiones cerradas de formas raras, el modo sin GitHub) lo puede probar quien coordina con varios clones, como `interactivo.py`; sus resultados van aparte en `prueba.md`, no en la hoja.

**Con el reto de un evento real** al que os vais a presentar:
- lo que se haga en el ensayo es trabajo previo. Repo privado solo para el ensayo y, al acabar, un tag (`previo-ensayo`) que fije qué existía y cuándo;
- en el evento, repo nuevo y la cadena otra vez desde el principio; lo que se reutilice del ensayo se declara como digan las bases;
- los datos de la empresa suelen llegar en el evento: para el ensayo, datos de ejemplo públicos o inventados.

## Lo que el OS guarda solo
- **En el portátil de quien coordina** (`.git/hackathon/os/relay/`): `eventos.jsonl` (cada evento del equipo), `github.json` (la última foto de los issues) y el último `estado.json`.
- **En cada clon** (`.git/hackathon/os/`): los JSONL de sus sesiones, `agente.log`, `arranque.log` (cuánto tardó cada arranque), `entregado/*.firmas` (lo que se inyectó a cada sesión) y `wip.json`. Con la web nueva, además, `acciones.jsonl` (cada Reclamar), `servicios.json` (lo último que comprobó de sus servicios) y `entregado/accion-<id>` (la acción que ya entregó un monitor).

`hk-os recoger` lo junta todo en un zip **sin los tokens** (el del relay y el de la web) **ni el código**. Los zips llevan nombres de usuario: se guardan fuera del repo del kit (por ejemplo, en `../ensayo-m8h-datos/`).

## Análisis
```bash
uv run --no-project evals/coordinacion/ensayo/resumen.py --zips ../ensayo-m8h-datos/*.zip --informe ../ensayo-m8h-datos/resumen.md
```
- **Qué sale.** Línea de tiempo de cada tarea (estado y fuente de cada cambio; un reclamo de la web sale como `reclamada (web)`), colisiones (nivel, desde y hasta, personas y a quién avisó), discrepancias por tipo (`atribucion_ambigua`, `actividad_ajena`, `sin_tarea`…), sesiones sin fin, caracteres inyectados por sesión, desfase de relojes, coste del arranque y, con la web nueva, sus acciones por persona: eventos con fuente `web` del relay, líneas de `acciones.jsonl` (y cuántas no llegaron al relay; las entregas del monitor, solo si el zip trae `entregado/accion-<id>`, que hoy `hk-os recoger` no guarda por ser carpetas vacías) y notas de Anotar (commits «Criterio: <papel> · …» del log de git).
- **Anonimizado por defecto** (Persona A, B…, también en rutas y textos), porque va a `prueba.md`, que es público. `--sin-anonimizar` solo escribe fuera del repo del kit.
- **Lo que no sale de los datos:** las preguntas en voz alta, si un estado era incorrecto, las acciones que la web rechazó, lo que se siguió haciendo en la terminal y si la vista de servicios cuadraba. Eso sale de la hoja. Para cada estado incorrecto de la tabla 4, la línea de tiempo de `resumen.py` suele dar la explicación.

Resultados, en `evals/coordinacion/prueba.md` («M8h, fase 2»): la hoja (anonimizada), el recuento por persona y hora de cada bloque, y el resumen.
