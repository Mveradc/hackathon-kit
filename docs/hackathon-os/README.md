# Hackathon OS (M8) · especificación

Estado: **propuesta**. No hay código todavía. Este directorio especifica el M8 de hackathon-kit: una vista común y en tiempo real de qué se está haciendo, qué está hecho y qué falta, para todo el equipo (personas y agentes), construida sobre lo que ya existe (cadena, buzón, orquestador, compuerta y revisor). No se empieza desde cero.

## Problema
Hoy el estado del equipo está repartido en cuatro sitios que no se ven entre sí:
- `.hackathon/` en git (plan, decisiones, criterios): solo llega a los demás cuando alguien hace commit y push.
- GitHub Issues (buzón `hk`): mensajes, sin noción de tarea.
- `.hackathon/estado/` y `refs/hackathon/fusion/*` de cada orquestador, los informes de `<git común>/hackathon/informes/` y los contadores de la compuerta: todo local a cada portátil.
- Las sesiones de Claude Code: qué fichero está tocando cada agente o worker ahora mismo no lo sabe nadie más.

Nadie puede contestar sin preguntar en voz alta «¿quién está con X?», «¿esto ya está en main?» o «¿vamos a chocar en este fichero?».

## Objetivo
Una **proyección**, no una plataforma: un único modelo de estado (`estado.json`) que se calcula a partir de señales (hooks, git, eventos del orquestador, GitHub) y se muestra igual a personas (web) y a agentes (markdown inyectado y MCP). Nadie declara el estado a mano. El diferencial es avisar de colisiones antes de fusionar.

## Cómo leer esto (y cómo lo usa Claude Code)
En este orden. Cada fichero cita los requisitos (`R-xx`) y las decisiones (`ADR-xxxx`) que aplica.

| Fichero | Qué contiene |
|---|---|
| [constitucion.md](constitucion.md) | Invariantes que ningún hito puede romper. Si una tarea choca con una, para y pregunta. |
| [requisitos.md](requisitos.md) | Qué tiene que hacer el sistema y por qué, con criterios de aceptación en formato EARS. Sin el *cómo*. |
| [diseno.md](diseno.md) | Componentes, flujo de datos, modelo de actores, ciclo de vida de una tarea y dónde vive cada dato. |
| [adr/](adr/) | Decisiones de arquitectura, cada una con alternativas descartadas. Las marcadas «propuesta» las decide el usuario. |
| [contratos/](contratos/) | Esquema de eventos, esquema de `estado.json`, API del relay y del demonio, herramientas MCP. Se congelan antes de implementar. |
| [hitos.md](hitos.md) | M8.0–M8h: objetivo, alcance y criterios de validación de cada hito, al estilo de `docs/coordinacion.md`. |
| [tareas.md](tareas.md) | Tareas con ID, requisito que cubren, `[P]` si se pueden hacer en paralelo y «Hecho cuando» ejecutable. Mismo formato que un encargo del orquestador. |
| [simulador.md](simulador.md) | Guiones de equipo simulado que alimentan los criterios de validación y acaban en `evals/`. |
| [preguntas-abiertas.md](preguntas-abiertas.md) | Lo que hay que verificar antes de comprometer una decisión (Paso 0). |

Reglas para quien implemente (persona o agente):
- Un hito a la vez y solo lo que su validación exige (regla del CLAUDE.md del kit). Lo útil para más adelante va a «Pendiente».
- Antes de tocar código, comprueba que el contrato que aplica está en `contratos/` y no tiene `[POR DECIDIR]`. Si lo tiene, para y pregunta.
- Las marcas `[POR DECIDIR: …]` son preguntas abiertas: no se rellenan con una suposición.
- Todo el M8 es opcional: con el OS desactivado, el kit se comporta exactamente como la 0.3.2.

## Prior art revisado
- [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability): hooks → POST → servidor → WebSocket → interfaz. Referencia del sobre de evento y del flujo.
- [steveyegge/beads](https://github.com/steveyegge/beads): «listo» = sin bloqueos abiertos, reclamar atómico, salida `--json` estable.
- [Backlog.md](https://github.com/MrLesk/Backlog.md): tablero web local, MCP, `--json --watch`.
- [Vibe Kanban](https://virtuslab.com/blog/ai/vibe-kanban/): ciclo de vida tarjeta → worktree → revisión → fusión, en una sola máquina.
- MCP Agent Mail: reservas consultivas de ficheros con TTL y guard en pre-commit.
- [Mergiraf](https://mergiraf.org/architecture.html): fusión estructural con tree-sitter que vuelve a la fusión por líneas si no puede analizar.
- Palantír (ICSE 2003) y Crystal (ESEC/FSE 2011): conciencia de espacio de trabajo y detección especulativa de conflictos.

Ninguno coordina varias personas en varias máquinas con autoridad humana (`autoridad.md`), deriva el estado del revisor y la compuerta, ni trata los criterios del jurado como dato. Ese es el hueco.
