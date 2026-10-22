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
**Hecha (2026-10-18):** la 0.4.0 sale sin ensayo, por decisión del usuario; `docs/limitaciones.md` lo dice.

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

## M10 · Vista de jurado y ruta crítica

Abierto el 2026-10-19 (decisiones del usuario en el PR #42 y el issue #41; ADR-0012 y ADR-0013 aceptados; contratos en `api.md` §11). Todo lo de M10 corre solo con `vista_jurado:` o `ruta_critica:` en `os.md`. Reparto en terminales: K-102, K-103 y K-104 en paralelo y, después, K-105, K-106 y K-107 en paralelo. En cada tanda, las rutas de las tres tareas no se pisan, y cada tarea tiene su propio fichero de prueba nuevo. Los nombres de campos, secciones y firmas son los de `api.md` §6 y §11 y `estado.schema.json`.

### K-100 · Paso 0 de M10
Cubre: R-35, R-36 · Puedes tocar: scratchpad (fuera del repo del kit), `evals/coordinacion/prueba.md` (solo «M10, Paso 0»)
Hecho cuando: el inventario del issue #41 está cerrado y anotado en `evals/coordinacion/prueba.md` («M10, Paso 0»), con:
- las preguntas de #41 respondidas por el usuario (2026-10-19: en ADR-0012 y ADR-0013; N = 3, fijo en el contrato);
- cuántos `Hasta` de los planes de ejemplo (02, 03) y de `evals/coordinacion/partida-m8-03` se resuelven a una hora absoluta con las reglas de `api.md` §11.2, y cuáles no y por qué motivo;
- el tamaño en caracteres de la sección `## Jurado y ruta` y del bloque de inicio con 5 personas, 20 tareas y 15 notas (para el criterio 6);
- el tiempo de reconstruir la historia de transiciones desde un `relay/eventos.jsonl` sintético de 39 h (al arrancar el relay y por incrementos), en Windows.

### K-101 · ADR y contratos
Cubre: R-35, R-36 · Depende de: K-100 (las preguntas) · Puedes tocar: `docs/hackathon-os/adr/0009-*.md` (la nota de J7), `0012-*.md`, `0013-*.md`, `docs/hackathon-os/contratos/api.md`, `docs/hackathon-os/contratos/estado.schema.json`
Contratos que aplican: ADR-0006, ADR-0009
Hecho cuando:
- ADR-0012 y ADR-0013 aceptados, con cada decisión y su porqué, y la tabla en «Decididas (2026-10-19)»; ADR-0009 con la nota de J7;
- `api.md` con la §11 nueva (interruptores, lo que lee el relay, bloques `jurado` y `ruta`, MCP y vista de ejemplo) y lo que cambia en §3, §4 y §6, todo marcado «tras congelar, 2026-10-19, M10»;
- `estado.schema.json` con `jurado`, `ruta`, los campos nuevos de las tareas (`hasta` con su motivo, `franja`, `orden_plan`, `historia`, `criterios`, `conexiones`) y los `$defs` de la nota (con su clave) y de los bloques de la vista, todos opcionales hasta que exista el código;
- el esquema valida con el validador de M8b y con jsonschema, y la vista de ejemplo de §11.6 valida contra `$defs/vista_jurado` y `$defs/vista_ruta`; `hkos/pruebas`, `igualdad.py` y `prueba_hooks.py` en verde;
- R-35 y R-36 no cambian (ninguna decisión los toca); G13 y G14 se describen en `simulador.md` en K-105.

Lo revisa el usuario antes de K-102.
**En el PR #42 (2026-10-19):** listo para revisar.

### K-102 · Cobertura del jurado (función pura) [P]
Cubre: R-35 · Depende de: K-101 · Puedes tocar: `hkos/jurado.py`, `hkos/pruebas/test_jurado.py`
Contratos que aplican: ADR-0012, `api.md` §11.3, `$defs/vista_jurado`
Hecho cuando: `hkos/jurado.py` calcula el bloque `jurado` (con `resumen` y la `cuenta` de la firma) y pasa su tabla de casos, cada salida validada contra `$defs/vista_jurado`:
- nota sin enlace (`sin_tarea`);
- nota declarada con su tarea en curso (`declarada`);
- nota cubierta: todas sus tareas publicadas o cerradas, con la evidencia y su hora; con una de dos sin hacer, `declarada`;
- dos notas en el mismo minuto: la cita sin quién, `ambigua`; con «· quién», casa con una;
- una cita que no casa con ninguna nota (`sin_nota`);
- una nota solo en el pitch (`en_pitch`), y una con tarea y pitch (la cobertura, de la tarea);
- una nota que corrige a otra (`corregida_por`), y una corrección ambigua (no marca ninguna);
- una tarea `cerrada` a mano (⚑): `declarada`, no `cubierta`;
- una publicada que vuelve a `en_curso`: sigue `cubierta`, con `trabajo_nuevo_desde`;
- una Prueba que falla y una vieja: se enseñan y no cambian la cobertura;
- una evidencia vieja: cobertura `viejo`;
- el orden: sin cubrir por fuerza y luego por hora, cubiertas, corregidas;
- una nota con texto imperativo, que sale como dato, entrecomillada.

Sin red, sin git y sin reloj propio (`ahora` es un parámetro).

### K-103 · Ruta crítica (función pura) [P]
Cubre: R-36 · Depende de: K-101 · Puedes tocar: `hkos/ruta.py`, `hkos/pruebas/test_ruta.py`
Contratos que aplican: ADR-0013, `api.md` §11.4, `$defs/vista_ruta`
Hecho cuando: `hkos/ruta.py` calcula el bloque `ruta` (con `resumen` y el veredicto de la firma) y pasa su tabla de casos, cada salida validada contra `$defs/vista_ruta`:
- sin `Entrega:`, ilegible o sin resolver: `sin_entrega`; con dos horas en la línea: `entrega_doble`;
- la fila de Hitos o una nota `dato` distinta de `equipo.md`: en `otras_entregas`, **con** estimación; con «(confirmar)», estimación con `confirmar: true`;
- un ciclo en las dependencias (hecho y motivo);
- una tarea abierta sin franja: `sin_plazo`, nunca «a tiempo»;
- un plazo vencido (rojo) y lo que arrastra, por `depende_de` y por orden del plan;
- una persona con tareas abiertas y menos de 3 medidas: `pocos_datos`, sin hora prevista, «n de 3»;
- 3 o más por persona: rango, margen contra la entrega, base y cada uno de los veredictos `a_tiempo`, `justo` y `no_llega` (ámbar), en sus fronteras;
- la cadena de cada persona (`orden_del_plan`) y la cadena más larga;
- tareas «Si …» y `[SI DA TIEMPO]` fuera de la entrega;
- descansos: no cuentan en el ritmo ni en el fin previsto, y no sacan «sin señales»;
- una persona sin señales: hecho `sin_senales` (gris), nunca riesgo por lentitud;
- una `cerrada` a mano: hecha para la ruta, no medida;
- un dato viejo: el bloque `viejo`, con `dato_mas_viejo`;
- el veredicto (la firma) no cambia si solo se mueven la hora estimada, el margen o los hechos.

Sin red, sin git y con `ahora` como parámetro.

### K-104 · Datos de entrada en el relay [P]
Cubre: R-35, R-36 · Depende de: K-101 · Puedes tocar: `hkos/lecturas.py` (nuevo: los lectores puros de `criterios.md`, `equipo.md`, `plan.md` —etiquetas, `Hasta`, franjas, orden, Hitos y Descansos— y `pitch.md`), `hkos/relay.py`, `hkos/modelo.py` (historia de transiciones), `hkos/red.py` (lectura de `vista_jurado:` y `ruta_critica:`), `hkos/pruebas/test_relay_m10.py`
Contratos que aplican: `api.md` §3 y §11.1–§11.2, `estado.schema.json`
Hecho cuando:
- con los interruptores encendidos, `estado.json` lleva, leído de `origin/main` del clon del relay:
  - `jurado`: las notas de `criterios.md` con su clave y todos sus campos, el estado del fichero y las citas de `pitch.md`;
  - en las tareas, `criterios` (la etiqueta de «Cómo se comprueba») y `conexiones`;
  - `ruta`: `equipo`, `zona`, `inicio`, `entrega` (con `confirmar` y el motivo `dos_horas`), `otras_entregas`, `hitos` y `descansos`;
  - en las tareas, `hasta` (resuelto o `null` con su motivo), `franja`, `orden_plan`, `historia` y `evidencia`;
- los `Hasta` de los planes 02 y 03 se resuelven como dice K-100;
- todo lo nuevo valida contra el esquema;
- con los interruptores apagados, `estado.json` sale byte a byte como hoy (`test_relay.py`, `test_relay_m9a.py` y `carga.py` sin cambios);
- el arranque con un registro grande, dentro de lo medido en K-100.

`compilar.py` y `github.py` no se tocan: el plan se lee con `compilar.leer_plan` tal como está.

### K-105 · Proyección, MCP y guiones G13 y G14 [P]
Cubre: R-24, R-25, R-28, R-35, R-36 · Depende de: K-102, K-103, K-104 · Puedes tocar: `hkos/proyeccion.py`, `hkos/mcp.py`, `scripts/os/delta.sh`, `scripts/coordinacion/sesion.sh`, `evals/coordinacion/simulador/` (G13 y G14, `simula.py`, `igualdad.py`, `fixture.py`, `tareas-03.json`), `docs/hackathon-os/simulador.md` (G13 y G14), `hkos/pruebas/test_proyeccion_m10.py`
Contratos que aplican: `api.md` §6 y §11.3–§11.5, ADR-0009 (con su nota), ADR-0012, ADR-0013
Hecho cuando:
- la vista lleva los bloques `jurado` y `ruta`, calculados con `hkos/jurado.py` y `hkos/ruta.py`, solo si `estado.json` trae `jurado` o `ruta`;
- `estado-equipo.md` lleva la sección `## Jurado y ruta` (una línea por bloque, el `resumen`) y las firmas `jurado:` (la cuenta) y `ruta:` (solo el veredicto), dentro del presupuesto (criterio 6 de M10, con G10 ampliado); el delta recorre las secciones en el orden de §6;
- el MCP responde `jurado` y `ruta` (§11.5);
- criterios 2 y 3 de M10 (G13 y G14 en el simulador, descritos en `simulador.md`);
- `igualdad.py` en G1–G6, G12, G13 y G14 (la parte de datos del criterio 4: bloques enteros vista–MCP y línea del md–`resumen`).

### K-106 · Web: jurado y ruta [P]
Cubre: R-26, R-35, R-36 · Depende de: K-101 (para empezar, con la vista de ejemplo de `api.md` §11.6) y K-105 (para cerrar, con las vistas de G13 y G14) · Puedes tocar: `hkos/web-src/` (incluido `scripts/vistas_ejemplo.py`), `hkos/web/nueva/`, `.github/workflows/web-m9a.yml`
Contratos que aplican: ADR-0009, ADR-0012, ADR-0013, `api.md` §4 y §11, `docs/hackathon-os/diseno-web/` (las pantallas del PR #43, con el margen contra la entrega y la franja en lugar de horas declaradas)
Hecho cuando:
- la parte de Vitest y CI del criterio 4 de M10: G13, G14 y la vista de ejemplo pintados, y cada campo en el DOM con el mismo texto;
- la web no calcula nada: ni cobertura, ni orden, ni rangos, ni veredicto, ni «viejo» (ADR-0009). Solo formatea «hace X» y coloca en la línea de tiempo las horas que trae la vista;
- lo que es estimación se pinta distinto de los hechos; el rojo, solo para `plazo_pasado`; «no llega», ámbar; lo declarado, con su marca;
- sigue el criterio 2 de M9a: sin URL externa y compilado igual al fuente;
- sin los bloques en la vista, la web es la de la 0.4.0.

### K-107 · Cadena e interruptores [P]
Cubre: R-01, R-35, R-36 · Depende de: K-101 · Puedes tocar: `skills/hack-scaffold/templates/os.md`, `skills/hack-scaffold/templates/CLAUDE.md`, `skills/hack-scaffold/SKILL.md`, `skills/hack-scaffold/examples/`, `skills/hack-plan/` (`SKILL.md`, `templates/`, `examples/`), `skills/hack-check/SKILL.md`
Contratos que aplican: ADR-0012 (decisiones 3A y 8A), ADR-0013 (decisiones 1A, 2A, 8B, 9A y 11C), `api.md` §11.1–§11.2
Hecho cuando:
- `os.md` de `/hack-scaffold` trae `vista_jurado: no` y `ruta_critica: no`;
- el `CLAUDE.md` que genera `/hack-scaffold` recuerda, en Convenciones, que cada commit empieza por `Txx · …` (el ID de su tarea);
- `/hack-plan` lee `criterios.md` y pone la etiqueta `(criterios: <fecha hora>[ · quién])` al final de «Cómo se comprueba» de las filas que recogen una nota; escribe `Hasta` con día y hora (`sáb 02:30`) o `H+N`, marca los repliegues con «Si …» o `[SI DA TIEMPO]` y escribe «## Descansos» como `- <@usuario | Todos>: <día> HH:MM–HH:MM`; con las mismas 5 columnas, y `compilar.leer_plan` lo lee sin errores;
- `/hack-check aplicar` pone o corrige esa etiqueta en el plan (no en `criterios.md`, que solo escriben personas), con «· quién» cuando dos notas comparten minuto;
- con el reto 03, `hkos/lecturas.py` (K-104) saca del plan generado los enlaces, los plazos, la entrega y los descansos (comprobado cuando K-104 esté; antes, contra las reglas de §11.2);
- `comprobar.py` sin regresiones con los retos 02 y 03;
- los ejemplos, regenerados y anonimizados.

### K-108 · Validación con modelo y en sandbox
Depende de: todo lo anterior · Puedes tocar: `evals/coordinacion/` (incluido un `jurado_ruta_vivo.py` nuevo), `docs/limitaciones.md` (validación sin datos reales), carpetas de prueba en `../`
Hecho cuando: criterios 1, 5 y 7 de M10, con los resultados en `evals/coordinacion/prueba.md` («M10»). El cierre se anota en `hitos.md` y en `docs/historial.md`, y la 0.5.0 la decide el usuario. El ensayo con un equipo, después (revisa el 3 y los umbrales del veredicto).
**Hecha (2026-10-21):**
- La primera pasada, el 2026-10-20 (PR #70): el criterio 7 falló por la sesión por MCP.
- El ajuste 5, en los PR #71–#74.
- La sesión por MCP, repetida tres veces el 2026-10-21, pasa.

Resultados en `evals/coordinacion/prueba.md` («M10, K-108» y «M10, K-108, repetición del MCP»).

## M11 · Nivel 2b de colisiones con Mergiraf

Especificado el 2026-10-21; ADR-0014 aceptado el 2026-10-22 (las siete recomendaciones, PR #78; sección M11 de `hitos.md`). Mergiraf solo se instala, a mano y opcional, en el portátil del coordinador; el kit nunca lo instala ni lo pide (decisión 1A, que revoca la del 2026-10-14 solo para ese portátil). Cuándo se empieza lo decide el usuario. Todo lo de M11 corre solo en el relay y solo con `fusion_estructural: sí`, `publicar_wip: sí` y Mergiraf en el `PATH`. Reparto en terminales: K-109 y K-110 seguidas; después K-111, K-112 y K-113 en paralelo (sus rutas no se pisan y cada una tiene su propio fichero de prueba nuevo); al final, K-114. La interfaz entre K-111 y K-112 es la de ADR-0014: `conflictos` = `[{personas, rutas, rutas_2b, desde, desde_2b}]`, con `rutas_2b` y `desde_2b` solo si 2b está activo.

### K-109 · Paso 0 de M11
Cubre: R-34 · Puedes tocar: scratchpad (fuera del repo del kit), `evals/coordinacion/prueba.md` (solo «M11, Paso 0»), `docs/coordinacion.md` (las filas de P12 y P17), `docs/hackathon-os/preguntas-abiertas.md` (P17)
Hecho cuando: «M11, Paso 0» de `evals/coordinacion/prueba.md` tiene, además de P12 en Linux (hecho el 2026-10-21, Mergiraf 0.20.0):
- P17: en Windows (y en macOS si hay quien lo pruebe), el binario de la release oficial arranca con un comando, los casos de P12 dan los mismos códigos de salida, y se sabe dónde guarda las copias de lo que resuelve y si se pueden llevar a un directorio temporal;
- cuánto tarda Mergiraf en los ficheros de los retos 02 y 03 (los más grandes de cada lenguaje del reto), para confirmar los plazos de ADR-0014 (5 s por fichero, 20 s por ciclo);
- que `git merge-tree --write-tree --no-messages` sin `--name-only` da las etapas con el mismo código de salida en Git 2.38 (la mínima del nivel 2) y en la del relay de Windows (P11: 2.49);
- la versión mínima de Mergiraf que se acepta (decisión 5 de ADR-0014).
Nada se instala en el repo ni se añade como dependencia. Sin modelo.

### K-110 · ADR y contratos
Cubre: R-34 · Depende de: K-109 · Puedes tocar: `docs/hackathon-os/adr/0014-*.md` (solo lo que cambie con P17), `docs/hackathon-os/contratos/api.md`, `docs/hackathon-os/diseno.md` (§7)
Contratos que aplican: ADR-0007, ADR-0009, ADR-0014
Hecho cuando:
- ADR-0014 (aceptado el 2026-10-22) con lo que cambie con P17 (Windows y macOS: copias de Mergiraf, binario, versión mínima), como ajuste fechado;
- `api.md` con las notas «tras congelar, M11» de la decisión 6: §0 (`fusion_estructural:`), §3 (el nivel 2b en el párrafo de colisiones del relay), §5 (la frase de la descripción de `colisiones`) y §6 (la línea `2b` de ejemplo); `estado.schema.json` sin cambios (el valor `2b` ya estaba);
- `diseno.md` §7 con la fila 2b al día y la definición de «Nivel 2b»;
- R-34 no cambia; G15 se describe en `simulador.md` en K-112;
- `hkos/pruebas`, `igualdad.py` y `prueba_hooks.py` en verde.

Lo revisa el usuario antes de K-111.

### K-111 · Mergiraf en el cálculo del nivel 2 [P]
Cubre: R-34 · Depende de: K-110 · Puedes tocar: `hkos/colisiones_merge.py`, `hkos/pruebas/test_colisiones_2b.py`, `hkos/pruebas/mergiraf_falso.py` (nuevo: un `mergiraf` falso que anota sus llamadas y devuelve el código que se le pida)
Contratos que aplican: ADR-0014 (detección, cuándo se ejecuta, plazos, caché, limpieza), `api.md` §3
Hecho cuando: la clase `Calculo` (o una pieza nueva en el mismo módulo, llamada desde ella):
- detecta Mergiraf al arrancar (`shutil.which`, `mergiraf --version` con plazo de 5 s, versión mínima) solo si se le pasa `fusion_estructural=True`, y avisa una vez si falta;
- ejecuta `merge-tree` sin `--name-only`, lee las etapas y da `rutas` y `rutas_2b` por par, con `desde` y `desde_2b`;
- intenta Mergiraf solo con las tres etapas y modos `100644`/`100755`, con los blobs en un directorio temporal fuera del clon, `-p <ruta>`, `-t 5000`, `XDG_DATA_HOME` en ese directorio (y lo que diga P17 en Windows y macOS), sin `--allow-parse-errors`, y borra el directorio siempre;
- cuenta como resuelto solo el rc 0; respeta los plazos de 10 s por proceso y 20 s por ciclo; guarda en caché por `(blobs, ruta)` también el «no resuelve»;
- pasa los casos del criterio 2 de M11 (con el falso y, si está, con el real);
- con `fusion_estructural=False` (o sin el parámetro), `conflictos` y las llamadas a git son las de la 0.5.0: `test_colisiones_merge.py` sin cambios y en verde.

### K-112 · Modelo, relay, proyección, MCP y guion G15 [P]
Cubre: R-24, R-25, R-28, R-34 · Depende de: K-110 · Puedes tocar: `hkos/colisiones.py`, `hkos/relay.py` (pasar el interruptor a `Calculo`), `hkos/red.py` (lectura de `fusion_estructural:`), `hkos/proyeccion.py` (`linea_colision`), `hkos/mcp.py` (la descripción de `colisiones`), `evals/coordinacion/simulador/` (G15, `simula.py`, `igualdad.py`, `fixture.py`), `docs/hackathon-os/simulador.md` (G15), `hkos/pruebas/test_proyeccion_m11.py`
Contratos que aplican: ADR-0009, ADR-0014, `api.md` §0, §3, §5 y §6, `estado.schema.json`
Hecho cuando:
- `colisiones.calcular` da `2:<a>+<b>` rojo con `rutas` y `2b:<a>+<b>` amarillo con `rutas_2b` (cada una solo si tiene rutas), y las dos tapan el nivel 1 entre esas personas; sin `rutas_2b`, la salida es la de la 0.5.0 (`test_colisiones.py` sin cambios);
- el relay lee `fusion_estructural:` de su `os.md` y se lo pasa al cálculo del nivel 2;
- `estado-equipo.md` lleva `- AMARILLO · nivel 2b · fusión estructural sin conflictos · …` (decisión 7) y la firma de colisiones cambia al bajar o subir de nivel;
- la descripción de `colisiones` en el MCP lleva la frase de ADR-0014;
- criterios 3 (la parte de datos: G15 e `igualdad.py` en G1–G6 y G12–G15) y 4 de M11 (delta y monitor con `delta.sh` y `escucha.sh` tal como están, que no se tocan);
- con el interruptor apagado, `estado.json`, la vista y `estado-equipo.md` byte a byte como en la 0.5.0 (criterio 1 de M11, la parte sin relay vivo).

### K-113 · Web, cadena y documentación [P]
Cubre: R-01, R-26, R-34 · Depende de: K-110 · Puedes tocar: `hkos/web-src/` (solo pruebas de Vitest y el texto de la alerta, decisión 7), `hkos/web/nueva/`, `hkos/web/index.html` (solo el texto de la decisión 7), `skills/hack-scaffold/templates/os.md`, `README.md` (la línea de Mergiraf), `docs/limitaciones.md`
Contratos que aplican: ADR-0009, ADR-0014 (decisiones 1, 2, 3 y 7)
Hecho cuando:
- Vitest pinta una colisión `2b` (la de G15 cuando K-112 la tenga; antes, una vista de ejemplo) y el texto sale en el DOM igual que en el md; la web no calcula nada nuevo;
- sigue el criterio 2 de M9a: sin URL externa y compilado igual al fuente;
- `os.md` de `/hack-scaffold` trae `fusion_estructural: no` con un comentario que dice que hace falta Mergiraf solo en el portátil del relay;
- el README y `docs/limitaciones.md` dicen cómo se instala Mergiraf en el portátil del coordinador (decisión 3: binario oficial en Windows y Linux, `brew install mergiraf` en macOS y `cargo install --locked mergiraf` como alternativa, según lo que confirme P17), que el kit no lo instala ni lo pide, qué lenguajes baja y que «amarillo» no quiere decir que la fusión funcione;
- `comprobar.py` sin regresiones con un reto, sin coordinación.

### K-114 · Validación en vivo
Depende de: todo lo anterior · Puedes tocar: `evals/coordinacion/` (incluido un `colisiones_2b_vivo.py` nuevo), `docs/limitaciones.md`, carpetas de prueba en `../`
Hecho cuando: criterios 1 (la parte con el relay vivo), 5, 6 y 7 de M11, con los resultados en `evals/coordinacion/prueba.md` («M11»). Sin modelo: el nivel 2b no depende de ninguna sesión de Claude Code. El cierre se anota en `hitos.md` y en `docs/historial.md`; la versión que lo lleve la decide el usuario.
