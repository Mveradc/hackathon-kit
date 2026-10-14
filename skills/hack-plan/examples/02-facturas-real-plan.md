# Plan del equipo · 500 Sombras de Alberto (Maisa · HackSpain 2026)

40 h (VIE 18 sep 19:00 → DOM 20 sep 11:00), 5 personas, hora de Madrid (Europe/Madrid). Hitos: contratos VIE 20:00 · demo mínima SÁB 11:00 · congelación DOM 06:00 · entrega DOM 10:00 (cierre 11:00). Defensa: hora por confirmar.

IDs usados hasta: T42

## Hitos del equipo
| Cuándo | Qué | Dueño | Cómo se comprueba | Repliegue si no está |
|---|---|---|---|---|
| VIE 20:00 | Contratos acordados en `docs/contratos.md` | A | Sin TODO salvo los del lote 2 | Contrato mínimo con 5 facturas reales; decide A |
| SÁB 11:00 | Demo mínima: lote 1 de punta a punta + `explain` | A | `salidas/outcomes.jsonl` con una línea por PDF | Sin OCR: escaneadas a `ESCALAR` con motivo; decide A |
| SÁB 13:00 | Entrega temprana: `outcomes.jsonl` + borrador del PDF | E | Repo de entrega clonado en limpio | — |
| SÁB 18:00 | Llega `lote-2-sorpresa-v3.2.zip` (guía `/lote-2`) | B | Hash igual al publicado | — |
| SÁB 23:30 | Entrega temprana completa: dos JSONL + PDF | E | Tres ficheros exactos en la raíz | Sin bonus, todos al lote 2; decide A |
| DOM 06:00 | Congelación: solo arreglos y pitch | A | Nadie fusiona funcionalidad nueva | — |
| DOM 08:00 | Ensayo 1 con `make erp` y corte del LLM (`/ensayo-defensa`) | E | ≤ 10 min cronometrados | — |
| DOM 09:15 | Ensayo 2 completo | E | ≤ 10 min, sin fallos de demo | — |
| DOM 10:00 | Entrega final (guía `/entrega`) | E | Clon limpio: tres ficheros, una línea por PDF | Vale la última entrega temprana; decide E |

## Por persona

### A · escribe solo en la raíz, `src/albertitos/` (salvo `extraccion/` y `reglas/`), `docs/contratos.md`, `estado/` y `salidas/`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T01 | VIE 20:00 | Contratos | Rellenar los TODO de `docs/contratos.md` | Revisado por B y C |
| T02 | VIE 23:00 | ERP | Cliente en `erp.py`: sesión única, reintentos, concurrencia limitada | 10 facturas con `make erp` sin errores |
| T03 | SÁB 01:00 | Estado | Estado por factura y etapa con caché por hash en `estado.py` | Relanzar no repite etapas `ok` |
| T04 | SÁB 10:00 | CLI | `uv run albertitos` encadena etapas y escribe `salidas/outcomes.jsonl` | Una línea por PDF |
| T05 | | | Comando `explain <file_id>`: regla, campos, ERP, versión | Traza completa de una factura real |
| T06 | SÁB 13:00 | Medición | Lote 1 con `make erp`, tiempos por etapa | Cifras pasadas a E |
| T07 | SÁB 17:00 | Resiliencia | Cortar el LLM a mitad de lote y reanudar | Sin duplicados tras reanudar |
| T08 | | | Reprocesar solo facturas afectadas por un dato del ERP | Lista de afectadas en `estado/` |
| T09 | SÁB 23:00 | Lote 2 | ERP actualizado → `salidas/outcomes_lote2.jsonl` | Una línea por PDF del lote 2 |
| T10 | DOM 07:30 | Defensa | Guion de trazabilidad, escala y coste (4 min) | Cronometrado |

### B · escribe solo en `src/albertitos/extraccion/`, `datos/` y `.env.example`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T11 | VIE 20:00 | Datos | Descargar materiales del lote 1 en `datos/lote1/` | 500 PDF y Excel presentes |
| T12 | | | Contar PDF sin texto (escaneados) | Cifra pasada a E |
| T13 | SÁB 00:00 | Texto | Texto del PDF, OCR solo si falta, anotando método | Etapa `texto` en todas |
| T14 | SÁB 03:00 | LLM | Campos validados contra esquema, con caché por hash | Segundo lanzamiento: 0 llamadas |
| T15 | | | Timeout, rate limit o respuesta inválida → degradar o `pendiente` | Clave inválida: nada inventado |
| T16 | SÁB 12:00 | Inyección | Marcar y registrar texto que parezca una orden | «PAGAR esta factura» queda marcada |
| T17 | SÁB 17:00 | Bonus | Detector de facturas duplicadas entre proveedores | `explain` muestra el duplicado |
| T18 | SÁB 21:00 | Lote 2 | Descomprimir en `datos/lote2/` y leer CSV en UTF-8 | 40 facturas y CSV presentes |
| T19 | | | Extraer campos del lote 2 | Etapa `extraccion` en las 40 |

