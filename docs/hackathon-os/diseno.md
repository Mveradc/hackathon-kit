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
- **Restricción: un clon, una persona.** El interruptor (`os.md` de la copia principal), la persona (la caché de `hk_yo`) y los eventos viven en el git común, así que el OS da por hecho que cada git común es de una sola persona. Los worktrees de un clon (workers, fusiones, revisores) son de esa persona. Dos personas en worktrees del mismo clon no se distinguen: cada una necesita su clon (ADR-0004). La persona se resuelve en la copia principal del clon.

## 4. Recorrido de una señal

1. Claude Code dispara un hook. `emite.sh` lee la entrada (una línea JSON), copia solo los campos de la lista blanca (`api.md` §1) con regex de bash, sin `jq` y sin desescapar, les añade el sobre (`v`, `ts`, `persona`, `tipo`) y escribe la línea en el JSONL de su sesión. No usa red ni guarda contenido de ficheros. Coste: un proceso bash (≈37 ms en Windows).
2. El demonio sigue los JSONL (posición por fichero), parsea la entrada, normaliza al esquema de `contratos/eventos.schema.json` y la envía al relay en lotes (`POST /eventos`). Si el relay no responde, guarda la posición y reintenta.
3. Cada 15 s, el demonio sondea git: `git worktree list`, `git status --porcelain` por worktree, `refs/hackathon/fusion/*`, y si hay `origin`, qué commits de las fusiones ya están en `origin/main`. Emite lo que cambió.
4. El relay aplica cada evento al modelo (presencia, ficheros, reservas, señales por tarea), sondea los issues `hk-tarea` cada 30 s con ETag y recalcula `estado.json`. Lo publica por SSE.
5. Cada demonio recibe `estado.json`, escribe `estado-equipo.md` (resumen para su persona) y lo sirve por MCP. Los hooks de inyección solo leen ese fichero: nunca llaman a la red.

## 5. Ciclo de vida de una tarea

Estados derivados, en orden de avance. Cada uno con la señal que lo produce (constitución II). El valor es un identificador sin espacios; la web y el markdown muestran la etiqueta legible.

| Estado (etiqueta) | Señal | Fuente |
|---|---|---|
| `pendiente` (pendiente) | Issue `hk-tarea` abierto con alguna dependencia sin cumplir | GitHub |
| `lista` (lista) | Issue abierto y todas sus dependencias `publicada` o `cerrada` (sin dependencias, también) | Derivado |
| `reclamada` (reclamada) | Issue asignado a su dueño, o evento `reclamo` suyo, sin actividad aún. El compilador pone el dueño en el issue, pero no lo asigna | GitHub / MCP |
| `en_curso` (en curso) | Actividad de un actor de su dueño en la tarea (encargo con su ID, o un evento atribuido a ella), esté reclamada o no | Hooks / git |
| `parada` (parada) | `en_curso` sin actividad de su dueño en `umbral_parada_min` (20 min, R-14). Solo desde `en_curso` | Derivado |
| `en_revision` (en revisión) | `fusion.creada` (o `refs/hackathon/fusion/<ID>`) pendiente de veredicto, o con APROBADO y sin `fusion.aprobada` | Hooks / git |
| `integrada` (integrada) | `fusion.aprobada`: el `main` local de su persona contiene la fusión | git |
| `no_cerrada` (no cerrada) | Segundo CAMBIOS del revisor sin un APROBADO en medio | Hooks |
| `publicada` (publicada) | La última fusión aprobada o el último commit con su ID está en el `datos.incluye` de un `push` con fuente `git` | git |
| `cerrada` (cerrada) | `publicada` e issue cerrado por alguien del equipo | GitHub |

- Una tarea humana (sin orquestador) pasa de `en_curso` a `publicada` cuando un commit que menciona su ID (`T07` en el mensaje) llega a `origin/main`. No hay `integrada` porque no hay revisor.
- `verificada` no existe como estado aparte: para el orquestador, APROBADO ya incluye volver a ejecutar la comprobación en un worktree limpio. Para tareas humanas, la verificación queda fuera de la v1 (ejecutar la «Cómo se comprueba» del plan es un extra).
- Dos pasos, los dos puros y probados con la tabla de §5.2:
  1. **Atribución** (`hkos/modelo.py`, regla 9): recorre todos los eventos del equipo en orden y pone `tarea` a los que no la traen, según el estado de las tareas de su persona en ese momento. Depende de varias tareas a la vez, así que no va dentro del motor.
  2. **Motor de estados** (`hkos/estados.py`), tarea por tarea: `derivar(tarea, issue, eventos de la tarea, dependencias, equipo, ahora, umbral) → {estado, declarado, fusion, cumplidas_por_cierre, discrepancias}`, donde `dependencias` da, por ID, el estado derivado y el declarado de cada una.
