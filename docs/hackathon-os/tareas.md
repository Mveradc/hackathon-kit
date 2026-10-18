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
Cubre: R-09, R-13, R-14 · Depende de: K-20 · Puedes tocar: `hkos/estados.*`, `hkos/pruebas/`
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
Cubre: R-10 · Depende de: K-20, K-31 · Puedes tocar: `hkos/normaliza.*`
Contratos que aplican: `api.md` §2
Hecho cuando: criterios 2 y 5 de M8c con las entradas reales y una pasada del orquestador.

## M8d · Demonio y relay

### K-40 · Relay: eventos, latidos, presencia, persistencia
Cubre: R-16, R-18, R-32 · Depende de: K-20 · Puedes tocar: `hkos/relay.*`
Contratos que aplican: `api.md` §3
Hecho cuando: criterios 2, 4 y 5 de M8d.

### K-41 · Relay: SSE [P]
Cubre: R-26 · Depende de: K-40 · Puedes tocar: `hkos/relay.*`
Hecho cuando: G11 sin pérdidas (criterio 5 de M8d). Las reservas (`api.md` §3) pasan a K-73 (M8g), donde se valida R-22.

### K-42 · Demonio local [P]
Cubre: R-16, R-29 · Depende de: K-34 · Puedes tocar: `hkos/agente.*`
Contratos que aplican: `api.md` §4
Hecho cuando: criterios 1, 3, 6 y 7 de M8d. El sondeo de git del demonio pasa a K-52 (M8e), `estado-equipo.md` a K-60 (M8f) y `publicar_wip` a K-71 (M8g).

### K-43 · `hk-os unir` y `hk-os relay` (arranque)
Cubre: R-02 · Depende de: K-40, K-42 · Puedes tocar: `bin/hk-os`, `hkos/cli.*`, `scripts/os/arranque.sh`, `scripts/coordinacion/sesion.sh` (lanzar el demonio)
Hecho cuando: dos copias del sandbox se unen con un comando cada una.

## M8e · Estado duradero

### K-50 · `hk-os compilar` [P]
Cubre: R-05, R-06 · Depende de: K-10 · Puedes tocar: `hkos/compilar.*`
Contratos que aplican: ADR-0001
Hecho cuando: criterio 1 de M8e.

### K-51 · Sondeo de GitHub con ETag y filtro de autores [P]
Cubre: R-30, R-31 · Depende de: K-40 · Puedes tocar: `hkos/github.*`
Hecho cuando: criterios 5 y 6 de M8e.

### K-52 · Motor de estados integrado y antigüedades
Cubre: R-08, R-09, R-12–R-15 · Depende de: K-21, K-50, K-51 · Puedes tocar: `hkos/relay.*`, `hkos/estados.*`, `hkos/agente.*` (el sondeo de git de `api.md` §4)
Hecho cuando: criterios 2–4 de M8e.

## M8f · Proyección

### K-60 · Módulo de proyección (estado.json → md, datos de la web) [P]
Cubre: R-24, R-28 · Depende de: K-52 · Puedes tocar: `hkos/proyeccion.*`, `hkos/agente.*` (recibir `estado.json` y escribir `estado-equipo.md`)
Contratos que aplican: `api.md` §6, ADR-0006
Hecho cuando: test de igualdad en G1–G4.

### K-61 · Web de solo lectura [P]
Cubre: R-26 · Depende de: K-41 · Puedes tocar: `hkos/web/`
Hecho cuando: criterio 1 de M8f.

### K-62 · `sesion.sh` ampliado y `delta.sh`
Cubre: R-24, R-25 · Depende de: K-60 · Puedes tocar: `scripts/coordinacion/sesion.sh`, `scripts/os/delta.sh`, `hooks/hooks.json`
Hecho cuando: criterios 2 y 3 de M8f; sin OS activo, `sesion.sh` imprime exactamente lo mismo que en la 0.3.2.

### K-63 · MCP [P]
Cubre: R-27 · Depende de: K-42 · Puedes tocar: `hkos/mcp.*`, `.mcp.json`
Contratos que aplican: `api.md` §5
Hecho cuando: criterio 4 de M8f.

## M8g · Colisiones

### K-70 · Nivel 1 en el relay [P]
Cubre: R-19 · Depende de: K-52 · Puedes tocar: `hkos/colisiones.*`
Hecho cuando: G5 y criterio 6 de M8g.

### K-71 · Nivel 2: trabajo en curso y `merge-tree` [P]
Cubre: R-20 · Depende de: K-42, P9–P11 · Puedes tocar: `hkos/agente.*` (solo la publicación), `hkos/colisiones_merge.*`
Hecho cuando: G5b (criterio 2 de M8g).

### K-72 · Nivel 3: contratos [P]
Cubre: R-21 · Depende de: K-12, K-52 · Puedes tocar: `hkos/contratos.*`
Hecho cuando: G6 (criterio 3 de M8g).

