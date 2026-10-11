# Revisor C1–C6 · 04-edge-ai-caidas-real · tercera pasada (cadena completa con /hack-check)

Cadena `../prueba-m4-04-v2` con el kit actual y `/hack-check aplicar`, rúbrica de cierre, 2026-10-06.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (grave) | `analisis.md`: «Tiempo presencial: desde el 4 oct a las 14:00». Omite «11:00 AM – 12:00 PM · REGISTRATION · […] Team & member verification» |
| C2 | Falla (leve) | `enfoques.md` (A y B): «*Track-Specific (30 %) + pista 3 (40 %)*: alto». Suma los dos bloques como si fueran la misma rúbrica, cuando eso es la ambigüedad 5 |
| C3 | Falla (leve) | `reglas/datos.md`: «Las grabaciones de prueba se separan de las de ajuste […] (análisis: riesgos y trampas, falsos positivos)». El análisis no dice eso |
| C4 | Falla (grave) | `decision.md` «Fecha: 2026-10-05» y `enfoques.md` «hoy es 5 oct 2026», pero `plan.md` arranca en «4 oct 15:00 \| Contratos». Además, C falta en la verificación de miembros del 4 oct |
| C5 | Falla (leve) | `pitch.md`: «receptor mostrando el aviso», pero en `plan.md` el receptor solo saca el aviso por serie y no hay tarea de pantalla ni indicador |
| C6 | En parte | Carpetas, dueños y contratos claros, pero el calendario no cuadra con la fecha de la decisión |

Bloqueantes: 1

## Fallos encontrados

**Graves**

1. **Grave, bloqueante (descalificación). C1, C3 y C4.** Falta la hora de registro y verificación de miembros, y C no está ese día.
   - **Ficheros:** `analisis.md` («Tiempo presencial: desde el 4 oct a las 14:00»), `CLAUDE.generado.md` («Ronda 2 presencial: 4 oct 2026 14:00 → 6 oct 2026»), `plan.md` («C llega el 5 oct a las 08:00») y `verificacion.md` («El resto de entregables cuadra»).
   - **Qué dice el enunciado:** el 4 oct empieza con «11:00 AM – 12:00 PM · REGISTRATION · Desk Registration starts — Team & member verification», seguido de «Goodies & ID card collection».
   - **Por qué importa:** ningún fichero menciona esa franja. El plan da por bueno que una persona falte a la verificación de miembros y no pregunta a la organización si eso es aceptable, ni en las preguntas ni en las ambigüedades. El enunciado no dice que la verificación sea eliminatoria, pero sí que es el primer paso del evento. Puede costar la elegibilidad de C o del equipo, y arreglarlo cuesta una pregunta.

2. **Grave, no bloqueante. C4.** El plan no cuadra con la fecha en que se tomó la decisión.
   - **Ficheros:** `decision.md` dice «Fecha: 2026-10-05» y `enfoques.md` avisa: «hoy es 5 oct 2026 […] os quedan pocas horas de trabajo».
   - **Qué hace el plan:** reparte «44 h (4 oct 14:00 → 6 oct 10:00)», con hitos el 4 oct a las 15:00 y bloques de A y B el 4 oct (IMU 18:00, Detección 23:00, Grabador 17:00…), y la demo mínima el 5 oct a las 08:00.
   - **Por qué importa:** si el equipo empieza el 5 oct, casi la mitad del calendario ya ha pasado. Nadie reajustó los bloques a «partís de lo que hicierais en la Ronda 1», que es lo que suponen los propios enfoques. `verificacion.md` no lo detecta.

**Leves**

3. **Leve. C1.** El riesgo «Límites de API `(riesgo típico)`» de `analisis.md` no cita ninguna parte del enunciado. Solo apoya «si la alerta se envía mediante un servicio externo», y eso es una hipótesis, no texto del reto.

4. **Leve. C2, y se arrastra a C3.** Los enfoques A y B puntúan «Track-Specific (30 %) + pista 3 (40 %)» como un único bloque. Que la rúbrica sea la misma es justo la ambigüedad 5, y solo el enfoque C la nombra. Llega hasta `reglas/firmware.md` («el firmware es el núcleo de la nota»), donde ya va marcado como supuesto.

5. **Leve. C2.** «Es el planteamiento más habitual en detección de caídas» (`enfoques.md`, copiado en `decision.md`) es conocimiento externo sin marcar. De ahí sale «Innovation está bajo» en `CLAUDE.generado.md`.

6. **Leve. C3.** En `reglas/datos.md`, la regla de separar prueba y ajuste lleva la etiqueta «(análisis: riesgos y trampas, falsos positivos)», pero el análisis solo dice «Si no se mide, es difícil demostrarlo». `verificacion.md` lo admite («La etiqueta del análisis respalda que hay que medir, no la separación. Sin cambio») y aun así no lo corrige.

