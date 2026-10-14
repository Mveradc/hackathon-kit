# Diseño

Cómo se cumplen los requisitos. Las decisiones con alternativas están en `adr/`; los formatos exactos, en `contratos/`.

## 1. Vista general

```
 portátil de cada persona                                   portátil coordinador
 ┌──────────────────────────────────────────────┐          ┌──────────────────────────────┐
 │ Claude Code (sesión, orquestador, workers,   │          │ hk-os relay                   │
 │ revisor)                                     │          │  · presencia y reservas (TTL) │
 │   hooks del plugin (bash, async)             │          │  · registro de eventos (JSONL)│
 │      │ una línea JSON por evento             │  HTTP    │  · sondeo de GitHub (ETag)    │
 │      ▼                                       │ ───────▶ │  · motor de estados           │
 │ <git común>/hackathon/os/eventos/*.jsonl     │  token   │  · estado.json                │
 │      │                                       │ ◀─────── │  · web + SSE                  │
 │      ▼                                       │  SSE     └──────────────┬───────────────┘
 │ hk-os agente (demonio local)                 │                         │ gh api (solo él)
 │  · lee los JSONL y git (status, worktrees,   │                         ▼
 │    refs/hackathon/*)                         │                   GitHub Issues
 │  · reenvía al relay, recibe estado.json      │                   (hk-tarea, buzón hk)
 │  · escribe estado-equipo.md (para hooks)     │
 │  · MCP stdio para los agentes                │
 └──────────────────────────────────────────────┘
```

Tres capas, cada una útil sin la siguiente (constitución VIII):
1. **Emisión local**: hooks que escriben eventos en ficheros locales. Funciona sin red y sin demonio.
2. **Agregación**: el demonio de cada persona y el relay del equipo juntan los eventos, la presencia y GitHub en un modelo.
3. **Proyección**: `estado.json` → web (personas), `estado-equipo.md` (hooks de inyección) y MCP (agentes).

## 2. Componentes

| Componente | Qué es | Dónde corre | Escribe |
|---|---|---|---|
| `scripts/os/emite.sh` | Hook bash (`async: true`; síncrono en `SessionEnd`) que añade una línea JSON por evento, solo con los campos de la lista blanca de `api.md` §1 | Cada sesión y subagente | `<git común>/hackathon/os/eventos/<session_id>.jsonl` |
| `scripts/os/arbol.sh` | Hook bash en `Stop`, `SubagentStop` y `PostToolBatch`: `git status --porcelain` y diff contra la base del `cwd` | Cada sesión y subagente | Evento `arbol` |
| Cambios en `compuerta.sh` | Emite `compuerta.ok` / `compuerta.ko` con los motivos | Workers | Evento |
| `hk-os agente` | Demonio local: lee los JSONL, sondea git, habla con el relay, sirve MCP | Uno por persona y repo | `<git común>/hackathon/os/estado-equipo.md` |
| `hk-os relay` | Servidor HTTP + SSE: presencia, reservas, eventos, sondeo de GitHub, motor de estados, web | Portátil coordinador | `estado.json`, `<git común>/hackathon/os/relay/eventos.jsonl` |
| `hk-os compilar` | Compila `plan.md` a issues `hk-tarea` | Quien lo lanza | Issues |
| Cambios en `sesion.sh` | SessionStart: lanza el demonio si no responde en su puerto (ADR-0004) y añade el estado del equipo | Cada sesión | — |
| `scripts/os/delta.sh` | UserPromptSubmit: inyecta solo lo que cambió | Cada sesión | — |
| `scripts/os/reserva.sh` | PreToolUse Edit/Write: avisa si el fichero está reservado o en colisión | Cada sesión y subagente | — |

Lenguaje del demonio y del relay: Python con biblioteca estándar, lanzado con `uv run` (ADR-0005). Los hooks siguen en bash.

## 3. Actores

```
persona (usuario de GitHub)
  └─ sesión (session_id) · papel: principal | orquestador
       └─ subagente (agent_id) · papel: worker | revisor
humano (la persona actuando fuera de Claude Code: commits a mano, issues desde la web)
```

- El papel sale de `agent_type` (`hackathon-kit:orquestador`, `…:worker`, `…:revisor`; sin `agent_type`, `principal`).
- La persona sale de `hk_yo` (usuario de `gh`), igual que en el buzón.
- El worktree sale de `cwd` (en subagentes con `isolation: worktree`, `cwd` es la raíz del worktree: comprobado en M8.0, P4).
- Lo que una persona hace a mano se ve por git (commits, ramas, `git status` que sondea el demonio), como actor `humano`.

