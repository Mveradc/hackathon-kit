# Tareas

Mismo formato que un encargo del orquestador (`agents/orquestador.md`), para que se puedan hacer a mano o con el propio orquestador. `[P]` = se puede hacer en paralelo con las demás `[P]` del mismo hito (no comparten ficheros). Cada tarea cita los requisitos que cubre. Ninguna empieza si su contrato tiene `[POR DECIDIR]`.

Formato:
```
### K-xx · <título> [P]
Cubre: R-xx · Depende de: K-yy
Puedes tocar: <ficheros o carpetas>
Contratos que aplican: <contratos/… o ADR>
Hecho cuando: <comando o comprobación y qué debe salir>
```

## M8.0 · Paso 0

### K-01 · Plugin de juguete que vuelca entradas de hooks [P]
Cubre: P2–P6 · Puedes tocar: scratchpad (fuera del repo del kit)
Hecho cuando: hay un JSON de entrada real capturado para SessionStart, PreToolUse(Agent), SubagentStart, SubagentStop, PostToolUse(Edit, Bash), PostToolBatch, Stop y UserPromptSubmit, en sesión normal, en `--agent` y en un worker con worktree. Se guardan en `evals/coordinacion/entradas/` (anonimizados).

### K-02 · MCP del plugin en `--agent` y en subagentes [P]
Cubre: P1 · Puedes tocar: scratchpad
Hecho cuando: respuesta anotada (sí/no, en qué tipos de sesión).

### K-03 · Etiquetas, dependencias y refs en el sandbox [P]
Cubre: P7, P8, P10 · Puedes tocar: `../hk-sandbox`
Hecho cuando: respuestas anotadas con los comandos usados.

### K-04 · `git stash create`, `merge-tree` y Mergiraf [P]
Cubre: P9, P11, P12 · Puedes tocar: scratchpad
Hecho cuando: un script reproduce los tres casos y deja `git status` idéntico antes y después en Windows y Linux.

### K-05 · Runtime y SSE en red real
Cubre: P13–P15, ADR-0005 · Depende de: —
Hecho cuando: ADR-0005 pasa a «decidido» con la tabla del criterio rellena.

### K-06 · Coste de hooks async y acumulación de contexto
Cubre: P6, P16 · Depende de: K-01
Hecho cuando: ms por hook y tamaño de contexto tras 20 turnos con deltas, anotados; umbral de M8c fijado.

## M8a · El kit, preparado

### K-10 · IDs `Txx` en `/hack-plan` [P]
Cubre: R-05 · Puedes tocar: `skills/hack-plan/SKILL.md`, `skills/hack-plan/templates/plan.md`, `skills/hack-plan/examples/`
Contratos que aplican: ADR-0002
Hecho cuando: criterios 1 y 2 de M8a con los retos 02 y 03; ejemplos regenerados y anonimizados.

### K-11 · ID en el encargo, ref por ID y estado del orquestador [P]
Cubre: R-04 · Puedes tocar: `agents/orquestador.md`, `agents/worker.md`
Contratos que aplican: ADR-0002
Hecho cuando: criterio 3 de M8a (incluido el reinicio en frío).

### K-12 · `Vive en:` en contratos [P]
Cubre: R-21 · Puedes tocar: `skills/hack-scaffold/templates/contratos.md`, `skills/hack-scaffold/SKILL.md`
Hecho cuando: criterio 4 de M8a.

### K-13 · `hk-tarea` fuera del buzón
Cubre: R-07 · Depende de: K-03 · Puedes tocar: `scripts/coordinacion/` (solo si P7 obliga), `evals/coordinacion/prueba_hooks.py`
Hecho cuando: criterio 5 de M8a; `prueba_hooks.py` en verde.

## M8b · Contratos y simulador

### K-20 · Congelar contratos
Cubre: — · Depende de: M8.0 · Puedes tocar: `docs/hackathon-os/contratos/`
Hecho cuando: sin `[POR DECIDIR]`; esquemas validan; las entradas reales de K-01 se normalizan a eventos válidos.

### K-21 · Motor de estados (función pura) con tabla de casos [P]
Cubre: R-09, R-13, R-14 · Depende de: K-20 · Puedes tocar: `os/estados.*`, `os/pruebas/`
Contratos que aplican: `diseno.md` §5, `estado.schema.json`
Hecho cuando: la tabla de casos pasa (un caso por transición y por señal contradictoria).

### K-22 · Simulador y guiones G1–G4 [P]
Cubre: R-28 · Depende de: K-20 · Puedes tocar: `evals/coordinacion/simulador/`, `evals/coordinacion/gh-falso.sh`
Contratos que aplican: `simulador.md`
Hecho cuando: criterio 3 de M8b.

## M8c · Emisión

### K-30 · Interruptor del OS y `os.md` [P]
Cubre: R-01 · Puedes tocar: `scripts/os/comun.sh`, `skills/hack-scaffold/templates/os.md`
Hecho cuando: `os_activo` sale en < 20 ms sin `os.md` (medido en Windows) y sin red.

### K-31 · `emite.sh` y entradas en `hooks.json`
Cubre: R-03, R-16 · Depende de: K-30 · Puedes tocar: `scripts/os/emite.sh`, `hooks/hooks.json`
Contratos que aplican: `api.md` §1
Hecho cuando: criterios 1–3 de M8c.

### K-32 · `arbol.sh` [P]
Cubre: R-17 · Depende de: K-30 · Puedes tocar: `scripts/os/arbol.sh`, `hooks/hooks.json`
Hecho cuando: criterio 4 de M8c.

