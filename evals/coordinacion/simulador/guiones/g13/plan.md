# Plan del equipo · X Ray · Embat (HackSpain 2026)

39 h (vie 18 sep 19:00 → dom 20 sep 10:00), 3 personas, Europe/Madrid. Hitos: contratos vie 20:00 · demo mínima sáb 12:30 · congelación sáb 22:00 · entrega dom 10:00.

IDs usados hasta: T28

## Hitos del equipo
| Cuándo | Qué | Dueño | Cómo se comprueba | Repliegue si no está |
|---|---|---|---|---|
| vie 20:00 | Contratos acordados: ventana de 24 meses, ficha motor → web y entregables (`docs/contratos.md`) | Persona A | B y C lo releen y dan el visto bueno | Se trabaja con el ejemplo del contrato y columnas provisionales; decide A |
| sáb mañana (hora por confirmar) | Sesión formativa sobre los datos | Persona A | Dudas de columnas resueltas en `docs/contratos.md` | — |
| sáb 12:30 | Demo mínima de principio a fin (≈45 %, cuando vuelve B): `uv run arranca.py`, una empresa real con curva, desglose y acciones | Persona A | C recorre la ficha de una empresa real sin ayuda | Score sin suavizado fino y una sola regla de acción; decide A |
| sáb 20:00 | Demo abierta por URL pública | Persona A | Se abre desde un móvil fuera de la red del aula | Túnel desde el portátil de A (conocimiento externo, verificar) y vídeo grabado; deciden A y C |
| sáb 22:00 | Congelación: después, solo arreglos y pitch | Persona C | Nadie abre tareas nuevas | — |
| sáb 22:30 | Entrega temprana, si se puede volver a entregar (supuesto: ambigüedad 5) | Persona C | Justificante de envío guardado | — |
| sáb 22:30 | Ensayo 1 del pitch completo, 5 min (inferido, ambigüedad 6) | Persona B y Persona C | Cronometrado, con las dos empresas en vivo | — |
| dom 08:30 | Ensayo 2 del pitch completo | Persona B y Persona C | Dentro de tiempo y sin fallos de demo | Se usa el vídeo grabado; decide C |
| dom 10:00 | Entrega final (pitch: hora por confirmar) | Persona C | URL, repositorio y lo que pida Embat enviados | — |

## Por persona

### Persona A · escribe solo en `motor/`, `datos/`, `docs/`, `arranca.py`, `.gitignore`, `.gitattributes`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T01 | vie 19:45 | Contratos | Fijar en `docs/contratos.md` los 24 meses `YYYY-MM` que se usan | Sin TODO de ventana |
| T02 | vie 20:30 | Ficha falsa | `GET /api/empresas/{company_id}/ficha` devuelve el ejemplo del contrato | `curl` devuelve el JSON del contrato |
| T03 | vie 23:00 | Datos | Cargar los CSV de `datos/` en UTF-8 desde `motor/src/motor/datos.py` | Cargan 1.286 `company_id` sin errores |
| T04 | | | Copiar las columnas reales de `data_dictionary.md` a `docs/contratos.md` | Sin TODO de columnas |
| T05 | sáb 02:30 | Features | Calcular caja, cobros (días de cobro) y deuda mensuales por `company_id`, sin mezclar monedas | 24 meses por empresa |
| T06 | sáb 11:00 | Score | Score 0–100 suavizado con `tendencia` en `motor/src/motor/score.py` | Un bache de un mes no cambia la tendencia (criterios: 2026-09-19 10:40) |
| T07 | | | Desglose caja/cobros/deuda en puntos de score | La suma cuadra con el cambio del mes |
| T08 | sáb 12:30 | Acciones | 2–3 reglas sobre los datos de la empresa que citan su cifra | Cada acción trae `regla` y `cifra` (criterios: 2026-09-18 20:15 · Jorge) |
| T09 | sáb 16:00 | Despliegue | Publicar motor y web en una URL pública (plataforma por elegir) | La ficha abre por URL (criterios: 2026-09-19 11:20) |
| T10 | sáb 19:00 | Validación | Apartar empresas y medir la estabilidad del score en ellas (`docs/validacion.md`) | Cifra anotada con método |

