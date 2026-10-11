Fuente: evals/retos/02-facturas-real.md

Ficheros comprobados: `analisis.md`, `decision.md`, `equipo.md`, `plan.md`, `pitch.md`, `CLAUDE.md`, `.claude/rules/*.md` (3), `.claude/skills/*/SKILL.md` (3) y `docs/contratos.md`. No falta ninguno.

**No se ha aplicado ningún cambio**: esta sesión no puede preguntar. `/hack-check aplicar` aplica los cambios de texto y toma el argumento como confirmación de los cambios de calendario y de las filas propuestas.

## Bloqueantes

| Qué | Dice el enunciado (cita) | Dice <fichero> | Qué hacer | ¿Aplicado? |
|---|---|---|---|---|
| Compartir el teamId y la URL del repo de entrega con la organización | «Compartid vuestro teamId y la URL de un repositorio público de GitHub separado de vuestra solución.» | `plan.md`: la única tarea con dueño es «URL y teamId en `.hackathon/equipo.md`» (E, SÁB 00:00), que los apunta pero no los envía. El envío solo aparece en el paso 5 de la guía `/entrega`, dentro del hito del DOM 10:00, y su «Cómo se comprueba» no lo incluye. `docs/contratos.md` y la guía `/entrega` tienen el canal como TODO | Fila propuesta en la tabla de E: `SÁB 13:00 · Entrega · Compartir el teamId y la URL del repo de entrega por el canal que indique la organización · La organización confirma que los ha recibido`. E está disponible a esa hora y coincide con la entrega temprana. Si la organización no ha dicho el canal (pregunta «teamId: ¿dónde se comunica?», VIE 21:00), E lo pregunta a los mentores del track | No (pendiente de confirmación) |

Resto de condiciones con consecuencia, revisadas y sin diferencias:

- **Validación APTO**, que hace falta para optar al premio: «Para ser aptos hace falta un registro único por cada archivo de ambos lotes, con un result aceptado por la referencia privada». Está igual en el análisis, la regla 1 del `CLAUDE.md`, `salida-y-reglas.md`, `contratos.md` y `/entrega`. Tareas: C (SÁB 12:00) y los hitos del SÁB 11:00, SÁB 23:30 y DOM 10:00.
- **Repo separado con exactamente tres ficheros, sin código, credenciales ni ejecutables**: sin diferencias. La tarea es de E (SÁB 00:00) y lo comprueban los hitos del SÁB 23:30 y del DOM 10:00.
- **Cierre**: «DOM 20 · 11:00, hora de Madrid». Es igual en todos los ficheros, y la entrega final del DOM 10:00 deja una hora de margen.
- **Equipo de 2 a 5 personas**: son 5. El enunciado no pide inscripción, documentos firmados ni asistencia obligatoria.
- **Ausencias**: C (SÁB 14:00–18:00) y D (hasta SÁB 10:00) no tienen nada exigido por el enunciado en esas franjas. La defensa (DOM, «Por confirmar») la presentan A, D y E, y los tres están el domingo.
- **Trabajo previo**: el enunciado no exige que el trabajo se cree durante el evento, así que no se aplica. Aviso: «Fechas» del `CLAUDE.md` no tiene fecha de generación, y `decision.md` es del 2026-10-10, posterior al evento (18–20 sep 2026).

## Afirmaciones

