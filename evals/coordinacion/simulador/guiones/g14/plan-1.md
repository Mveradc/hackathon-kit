# Plan del equipo · X Ray · Embat (HackSpain 2026)

39 h (inicio por confirmar → dom 20 sep 10:00), 3 personas, Europe/Madrid. Mientras la organización no confirme el inicio, los plazos van en horas desde el inicio (H+N). Hitos: contratos H+1 · demo mínima H+17 · congelación H+27 · entrega dom 20 sep 09:30.

IDs usados hasta: T28

## Hitos del equipo
| Cuándo | Qué | Dueño | Cómo se comprueba | Repliegue si no está |
|---|---|---|---|---|
| H+1 | Contratos acordados: ventana de 24 meses, ficha motor → web y entregables (`docs/contratos.md`) | Persona A | B y C lo releen y dan el visto bueno | Se trabaja con el ejemplo del contrato; decide A |
| H+17 | Demo mínima de principio a fin: una empresa real con curva, desglose y acciones | Persona A | C recorre la ficha de una empresa real sin ayuda | Score sin suavizado fino y una sola regla; decide A |
| H+27 | Congelación: después, solo arreglos y pitch | Persona C | Nadie abre tareas nuevas | — |
| dom 20 sep 09:30 | Entrega final (pitch: hora por confirmar) | Persona C | URL, repositorio y lo que pida Embat enviados | — |

## Por persona

### Persona A · escribe solo en `motor/`, `datos/`, `docs/`, `arranca.py`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T01 | H+1 | Contratos | Fijar en `docs/contratos.md` los 24 meses `YYYY-MM` que se usan | Sin TODO de ventana |
| T02 | H+2 | Ficha falsa | `GET /api/empresas/{company_id}/ficha` devuelve el ejemplo del contrato | `curl` devuelve el JSON del contrato |
| T03 | H+4 | Datos | Cargar los CSV de `datos/` en UTF-8 desde `motor/src/motor/datos.py` | Cargan 1.286 `company_id` sin errores |
| T04 | | | Copiar las columnas reales de `data_dictionary.md` a `docs/contratos.md` | Sin TODO de columnas |
| T05 | H+8 | Features | Calcular caja, cobros y deuda mensuales por `company_id`, sin mezclar monedas | 24 meses por empresa |
| T06 | H+16 | Score | Score 0–100 suavizado con `tendencia` en `motor/src/motor/score.py` | Un bache de un mes no cambia la tendencia |
| T07 | | | Desglose caja/cobros/deuda en puntos de score | La suma cuadra con el cambio del mes |
| T08 | H+18 | Acciones | 2–3 reglas sobre los datos de la empresa que citan su cifra | Cada acción trae `regla` y `cifra` |
| T09 | H+21 | Despliegue | Publicar motor y web en una URL pública (plataforma por elegir) | La ficha abre por URL |
| T10 | H+24 | Validación | Si Embat pide validación propia: apartar empresas y medir la estabilidad del score (`docs/validacion.md`) | Cifra anotada con método |

### Persona B · escribe solo en `web/`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T11 | H+4 | Ficha | Score, curva de 24 meses y flecha de tendencia en `web/src/`, con el JSON de ejemplo | Se ven 24 puntos y la flecha |
| T12 | | | Desglose «qué lo movió» (caja, cobros, deuda) con signo | Tres aportaciones visibles |
| T13 | | | Lista de 0–3 acciones con su cifra | Las acciones del ejemplo se ven |
| T14 | H+6 | Selector | Elegir `company_id` y pedir la ficha a `/api` (T02) | Cambiar de id cambia la ficha |
| T15 | H+14 | Estados | Mensaje de carga y de empresa inexistente | Un id inválido no deja la pantalla en blanco |
| T16 | H+16 | Build | `npm run build --prefix web` limpio para el despliegue | Build sin errores |
| T17 | H+20 | Pulido | Ninguna vista enseña el score sin curva, tendencia y desglose | Revisado vista a vista |
| T18 | | | Cada cifra lleva su moneda o «puntos» | Ninguna cifra sin unidad |
| T19 | H+23 | Datos reales | Probar la ficha con 5 empresas reales y corregir lo que se rompa | Las 5 se pintan bien |

### Persona C · escribe solo en `README.md`, `CLAUDE.md`, `.claude/`, `pitch/`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T20 | H+2 | Preguntas | Preguntar a Embat las ambigüedades y anotar respuestas en `pitch/preguntas.md` | Cada pregunta con respuesta o «sin respuesta» |
| T21 | H+4 | Guion | `pitch/guion.md`: CFO, comprador Embat y por qué lo compra | Leído en voz alta en menos de 5 min |
| T22 | H+17 | Supuestos | Actualizar reglas 8–10 y «Despliegue» de `CLAUDE.md` con las respuestas | Cada supuesto confirmado o pendiente |
| T23 | | | Ajustar `.claude/skills/entrega/SKILL.md` a la forma de entrega | Pasos coinciden con lo que pide Embat |
| T24 | H+19 | Acciones | Revisar como CFO el texto de las acciones en `pitch/revision-acciones.md` | A recibe la lista de cambios |
| T25 | H+21 | README | `README.md` con la URL de la demo y el arranque local | B arranca siguiendo solo el README |
| T26 | H+23 | Pitch | Diapositivas en `pitch/` con capturas de las dos fichas | Caben en 5 min |
| T27 | H+26 | Casos demo | Elegir una empresa que mejora y otra que cae en `pitch/guion.md` | Dos ids con tendencia opuesta |
| T28 | hora por confirmar | Preguntas | Respuesta a «¿cómo sabéis que acierta?» para el turno de preguntas | Una frase con cifra y método |

## Quién espera a quién
- T14 espera a T02: hasta entonces B lee el JSON de ejemplo de `docs/contratos.md` desde un fichero local de `web/`.
- T05 espera a T03 y T04: A avanza con las columnas del ejemplo y las renombra tras la sesión formativa.
- T19 espera a T06–T08: B sigue con el pulido contra la ficha falsa; A avisa en cuanto haya ficha real.
- T09 espera a T16: A prueba antes la plataforma publicando el «hola mundo» de `/api/hola`.
- T27 espera a T06: C prepara los criterios de elección y pide a A una lista de candidatas por tendencia.

## Descansos
| Turno | Quién |
|---|---|
| sáb 00:30–06:30 | Persona C |
| sáb 01:00–07:00 | Persona B |
| sáb 02:30–08:00 | Persona A |
| sáb 23:00–dom 07:30 | Persona B y Persona C |
| sáb 23:30–dom 07:00 | Persona A |
