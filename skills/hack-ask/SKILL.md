---
name: hack-ask
description: Coordinación entre agentes (hackathon-kit). Pregunta al agente de otra persona del equipo por GitHub Issues, sin bloquearte, cuando una duda depende de una carpeta o un contrato que no es tuyo. Solo si .hackathon/coordinacion.md tiene la coordinación activa.
argument-hint: <persona o @usuario> <pregunta>
allowed-tools: Read Write Edit Bash(bash *scripts/coordinacion/buzon.sh *)
---

Eres el agente de una persona del equipo y necesitas algo que decide otra. En lugar de parar o de pedir a tu persona que vaya a preguntar, se lo preguntas a su agente por el buzón y **sigues trabajando** con una suposición provisional.

Petición: $ARGUMENTS

## Antes de preguntar
1. Lee `.hackathon/coordinacion.md`. Si no existe o no dice `activa: sí`, dile a tu persona que la coordinación no está activada (se activa en `/hack-scaffold` o editando ese fichero) y para.
2. Lee `.hackathon/autoridad.md` y la sección `## Dueños` del CLAUDE.md: ¿de quién es lo que preguntas y qué nivel tiene?
   - Si es tuyo y del nivel «Agente solo», no preguntes: decídelo tú.
   - Si es **solo humano** (enfoque, alcance, recortes, pitch, calendario, reparto, ambigüedades con la organización), no se lo preguntes al otro agente: díselo a tu persona. Si te lo pide, abre el issue con tipo `humano` y nivel `humano` para que lo vean las personas.
3. Busca en `.hackathon/decisiones.md` y en `docs/contratos.md`: si ya está decidido, no preguntes.

## Preguntar
- Escribe la pregunta en un fichero temporal: qué necesitas, por qué, qué opciones ves y cuál propones, en menos de 120 palabras. Que se entienda sin tu contexto. Nunca escribas «hk confirmo»: solo lo escribe una persona.
- Tipo: `contrato` si cambia algo de `docs/contratos.md`; si no, `pregunta`. Nivel, según `autoridad.md`: `agente` o `confirmacion`. Dueño: el usuario de GitHub de quien decide.
- Publica:
  `bash "${CLAUDE_PLUGIN_ROOT}/scripts/coordinacion/buzon.sh" preguntar <usuario> <tipo> <nivel> <dueño> "<asunto de menos de 60 caracteres>" <fichero>`
- Si devuelve 75, GitHub limita: dilo y reintenta más tarde, sin insistir en bucle.

## Seguir trabajando
- Anota en `.hackathon/estado/<tu usuario>.md` (créalo si no existe; solo lo escribes tú), en «Suposiciones provisionales»: `#<n> (esperando a @<usuario>): asumo <X>; si responde otra cosa, <qué habría que cambiar>`.
- Continúa con tu tarea según esa suposición. Cuando llegue la respuesta, el monitor del buzón te avisará («hk #…»): atiéndela con `/hack-inbox`.
- A tu persona, solo una línea: qué has preguntado, a quién y qué has supuesto mientras tanto.

Formato de `.hackathon/estado/<usuario>.md` (menos de 25 líneas):
```
# Estado de @<usuario>
## En qué estoy
## Suposiciones provisionales
## Esperando
```
