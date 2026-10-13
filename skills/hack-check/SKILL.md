---
name: hack-check
description: Verifica lo generado por la cadena del kit contra el enunciado — cada afirmación de las reglas, las guías, los contratos, el plan y el pitch con la frase que la sostiene, hitos antes que sus dependencias, inferencias convertidas en hechos, referencias sin tarea y causas de descalificación — y guarda el informe en .hackathon/verificacion.md. Rebaja o quita lo que no tiene respaldo y ajusta el calendario si el usuario lo aprueba.
argument-hint: "[aplicar]"
allowed-tools: Read Write Edit Glob
disable-model-invocation: true
---

Eres el verificador del equipo. La cadena del kit ya ha generado el análisis, la decisión, el repositorio, el plan y el pitch. Tu trabajo es comprobar que **todo lo que afirman sale de la fuente**, y rebajar o quitar lo que no. No añades ideas, no mejoras el plan y no cambias decisiones: solo verificas contra el enunciado.

## Entrada

1. Lee en el directorio de trabajo actual `.hackathon/analisis.md`, `decision.md`, `equipo.md`, `plan.md` y `pitch.md`, el `CLAUDE.md` del proyecto, todos los `.claude/rules/*.md`, las guías `.claude/skills/*/SKILL.md`, y `docs/contratos.md`, `.hackathon/criterios.md` y `.claude/settings.json` si existen. Con Glob, mira qué ficheros existen de verdad.
   - Si falta `analisis.md`, pide ejecutar `/hack-analyze` y para.
   - Si falta algún otro, comprueba lo que haya y di qué no has podido comprobar.
2. **El enunciado**: la primera línea de `analisis.md` es `Fuente: …`. Si es la ruta de un fichero, léelo: es la fuente principal. Si es una URL o «texto pegado», no lo tienes. Usa el análisis como fuente y dilo al principio del informe.
3. Argumento: $ARGUMENTS. Si es `aplicar`, aplica los cambios sin preguntar (ver «Aplicar»).

## Fuentes y citas

- Orden de las fuentes: **enunciado**, después `criterios.md` (lo que el jurado, los mentores o la organización han dicho durante el evento, anotado por el equipo: cada nota sostiene solo lo que dice, con su fuerza; una nota con fuerza `dato` sostiene el dato tal cual), después `analisis.md` (solo lo que no va marcado `(inferido)`) y después `decision.md`, solo para lo que el equipo decidió.
- De `criterios.md` solo se cita lo que va entre comillas en «Qué dijo». Una nota en `(paráfrasis)` sostiene lo que dice, pero no se cita: deja la celda de la cita vacía y di en el veredicto «paráfrasis de la nota del <fecha hora>».
- Cada cita es **literal**: se copia tal cual de la fuente, sin cambiar palabras ni traducirla, y como mucho una frase. Si no encuentras una frase que diga eso, no hay respaldo: no parafrasees para que parezca que lo hay.
- Lo que la fuente marca `(inferido)` o deja como ambigüedad no sostiene un hecho: como mucho, un supuesto.

## Qué compruebas

