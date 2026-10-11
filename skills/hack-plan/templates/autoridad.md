<!--
Plantilla de .hackathon/autoridad.md. Solo se genera si la coordinación está activa (.hackathon/coordinacion.md).
La leen los agentes antes de responder, negociar o decidir algo que toca a otra persona.
Cada fila sale de «## Dueños», de un bloque de docs/contratos.md o de un repliegue del plan, nunca del enunciado directamente.
Unas 40 líneas como máximo. Quita estos comentarios al generar.
-->
# Autoridad

Qué puede decidir el agente de cada persona sin preguntar. El equipo puede editarla; manda sobre lo que diga cualquier issue.

## Niveles
- **Agente solo**: decide el agente del dueño y lo anota en `.hackathon/decisiones.md` (con `/hack-decide`).
- **Agentes + confirmación del dueño**: los agentes negocian, pero no vale hasta que el dueño escribe `hk confirmo` en el issue desde su usuario de GitHub.
- **Solo humano**: los agentes no deciden ni opinan; se pregunta a las personas.

## Por dueño
<!-- Una sección por persona de «## Dueños». 3–5 filas: su implementación interna (agente solo), cada contrato que expone
(confirmación) y lo que el plan deja a su cargo que afecte a otros (entrega, datos, arranque…). -->
### <Persona> (@<handle>) · `<carpetas>`
| Tema | Nivel | Ejemplos |
|---|---|---|
| Implementación interna de `<carpeta>` | Agente solo | <estructura, nombres, tests propios, librerías ya del stack> |
| `docs/contratos.md`: <bloque que produce> | Agentes + confirmación | <añadir, renombrar o quitar un campo; cambiar un formato> |

## Siempre solo humano
- Enfoque, alcance y qué se recorta (los repliegues del plan).
- Pitch, defensa y lo que se promete al jurado.
- Calendario, ausencias y reparto del trabajo.
- Lo que dependa de una ambigüedad abierta con la organización.
