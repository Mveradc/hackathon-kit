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

Comprueba que `/hack` muestra los diez comandos: los seis de la cadena, `/hack-note` y los tres de coordinación entre agentes. Cada uno se invoca como `/hack-<nombre>` o `/hackathon-kit:hack-<nombre>`.

## Flujo

Lánzalo en la carpeta vacía del proyecto. Cada comando lee el fichero del paso anterior en `.hackathon/`, que puedes editar a mano entre paso y paso.

```
/hack-analyze <reto> → /hack-approaches → tú eliges → /hack-scaffold <stack>
   → rellenas equipo.md → /hack-plan → /hack-pitch → /hack-check
```

| Comando | Qué hace | Escribe |
|---|---|---|
| `/hack-analyze <texto, fichero o URL>` | Qué piden, cómo se evalúa, restricciones, ambigüedades y riesgos. No propone soluciones. | `.hackathon/analisis.md` |
| `/hack-approaches [perfil del equipo]` | 2–3 enfoques realmente distintos, justificados con los criterios de evaluación. Si existe `.hackathon/equipo.md`, dice después cómo encaja cada uno con vuestro equipo (quién cubre qué, huecos, ausencias), sin cambiar los enfoques. **No elige por ti**: te pregunta. | `enfoques.md`, `decision.md` |
| `/hack-scaffold [stack]` | CLAUDE.md del proyecto, reglas, skills, contratos entre piezas, README y un hola mundo que arranca con un solo comando. Sin lógica de la aplicación. También escribe `.claude/settings.json` para que los commits y PR que haga Claude no lleven su coautoría, salvo que las bases pidan declarar el uso de IA. | el repositorio |
| `/hack-plan [ajustes]` | Hitos con hora, tareas por persona, dependencias y repliegues, a partir de `equipo.md` (plantilla en `skills/hack-plan/templates/`). Añade los dueños por carpeta al CLAUDE.md. | `plan.md` |
| `/hack-pitch [ajustes]` | Guion por bloques con tiempo, criterio que cubre y quién habla; preguntas probables del jurado y cifras que hay que medir. | `pitch.md` |
| `/hack-check [aplicar]` | Contrasta cada afirmación con la frase del enunciado que la sostiene y revisa las causas de descalificación. Con tu aprobación, rebaja o quita lo que no tiene respaldo. | `verificacion.md` |
| `/hack-note <quién y qué dijo>` | Durante el evento, anota lo que dicen el jurado, los mentores o la organización y no está en el enunciado: quién, sus palabras y su fuerza, sin reforzarla. `/hack-pitch` y `/hack-check` lo tienen en cuenta. | `criterios.md` |

Ejemplos de salida de dos retos reales, en `skills/*/examples/`.

## Coordinación entre agentes (opcional, experimental, desde la 0.2.0)

> **Experimental.** Validada en un repo sandbox privado con una persona simulando al equipo (dos cuentas, dos sesiones), todavía no con un equipo real.

Cuando cada persona trabaja con su propio Claude Code, las preguntas entre piezas suelen ir agente → persona → persona → agente. Con la coordinación activada, los agentes se preguntan entre sí por GitHub Issues, y a las personas solo llegan las decisiones de diseño, producto o pitch.

- Se activa en `/hack-scaffold` (pregunta; por defecto, no). Guarda en `.hackathon/coordinacion.md` el repo y el usuario de GitHub de cada persona, y `/hack-plan` añade `.hackathon/autoridad.md`: qué decide cada agente solo, qué necesita la confirmación de su dueño y qué es solo de personas.
- `/hack-ask` pregunta a otro agente sin bloquearse (trabaja con una suposición provisional), `/hack-inbox` atiende lo que llega y `/hack-decide` cierra un acuerdo en `.hackathon/decisiones.md`. Un monitor en segundo plano consulta el repo cada minuto y no dice nada si no hay novedades.
- Un cambio de contrato solo se cierra cuando su dueño comenta exactamente `hk confirmo` desde su cuenta de GitHub. Los desacuerdos largos y los bucles se cortan y se escalan a las personas.
- Cada nota de `/hack-note` se avisa a todo el equipo: el agente de cada persona se la resume y le dice que haga `git pull`.
- Requisitos: `gh` con la cuenta de cada persona, Git Bash en Windows y sesión interactiva (no `claude -p`). Depende de los monitores de plugin, una función experimental de Claude Code.
- Desde la 0.3.0, un hook impide a cualquier agente publicar `hk confirmo` con `gh`. Es una red, no una garantía: el agente usa el `gh` de su persona y podría rodearla.

