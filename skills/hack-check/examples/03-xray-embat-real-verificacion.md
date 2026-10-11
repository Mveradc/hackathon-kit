Fuente: evals/retos/03-xray-embat-real.md

> El fichero es una transcripción de un equipo participante, con una nota del equipo (19 sep) y un «Resumen ejecutivo» que no son de la organización. Se ha verificado contra ese texto y, en su defecto, contra `analisis.md` y `decision.md`.
>
> No se ha podido preguntar al usuario (sesión no interactiva): **no se ha cambiado ningún fichero**. `/hack-check aplicar` aplica los cambios de texto y las filas y cambios de calendario propuestos.

## Bloqueantes

| Qué | Dice el enunciado (cita) | Dice <fichero> | Qué hacer | ¿Aplicado? |
|---|---|---|---|---|
| Predicción sobre el test oculto: obligatoria en la tabla de requisitos; solo la anula una nota de otro equipo | «Predicción sobre el test oculto», marcada «Obligatorio» en la tabla de requisitos y, en la nota del equipo, «Las filas «Predicción sobre el test oculto» y «leaderboard» de este enunciado quedan sin efecto; todo lo demás sigue vigente.» | `docs/contratos.md`: «predicción sobre el test oculto \| — \| **no** \|». `CLAUDE.md` («Qué puntúa»): «El test oculto quedó sin efecto…», pero la regla 12 dice que ante conflicto «manda el enunciado y se pregunta a Embat». `plan.md`: ninguna pregunta ni tarea sobre el test oculto. | 1) En `docs/contratos.md`, cambiar «Obligatorio» de `no` a `por confirmar` y el origen a `supuesto: nota no oficial del 19 sep, confirmar con la organización` (avisar al equipo antes, según `convenciones.md`). 2) **Fila propuesta en `plan.md` › Preguntas a la organización:** `\| Test oculto · ¿Existen el test oculto, el script de scoring y el leaderboard («disponibles desde el viernes»)? Es obligatorio en el enunciado y solo lo anula la nota de otro equipo \| C \| Vie 20:00 \|`. 3) **Fila propuesta en `plan.md` › A:** `\| Sáb 22:00 \| Test oculto \| Si Embat confirma que existe: puntuar las empresas ocultas y entregarlas por su canal \| Hay acuse o puntuación en el leaderboard \|`. | No (sin confirmación) |

Comprobaciones sin bloqueante:
- **Resto de requisitos obligatorios** (dos direcciones, trayectoria, explicación, producto, comprador, demo navegable): están igual en el análisis, el `CLAUDE.md`, las reglas y las guías, tienen tarea con dueño antes de la entrega y el pitch no los contradice.
- **Fecha de entrega**: el enunciado no la da. La hora del domingo a las 10:00 sale de `equipo.md`, y la ambigüedad 5 tiene dueño (C) y límite (vie 20:00).
- **Trabajo previo**: el enunciado no exige que el código se cree durante el evento. No aplica. Aviso: el `CLAUDE.md` no tiene fecha de generación, y los ficheros tienen fecha del 10 oct 2026, después del evento (18–20 sep).
- **Inscripción, consentimientos, presencia y tamaño del equipo**: el enunciado no fija ninguna condición.

## Afirmaciones