| Fichero | Afirmación (resumida) | Veredicto | Cita literal | Fuente de la cita |
|---|---|---|---|---|
| CLAUDE.md | Qué puntúa: APTO, registro único por archivo, ambos lotes; no suma ni desempata; sin APTO no hay premio | Sostenida | «Si no sois aptos, podéis defender el proyecto y recibir feedback, pero no optar al premio.» | enunciado |
| CLAUDE.md | Producto (35) se evalúa sobre `albertitos_plan.pdf` (Arquitectura + 2–5 ADRs) | Sostenida | «El PDF se evalúa en Producto, arquitectura y ADRs; no forma parte de esta validación.» | enunciado |
| CLAUDE.md | Escalabilidad y coste (25): capacidad, hardware, límites, fórmula de coste y plan para más volumen; primer desempate | Sostenida, aunque omite «nuevos tipos de archivo» (ver cobertura) | «Desempates: primero escalabilidad y coste; después resiliencia; después el bonus de mejora adicional; finalmente, decisión motivada del tribunal.» | enunciado |
| CLAUDE.md | Trazabilidad (20), Resiliencia ante fallos del LLM (10), Calidad (10) «clara, proporcionada y agradable de operar» | Sostenida | «Una solución clara, proporcionada y agradable de operar, con decisiones útiles para Alberto.» | enunciado |
| CLAUDE.md | Bonus +10: mejora original implementada y mostrada; no cuentan maquetas ni el lote del sábado; el tamaño no puntúa | Sostenida | «No cuentan propuestas, maquetas, cambios cosméticos ni partes necesarias del flujo principal.» | enunciado |
| CLAUDE.md | Comandos: `make erp`; `make erp-fast` sin latencia, solo para tests; escucha en `http://127.0.0.1:8009` | Sostenida | «make erp-fast elimina la latencia artificial para tests locales.» | enunciado |
| CLAUDE.md | Regla 1: una línea por PDF, `file_id` exacto, tres valores de `result` | Sostenida | «result debe ser PAGAR, NO_PAGAR o ESCALAR.» | enunciado |
| CLAUDE.md, convenciones.md (viñeta 5), contratos.md (repo) | Regla 2 y equivalentes: repo público separado, raíz con exactamente 3 ficheros, sin código, credenciales ni ejecutables | Sostenida | «Su raíz debe contener exactamente los dos JSONL y albertitos_plan.pdf.» | enunciado |
| CLAUDE.md, salida-y-reglas.md, fuentes-externas.md, contratos.md (estado) | Reglas 3–7 y viñetas «(decisión)»: el LLM solo extrae, decide el motor de reglas, etapas idempotentes, estado por factura y etapa, caché por hash y versión, degradar o `pendiente`, ERP con sesión única, reintentos y concurrencia limitada, reglas como código versionado, `explain`, reprocesar solo lo afectado | Sostenida | «Almacén de estado local con una fila por factura y etapa, caché por hash de documento y versión de reglas.» | decision.md |
| CLAUDE.md | Regla 8: separar mediciones de estimaciones; latencia con `make erp`, no con `erp-fast` | Sostenida | «Separad mediciones de estimaciones» y «make erp-fast elimina la latencia artificial para tests locales.» | enunciado |
| CLAUDE.md | Reglas 9, 13 y 14: etiqueta `(análisis: riesgo típico)` | Sostenida, pero la etiqueta tiene un formato no válido: pasa a `(riesgo típico)` | — (el análisis las marca como «(riesgo típico)» en «Riesgos y trampas») | analisis.md |
| CLAUDE.md, salida-y-reglas.md | Reglas 10 y 11 y viñetas 15–16: ilegible → ESCALAR; Excel frente a ERP → ESCALAR | Supuesto (ya bien marcado) | «¿Qué pasa con archivos ilegibles o corruptos?» / «¿El ERP es la fuente de verdad si contradice el Excel?» | analisis.md |
| CLAUDE.md | Regla 12: la regla nueva sube la versión y `outcomes.jsonl` se conserva | Supuesto (ya bien marcado) | «¿Hay que reprocesar también el lote 1 con la regla nueva, o `outcomes.jsonl` se queda con las reglas originales?» | analisis.md |
| CLAUDE.md | Fuera de alcance: interfaz gráfica, agentes autónomos y chat | Sostenida | «Qué se deja fuera: interfaz gráfica, agentes autónomos, chat con Alberto.» | decision.md |
| CLAUDE.md | Fechas: VIE 19:00 inicio y materiales; SÁB 18:00 zip con hashes; DOM cambio de dato sin hora; DOM 11:00 cierre; defensa «Por confirmar» | Sostenida | «El sábado a las 18:00 se publica lote-2-sorpresa-v3.2.zip.» | enunciado |
| convenciones.md | Viñetas 1–4 `(convención del kit)` | Sostenida (etiqueta permitida en este fichero) | — | — |
| convenciones.md | Viñetas 6 (UTF-8) y 7 (sin `make`, bash ni `&`): etiqueta `(análisis: riesgo típico)` | Sostenida, pero el formato de la etiqueta pasa a `(riesgo típico)` | — (riesgos típicos de «Codificación y tildes» y «Herramientas que no funcionan en todos los sistemas») | analisis.md |
| fuentes-externas.md | Viñetas 2 (inyección) y 8 (fechas): etiqueta `(análisis: riesgo típico)` | Sostenida, pero el formato de la etiqueta pasa a `(riesgo típico)` | — | analisis.md |
| fuentes-externas.md | Viñeta 6: cada llamada registra latencia, intentos y error para la fórmula de coste | Sostenida | «Seguid una decisión real y mostrad estado, evidencia, versiones, latencia, errores, reintentos y trabajo pendiente.» | enunciado |
| fuentes-externas.md | Viñeta 7: `erp-fast` solo para tests y no se presenta como capacidad real | Sostenida | «make erp-fast elimina la latencia artificial para tests locales.» | enunciado |
| salida-y-reglas.md | Viñetas 2 y 3: `file_id` tal cual; nº de líneas = nº de PDF y sin repetidos | Sostenida | «Un registro único por archivo · ambos lotes · resultado aceptado.» | enunciado |
| ensayo-defensa | Defensa de 10 min en 2 + 2 + 4 + 2, hora por confirmar, rúbrica 100 + 10, primer desempate | Sostenida | «Trazabilidad, escala y coste · 4 min.» | enunciado |
| ensayo-defensa | «ERP arrancado con `make erp` (latencia real)» | Quitar «latencia real», que contradice la fuente: es latencia artificial. Propuesta: «(con su latencia artificial)» | «make erp-fast elimina la latencia artificial para tests locales.» | enunciado |
| ensayo-defensa | El bonus se enseña en un paso 6, aparte | Diferencia con la fuente (solo se informa): el enunciado lo coloca en el bloque de demo | «Si optáis al bonus, enseñad también la mejora adicional implementada.» (dentro de «Demo y contexto · 2 min») | enunciado |
| entrega | Cierre DOM 11:00 Madrid, clonado y commit; APTO y 35 puntos del PDF en juego; 3 ficheros exactos; repo público | Sostenida | «La organización clonará el repositorio y registrará el commit a esa hora.» | enunciado |
| entrega | Contenido del PDF: Arquitectura (componentes, flujo, reparto, trazabilidad, recuperación) + 2–5 ADRs con 5 apartados | Sostenida | «ADRs / trade-offs: de 2 a 5 decisiones con contexto, alternativas consideradas, decisión, consecuencias aceptadas y evidencia.» | enunciado |
| lote-2 | +40 facturas, ERP actualizado, regla nueva, conservar el trabajo, unas 17 h hasta el cierre, se evalúan arquitectura, observabilidad y recuperación | Sostenida | «No se puntúa un conteo de aciertos: se evalúan arquitectura, observabilidad y recuperación.» | enunciado |
| lote-2 | El zip trae `erp_export_lote2`, `pedidos_nuevos.csv`, `proveedores_nuevos.csv` y 40 facturas; comprobar el hash | Sostenida (el enunciado también habla de un `pull` del repo: ambigüedad 8, ya preguntada) | «En él encontraréis los CSVs erp_export_lote2, pedidos_nuevos.csv y proveedores_nuevos.csv, además de 40 nuevas facturitas.» | enunciado |
| lote-2 | «incluidos los ilegibles (el «café»)»: da por hecho que el lote 2 trae archivos ilegibles | Supuesto. Propuesta: «incluidos los ilegibles, si los hay (supuesto: ambigüedad 4, confirmar con la organización)» | — (el enunciado solo dice «te ha parecido escuchar que se ha caído un café por ahí...») | — |
| contratos.md | JSONL: un objeto por línea; `file_id`, `result` y campos de traza opcionales; solo se validan `file_id` y `result` | Sostenida | «Incluid un objeto por factura; los campos de traza son opcionales.» | enunciado |
| contratos.md | Repo: teamId y URL obligatorios; código, credenciales y ejecutables prohibidos | Sostenida | «No subáis vuestra solución, código, credenciales ni una aplicación ejecutable.» | enunciado |
| contratos.md | Datos de entrada: 500 PDF (algunos escaneados) + 40; ERP en `127.0.0.1:8009` con sesiones, reintentos y latencia artificial; CSV del lote 2 | Sostenida | «Recibís 500 facturas PDF —algunas escaneadas—, un Excel de proveedores, pedidos y normas de pago, y un ERP local de 2009.» | enunciado |
| contratos.md | Tipo del Excel: `xlsx` (origen: enunciado) | Supuesto. Propuesta: «xlsx (supuesto: el enunciado solo dice «un Excel», confirmar al recibirlo)» | — | — |
| contratos.md | Estado: `latencia_ms` «medida, no estimada» (enunciado) | Sostenida | «Separad mediciones de estimaciones» | enunciado |
| plan.md | 40 h de VIE 19:00 a DOM 11:00, hora de Madrid; defensa por confirmar; lote 2 el SÁB 18:00 con hash | Sostenida | «Todos los horarios son de Madrid.» | enunciado |
| plan.md | Tareas que dan por existentes 500 PDF + Excel (B, VIE 20:00) y 40 facturas + CSV (B, SÁB 21:00) | Sostenida | «además de 40 nuevas facturitas» | enunciado |
| plan.md | ADR «Cinco apartados con evidencia»; tres ADRs | Sostenida (3 está entre 2 y 5) | «con entre 2 y 5 decisiones relevantes» | enunciado |
| plan.md | Preguntas a la organización 1–8 y teamId | Sostenida (coinciden con las ambigüedades) | «Compartid vuestro teamId» | enunciado |
| pitch.md | Cabecera: 10 min, estructura 2 + 2 + 4 + 2, presentan E, D y A, `make erp` y no `erp-fast` | Sostenida | «Defensa · 10 minutos por equipo» | enunciado |
| pitch.md | Contexto y Demo: «el LLM solo lee; decide un motor de reglas versionado»; un comando que procesa, reanuda y valida | Sostenida | «el LLM solo extrae campos de los PDF y un motor de reglas explícito decide» | decision.md |
| pitch.md | Arquitectura: etapas idempotentes, caché por hash, tres ADRs; en pantalla, «Diagrama» de `albertitos_plan.pdf` | Sostenida; el diagrama no tiene tarea (ver referencias) | «Recoged la arquitectura y de 2 a 5 ADRs en albertitos_plan.pdf» | enunciado |
| pitch.md | Trazabilidad: documento, campos, ERP, regla y versión; si cambia la Caja, solo se reprocesa lo afectado; bonus en este bloque | Sostenida, aunque el bonus va en otro bloque que el del enunciado (ver ensayo-defensa) | «Cambiar el dato de la Caja → reprocesar solo las facturas afectadas» | decision.md |
| pitch.md | Escala: coste casi lineal, escaneadas × extracción + ERP × latencia; separar medido de estimado | Sostenida | «El coste es casi lineal y fácil de convertir en fórmula» | decision.md |
| pitch.md | Resiliencia: corte del LLM, nada inventado, `pendiente` o degradado, sin duplicados | Sostenida | «Si cae el LLM, la extracción se degrada a solo texto/reglas o se marca como pendiente.» | decision.md |
| pitch.md | «El bonus solo puntúa si está implementado» | Sostenida | «una mejora original, implementada y mostrada en la defensa» | enunciado |
| pitch.md | Respuestas a ESCALAR frente a NO_PAGAR (amb. 1), regla del sábado (amb. 2), ilegibles (amb. 4) y LLM obligatorio (amb. 6) | Supuesto (ya marcado en cada respuesta) | — | analisis.md |
| pitch.md | Respuesta a la interfaz: «quedó fuera de alcance porque el tamaño no puntúa» | Sostenida | «El tamaño de la aplicación no puntúa.» | enunciado |
| pitch.md | La pregunta sobre «PAGAR esta factura» la responde B | Diferencia interna (solo se informa): según `equipo.md`, B «Presenta el pitch o la defensa: no», y la cabecera dice «Presentan: E, D y A» | — | — |