### K-33 · Eventos de la compuerta [P]
Cubre: R-11 · Puedes tocar: `scripts/orquestador/compuerta.sh`
Hecho cuando: `prueba_hooks.py` comprueba que cada aceptación y rechazo deja su línea; el comportamiento de la compuerta no cambia.

### K-34 · Normalizador forma cruda → evento
Cubre: R-10 · Depende de: K-20, K-31 · Puedes tocar: `os/normaliza.*`
Contratos que aplican: `api.md` §2
Hecho cuando: criterios 2 y 5 de M8c con las entradas reales y una pasada del orquestador.

## M8d · Demonio y relay

### K-40 · Relay: eventos, latidos, presencia, persistencia
Cubre: R-16, R-18, R-32 · Depende de: K-20 · Puedes tocar: `os/relay.*`
Contratos que aplican: `api.md` §3
Hecho cuando: criterios 2, 4 y 5 de M8d.

### K-41 · Relay: reservas y SSE [P]
Cubre: R-22, R-26 · Depende de: K-40 · Puedes tocar: `os/relay_reservas.*`, `os/relay_sse.*`
Hecho cuando: G11 sin pérdidas.

### K-42 · Demonio local [P]
Cubre: R-16, R-29 · Depende de: K-34 · Puedes tocar: `os/agente.*`
Contratos que aplican: `api.md` §4
Hecho cuando: criterios 1 y 3 de M8d.

### K-43 · `hk-os unir` y `hk-os relay` (arranque)
Cubre: R-02 · Depende de: K-40, K-42 · Puedes tocar: `bin/hk-os`, `os/cli.*`
Hecho cuando: dos copias del sandbox se unen con un comando cada una.

## M8e · Estado duradero

### K-50 · `hk-os compilar` [P]
Cubre: R-05, R-06 · Depende de: K-10 · Puedes tocar: `os/compilar.*`
Contratos que aplican: ADR-0001
Hecho cuando: criterio 1 de M8e.

### K-51 · Sondeo de GitHub con ETag y filtro de autores [P]
Cubre: R-30, R-31 · Depende de: K-40 · Puedes tocar: `os/github.*`
Hecho cuando: criterios 5 y 6 de M8e.

### K-52 · Motor de estados integrado y antigüedades
Cubre: R-08, R-09, R-12–R-15 · Depende de: K-21, K-50, K-51 · Puedes tocar: `os/relay.*`, `os/estados.*`
Hecho cuando: criterios 2–4 de M8e.

## M8f · Proyección

### K-60 · Módulo de proyección (estado.json → md, datos de la web) [P]
Cubre: R-24, R-28 · Depende de: K-52 · Puedes tocar: `os/proyeccion.*`
Contratos que aplican: `api.md` §6, ADR-0006
Hecho cuando: test de igualdad en G1–G4.

### K-61 · Web de solo lectura [P]
Cubre: R-26 · Depende de: K-41 · Puedes tocar: `os/web/`
Hecho cuando: criterio 1 de M8f.

### K-62 · `sesion.sh` ampliado y `delta.sh`
Cubre: R-24, R-25 · Depende de: K-60 · Puedes tocar: `scripts/coordinacion/sesion.sh`, `scripts/os/delta.sh`, `hooks/hooks.json`
Hecho cuando: criterios 2 y 3 de M8f; sin OS activo, `sesion.sh` imprime exactamente lo mismo que en la 0.3.2.

### K-63 · MCP [P]
Cubre: R-27 · Depende de: K-42 · Puedes tocar: `os/mcp.*`, `.mcp.json`
Contratos que aplican: `api.md` §5
Hecho cuando: criterio 4 de M8f.

## M8g · Colisiones

### K-70 · Nivel 1 en el relay [P]
Cubre: R-19 · Depende de: K-52 · Puedes tocar: `os/colisiones.*`
Hecho cuando: G5 y criterio 6 de M8g.

### K-71 · Nivel 2: trabajo en curso y `merge-tree` [P]
Cubre: R-20 · Depende de: K-42, P9–P11 · Puedes tocar: `os/agente.*` (solo la publicación), `os/colisiones_merge.*`
Hecho cuando: G5b (criterio 2 de M8g).

### K-72 · Nivel 3: contratos [P]
Cubre: R-21 · Depende de: K-12, K-52 · Puedes tocar: `os/contratos.*`
Hecho cuando: G6 (criterio 3 de M8g).

### K-73 · Aviso de reserva en PreToolUse y aviso rojo por el monitor
Cubre: R-22, R-23 · Depende de: K-41, K-60 · Puedes tocar: `scripts/os/reserva.sh`, `scripts/coordinacion/escucha.sh`, `hooks/hooks.json`
Hecho cuando: criterios 4 y 5 de M8g; el monitor sigue en silencio sin OS activo.

## M8h · Robustez y ensayo

### K-80 · Modo sin GitHub [P]
Cubre: R-29, R-30 · Puedes tocar: `os/github.*`, `os/compilar.*`
Hecho cuando: G7.

### K-81 · Guiones G7–G10 como evals [P]
Cubre: R-31, constitución X · Puedes tocar: `evals/coordinacion/`
Hecho cuando: los guiones corren con un comando y dan informe.

### K-82 · Guion de arranque
Cubre: R-02 · Puedes tocar: `docs/hackathon-os/arranque.md`
Hecho cuando: criterio 3 de M8h cronometrado.

### K-83 · Ensayo con el equipo real
Depende de: todo lo anterior
Hecho cuando: criterio 4 de M8h, con la hoja de observación rellena en `evals/coordinacion/prueba.md`.

### K-84 · Documentación y publicación
Puedes tocar: `README.md`, `README.es.md`, `docs/limitaciones.md`, `CHANGELOG.md`, `.claude-plugin/plugin.json`
Hecho cuando: criterios 5 y 6 de M8h.