- `modelo.py` agrupa las discrepancias de los dos pasos por (tipo, tarea, persona).

### 5.1 Reglas del motor
Recorre los eventos de la tarea en orden de `ts`, sin repetidos (`id`), y lleva una fase: ninguna, `en_curso`, `en_revision`, `integrada`, `no_cerrada` o `publicada`.
1. **Actividad**: todo evento de un actor del dueño con la tarea (o atribuido a ella, regla 9) renueva la hora de la última actividad. Sin fase, pasa a `en_curso`. La actividad de otra persona no cambia nada y va a `discrepancias` (`actividad_ajena`). **Excepción (M8e):** si el dueño no tiene GitHub en la tabla de `coordinacion.md` (dueño «C», no un usuario), cuenta la actividad de cualquier persona del equipo que traiga el ID de la tarea: el ID manda sobre quién lo escribe. Lo atribuido por la regla 9 nunca llega a esas tareas, porque solo atribuye a tareas de la propia persona.
2. **`encargo.lanzado`**: desde ninguna fase, `integrada` o `publicada`, pasa a `en_curso` (un encargo nuevo de la misma tarea, como `T18 (2/2)`). Desde `no_cerrada`, pasa a `en_curso` y pone a cero la cuenta de CAMBIOS (la persona reintenta). Un encargo relanzado tras el primer CAMBIOS **no** la pone a cero.
3. **`fusion.creada`**: pasa a `en_revision` con esa fusión como la actual y sin veredicto.
4. **`revision.veredicto`** sobre un sha que no es la fusión actual: se ignora (`veredicto_sha`). Sobre la actual:
   - APROBADO: pone a cero la cuenta de CAMBIOS y sigue en `en_revision` hasta `fusion.aprobada` (gana git).
   - CAMBIOS: suma uno. Con 1, pasa a `en_curso`; con 2, a `no_cerrada`.
5. **`fusion.descartada`**: solo vuelve a `en_curso` desde `en_revision` sin veredicto. `no_cerrada` es pegajoso: un `fusion.descartada` posterior (el orquestador borra la referencia tras el segundo CAMBIOS) no lo cambia.
6. **`fusion.aprobada`** (confirmada por git, `api.md` §2): pasa a `integrada` aunque falte el veredicto, que va a `discrepancias` (`hook_frente_a_git`).
7. **`commit`** con la tarea: su sha pasa a ser el último que hay que publicar; desde `publicada`, vuelve a `en_curso`. Salvo que ese sha ya esté en algún `incluye` visto, o que el commit traiga `datos.alcanzable: true` (el demonio lo ve alcanzable desde `origin/main`): entonces no hace retroceder la tarea.
8. **`push`**: solo cuenta con fuente `git`. Si su `incluye` tiene la última fusión aprobada o el último commit, pasa a `publicada`. Si tiene una fusión todavía en revisión, también (gana git, `hook_frente_a_git`). Un `push` de hook sin el de git no publica.
9. **Atribución** (paso previo, en `modelo.py`): un evento sin `tarea` (`edicion`, `arbol` y, desde M8e, `commit`: un commit es la misma señal que una edición) cuenta para la tarea de su persona si esta tiene exactamente una tarea `reclamada`, `en_curso` o `parada` en ese momento. Con varias, no cuenta y va a `discrepancias` (`atribucion_ambigua`). Con ninguna, no cuenta y va a `sin_tarea` (un commit, como «commit: <rama>»: así sale una rama sin ID, R-15). De un `arbol`, a `sin_tarea` solo va lo que no tiene commit: lo que sale únicamente del diff contra `origin/main` (`datos.solo_diff`) ya cuenta por su `commit` (2026-10-16; ruido de M8e con lo integrado en `main` local antes del push). El `arbol` del demonio no se atribuye ni va a `sin_tarea`: solo cuenta para las colisiones. Un commit de una rama de worker ya trae la tarea de su encargo (la pone el demonio). El mapeo por carpetas queda aplazado: el plan da carpetas por persona, no por tarea, así que no distingue entre dos tareas de la misma persona.
10. **Sin fase**: `reclamada` si el issue está asignado al dueño o hay un `reclamo` suyo; si no, `lista` o `pendiente` según las dependencias. Una dependencia se cumple si está `publicada` o `cerrada`, o si su issue lo ha cerrado alguien del equipo aunque no esté publicada (tareas sin código: preguntas, decisiones, pitch). En ese caso va en `cumplidas_por_cierre` de la dependiente, para que las vistas muestren «⚑ T02 cerrada a mano». `integrada` no la cumple. Una dependencia con un ID que no existe no se cumple (`dependencia_inexistente`).
11. **`parada`**: con fase `en_curso` y `ahora` − última actividad > umbral.
12. **Issue cerrado** por alguien del equipo: con `publicada`, el estado es `cerrada`; si no, el estado sigue siendo el derivado y `declarado` = `cerrada` (⚑). Reabrirlo quita la marca. Una asignación, un cierre o una reapertura de alguien de fuera del equipo se ignora (`fuera_del_equipo`).
13. **Fuente y hora** del estado: las del evento que lo produce (`en_curso`, la última actividad); `lista` y `parada` llevan `derivado`, con la hora en que se cumplió la condición (la última dependencia cumplida o el umbral alcanzado).

