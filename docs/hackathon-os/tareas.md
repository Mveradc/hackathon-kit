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

## M10 · Vista de jurado y ruta crítica — BORRADOR

**BORRADOR (2026-10-19):** lo decide el usuario junto con ADR-0012 y ADR-0013. Todo lo de M10 corre solo con los interruptores de ADR-0012 (decisión 8) en `os.md`. Reparto en terminales: K-102, K-103 y K-104 en paralelo (no comparten ficheros) y, después, K-105, K-106 y K-107 en paralelo. Los ficheros de prueba son nuevos y uno por tarea, para que no se pisen. Los nombres de campos y secciones siguen a lo que fije K-101 en los contratos.

### K-100 · Paso 0 de M10
Cubre: R-35, R-36 · Puedes tocar: scratchpad (fuera del repo del kit), `evals/coordinacion/prueba.md` (solo «M10, Paso 0»)
Hecho cuando: el inventario del issue #41 está cerrado y anotado en `evals/coordinacion/prueba.md` («M10, Paso 0»), con:
- las preguntas de #41 respondidas por el usuario, o pasadas a las tablas de ADR-0012 y ADR-0013;
- cuántos `Hasta` de los planes de ejemplo (02, 03) y de `evals/coordinacion/partida-m8-03` se resuelven a una hora absoluta con `equipo.md`, y cuáles no;
- el tamaño en caracteres de las secciones nuevas de `estado-equipo.md` con 5 personas, 20 tareas y 15 notas (para el criterio 6);
- el tiempo de reconstruir la historia de transiciones desde un `relay/eventos.jsonl` sintético de 39 h (al arrancar el relay y por incrementos), en Windows;
- una propuesta de N (tareas medidas mínimas) con el guion largo del reto 03.

### K-101 · ADR, requisitos y contratos
Cubre: R-35, R-36 · Depende de: K-100 · Puedes tocar: `docs/hackathon-os/adr/0012-*.md`, `0013-*.md`, `docs/hackathon-os/requisitos.md` (R-35 y R-36), `docs/hackathon-os/simulador.md` (G13 y G14), `docs/hackathon-os/contratos/`
Contratos que aplican: ADR-0006, ADR-0009
Hecho cuando:
- ADR-0012 y ADR-0013 aceptados con lo que decida el usuario, sin «Decisiones pendientes» abiertas;
- R-35 y R-36 reescritos si alguna decisión los cambia (rúbrica, ritmo);
- `api.md` sin `[POR DECIDIR]` en §0 (interruptores), §3 (lo que lee el relay), §5 (MCP), §6 (secciones del md y bloques `jurado` y `ruta` de la vista, con una vista de ejemplo) y §7;
- `estado.schema.json` con los campos nuevos (plazo resuelto y `evidencia` de las tareas, notas, entrega e historia), que validan con el validador de M8b;
- G13 y G14 descritos en `simulador.md`.

Lo revisa el usuario antes de K-102.

### K-102 · Cobertura del jurado (función pura) [P]
Cubre: R-35 · Depende de: K-101 · Puedes tocar: `hkos/jurado.py`, `hkos/pruebas/test_jurado.py`
Contratos que aplican: ADR-0012, `api.md` §6
Hecho cuando: `hkos/jurado.py` pasa su tabla de casos:
- nota sin enlace;
- nota declarada con su tarea en curso;
- nota cubierta, con la evidencia y su hora;
- dos notas en el mismo minuto, con un enlace ambiguo;
- un enlace a una tarea que no existe;
- una nota que corrige a otra;
- una tarea `cerrada` a mano (⚑): declarada, no cubierta;
- una publicada que vuelve a `en_curso` (decisión 6);
- una evidencia vieja;
- una nota con texto imperativo, que sale entrecomillada;
- y lo de las decisiones 1, 4 y 5 que se elija (rúbrica, Prueba, pitch).

Sin red, sin git y sin reloj propio (`ahora` es un parámetro).

### K-103 · Ruta crítica (función pura) [P]
Cubre: R-36 · Depende de: K-101 · Puedes tocar: `hkos/ruta.py`, `hkos/pruebas/test_ruta.py`
Contratos que aplican: ADR-0013, `api.md` §6
Hecho cuando: `hkos/ruta.py` pasa su tabla de casos:
- sin entrega, y con dos entregas distintas;
- un ciclo en las dependencias;
- una tarea sin plazo, que no sale como «a tiempo»;
- un plazo vencido y lo que arrastra;
- menos de N tareas medidas: sin hora prevista y «n de N»;
- N o más: rango, base y veredicto;
- la cadena de cada persona, si se elige en la decisión 3;
- descansos (decisión 9);
- una persona sin señales: «sin señales», no riesgo;
- un dato viejo;
- la firma para los deltas, que no cambia si solo se mueve la hora estimada.

Sin red, sin git y con `ahora` como parámetro.