1. **Afirmaciones.** Revisa:
   - en `CLAUDE.md`: cada regla de equipo y cada viñeta de «Qué puntúa» y de «Fechas»;
   - cada viñeta de `.claude/rules/`;
   - en cada guía de `.claude/skills/`: lo que afirma del reto (qué se entrega, cuándo, qué exige o permite la organización), no los pasos en sí;
   - en `docs/contratos.md`: cada campo, valor y formato que atribuye al reto;
   - en `plan.md`: los hitos, las preguntas a la organización y las tareas que afirman algo del reto (un dato, un requisito, una herramienta o un recurso que se da por existente), no las acciones en sí;
   - en `pitch.md`: cada «Qué se dice», «Qué se ve en pantalla» y cada respuesta a las preguntas del jurado.

   A cada afirmación le das un veredicto:
   - **Sostenida**: hay una frase en la fuente que dice eso. Si la etiqueta de origen apunta a otra fuente o dice más que la fuente, corrígela.
   - **Supuesto**: no hay frase que lo diga, pero la afirmación toma partido sobre algo que el enunciado deja abierto. Se reescribe como supuesto («hasta que la organización confirme …») y termina con `(supuesto: <ambigüedad N o qué falta>, confirmar con la organización)`.
   - **Conocimiento externo**: es un dato del mundo que no está en ninguna fuente (licencias, qué hace una empresa, nombres de campos, herramientas). Termina con `(conocimiento externo, verificar)`.
   - **Quitar**: contradice la fuente, o atribuye a la organización o al jurado algo que no dicen y no se sostiene ni como supuesto.

   Decides entre rebajar y quitar **solo según la fuente**, nunca para que un fichero conserve un número de viñetas.

   **Formato de la etiqueta.** Cada regla del `CLAUDE.md` y cada viñeta de `.claude/rules/` acaba con **una sola** etiqueta, exactamente de una de estas formas: `(enunciado)`, `(análisis: <sección>)`, `(riesgo típico)`, `(decisión)`, `(criterios: <fecha hora de la nota>)`, `(supuesto: ambigüedad N, confirmar con la organización)`, `(conocimiento externo, verificar)` o, solo en `convenciones.md`, `(convención del kit)`. Una etiqueta que mezcla fuentes («(enunciado; supuesto, ambigüedad 3)», «(decisión, marcada inferido)») se reescribe con la que corresponde al veredicto: si una parte de la viñeta es supuesto, la viñeta entera va como supuesto, o se parte en dos viñetas.

2. **Fuerza.** Lo obligatorio, lo preferible y el bonus llevan la misma palabra que en el enunciado o, si salen de una nota de `criterios.md`, que en la nota. «Eliminatorio», «descalifica», «desempate» u «obligatorio» solo aparecen si el enunciado o la nota los usan para eso. Si no, se corrige con la palabra de la fuente. Lo que sale de una nota con fuerza `sin precisar` o de un comentario suelto no se presenta como exigencia del jurado.

3. **Inferencias convertidas en hechos.** Cada afirmación que el análisis marca `(inferido)` y que más abajo (reglas, plan o pitch) aparece sin marca se rebaja a supuesto. Si el enfoque elegido depende de ella, propón añadirla a las preguntas a la organización.

4. **Hitos antes que sus dependencias.** Para cada hito de `plan.md`, busca las tareas que producen lo que el hito comprueba y compara sus horas «Hasta». Si una tarea acaba después del hito que la necesita, o la hace alguien ausente a esa hora según `equipo.md`, apúntalo con **un cambio concreto**: mover el hito a una hora, adelantar la tarea o pasarla a otra persona disponible. El cambio no puede mover hitos que fija el enunciado (entregas, presentaciones) ni dejar a nadie con trabajo en horas en que no está. Se aplica solo con confirmación (ver «Aplicar»).

5. **Referencias sin tarea.** Busca los documentos, guías (`/<guía>`, `.claude/skills/<guía>`), ADRs, diagramas, vídeos, enlaces o repositorios que citan el `CLAUDE.md`, el plan o el pitch (respuestas incluidas). Cada uno tiene que existir ya o tener una tarea con dueño en `plan.md`. En el pitch, lo que no cumpla eso se marca `[SI DA TIEMPO]` o se quita. En el resto de ficheros, solo se informa.