### Persona B · escribe solo en `web/`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T11 | vie 23:30 | Ficha | Score, curva de 24 meses y flecha de tendencia en `web/src/`, con el JSON de ejemplo | Se ven 24 puntos y la flecha (criterios: 2026-09-18 20:15 · Lucía) |
| T12 | | | Desglose «qué lo movió» (caja, cobros, deuda) con signo | Tres aportaciones visibles |
| T13 | | | Lista de 0–3 acciones con su cifra | Las acciones del ejemplo se ven (criterios: 2026-09-18 20:15 · Jorge) |
| T14 | sáb 01:00 | Selector | Elegir `company_id` y pedir la ficha a `/api` (T02) | Cambiar de id cambia la ficha |
| T15 | sáb 08:45 | Estados | Mensaje de carga y de empresa inexistente | Un id inválido no deja la pantalla en blanco |
| T16 | sáb 14:00 | Datos reales | Probar la ficha con 5 empresas reales y corregir lo que se rompa | Las 5 se pintan bien |
| T17 | | | `npm run build --prefix web` limpio para el despliegue | Build sin errores |
| T18 | sáb 18:00 | Pulido | Ninguna vista enseña el score sin curva, tendencia y desglose | Revisado vista a vista |
| T19 | | | Cada cifra lleva su moneda o «puntos» | Ninguna cifra sin unidad |

### Persona C · escribe solo en `README.md`, `CLAUDE.md`, `.claude/`, `pitch/`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T20 | vie 20:30 | Preguntas | Preguntar a Embat las ambigüedades de abajo y anotar respuestas en `pitch/preguntas.md` | Cada pregunta con respuesta o «sin respuesta» (criterios: 2026-09-18 20:40) |
| T21 | vie 23:00 | Guion | `pitch/guion.md`: CFO, comprador Embat y por qué lo compra | Leído en voz alta en menos de 5 min |
| T22 | sáb 12:00 | Supuestos | Actualizar reglas 8–10 y «Despliegue» de `CLAUDE.md` con las respuestas | Cada supuesto confirmado o pendiente |
| T23 | | | Ajustar `.claude/skills/entrega/SKILL.md` a la forma de entrega | Pasos coinciden con lo que pide Embat (criterios: 2026-09-19 11:20) |
| T24 | sáb 14:00 | Casos demo | Elegir una empresa que mejora (≈45→65) y otra que cae (≈82→68) en `pitch/guion.md` | Dos ids con tendencia opuesta |
| T25 | sáb 15:30 | Acciones | Revisar como CFO el texto de las acciones en `pitch/revision-acciones.md` | A recibe la lista de cambios |
| T26 | sáb 18:00 | README | `README.md` con la URL de la demo y el arranque local | B arranca siguiendo solo el README |
| T27 | sáb 21:00 | Pitch | Diapositivas en `pitch/` con capturas de las dos fichas | Caben en 5 min |
| T28 | | | Respuesta a «¿cómo sabéis que acierta?» con la cifra de T10 | Una frase con cifra y método |

## Quién espera a quién
- T14 espera a T02: hasta entonces B lee el JSON de ejemplo de `docs/contratos.md` desde un fichero local de `web/`.
- T05 espera a T03 y T04: A avanza con las columnas del ejemplo y las renombra tras la sesión formativa.
- T16 espera a T06–T08: B sigue con T15 contra la ficha falsa; A avisa en cuanto haya ficha real.
- T09 espera a T17: A prueba antes la plataforma publicando el «hola mundo» de `/api/hola`.
- T24 espera a T06: C prepara los criterios de elección y pide a A una lista de candidatas por tendencia.
- T28 espera a T10: si no llega, C defiende la estabilidad con un bache de la demo, sin decir «acertado».

## Preguntas a la organización
| Pregunta | Dueño | Hasta |
|---|---|---|
| 5. Cuándo y cómo se entrega, y si hace falta deploy público | Persona C | vie 20:30 |
| 1 y 2. Cómo se valora la generalización y si hay etiqueta de salud | Persona C | vie 20:30 |
| 3. Score por empresa o por grupo | Persona A | sesión formativa |
| 7 y 8. Escala 0–100 y trato de varias monedas | Persona A | sesión formativa |
| 6 y 4. Duración del pitch, preguntas y peso de los bloques | Persona C | sáb 12:00 |

## Descansos
| Turno | Quién |
|---|---|
| sáb 00:30–06:30 | Persona C |
| sáb 01:00–07:00 | Persona B |
| sáb 02:30–08:00 | Persona A |
| sáb 23:00–dom 07:30 | Persona B y Persona C |
| sáb 23:30–dom 07:00 | Persona A |
