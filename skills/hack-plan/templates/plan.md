<!--
Plantilla de .hackathon/plan.md. Se lee entero en cinco minutos (≤ ~1.100 palabras).
La sección de cada persona cabe en una pantalla. Una tarea por fila; como máximo 3 filas por bloque.
Si no cabe, quita tareas menores o recorta detalle (nunca juntes tareas en una celda); no añadas secciones ni columnas. Quita estos comentarios al generar.
Las horas («Cuándo», «Hasta», descansos) van como «<día> HH:MM» (vie 19:45, sáb 02:30) o, sin inicio conocido, «H+N»:
el Hackathon OS las lee con el Inicio y la zona horaria de equipo.md.
-->
# Plan del equipo · <reto>

<Duración, número de personas, zona horaria.> Hitos: <contratos HH:MM · demo mínima HH:MM · congelación HH:MM · entrega HH:MM>.

IDs usados hasta: T<NN>

## Hitos del equipo
<!--
Siempre: (1) contratos entre piezas acordados en la primera hora; (2) demo mínima de principio a fin
hacia el 40 % del tiempo hasta la entrega; (3) congelación de funcionalidades con tiempo para al menos
dos ensayos completos del pitch. Además, los eventos del reto (cambios anunciados, entregas, defensa)
y una entrega temprana si el formato permite volver a entregar.
Repliegue solo en los hitos críticos: qué se recorta si no se llega y quién lo decide.
-->
| Cuándo | Qué | Dueño | Cómo se comprueba | Repliegue si no está |
|---|---|---|---|---|

## Por persona
<!-- Una sección por persona, en una pantalla. Entre todas, cubren todo lo que creó el scaffold (incluidos la raíz
y el arranque) y toda carpeta en la que escriba una tarea, cada cosa con un solo dueño.
Cada tarea, redactada para que la ejecute un agente:
qué ficheros toca y cuándo está hecha. Una tarea por fila, nunca varias en una celda separadas por «;».
Un bloque ocupa 1–3 filas: la primera lleva hora y bloque; las siguientes dejan esas celdas vacías.
Cada fila lleva un ID único (T01, T02…, en orden de aparición) que no cambia al ajustar el plan y no se reutiliza.
Una tarea que solo se hace si pasa algo empieza por «Si …:»; un extra que no hace falta para entregar empieza por «[SI DA TIEMPO]».
La fila que recoge una nota de criterios.md acaba «Cómo se comprueba» con «(criterios: AAAA-MM-DD HH:MM)»,
con « · quién» si otra nota tiene la misma fecha y hora. -->

### <Nombre> · escribe solo en `<carpetas>`
| ID | Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|---|
| T01 | <día HH:MM> | <bloque> | <tarea 1> | <comprobación> |
| T02 | | | <tarea 2> | <comprobación> (criterios: <AAAA-MM-DD HH:MM>) |
| T03 | <día HH:MM> | <bloque> | [SI DA TIEMPO] <extra> | <comprobación> |

## Quién espera a quién
<!-- Solo bloqueos reales, citando IDs («T05 espera a T02»). Cada uno con cómo desbloquear antes (p. ej., trabajar contra el contrato acordado con datos falsos). -->

## Preguntas a la organización
<!-- Ambigüedades abiertas del análisis que afectan al plan, con dueño y hora límite para preguntarlas. -->

## Descansos
<!-- Solo si el hackathon dura más de ~20 h. Turnos; descansa antes quien presenta.
Una línea por persona y turno, sin tabla: «- <@usuario | Nombre | Todos>: <día> HH:MM–HH:MM», con el día en que empieza
(si acaba al día siguiente, basta con la hora: «- @ana: sáb 23:30–07:00»). -->
- <@usuario | Nombre | Todos>: <día HH:MM>–<HH:MM>