Palabras de fuerza: «desempate», «obligatorio» y «prohibido» se usan como en el enunciado («Desempates: primero escalabilidad y coste», «No subáis…»). No hay ninguna que corregir.

## Hitos antes que sus dependencias

| Hito | Depende de | Choque | Cambio propuesto | ¿Aplicado? |
|---|---|---|---|---|
| VIE 20:00 · Contratos «Sin TODO salvo los del lote 2» (A) | El TODO del teamId depende de la pregunta «teamId: ¿dónde se comunica?» (E, límite VIE 21:00). Los endpoints del ERP dependen del cliente del ERP de A (hasta VIE 23:00) | Las dos dependencias acaban después del hito | Cambiar «Cómo se comprueba» por «Sin TODO salvo los del lote 2, el teamId y los endpoints del ERP (estos, antes del VIE 23:00)» | No |
| SÁB 11:00 · Demo mínima, «`salidas/outcomes.jsonl` con una línea por PDF» (A) | Validador del JSONL de C (hasta SÁB 12:00) | El validador llega una hora después del hito que lo comprueba | Adelantar la tarea de C «Validar JSONL» a SÁB 11:00 (C está disponible de 09:00 a 14:00) | No |

Sin choque, aunque sin margen: D termina el PDF final a las SÁB 23:30, la misma hora del hito de entrega completa de E.