| Fichero | Afirmación (resumida) | Veredicto | Cita literal | Fuente de la cita |
|---|---|---|---|---|
| CLAUDE.md · Qué puntúa | Obligatorio: dos direcciones, trayectoria, explicación, producto, comprador y demo navegable; el notebook local no cuenta | Sostenida | «Un notebook que solo corre en el portátil **no cuenta**.» | enunciado |
| CLAUDE.md · Qué puntúa | El test oculto quedó sin efecto según una nota no oficial | Sostenida (como nota); ver bloqueante | «Las filas «Predicción sobre el test oculto» y «leaderboard» de este enunciado quedan sin efecto; todo lo demás sigue vigente.» | enunciado |
| CLAUDE.md · Qué puntúa | Tres bloques con el mismo peso y sus partes | Sostenida | «Tres bloques con el **mismo peso**: si acierta, si llega a tiempo y si vale algo.» | enunciado |
| CLAUDE.md · Qué puntúa | Según la nota, Embat valora «sobre todo el producto» | Sostenida (como nota) | «Embat confirmó que no tiene script de scoring ni leaderboard y que valora sobre todo el producto construido encima del score.» | enunciado |
| CLAUDE.md · Qué puntúa | Bonus: anticipación medida y monitor que avisa | Sostenida | «Enseñar cuántos meses antes detecta el cambio, no solo que lo detecta.» (estado: «Bonus») | enunciado |
| CLAUDE.md · Qué puntúa | Frase guía | Sostenida | «Un modelo sencillo con un producto claro encima interesa más que uno sofisticado que se queda en el número.» | enunciado |
| CLAUDE.md · Fechas | Evento: 18–20 sep 2026, ETSIT UPM, Madrid «(análisis)» | Sostenida; la etiqueta pasa a `(enunciado)` | «**Evento:** HackSpain 2026 · 18–20 de septiembre · ETSIT UPM, Madrid» | enunciado |
| CLAUDE.md · Fechas | Inicio: viernes 18 sep, 19:00 | Supuesto: la hora sale de `equipo.md`, no de la fuente → «hasta que la organización confirme, inicio el vie 18 sep 2026 a las 19:00 (supuesto: horas de hacking no especificadas, confirmar con la organización)» | «Horas de hacking y hora de cierre: **No especificado**.» | analisis.md |
| CLAUDE.md · Fechas | Entrega: domingo 20 sep, 10:00 | Supuesto (ya lo indica, pero sin el formato) → «(supuesto: ambigüedad 5, confirmar con la organización)» | «Fecha y hora de entrega, repositorio, vídeo o documento: **No especificado**.» | analisis.md |
| CLAUDE.md · Fechas | Sesión formativa el sábado por la mañana «(análisis)» | Sostenida; la etiqueta pasa a `(enunciado)` | «El **sábado por la mañana**, media hora sobre cómo se mueve de verdad el dinero dentro de una empresa: de dónde sale cada fichero y qué significa.» | enunciado |
| CLAUDE.md · Fechas | Pitch de 5 minutos «(inferido, ambigüedad 6)» | Supuesto: se reescribe a «(supuesto: ambigüedad 6, confirmar con la organización)» | «Que el pitch dure 5 minutos es (inferido): el resumen del equipo lo da por hecho, pero el enunciado no lo dice así.» | analisis.md |
| CLAUDE.md · regla 1 | Ningún score sin curva de 24 meses, tendencia y desglose «(enunciado; decisión)» | Sostenida; la etiqueta mezcla fuentes y pasa a `(decisión)` | «curva de 24 meses, flecha de tendencia, desglose «qué lo movió este mes» (caja, cobros, deuda)» | decision.md |
| CLAUDE.md · regla 2 | El mismo cálculo sube y baja; la demo abre 45→65 y 82→68 «(enunciado; decisión)» | Sostenida; la etiqueta mezcla fuentes y pasa a `(decisión)` | «abrir una empresa que mejora (tipo 45→65) y otra que cae con buen nivel (tipo 82→68)» | decision.md |
| CLAUDE.md · regla 3 | Un bache de un mes no cambia la tendencia; score suavizado | Sostenida | «Un score que oscile con la caja de cada mes penaliza.» | analisis.md |
| CLAUDE.md · regla 4 | Cada acción sale de una regla y cita su cifra | Sostenida | «parecer «solo un dashboard» si las acciones son genéricas» | decision.md |
| CLAUDE.md · regla 5 | LLM: datos delimitados y respaldo sin LLM «(análisis: riesgo típico; decisión)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «Si un LLM los lee (por ejemplo, en un «agente de recomendaciones»), alguno podría contener texto que parezca una orden.» | analisis.md |
| CLAUDE.md · regla 6 | UTF-8 «(análisis: riesgo típico)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «con riesgo de que se rompan en Windows si no se lee en UTF-8.» | analisis.md |
| CLAUDE.md · regla 7 | `YYYY-MM`; 25 meses nominales frente a 24 «(análisis: riesgo típico)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «El rango «septiembre de 2024 a septiembre de 2026» suma 25 meses nominales frente a los «24 meses» anunciados.» | analisis.md |
| CLAUDE.md · regla 8 | Una ficha por `company_id` | Supuesto (bien marcado) | «**¿El score es por empresa (1.286) o por grupo (250)?**» | analisis.md |
| CLAUDE.md · regla 9 | Score de 0 a 100 | Supuesto (bien marcado) | «**¿Escala de 0 a 100?**» | analisis.md |
| CLAUDE.md · regla 10 | No se suman monedas distintas | Supuesto (bien marcado) | «**¿Cómo se tratan las varias monedas?**» | analisis.md |
| CLAUDE.md · regla 11 | No se dice «acertado» sin validación propia | Supuesto (bien marcado) | «**¿Existe alguna etiqueta o «verdad» de salud financiera en los datos?**» | analisis.md |
| CLAUDE.md · regla 12 | La nota y el resumen no son oficiales; manda el enunciado | Sostenida (choca con «Qué puntúa»: ver bloqueante) | «Es fácil mezclar texto oficial, nota y resumen.» | analisis.md |
| CLAUDE.md · Fuera de alcance | Cartera, alertas, backtest y grupo «(decisión)» | Sostenida | «**Qué se deja fuera**: vista de cartera, alertas automáticas, backtest de anticipación, consolidación por grupo.» | decision.md |
| CLAUDE.md · Despliegue | «la demo tiene que abrirse por URL (enunciado)» | Supuesto: el enunciado pide una demo navegable, no una URL → «hasta que la organización confirme la forma de entrega, la demo se abre por URL (supuesto: ambigüedad 5, confirmar con la organización)» | «Algo que se abra y se pruebe delante del jurado.» | enunciado |
| convenciones.md | Idioma, nombres, commits, secretos, `.hackathon/` y avisos de contrato «(convención del kit)» | Sostenida (seis viñetas) | — (convención del kit, no es del reto) | — |
| convenciones.md | El dataset no va a git porque la licencia no está especificada | Sostenida. Aviso: el enunciado dice «Nueve ficheros CSV», pero su tabla lista ocho | «Licencia y uso de los datos fuera del evento: **No especificado**.» | analisis.md |
| convenciones.md | UTF-8 «(análisis: riesgo típico)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «con riesgo de que se rompan en Windows si no se lee en UTF-8.» | analisis.md |
| datos-y-score.md | UTF-8 y unión por `company_id` «(análisis: recursos disponibles; riesgo típico)» | Sostenida; se parte en dos: UTF-8 `(riesgo típico)` / unión por `company_id` `(enunciado)` | «Su `company_id` es la clave que cruza todos los demás ficheros.» | enunciado |
| datos-y-score.md | Score por `company_id`, sin mezclarlo con el del holding | Supuesto (bien marcado) | «**¿El score es por empresa (1.286) o por grupo (250)?**» | analisis.md |
| datos-y-score.md | Monedas sin sumar; `moneda` de `companies.csv` | Supuesto (bien marcado) | «**¿Cómo se tratan las varias monedas?**» | analisis.md |
| datos-y-score.md | `YYYY-MM`; `balances` es una foto a 1-sep-2026 «(análisis: riesgo típico; recursos disponibles)» | Sostenida; se parte en dos: fechas `(riesgo típico)` / `balances` `(enunciado)` | «Saldo de cada cuenta y producto a **1 de septiembre de 2026**, la foto final.» | enunciado |
| datos-y-score.md | Ventana de 24 meses fijada en contratos «(análisis: riesgo típico)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «El rango «septiembre de 2024 a septiembre de 2026» suma 25 meses nominales frente a los «24 meses» anunciados.» | analisis.md |
| datos-y-score.md | Score suavizado «(análisis: riesgos y trampas, bache frente a caída)» | Sostenida; la etiqueta pasa a `(análisis: riesgos y trampas)` | «Un score que oscile con la caja de cada mes penaliza.» | analisis.md |
| datos-y-score.md | El mismo cálculo sube y baja «(enunciado; decisión)» | Sostenida; la etiqueta pasa a `(decisión)` | «abrir una empresa que mejora (tipo 45→65) y otra que cae con buen nivel (tipo 82→68)» | decision.md |
| datos-y-score.md | Desglose caja, cobros y deuda | Sostenida | «desglose «qué lo movió este mes» (caja, cobros, deuda)» | decision.md |
| datos-y-score.md | Escala 0–100 | Supuesto (bien marcado) | «**¿Escala de 0 a 100?**» | analisis.md |
| datos-y-score.md | No se habla de «precisión» sin validación | Supuesto (bien marcado) | «**¿Existe alguna etiqueta o «verdad» de salud financiera en los datos?**» | analisis.md |
| ficha-y-acciones.md | La ficha muestra juntos score, curva, flecha y desglose | Sostenida | «curva de 24 meses, flecha de tendencia, desglose «qué lo movió este mes» (caja, cobros, deuda)» | decision.md |
| ficha-y-acciones.md | 2–3 acciones por regla y con cifra | Sostenida | «2–3 acciones sugeridas a partir de reglas (p. ej. «tus cobros se alargan 12 días»)» | decision.md |
| ficha-y-acciones.md | Texto para el CFO o tesorero | Sostenida | «Es para el CFO o tesorero de las empresas cliente; el comprador es Embat, que lo ofrece como módulo a sus clientes.» | decision.md |
| ficha-y-acciones.md | LLM: concepto y contraparte como datos «(análisis: riesgo típico)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «Si un LLM los lee (por ejemplo, en un «agente de recomendaciones»), alguno podría contener texto que parezca una orden.» | analisis.md |
| ficha-y-acciones.md | La demo no depende de un LLM en vivo «(análisis: riesgo típico; decisión)» | Sostenida; la etiqueta pasa a `(riesgo típico)` | «Si se usa un LLM en la demo en vivo, las cuotas, la latencia o el coste pueden fallar justo delante del jurado.» | analisis.md |
| ficha-y-acciones.md | «La demo se abre por URL en un navegador; un notebook local no cuenta (enunciado)» | Supuesto en parte; se parte en dos: «La demo se abre y se prueba delante del jurado; un notebook que solo corre en el portátil no cuenta (enunciado)» / «Hasta que la organización confirme la forma de entrega, se abre por URL en un navegador (supuesto: ambigüedad 5, confirmar con la organización)» | «Algo que se abra y se pruebe delante del jurado.» | enunciado |
| ficha-y-acciones.md | Dos clics a las dos empresas de la demo | Sostenida (el «dos clics» es un detalle del plan) | «abrir una empresa que mejora (tipo 45→65) y otra que cae con buen nivel (tipo 82→68)» | decision.md |
| ficha-y-acciones.md | Importes con su moneda | Supuesto (bien marcado) | «**¿Cómo se tratan las varias monedas?**» | analisis.md |
| ficha-y-acciones.md | Northbrook y Velasco son ejemplos, no datos | Sostenida | «**El ejemplo es ilustrativo**: Northbrook y Velasco no tienen por qué estar en el dataset.» | analisis.md |
| skills/ensayo-demo | «el pitch dura 5 minutos (inferido, ambigüedad 6)» | Supuesto: inferencia escrita como hecho → «hasta que la organización confirme, se ensaya para 5 minutos (supuesto: ambigüedad 6, confirmar con la organización)» | «Que el pitch dure 5 minutos es (inferido): el resumen del equipo lo da por hecho, pero el enunciado no lo dice así.» | analisis.md |
| skills/ensayo-demo | Qué está en juego: «si en cinco minutos no se ve…» | Sostenida | «Por muy buena que sea la señal que se encuentre, si en cinco minutos no se ve a quién se le vende y por qué, se queda a medias.» | enunciado |
| skills/ensayo-demo | Paso 3: «mostrando que se detecta antes de que sea evidente» | Quitar la cláusula: afirma una anticipación que el plan no mide y que la decisión deja fuera (choca con la regla 11 y con la respuesta del pitch «No lo hemos medido») | «la anticipación medida y el monitor no son el foco.» | decision.md |
| skills/entrega | Entrega el dom 20 sep a las 10:00, sin confirmar | Supuesto (bien marcado) | «Fecha y hora de entrega, repositorio, vídeo o documento: **No especificado**.» | analisis.md |
| skills/entrega | Artesanía: «que la demo se abra y se pruebe» | Sostenida | «Y que la demo se abra y se pruebe.» | enunciado |
| skills/entrega | Comprobación: «La demo se abre por URL» | Supuesto → «(supuesto: ambigüedad 5, confirmar con la organización)» | «**¿Cuándo y cómo se entrega?** Hora límite, URL de la demo, repositorio, ¿hace falta un deploy público?» | analisis.md |
| docs/contratos.md · entrada | 9 CSV + JSON + diccionario; 1.286 empresas en 250 grupos; sep-2024 a sep-2026 | Sostenida | «**1.286 empresas sintéticas** agrupadas en **250 grupos empresariales**.» | enunciado |
| docs/contratos.md · entrada | Los ficheros: lista de ocho nombres | Sostenida. Aviso: el enunciado dice «Nueve ficheros CSV» y lista ocho; falta uno o el recuento está mal (preguntar en la sesión formativa) | «**Nueve ficheros CSV** (también disponible en JSON) + diccionario de datos.» | enunciado |
| docs/contratos.md · entrada | `company_id` es la clave común | Sostenida; el origen pasa a `enunciado` | «Su `company_id` es la clave que cruza todos los demás ficheros.» | enunciado |
| docs/contratos.md · entrada | Columnas `país` y `moneda` | Supuesto: el enunciado dice que esos datos existen, pero no cómo se llama la columna → origen «supuesto: nombre exacto en `data_dictionary.md`, confirmar con la organización» | «Una empresa por fila: grupo, país, moneda, ERP y fecha de alta.» | enunciado |
| docs/contratos.md · entrada | Concepto del banco y contraparte: texto libre, con tildes y texto con forma de orden | Sostenida; lo de las tildes es (inferido) en el análisis → origen `riesgo típico` | «Movimientos bancarios de los 24 meses: fecha, importe, categoría, estado de conciliación, contraparte y concepto del banco.» | enunciado |
| docs/contratos.md · entrada | `balances`: foto a 1-sep-2026 | Sostenida | «Saldo de cada cuenta y producto a **1 de septiembre de 2026**, la foto final.» | enunciado |
| docs/contratos.md · entrada | Ventana de meses y UTF-8 | Sostenida (riesgo típico) | «El rango «septiembre de 2024 a septiembre de 2026» suma 25 meses nominales frente a los «24 meses» anunciados.» | analisis.md |
| docs/contratos.md · ficha | `company_id`, `moneda` y `score` 0–100 | Supuestos (bien marcados: ambigüedades 3, 8 y 7) | «**¿Escala de 0 a 100?**» | analisis.md |
| docs/contratos.md · ficha | `tendencia`, `curva`, `desglose` y `acciones` | Sostenida | «curva de 24 meses, flecha de tendencia, desglose «qué lo movió este mes» (caja, cobros, deuda)» | decision.md |
| docs/contratos.md · entrega | La recibe el jurado; el canal está por confirmar | Sostenida | «Algo que se abra y se pruebe delante del jurado.» | enunciado |
| docs/contratos.md · entrega | Demo navegable de tipo «URL» «(enunciado)» | Supuesto en el formato: el origen pasa a «enunciado; URL: supuesto, ambigüedad 5, confirmar con la organización» | «Algo que se abra y se pruebe delante del jurado.» | enunciado |
| docs/contratos.md · entrega | Producto, comprador y explicación son obligatorios | Sostenida | «Saber quién lo paga y por qué le sale a cuenta.» | enunciado |
| docs/contratos.md · entrega | Pitch de 5 min; repositorio, vídeo y documento | Supuestos (bien marcados) | «Fecha y hora de entrega, repositorio, vídeo o documento: **No especificado**.» | analisis.md |
| docs/contratos.md · entrega | Predicción sobre el test oculto: obligatorio «no» | Quitar el «no» y poner «por confirmar» (contradice la tabla del enunciado; ver bloqueante) | «Predicción sobre el test oculto», marcada «Obligatorio» en la tabla de requisitos | enunciado |
| plan.md | 39 horas, del vie a las 19:00 al dom a las 10:00 | Supuesto (sale de `equipo.md`) → añadir «(supuesto: ambigüedad 5, confirmar con la organización)» | «Horas de hacking y hora de cierre: **No especificado**.» | analisis.md |
| plan.md | Sesión formativa el sábado por la mañana | Sostenida | «El **sábado por la mañana**, media hora sobre cómo se mueve de verdad el dinero dentro de una empresa: de dónde sale cada fichero y qué significa.» | enunciado |
| plan.md | Demo por URL (ambigüedad 5) | Supuesto (bien marcado) | «**¿Cuándo y cómo se entrega?** Hora límite, URL de la demo, repositorio, ¿hace falta un deploy público?» | analisis.md |
| plan.md | Ensayo «≤ 5 min (inferido, ambigüedad 6)» | Supuesto → formato «(supuesto: ambigüedad 6, confirmar con la organización)» | «Que el pitch dure 5 minutos es (inferido): el resumen del equipo lo da por hecho, pero el enunciado no lo dice así.» | analisis.md |
| plan.md | Entrega final, límite a las 10:00 | Supuesto → añadir «(supuesto: ambigüedad 5, confirmar con la organización)» | «Fecha y hora de entrega, repositorio, vídeo o documento: **No especificado**.» | analisis.md |
| plan.md | 1.286 empresas × 24 meses | Sostenida | «**1.286 empresas sintéticas** agrupadas en **250 grupos empresariales**.» | enunciado |
| plan.md | Plataforma de despliegue | Conocimiento externo (bien marcado) | — | — |
| plan.md | Las respuestas de Embat se piden el viernes | Sostenida | «Dos ingenieros rotando en el aula todo el fin de semana y un especialista de datos localizable de noche.» | enunciado |
| plan.md | C: «Guion de 5 min» (sáb 19:00) | Supuesto: inferencia sin marca → «Guion de 5 min (supuesto: ambigüedad 6, confirmar con la organización)» | «Que el pitch dure 5 minutos es (inferido): el resumen del equipo lo da por hecho, pero el enunciado no lo dice así.» | analisis.md |
| plan.md | Empresas tipo 45→65 y 82→68 | Sostenida | «Una empresa que pasa de 45 a 65 puede tener números mediocres hoy y ser la mejor apuesta del año que viene.» | enunciado |
| plan.md | Preguntas a la organización: ambigüedades 1 a 8 | Sostenida (falta la del test oculto: ver bloqueante) | «**¿Cuándo y cómo se entrega?** Hora límite, URL de la demo, repositorio, ¿hace falta un deploy público?» | analisis.md |
| pitch.md | 5 min (inferido) [CONFIRMAR] | Supuesto (bien marcado) | «Que el pitch dure 5 minutos es (inferido): el resumen del equipo lo da por hecho, pero el enunciado no lo dice así.» | analisis.md |
| pitch.md · 0:00 | «Embat ya tiene el rastro de banco, facturas y deuda de sus clientes» | Conocimiento externo: la fuente dice que Embat entrega los datos, no que sean de sus clientes → «(conocimiento externo, verificar)» | «**Pista: la empresa que entrega los datos (Embat) es el comprador más obvio.**» | enunciado |
| pitch.md · 0:40 y 1:40 | Una empresa sube y otra cae con el mismo cálculo | Sostenida | «abrir una empresa que mejora (tipo 45→65) y otra que cae con buen nivel (tipo 82→68)» | decision.md |
| pitch.md · 2:40 | Tres señales, score suavizado y modelo sencillo | Sostenida | «La estabilidad sale bien con el suavizado» | decision.md |
| pitch.md · 3:40 | Embat, «el comprador más obvio», lo ofrece como módulo | Sostenida | «**Pista: la empresa que entrega los datos (Embat) es el comprador más obvio.**» | enunciado |
| pitch.md · 4:30 | Cierre con la frase guía | Sostenida | «Un modelo sencillo con un producto claro encima interesa más que uno sofisticado que se queda en el número.» | enunciado |
| pitch.md · Preguntas | «No lo llamamos «acertado»: no hay etiqueta (ambigüedad 2)» | Supuesto: la ambigüedad 2 sigue abierta → «no hemos encontrado etiqueta y está pendiente de confirmar con Embat (ambigüedad 2)» | «**¿Existe alguna etiqueta o «verdad» de salud financiera en los datos?**» | analisis.md |
| pitch.md · Preguntas | La anticipación no se ha medido; el backtest quedó fuera | Sostenida | «**Qué se deja fuera**: vista de cartera, alertas automáticas, backtest de anticipación, consolidación por grupo.» | decision.md |
| pitch.md · Preguntas | Bache: suavizado | Sostenida | «La estabilidad sale bien con el suavizado» | decision.md |
| pitch.md · Preguntas | No es un dashboard: cada acción cita una cifra | Sostenida | «parecer «solo un dashboard» si las acciones son genéricas» | decision.md |
| pitch.md · Preguntas | Embat, «el comprador más obvio»; el precio no está validado | Sostenida | «**Pista: la empresa que entrega los datos (Embat) es el comprador más obvio.**» | enunciado |
| pitch.md · Preguntas | Grupos y monedas: supuestos pendientes | Sostenida (como supuestos) | «**¿El score es por empresa (1.286) o por grupo (250)?**» | analisis.md |

