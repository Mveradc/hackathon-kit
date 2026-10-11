# Revisor C1–C6 · 02-facturas-real

Informe literal del revisor independiente (`claude -p` sin el plugin, 2026-10-05). Resumen y patrones en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla | `analisis.md`: «ERP local obligatorio como fuente», cuando el enunciado no dice que sea obligatorio y la frase no va marcada como inferida |
| C2 | Falla | `enfoques.md`: «Depende de disponer de créditos de LLM, que el reto no ofrece»; el enunciado no dice nada sobre créditos |
| C3 | Falla | `CLAUDE.generado.md` regla 7: «El ERP es fuente obligatoria… (enunciado)», y la regla 11, «sin reprocesar el lote 1», se atribuye a un riesgo del análisis que no dice eso |
| C4 | Falla | `plan.md`: «Cola persistente en `salida/`…; `llm.py`…; `writer.py`» (varias tareas en una celda); el bonus solo aparece como «propuesta» y no hay tarea para el teamId |
| C5 | Falla | `pitch.md`: «una mejora… ya implementada», pero el plan no tiene ninguna tarea que la implemente |
| C6 | Falla | `CLAUDE.generado.md` → Comandos: solo `uv run albertito`; faltan `make erp`, `make erp-status` y `make erp-login` |

## Fallos encontrados
1. **ESCALAR se trata como resultado seguro por defecto (C3, C4, C5).** `CLAUDE.generado.md`, regla 10: «En la duda, `ESCALAR` antes que adivinar… (ambigüedad 1)». Las reglas 2 y 9 hacen lo mismo, y también `salida-jsonl.md` («`ESCALAR` por defecto»), `agentes-y-proveedores.md`, los repliegues del `plan.md` («Lo no procesado sale como ESCALAR», «lo que falle, ESCALAR») y la respuesta de `pitch.md` («preferimos escalar a adivinar»).
   - **Qué dice el enunciado:** solo «resultado aceptado por la referencia privada». No dice que ESCALAR se acepte en caso de duda; eso es justo lo que pregunta la ambigüedad 1.
   - **Por qué importa:** la etiqueta cita una pregunta abierta como si fuera la respuesta. Si la referencia espera PAGAR o NO_PAGAR, este repliegue deja al equipo NO APTO y sin premio.
2. **Decide no reprocesar el lote 1 (C3, C4, C5).** `CLAUDE.generado.md`, regla 11: «El lote 2 se procesa sin reprocesar el lote 1… (análisis: riesgos; ambigüedad 2)». Se repite en `plan.md` («Lote 2 sin reprocesar el lote 1») y en `pitch.md` («el impacto del sábado va aparte»).
   - **Qué dice el enunciado:** «Integrad el cambio, conservad el trabajo y explicad qué decisiones debéis reprocesar».
   - **Qué dice la fuente citada:** el análisis habla de no reprocesar *todo*, no de dejar el lote 1 sin tocar. La etiqueta no corresponde a lo que dice la fuente.
   - **Por qué importa:** la ambigüedad 2 sigue abierta, pero el scaffolding la resuelve en la dirección más arriesgada. Si la regla nueva cambia resultados del lote 1, `outcomes.jsonl` queda mal.
3. **El bonus no se implementa (C4, C5).** `plan.md` solo prevé una «propuesta de bonus en la demo mínima» (Persona E, SÁB 23:30), y ningún bloque la construye. Aun así, `pitch.md` dice: «una mejora… ya implementada… funcionando».
   - **Qué dice el enunciado:** «No cuentan propuestas, maquetas». Además, la «Vista de escaladas» es parte del flujo principal (humano en el bucle), así que tampoco serviría como bonus.
   - **Por qué importa:** el pitch afirma un resultado que el plan no produce. Afecta al bonus (+10), que además es el tercer criterio de desempate.
4. **«ERP obligatorio» presentado como dato del enunciado (C1, C3).** `analisis.md` dice «ERP local obligatorio como fuente» y `CLAUDE.generado.md`, regla 7, lo repite con la etiqueta «(enunciado)».
   - **Qué dice el enunciado:** describe el ERP y explica cómo arrancarlo, pero no lo hace obligatorio.
   - **Por qué importa:** es una inferencia sin marcar con una etiqueta falsa, y obliga a consultar siempre un ERP lento.
5. **Las tareas no encajan con los perfiles del equipo (C4).**
   - Todo el núcleo backend (contratos, cola, LLM, orquestador, ejecuciones y entregas) recae en Persona B, cuyos puntos fuertes son «negocio, ciberseguridad». Además, «Todos esperan a Persona B».
   - Persona C, que «prefiere no hacer backend», lleva el extractor y el decisor.
   - Persona E, que es de frontend y prefiere no hacer backend, lleva `trace.py`.
   - La decisión pide «una o dos con experiencia en LLM y agentes» y nadie en `equipo.md` la tiene. El plan no menciona este hueco.
6. **Varias tareas en una sola celda (C4).** Es justo el fallo de ejemplo del criterio:
   - Persona B, SÁB 03:00, tres tareas.
   - Persona B, SÁB 18:00: «Ejecución completa…; entrega temprana; inyección de 429».
   - Persona D, SÁB 01:00, dos tareas.
   - Persona E, SÁB 23:30, dos tareas.
   - Persona A, DOM 11:00, dos tareas.