### K-73 · Aviso de reserva en PreToolUse y aviso rojo por el monitor
Cubre: R-22, R-23 · Depende de: K-41, K-60 · Puedes tocar: `scripts/os/reserva.sh`, `scripts/coordinacion/escucha.sh`, `hooks/hooks.json`, `hkos/relay.*` (reservas de `api.md` §3, desde M8d)
Hecho cuando: criterios 4 y 5 de M8g; el monitor sigue en silencio sin OS activo.

## M8h · Robustez y ensayo

### K-80 · Modo sin GitHub [P]
Cubre: R-29, R-30 · Puedes tocar: `hkos/github.*`, `hkos/compilar.*`
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
**Aplazada sin fecha** (decisión del usuario, 2026-10-18): ahora no se puede coordinar al equipo. Va después del cierre de M9a.

### K-84 · Documentación y publicación
Puedes tocar: `README.md`, `README.es.md`, `docs/limitaciones.md`, `CHANGELOG.md`, `.claude-plugin/plugin.json`
Hecho cuando: criterios 5 y 6 de M8h.

## M9a · Web de trabajo, nivel A

Se adelanta a K-83 (el ensayo) por decisión del usuario (2026-10-17). Diseño en `docs/hackathon-os/diseno-web/`. Todo lo de M9a corre solo con `web_nueva: sí` en `os.md`.

### K-90 · Paso 0 de M9a
Cubre: — · Puedes tocar: scratchpad (fuera del repo del kit)
Hecho cuando: anotado en `evals/coordinacion/prueba.md` («M9a, Paso 0»):
- si `PostToolUseFailure` de Bash llega con `tool_input.command` cuando el comando sale ≠ 0 (entrada real capturada y anonimizada en `evals/coordinacion/entradas/`). Si no llega, la alternativa la decide el usuario;
- las versiones exactas de React, Vite y Vitest;
- la licencia (OFL) y el tamaño en woff2 de Space Grotesk, IBM Plex Sans y JetBrains Mono;
- que una línea en un fichero que lee `escucha.sh` abre un turno, con `interactivo.py`.

### K-91 · ADR, constitución y contratos
Cubre: R-33 · Depende de: K-90 · Puedes tocar: `docs/hackathon-os/adr/0009-*.md`, `0010-*.md`, `0011-*.md`, `docs/hackathon-os/constitucion.md`, `docs/hackathon-os/contratos/`
Contratos que aplican: ADR-0006, ADR-0008
Hecho cuando: ADR-0009–0011 escritos con lo que decidió el usuario; IV reformulado y V ampliado en la constitución; `api.md` (§0, §1, §3, §4, §6, §7) y los dos esquemas sin `[POR DECIDIR]`, y los esquemas validan con el validador de M8b. `api.md` §4 recoge las precisiones de la revisión: el token solo en `X-HK-Token`, nunca en la query; `/v1/stream` leído con `fetch`; el reintento único de Anotar; la regla de Salud. Lo revisa el usuario antes de K-92.

### K-92 · `servicios.md` [P]
Cubre: R-33 · Depende de: K-91 · Puedes tocar: `skills/hack-scaffold/templates/servicios.md`, `skills/hack-scaffold/SKILL.md` (paso de coordinación), `skills/hack-plan/templates/autoridad.md`, `hkos/servicios.py`, `hkos/pruebas/`
Contratos que aplican: ADR-0011
Hecho cuando: `hkos/servicios.py` pasa su tabla de casos (fila confirmada; cambiada por otra persona; comando de Prueba cambiado; sha desconocido; dueño que no coincide con `autoridad.md`; fila de Propuestas que su dueño pasa a su sección; fila añadida por un worker de su dueño, rama `worktree-agent-*`; Salud que no es una ruta: `http://…`, `//host`, `/../`; fichero fuera de todo servicio; filas iniciales de `/hack-scaffold`).

### K-93 · Relay: servicios y SSE `eventos` [P]
Cubre: R-26, R-33 · Depende de: K-92 · Puedes tocar: `hkos/relay.py`, `hkos/modelo.py`
Contratos que aplican: `api.md` §3, ADR-0011
Hecho cuando: con `web_nueva: sí`, `estado.json` lleva `servicios` (de `origin/main` del clon del relay y de los eventos `commit`, `servicio.estado` y `prueba`) y `/v1/stream` emite `eventos` (lista blanca de campos, pulso `github`); con `no`, el stream es el de hoy (`carga.py` e `igualdad.py` sin cambios).

### K-94 · Demonio: la web, los datos y la salud
Cubre: R-26, R-33 · Depende de: K-93 · Puedes tocar: `hkos/agente.py`, `hkos/cli.py`, `bin/hk-os`
Contratos que aplican: `api.md` §4, ADR-0010
Hecho cuando: criterios 2 y 6 de M9a; con `web_nueva: sí`, el demonio se suscribe al SSE del relay y comprueba puerto y salud de los servicios confirmados de su persona (evento `servicio.estado` solo al cambiar); `hk-os web` abre la URL con el token en el fragmento.