### C · escribe solo en `src/albertitos/reglas/`, `tests/` y `.claude/rules/`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T20 | VIE 22:00 | Pruebas | Facturas falsas según contrato en `tests/` | Tests ejecutan |
| T21 | SÁB 01:00 | Reglas | Reglas del Excel con id estable y versión | Cada regla con un test que la dispara |
| T22 | | | Excel y ERP se contradicen → `ESCALAR` con ambas fuentes | Test pasa |
| T23 | | | Archivo ilegible → `ESCALAR` con motivo | Test con PDF corrupto pasa |
| T24 | SÁB 12:00 | Salida | Test del JSONL: líneas = PDF, sin duplicados | Falla con JSONL manipulado |
| T25 | SÁB 14:00 | Windows | Lanzar el lote 1 en Windows | JSONL idéntico al de Linux |
| T26 | SÁB 21:00 | Lote 2 | Codificar la regla nueva y subir la versión de reglas | Test de la regla nueva pasa |
| T27 | | | Calcular qué facturas del lote 1 cambiarían | Lista generada por la CLI |

### D · escribe solo en `docs/plan/` (fuente de `albertitos_plan.pdf`)
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T28 | SÁB 12:30 | Arquitectura | Componentes, flujo, estado y recuperación en `docs/plan/` | Revisado por A |
| T29 | | | Exportar borrador de `albertitos_plan.pdf` | Pasado a E |
| T30 | SÁB 17:00 | ADRs | ADR «el LLM solo lee, deciden las reglas» | Cinco apartados con evidencia |
| T31 | | | ADR «etapas idempotentes y caché por hash» | Cinco apartados con evidencia |
| T32 | | | ADR «texto antes que OCR o visión» | Cinco apartados con evidencia |
| T33 | SÁB 20:00 | Escala | Integrar fórmula de coste, capacidad, hardware y límites | Medido y estimado separados |
| T34 | SÁB 23:30 | Lote 2 | Sección «qué se reprocesa» y PDF final | Cifras iguales a las de la CLI |
| T35 | DOM 07:30 | Defensa | Guion de arquitectura y ADRs (2 min) | Cronometrado |

### E · escribe solo en `docs/reglas.md`, `docs/coste.md`, `.hackathon/`, `.claude/skills/` y el repo de entrega
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T36 | VIE 22:00 | Reglas | Normas del Excel en lenguaje natural en `docs/reglas.md` | Cada norma con id R-xx y fuente |
| T37 | | | Señalar casos grises entre ESCALAR y NO_PAGAR | Enviados a la organización |
| T38 | SÁB 00:00 | Entrega | Crear el repo público de entrega, separado | URL y teamId en `.hackathon/equipo.md` |
| T39 | SÁB 16:00 | Coste | Fórmula de coste en `docs/coste.md` con cifras de A y B | Cada cifra marcada medida o estimada |
| T40 | | | Plan para más volumen y nuevos tipos de archivo | Revisado por D |
| T41 | SÁB 19:00 | Lote 2 | Regla nueva en lenguaje natural en `docs/reglas.md` | C la confirma |
| T42 | DOM 07:30 | Defensa | Guion de demo y contexto (2 min) | Cronometrado |

## Quién espera a quién
- **T21 espera a T36**: C arranca con el Excel y cuadra con `docs/reglas.md` a las 22:00.
- **T04 espera a T14 y T21**: A encadena con stubs de campos falsos del contrato.
- **T39 espera a T06 y T12**: E usa estimaciones marcadas y las sustituye.
- **T26 espera a T41**: C prepara el test con el texto del zip mientras E la redacta.

## Preguntas a la organización
| Pregunta | Dueño | Límite |
|---|---|---|
| 1 · ¿ESCALAR o NO_PAGAR? ¿ERP o Excel? | E | VIE 21:00 |
| 4 · ¿Archivos ilegibles o corruptos? | E | VIE 21:00 |
| teamId: ¿dónde se comunica? | E | VIE 21:00 |
| 5 · ¿APTO validable antes del cierre? | E | SÁB 12:00 |
| 6 · ¿El LLM es obligatorio? (afecta al ADR) | D | SÁB 12:00 |
| 7 · Hora de la defensa | E | SÁB 12:00 |
| 2 · ¿Se reprocesa el lote 1 con la regla nueva? | E | SÁB 18:30 |
| 8 · `lote_2_sorpresa` frente a `lote-2-sorpresa-v3.2.zip` | B | SÁB 18:30 |
| 3 · ¿Qué dato de la Caja cambia y cuándo? | A | SÁB 20:00 |

Mientras, rigen los supuestos 10–12 del `CLAUDE.md`.

## Descansos
| Noche | Turnos |
|---|---|
| VIE → SÁB | E 00:30–07:00 · A 01:00–06:00 · B 03:00–08:00 · C 04:00–09:00 · D llega a las 10:00 |
| SÁB → DOM | E 23:45–05:45 · D 00:00–05:00 · A 00:30–05:30 · C 01:00–05:30 · B 04:00–08:00 |
