# Ensayo con el equipo real (M8h, fase 2: K-83 y criterio 4)

**Qué se mide.** Si el Hackathon OS reduce las preguntas en voz alta («¿quién está con…?», «¿está en main?», «¿vamos a chocar?»), cuántas colisiones avisa antes de fusionar y cuántas se le escapan, y si algún estado sale mal sin explicación. **Criterio 4:** ningún estado incorrecto sin explicación, y menos preguntas en voz alta con el OS que en el control.

**Cómo.** El mismo equipo y el mismo reto en dos bloques: primero 60 minutos sin OS (control) y después al menos 3 horas con él. Las tasas se comparan por persona y hora. HackSpain sirve como referencia secundaria (pregunta 6 del cuestionario). Con 3–5 personas y fases distintas del reto, el resultado es una **tendencia, no una estadística**: el informe lo dirá así.

## Qué hace falta
- **3–5 personas**, cada una con su portátil y su cuenta de GitHub, y lo de «El día antes» de [`docs/hackathon-os/arranque.md`](../../../docs/hackathon-os/arranque.md) hecho, con el kit instalado desde la versión que tenga la fase 1 de M8h (`main` tras su commit).
- **Un repo privado nuevo** para el ensayo, con todas las personas invitadas (no el sandbox de las pruebas ni el repo del kit).
- **Papeles:**
  - quien **coordina** (relay y `hk-os compilar`);
  - quien **observa** (puede ser la misma persona; rellena [`hoja.md`](hoja.md), impresa o en su portátil);
  - el resto programa.
  Cada persona apunta sus propias preguntas en voz alta en la tabla 1 de la hoja, o se las dice a quien observa.
- **Reto 03** (`evals/retos/03-xray-embat-real.md`, solo en local: pasadlo por el chat del equipo).

## El día
| Bloque | Duración | Qué se hace | Qué se apunta |
|---|---|---|---|
| 0 · Cadena del kit | 30–40 min | Quien coordina: `/hack-analyze`, `/hack-approaches` (el equipo elige), `/hack-scaffold` (con la coordinación activa: `coordinacion.md` con todas las personas), `equipo.md` y `/hack-plan`. Commit y push. Cada persona clona | Nada (no cuenta). Hora de fin |
| 1 · **Control** | 60 min | Trabajo normal con el kit como en la 0.3.2: buzón y orquestador sí, OS **apagado** (sin `os.md`, o con `activa: no`) | Tabla 1 (preguntas), tabla 3 (colisiones que salen) |
| Arranque del OS | ≤ 10 min | [`arranque.md`](../../../docs/hackathon-os/arranque.md), «Los 10 minutos», cronometrado | Cabecera: minutos y hora en que todos salen en la web. Desfases de reloj. Incidencias |
| 2 · **Con el OS** | ≥ 3 h | Trabajo normal. La web abierta en algún sitio visible (una pantalla o el portátil de quien observa). Si queréis probar el nivel 2, `publicar_wip: sí` en `os.md` (lee su aviso antes) | Todas las tablas |
| Cierre | 15 min | Cada persona: [`cuestionario.md`](cuestionario.md) y `hk-os recoger`; los zips, a quien analiza (por un canal privado, no al repo) | — |

Mientras dura el bloque 2, **no expliquéis el OS** a quien pregunta en voz alta: apuntad la pregunta y, si el OS ya lo decía, marcadlo en la última columna. Cerrad las sesiones de Claude Code como lo haríais normalmente (unas con `/exit`, otras cerrando la terminal): el ensayo mide también si se pierde el aviso de fin de sesión.

## Lo que el OS guarda solo
- **En el portátil de quien coordina** (`.git/hackathon/os/relay/`): `eventos.jsonl` (cada evento del equipo), `github.json` (la última foto de los issues) y el último `estado.json`.
- **En cada clon** (`.git/hackathon/os/`): los JSONL de sus sesiones, `agente.log`, `arranque.log` (cuánto tardó cada arranque), `entregado/*.firmas` (lo que se inyectó a cada sesión) y `wip.json`.

`hk-os recoger` lo junta todo en un zip **sin el token ni el código**. Los zips llevan nombres de usuario: se guardan fuera del repo del kit (por ejemplo, en `../ensayo-m8h-datos/`).

## Análisis
```bash
uv run --no-project evals/coordinacion/ensayo/resumen.py --zips ../ensayo-m8h-datos/*.zip --informe ../ensayo-m8h-datos/resumen.md
```
- **Qué sale.** Línea de tiempo de cada tarea (estado y fuente de cada cambio), colisiones (nivel, desde y hasta, personas y a quién avisó), discrepancias por tipo (`atribucion_ambigua`, `actividad_ajena`, `sin_tarea`…), sesiones sin fin, caracteres inyectados por sesión, desfase de relojes y coste del arranque.
- **Anonimizado por defecto** (Persona A, B…, también en rutas y textos), porque va a `prueba.md`, que es público. `--sin-anonimizar` solo escribe fuera del repo del kit.
- **Lo que no sale de los datos:** las preguntas en voz alta y si un estado era incorrecto. Eso sale de la hoja. Para cada estado incorrecto de la tabla 4, la línea de tiempo de `resumen.py` suele dar la explicación.

Resultados, en `evals/coordinacion/prueba.md` («M8h, fase 2»): la hoja (anonimizada), el recuento por persona y hora de cada bloque, y el resumen.
