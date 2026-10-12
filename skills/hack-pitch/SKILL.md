---
name: hack-pitch
description: Genera el esqueleto del pitch o de la defensa de un reto de hackathon en .hackathon/pitch.md — guion por bloques con tiempo, criterio que cubre, quién habla, mensaje clave y qué se ve en pantalla; preguntas probables del jurado y cifras que hay que medir. Pensado para lanzarse justo después de /hack-plan.
argument-hint: [ajustes, por ejemplo "presenta Ana sola"]
allowed-tools: Read Write Glob
disable-model-invocation: true
---

Eres quien prepara la presentación del equipo **al principio del hackathon**, no al final. El guion es un objetivo: dice qué tiene que poder enseñarse al jurado, qué criterio gana cada minuto y qué cifras hay que medir, y antes de cuándo. Se lee en unos cinco minutos.

## Entrada

1. Lee `.hackathon/analisis.md`, `.hackathon/decision.md` y `.hackathon/equipo.md` en el directorio de trabajo actual, y `.hackathon/plan.md` si existe.
   - Si falta `decision.md`, pide ejecutar `/hack-approaches` y para.
   - **Si falta `equipo.md`**: créalo a partir de `${CLAUDE_PLUGIN_ROOT}/skills/hack-plan/templates/equipo.md`, rellenando de antemano las fechas del hackathon que dé el análisis (con "(confirmar)" detrás). Di al usuario que lo rellene y vuelva a lanzar el comando, y para.
   - **Si `equipo.md` conserva algún marcador `< >`**: di exactamente qué falta y para.
   - Si falta `plan.md`, sigue, pero avisa de que conviene ejecutar antes `/hack-plan`, y deja "—" en dueños e hitos de las cifras.
   - Lee también `.hackathon/criterios.md` si existe: lo que el jurado, los mentores o la organización han dicho durante el evento, anotado por el equipo con `/hack-note`.
2. Ajustes (opcionales): $ARGUMENTS
3. Lee la plantilla `${CLAUDE_SKILL_DIR}/templates/pitch.md`.

## Estructura

- Si el análisis recoge una estructura para la presentación o la defensa (bloques, minutos, qué pide el jurado), **síguela tal cual** y di de dónde sale.
- Si no, usa esta por defecto, repartida en la duración que dé el análisis: problema y para quién → demo del producto → cómo funciona y por qué se decidió así → impacto o quién paga → cierre.
- Si la duración no se conoce, usa 5 minutos y pon `[CONFIRMAR: duración]` en la cabecera.

## Reglas

- **Criterios**: cada bloque indica qué criterio de evaluación cubre, con el nombre y el peso **copiados de la rúbrica de `analisis.md`**, nunca de memoria. Ningún criterio con peso se queda sin bloque; si alguno no cabe, dilo debajo de la tabla.
- **Notas de `criterios.md`**: cada nota que afecta al pitch tiene un bloque, un mensaje o una respuesta que la recoge, y ese texto acaba con `(criterios: <fecha hora de la nota>)`. Una nota con fuerza `dato` sostiene ese dato tal cual (por ejemplo, la duración), aunque el análisis lo dejara como ambigüedad. En lo demás, usa la misma fuerza que la nota: un comentario suelto o una fuerza `sin precisar` no se presenta como algo que el jurado exige. Si una nota choca con la rúbrica del análisis, no elijas entre las dos: sigue la rúbrica y dilo debajo de la tabla para que decida el equipo.
- **Quién habla**: quien presenta según `equipo.md`; en las preguntas, responde el dueño de ese tema según `plan.md`.
- **Qué se dice**: una sola línea por bloque con el mensaje clave, para decirla en voz alta. No escribas el discurso.
- **Qué se ve en pantalla**: lo que el enfoque elegido tendrá construido. Si aún no existe, escríbelo como objetivo ("la ficha con el desglose del score"), no como algo hecho.
- **Cruce con `plan.md`**: antes de guardar, repasa cada cosa que el guion o las respuestas dicen que se enseña, se construye o funciona, y búscale la tarea de `plan.md` que la produce. Si no la tiene, márcala con `[SI DA TIEMPO]` o quítala. Nada se presenta como «ya implementado».
- **Cifras y resultados**: nunca inventados. Toda cifra **y todo resultado o conclusión que dependa de medir** («el cuello es X», «detecta antes», «la autonomía es medida», «funciona con datos reales») va como `[CIFRA: qué se mide]`, sin adelantar hacia dónde saldrá. Cada una aparece en "Cifras que hay que medir" con cómo obtenerla, su dueño y antes de qué hito de `plan.md`.
- **Nada inventado**: ni clientes, ni testimonios, ni datos reales donde son simulados, ni lo que hace hoy el comprador. Los mensajes salen de la decisión y del análisis, con la misma fuerza que les dé el análisis (obligatorio, preferible, bonus). Lo que no venga de ahí y sea conocimiento tuyo (licencias, qué hace una empresa) va con `(conocimiento externo, verificar)`, y lo que dependa de una ambigüedad abierta, como supuesto que hay que confirmar con la organización.
- **Preguntas del jurado** (5–6): salen de los criterios de evaluación, de las ambigüedades y riesgos del análisis y, sobre todo, de los **puntos débiles del enfoque elegido** según su "Cómo puntúa" en la decisión. El esqueleto de la respuesta, en una o dos líneas, con huecos de cifra donde haga falta.
- **Si falla la demo**: 3–5 líneas con el plan B de cada cosa que se enseña en directo.
- **Tamaño**: unas 900 palabras como máximo; cuéntalas antes de guardar. Para conseguirlo:
  - cabecera en dos líneas como mucho;
  - "Qué se dice": una frase de unas 25 palabras; "Qué se ve en pantalla": unas 15 palabras;
  - 5–6 preguntas, con respuestas de unas 25 palabras;
  - en "Cifras que hay que medir", solo las cifras que aparecen en el guion o en las respuestas, con "Cómo obtenerla" en unas 12 palabras.
  - las notas de `criterios.md` caben en ese tamaño: se recogen dentro de un bloque, una respuesta o la cabecera que ya existen, y debajo de la tabla, como mucho, una línea por nota que choca con algo.
  Si aun así no cabe, recorta detalle; no añadas secciones a la plantilla.

## Guardar

Escribe `.hackathon/pitch.md` siguiendo la plantilla. Si ya existe, pregunta con AskUserQuestion si sobrescribirlo (el equipo puede haberlo editado). Si no puedes preguntar, no lo sobrescribas: di cómo seguir y para. No modifiques ningún otro fichero.

## Resumen

Termina con, en pocas líneas: la estructura usada y de dónde sale, qué criterio queda más flojo en el guion, qué notas de `criterios.md` se han recogido y dónde (si hay), y las cifras que hay que medir antes con su hito. Siguiente paso: `/hack-check`, que verifica todo lo generado contra el enunciado.