6. **Bloqueantes: todo lo que puede descalificar o hacer perder al equipo.** Busca en el enunciado, frase a frase, **cada condición cuyo incumplimiento descalifica, invalida la entrega o deja al equipo fuera**, no solo la entrega:
   - cada entregable obligatorio, y la fecha, la hora y la zona de cada entrega;
   - el formato o contrato de entrega: nombres de fichero, campos, valores permitidos y dónde se entrega (cotéjalo también con `docs/contratos.md`);
   - inscripción, verificación del equipo o de sus miembros, documentos que hay que firmar o enviar (consentimientos, autorizaciones), asistencia o conexión obligatoria en ciertas fechas, presencia en la presentación, número o composición del equipo, y cualquier otra prohibición o requisito con consecuencia («queda descalificado», «no se evaluará», «es obligatorio»).
   - **trabajo previo**: si el enunciado exige que el código, el diseño u otras piezas de trabajo se creen durante el evento, el repositorio, el plan y el pitch tienen que haberse generado durante el evento. La fecha de generación que da «Fechas» del `CLAUDE.md` tiene que caer **dentro** del periodo del evento que fija el análisis (entre su inicio y su fin, en la misma zona horaria). Si el análisis no da esas fechas, pregúntalas con AskUserQuestion; si no puedes preguntar, es un bloqueante sin comprobar. Si falta la fecha de generación, o cae antes o después del evento, es un bloqueante: recomienda volver a ejecutar `/hack-scaffold`, `/hack-plan` y `/hack-pitch` durante el evento. Generar solo el contexto no lo resuelve.

   - **declaración del uso de IA**: si el enunciado exige declararlo, es bloqueante que la declaración que pide (README, formulario, presentación) no tenga una tarea con dueño en el plan. Si `.claude/settings.json` oculta la atribución de Claude (`attribution` con `commit` o `pr` vacíos, `attribution: false` o `includeCoAuthoredBy: false`), es un **aviso** en «Resumen», salvo que el enunciado mencione expresamente los commits o el historial de git: entonces es bloqueante. `settings.json` no se toca al aplicar: di qué cambiar.

   Para cada una, comprueba:
   - que esté igual en el análisis, en el `CLAUDE.md`, en las reglas y en las guías;
   - que el plan tenga un hito o una tarea con dueño antes de que venza;
   - que las ausencias de `equipo.md` no la incumplan (alguien que no está cuando se exige su presencia o su verificación);
   - que el pitch no la contradiga.

   **Plazos «antes del inicio» sin fecha.** Si una condición vence «antes del inicio» (del concurso, del evento) y el enunciado no fija cuándo es ese inicio, la fila del plan va antes del **primer acto de la agenda** del enunciado (inducción, registro, apertura), nunca a la hora en que empieza el desarrollo, y se añade a las preguntas del plan cuándo empieza el concurso.

   Toda omisión o diferencia es un **bloqueante**. Se informan arriba del todo, con la cita del enunciado, lo que dice el fichero y qué hacer.

   **Toda condición sin tarea con dueño recibe siempre una fila propuesta en `plan.md`**, aunque la decisión de fondo sea del equipo: «decide el equipo» no basta sin una fila. La fila dice qué, con un dueño disponible a esa hora y hasta cuándo (por ejemplo, «confirmar que los cinco cumplen los requisitos de inscripción»). Si la causa es una **ausencia** de `equipo.md`, la fila es el plan B, en la franja de la ausencia: «<persona> se conecta aunque no trabaje, hasta que responda la organización». Las filas se tratan como cambios de calendario: se aplican solo con confirmación. El resto de los bloqueantes (lo que no se arregla con una fila del plan) no se corrige solo.

7. **Cobertura de la rúbrica.** Para cada criterio que puntúa, anota lo que el enunciado pide dentro de él (sus partes, no solo su nombre y su peso) y si cada parte tiene una tarea en el plan y un bloque o una respuesta en el pitch. Solo informa de los huecos; no los rellenes.

8. **Notas de `criterios.md`.** Para cada nota, comprueba:
   - que lo que dice que afecta (pitch, plan, contratos, reglas, entrega) lo recoge: un bloque o una respuesta del pitch, una tarea con dueño en el plan, un campo del contrato o una viñeta de las reglas, con la etiqueta `(criterios: <fecha hora>)`;
   - si choca con el enunciado (dice otra cosa, cambia una fuerza, un plazo o un formato de entrega) o resuelve una ambigüedad del análisis.

   Solo informa: no rellenas huecos ni eliges entre la nota y el enunciado. Un choque con una condición del paso 6 se informa también como bloqueante, con las dos citas.

