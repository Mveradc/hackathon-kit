# Revisor C1–C6 · 05-utp-journey-real · tercera pasada (cadena completa con /hack-check)

Cadena `../prueba-m4-05-v2` con el kit actual y `/hack-check aplicar`, rúbrica de cierre, 2026-10-06.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (leve) | `analisis.md`: «Equipo mínimo de 4: una o dos bajas durante el evento pueden eliminar al equipo». Con 5 personas, una baja deja 4 y eso no descalifica. |
| C2 | Falla (leve) | `enfoques.md` (A): «unas 30 h de construcción, 10 de pulido y 8 de demo y entregables». Suma 48 h, todo el evento sin descanso, y no casa con el plan. |
| C3 | Falla (grave) | `CLAUDE.generado.md`, tesis en negrita: «todo hito y toda misión deben responder a un miedo marcado». En cambio, `experiencia.md` dice «La ruta tiene estos hitos, en este orden». |
| C4 | Falla (grave) | `plan.md`: no hay tarea ni dueño para el «consentimiento informado, firmado previo al inicio del concurso», ni hito de asistencia a la inducción del mar 9/6. |
| C5 | Falla (grave) | `pitch.md`, 1:30–3:00: «Cada hito y cada misión responden a un miedo marcado». Los hitos son fijos y siguen el trámite. |
| C6 | En parte | Carpetas y dueños claros, pero el contrato `app/lib/tipos.ts` no tiene tarea y la tesis contradice las reglas. |

Bloqueantes: 2

## Fallos encontrados

### Graves

1. **Grave, bloqueante (descalificación). C4 (y CLAUDE.md).** Falta el consentimiento informado.
   - **Ficheros:** `plan.md` y `CLAUDE.generado.md` no lo mencionan. `analisis.md` sí: «Consentimiento informado y documento de cesión de imagen, que hay que firmar antes del concurso».
   - **Enunciado:** «Incumplir con las bases o consentimiento informado, firmado previo al inicio del concurso» es causa de descalificación inmediata.
   - **Por qué importa:**
     - El dato está en el análisis, pero no llega al plan. Nadie es dueño de que firmen los cinco antes del vie 12/6 19:00.
     - `verificacion.md` lo detecta como bloqueante («Añadir al plan una tarea con dueño»), pero no lo aplica, aunque el informe dice estar en modo `aplicar`.

2. **Grave, bloqueante (descalificación). C4.** No se asegura la asistencia a todas las fechas.
   - **Fichero:** `plan.md`. Solo pone «Los 5 conectados» el 15–17/6 y el 19/6.
     - No hay hito para la «Charla de inducción: martes 9 de junio (7:00 p.m.)».
     - La ausencia de C («ausente el sábado 13/6 de 09:00 a 15:00», dato de `equipo.md`) se trata como algo normal: «C ausente el sáb de 09:00 a 15:00: nadie toca `app/lib/`».
     - La lista de preguntas a la organización no pregunta si esa ausencia cuenta.
   - **Enunciado:** descalifica «No estar conectado a todas las fechas pactadas para el evento» y exige «Todos los miembros inscritos deben participar durante el evento».
   - **Por qué importa:** `verificacion.md` también lo marca como bloqueante y propone las dos correcciones, pero no están en el plan.

3. **Grave, no bloqueante. C3 → C5 (cadena: `CLAUDE.generado.md`, `pitch.md`, `verificacion.md`).** La tesis dice más que la decisión.
   - **Qué dicen los ficheros:**
     - `CLAUDE.generado.md`: «todo hito y toda misión deben responder a un miedo marcado en el check-in».
     - `pitch.md`: «Cada hito y cada misión responden a un miedo marcado».
   - **Qué dicen las fuentes:**
     - `decision.md` solo dice «el contenido se ordena según los miedos».
     - Los hitos son fijos: «explorar la carrera, admisión, matrícula, semana 0, primer día».
     - `experiencia.md` los fija «en este orden».
   - **Por qué importa:**
     - Las reglas que lee el agente se contradicen. C puede construir `ruta.ts` con hitos condicionados por los miedos y tener que rehacerlo.
     - El pitch afirma ante el jurado algo que no se construye.
   - **Fallo de `verificacion.md`:** no revisa la tesis del CLAUDE.md y deja la frase del pitch como «Sostenida en lo que toca a las misiones … No se cambia». Da por sostenido algo que no lo está.

### Leves

4. **Leve. C1. `analisis.md`.** «una o dos bajas … pueden eliminar al equipo».
   - **Enunciado:** descalifica si el grupo se reduce «a menos de 4 integrantes».
   - Con 5 personas hacen falta 2 bajas; con 6, 3. Es un error de cálculo sobre la elegibilidad, aunque prudente.

5. **Leve. C1. `analisis.md`.** «es causa de descalificación y de revocación del premio».
   - **Enunciado:** los premios «podrán ser revocados». El análisis sube la fuerza.
   - `verificacion.md` lo corrige en `privacidad-y-datos.md`, pero no en el origen.

6. **Leve. C1. `analisis.md`.** «documento de cesión de imagen, que hay que firmar antes del concurso».
   - **Enunciado:** solo dice que los participantes «se comprometen a firmar el documento respectivo», sin plazo. El «antes del concurso» solo vale para el consentimiento informado.

