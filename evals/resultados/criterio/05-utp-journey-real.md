# Revisor C1–C6 · 05-utp-journey-real

Informe literal del revisor independiente (`claude -p` sin el plugin, 2026-10-05). Resumen y patrones en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Pasa | `analisis.md`: pesos «no están especificados», «online (inferido)», UTC-5 «(inferido)», 8 ambigüedades. Hay errores menores, como «documento de cesión de imagen: hay que firmarlos antes del concurso» |
| C2 | Pasa | `enfoques.md`: A ruta, B conversación, C red humana con panel. No nombra stacks y la «Orientación» es condicional. Hay una cita falsa: «se reserva implementar» |
| C3 | Falla | `reglas/datos-y-privacidad.md` y `ruta-y-contenido.md` tienen `paths: "app/**"`, pero sus reglas gobiernan `lib/route.ts`, `lib/types.ts` y `content/*.json` |
| C4 | Falla | `plan.md`, C «Sáb 03:00»: «`lib/route.ts` (…); `lib/progress.ts` (…); script que compara…». Hay tareas agrupadas con «;» en una sola celda, y `datos/` y `package.json` no tienen dueño |
| C5 | Falla | `pitch.md`: «una prueba real de la carrera», cuando el contenido es ficticio. «¿Cómo sabéis que esos son los miedos reales?» se responde con «Salen del enunciado», que no enumera ningún miedo. No hay guion para la semifinal |
| C6 | Pasa | `plan.md` da a cada persona carpeta exclusiva, bloque hasta Vie 20:00–22:00 y contrato `lib/types.ts` con entidades nombradas |

## Fallos encontrados
1. **C5, `pitch.md` (demo 7:00–10:00): «una prueba real de la carrera».** El propio kit dice que los testimonios son ficticios (`plan.md`: «testimonios ficticios») y que todo dato de la UTP «es contenido simulado y se presenta como ejemplo» (`reglas/datos-y-privacidad.md`). El enunciado descalifica las «propuestas […] engañosas». El guion hace que la persona que presenta afirme algo falso delante del jurado.
2. **C5, `pitch.md` (preguntas): «Salen del enunciado y de criterio de orientación».** El enunciado solo dice «supere sus miedos». Las cuatro categorías (dinero, notas, encajar, equivocarse de carrera) las inventó el enfoque A. Es una atribución falsa a la fuente, y es justo la pregunta que el jurado puede comprobar.
3. **C3, `reglas/datos-y-privacidad.md` y `reglas/ruta-y-contenido.md`: `paths: - "app/**"`.** Sus reglas tratan de «un único tipo» (que vive en `lib/types.ts`), de que la ruta sea una «función pura» (`lib/route.ts`, de C) y de los hitos «como datos» (`content/`, de D). Según `plan.md`, B escribe «solo en `app/` (salvo `app/api/`)». Así, C y D, que son quienes implementan esas reglas, nunca las cargan.
4. **C5, `pitch.md`: no hay guion para la semifinal.** Solo aparece «semifinal de 15 min [CONFIRMAR: reparto]». El enunciado fija para esa fase «propuesta de valor […], como responde al reto propuesto y las funcionalidades desarrolladas», y es el filtro para llegar a la final. Toda la preparación apunta a una fase a la que quizá no se llegue.
5. **C5, `pitch.md`: «el informe real de la UTP se conecta cambiando solo ese tipo».** El enunciado no dice quién emite el informe; la ambigüedad 1 pregunta precisamente «quién lo emite». Además, se promete una integración trivial con un formato que se desconoce. Es una afirmación sin base que el jurado (UTP) puede desmontar.
6. **C5, `pitch.md`: las preguntas del jurado no atacan el punto débil principal.** El reto pide «acompañamiento integral» y el enfoque A deja fuera el «contacto con personas reales» (`decision.md`). Nadie prepara la pregunta «¿dónde está el acompañamiento si no hay ninguna persona?».
7. **C3 y C4: la ambigüedad 6 se resuelve por su cuenta, y hay un andamiaje previo.** `CLAUDE.generado.md`, regla 11, y `reglas/convenciones.md` dicen «Las librerías externas entran solo como dependencias de npm (enunciado: originalidad; ambigüedad 6)». La ambigüedad 6 pregunta justamente si valen las librerías y las plantillas, y la regla lo da por permitido mientras cita la ambigüedad como si fuera su respaldo. A la vez, `plan.md` («Hoy solo existe `app/`») y `CLAUDE.generado.md` («page.tsx … hola mundo») parten de un proyecto Next.js creado antes del inicio. Eso choca con «El código […] deben ser creados durante el evento».
8. **C4, `plan.md`: varias tareas por celda separadas por «;».** Ocurre en C «Motor», «Datos» y «Cierre»; D «Ruta», «Pruebas» y «Tono»; E «Slides» y «Entrega temprana»; B «Integración». Es el patrón de fallo ya visto en el Reto 03.
9. **C4, carpetas y ficheros sin dueño.** `reglas/convenciones.md` crea `datos/` «fuera de git», pero ninguna persona del plan la tiene asignada; además, contradice la regla 1 de `CLAUDE.generado.md` («No se cargan ni guardan datos de alumnos reales»). `package.json` y el script `npm run arranca` tampoco tienen dueño. `CLAUDE.generado.md` da el comando como existente, mientras `plan.md` pone a C a escribir el «README con `npm run arranca`» el domingo, y el pitch depende de él.
10. **C4, `plan.md`: incoherencias internas.**
    - E «Envía las preguntas a la organización» antes del Vie 20:00, pero la tabla de preguntas asigna otros dueños (C, D, A) con límites hasta el «Sáb 12:00».
    - El hito de contratos lleva como dueño a C y mezcla una «lista de entregables» que en realidad es tarea de E.
    - D entrega su ejemplo a las «20:30» en las dependencias, pero a las «Vie 20:00» en su tabla.