Ninguna fila aplicada.

Aviso fuera del enunciado: `pitch.md` da a A cuatro respuestas del jurado, pero `equipo.md` dice que A «Presenta el pitch o la defensa: no». Decide el equipo: o A está en el turno de preguntas, o esas respuestas pasan a B o a C.

## Hitos antes que sus dependencias

| Hito | Depende de | Choque | Cambio propuesto | ¿Aplicado? |
|---|---|---|---|---|
| Sáb 20:00 · Entrega temprana (C) | C · README con la URL y el comprador, hasta sáb 22:00; la guía `entrega` exige el comprador «en la demo o en el README» | La tarea acaba 2 h después del hito que la necesita | Mover el hito a **sáb 22:30** (C está disponible hasta las 23:00) | No |
| Vie 20:00 · Contratos «sin TODO en … meses» (A) | A · Cargar los CSV en una tabla mensual, hasta vie 23:30. Hace falta ver los datos para decidir qué 24 de los 25 meses se usan | Se comprueba la ventana de meses antes de haber cargado los datos | Dejar el hito de vie 20:00 solo para la ficha y comprobar «sin TODO en meses» a las **vie 23:30**, junto a la tarea de datos de A | No |
| Dom 07:00 · Ensayo 1 (C) | Las respuestas del jurado asignadas a A en `pitch.md` | A descansa de dom 05:00 a 08:00 | Ensayar las preguntas en el ensayo 2 (dom 08:30, con A despierta) o pasarlas a B o C | No |

