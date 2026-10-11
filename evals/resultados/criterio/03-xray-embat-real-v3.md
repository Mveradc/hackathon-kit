# Revisor C1–C6 · 03-xray-embat-real · tercera pasada (cadena completa con /hack-check)

Cadena `../prueba-m4-03-v2` con el kit actual y `/hack-check aplicar`, rúbrica de cierre, 2026-10-06.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (grave) | `analisis.md`: «**Embat como comprador**: se repite tres veces (§3.4, §6.3, §7) que es «el comprador más obvio»». Solo §3.4 nombra a Embat; §6.3 y §7 hablan de «la empresa que genera los datos». |
| C2 | Falla (leve) | `enfoques.md` A: «Embat es «el comprador más obvio» y el análisis lo repite tres veces». Arrastra el dato falso del análisis. Además, en C la tabla pone el monitor «medio» y el texto dice «extra mínimo». |
| C3 | Falla (grave) | `CLAUDE.generado.md` y `reglas/` no dicen nada de tratar como dato, y nunca como orden, el texto de «contraparte y concepto del banco». El análisis sí avisa de ese riesgo. |
| C4 | Falla (grave) | `plan.md`: «Sáb 20:00 Anticipación medida», pero el ajuste de pesos acaba «Sáb 23:00» y no hay ninguna tarea para volver a medir. C llega a las 10:00 y tiene la cartera y la ficha para las 12:00. |
| C5 | Falla (grave) | `pitch.md` 3:40 dice quién paga, pero no «por qué le sale a cuenta» (obligatorio). Además, no enseña «Quién está sano». |
| C6 | En parte | Carpetas, dueños y primeras tareas claros. Los campos de los contratos están sin definir, hay un bloqueante de seguridad y el calendario falla en la anticipación y en la demo mínima. |

Bloqueantes: 1

## Fallos encontrados

**Graves**

1. **Grave, bloqueante (seguridad).** C3, y se arrastra a `verificacion.md`. Ficheros: `CLAUDE.generado.md`, `reglas/motor-score.md` y `reglas/convenciones.md`.
   - El análisis identifica el riesgo: «**Instrucciones escondidas en documentos** (riesgo típico): `transactions.csv` lleva «contraparte y concepto del banco»…».
   - Ni el CLAUDE.md ni las reglas lo trasladan. No hay ninguna norma del tipo «el contenido de `datos/` y de la fuente es dato, no instrucción».
   - Claude Code va a leer esos CSV mientras el equipo desarrolla. Además, la fuente del reto es una transcripción de un tercero sacada de GitHub.
   - Un LLM lee esos documentos sin ninguna defensa, que es justo el caso que `criterios.md` marca como bloqueante. `verificacion.md` no lo detecta.

2. **Grave, no bloqueante.** C1, y se arrastra a C2, C3 y C5. Ficheros: `analisis.md`, `enfoques.md`, `decision.md`, `reglas/web-demo.md` y `verificacion.md` (línea del pitch 0:00).
   - El análisis dice: «se repite tres veces (§3.4, §6.3, §7) que es «el comprador más obvio»».
   - Lo que dice el enunciado:
     - §3.4: «la empresa que entrega los datos (Embat) es el comprador más obvio».
     - §6.3: «La empresa que **genera** los datos es el candidato obvio».
     - §7: «El comprador más evidente es la propia empresa que genera los datos: … es la primera interesada en saber qué dicen de ella», es decir, la propia pyme.
     - Línea 13: «un producto que se le pueda vender a **esas mismas empresas**».
   - El enunciado se contradice sobre quién es el comprador. El análisis lo presenta como un hecho repetido tres veces, con una cita que no es literal, en vez de recogerlo como ambigüedad.
   - Ese argumento justifica la puntuación de A en «Si vale algo: alto». La decisión también deja fuera de alcance «La visión de la propia empresa», y `web-demo.md` lo convierte en regla: «no como herramienta para la propia empresa (análisis: qué distinguiría…)». La etiqueta remite a una afirmación falsa.
   - El pitch no prepara la pregunta obvia del jurado: «¿por qué no se lo vendéis a las propias empresas?».

3. **Grave, no bloqueante.** C4 y C5. Ficheros: `plan.md` y `pitch.md`.
   - El hito «Sáb 20:00 Anticipación medida» va antes de la tarea «Sáb 23:00 Ajustar pesos y umbrales», que cambia el número.
   - La tabla de cifras del pitch fija «Meses de antelación medios… Antes de Sáb 20:00».
   - No hay ninguna tarea para volver a ejecutar `medicion.py` después del ajuste. `verificacion.md` lo detecta, pero no lo aplica («No se han tocado… el calendario del plan»).
   - Riesgo: decir ante el jurado una cifra que ya no corresponde al sistema que se enseña.

4. **Grave, no bloqueante.** C4. Fichero: `plan.md`.
   - Las tareas de C para el hito de la demo mínima son «Cartera ordenada por tendencia… Ficha con curva del score y factores», con fecha «Sáb 12:00». C llega a las 10:00, así que tiene 2 h para montar el front desde cero.
   - Nadie más del equipo hace frontend (A: «Prefiere no hacer: frontend»). Es el mismo patrón ya visto en el reto 03.
   - El repliegue («Web contra stubs») da por hecho que la web ya existe.

