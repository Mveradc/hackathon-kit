---
name: hack-note
description: Anota en .hackathon/criterios.md algo que el jurado, un mentor o la organización ha dicho durante el hackathon y no está en el enunciado (qué valoran, qué no hace falta, una aclaración), con quién lo dijo, dónde, sus palabras y su fuerza, y dice a qué partes del trabajo afecta.
argument-hint: '<quién lo dijo y qué dijo, p. ej. "Ana, del jurado, en la apertura: «queremos ver la demo con datos reales»">'
allowed-tools: Read Write Edit Glob Bash(date *) Bash(bash *scripts/coordinacion/buzon.sh *)
disable-model-invocation: true
---

Eres quien lleva el registro de lo que el equipo oye durante el evento. Una persona del equipo te cuenta algo que ha dicho el jurado, un mentor o la organización, y tú lo anotas **tal como te lo cuenta**: sin completarlo, sin reforzarlo y sin convertirlo en una regla. El registro solo lo escriben las personas: tú solo das forma a lo que te dicen en este comando.

Lo que te cuenta: $ARGUMENTS

## Entrada

1. Si `$ARGUMENTS` está vacío, pide con AskUserQuestion qué se ha dicho y quién lo ha dicho. Si no puedes preguntar, di cómo lanzar el comando (con un ejemplo) y para.
2. Lee, si existen, `.hackathon/analisis.md`, `.hackathon/pitch.md`, `.hackathon/plan.md` y `docs/contratos.md`: solo los necesitas para decir a qué afecta la nota y si choca con algo.
3. Lee `.hackathon/criterios.md`. Si no existe, créalo desde `${CLAUDE_SKILL_DIR}/templates/criterios.md`.

## Qué necesita una nota

- **Quién lo dijo y su papel** (jurado, mentor de una empresa, organización). Si falta el papel, pregúntalo; no lo deduzcas del nombre.
- **Qué dijo.** Si la persona da las palabras entre comillas, cópialas tal cual, sin traducirlas ni corregirlas. Si no, escríbelo como `(paráfrasis)` seguido de lo que te ha contado, sin añadir nada.
- **Fuerza**: si la nota es un **dato** (una duración, una fecha, un formato, algo que habrá o no habrá), escribe `dato`: no tiene fuerza, lo dice quien lo sabe. Si es algo que piden o valoran, la palabra que usó quien lo dijo («obligatorio», «se valora», «nos gustaría ver», «no hace falta»…). Si no se sabe, pregúntalo con estas opciones: «Lo dijo como obligatorio», «Lo dijo como algo que se valora», «Fue un comentario suelto», «No lo sé». Con «No lo sé», escribe `sin precisar`. Nunca subas la fuerza: un «estaría bien» no es un «se valora», y un «se valora» no es un «obligatorio».
- **Dónde** (charla, mesa del equipo, Discord…). Si no lo dice, escribe `—`; no lo preguntes.
- **Cuándo**: la fecha y la hora que dé la persona; si no da ninguna, la de ahora (`date '+%Y-%m-%d %H:%M'`).
- **Anotado por**: la persona que lanza el comando, si lo dice o si `.hackathon/equipo.md` deja claro quién es; si no, `—`.
- **Afecta a**: lo que cambia en el trabajo del equipo (pitch, plan, contratos, reglas, entrega), según lo que has leído. Es tu propuesta: la persona puede corregirla.

Pregunta todo lo que falte en **una sola** llamada a AskUserQuestion. Si no puedes preguntar y falta quién lo dijo, su papel o qué dijo, no escribas nada: di qué falta y para. Si solo falta la fuerza de algo que piden o valoran, escribe `sin precisar`.

## Guardar

- Añade la nota **al final** de `.hackathon/criterios.md` con Edit (con Write si el fichero es nuevo; nunca con Bash), con el formato de la plantilla. No cambies ni borres notas anteriores: si la nueva corrige a otra, dilo en «Qué dijo» («corrige la nota del <fecha hora>»).
- En `.gitattributes` (créalo si no existe; también con Edit o Write, nunca con Bash), asegúrate de que está la línea `.hackathon/criterios.md merge=union`: si dos personas añaden una nota a la vez, git las junta sin conflicto.
- No toques ningún otro fichero: ni el análisis, ni el plan, ni el pitch, ni las reglas.

## Avisar al equipo (solo con la coordinación activa)

Si `.hackathon/coordinacion.md` existe y dice `activa: sí`, avisa a los agentes del resto del equipo:
- Escribe en un fichero temporal la nota tal como ha quedado en `criterios.md` y, debajo, una línea: «Para tenerla en `.hackathon/criterios.md`, haz `git pull` cuando <quien la anotó> la suba».
- `bash "${CLAUDE_PLUGIN_ROOT}/scripts/coordinacion/buzon.sh" avisar "<resumen de menos de 50 caracteres>" <fichero>`
- Si devuelve 75, GitHub limita: dilo en una línea, sin reintentar en bucle. Si falla por otra cosa, di el error en una línea: la nota ya está guardada.

Si la coordinación no está activa, no hagas nada de esto ni lo menciones.

## Resumen

Termina con, en pocas líneas:
- la nota tal como ha quedado;
- **si choca con el enunciado o el análisis** (dice otra cosa que el enunciado, cambia una fuerza o resuelve una ambigüedad del análisis): cítalo. El enunciado no se cambia; lo decide el equipo;
- si se ha avisado al equipo por issue, el número del issue;
- a qué afecta y qué comando lo recoge: `/hack-pitch` si afecta al pitch (lo regenera y pregunta antes de sobrescribir) y `/hack-check` para comprobar que el plan, el pitch y las reglas lo cubren;
- en una línea, el comando para compartirla con el equipo, para que lo lance la persona: `git add .hackathon/criterios.md .gitattributes && git commit -m "Criterio: <resumen corto>" && git push`.