## Referencias sin tarea

| Fichero | Referencia | Qué se ha hecho |
|---|---|---|
| pitch.md | «Diagrama» de `albertitos_plan.pdf` (bloque de arquitectura): la tarea de D no menciona ningún diagrama | Propuesta: marcarlo `[SI DA TIEMPO]` (no aplicado) |
| pitch.md | «lote de demo reducido» (si falla la demo): ninguna tarea lo prepara | Propuesta: marcarlo `[SI DA TIEMPO]` (no aplicado) |
| ensayo-defensa | «salida grabada» como plan B: no tiene tarea | Solo se informa |
| plan.md, pitch.md | `docs/reglas.md`, `docs/coste.md`, `docs/plan/`, `erp.py`, `estado.py`, `tests/`: no existen todavía, pero tienen tarea con dueño (E, E, D, A, A y C) | Correcto |

## Cobertura de la rúbrica

| Criterio | Lo que pide (cita) | Plan | Pitch |
|---|---|---|---|
| Producto, arquitectura y ADRs (35) | «Arquitectura: componentes, flujo de datos y estado, reparto entre agentes, modelos y personas, trazabilidad y recuperación de fallos.» | La tarea de D (SÁB 12:30) cubre componentes, flujo, estado y recuperación. Faltan el **reparto entre agentes, modelos y personas** y la trazabilidad | El bloque 2:00–4:00 no habla del reparto ni defiende el formato (CLI): eso solo sale en una respuesta |
| Producto (35) | «Definid quién lo usa y qué trabajo le ahorra.» | Ninguna tarea lo pone en el PDF | Solo se insinúa en el contexto (0:00–0:45) |
| Trazabilidad y observabilidad (20) | «mostrad estado, evidencia, versiones, latencia, errores, reintentos y trabajo pendiente» / «Mostrad cómo detectar errores, reintentos, trabajo pendiente y coste.» | `explain` cubre la regla, los campos, el ERP y la versión. Ninguna tarea **muestra** la latencia, los errores, los reintentos y el trabajo pendiente del lote (se registran, pero no se enseñan) | El bloque 4:00–6:00 solo enseña `explain` |
| Escalabilidad y coste (25) | «Aportad capacidad, hardware, límites, fórmula de coste y un plan para incorporar más volumen y nuevos tipos de archivo.» | Cubierto (D SÁB 20:00, E SÁB 16:00) | El bloque 6:00–8:00 no menciona el **hardware** ni los **límites**. Los nuevos tipos de archivo solo salen en las preguntas |
| Escalabilidad (defensa) | «contad qué cambiaría con emails, imágenes o Excel» | Ninguna tarea específica | Solo «nuevo tipo de archivo = nueva etapa», en las preguntas |
| Lote 2 | «DEBÉIS MOSTRAR: Qué cambia, cómo seguís su impacto y cuáles son los límites del sistema.» | Cubierto (C SÁB 21:00, D SÁB 23:30) | El guion no tiene ningún bloque para el lote 2: solo una respuesta a una pregunta |
| Calidad de ejecución (10) | «clara, proporcionada y agradable de operar» | Ninguna tarea sobre la experiencia de uso de la CLI (mensajes, resumen, ayuda) | Bloque de demo, cubierto |
| Bonus (+10) | «Si optáis al bonus, enseñad también la mejora adicional implementada.» (en «Demo y contexto») | Cubierto (B SÁB 17:00) | Va en el bloque de trazabilidad, no en el de demo |