## Orquestador (opcional, experimental, desde la 0.3.0)

> **Experimental.** Validado en una copia de prueba de un reto real con una persona simulando al equipo, todavía no con un equipo real.

Un orquestador por persona toma sus tareas de `.hackathon/plan.md` y las saca adelante sin escribir código él mismo:

```
claude --agent hackathon-kit:orquestador
```

- Parte cada bloque del plan en encargos pequeños y se los da a **workers** (Sonnet), como mucho dos a la vez, cada uno en su propio worktree de git. Un hook impide al orquestador (Opus) editar código.
- Fusiona la rama de cada worker **fuera de tu rama**. Un **revisor** independiente (Sonnet) comprueba esa fusión en su propio worktree y vuelve a ejecutar la comprobación, sin ver el informe del worker. Tu rama solo avanza (en rápido) hasta fusiones aprobadas. Si el revisor pide cambios dos veces, la tarea queda sin cerrar y tu rama no se toca.
- Sube sus fusiones aprobadas (nunca forzando), pero nunca hace commit ni push de tu trabajo.
- El avance queda en `.hackathon/estado/<persona>.md`. **Reinicia el orquestador al terminar cada bloque**: su contexto crece con cada encargo, y una sesión nueva retoma desde el estado sin repetir lo fusionado. También se recupera tras un corte: vuelve a revisar la fusión pendiente y te pregunta qué hacer con los worktrees que quedaron, sin borrar nada por su cuenta.
- Coste: unos 0,9–1,6 USD por bloque de uno o dos encargos, casi todo del orquestador.

## Hackathon OS (opcional, experimental, desde la 0.4.0)

> **Experimental.** Validado sin modelo (más de 600 pruebas y las evals de `evals/coordinacion/`) y en un repo de prueba con una persona simulando al equipo. **Todavía sin ensayo con un equipo real.**

Que todo el equipo sepa quién hace qué, qué está ya en `main` y dónde vais a chocar, sin preguntarlo en voz alta. Se enciende con `activa: sí` en `.hackathon/os.md`; apagado, todo funciona como en la 0.3.2.

