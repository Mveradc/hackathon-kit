# Revisor C1–C6 · 02-facturas-real · línea base (rúbrica con grave/leve)

Salidas antiguas (`prueba-m3a`) revisadas con la rúbrica y el prompt nuevos, 2026-10-05. Comparación en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (grave) | `analisis.md`: «ERP local obligatorio como fuente». El enunciado no dice «obligatorio» y el dato pasa al CLAUDE.md con la etiqueta «(enunciado)». |
| C2 | Falla (leve) | `enfoques.md`: fila «Encaje con el perfil del jurado (inferido)», que no es un criterio de la rúbrica, y «créditos de LLM, que el reto no ofrece» |
| C3 | Falla (grave) | `CLAUDE.generado.md` regla 7: «El ERP es fuente obligatoria: se consulta siempre (enunciado)». La regla 11 da por hecha la ambigüedad 2. |
| C4 | Falla (grave) | `plan.md`: Persona E solo hace una «propuesta de bonus» y nadie implementa la mejora. No hay ninguna tarea para el cambio de un dato de la Caja el domingo. |
| C5 | Falla (grave) | `pitch.md`: «una mejora que Alberto usa fuera del flujo principal, ya implementada», sin ninguna tarea en el plan |
| C6 | Falla (leve) | `CLAUDE.generado.md` → Comandos: solo `uv run albertito`. Faltan `make erp` y el dueño del arranque. |

## Fallos encontrados

**Graves**

1. **Grave · C1, C3 · `analisis.md`, `CLAUDE.generado.md`**
   - `analisis.md` dice «ERP local obligatorio como fuente». El CLAUDE.md lo convierte en la regla 7: «El ERP es fuente obligatoria: se consulta siempre y se gestionan sus sesiones y reintentos (enunciado)».
   - El enunciado solo dice que recibís «un ERP local de 2009» y explica cómo arrancarlo. No lo declara obligatorio ni pide consultarlo siempre.
   - Es un requisito inventado y la etiqueta «(enunciado)» es falsa. Condiciona el diseño, porque obliga a llamar al ERP en cada factura con latencia artificial, y eso afecta a la escala, que vale 25 puntos y es el primer desempate.

2. **Grave · C3, C4, C5 · `CLAUDE.generado.md`, `plan.md`, `pitch.md`**
   - El CLAUDE.md, en la regla 11, dice «El lote 2 se procesa sin reprocesar el lote 1 … (análisis: riesgos; ambigüedad 2)».
   - El análisis dice «sin reprocesar **todo**», no «sin reprocesar el lote 1». La etiqueta no corresponde a lo que dice la fuente.
   - El enunciado pide «explicad qué decisiones debéis reprocesar». La ambigüedad 2, sobre si la regla nueva afecta al lote 1, se resuelve como un hecho y no como un supuesto.
   - La regla pasa al plan: Persona B tiene «Lote 2 sin reprocesar el lote 1» y el hito de las 23:30 calcula el impacto «registrado aparte». También pasa al pitch, en «sin reprocesar».
   - Además, el diseño se contradice: la regla nueva va en el prompt del decisor (tarea de Persona C), así que no se puede saber qué decisiones cambian sin volver a llamar al LLM.

3. **Grave · C4, C5 · `plan.md`, `pitch.md`**
   - El pitch dice: «una mejora que Alberto usa fuera del flujo principal, ya implementada», con «La mejora elegida el SÁB (propuesta de Persona E) funcionando».
   - En el plan, la única tarea es «propuesta de bonus en la demo mínima», dentro de un bloque que vence el SÁB 23:30, aunque la demo mínima era a las 11:00. Nadie la implementa.
   - El enunciado dice que en el bonus «no cuentan propuestas, maquetas…». El pitch promete algo que nadie construye y tampoco lo marca como `[SI DA TIEMPO]`.

4. **Grave · C4, C5 · `plan.md`, `pitch.md`**
   - El enunciado dice: «El domingo también podrá cambiar un dato de la Caja para comprobar la demo» y «DEBÉIS MOSTRAR: qué cambia, cómo seguís su impacto y cuáles son los límites del sistema».
   - El plan solo pregunta a la organización por la ambigüedad 3 (Persona A, SÁB 12:00). No hay ninguna tarea para recalcular ni para preparar ese cambio en directo.
   - El pitch no tiene ningún bloque para el cambio de la Caja ni para los «límites del sistema». El jurado puede pedirlo en directo y el equipo no estará preparado.

**Leves**

5. **Leve · C1 · `analisis.md`**
   - El análisis dice: «Quedar NO APTO por el formato: … ficheros de más en la raíz del repo».
   - El enunciado exige «exactamente» los tres ficheros, pero la validación solo mira «registro único por archivo · ambos lotes · resultado aceptado». Convierte un requisito en un motivo de eliminación que el enunciado no da.
   - No cambia lo que se construye.

6. **Leve · C1 · `analisis.md`**
   - Escribe «hace falta dar cifras **medidas** … separadas de las estimadas», cuando el enunciado dice «Medid o estimad». Se endurece lo que pide.