## Referencias sin tarea

| Fichero | Referencia | Qué se ha hecho |
|---|---|---|
| pitch.md («Antes de empezar», «Si falla la demo») y plan.md (repliegue del hito de sáb 16:00) | Vídeo grabado de la ficha o de las dos fichas | Ninguna tarea lo graba. Propuesta: marcarlo `[SI DA TIEMPO]` en el pitch o añadir una tarea (por ejemplo, B hasta dom 05:00). Sin aplicar |
| plan.md / pitch.md | `pitch/guion.md` y las diapositivas en `pitch/` | No existen todavía, pero tienen tarea (C, sáb 19:00). Correcto |
| plan.md | `datos/` (dataset de Embat) | No existe todavía; lo entrega la organización y lo carga A (vie 23:30). Correcto |

## Cobertura de la rúbrica

| Criterio | Lo que pide (cita) | Plan | Pitch |
|---|---|---|---|
| Si acierta · Generalización | «¿Funciona en las empresas que no ha visto nunca?» | Solo una tarea condicional («Si Embat pide validación propia»), sin pregunta sobre el test oculto | El bloque 2:40 dice que cubre la generalización, pero no la menciona; la respuesta está en `[SI DA TIEMPO]` |
| Si llega a tiempo · Anticipación | «Cuántos meses antes, **medido**.» | Sin tarea (fuera de alcance por decisión) | Sin bloque; solo «No lo hemos medido» |
| Si llega a tiempo · Monitor (puntos extra) | «Puntos extra si además avisa solo, sin que nadie pregunte.» | Sin tarea (fuera de alcance) | Sin bloque |
| Si vale algo · Comprador | «¿Se sabe quién lo paga y por qué le sale a cuenta?» | README con el comprador (C), pero sin tarea sobre por qué le sale a cuenta | Se dice quién paga; el «por qué le sale a cuenta» se queda en «ya tiene los datos» |
| (§2, pregunta 1) Quién está sano | «Reconocer a una empresa excepcionalmente sólida es tan útil como detectar a la que se hunde.» | Sin tarea: la demo solo elige una empresa que mejora y otra que cae | Sin bloque |
| Predicción sobre el test oculto | Obligatoria en la tabla de requisitos; solo la anula una nota no oficial | Sin tarea ni pregunta | Sin mención |

## Resumen

- Afirmaciones revisadas: 92. Sostenidas: 59 (16 con la etiqueta por corregir). Supuestos bien marcados: 15. Rebajadas a supuesto: 14. Conocimiento externo: 1 ya marcado y 1 nuevo. Para quitar: 2. Ninguna aplicada.
- Bloqueantes: 1 (predicción sobre el test oculto), con 2 filas propuestas para `plan.md` y un cambio en `docs/contratos.md`.
- Choques de calendario: 3, ninguno aplicado.
- Referencias sin tarea: 1 (el vídeo de respaldo).
- Huecos de cobertura: 6.