## Resumen

- Afirmaciones revisadas (agrupadas en 48 filas): 40 sostenidas; 5 filas de supuesto, de las que 2 son nuevas (`lote-2`: ilegibles del «café»; `contratos.md`: tipo `xlsx`) y 3 ya estaban bien marcadas; 1 a quitar (`ensayo-defensa`: «latencia real»); 2 diferencias solo informadas (dónde va el bonus en la defensa, y B respondiendo preguntas sin presentar). 0 de conocimiento externo.
- Formato de etiquetas: 7 viñetas con `(análisis: riesgo típico)` pasan a `(riesgo típico)`: las reglas 9, 13 y 14 del `CLAUDE.md`, 2 de `convenciones.md` y 2 de `fuentes-externas.md`.
- Palabras de fuerza: ninguna que corregir.
- Bloqueantes: 1 (enviar el teamId y la URL no tiene tarea con dueño; se propone una fila para E el SÁB 13:00).
- Choques de calendario: 2 (el hito de contratos del VIE 20:00 y el validador de C frente a la demo mínima del SÁB 11:00).
- Referencias sin tarea: 3 (2 en el pitch, 1 en `ensayo-defensa`).
- Huecos de cobertura: 8, sobre todo en lo que se enseña en la defensa.
- Cambios aplicados: ninguno.