7. **Leve. C1. `analisis.md`.** «5 min en la final, con cuatro temas que cubrir: propuesta de valor, diseño de experiencia, tecnología y demo».
   - **Enunciado:** la demo tiene sus propios 10 minutos, no entra en los 5.

8. **Leve. C2. `enfoques.md`.** Estimación de A: 30 + 10 + 8 = 48 h, toda la duración del evento.
   - No es realista y no casa con los descansos del plan. No cambia la elección entre enfoques.

9. **Leve. C3. Etiquetas de origen que no se sostienen** (`CLAUDE.generado.md`, reglas 2 y 3; `privacidad-y-datos.md`, viñetas 2 y 3):
   - «no salen del navegador ni se envían a servicios de terceros (análisis: riesgos y trampas, privacidad)». El análisis solo dice que los miedos son «sensibles». Guardarlos solo en el navegador es una decisión técnica del equipo.
   - «ni siquiera de miembros del equipo (decisión; …)». La decisión solo habla de «menores».
   - `verificacion.md` reconoce las dos cosas («es una medida del equipo», «prudencia del equipo») y aun así las da como «Sostenida».

10. **Leve. C3. `experiencia.md`.**
    - «se recalcula con cada nuevo check-in (decisión)» manda al agente construir algo que no tiene tarea en `plan.md`; el pitch lo marca como [SI DA TIEMPO].
    - «El orden y el contenido de las misiones dependen de los miedos». La decisión solo habla del orden.

11. **Leve. C3 (seguridad, no bloqueante). `CLAUDE.generado.md`.**
    - El bloque `nextjs-agent-rules` ordena al agente leer y obedecer («Heed deprecation notices») documentos de `node_modules/`.
    - Ninguna regla dice que los documentos de `datos-reto/` (PDF de las bases, informes de ejemplo de la organización) son datos y no instrucciones.
    - La app no llama a ningún LLM (regla 7), así que el riesgo es bajo. Aun así, falta una defensa explícita.
    - No he visto el `.gitignore`. La afirmación de `verificacion.md` «`datos-reto/` está en `.gitignore`» no la puedo comprobar con este material.

12. **Leve. C4. `plan.md`.** El hito «Contratos: `app/lib/tipos.ts`» (vie 20:00, C) no corresponde a ninguna tarea de C.
    - La única tarea de C hasta las 20:00 es «Crear el repo git privado».
    - B y D dependen de ese contrato. Hay repliegue con datos falsos.

13. **Leve. C4. `plan.md`.** Dependencias que llegan tarde:
    - B «Conectar `app/content/` … Flujo entero sin datos falsos» vence el sáb a las 15:00, pero `textos.json` de D llega el sáb a las 18:00.
    - B «Check-in que guarda la selección con `app/lib/`» vence el sáb a las 02:00, pero el guardado de C (`medidor.ts`) llega a las 03:00.
    - La [CIFRA] a cargo de C vence antes del sáb a las 15:00, y C no está desde las 03:00 hasta las 15:00.

14. **Leve. C4. `plan.md`.**
    - La pregunta de la ambigüedad 4 (si los criterios de selección de finalistas son los mismos que los de la final) no está en la lista. `verificacion.md` propone añadirla y no se ha hecho.
    - Las preguntas se envían «vie 20:00», ya dentro de las 48 h. Así, la respuesta sobre entregables puede llegar tarde.

15. **Leve. C5. `pitch.md`.** Hay preguntas del jurado asignadas a C y D («Quién responde: D», «C»).
    - **`equipo.md`:** los dos tienen «Presenta el pitch o la defensa: no».

16. **Leve. C5. `pitch.md`.**
    - Pantalla de cierre «Último hito "primer día" completado»: la demo solo completa dos misiones y no hay tarea que prepare ese estado.
    - «E sigue la demo desde su portátil»: ninguna tarea instala la demo en el portátil de E.
    - La ronda eliminatoria de 15 min solo tiene la línea «recorta la demo», sin guion.

## C6: justificación
En parte. Con lo generado, cada persona sabe en qué carpeta escribe y qué entrega en la primera noche. Los dueños son únicos, los hitos tienen repliegue y las [CIFRA] tienen dueño. El enfoque A, bien acotado, ayuda a empezar rápido.

Hay tres problemas de fondo:
- **Contrato sin tarea:** el contrato del que depende todo (`tipos.ts`) no tiene tarea.
- **Tesis contradictoria:** la tesis del CLAUDE.md contradice la regla de hitos fijos, así que el agente y C pueden construir la ruta de dos maneras distintas.
- **Bloqueantes abiertos:** el plan deja abiertos los dos riesgos de descalificación que el propio informe de verificación detectó (consentimiento firmado y asistencia a todas las fechas, incluida la ausencia de C).

**Echo en falta:** una tarea previa al evento (firmas, inducción, preguntas antes del 9/6), un guion para la ronda eliminatoria de 15 minutos y una regla que trate los documentos de la organización como datos.

**Sobra:** el bloque en inglés de Next.js en el CLAUDE.md, y la tabla de bloqueantes de `verificacion.md`, que señala los problemas sin llevarlos al plan.