7. **Leve. C3.** También en `reglas/datos.md`, «Cada grabación lleva […] la frecuencia de muestreo (decisión)» no tiene respaldo: `decision.md` no habla de frecuencia. `verificacion.md` lo da por «Sostenida» con una cita que tampoco la menciona.

8. **Leve. C3.** «No hay dataset: los datos de entrenamiento y prueba son los que grabemos nosotros (análisis: recursos disponibles)» aparece en la regla 9 de `CLAUDE.generado.md` y en `reglas/datos.md` («Todos los datos salen de grabaciones propias»).
   - **Qué dice el análisis:** solo que la organización no da dataset.
   - **Por qué importa:** limitarse a grabaciones propias, y así descartar datasets públicos, es una decisión del equipo, no un dato del análisis. La etiqueta de origen es falsa. `verificacion.md` la da por sostenida con la cita «Datasets: ninguno.», que no lo respalda.

9. **Leve. C3.** `reglas/firmware.md` fija «`board = esp32dev`, `espressif32@6.13.0`». La versión de plataforma no sale del enunciado ni lleva etiqueta: el «(supuesto: ambigüedad 9)» solo cubre lo de Arduino frente a ESP32.

10. **Leve. C4.** `verificacion.md` detectó tres choques de calendario que siguen en `plan.md`:
    - La «Métrica final» de B (6 oct 07:30) llega después de «Pitch final» de C (06:00, «Todas las cifras son medidas») y del «Ensayo completo 1» (06:30).
    - El repliegue de la congelación de las 05:00 dice «deciden A y B», pero B duerme de 02:00 a 06:00.
    - La tarea «Pitch E1» termina a las 12:30, a la misma hora que su ensayo.

11. **Leve. C4.** En las «Preguntas a la organización» de `plan.md` faltan las ambigüedades 5 y 7, que `decision.md` marca como abiertas y de las que depende el supuesto de `reglas/firmware.md`. `verificacion.md` lo propone («no se ha cambiado»).

12. **Leve. C4.** Ninguna tarea reserva tiempo para el «On-Site Challenge» (5 oct 14:00–20:00). Justo en esa franja A tiene «Consumo» hasta las 19:00 y C tiene «Coste» hasta las 18:00 y «Consumo» hasta las 20:45, aunque el contenido del reto es desconocido (ambigüedad 3).

13. **Leve. C4.**
    - **Grabación con A ocupado:** «Grabar ≥20 caídas sobre colchoneta con A» (hasta 4 oct 23:00) choca con el bloque «Detección» de A, que también acaba a las 23:00.
    - **Colchoneta sin dueño:** es inferida y ninguna tarea la consigue.
    - **Hito con dos dueños:** el de contratos va a cargo de «A y B».

14. **Leve. C5.** `pitch.md` enseña la «foto del montaje» y el «colgante puesto» sin tarea que los produzca, y `verificacion.md` solo lo informa. Tampoco hay tarea que haga que el receptor «muestre» el aviso fuera del monitor serie.

15. **Leve. C3 y C4 (`verificacion.md`).**
    - **Bloqueante sin base:** clasifica como bloqueante la «Ronda 1 sin mención». El enunciado dice que la Ronda 1 acaba el 4 oct y que «is not an elimination round; all finalist teams […] will continue to Round 2». Para el 5–6 oct no hay riesgo de descalificación, y se queda sin señalar el bloqueante real (fallo 1).
    - **Recuentos que no cuadran:** declara «50 filas», la tabla tiene 51, y las categorías suman 49 (33+11+1+1+3).

16. **Sin poder comprobar.** Las guías `.claude/skills/evaluacion-demo` y `on-site-challenge` y el `.gitignore` no están entre los ficheros que me han pasado. No he encontrado fallos de seguridad: los secretos van en `.env` y el enunciado no contiene instrucciones escondidas.

## C6: justificación
En parte. Cada persona sabe en qué carpeta escribe (A en `dispositivo/` y `receptor/`, B en `datos/`, C en la raíz y `docs/`) y contra qué contrato trabaja (`datos/contratos.md`, `alerta.h`, `umbrales.h`). Las reglas de firmware y datos son concretas y propias del reto: ventana de cancelación, ESP-NOW con ACK, dos cifras de evaluación. Eso permite arrancar rápido.

Pero el plan está escrito como si fueran las 14:00 del 4 oct cuando la decisión es del 5 oct, así que el equipo tendría que rehacer el calendario antes de usarlo. Además, nadie ha preguntado si C puede faltar a la verificación de miembros.

**Echaría en falta:**
- un calendario rebasado a partir del momento real;
- capacidad reservada para el On-Site Challenge;
- una tarea de pantalla o indicador en el receptor;
- medir RAM y flash para Code Efficiency.

**Sobra:** el bloqueante de la Ronda 1 en `verificacion.md`, que distrae del riesgo de verdad.