## 4. Recorrido de una señal

1. Claude Code dispara un hook. `emite.sh` lee la entrada (una línea JSON), copia solo los campos de la lista blanca (`api.md` §1) con regex de bash, sin `jq` y sin desescapar, les añade el sobre (`v`, `ts`, `persona`, `tipo`) y escribe la línea en el JSONL de su sesión. No usa red ni guarda contenido de ficheros. Coste: un proceso bash (≈37 ms en Windows).
2. El demonio sigue los JSONL (posición por fichero), parsea la entrada, normaliza al esquema de `contratos/eventos.schema.json` y la envía al relay en lotes (`POST /eventos`). Si el relay no responde, guarda la posición y reintenta.
3. Cada 15 s, el demonio sondea git: `git worktree list`, `git status --porcelain` por worktree, `refs/hackathon/fusion/*`, y si hay `origin`, qué commits de las fusiones ya están en `origin/main`. Emite lo que cambió.
4. El relay aplica cada evento al modelo (presencia, ficheros, reservas, señales por tarea), sondea los issues `hk-tarea` cada 30 s con ETag y recalcula `estado.json`. Lo publica por SSE.
5. Cada demonio recibe `estado.json`, escribe `estado-equipo.md` (resumen para su persona) y lo sirve por MCP. Los hooks de inyección solo leen ese fichero: nunca llaman a la red.

## 5. Ciclo de vida de una tarea

Estados derivados, en orden de avance. Cada uno con la señal que lo produce (constitución II).

| Estado | Señal | Fuente |
|---|---|---|
| `pendiente` | Issue `hk-tarea` abierto | GitHub |
| `lista` | `pendiente` y todas sus dependencias cerradas | GitHub (derivado) |
| `reclamada` | Asignada a una persona (`reclamar`, o asignación del compilador) sin actividad aún | GitHub / MCP (declarado) |
| `en curso` | Reclamada **y** actividad de un actor de su dueño en la tarea: encargo lanzado con su ID, o ediciones dentro de las carpetas de la tarea | Hooks / git |
| `parada` | `en curso` sin actividad en 20 min (R-14) | Derivado |
| `en revisión` | Existe `refs/hackathon/fusion/<ID>` o evento `fusion.creada` | git / hooks |
| `integrada` | Veredicto APROBADO y `main` local de su persona contiene la fusión | Hooks + git |
| `no cerrada` | Segundo CAMBIOS del revisor | Hooks |
| `publicada` | La fusión (o el commit humano que cierra la tarea) es alcanzable desde `origin/main` | git |
| `cerrada` | Issue cerrado por alguien del equipo | GitHub (declarado, ⚑ si no hay `publicada`) |

- Una tarea humana (sin orquestador) pasa de `en curso` a `publicada` cuando un commit que menciona su ID (`T07` en el mensaje) llega a `origin/main`. No hay `integrada` porque no hay revisor.
- `verificada` no existe como estado aparte: para el orquestador, APROBADO ya incluye volver a ejecutar la comprobación en un worktree limpio. Para tareas humanas, la verificación queda fuera de la v1 (ejecutar la «Cómo se comprueba» del plan es un extra).
- La transición la hace el motor de estados en el relay, una función pura `(señales de la tarea) → estado`, probada con tablas.

## 6. Cómo se detectan los eventos del orquestador

Sin tocar su lógica (está validada): se detectan con hooks sobre lo que ya hace. Lo único que cambia en su prompt es una línea `ID: Txx` en cada encargo.

| Evento | Cómo se detecta |
|---|---|
| `encargo.lanzado` | PreToolUse sobre `Agent` con `agent_type` orquestador y `subagent_type` worker: el emisor saca de `tool_input.prompt` solo `ID:` y `Base:` (campo comprobado en M8.0, P2) |
| `worker.inicio` / `worker.fin` | `SubagentStart` / `SubagentStop` con `agent_type` worker; el ID de la tarea, de la primera línea del transcript del worker (P3) |
| `compuerta.ok` / `compuerta.ko` | Lo emite `compuerta.sh` |
| `fusion.creada` | PostToolUse Bash del orquestador con `git update-ref refs/hackathon/fusion/<ID>`; el demonio lo confirma leyendo la ref |
| `revision.veredicto` | `SubagentStop` del revisor: `Veredicto:` y `Fusión:` de `last_assistant_message` |
| `fusion.aprobada` | PostToolUse Bash del orquestador con `git merge --ff-only <sha>`, confirmado porque `main` contiene el sha |
| `fusion.descartada` | `git update-ref -d refs/hackathon/fusion/<ID>` sin `ff-only` previo |
| `push` | PostToolUse Bash con `git push`, confirmado por el demonio comparando `origin/main` |