### K-95 · Acciones: Anotar y Reclamar
Cubre: R-30, R-33 · Depende de: K-94 · Puedes tocar: `hkos/acciones.py`, `hkos/agente.py` (rutas de acción), `scripts/coordinacion/escucha.sh`, `evals/coordinacion/prueba_hooks.py`
Contratos que aplican: `api.md` §4 y §5, ADR-0010
Hecho cuando: criterios 7 y 8 de M9a (incluido el push de Anotar rechazado: un reintento sobre el `origin/main` nuevo y, si falla, aviso en la web sin tocar la copia); `prueba_hooks.py` comprueba que una línea de `acciones.jsonl` sale en un solo monitor y que, sin OS activo, el monitor no la lee.
**Hecha (PR #8), salvo lo que es de K-99.** `hkos/acciones.py`, las rutas de acción de `agente.py` y la entrega por `escucha.sh`; los criterios 7 y 8 quedan cubiertos sin sandbox por `hkos/pruebas/test_acciones.py` (remoto `bare`, dos clones y `gh` falso) y por `prueba_hooks.py` (un solo monitor de dos; nada sin OS activo ni con `web_nueva: no`). Falta lo de K-99: Anotar y Reclamar en `Mveradc/hk-sandbox` con @hk-persona-b (asignación y `gh api user` reales, push a `main` de GitHub, la nota en novedades en ≤ 60 s con el relay de verdad) y la prueba interactiva del turno.

### K-96 · `prueba.sh` [P]
Cubre: R-33 · Depende de: K-91 · Puedes tocar: `scripts/os/prueba.sh`, `scripts/os/comun.sh`, `hooks/hooks.json`, `hkos/normaliza.py`, `evals/coordinacion/prueba_hooks.py`
Contratos que aplican: `api.md` §1 y §2
Hecho cuando: `prueba_hooks.py`: un Bash cuyo comando es exactamente la Prueba de una conexión deja una línea cruda `prueba` (pasa o falla) que el normalizador convierte en un evento válido; cualquier otro comando no deja nada; sin OS activo o con `web_nueva: no`, nada.

### K-97 · Proyección de servicios
Cubre: R-24, R-28 · Depende de: K-93 · Puedes tocar: `hkos/proyeccion.py`, `scripts/os/delta.sh`, `scripts/coordinacion/sesion.sh`, `evals/coordinacion/simulador/`
Contratos que aplican: `api.md` §6, ADR-0009
Hecho cuando: la vista lleva el bloque `servicios`; `estado-equipo.md` lleva `## Servicios` (desajustes y propuestas que afectan a la persona) y su firma, dentro del presupuesto de R-24; `igualdad.py` pasa con G1–G6 y el guion nuevo G12 (servicios).

### K-98 · Web React + Vite
Cubre: R-26, R-33 · Depende de: K-94, K-97 · Puedes tocar: `hkos/web-src/`, `hkos/web/nueva/`, `.github/workflows/web-m9a.yml`
Contratos que aplican: ADR-0009, `docs/hackathon-os/diseno-web/`
Hecho cuando: criterios 2, 3 y 4 de M9a; cabina por defecto; el token, fuera de la URL nada más leerlo y solo en memoria; el stream, con `fetch` y `X-HK-Token`; «sin conexión» tras `max(umbral_viejo_s, 40 s)` sin datos; `TeamGraph` reescrito para React 19, no copiado de `diseno-web/`: refs como prop y sin `forwardRef`, y cada paquete ligado a un `id` de evento, que se lanza una vez y se retira al acabar su animación de CSS o SVG, sin temporizadores que generen actividad; los siete componentes con sus nombres, props y clases `hk-*`; fuentes dentro del repo; el CI en verde.

### Revisión independiente de K-91–K-97 (issue #2)
Hallazgos **1, 4, 5, 6, 9 y 13 resueltos** por el PR #7 (`hkos/servicios.py` y la lectura de la historia de `servicios.md` en `hkos/relay.py`, con sus pruebas en `test_servicios.py` y `test_relay_m9a.py`): ninguna fila sale «confirmada» por error. El 8 (`prueba.sh` con un Bash en segundo plano) lo arregla el commit de `prueba.sh` de la rama `m9a-prueba-docs`. Siguen abiertos el 2, 3, 7, 10, 11 y 12. Lo que el PR #7 pide en ADR-0011, `api.md` §10 y `estado.schema.json` (contratos congelados) queda para quien los revise.

### K-99 · Validación con modelo y en sandbox
Depende de: todo lo anterior · Puedes tocar: `evals/coordinacion/`, carpetas de prueba en `../`
Hecho cuando: criterios 1, 5, 8 y 9 de M9a; `/hack-scaffold` y `/hack-plan` con el reto 03 y la coordinación activa; Anotar y Reclamar en `Mveradc/hk-sandbox` con @hk-persona-b; resultados en `evals/coordinacion/prueba.md` («M9a»).
Va después de que el usuario decida el borrador de contratos y ADR del PR #13 (2026-10-18), para validar contra el contrato que quede.
**Hecha (2026-10-18):** PR #36 y #37; el turno interactivo, el usuario. Resultados en `evals/coordinacion/prueba.md` («M9a, K-99» y «M9a, cierre»).
