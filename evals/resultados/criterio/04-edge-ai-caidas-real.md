# Revisor C1–C6 · 04-edge-ai-caidas-real

Informe literal del revisor independiente (`claude -p` sin el plugin, 2026-10-05). Resumen y patrones en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Pasa | `analisis.md`: los pesos 18/12/12/9/9 aparecen marcados como «(inferido)» y cuadran con el 30/20/20/15/15 del 60 %. Las horas de 14:00–20:00, 08:00–13:00 y 08:00–10:00 coinciden con el horario. Solo hay imprecisiones menores. |
| C2 | Pasa | `enfoques.md`: «Colgante (T3)» frente a «Visión (T2)» frente a «Doble confirmación (T2)». Difieren en el sensor, el track y la arquitectura, no recomiendan ninguno y usan los pesos del análisis. La etiqueta «(ambigüedad 9)» del enfoque C está mal aplicada. |
| C3 | Falla | `CLAUDE.generado.md`: «Evaluación 1 (hora exacta no especificada…)», pero el enunciado dice «02:00 PM – 08:00 PM · EVALUATION - 1». `convenciones.md` es genérico («convención del kit») y las guías de `.claude/skills/` no existen. |
| C4 | Falla | `plan.md`: «Más capturas con C como tercera persona; conjunto de prueba separado; falsos positivos por clase; guion de pruebas…» son 4 tareas en una celda. El paso del `modelo.h` choca con la regla de «modelos fuera de git». |
| C5 | Falla | `pitch.md`: dice «autonomía medida, no estimada: `[CIFRA: autonomía estimada (días)]`». Ninguna pregunta del jurado ataca que la «emergency alert» solo llega a un receptor ESP-NOW cercano. |
| C6 | Pasa | Los contratos son concretos (CSV `t_ms,ax,…`, `int clasifica(const float *)`, struct ESP-NOW) y cada persona tiene carpeta propia. Faltan el arranque del repositorio y el paso del modelo de una carpeta a otra. |

## Fallos encontrados
1. **C4: celdas con varias tareas agrupadas.**
   - **Dónde:** `plan.md`, Persona B, bloque de las 11:30 del 5 oct: «Más capturas con C como tercera persona; conjunto de prueba separado; falsos positivos por clase; guion de pruebas en `datos/GUION_PRUEBAS.md`».
   - **Lo mismo en Persona A, bloque de las 19:30 del 4 oct:** una sola celda junta la máquina de estados, ESP-NOW con ACK y reintentos, el `receptor/src/main.cpp` y la integración del `modelo.h`.
   - **Por qué importa:** es el patrón exacto que el criterio prohíbe. Además, el bloque de A es el camino crítico de la demo mínima y solo tiene 2 h 30 min. En ese mismo hueco B le necesita para «Capturar las 4 clases (caída sobre colchoneta) con A». A queda asignado a dos cosas a la vez.

2. **C4/C6: el paso del modelo de `datos/` a `colgante/` se contradice.**
   - B exporta «`datos/modelos/modelo.h` para A».
   - `convenciones.md` dice que «los modelos entrenados no se suben a git: van en `datos/modelos/`».
   - A trabaja en Windows y B en Linux, y A «escribe solo en `colgante/`…».
   - **Por qué importa:** nadie dice cómo llega el fichero al firmware ni quién lo copia. La dependencia «A espera el `modelo.h` de B» no se puede resolver tal como está escrita.

3. **C4: las horas de las dependencias no cuadran.**
   - «A espera el `modelo.h` de B (4 oct 19:00)», pero el bloque de B que lo produce termina a las 19:30, que es justo la hora de la demo mínima.
   - El plan también habla de «≈14 h de trabajo efectivo», mientras que el análisis, el CLAUDE.md y `datos.md` dicen unas 13 h.
   - **Por qué importa:** la demo mínima depende de una entrega que llega a la misma hora en que debe estar terminada.

4. **C4: la congelación de la Evaluación 1 recae en quien acaba de llegar.**
   - Hito del 5 oct a las 12:30, dueño C. El repliegue dice «Se enseña la última versión que haya pasado la demo mínima; lo decide C».
   - C llega a las 08:00 de ese día y no sabe C++ avanzado (`equipo.md`).
   - **Por qué importa:** decidir qué versión del firmware se enseña debería ser cosa de A. Es el mismo tipo de fallo que el ejemplo del Reto 03.

5. **C4: el plan no deja tiempo real para el On-Site Challenge.**
   - El bloque de A «6 oct 08:00 · Ajustes: Cambios del On-Site Challenge» cae en una ventana en la que A está en la Evaluación 1 o el On-Site Challenge (5 oct, 14:00–20:00) o descansando (desde las 20:00).
   - La congelación final es a las 08:00 del 6 oct. Así se pierde el hueco «08:00 AM – 10:00 AM · FINAL POLISH · Testing, debugging» que da el enunciado.

6. **C5: el pitch afirma algo que su propio plan de medidas contradice.**
   - La respuesta a la pregunta de originalidad dice «autonomía medida, no estimada: `[CIFRA: autonomía estimada (días)]`».
   - La tabla de cifras la calcula como «Capacidad de la batería entre consumo medio medido», es decir, estimada.
   - **Por qué importa:** es una afirmación que el jurado puede desmontar en directo.