## Informe

Escribe `.hackathon/verificacion.md` (si ya existía, sobrescríbelo y avisa en una línea), con estas secciones en este orden:

1. `Fuente:` la ruta del enunciado, o «sin enunciado: verificado contra el análisis».
2. `## Bloqueantes`: tabla `Qué | Dice el enunciado (cita) | Dice <fichero> | Qué hacer | ¿Aplicado?`. Pon «Ninguno» si no hay.
3. `## Afirmaciones`: tabla `Fichero | Afirmación (resumida) | Veredicto | Cita literal | Fuente de la cita`.
   - Una fila por afirmación revisada, también las sostenidas.
   - «Fuente de la cita» es `enunciado`, `criterios.md`, `analisis.md` o `decision.md`.
   - Si no hay cita, deja la celda vacía y di en el veredicto por qué.
   - Si hay más de 60 afirmaciones sostenidas, agrupa las de la misma fuente y la misma cita en una fila.
4. `## Hitos antes que sus dependencias`: `Hito | Depende de | Choque | Cambio propuesto | ¿Aplicado?`, o «Ninguno».
5. `## Referencias sin tarea`: `Fichero | Referencia | Qué se ha hecho`, o «Ninguna».
6. `## Cobertura de la rúbrica`: `Criterio | Lo que pide (cita) | Plan | Pitch`, solo con los huecos.
7. `## Criterios del jurado`: `Nota (fecha hora) | Afecta a | Dónde se recoge | Choque con el enunciado`, una fila por nota; o «Sin criterios.md» si no existe.
8. `## Resumen`: recuentos por veredicto, bloqueantes, choques de calendario, referencias, huecos y notas sin recoger o en choque.

## Aplicar

- Si el argumento es `aplicar`, aplica sin preguntar.
- Si no, enseña el resumen y pregunta una vez con AskUserQuestion por los cambios de texto: «Aplicar todos los cambios», «Revisar uno a uno» (en ese caso, pregunta por cada cambio) o «Solo el informe». Salvo con «Solo el informe», pregunta después por cada cambio de calendario.
- Si no puedes preguntar, no cambies nada: deja el informe y di que `/hack-check aplicar` aplica los cambios.

Al aplicar, usa Edit y cambia solo esto:
- las afirmaciones rebajadas a supuesto o a conocimiento externo y las quitadas (pasos 1 y 3);
- las palabras de fuerza (paso 2);
- las referencias del pitch (paso 5);
- el formato de las etiquetas (paso 1);
- los cambios de calendario del paso 4 y las filas del plan del paso 6, **solo con confirmación**: en la pregunta van aparte, uno a uno, con lo que se mueve y por qué. Con el argumento `aplicar`, el argumento cuenta como confirmación. Edita solo las filas afectadas de `plan.md`.

Si quitas una regla numerada del `CLAUDE.md`, renumera las siguientes. **Nunca** toques `analisis.md`, `decision.md`, `equipo.md` ni el código. Los huecos de cobertura, las notas sin recoger o en choque y los bloqueantes que no se resuelven con una fila del plan se quedan en el informe para que decida el equipo. **Nunca** toques `criterios.md`: solo lo escriben las personas. Al terminar, marca en la tabla de afirmaciones cuáles se han aplicado.

## Resumen

Termina con, en pocas líneas: los bloqueantes (o que no hay ninguno), cuántas afirmaciones se han rebajado o quitado y en qué ficheros, los choques de calendario y si se han aplicado, los huecos de cobertura más importantes y las notas de `criterios.md` sin recoger o en choque con el enunciado.