7. **Carpetas con varios dueños o sin dueño (C3, C4).**
   - En `salida/` escriben Persona B (la cola) y Persona C («Aciertos y ESCALAR por factura en `salida/`»), y no tiene dueño en la tabla.
   - `datos/revisadas.csv` lo escribe Persona D, que según el plan «escribe solo en `validator.py` y `docs/`».
   - `.env.example` y `decision.md` quedan fuera de las listas de ficheros de sus autores.
   - `src/albertito/` tiene cinco dueños a la vez, y nadie se encarga de crear el proyecto ejecutable (`uv run albertito`).
8. **No hay tarea para identificar al equipo (C4).**
   - **Qué dice el enunciado:** el paso 1 de la entrega es «Compartid el teamId y la URL pública de GitHub».
   - **Qué falta en el plan:** no hay ninguna tarea ni dueño para el teamId, ni para crear y compartir el repositorio de entrega.
   - **Por qué importa:** sin ese paso, la organización no puede clonar la entrega.
9. **Comandos incompletos y stack sin justificar (C3, C6).** La tabla de Comandos de `CLAUDE.generado.md` solo tiene `uv run albertito`.
   - **Qué falta:** `make help`, `make erp`, `make erp-status` y `make erp-login`, que son los comandos concretos que da el enunciado, más `MANUAL_ERP_2009.md` como referencia.
   - **Stack sin origen:** `uv` (es decir, Python) no sale ni del enunciado ni de `decision.md`.
   - **Guías de pasos:** `CLAUDE.generado.md` remite a «`.claude/skills/`», pero no se han entregado. No hay guía para momentos clave del reto: llegada del lote 2, preparación del repositorio de entrega y verificación de los JSONL.
10. **Al pitch le falta cubrir partes que el enunciado exige (C5).**
    - **Lote 2:** el enunciado pide mostrar «cuáles son los límites del sistema»; el pitch solo muestra una [CIFRA] de cambios.
    - **Escala y coste (25):** no incluye «cómo añadiríais nuevos tipos de archivo» ni «qué cambiaría con emails, imágenes o Excel»; solo aparece en una pregunta probable.
    - **Cambio en la Caja:** no prepara el cambio en directo de «un dato de la Caja» del domingo.
    - **Quién habla:** pone a Persona B y a Persona C a responder preguntas del tribunal, aunque `equipo.md` dice que no presentan.
11. **Créditos de LLM presentados como hecho (C2).** `enfoques.md` y `decision.md` dicen «créditos de LLM, que el reto no ofrece».
    - **Qué dice el enunciado:** nada; el análisis decía correctamente «No se mencionan».
    - **Por qué importa:** convierte una ausencia en una afirmación sin base.
12. **Exageraciones sobre el PDF y las mediciones (C1, C3).**
    - «El PDF vale 35 puntos» aparece en `analisis.md` y en `convenciones.md`. El enunciado dice que la falta del PDF «puede dejar sin puntos» el criterio de 35, que también se defiende en directo.
    - «hace falta dar cifras **medidas**» aparece en `analisis.md`. El enunciado dice «Medid o estimad».
13. **Un criterio fuera de la rúbrica sesga la elección (C2).** `enfoques.md` añade la fila «Encaje con el perfil del jurado (inferido)», basada en «Maisa (empresa de IA para operaciones)». Ese dato no está en el enunciado, y la fila no es un criterio de la rúbrica. Va marcado como inferido, pero empuja hacia B.
14. **Fallos menores (C1).**
    - «presencial» no está marcado como inferido.
    - El análisis dice «Defensa… (fecha/hora "Por confirmar")», pero la fecha (DOM 20) sí está confirmada; solo falta la hora.
    - Varios riesgos («Commit tardío», «ERP lento») no citan la parte del enunciado que los justifica.
    - `plan.md` da la defensa a las 11:00 (dato de `equipo.md`), mientras que `CLAUDE.generado.md` dice «por confirmar»: los dos ficheros generados no son coherentes.

## C6: justificación
Cada persona sabe qué ficheros le tocan y que el contrato será `schemas.py` a las 20:00. Las reglas de JSONL, de trazas y de resiliencia sí aterrizan en este reto.

Pero el arranque cojea:
- **Comandos:** falta el comando que lo arranca todo (`make erp`), y el stack (`uv`) aparece sin decisión previa y sin nadie que cree el proyecto.
- **Contrato:** los campos de los esquemas no están definidos, así que los primeros 45 minutos dependen de una persona sin perfil backend.
- **Cosas que habrá que deshacer:** probablemente la política de ESCALAR por defecto y la de no reprocesar el lote 1, si la organización responde en contra de lo que suponen.
- **Lo que echaría en falta:** un dueño para `salida/` y `datos/`, la tarea del teamId y del repositorio de entrega, la implementación real del bonus y guías para el SÁB 18:00 y para la entrega.
- **Lo que sobra:** las convenciones genéricas de commits e idioma, y la fila sobre el «perfil del jurado».