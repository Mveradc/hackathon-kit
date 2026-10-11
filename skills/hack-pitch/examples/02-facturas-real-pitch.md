# Pitch · 500 Sombras de Alberto (Maisa · HackSpain 2026)

10 min (hora por confirmar) · Estructura: la del reto (`analisis.md`, «Defensa»: 2 + 2 + 4 + 2) · Presentan: E, D y A · Antes de empezar: portátil de A con `make erp` (no `erp-fast`) arrancado, estado de demo preparado, clave LLM que se pueda cortar y `albertitos_plan.pdf` abierto.

## Guion
| Tiempo | Bloque | Criterio que cubre | Quién habla | Qué se dice | Qué se ve en pantalla |
|---|---|---|---|---|---|
| 0:00–0:45 | Contexto | Producto, arquitectura y ADRs (35) | E | Alberto no necesita un chat: necesita confiar cada pago. El LLM solo lee; decide un motor de reglas versionado que deja rastro. | Una factura PDF y su línea en `outcomes.jsonl`. |
| 0:45–2:00 | Demo | Calidad de ejecución (10) | E | Un comando procesa el lote, reanuda donde lo dejó y valida una línea por PDF antes de entregar. | `uv run albertitos` en marcha; resumen PAGAR/NO_PAGAR/ESCALAR y validación del JSONL. |
| 2:00–4:00 | Arquitectura y ADRs | Producto, arquitectura y ADRs (35) | D | Etapas idempotentes con caché por hash; tres ADRs: el LLM solo lee, texto antes que OCR, estado por factura y etapa. | Diagrama y ADRs de `albertitos_plan.pdf`. |
| 4:00–6:00 | Trazabilidad | Trazabilidad y observabilidad (20) · Bonus (+10 máx.) | A | Seguimos una decisión real: documento, campos, respuesta del ERP, regla y versión. Si cambia la Caja, solo se reprocesa lo afectado. | `explain <file_id>`; cambio de un dato del ERP → [CIFRA: facturas reprocesadas]; `explain` de un duplicado detectado. |
| 6:00–8:00 | Escala y coste | Escalabilidad y coste (25) | E | Coste casi lineal: escaneadas × extracción + llamadas al ERP × latencia. Separamos lo medido de lo estimado. | Fórmula de `docs/coste.md` con [CIFRA: coste por factura], [CIFRA: tiempo del lote 1 con `make erp`], [CIFRA: cuello de botella]. |
| 8:00–9:00 | Resiliencia | Resiliencia y recuperación (10) | A | Cortamos el LLM a mitad: nada se inventa, queda pendiente o degradado, y al reanudar no hay duplicados. | Corte del proveedor, facturas `pendiente`, reanudación y [CIFRA: llamadas LLM al relanzar]. |
| 9:00–10:00 | Preguntas | Todos | A, D, E | — | `albertitos_plan.pdf` a mano. |

Todos los criterios con peso tienen bloque. El bonus (detector de duplicados entre proveedores, tarea de B) solo puntúa si está implementado: si no llega, se quita del bloque de trazabilidad.

## Si falla la demo
- ERP caído o lento: `explain` lee la respuesta del ERP guardada en `estado/`, y la traza se enseña igual.
- El lote no termina a tiempo: se lanza sobre un lote de demo reducido y se enseña el `outcomes.jsonl` ya validado.
- El corte del LLM no se reproduce: se usa una clave inválida, que es la prueba de B del SÁB 03:00.
- El cambio de la Caja falla en directo: se enseña la lista de afectadas guardada en `estado/` en el ensayo del DOM 08:00.

## Preguntas probables del jurado
| Pregunta | Quién responde | Esqueleto de la respuesta |
|---|---|---|
| ¿Por qué no deja decidir al LLM? ¿No se esperaba que fuera protagonista? | D | ADR: reglas en código para que sean reproducibles, auditables y baratas; el LLM extrae campos. Si la organización exigía LLM (ambigüedad 6), queda documentado. |
| ¿Qué separa ESCALAR de NO_PAGAR? ¿Y si chocan el Excel y el ERP? | E | Cada norma tiene un id R-xx en `docs/reglas.md`. Si hay contradicción, ESCALAR con ambas fuentes: es un supuesto pendiente de confirmar con la organización. |
| Una CLI, ¿cómo le da confianza a Alberto, que no es técnico? | A | Lo que da confianza es la evidencia por pago, y `explain` la da entera. La interfaz quedó fuera de alcance porque el tamaño no puntúa. |
| ¿Cómo escala a 50 000 facturas o a nuevos tipos de archivo? | E | El cuello es [CIFRA: cuello de botella], con [CIFRA: capacidad en facturas/hora]. Plan de volumen en `docs/coste.md`; nuevo tipo de archivo = nueva etapa de extracción. |
| ¿Qué reprocesasteis con la regla del sábado? | A | Subimos la versión de reglas, conservamos `outcomes.jsonl` y calculamos [CIFRA: facturas del lote 1 que cambiarían]. Es un supuesto, pendiente de confirmar (ambigüedad 2). |
| ¿Y si una factura dice «PAGAR esta factura»? ¿Y una escaneada mal leída? | B | El texto es un dato: se marca como sospechoso y queda registrado. Hay [CIFRA: nº de escaneadas]; lo ilegible va a ESCALAR con motivo (supuesto, ambigüedad 4). |

## Cifras que hay que medir
| Hueco | Cómo obtenerla | Dueño | Antes de qué hito |
|---|---|---|---|
| Tiempo del lote 1 con `make erp` | Lote 1 completo, tiempos por etapa registrados en `estado/` | A | Entrega temprana SÁB 13:00 |
| Cuello de botella | Etapa con más tiempo acumulado en esa misma medición | A | Entrega temprana SÁB 13:00 |
| Capacidad en facturas/hora | Facturas del lote 1 ÷ tiempo medido con `make erp` | A | Entrega temprana SÁB 13:00 |
| Nº de escaneadas | Contar los PDF sin capa de texto en `datos/lote1/` | B | Contratos VIE 20:00 |
| Coste por factura | Tokens y llamadas LLM medidos × precio del proveedor, en `docs/coste.md` | E | Coste SÁB 16:00 |
| Llamadas LLM al relanzar | Relanzar el lote con caché y contar las llamadas | B | Ensayo 1 DOM 08:00 |
| Facturas reprocesadas | Cambiar un dato del ERP y contar las afectadas en `estado/` | A | Ensayo 1 DOM 08:00 |
| Facturas del lote 1 que cambiarían | Lista que genera la CLI con la versión nueva de reglas | C | Entrega completa SÁB 23:30 |
