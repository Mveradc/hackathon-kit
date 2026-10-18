# ADR-0013 · Ruta crítica: de dónde salen dependencias, horas y ritmo, cómo se dice la incertidumbre y qué se hace sin datos

Estado: **BORRADOR** (2026-10-19, para M10). Lo decide el usuario con la tabla «Decisiones pendientes». Lo marcado **(Paso 0)** depende de K-100 (issue #41, «M10, Paso 0»), que está abierto. El interruptor es la decisión 8 de ADR-0012.

## Contexto
R-36: «DONDE la ruta crítica esté activa, el sistema DEBE estimar, con las dependencias y el ritmo real, si se llega a la entrega y qué tareas la ponen en riesgo». Lo que hay hoy (inventario del issue #41, §2, §3 y §6):
- **Dependencias:** solo las de «Quién espera a quién», que llegan a `estado.json` como `depende_de`. En el plan del reto 03, solo **6 de 28** tareas tienen alguna: la cadena real es la de cada persona (un dueño por carpeta y sus filas en orden).
- **Horas:** el plan no tiene duraciones. Tiene un **plazo** por fila, `Hasta`, en texto libre (`vie 19:45`, `VIE 23:00`, `H+2` si no se sabe el inicio; una celda vacía hereda la de arriba). Está en el cuerpo del issue, pero **no llega a `estado.json`**.
- **Entrega:** en hasta cinco sitios, todos declarados y en texto libre (`equipo.md`, cabecera e Hitos del plan, `CLAUDE.md`, análisis, una nota de fuerza `dato`), que no siempre coinciden (02: «10:00 (cierre 11:00)»).
- **Ritmo:** `estado.json` es solo el presente (en `en_curso`, `observado_en` es la última actividad, no el inicio). Pero el relay guarda todos los eventos y `modelo.calcular(…, ahora)` es puro, así que **la historia de transiciones se puede reconstruir** (comprobado con G2 y G3 en el Paso 0).
- **Datos reales: ninguno.** Los guiones duran minutos y el ensayo sigue aplazado. Un commit sin `Txx` (con más de una tarea abierta) no hace avanzar ninguna tarea.

Valen la constitución II, III, IV y X (una hora estimada que se mueve con el reloj no puede inyectar nada) y ADR-0009.

## Decisión (lo que no depende de la tabla)
- **Detrás de un interruptor** (ADR-0012, decisión 8). Apagado, todo como en la 0.4.0 (constitución I).
- **Dónde se calcula:** el relay pone en `estado.json` lo que lee (plazos resueltos, entrega, historia de transiciones por tarea) y `proyeccion.vista` calcula el bloque `ruta`. La web solo lo pinta. El cálculo es una función pura con su tabla de casos (`hkos/ruta.py`), con `ahora` como parámetro, como el motor de estados.
- **Hechos aparte de estimaciones.** La vista separa:
  - **hechos** (derivados y comprobables): «T05: su plazo pasó a las 02:30 y sigue en curso»; qué tareas arrastra una atrasada por sus dependencias; qué tareas están `parada` o `no_cerrada` en la ruta;
  - **la estimación**, que siempre lleva la palabra «estimación», su base (cuántas tareas medidas y desde cuándo), un **rango** y nunca una sola hora, la hora en que se calculó y la antigüedad de su dato más viejo.
- **Sin estimación, y lo dice**, cuando:
  - no hay hora de entrega que se pueda leer: «sin hora de entrega»;
  - hay dos horas de entrega distintas: se enseñan las dos, como discrepancia, sin elegir;
  - las dependencias tienen un ciclo: «ciclo T04 → T07 → T04»;
  - hay menos datos que el mínimo (decisión 7).
- **Sin plazo no es «a tiempo».** Una tarea con `Hasta` vacío o sin resolver sale en una lista aparte, «sin plazo», y no cuenta como a tiempo ni como atrasada.
- **Sin señales no es lento.** Si una persona no deja señales (commits sin ID, `atribucion_ambigua`, sin OS), la vista dice «sin señales de @x desde HH:MM» y enseña al lado sus `sin_tarea` y discrepancias; nunca «@x va lenta».
- **Lo declarado, como declarado:** `Hasta`, la entrega y los descansos salen del plan o de `equipo.md` y llevan su procedencia y la hora del commit de ese fichero (como `servicios`). Una tarea `cerrada` a mano cuenta como hecha con su ⚑.
- **Silencio (X, R-25, G10):** la firma de los deltas solo cambia con el **veredicto** (a tiempo, justo, no llega o sin estimación), la lista de tareas en riesgo de la persona o un hecho nuevo (un plazo que pasa). Que la hora estimada se mueva no inyecta nada.
- **Horas con zona:** toda hora sale con la zona horaria del plan o de `equipo.md`. Los `ts` de los commits son del reloj del portátil: si se guarda el desfase que imprime `hk-os unir`, se enseña.
- **Viejo:** sin relay o sin GitHub, la estimación sale vieja, con la antigüedad de su dato más viejo (III, R-12).
- **Prueba doble de ADR-0009:** `igualdad.py` con el guion nuevo **G14** (ruta), y Vitest pinta G14.

## Decisiones pendientes

Aquí no se cambia nada: es para decidir. Cada fila da 2 o 3 opciones con sus pros y sus contras.

| Decisión | Opciones | Pros | Contras |
|---|---|---|---|
| **1. Hora de entrega** (Paso 0, #41 pregunta 4) | **A.** Manda `- Entrega:` de `equipo.md` (declarado, con «(confirmar)» si lo lleva); la fila «Entrega» de Hitos y las notas `dato` se comparan y, si no coinciden, salen como discrepancia | Ya existe y tiene un formato con zona horaria. El relay ya tiene `origin/main` | `equipo.md` puede no estar en `main` o estar mal: entonces no hay estimación. En los evals, el patrón 8 (fechas que se contradicen) sale en 3 de 5 retos |
| | **B.** La fila «Entrega» de «Hitos del equipo» del plan | Está junto a los plazos que usa la ruta | Hoy no la lee ningún código. Texto libre («dom 10:00», «hora por confirmar») |
| | **C.** Una línea `entrega:` nueva en `os.md` | Un solo sitio, con formato fijo | Una fuente más que puede contradecir a las otras. La tiene que escribir alguien al arrancar el OS |
| **2. `Hasta` como hora absoluta** (Paso 0: cuántos `Hasta` de los planes de ejemplo se resuelven) | **A.** Resolverlo con `Inicio:` y la zona horaria de `equipo.md` (día de la semana + hora); lo que no se resuelva (`H+2` sin inicio, «hora por confirmar») va en `null` con su motivo y sale «sin plazo» | El plan no cambia. Funciona con los ejemplos 02 y 03 | Interpretar texto libre: un formato raro da un plazo equivocado. Hay que decir de dónde sale cada hora |
| | **B.** Ignorar `Hasta`: solo cuenta la entrega | Nada que interpretar | Sin plazos intermedios no hay «atrasada» ni ruta: R-36 queda en «llegamos o no» |
| | **C.** Formato estricto nuevo en `/hack-plan` (`sáb 02:30` siempre con día y hora, o ISO) | Se lee sin ambigüedad | Cambia la cadena y los ejemplos; los planes hechos antes no valen. Sigue sin resolver `H+N` |
| **3. Dependencias** (#41, §6 riesgo 8) | **A.** Solo `depende_de` (las de «Quién espera a quién») | Es lo declarado, sin inferir nada | Subestima: con 6 de 28 tareas con dependencias, la «ruta» casi no existe |
| | **B.** `depende_de` y la cadena de cada persona (sus filas, en orden), marcada «orden del plan» | Es la cadena real: una persona hace sus tareas una detrás de otra | Una persona puede saltarse el orden; la cadena inferida se tiene que enseñar como inferida |
| | **C.** B y los hitos del equipo (demo mínima, congelación) como topes intermedios | Avisa antes de la entrega, en el hito que importa | Hay que leer la tabla de Hitos (hoy nadie la lee) y enlazar cada hito con tareas, que el plan no hace |
| **4. Duración de una tarea** (#41 pregunta 5) | **A.** Franja derivada del plan: del `Hasta` de la fila anterior de la misma persona (o del inicio) al de esta; las filas que heredan el `Hasta` se reparten la franja del bloque | El formato no cambia. Usa lo que el plan ya dice | Es una franja, no una estimación: un plan apretado al final infla el riesgo. Hay que decirlo así |
| | **B.** Columna «Horas» nueva en el plan | Una duración explícita | Rompe las 5 columnas de `leer_plan` (`compilar.py`): un relay de la 0.4.0 daría el plan por mal formado. Cambia la cadena |
| | **C.** Sin duraciones: la ruta solo dice qué está atrasado y qué arrastra | Ninguna estimación que pueda mentir | No responde «¿llegamos?», que es lo que pide R-36 |
| **5. Ritmo real** (#41 pregunta 7) | **A.** Por persona: duración real ÷ franja planificada de sus tareas ya hechas (desde la primera señal hasta `publicada`), con al menos N | Cada persona tiene su ritmo; uno lento no contamina a los demás | Con 3–5 personas, N tareas por persona tardan horas en llegar |
| | **B.** Del equipo entero (la misma razón, con todas las tareas hechas) | Llega antes a N | Mezcla ritmos muy distintos (una persona en el pitch y otra en el motor) |
| | **C.** Sin ritmo en la 0.5.0: solo plazos, dependencias y hechos | Lo más honesto con los datos de hoy | No cumple «el ritmo real» de R-36: hay que reescribirlo |
| **6. Cómo se dice la incertidumbre** | **A.** Un rango de la hora prevista de fin (con el ritmo más rápido y el más lento de lo medido, o p25–p75 desde más datos), un veredicto de cuatro valores (a tiempo · justo · no llega · sin estimación) y la base (n, desde cuándo) | Se lee de un vistazo y no da una precisión que no hay. El veredicto sirve para la firma de los deltas | El umbral entre «justo» y «a tiempo» es arbitrario (p. ej., si el rango pasa de la entrega) |
| | **B.** Solo la holgura en minutos («−40 min, estimación, n = 4») | Un solo número | Un número parece exacto aunque lleve «estimación»; cambia en cada cálculo |
| | **C.** Semáforo sin número, con el motivo («T06 y T08 van atrasadas y arrastran a T16») | Nada que parezca exacto | No dice cuánto falta ni cuánto sobra |
| **7. Con pocos datos o sin ellos** (Paso 0: qué N) | **A.** Por debajo de N tareas medidas, no hay hora prevista: solo los hechos y «sin ritmo todavía (n de N)» | Nunca estima con ruido. Desde el minuto uno ya enseña lo atrasado | Las primeras horas solo hay hechos: la estimación llega tarde |
| | **B.** Por debajo de N, la estimación usa el ritmo del plan (razón 1) y sale «supuesto: ritmo del plan» | Siempre hay una estimación | Un supuesto puede leerse como una estimación de verdad; es justo lo que el principio II quiere evitar |
| | **C.** No se enseña nada de la ruta hasta N | La vista nunca está a medias | Esconde hechos que ya son ciertos (un plazo vencido) |
| **8. Qué tareas cuentan para la entrega** (#41 pregunta 6) | **A.** Todas | Sin reglas nuevas | Una tarea de «si da tiempo» atrasa la entrega sin motivo |
| | **B.** Todas menos las que empiezan por «Si …» o llevan `[SI DA TIEMPO]` | Usa lo que `/hack-plan` ya escribe a veces | Es una convención de texto: si no se sigue, cuenta igual |
| | **C.** Una marca nueva en el plan para las imprescindibles | Explícita | Cambia la cadena y la huella del issue |
| **9. Descansos** (#41 pregunta 10) | **A.** Leer «## Descansos» del plan: no cuentan como atraso ni para el ritmo | Una noche de sueño no sale como «parada» ni hunde el ritmo | Otra sección que leer, en texto libre; solo existe en hackathones de más de ~20 h |
| | **B.** Ignorarlos en la 0.5.0 y decirlo en `docs/limitaciones.md` | Nada nuevo | En un reto de 39 h, la estimación de la mañana sale mal por el sueño |
| **10. El riesgo en las sesiones** | **A.** Solo en los deltas, cuando cambia el veredicto o la lista de tareas en riesgo de la persona | Silencio cuando no cambia nada (X) | Un «no llega» espera al siguiente turno de la sesión |
| | **B.** A y el monitor abre un turno al pasar a «no llega» (como una colisión roja) | Avisa en el momento | Un turno inducido por una estimación, que puede ser ruido; más coste |
| | **C.** No se inyecta: solo el md, el MCP y la web | Ningún coste en la sesión | El agente que no consulte el MCP no se entera |
| **11. Commits sin ID** (#41 pregunta 9) | **A.** Recordar `Txx · …` en el `CLAUDE.md` que genera `/hack-scaffold` | Más tareas avanzan solas: mejor ritmo medido | Cambia la cadena; depende de que lo sigan |
| | **B.** Aceptar que esas tareas avanzan solo por fusión o cierre | Nada nuevo | Una persona sin IDs parece parada |
| | **C.** Las dos, y «sin señales» en vez de riesgo (como en la decisión fija de arriba) | Más datos y la vista no culpa a nadie | Lo de A |

## Alternativas descartadas
- **Que un modelo estime las duraciones o el riesgo:** no es una señal (constitución II) y no se puede probar sin modelo.
- **Que la persona declare cuánto le falta** (acción en la web): sería declarado y caro; una acción nueva necesita ADR-0010 y queda fuera de M10.
- **Replanificar sola** (mover tareas, cambiar dueños): la ruta avisa; lo decide el equipo con `/hack-plan` (constitución VI).

## Riesgos aceptados (si se aprueba tal cual)
- La franja del plan no es una duración: un plan optimista da un ritmo «lento» que es del plan, no de la persona. Se dice «contra el plan».
- La historia se reconstruye desde el registro del relay: si se pierde `relay/eventos.jsonl`, el ritmo vuelve a «sin ritmo todavía».
- Un ajuste del plan cambia los `Hasta`: el ritmo de antes se mide contra la franja de entonces o se pierde (Paso 0).
- Sin datos reales, los umbrales (N, «justo») salen del simulador. El ensayo de M8h los revisará.