### K-104 · Datos de entrada en el relay [P]
Cubre: R-35, R-36 · Depende de: K-101 · Puedes tocar: `hkos/relay.py`, `hkos/modelo.py`, `hkos/github.py`, `hkos/red.py` (lectura de los interruptores), `hkos/compilar.py` (solo si la decisión 2 de ADR-0013 o la 3 de ADR-0012 lo piden, para el modo sin GitHub), `hkos/pruebas/test_relay_m10.py`
Contratos que aplican: `api.md` §0, §3 y §8, `estado.schema.json`
Hecho cuando:
- con los interruptores encendidos, `estado.json` lleva:
  - las notas de `criterios.md` de `origin/main`, con su clave y todos sus campos;
  - los enlaces declarados (decisión 3 de ADR-0012);
  - el plazo de cada tarea, resuelto o `null` con su motivo;
  - `tareas[].evidencia`, rellena;
  - la entrega, con sus discrepancias;
  - la historia de transiciones por tarea, reconstruida desde `relay/eventos.jsonl` y los eventos de GitHub;
- todo lo nuevo es `{valor, fuente, observado_en}` y valida contra el esquema;
- con los interruptores apagados, `estado.json` sale byte a byte como hoy (`test_relay.py`, `test_relay_m9a.py` y `carga.py` sin cambios);
- el arranque con un registro grande, dentro de lo medido en K-100.

### K-105 · Proyección, MCP y guiones G13 y G14 [P]
Cubre: R-24, R-25, R-28, R-35, R-36 · Depende de: K-102, K-103, K-104 · Puedes tocar: `hkos/proyeccion.py`, `hkos/mcp.py`, `scripts/os/delta.sh`, `scripts/coordinacion/sesion.sh`, `evals/coordinacion/simulador/` (G13 y G14, `simula.py`, `igualdad.py`, `fixture.py`, `tareas-03.json`), `hkos/pruebas/test_proyeccion_m10.py`
Contratos que aplican: `api.md` §5 y §6, ADR-0009, ADR-0012, ADR-0013
Hecho cuando:
- la vista lleva los bloques `jurado` y `ruta`, calculados con `hkos/jurado.py` y `hkos/ruta.py`;
- `estado-equipo.md` lleva sus secciones y sus firmas, dentro del presupuesto (criterio 6 de M10, con G10 ampliado);
- el MCP responde las consultas que fije `api.md` §5;
- criterios 2 y 3 de M10 (G13 y G14 en el simulador);
- `igualdad.py` en G1–G6, G12, G13 y G14 (la parte de datos del criterio 4).

### K-106 · Web: jurado y ruta [P]
Cubre: R-26, R-35, R-36 · Depende de: K-101 (para empezar, con la vista de ejemplo de `api.md` §6) y K-105 (para cerrar, con las vistas de G13 y G14) · Puedes tocar: `hkos/web-src/` (incluido `scripts/vistas_ejemplo.py`), `hkos/web/nueva/`, `.github/workflows/web-m9a.yml`
Contratos que aplican: ADR-0009, ADR-0012, ADR-0013, `docs/hackathon-os/diseno-web/` (lo que haya cuando empiece: otra terminal lo está diseñando)
Hecho cuando:
- la parte de Vitest y CI del criterio 4 de M10: G13 y G14 pintados, y cada campo en el DOM con el mismo texto;
- la web no calcula nada: ni estados, ni rangos, ni «viejo» (ADR-0009). Solo formatea «hace X»;
- lo que es estimación se pinta distinto de lo que es hecho, y lo declarado con su marca;
- sigue el criterio 2 de M9a: sin URL externa y compilado igual al fuente;
- con los interruptores apagados, la web es la de la 0.4.0.

### K-107 · Cadena e interruptores [P]
Cubre: R-01, R-35, R-36 · Depende de: K-101 · Puedes tocar: `skills/hack-scaffold/templates/os.md`, `skills/hack-plan/` (`SKILL.md`, `templates/`, `examples/`), `skills/hack-check/SKILL.md`, `skills/hack-scaffold/templates/CLAUDE.md` (cada uno solo si su decisión lo pide: enlaces en el plan, entrega, descansos, «Txx ·» en los commits)
Contratos que aplican: ADR-0012 (decisiones 3 y 8), ADR-0013 (decisiones 1, 2, 9 y 11)
Hecho cuando:
- `os.md` de `/hack-scaffold` trae los interruptores, apagados;
- `/hack-plan` con el reto 03 genera un plan que `compilar.leer_plan` lee sin errores, con las mismas 5 columnas, y del que las funciones de K-104 sacan los enlaces, los plazos y la entrega;
- `comprobar.py` sin regresiones con los retos 02 y 03;
- los ejemplos, regenerados y anonimizados.

### K-108 · Validación con modelo y en sandbox
Depende de: todo lo anterior · Puedes tocar: `evals/coordinacion/` (incluido un `jurado_ruta_vivo.py` nuevo), carpetas de prueba en `../`
Hecho cuando: criterios 1, 5 y 7 de M10, con los resultados en `evals/coordinacion/prueba.md` («M10»). El cierre se anota en `hitos.md` y en `docs/historial.md`, y la 0.5.0 la decide el usuario.