7. **C5: falta la pregunta sobre el punto más débil del enfoque.**
   - El enunciado pide «generates emergency alerts». El enfoque elegido solo avisa a un ESP-NOW cercano («avisa sin red»).
   - La ambigüedad 4 sigue abierta y ninguna pregunta probable ataca esto (¿cómo se entera un familiar o un servicio de emergencias?).
   - Tampoco se pregunta por los falsos negativos (caídas lentas o sin impacto).

8. **C3/C5: el scaffolding y el pitch cierran una ambigüedad abierta como si estuviera resuelta.**
   - CLAUDE.md, regla 5: «La alerta al receptor no depende del Wi-Fi del recinto ni de servicios externos (… ambigüedad 4)».
   - `firmware.md`: «La alerta al receptor va por ESP-NOW (ambigüedad 4…)».
   - El pitch: «no hace falta Wi-Fi».
   - El enunciado no dice qué es una «emergency alert». La etiqueta cita una ambigüedad sin resolver como si justificara la regla, y no hay plan B si la organización exige que la alerta llegue a un tercero.

9. **C3: el CLAUDE.md da fechas erróneas.**
   - «Evaluación 1 (hora exacta no especificada; el análisis la sitúa hacia las 14:00)». El enunciado sí la da: «02:00 PM – 08:00 PM · EVALUATION - 1».
   - «comienzo de la Ronda 2 presencial a las 11:00 (≈6 h de trabajo)». A las 11:00 empieza el registro; el hackathon empieza a las 14:00 («Formal Inauguration and Hackathon Begins»). Las 6 h solo salen contando desde las 14:00.
   - El origen está en `analisis.md`: «la Ronda 2 presencial empieza hoy a las 11:00». Es defendible en el análisis, pero en el CLAUDE.md pasa a leerse como hora de inicio del trabajo.

10. **C3: faltan las guías de pasos.**
    - El CLAUDE.md remite a «Guías de pasos: `.claude/skills/`», pero entre las salidas no hay ninguna.
    - El criterio exige que las guías cubran los momentos clave del reto: congelación, ensayo, medida de consumo, respuesta al On-Site Challenge.

11. **C3: reglas genéricas que no salen del reto.**
    - En `convenciones.md`, cuatro de las seis reglas son «(convención del kit)».
    - «Secretos solo en `.env` (nunca en `platformio.ini`…)» no viene a cuento: con ESP-NOW, sin nube ni servicios externos, no hay secretos.
    - La regla de IST está repetida en el CLAUDE.md (regla 9) y en `convenciones.md`.

12. **C3: una etiqueta de origen que exagera.**
    - CLAUDE.md, regla 2: «impacto, clasificador e inactividad posterior tienen que coincidir (enunciado: *"minimal false alarms"*)».
    - El enunciado pide pocas falsas alarmas. El mecanismo concreto de tres filtros es una decisión del equipo y debería ir etiquetado como «(decisión)».

13. **C2: etiqueta de ambigüedad mal aplicada.**
    - En el enfoque C: «depende de que se admitan dos plataformas en un mismo proyecto… (ambigüedad 9)».
    - La ambigüedad 9 pregunta si hay que declarar el track y si se puede cambiar, no si se pueden mezclar plataformas.
    - Hay además una incoherencia menor: Presentation & Documentation del enfoque A sale como «neutro» en el texto y como «medio» en la tabla.

14. **C5/C4: el pitch crea tareas que el plan no asigna.**
    - «20 alertas seguidas en la sala» (A), «autonomía estimada» y «coste de materiales (€)» (C) no aparecen en ningún bloque del plan.
    - El coste va en € en un evento en la India con premios en ₹.

15. **C1 (menor): una afirmación de obligación sin base en el problema.**
    - `analisis.md`: «la IA tiene que ejecutarse en el propio dispositivo». Lo apoya en una frase descriptiva del evento («embedded intelligence at the sensor node»).
    - El texto de BIO-06 no lo exige, y los criterios del Track 3 no mencionan la nube. Es razonable, pero se presenta como requisito.
    - Se arrastra a la regla 1 del CLAUDE.md y a `firmware.md`.

## C6: justificación
En general sí. A y B saben desde el minuto cero qué ficheros escriben (`colgante/src/contrato.h`, `datos/CONTRATO.md`, `captura.py`) y contra qué contrato (formato CSV, firma de `clasifica()`, struct ESP-NOW con ACK). Cada uno tiene una forma de desbloquearse que funciona: datos falsos y dataset público para B, un `clasifica()` por reglas con la misma firma para A. C llega con tareas claras.

Echo en falta tres cosas:
- **Quién crea el arranque del repositorio.** Nadie tiene asignada la creación de los proyectos PlatformIO ni de `arranca.py`, y la primera comprobación de A («Compila con `uv run arranca.py`») ya depende de ello.
- **Cómo llega el `modelo.h` al firmware.**
- **Una pregunta sobre el hardware más temprana.** Se plantea a las 14:15, cuando podía hacerse en el registro de las 11:00.

También falta un plan B si la organización exige que la alerta llegue a un tercero, y faltan las guías de pasos prometidas.

Sobran las convenciones genéricas del kit (los secretos en `.env`), tener el contrato duplicado en dos ficheros que «dicen lo mismo» y la sección de fechas del CLAUDE.md, que repite el horario con errores en vez de remitir a `equipo.md`.