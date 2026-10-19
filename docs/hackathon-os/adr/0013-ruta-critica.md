# ADR-0013 · Ruta crítica: de dónde salen dependencias, horas y ritmo, cómo se dice la incertidumbre y qué se hace sin datos

Estado: **aceptada** (2026-10-19, por el usuario al decidir la tabla del PR #42 y las preguntas del issue #41, «M10, Paso 0»). Contratos en `api.md` §11 y `estado.schema.json` (K-101). El interruptor es la decisión 8 de ADR-0012. Ajustada el mismo día con las decisiones del issue #46 (abajo, «Ajustes tras la revisión»).

## Contexto
R-36: «DONDE la ruta crítica esté activa, el sistema DEBE estimar, con las dependencias y el ritmo real, si se llega a la entrega y qué tareas la ponen en riesgo». Lo que hay hoy (inventario del issue #41, §2, §3 y §6):
- **Dependencias:** solo las de «Quién espera a quién», que llegan a `estado.json` como `depende_de`. En el plan del reto 03, solo **6 de 28** tareas tienen alguna: la cadena real es la de cada persona (un dueño por carpeta y sus filas en orden).
- **Horas:** el plan no tiene duraciones. Tiene un **plazo** por fila, `Hasta`, en texto libre (`vie 19:45`, `VIE 23:00`, `H+2` si no se sabe el inicio; una celda vacía hereda la de arriba). Está en el cuerpo del issue, pero **no llega a `estado.json`**.
- **Entrega:** en hasta cinco sitios, todos declarados y en texto libre (`equipo.md`, cabecera e Hitos del plan, `CLAUDE.md`, análisis, una nota de fuerza `dato`), que no siempre coinciden (02: «10:00 (cierre 11:00)»).
- **Ritmo:** `estado.json` es solo el presente (en `en_curso`, `observado_en` es la última actividad, no el inicio). Pero el relay guarda todos los eventos y `modelo.calcular(…, ahora)` es puro, así que **la historia de transiciones se puede reconstruir** (comprobado con G2 y G3 en el Paso 0).
- **Datos reales: ninguno.** Los guiones duran minutos y el ensayo sigue aplazado. Un commit sin `Txx` (con más de una tarea abierta) no hace avanzar ninguna tarea.

Valen la constitución II, III, IV y X (una hora estimada que se mueve con el reloj no puede inyectar nada) y ADR-0009.

## Decisión (común)
- **Detrás de su interruptor**, `ruta_critica:` en `os.md` (ADR-0012, decisión 8A). Apagado, todo como en la 0.4.0 (constitución I).
- **Dónde se calcula:** el relay pone en `estado.json` lo que lee (plazos resueltos, franjas, orden del plan, entrega, hitos, descansos e historia de transiciones por tarea) y `proyeccion.vista` calcula el bloque `ruta`. La web solo lo pinta. El cálculo es una función pura con su tabla de casos (`hkos/ruta.py`), con `ahora` como parámetro, como el motor de estados.
- **El objetivo es la entrega**, no la congelación: el margen se mide contra la hora de `Entrega:`. La congelación y los demás hitos del plan salen como marcas en la vista (declarados, con «pasado» o no), sin previsión propia. Porque la entrega es lo único que el reto exige; la congelación la pone el equipo y puede moverla.
- **Hechos aparte de estimaciones.** La vista separa:
  - **hechos** (derivados y comprobables), desde el minuto uno: «T05: su plazo pasó a las 02:30 y sigue en curso», con lo que arrastra por sus dependencias y por el orden del plan; las tareas `parada` o `no_cerrada` de la cadena; las personas sin señales; un ciclo;
  - **la estimación**, que siempre lleva la palabra «estimación», su base (cuántas tareas medidas por persona y desde cuándo), un **rango** y nunca una sola hora, la hora en que se calculó y la antigüedad de su dato más viejo.
- **Colores:** el **rojo es solo para hechos** (un plazo que ya ha pasado). «No llega» es una previsión: **ámbar**, como «justo». «Sin estimación» es gris.
- **Sin estimación, y lo dice**, solo cuando:
  - `equipo.md` no tiene `- Entrega:`, no se puede leer, o esa línea no se puede resolver a una hora: «sin hora de entrega». Si trae dos horas («10:00 (cierre 11:00)»), manda la primera y la otra se enseña al lado (ajuste 5);
  - las dependencias tienen un ciclo: «ciclo T04 → T07 → T04»;
  - alguna persona con tareas abiertas tiene menos de 3 tareas medidas (decisión 7);
  - ninguna tarea abierta que cuenta tiene franja: «sin plazo: T28» (tras congelar, 2026-10-19, M10, ajuste 2).
- **Sin plazo no es «a tiempo».** Una tarea con `Hasta` vacío o sin resolver sale en una lista aparte, «sin plazo», con su motivo, y no cuenta como a tiempo ni como atrasada. Si alguna otra tarea abierta tiene franja, **no quita la estimación** (ajuste 1, issue #46): el resto se estima y el resumen lo dice («sin contar T28 (sin plazo)»). Si ninguna la tiene, no hay estimación (tras congelar, 2026-10-19, M10, ajuste 2).
- **Sin señales no es lento.** Si una persona no deja señales (commits sin ID, `atribucion_ambigua`, sin OS), la vista dice «sin señales de @x desde HH:MM» (gris) y enseña al lado sus `sin_tarea` y discrepancias; nunca «@x va lenta». No hay ningún hecho de tipo «lentitud».
- **Lo declarado, como declarado:** `Hasta`, la franja, el orden del plan, la entrega, los hitos y los descansos salen del plan o de `equipo.md` y llevan su procedencia y la hora del commit de ese fichero (como `servicios`). Una tarea `cerrada` a mano cuenta como hecha para la ruta, con su ⚑, pero no se mide para el ritmo.
- **Horas con zona:** toda hora sale con la zona horaria de `equipo.md`. Los `ts` de los commits son del reloj del portátil.
- **Viejo:** sin relay o sin GitHub, la estimación sale vieja, con la antigüedad de su dato más viejo (III, R-12).
- **Prueba doble de ADR-0009:** `igualdad.py` con el guion nuevo **G14** (ruta), y Vitest pinta G14.

## Decididas (2026-10-19)

| Decisión | Elegida | Por qué |
|---|---|---|
| **1. Hora de entrega** | **A.** Manda `- Entrega:` de `equipo.md` (declarado). La fila «Entrega» de Hitos y las notas de fuerza `dato` que afectan a la entrega se comparan: si no coinciden, se enseñan **al lado**, como discrepancia, sin elegir, y **no quitan la estimación**. Sin estimación solo si `equipo.md` no tiene `Entrega:`, no se puede leer, o esa línea trae dos horas o no se puede resolver. Con «(confirmar)», hay estimación, marcada como declarada con «(confirmar)» | Ya existe, con formato y zona horaria, y el relay ya tiene `origin/main`. Una sola fuente que manda evita que la vista elija entre dos textos; las otras se ven para que el equipo corrija la que esté mal (el patrón 8 de los evals: fechas que se contradicen en 3 de 5 retos). Que una discrepancia apagara la estimación la dejaría sin cifra justo en los retos que más la necesitan |
| **2. `Hasta` como hora absoluta** | **A.** Resolverlo con `Inicio:` y la zona horaria de `equipo.md` (día de la semana + hora; `H+N` desde el inicio). Lo que no se resuelva va en `null` con su motivo y sale «sin plazo», nunca «a tiempo» | El plan no cambia y funciona con los ejemplos 02 y 03. Cada hora dice de dónde sale; un formato raro sale como «sin plazo», no como un plazo inventado |
| **3. Dependencias** | **B.** `depende_de` y la cadena de cada persona (sus filas, en orden), marcada «orden del plan» (inferida) | Con 6 de 28 tareas con dependencias, solo `depende_de` no da ruta. Una persona hace sus tareas una detrás de otra; como es inferido, se enseña como tal. Los hitos como topes (C) quedan fuera: el plan no enlaza hitos con tareas |
| **4. Duración de una tarea** | **A.** Franja derivada del plan: del `Hasta` de la fila anterior de la misma persona (o del inicio) al de esta; las filas que heredan el `Hasta` se reparten la franja del bloque. Sin columna «Horas» | El formato no cambia y `leer_plan` sigue con 5 columnas (un relay de la 0.4.0 no da el plan por mal formado). Es una franja, no una estimación, y se dice así |
| **5. Ritmo real** | **A.** Por persona: duración real (de la primera señal a hecha, sin descansos) ÷ franja, de sus tareas hechas no declaradas, desde **3** | Cada persona tiene su ritmo; una lenta no contamina a las demás. Cumple «el ritmo real» de R-36 sin reescribirlo |
| **6. Cómo se dice la incertidumbre** | **A.** Un rango de la hora de fin (con el ritmo más rápido y el más lento de cada persona), el margen contra la entrega en minutos (mínimo y máximo), un veredicto de cuatro valores y la base. Umbrales fijos: **a tiempo** si el fin tarde no pasa de la entrega; **justo** si la entrega cae dentro del rango; **no llega** si hasta el fin temprano la pasa | Se lee de un vistazo y no da una precisión que no hay. El veredicto, con umbrales fijos y sin parámetros, sirve para la firma de los deltas y se prueba sin modelo |
| **7. Con pocos datos** | **A.** Si alguna persona con tareas abiertas que cuentan tiene menos de 3 tareas medidas, no hay hora prevista: solo los hechos y «sin ritmo todavía (n de 3)» por persona. El 3 es **fijo en el contrato** (`base.minimo`), no se configura | Nunca estima con ruido y desde el minuto uno ya enseña lo atrasado. Un umbral configurable sería una forma de ajustar la vista hasta que diga lo que se quiere oír |
| **8. Qué tareas cuentan para la entrega** | **B.** Todas menos las que empiezan por «Si …» o llevan `[SI DA TIEMPO]`, que salen aparte, «fuera de la entrega» | Usa lo que `/hack-plan` ya escribe: un repliegue o un extra no retrasa la entrega. Si no se sigue la convención, la tarea cuenta (el lado seguro) |
| **9. Descansos** | **A.** Leer «## Descansos» del plan: no cuentan para la duración real (ritmo) ni para el fin previsto, y una persona en descanso no sale «sin señales» | En un reto de 39 h, una noche de sueño hundiría el ritmo y la estimación de la mañana. `/hack-plan` los escribe con un formato que se lee (K-107); lo que no se entienda se enseña y no se usa |
| **10. El riesgo en las sesiones** | **A.** Solo un delta, y solo cuando cambia el **veredicto** (la firma `ruta:` es el veredicto). Ni turno del monitor ni inyección por una hora que se mueve | Silencio cuando no cambia nada (X, R-25). Una estimación puede ser ruido: no justifica abrir un turno |
| **11. Commits sin ID** | **C.** El `CLAUDE.md` que genera `/hack-scaffold` recuerda `Txx · …` en los commits, y la vista dice «sin señales de @x desde HH:MM», nunca «va lenta» | Más tareas avanzan solas (mejor ritmo medido) y, cuando no, la vista no culpa a nadie |

Validación sin datos reales (#41, pregunta 12): guiones largos del simulador (G14, 39 h del reto 03, con commits, descansos y un ajuste del plan) para cerrar el hito, y el ensayo con un equipo después.

## Ajustes tras la revisión (2026-10-19, issue #46)
Decididos por el usuario sobre las «Decisiones que faltan» de la revisión de los contratos de M10. Mandan sobre lo de arriba donde lo contradigan. La numeración es la del issue; los ajustes 2 y 6 son de ADR-0012. Detalle en `api.md` (§0, §6 y §11) y en `estado.schema.json`.

| Ajuste | Elegido | Por qué |
|---|---|---|
| **1. Una tarea abierta sin plazo** | **No quita la estimación.** Sale en `sin_plazo[]` con su motivo, cuenta 0 min en el cálculo (sus sucesoras empiezan al acabar sus predecesoras) y el resto se estima. El resumen lo dice: «sin contar T28 (sin plazo)». `sin_plazo` deja de ser motivo de `sin_estimacion` (salvo cuando ninguna tarea abierta tiene franja: «Ajuste 2 tras congelar», abajo) | Con el contrato anterior, una sola fila «hora por confirmar» dejaba sin cifra a todo el reto (A3). Sigue sin contar como a tiempo, y se dice qué no se ha contado |
| **3. Qué tareas ponen la entrega en riesgo** | **`ruta.riesgos[]`**: `{tarea, tipo: "estimacion", fin_tarde, dueno, en_cadena, viejo}`, cada tarea abierta que según la estimación acaba después de la entrega, esté o no en la cadena. La cadena es solo de tareas abiertas. **No** hay hora central, ni previsión por hito, ni «fiabilidad»: lo dicen el rango y la base | R-36 pide decir «qué tareas la ponen en riesgo», y los hechos solo traen lo que ya ha pasado (A6). Una hora central o una fiabilidad darían una precisión que no hay (decisión 6A); los hitos no se enlazan con tareas (decisión 3B) |
| **4. Formato de los descansos** | Se leen de la tabla `\| Turno \| Quién \|` y de las líneas `- <@usuario \| Nombre \| Todos>: <día> HH:MM–[<día>] HH:MM`. Varias personas por turno (`descanso.personas`, una lista; `null` = «Todos»); el final puede llevar día. Se restan **de la franja** al medir el ritmo (y de la duración real, como ya decía la decisión 9A) | Los ejemplos de `/hack-plan` y G14 usan la tabla, y ningún turno casaba con el formato anterior (A5). Un descanso dentro de la franja no es tiempo planificado de trabajo: sin restarlo, una noche de sueño daría un ritmo «rápido» que no lo es (M12) |
| **5. La hora de entrega** | «Dos horas» = dos horas distintas en la línea `- Entrega:`, sin contar la zona. **Manda la primera**; la otra va a `otras_entregas` y **no quita la estimación**. Valen «dom 20 sep 09:30» y «dom 20 sep 2026 10:00»; sin zona, se hereda la de `Inicio:`. Solo es una entrega la fila de Hitos cuya Qué es «Entrega» o empieza por «Entrega final»; las demás son hitos. Una nota `dato` sobre la entrega sale como «(criterios.md, nota de HH:MM)», nunca con su texto (V) | R1A ya decía que una discrepancia no deja sin cifra, y «10:00 (cierre 11:00)» del reto 02 es justo una (M2); un desfase `+02:00` no es una segunda hora. Los formatos reales de G14 y del reto 03 daban «sin hora de entrega» (M3). «Entrega temprana» del reto 02 salía siempre como discrepancia (M4). El texto de una nota es dato, no va al md (M5) |
| **7. Delta y MCP** (decisión 10A) | El delta de `## Jurado y ruta` se filtra por línea y firma: la línea de la ruta solo se inyecta si cambia su veredicto. La herramienta `ruta` del MCP solo se lista con `ruta_critica: sí` (ADR-0012, ajuste 7) | Sin el filtro, un cambio del jurado inyectaba la línea de la ruta aunque el veredicto no cambiara, en contra de 10A y de X (M18) |

## Ajuste 2 tras congelar (2026-10-19, M10)
Tres puntos en que los ajustes del issue #46 (PR #53) dejaron el contrato distinto del código, decididos por el usuario. Mandan sobre lo de arriba donde lo contradigan. Detalle en `api.md` (registro de cambios y §11) y en `estado.schema.json`, marcado «tras congelar, 2026-10-19, M10, ajuste 2».

| Punto | Elegido | Por qué |
|---|---|---|
| **1. `sin_plazo` como motivo** | Vuelve a ser motivo de `sin_estimacion`, **solo** cuando hay tareas abiertas que cuentan y **ninguna** tiene franja. Si alguna la tiene, todo queda como dice el ajuste 1: las que no la tienen van a `sin_plazo[]`, cuentan 0 min y no quitan la estimación | Sin ninguna franja no hay nada que medir: con el ajuste 1 solo, todas contarían 0 min y el veredicto saldría «a tiempo» sin haber medido nada, justo lo que «sin plazo no es a tiempo» prohíbe |
| **2. `dos_horas`** | Se queda como motivo de `Inicio:`: con dos horas distintas, `valor: null` y `motivo: dos_horas`. Solo deja de existir en `Entrega:`, donde manda la primera y la otra va a `otras_entregas` (ajuste 5) | En `Entrega:` la segunda hora tiene sitio, `otras_entregas`; en `Inicio:` no hay dónde enseñarla, y elegir una sería una decisión que no ha tomado el equipo |
| **3. Orden del resumen de la ruta** | «plazo pasado» va justo detrás del veredicto (o del motivo de «sin estimación»), antes que «sin contar…» y «otra entrega…» | El resumen se corta a 120 caracteres (M17): con el orden anterior, el corte quitaba el plazo pasado o su hora (los dos ejemplos de `api.md` §11.6), el único dato rojo (un hecho), y dejaba lo declarado o lo que no se ha contado |

## Alternativas descartadas
- **Que un modelo estime las duraciones o el riesgo:** no es una señal (constitución II) y no se puede probar sin modelo.
- **Que la persona declare cuánto le falta** (acción en la web): sería declarado y caro; una acción nueva necesita ADR-0010 y queda fuera de M10.
- **Replanificar sola** (mover tareas, cambiar dueños): la ruta avisa; lo decide el equipo con `/hack-plan` (constitución VI).
- **Medir contra la congelación** (la propuesta del diseño de la 0.5.0, PR #43): la congelación es del equipo y puede moverse; la entrega es la del reto. La congelación sale como hito.
- **Rojo para «no llega»:** el rojo dice que algo ya ha fallado; una previsión no lo ha hecho.
- **Elegir entre dos horas de entrega** (por ejemplo, la más temprana): sería una decisión que no ha tomado el equipo. Desde el ajuste 5 manda la primera que escribe el equipo, sin compararlas, y la otra se enseña al lado.

## Riesgos aceptados
- La franja del plan no es una duración: un plan optimista da un ritmo «lento» que es del plan, no de la persona. Se dice «contra el plan».
- Con discrepancias en la entrega, la estimación usa la de `equipo.md` aunque la buena sea otra: la discrepancia sale al lado para que se corrija.
- La historia se reconstruye desde el registro del relay: si se pierde `relay/eventos.jsonl`, el ritmo vuelve a «sin ritmo todavía».
- Un ajuste del plan cambia los `Hasta`: el ritmo de antes se mide contra la franja de entonces o se pierde (Paso 0).
- El 3 y los umbrales del veredicto salen del simulador, sin datos reales. El ensayo de M8h los revisará; cambiarlos es cambiar el contrato.