- **Estado del equipo.** Un demonio por persona (sin modelo) cuenta lo que pasa en su clon y un relay en el portátil de quien coordina lo junta. Cada sesión recibe al empezar un bloque «Equipo» corto y, en cada turno, solo lo que ha cambiado y la afecta. Un servidor MCP `os` responde `estado`, `tarea` y `colisiones`. Lo viejo se dice como viejo, con su hora.
- **Avisos de colisión, nunca bloqueos:** dos personas en el mismo fichero, cambios incompatibles antes de fusionar (opcional, con `publicar_wip: sí`) y contratos tocados por quien no es su dueño.
- **Fusión estructural con Mergiraf** (desde la 0.6.0, `fusion_estructural: sí`, además de `publicar_wip: sí`): un conflicto de git que [Mergiraf](https://codeberg.org/mergiraf/mergiraf) (0.20.0 o posterior) fusiona sin conflictos baja de rojo a amarillo (`nivel 2b · fusión estructural sin conflictos`). Solo hace falta en el portátil de quien coordina (el del relay), instalado a mano: el binario de la release oficial en Windows (x86_64) y Linux, `brew install mergiraf` en macOS, o `cargo install --locked mergiraf` (lo único en Windows en ARM). El kit no lo instala ni lo pide. Solo sirve en los lenguajes que Mergiraf analiza (Python, JavaScript, TypeScript, JSON, YAML, TOML, HTML, Markdown, Java, Go, Rust…); CSS, SQL, `.txt` y `.ipynb` siguen en rojo. «Amarillo» no quiere decir que la fusión funcione: revisadla.
- **Web de trabajo** (`web_nueva: sí`): la sirve el demonio de cada persona en `127.0.0.1` y la abre `hk-os web`. Cuatro vistas (cabina, red, tablero y servicios) y dos acciones: **Anotar** (añade una nota a `criterios.md` de `origin/main` sin tocar tu copia) y **Reclamar** (asigna el issue con tu `gh` y abre un turno en tu sesión). Nadie instala Node: la web va compilada.
- **`.hackathon/servicios.md`**: puertos, rutas de salud y conexiones entre piezas. Una fila solo sale confirmada si su dueño la subió en un commit hecho en su portátil.
- **Vista de jurado y ruta crítica** (desde la 0.5.0, cada una con su interruptor en `.hackathon/os.md`: `vista_jurado: sí`, `ruta_critica: sí`): qué tarea o evidencia cubre cada nota de `criterios.md`, y si se llega a la `Entrega:` de `equipo.md` (los plazos pasados y lo que arrastran, la cadena y una estimación con rango solo a partir de 3 tareas medidas por persona). Salen en la web de trabajo, en una línea cada una del estado del equipo y en las herramientas `jurado` y `ruta` del MCP. Apagadas, todo es byte a byte como en la 0.4.0.
- **Sin GitHub:** un remoto del equipo en el portátil de quien coordina y las tareas desde `plan.md`.
- **Requisitos:** uv, Git (2.38 o más en el portátil de quien coordina), `gh` con la cuenta de cada persona y, en macOS, bash 5 (`brew install bash`). El relay habla HTTP sin cifrar: en una red que no sea de confianza, Tailscale o ZeroTier.
- Guion de arranque en 10 minutos: [docs/hackathon-os/arranque.md](docs/hackathon-os/arranque.md). Diseño, contratos y decisiones: [docs/hackathon-os/](docs/hackathon-os/).

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
- **Un servidor MCP `os` en `/mcp`.** El servidor del estado del equipo del Hackathon OS lo declara el plugin, así que sale en `/mcp` en toda sesión, también con el OS apagado. Entonces no ofrece herramientas, no usa red y no necesita uv.
- **`publicar_wip: sí` sube tu trabajo sin commit.** En el Hackathon OS, esa opción de `.hackathon/os.md` sube al remoto lo versionado cambiado y lo nuevo que `.gitignore` no ignora. Excluye `.env*`, claves comunes, carpetas de datos y ficheros grandes, pero ninguna lista es completa: revisa el `.gitignore` antes. Borrar la ref no borra lo subido; una clave que suba hay que rotarla. Viene apagada.
- **El Hackathon OS no se ha ensayado con un equipo real.** Se ha validado sin modelo y en un repo de prueba con una persona simulando al equipo. Usadlo como un experimento y seguid hablando entre vosotros. La estimación de la ruta crítica (3 tareas medidas por persona, los umbrales del veredicto y el ritmo medido) tampoco se ha probado con datos reales, y las tareas de quien no tiene cuenta de GitHub no se miden. El nivel 2b con Mergiraf solo se ha probado con un fichero pequeño y dos personas, en Linux y en runners de Windows y macOS, no en un portátil real ni con el código de un reto.

Lista completa: [docs/limitaciones.md](docs/limitaciones.md).

## Validación

El kit se ha probado con seis retos (cinco reales y uno sintético) y una rúbrica con comprobaciones automáticas y de criterio: [evals/rubrica.md](evals/rubrica.md). Los enunciados de terceros no se publican; las fuentes están en [evals/retos/fuentes.md](evals/retos/fuentes.md).

## Licencia

[MIT](LICENSE)