### 5.2 Tabla de casos
B es la dueña de la tarea T10; A es otra persona del equipo; `@fuera` no está en `coordinacion.md`. Salvo que se diga otra cosa: issue abierto sin asignar, sin dependencias, umbral de 20 min y `ahora` un minuto después de la última señal. Las señales llevan su minuto (`t`). Los shas son letras (`X`, `Y`, `c1`).

| ID | Señales | Estado (fuente) | Además |
|---|---|---|---|
| **GitHub y dependencias** ||||
| E01 | Issue abierto; depende de T02, que está `en_curso` | `pendiente` (github) | |
| E02 | Issue abierto, sin dependencias | `lista` (derivado) | |
| E03 | Depende de T02 `publicada` | `lista` (derivado) | |
| E04 | Depende de T02 `cerrada` | `lista` (derivado) | |
| E05 | Depende de T02 `integrada` | `pendiente` (github) | `integrada` solo está en el `main` local de su dueño |
| E06 | Depende de T02, derivada `en_curso` con ⚑ `cerrada` | `lista` (derivado) | `cumplidas_por_cierre` = [T02] |
| E07 | Depende de T99, que no existe | `pendiente` (github) | `dependencia_inexistente` |
| E08 | t=0 issue asignado a B por B | `reclamada` (github) | |
| E09 | t=0 `reclamo` de B | `reclamada` (mcp) | |
| E10 | t=0 issue asignado a B por `@fuera` | `lista` (derivado) | `fuera_del_equipo` |
| **Actividad y `parada`** ||||
| E11 | t=0 `reclamo` de B · t=2 `edicion` de B con T10 | `en_curso` (hook, t=2) | |
| E12 | t=0 `encargo.lanzado` del orquestador de B, sin reclamar | `en_curso` (hook) | |
| E13 | t=0 `edicion` de A con T10 | `lista` (derivado) | `actividad_ajena` |
| E14 | t=0 `edicion` de B · `ahora` t=21 | `parada` (derivado, t=20) | |
| E15 | t=0 `edicion` de B · `ahora` t=19 | `en_curso` (hook, t=0) | |
| E16 | t=0 `edicion` de B · t=30 `edicion` de B · `ahora` t=31 | `en_curso` (hook, t=30) | sale de `parada` |
| E17 | t=0 `edicion` de B · t=20 `latido` de un actor de B con T10 · `ahora` t=30 | `en_curso` (hook, t=20) | el latido es actividad |
| E18 | t=0 `reclamo` de B · `ahora` t=30 | `reclamada` (mcp) | `parada` solo desde `en_curso` |
| E19 | t=0 `encargo.lanzado` · t=5 `fusion.creada` X · `ahora` t=40 | `en_revision` (hook) | sin `parada` en revisión |
| **Revisión y fusión** ||||
| E20 | `encargo.lanzado` · `fusion.creada` X | `en_revision` (hook) | |
| E21 | `encargo.lanzado` · `fusion.creada` X · APROBADO X | `en_revision` (hook) | sin `fusion.aprobada`, gana git |
| E22 | `encargo.lanzado` · `fusion.creada` X · APROBADO X · `fusion.aprobada` X | `integrada` (git) | `fusion` = X |
| E23 | `encargo.lanzado` · `fusion.creada` X · `fusion.aprobada` X, sin veredicto | `integrada` (git) | `hook_frente_a_git` |
| E24 | `fusion.creada` X · APROBADO Y | `en_revision` (hook) | `veredicto_sha` |
| E25 | `fusion.creada` X · `fusion.descartada` X, sin veredicto | `en_curso` (hook) | |
| E26 | … `integrada` (E22) · `encargo.lanzado` | `en_curso` (hook) | segundo encargo de la misma tarea |
| **CAMBIOS y `no_cerrada`** ||||
| E27 | `encargo.lanzado` · `fusion.creada` X · CAMBIOS X | `en_curso` (hook) | cuenta 1 |
| E28 | E27 · `encargo.lanzado` · `fusion.creada` Y | `en_revision` (hook) | cuenta 1: el relanzamiento no la reinicia |
| E29 | E28 · CAMBIOS Y | `no_cerrada` (hook) | cuenta 2 |
| E30 | Secuencia del orquestador: `encargo.lanzado` · `fusion.creada` X · CAMBIOS X · `encargo.lanzado` · `fusion.creada` Y · CAMBIOS Y · `fusion.descartada` Y | `no_cerrada` (hook) | el descarte no lo cambia |
| E31 | E30 · `encargo.lanzado` · `fusion.creada` Z | `en_revision` (hook) | la persona reintenta: cuenta 0 |
| E32 | E31 · CAMBIOS Z | `en_curso` (hook) | cuenta 1, no 3 |
| E33 | `fusion.creada` X · CAMBIOS X · `fusion.creada` Y · APROBADO Y · `fusion.aprobada` Y · `encargo.lanzado` · `fusion.creada` Z · CAMBIOS Z | `en_curso` (hook) | APROBADO reinició la cuenta |
| E34 | `fusion.creada` X · el mismo evento CAMBIOS X dos veces (mismo `id`) | `en_curso` (hook) | un repetido no cuenta |
| **Publicación y cierre** ||||
| E35 | E22 · `push` (git) con `incluye` = [X] | `publicada` (git) | |
| E50 | Depende de T02, sin actividad (`lista`) y cerrada por A | `lista` (derivado) | `cumplidas_por_cierre` = [T02]: tarea sin código |
| E51 | E35 · después, `commit` X de B con T10 | `publicada` (git) | el sha ya estaba en un `incluye` |
| E52 | E39 · `commit` c2 de B con T10 y `datos.alcanzable: true` | `publicada` (git) | alcanzable desde `origin/main` |
| E36 | E22 · `push` (hook), sin el de git | `integrada` (git) | un push de hook no publica |
| E37 | E22 · `push` (git) con `incluye` = [W] | `integrada` (git) | |
| E38 | `fusion.creada` X, sin veredicto · `push` (git) con `incluye` = [X] | `publicada` (git) | `hook_frente_a_git` |
| E39 | `reclamo` · `commit` c1 de B con T10 · `push` (git) con `incluye` = [c1] | `publicada` (git) | tarea humana |
| E40 | E39 · `commit` c2 de B con T10 | `en_curso` (git) | trabajo nuevo tras publicar |
| E41 | E35 · issue cerrado por B | `cerrada` (github) | |
| E42 | E11 · issue cerrado por B | `en_curso` (hook) | `declarado` = `cerrada` (⚑) |
| E43 | E42 · issue reabierto por B | `en_curso` (hook) | sin `declarado` |
| E44 | E35 · issue cerrado por `@fuera` | `publicada` (git) | `fuera_del_equipo` |
| **Atribución (regla 9, sobre el paso de `modelo.py`)** ||||
| E45 | `reclamo` de B en T10 · `edicion` de B sin tarea | T10 `en_curso` (hook) | |
| E46 | `reclamo` de B en T10 y en T11 · `edicion` de B sin tarea | T10 y T11 `reclamada` | `atribucion_ambigua` |
| E47 | B sin tareas reclamadas · `edicion` de B sin tarea | T10 `lista` | entrada en `sin_tarea` |
| E48 | T10 `en_curso` desde t=0 · t=15 `arbol` de B sin tarea · `ahora` t=30 | `en_curso` (hook, t=15) | un `arbol` atribuido renueva la actividad |
| E49 | `reclamo` de B en T10 · T11 de B `publicada` · `edicion` de B sin tarea | T10 `en_curso` (hook) | una tarea publicada no cuenta para la atribución |
| E55 | `reclamo` de B en T10 · `commit` c1 de B sin tarea (rama `ficha`) | T10 `en_curso` (git) | un commit sin ID se atribuye como una edición |
| E56 | `reclamo` de B en T10 y en T11 · `commit` c1 de B sin tarea | T10 y T11 `reclamada` | `atribucion_ambigua` |
| E57 | B sin tareas abiertas · `commit` c1 de B sin tarea (rama `experimento`) | T10 `lista` | `sin_tarea` «commit: experimento» (R-15) |
| E58 | `commit` c1 de B con T10 en la rama `worktree-agent-x` (tarea del encargo, puesta por el demonio), sin reclamar | T10 `en_curso` (git) | |
| **Tareas sin dueño de GitHub (M8e; dueño «C», que no está en el equipo)** ||||
| E53 | `commit` c1 de A con T10 | `en_curso` (git) | sin `actividad_ajena`: el ID manda |
| E54 | E53 · `push` (git) con `incluye` = [c1] | `publicada` (git) | |
| **Issues (M8e, `hkos/github.py`: de issues a tareas)** ||||
| E59 | Issue `hk-tarea` con el marcador de T10 abierto por `@fuera`, sin issue del equipo | T10 no está en `tareas` | `fuera_del_equipo` |
| E60 | T02 cerrada como `not_planned` (quitada del plan) · T10 depende de T02 | T02 no está en `tareas`; T10 `pendiente` (github) | `dependencia_inexistente` |

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