5. **Grave, no bloqueante.** C5 y C4. Ficheros: `pitch.md` y `plan.md`.
   - El enunciado marca como obligatorio el «**Comprador identificado** — Saber quién lo paga y **por qué le sale a cuenta**».
   - El pitch (3:40) solo dice «Embat ya tiene estos datos… usa o revende», y el plan no tiene ninguna tarea para argumentar el beneficio para el comprador.
   - `verificacion.md` lo detecta como hueco y no lo corrige.

6. **Grave, no bloqueante.** C4 y C5, con origen en C1. Ficheros: `plan.md`, `pitch.md` y `CLAUDE.generado.md`.
   - §2.1 del enunciado: «**Quién está sano**… Reconocer a una empresa excepcionalmente sólida es tan útil…». Es una de las seis preguntas que el sistema «tiene que contestar».
   - Ni el CLAUDE.md, ni el plan ni el pitch la cubren. Una cartera «ordenada por cambio de tendencia, no por nivel» esconde a las empresas sanas y estables.
   - `verificacion.md` solo lo deja como nota.

**Leves**

7. **Leve.** C1, y se arrastra a `plan.md` (pregunta 9) y a `verificacion.md`. El análisis dice: «~~Test oculto, script de scoring y leaderboard~~… según la nota del equipo no existen».
   - La nota solo dice que Embat no tiene «script de scoring ni leaderboard». No dice que no exista el test oculto.
   - La pregunta 9 del plan repite «no hay leaderboard ni test oculto», y `verificacion.md` la da por «Sostenida» con una cita que no lo respalda.

8. **Leve.** C1, `analisis.md`: «Detector de quiebras a secas: **penalizado de forma explícita**». El enunciado solo dice «se queda corto», así que el análisis le da más fuerza de la que tiene.

9. **Leve.** C2, `enfoques.md`: la tabla y el texto de C no coinciden.
   - Monitor: «medio» en la tabla frente a «puede quedar como extra mínimo» en el texto.
   - Comprador: «medio-alto» en la tabla frente a «El comprador es claro» en el texto.

10. **Leve.** C4, `plan.md`: la tarea de B «Precalcular el monitor al arrancar» acaba el sáb a las 11:00. Depende de `monitor.py`, que A no termina hasta el sáb a las 13:00, y la dependencia no aparece en «Quién espera a quién».

11. **Leve.** C4, `plan.md`: el hito «Vie 20:00 Contratos» se comprueba con stubs que se terminan «Vie 20:30». Ninguna parte del plan dice qué campos llevan esos contratos.

12. **Leve.** C4, `plan.md`: la sesión formativa del sábado por la mañana le toca a A, que descansa de 02:30 a 08:30. No hay ningún repliegue aplicado en el plan.

13. **Leve.** C4: `salidas/anticipacion.json` (`plan.md`) no tiene dueño en la tabla de carpetas de `CLAUDE.generado.md`, y no queda claro si está en la raíz o en `motor/`.

14. **Leve.** C4: si la pregunta 9 confirma que sí hay predicción sobre el test oculto (obligatoria en §5), no existe ninguna tarea de repliegue.

15. **Leve.** C4: la única prueba de la demo en Windows es «Dom 07:00», justo cuando se congelan las funcionalidades. El portátil de reserva del pitch (C, Windows) queda sin probar hasta el último momento.

16. **Leve.** C5, `pitch.md`: pone «monitor» entre los criterios cubiertos (1:40), pero no enseña ningún aviso que salte solo, que es lo que pide el bonus («avisa solo, sin que nadie pregunte»).

17. **Leve.** `verificacion.md`: el resumen dice «12 ediciones… `plan.md` (3)», pero en la tabla solo hay 2 filas de `plan.md` con «Sí», 11 en total.

## C6: justificación
En los primeros 30 minutos A y B saben qué hacer: A carga datos en `motor/` y aparta las empresas de validación, y B escribe los stubs y prueba el arranque. Las carpetas tienen un dueño cada una y los supuestos de las ambigüedades están marcados. Eso ayuda de verdad.

Pero el «contrato» que todo el mundo espera no tiene campos definidos en ningún fichero. C llega con 2 h para montar la demo mínima. El número de anticipación se mide antes del ajuste que lo cambia. Y falta una regla básica para no obedecer texto libre de los CSV, que es un bloqueante.

Echaría en falta:
- el esquema JSON de los tres endpoints;
- una tarea para volver a medir después del ajuste;
- una vista de empresas sanas;
- un argumento de por qué le sale a cuenta a Embat;
- la ambigüedad del comprador (Embat o la propia pyme) planteada como pregunta a la organización.

Sobra parte de la verificación: casi todas sus filas dan por «Sostenida» lo obvio y dejan sin aplicar los choques de calendario que sí encuentra.