La fuente de verdad es git (refs y `main`); los hooks dan inmediatez y contexto. Si un hook se pierde, el sondeo de git del demonio lo reconstruye.

## 7. Colisiones

Niveles (ADR-0007). Todos son avisos.

| Nivel | Qué detecta | Cómo | Color |
|---|---|---|---|
| 1 | Dos personas con cambios sin fusionar en el mismo fichero | Relay cruza `ficheros` de los eventos `arbol` de todos los actores | Amarillo |
| 2 | Conflicto real si se fusionan | El demonio publica su trabajo en curso como `refs/hackathon/wip/<persona>` (con `git stash create` para lo no commiteado, sin tocar el árbol); el relay o cualquier demonio ejecuta `git merge-tree --write-tree` por pares | Rojo |
| 2b | Conflicto textual que la fusión estructural resuelve | Mergiraf sobre los ficheros en conflicto (extra, R-34) | Amarillo |
| 3 | Contrato tocado por quien no es su dueño | Bloques de `docs/contratos.md` con línea `Vive en:` y dueño según `autoridad.md` | Rojo |
| Reserva | Edición de un fichero reservado por otro | PreToolUse Edit/Write lee las reservas de `estado-equipo` | Aviso en la sesión |

El trabajo de dos workers de la misma persona no colisiona en este sentido: el orquestador ya los serializa cuando comparten ficheros.

## 8. Inyección en las sesiones

- **SessionStart** (`sesion.sh`, ya existe): añade, si el OS está activo, el bloque «Equipo» desde `estado-equipo.md`. Presupuesto total de 2.500 caracteres (R-24), en este orden: tarea de la sesión y bloqueos, colisiones que la afectan, decisiones y criterios nuevos desde la última sesión, una línea por persona. El detalle, en la ruta de `estado-equipo.md`.
- **UserPromptSubmit** (`delta.sh`): compara el hash de lo relevante para la persona de esa sesión (su tarea, sus colisiones, decisiones y criterios nuevos) con el último entregado (`<git común>/hackathon/os/entregado/<session_id>`). Si cambió, imprime solo el cambio en ≤ 600 caracteres; si no, nada. Lleva la cuenta de lo inyectado desde el inicio o la última compactación: pasados 6.000 caracteres, solo colisiones rojas (R-25, R-25b). Lo inyectado no se borra del contexto (M8.0, P16).
- **Colisión roja a mitad de turno**: el monitor (`escucha.sh`) imprime una línea cuando `estado-equipo.md` marca una colisión roja nueva para esa persona. Una línea del monitor abre un turno (comprobado en M6a), así que solo se usa para rojo.
- Redacción factual, no imperativa (guía oficial de hooks), y todo lo externo entrecomillado con autor.

## 9. Degradación

| Falla | Qué sigue funcionando |
|---|---|
| Demonio no arrancado | Hooks escriben JSONL local; nada se pierde. Inyección: solo lo de la 0.3.2. |
| Relay caído | Demonio guarda y reintenta; proyección local (mi estado + último `estado.json` recibido, marcado viejo). |
| GitHub caído o limitando | Relay sigue con presencia, eventos y git; tareas con el último estado conocido, marcadas viejas. |
| Sin internet, con LAN | Relay por LAN; git por un remoto `bare` en el portátil coordinador (contingencia de M8h). |
| Sin nada | La 0.3.2 tal cual. |

## 10. Cambios en piezas existentes del kit (M8a)

- `skills/hack-plan`: columna `ID` en las tablas de cada persona (`T01`…), estable al ajustar el plan; dependencias por ID en «Quién espera a quién».
- `agents/orquestador.md`: línea `ID: <Txx>` en el encargo; nombre de la ref de fusión = ID; su estado pasa a `estado/<usuario>.orquestador.md` (ADR-0002).
- `skills/hack-scaffold/templates/contratos.md`: línea `Vive en: <rutas>` por bloque.
- Monitor y `buzon.sh`: siguen filtrando `labels=hk`; las tareas usan `hk-tarea`, que no contiene esa etiqueta (ADR-0001).
- `hooks/hooks.json`: entradas nuevas del OS, todas detrás del interruptor de R-01.
