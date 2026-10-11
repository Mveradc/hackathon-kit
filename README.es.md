# hackathon-kit

[English](README.md) · **Español**

Plugin de Claude Code que, a partir del enunciado de un reto de hackathon, deja al equipo listo para programar: analiza el reto, propone enfoques para que elijáis, genera el repositorio, el plan por persona y el guion del pitch, y lo verifica todo contra el enunciado.

**Para quién:** equipos de hackathon que usan Claude Code y quieren pasar del enunciado al primer commit sin perder la primera hora. Los prompts y las plantillas están en español, y el kit solo se ha validado en español.

<!-- TODO: GIF de uso -->
<!-- ![Demo](docs/demo.gif) -->

## Instalación

Dentro de una sesión de Claude Code:

```
/plugin marketplace add Mveradc/hackathon-kit
/plugin install hackathon-kit@hackathon-kit
```

O desde la terminal:

```
claude plugin marketplace add Mveradc/hackathon-kit
claude plugin install hackathon-kit@hackathon-kit
```

Para actualizar: `/plugin marketplace update hackathon-kit`. Para probarlo sin instalar, clona el repo y lanza `claude --plugin-dir <ruta al repo>`.

Comprueba que `/hack` muestra los seis comandos. Cada uno se invoca como `/hack-<nombre>` o `/hackathon-kit:hack-<nombre>`.

## Flujo

Lánzalo en la carpeta vacía del proyecto. Cada comando lee el fichero del paso anterior en `.hackathon/`, que puedes editar a mano entre paso y paso.

```
/hack-analyze <reto> → /hack-approaches → tú eliges → /hack-scaffold <stack>
   → rellenas equipo.md → /hack-plan → /hack-pitch → /hack-check
```

| Comando | Qué hace | Escribe |
|---|---|---|
| `/hack-analyze <texto, fichero o URL>` | Qué piden, cómo se evalúa, restricciones, ambigüedades y riesgos. No propone soluciones. | `.hackathon/analisis.md` |
| `/hack-approaches [perfil del equipo]` | 2–3 enfoques realmente distintos, justificados con los criterios de evaluación. **No elige por ti**: te pregunta. | `enfoques.md`, `decision.md` |
| `/hack-scaffold [stack]` | CLAUDE.md del proyecto, reglas, skills, contratos entre piezas, README y un hola mundo que arranca con un solo comando. Sin lógica de la aplicación. | el repositorio |
| `/hack-plan [ajustes]` | Hitos con hora, tareas por persona, dependencias y repliegues, a partir de `equipo.md` (plantilla en `skills/hack-plan/templates/`). Añade los dueños por carpeta al CLAUDE.md. | `plan.md` |
| `/hack-pitch [ajustes]` | Guion por bloques con tiempo, criterio que cubre y quién habla; preguntas probables del jurado y cifras que hay que medir. | `pitch.md` |
| `/hack-check [aplicar]` | Contrasta cada afirmación con la frase del enunciado que la sostiene y revisa las causas de descalificación. Con tu aprobación, rebaja o quita lo que no tiene respaldo. | `verificacion.md` |

Ejemplos de salida de dos retos reales, en `skills/*/examples/`.

## Coste y tiempo

- **Coste aproximado por cadena completa:** unos 4–5 USD por reto. Con la v0.1.0, 4,7 USD en los retos 02 y 03 (`claude -p`); `/hack-check` es el paso más caro, unos 1,5 USD.
- **Tiempo de los comandos:** unos 15 minutos por cadena en `claude -p`, sin contar a las personas.
- **Tiempo real, incluidos leer y decidir:** [PENDIENTE: pasada interactiva]

## Limitaciones principales

Lo generado es un punto de partida, no un plan cerrado. Las más importantes:

- **Eventos que prohíben el trabajo previo.** Si las bases exigen que todo se cree durante el evento, generar el repo, el plan o el pitch antes puede descalificar al equipo. `/hack-scaffold` lo detecta y solo genera si confirmas que el evento ha empezado. Lanza el scaffold, el plan y el pitch al empezar.
- **Ejecuta siempre `/hack-check` y revisa a mano.** Sin el check, la cadena da por ciertas inferencias y ambigüedades. Aun con él, un revisor independiente concluyó en los cinco retos de la validación que el equipo empieza antes y mejor solo *en parte*: el calendario, el reparto, las ausencias y las preguntas a la organización hay que cerrarlos vosotros.
- **Coherencia del plan tras el check.** Cuando el check añade filas al plan, no actualiza el resto (descansos, dependencias, repliegues). Revisa que el plan siga siendo coherente.
- **Enunciados por URL.** Con una URL, el análisis trabaja sobre un resumen de la página, no sobre el texto literal. Pega el texto si puedes.

Lista completa: [docs/limitaciones.md](docs/limitaciones.md).

## Validación

El kit se ha probado con seis retos (cinco reales y uno sintético) y una rúbrica con comprobaciones automáticas y de criterio: [evals/rubrica.md](evals/rubrica.md). Los enunciados de terceros no se publican; las fuentes están en [evals/retos/fuentes.md](evals/retos/fuentes.md).

## Licencia

[MIT](LICENSE)