7. **Leve · C1, C2 · `analisis.md`, `enfoques.md`, `decision.md`**
   - El análisis dice «Jurado de Maisa (empresa de IA para operaciones) (inferido)». Eso es conocimiento externo y no una inferencia del enunciado, que no describe a Maisa.
   - En `enfoques.md` se convierte en una fila de puntuación («Encaje con el perfil del jurado») que no existe en la rúbrica. Se repite en «encaja con el perfil de Maisa» de `enfoques.md` y `decision.md`.

8. **Leve · C2 · `enfoques.md`, `decision.md`**
   - Dicen: «Depende de disponer de créditos de LLM, que el reto no ofrece».
   - El enunciado no dice nada sobre créditos. El análisis decía bien «No se mencionan», y aquí se presenta como un hecho negativo.

9. **Leve · C1, C3 · `analisis.md`, `reglas/convenciones.md`**
   - Escriben «El PDF vale 35 puntos». Según el enunciado, el PDF «se evalúa en» el criterio de 35 puntos, que también incluye la defensa, y su ausencia «puede dejar sin puntos» ese criterio. Es una imprecisión que no cambia el sentido.

10. **Leve · C1 · `analisis.md`**
    - Omite «Definid quién lo usa y qué trabajo le ahorra», que forma parte del bloque de Producto (35 puntos).
    - Añade «presencial» sin marcarlo como inferido.

11. **Leve · C3 · `reglas/salida-jsonl.md`**
    - «Escribir en UTF-8 explícito» es un consejo genérico, no algo propio de este reto.

12. **Leve · C3 · `CLAUDE.generado.md`**
    - Remite a «Guías de pasos: `.claude/skills/`», pero entre las salidas no hay ninguna guía. No se puede comprobar que cubran los momentos clave del reto: el lote 2, la entrega y la defensa.

13. **Leve · C4 · `plan.md`, `CLAUDE.generado.md`**
    - Faltan dueños para varias carpetas en las que se escribe:
      - la raíz y el arranque (`pyproject` y `uv run albertito`);
      - `.env.example`, que escribe Persona B en la raíz;
      - `datos/`, donde Persona D escribe `datos/revisadas.csv`;
      - `salida/`, donde escriben la cola, Persona C y Persona A;
      - `.hackathon/decision.md`, donde Persona D anota las respuestas.
    - La tabla de dueños solo cubre `src/albertito/` y `docs/`.

14. **Leve · C4 · `plan.md`**
    - Varias celdas agrupan varias tareas separadas por punto y coma, que es justo el fallo de ejemplo del criterio. Algunos casos:
      - Persona B, SÁB 18:00: «Ejecución completa…; entrega temprana; inyección de 429…».
      - Persona B, SÁB 03:00.
      - Persona D, SÁB 01:00.
      - Persona A, SÁB 23:30.
      - Persona E, SÁB 23:30.

15. **Leve · C4 · `plan.md`**
    - Las cifras de Persona A vencen el SÁB 18:00, que es también el límite de la ejecución completa del lote 1 de Persona B. Esa dependencia no tiene margen ni forma de desbloquearse.

16. **Leve · C4 · `plan.md`**
    - La ruta crítica (contratos, cola, cliente LLM y orquestador) recae en Persona B, cuyos puntos fuertes son «negocio, ciberseguridad».
    - Los agentes recaen en Persona C, que «prefiere no hacer backend».
    - La decisión pedía «una o dos con experiencia en LLM y agentes». La disponibilidad cuadra, pero el reparto encaja mal con los perfiles.

17. **Leve · C5 · `pitch.md`**
    - Asigna preguntas del jurado a Persona B y a Persona C, que según `equipo.md` no presentan. No está claro que vayan a estar en la defensa.

18. **Leve · C5 · `pitch.md`**
    - Dice «Estructura: la del reto (analisis.md, «Defensa»)», pero el análisis no tiene una sección «Defensa». Solo hay un punto dentro de «Qué hay que entregar». La estructura del pitch sí coincide con el enunciado (2 + 2 + 4 + 2 minutos).

## C6: justificación
Ayuda a arrancar rápido. Hay contratos en `schemas.py` a las 20:00, módulos repartidos por persona, un contrato JSONL claro y hitos de entrega escalonados. Así, en los primeros 30 minutos casi todos sabrían en qué fichero trabajar.

Echo en falta:
- **Comandos:** el CLAUDE.md no dice cómo arrancar el ERP (`make help`, `make erp`, `make erp-status`) ni remite a `MANUAL_ERP_2009.md`, y Persona A lo necesita desde el primer minuto.
- **Arranque sin dueño:** nadie se encarga de `pyproject` ni del entry point de `uv run albertito`, que es justo lo que pide la demo mínima.
- **Decisiones previas:** no está decidido el proveedor de LLM ni cómo se paga, y sin eso Persona C y Persona B no pueden empezar en serio.
- **Tareas sin dueño:** nadie implementa el bonus ni prepara el cambio de dato de la Caja del domingo.

Lo que obliga a deshacer:
- La regla 7 (ERP «obligatorio» y consultado siempre) y la regla 11 (no reprocesar el lote 1) pueden llevar a construir algo que luego haya que cambiar.
- La política «en la duda, ESCALAR», justo cuando la validación exige el resultado de la referencia, pone el APTO en riesgo más de lo que el texto reconoce.

Lo que sobra: la fila de «perfil del jurado» y el UTF-8 genérico.