Definiciones (M8g; código en `hkos/colisiones.py`, `hkos/contratos.py` y `hkos/colisiones_merge.py`):
- **Ficheros de una persona:** por cada árbol en que trabaja (la copia principal o el worktree de un worker), las rutas de su último `arbol` más las de los `edicion` posteriores. Los de un worker dejan de contar con su `worker.fin` (lo suyo pasa a la fusión o se descarta); los de la copia principal cuentan siempre. El `arbol` de la copia principal también lo emite el demonio al ver moverse `origin/main` (fuente `git`, sin `contratos`: se quedan los del último `arbol` mientras `docs/contratos.md` siga cambiado), para que un push desde la terminal no deje el amarillo hasta la siguiente herramienta de la sesión (2026-10-16). Sin `.claude/worktrees/` ni entradas de carpeta («?? web/»); `.hackathon/` sí cuenta.
- **El mismo fichero:** la misma ruta relativa a la raíz de su árbol, con `/`, sin distinguir mayúsculas. Un renombrado cuenta por el nombre nuevo (git no da el viejo en `porcelain` ni en `diff --name-only`).
- **Nivel 1:** una colisión amarilla por conjunto de personas que comparten ficheros (`1:<a>+<b>`), con todas sus rutas. Deja de estarlo cuando el último `arbol` de una de ellas ya no tiene el fichero (subió, deshizo o descartó). Un fichero en conflicto de nivel 2 entre esas mismas personas sale solo en rojo.
- **Nivel 2:** `2:<a>+<b>`, con los ficheros que `merge-tree` da en conflicto.
- **Nivel 3:** `3:<bloque>:<persona>`. Rojo cuando alguien que no es el dueño del bloque tiene cambiada una ruta de su `Vive en:` o trae su título en `datos.contratos` de un `arbol`. Avisa a quien lo toca, al dueño (si tiene GitHub) y al resto del equipo (los consumidores).
- **Reservas:** las vigentes de las demás personas salen en «Reservas» de `estado-equipo.md` (bloque de inicio y deltas) y en `reservas.tsv`, del que lee `reserva.sh` (PreToolUse y SubagentStart de los workers).

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
| Sin internet, con LAN | Relay por LAN; git por el remoto del equipo (`hk-os remoto`, un `bare` en el portátil coordinador servido con el token, `api.md` §9); tareas de `plan.md` con `github: no` (M8h). |
| Sin nada | La 0.3.2 tal cual. |

## 10. Cambios en piezas existentes del kit (M8a)

- `skills/hack-plan`: columna `ID` en las tablas de cada persona (`T01`…), estable al ajustar el plan; dependencias por ID en «Quién espera a quién».
- `agents/orquestador.md`: línea `ID: <Txx>` en el encargo; nombre de la ref de fusión = ID; su estado pasa a `estado/<usuario>.orquestador.md` (ADR-0002).
- `skills/hack-scaffold/templates/contratos.md`: línea `Vive en: <rutas>` por bloque.
- Monitor y `buzon.sh`: siguen filtrando `labels=hk`; las tareas usan `hk-tarea`, que no contiene esa etiqueta (ADR-0001).
- `hooks/hooks.json`: entradas nuevas del OS, todas detrás del interruptor de R-01.
