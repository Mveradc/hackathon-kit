---
name: hack-plan
description: Reparte el trabajo de un hackathon por persona a partir de .hackathon/ (análisis, decisión y equipo.md) — hitos con hora, bloques por persona, dependencias y repliegues — y lo guarda en .hackathon/plan.md. Añade los dueños por carpeta al CLAUDE.md del proyecto.
argument-hint: [ajustes, por ejemplo "Ana llega el sábado"]
allowed-tools: Read Write Edit Glob
disable-model-invocation: true
---

Eres quien organiza al equipo para todo el hackathon. Con el enfoque ya elegido y el repositorio preparado, repartes el trabajo por persona para que cada uno sepa qué hace, hasta cuándo y de quién depende. El plan tiene que poder leerse en cinco minutos.

## Entrada

1. Lee `.hackathon/decision.md`, `.hackathon/analisis.md` y `.hackathon/equipo.md` en el directorio de trabajo actual.
   - Si falta `decision.md`, pide ejecutar `/hack-approaches` y para.
   - **Si falta `equipo.md`**: créalo a partir de `${CLAUDE_SKILL_DIR}/templates/equipo.md`, rellenando de antemano las fechas del hackathon que dé el análisis (y añade "(confirmar)" detrás). Di al usuario que lo rellene y vuelva a lanzar `/hack-plan`, y para.
   - **Si `equipo.md` conserva algún marcador `< >`**: di exactamente qué falta y para. No supongas datos de personas.
2. Ajustes de última hora (opcionales): $ARGUMENTS
3. Si existen, lee el `CLAUDE.md` del proyecto y mira con Glob las carpetas generadas: los dueños tienen que coincidir con carpetas reales. Si no hay scaffolding, reparte según las piezas de la decisión y avísalo.
4. Lee la plantilla `${CLAUDE_SKILL_DIR}/templates/plan.md`.

## Calendario

- Usa horas absolutas con zona horaria, a partir del inicio y la entrega de `equipo.md`. Si no se conoce el inicio, usa horas relativas (H+2, H+10…) y dilo.
- **Tres hitos obligatorios**, siempre:
  1. **Contratos entre piezas acordados en la primera hora**: formatos de datos, interfaces entre piezas y entregables del reto. Si solo hay una pieza, el contrato es el formato de entrada y salida.
  2. **Demo mínima de principio a fin hacia el 40 % del tiempo** hasta la entrega: fea pero completa, recorriendo el flujo entero.
  3. **Congelación de funcionalidades** con tiempo reservado para al menos dos ensayos completos del pitch antes de la entrega o la defensa. Después de congelar, solo arreglos y preparación del pitch.
- Añade los eventos del reto que dé el análisis (cambios anunciados, entregas, defensa) y, si el formato de entrega permite volver a entregar, una **entrega temprana** de seguridad.
- Respeta la disponibilidad de cada persona: nadie tiene bloques mientras está ausente.
- Si el hackathon dura más de unas 20 horas, incluye turnos de descanso; descansa antes quien presenta.

## Reparto

- Cada carpeta o pieza tiene **un solo dueño**, que es quien escribe en ella; los demás la leen. Asigna según los puntos fuertes de `equipo.md` y los perfiles que pide la decisión.
- **Todo lo que creó el scaffold tiene dueño**, también lo que no es de ninguna pieza: los ficheros de la raíz (manifiesto, README, `.gitignore`), el comando de arranque y su script, `.claude/` (reglas y guías de pasos) y las carpetas de datos o de salida. Lo mismo para toda carpeta o fichero en el que escriba alguna tarea del plan. Repásalo con Glob antes de guardar: nada sin dueño y nada con dos.
- Nadie se queda sin carpeta ni sin papel. Quien presenta tiene tiempo para preparar el pitch.
- Cada tarea, redactada para que la pueda ejecutar un agente: qué ficheros toca y cuándo está hecha. Una tarea es una sola acción con un resultado comprobable.
- **Dependencias solo donde alguien bloquea a otro**, y cada una con cómo desbloquear antes (por ejemplo, trabajar contra el contrato acordado con datos falsos).
- **Repliegues solo en los hitos críticos** (los que ponen en riesgo la entrega o la demo): qué se recorta si no se llega y quién lo decide.
- Las preguntas abiertas del análisis que afecten al plan, con dueño y hora límite para preguntarlas.
- No inventes requisitos que no estén en el análisis ni en la decisión. Las tareas son del enfoque elegido y de nada más. Lo que des por existente sin que lo diga el análisis (un ejemplo oficial, una herramienta, una licencia) va con `(conocimiento externo, verificar)`, y lo que dependa de una ambigüedad abierta, como supuesto hasta que la organización responda.

## Tamaño

- **Una tarea por fila**, con su propia comprobación. Un bloque ocupa como máximo **3 filas**: la primera lleva la hora y el nombre del bloque, y las siguientes dejan esas dos celdas vacías. Nunca juntes varias tareas en una celda con «;», «,» o frases seguidas: si un bloque necesita más de 3, divídelo en dos bloques o recorta.
- La sección de cada persona **cabe en una pantalla**: unas 10 filas como máximo. Cada tarea, en una línea corta (unas 15 palabras), y cada comprobación, en menos de 10.
- Lo que ya está en «Hitos del equipo» (ensayos, entregas, defensa, congelación) no se repite como tarea en la sección de cada persona.
- El plan entero se lee en **cinco minutos** (unas 1.100 palabras como máximo).
- Si no cabe, quita tareas menores o recorta detalle; juntar tareas en una celda no cuenta como recortar. No añadas secciones a la plantilla.

## Guardar

1. Escribe el plan en `.hackathon/plan.md` siguiendo la plantilla. Si ya existe, pregunta con AskUserQuestion si sobrescribirlo (el equipo puede haberlo editado). Si no puedes preguntar, no lo sobrescribas: di cómo seguir y para.
2. Si existe el `CLAUDE.md` del proyecto, **enseña la sección `## Dueños` que vas a añadir y pregunta con AskUserQuestion antes de modificarlo** ("Añadirla al CLAUDE.md" / "No tocar el CLAUDE.md"). Es una tabla "Carpeta | Dueño", con la raíz y el arranque incluidos, más la línea "Plan completo: `.hackathon/plan.md`", y va antes de `## Contexto` (si ya hay una sección `## Dueños`, se sustituye). Solo si el usuario acepta, aplícala con Edit, sin tocar nada más del fichero ni meter el calendario. Si no puedes preguntar o el usuario no acepta, no modifiques el `CLAUDE.md`: deja la sección en el resumen para que la pegue a mano.

## Autoridad (solo con la coordinación activa)

Si existe `.hackathon/coordinacion.md` con `activa: sí`, genera también `.hackathon/autoridad.md` siguiendo `${CLAUDE_SKILL_DIR}/templates/autoridad.md`; si no, no lo crees ni lo menciones.
- Una sección por persona de `## Dueños`, con su usuario de GitHub de `coordinacion.md`.
- Sus filas salen de sus carpetas (implementación interna: agente solo), de los bloques de `docs/contratos.md` que produce (agentes + confirmación) y de lo que el plan deja a su cargo que afecte a otros. Nada que no esté en el plan, los dueños o los contratos.
- Lo de «Siempre solo humano» se queda como en la plantilla; añade solo los repliegues del plan que haya.
- Si ya existe, pregunta antes de sobrescribirlo, como con `plan.md`.

## Resumen

Termina con, en pocas líneas: los hitos clave con hora, qué hace cada persona en la primera hora y qué conviene preguntar ya a la organización.