11. **C3, `reglas/convenciones.md`: reglas genéricas y etiquetas que no cuadran.**
    - «Commits cortos en español…» y «Secretos solo en `.env`» se etiquetan «(convención del kit)». No son propias del reto, y el diseño no usa ningún servicio con claves.
    - «Las fechas y horas que se muestren o se guarden usan la hora de Perú (UTC-5) (análisis: riesgo típico)». El riesgo del análisis trata del horario del evento, no de los datos de la app, y allí UTC-5 iba marcado como inferido.
12. **C3: etiquetas «(decisión)» sin base en `decision.md`.**
    - En `datos-y-privacidad.md`: «No se piden nombre completo, DNI, correo ni teléfono (… decisión)».
    - En `CLAUDE.generado.md`, regla 4: «al menos una tarea» por miedo. Es una operacionalización razonable, pero `decision.md` no dice eso.
13. **C3, `CLAUDE.generado.md`: «Descalifica: […] reutilizar código previo al evento».** Ese motivo no figura en «Criterios de descalificación». Está en «Consideraciones generales» y solo se conecta con la descalificación de forma indirecta, vía «Incumplir con las bases».
14. **C3: no se pueden revisar las guías de pasos.** `CLAUDE.generado.md` remite a `/entrega` y `/ensayo-demo`, y el plan depende de ellas, pero no están entre los ficheros a revisar. No se puede comprobar que cubran los momentos clave.
15. **C2, `enfoques.md` (C): «Transformación Digital "se reserva implementar"».** Va entre comillas como si fuera literal. El enunciado dice «El comité organizador (UTP y Xpedition) […] Tendrá la opción de implementar». La cita es falsa y el sujeto, inexacto.
16. **C1, `analisis.md`: errores menores, que no pasan a otros ficheros.**
    - «Consentimiento informado y documento de cesión de imagen: hay que firmarlos antes del concurso». Solo el consentimiento es «previo al inicio»; para el documento de imagen el enunciado no da plazo.
    - «están prohibidos el software malicioso, las propuestas engañosas… Si esto se detecta después, se revoca el premio». Las causas de revocación del enunciado son solo información falsa, derechos de autor o privacidad, y autoría ajena.
    - «Los organizadores son el área de Transformación Digital»: en realidad organizan la UTP y Xpedition.
    - Los premios aparecen en «Recursos disponibles», que no es su sección.
17. **C5, `pitch.md`: responden preguntas personas que no presentan.** D y C contestan preguntas aunque `equipo.md` marca «Presenta el pitch o la defensa: no». No se confirma que puedan intervenir.

## C6: justificación
Sí, el equipo arrancaría pronto. El plan asigna a cada persona una carpeta exclusiva, un primer bloque cerrado (A: flujo en `design/flujo.md`; B: pantallas con datos falsos; C: `lib/types.ts` con entidades nombradas; D: forma de los JSON; E: entregables). También fija hitos con repliegue y contempla la ausencia de C.

Echo en falta tres cosas:
- Un esquema mínimo de `lib/types.ts` y de `content/*.json` ya escrito. Sin él, B y D esperan a C durante la primera hora.
- La estructura de carpetas del plan dentro de `CLAUDE.generado.md`, que solo lista `app/`.
- Reglas que carguen en `lib/` y `content/`.

Sobra:
- Las convenciones genéricas del kit (commits, `.env`) y la carpeta `datos/`.
- La nota de que «las fechas del reto ya han pasado», que no aporta nada al equipo.
- Un comando de arranque que se da por existente sin que nadie lo tenga asignado.