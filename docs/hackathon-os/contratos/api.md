# Contratos: ficheros, eventos, API del relay, demonio y MCP

Un contrato congelado solo cambia subiendo `v` o con una nota aquí con su motivo. Las marcas `[POR DECIDIR]` se cierran antes de implementar lo que afectan.

| Parte | Estado |
|---|---|
| §1, §2, [eventos.schema.json](eventos.schema.json), [estado.schema.json](estado.schema.json) | **Congelados** (M8b, 2026-10-14) |
| §0 y §7 | **Congelados** (M8c, 2026-10-14) |
| §3 y §4 | **Congelados** (M8d, 2026-10-14) |
| §5 y §6 | **Congelados** (M8f, 2026-10-15) |
| §8 | **Congelado** (M8e, 2026-10-15) |
| §9 | **Nueva** (M8h, 2026-10-15): se congela al cerrar M8h |
| Lo de M9a en §0–§7, §10 y los dos esquemas | **Congelados** (K-91, M9a, 2026-10-17, aprobados por el usuario) |
| §11 y lo de M10 en §3, §4, §6 y [estado.schema.json](estado.schema.json) | **Nuevo** (tras congelar, 2026-10-19, M10, K-101): lo revisa el usuario en el PR #42 antes de K-102 |

Cambios tras congelar (sin subir `v`: solo añaden campos opcionales o fijan reglas que el código aún no usaba):
- 2026-10-14, M8c, §1: `transcript_path` en `SubagentStart`. Sin él, el demonio tendría que adivinar la carpeta de la sesión a partir del `cwd`, y M8.0 vio que eso se rompe con las mayúsculas de la ruta. Es una ruta local, no contenido.
- 2026-10-14, M8c, §1 y §2: el `id` del evento normalizado es `<session_id>-<nº de línea del JSONL>`, y los JSONL solo crecen. Así, releer un fichero da los mismos IDs y el relay descarta repetidos.
- 2026-10-14, M8c, §1: cada línea ocupa como mucho 1.000 bytes con el salto (ver «Tope por línea»); `arbol` recorta sus listas y lleva `"truncado": true` si no caben; `arbol` no se repite si el árbol de ese actor no ha cambiado.
- 2026-10-14, M8c, §2: quien lee los JSONL salta las líneas que no son JSON válido sin cortar la lectura, conserva la numeración de las demás y las cuenta (en M8d, discrepancia `linea_corrupta`).
- 2026-10-14, M8c, §1: `ts` con microsegundos (`2026-11-25T18:02:11.123456Z`), de `$EPOCHREALTIME` con `TZ=UTC0`, sin procesos. Varios hooks caen en el mismo segundo: el orden de los eventos es (`ts`, nº de línea). Sigue siendo `date-time` del esquema (RFC 3339 admite fracciones), así que el esquema no cambia.
- 2026-10-14, M8c, §1 y §2: la compuerta marca con `"tope": true` (y `datos.tope`) el tercer intento, que deja pasar sin evidencias.
- 2026-10-14, M8d, [estado.schema.json](estado.schema.json): `linea_corrupta` en el enum de `discrepancias` (las líneas rotas de los JSONL que cuenta cada demonio, §2). Solo añade un valor.
- 2026-10-15, M8e, [estado.schema.json](estado.schema.json): `dependencias_distintas` (las nativas de GitHub no coinciden con la línea «Depende de:» del cuerpo; manda la nativa, ADR-0001) e `issue_duplicado` (dos issues del equipo con el mismo ID; manda el de número menor) en el enum de `discrepancias`. Solo añade valores.
- 2026-10-15, M8e, §4: el sondeo de git, implementado en lo que exige M8e (`commit` y `push` de fuente git; abajo). Lo demás de esa viñeta queda aplazado.
- 2026-10-15, M8e, §2 y §4: la `tarea` de un `commit` de git es el ID con que **empieza** su asunto, no cualquier ID que cite. En vivo, el commit del plan «Ajuste del plan: T14 …» de A contaba como trabajo de T14 y salía `actividad_ajena`. Los merges no salen como `commit` (traer `origin` no es trabajo de una tarea).
- 2026-10-15, M8f, §3: `GET /v1/vista` (con ETag, la misma versión que `/v1/estado`) y el evento SSE `vista` detrás de cada `estado`, con el mismo `id`: `{servido_en, vista}`, la vista de `hkos/proyeccion.py` y la hora del relay al servirla. La web pinta esa vista, no calcula estados (constitución IV), y calcula «hace X» con la hora del relay y no con la del dispositivo. Solo añade: quien solo lee `estado` ignora el evento nuevo.
- 2026-10-15, M8f, §4: el demonio recibe el estado sondeando `GET /v1/estado` con `If-None-Match` cada 3 s (la alternativa de P15 al SSE) y deja `estado.json` y `estado-equipo.md` en `<git común>/hackathon/os/`. `agente.vivo` lleva una segunda línea con la hora (época) que renueva cada 15 s: `delta.sh` da por muerto un demonio cuya hora tiene más de 60 s aunque el fichero siga ahí.
- 2026-10-15, M8f, [estado.schema.json](estado.schema.json): `novedades` se rellena (el relay lee `.hackathon/decisiones.md` y `.hackathon/criterios.md` de `origin/main` de su clon, con `git fetch` cada 60 s). El esquema no cambia. Si el fetch falla más de `umbral_viejo_s`, `fuentes.git` = `sin fetch` con la hora del último bueno; antes, en silencio.
- 2026-10-15, M8f, regla 9 (`diseno.md` §5.1): un `edicion` o `arbol` cuyas rutas están todas bajo `.hackathon/` o `.claude/worktrees/` no va a `sin_tarea` (el estado del orquestador y los worktrees de los workers, que `arbol` de la copia principal ve como cambios: ruido de M8e).
- 2026-10-15, M8g, §1 y §2: la línea `arbol` lleva `contratos` (hasta 5 títulos `##` de los bloques de `docs/contratos.md` que tocan los cambios, de 80 caracteres como mucho) si `docs/contratos.md` está cambiado; `arbol.sh` lo saca con un `git diff -U0` contra la base, solo en ese caso, y va en la firma del árbol (tocar otro bloque del fichero ya cambiado es un `arbol` nuevo). `normaliza.py` lo pasa a `datos.contratos` (`datos` es abierto: el esquema no cambia). Para el nivel 3 (R-21).
- 2026-10-15, M8g, §2 y §3: `reserva` y `liberacion` los crea el relay desde `POST /v1/reservas` y `DELETE /v1/reservas/{id}` (el MCP llama a esa API); se guardan en `relay/eventos.jsonl` como los demás eventos y el `ts` es la hora del relay, así que caducan con un solo reloj. [estado.schema.json](estado.schema.json): `id` opcional en cada reserva (lo usan `liberar` y el aviso de una vez por sesión). Solo añade.
- 2026-10-15, M8g, §4: publicación del trabajo en curso (decisiones del usuario, ADR-0007 con nota): el padre del commit es la merge-base con `origin/main`, no HEAD; exclusiones ampliadas y aplicadas como pathspecs del propio `git add`; lo excluido que ya estaba vuelve a su versión de la base; no publica con el repo de GitHub público (salvo `publicar_wip: sí, incluso público`) ni si no sabe si lo es, ni con un merge, rebase o cherry-pick a medias; git sin diálogos de credenciales y `--no-verify` en ese push; línea `wip:` en `/salud`. Detalle en §4.
- 2026-10-15, M8g, §6: sección `## Reservas` (entre «Colisiones que te afectan» y «Novedades»; las reservas vigentes de las demás personas) y firma `reservas:` en la cabecera, sin horas (renovar una reserva no es un cambio). Las líneas `>` del principio pueden traer avisos del propio demonio que no están en `estado.json` (por qué no publica el trabajo en curso).
- 2026-10-15, M8g, §7: `reservas.tsv`, `wip.index`, `wip.pathspecs`, `wip.json` y `entregado/<session_id>-<agent_id o «sesion»>.reservas` en `<git común>/hackathon/os/`; `refs/hackathon/relay-wip/*` en el clon del relay.
- 2026-10-15, M8h, §0, §3, §6 y §7 (modo sin GitHub, K-80; decisiones del usuario):
  - **§0:** clave nueva `github: sí|no` (por defecto, `sí`); el modo se activa solo de forma explícita;
  - **§3:** con `github: no`, el relay no sondea GitHub. Toma las tareas de `.hackathon/plan.md` de `origin/main` de su clon (`compilar.SondeoPlan`, con el fetch de las novedades): sin issues, así que sin `reclamada` ni `cerrada`. `fuentes.github` = `{valor: "no", fuente: "git", observado_en: <hora del commit del plan>}`; la fuente de `pendiente` pasa a ser `git`. Un plan mal formado no borra las tareas: se queda el último bueno y se avisa una vez;
  - **§6:** `github=no` en la cabecera y la línea `> Sin GitHub: las tareas salen de plan.md de main (HH:MM); sin asignar ni cerrar issues.`; «no» nunca está viejo;
  - **§7:** `<git común>/hackathon/yo-fijo` (la persona declarada con `hk-os unir --persona`, que manda sobre gh en `hk_yo` y en los eventos), `yo-fijo.comprobado` y `<git común>/hackathon/os/remoto/equipo.git`;
  - **§9, nueva:** el remoto del equipo.
  - Con GitHub configurado y caído, todo sigue como antes: la última instantánea, marcada como vieja. Los esquemas no cambian.
- 2026-10-15, M8h, §3: la hora de un sondeo bueno de GitHub sin cambios no saca versión nueva (ni SSE) hasta que avanza un tercio de `umbral_viejo_s` respecto de la publicada (Pendiente de M8f: la web decía «actualizado» cada 30 s sin cambios). Así nada se ve «viejo» sin serlo.
- 2026-10-15, M8h, §4: `hk-os unir <url> <token> [--persona <usuario>] [--remoto <url>]` imprime el desfase del reloj frente a la cabecera `Date` del relay. `--remoto` pone `origin` = remoto del equipo (el anterior pasa a ser `github`) con el token en `http.<url>.extraHeader`, nunca en la URL, y `credential.<url>.helper` vacío; sin `--remoto`, deshace lo que hizo uno anterior (`hkos.remoto` en la configuración del clon). `hk-os recoger` deja un zip con `<git común>/hackathon/os/` sin `token`, `relay.url`, `wip.index`, `wip.pathspecs` ni `remoto/`, más el log de git y el desfase; nunca la configuración de git. El git del demonio y del publicador, sin askpass (`GIT_ASKPASS` vacío): con un `401`, git se quedaba esperando al askpass heredado (el de VS Code).
- 2026-10-15, M8h, §4 y §6: `hk-os unir` escribe ya `estado.json`, `estado-equipo.md` y `reservas.tsv` con el estado que acaba de pedir al relay, con el mismo código que el demonio. La persona sale de `--persona`, de `yo-fijo`, de la caché de `hk_yo` (si solo hay una) o de `gh api user`; si no se sabe, no escribe nada. Motivo (prueba interactiva de M8h): en la primera sesión tras unirse, el demonio lo lanza el propio SessionStart y aún no ha escrito el md, así que esa sesión no recibía el bloque «Estado del equipo».
- 2026-10-15, M8h, §0 y hooks: con bash < 5 (el 3.2 de macOS), `os_activo` falla y el OS se queda apagado; `arranque.sh` lo avisa una vez por sesión si `os.md` lo pide.
- 2026-10-16, tras M8h fase 1, §2 y §4 (Pendiente de M8e y M8g; `datos` es abierto: el esquema no cambia):
  - **§2:** el `arbol` normalizado lleva `datos.solo_diff` = cuántas de sus últimas rutas salen solo del `diff` (con commit, aún sin subir). De un `arbol`, a `sin_tarea` solo va lo demás (`diseno.md` §5.1, regla 9);
  - **§4:** cuando cambia `origin/main`, tras el `push`, el demonio emite el `arbol` de la copia principal (actor `demonio`, `worktree` vacío, fuente `git`, ID `git-<persona>-arbol-<sha12>-<hash8>`, `datos.base` y `solo_diff`, hasta 200 rutas con `truncado`), sin `contratos` y solo si cambió desde el último que emitió. No se atribuye a ninguna tarea: es para las colisiones. El `arbol` por worktree sigue aplazado.
- 2026-10-17, M9a (K-91; ADR-0009, ADR-0010 y ADR-0011). Sin subir `v`: todo añade campos, tipos, valores de enum o rutas, y con `web_nueva: no` nada de esto se produce. Lo cubren:
  - **§0:** la clave `web_nueva: no|sí`;
  - **§1:** la línea cruda `prueba` (`scripts/os/prueba.sh`);
  - **§2:** los eventos `prueba`, `servicio.estado` y `reclamo` con fuente `web`;
  - **§3:** el evento SSE `eventos` y `servicios` en `estado.json`;
  - **§4:** la web del demonio, sus rutas de datos y de acción, la seguridad, la suscripción SSE y la salud de los servicios;
  - **§5:** una nota sobre `reclamar`;
  - **§6:** la sección `## Servicios` y la firma `servicios:`;
  - **§7:** los ficheros nuevos. `hk-os recoger` deja fuera `web.token` y `nota.index`, como el token del relay;
  - **§10, nueva:** el formato de `servicios.md`;
  - los esquemas: en [eventos.schema.json](eventos.schema.json), los tipos `prueba` y `servicio.estado`, las fuentes `web` y `demonio` y los campos de `datos`; en [estado.schema.json](estado.schema.json), `servicios` (opcional) y las fuentes `web` y `demonio`.
  - Al aprobar (decisiones del usuario):
    - las propuestas van en dos tablas, «Propuestas de servicios» y «Propuestas de conexiones», con el mismo formato que la suya más Autor y Hora (§10);
    - «sin conexión» de la web salta tras `max(umbral_viejo_s, 40 s)`: al menos el doble del `ping` de 20 s (§4);
    - `reclamada` desde la web, con la fuente `web` y declarada, en K-93 (§2).
  - En K-92, tras congelar (aclaraciones del usuario, sin cambiar el esquema):
    - la columna Dueño de un servicio puede ir sin valor mientras no hay reparto. Entonces manda `autoridad.md` y no hay desajuste (§10);
    - una carpeta sin dueño en `autoridad.md`:
      - **antes del reparto** (sin `autoridad.md` o sin ninguna persona en él), «sin dueño» y sin desajuste; la fila solo se confirma si viene de `/hack-scaffold`, y lo mismo una conexión con un extremo sin dueño;
      - **con el reparto hecho**, desajuste `dueno_distinto` y sin confirmar.
  - En K-97, tras congelar (solo añade):
    - en [estado.schema.json](estado.schema.json), `duenos` (opcional) en cada propuesta: quién la confirma, para la sección `## Servicios` de cada persona;
    - en la vista, cada tarjeta lleva `estado_declarado: true` si su estado es declarado (`reclamada` desde la web o el MCP). El md lo dice («· declarado») y entra en la firma de «Tu trabajo» solo cuando es verdad, así que las firmas de antes no cambian.
- 2026-10-18, PR #13 (decisión del usuario; issue #2, hallazgo 12), §2 y [eventos.schema.json](eventos.schema.json): patrón `^[A-Za-z0-9._:-]{1,200}$` para el `id`, que sale en el SSE `eventos`. Restringe, pero todo lo que producen hoy los hooks, el demonio, la web y el relay ya lo cumple (comprobado con `hkos/pruebas`, `prueba_hooks.py` e `igualdad.py`).
- 2026-10-19, M10 (K-101; ADR-0012 y ADR-0013, decisiones del usuario en el PR #42 y el issue #41). Sin subir `v`: todo añade campos opcionales, `$defs` o secciones, y con `vista_jurado: no` y `ruta_critica: no` nada de esto se produce. Lo cubren:
  - **§11, nueva:** los interruptores `vista_jurado:` y `ruta_critica:` (claves de §0), lo que lee el relay, los bloques `jurado` y `ruta` de la vista, las herramientas `jurado` y `ruta` del MCP (de §5) y una vista de ejemplo;
  - **§3:** el relay lee `criterios.md`, `plan.md`, `pitch.md` y `equipo.md` y reconstruye la historia de cada tarea;
  - **§4:** la vista del demonio y de su web lleva los bloques; la web los pinta y no calcula nada;
  - **§6:** la sección `## Jurado y ruta` (una línea por vista) y las firmas `jurado:` y `ruta:`;
  - [estado.schema.json](estado.schema.json): `jurado` y `ruta` (opcionales); en `tareas[]`, `hasta` (con el motivo de «sin plazo»), `franja`, `orden_plan`, `historia`, `criterios` y `conexiones` (opcionales), y `evidencia` se rellena; los `$defs` `plazo`, `franja`, `historia`, `hora_declarada`, `descanso`, `nota` (con su `clave`), `cita`, `fuerza`, `vista_jurado` y `vista_ruta`. Todo dato es `{valor, fuente, observado_en}` (o lleva esos tres campos) y `viejo` en la vista. Lo validan el validador de M8b (`hkos/esquema.py`) y jsonschema.
- 2026-10-19, M10, issue #46 (las «Decisiones que faltan» de la revisión de los contratos de M10, decididas por el usuario; ajustes en ADR-0012 y ADR-0013). Sin subir `v`. Lo que cambia de forma se escribe aquí solo con la forma nueva; el esquema admite aún la anterior, con su `description` «TRANSITORIO (issue #46)», hasta que el código se adapte (K-105). Lo cubren:
  - **§11.4 y [estado.schema.json](estado.schema.json):** una tarea abierta sin plazo no quita la estimación: sale en `sin_plazo[]` y el resto se estima (ajuste 1 de ADR-0013);
  - **§11.3 y el esquema:** «sin cubrir» es todo lo no cubierto, sin las corregidas; `declarada` se parte en `planificada` y `en_curso`, y `cuenta` lo dice (ajuste 2 de ADR-0012);
  - **§11.4 y el esquema:** `ruta.riesgos[]`, las tareas que según la estimación acaban después de la entrega; sin hora central, previsión por hito ni «fiabilidad» (ajuste 3 de ADR-0013);
  - **§11.2, §11.4 y el esquema:** los descansos se leen de la tabla `| Turno | Quién |` y de las líneas `- quién: turno`, con varias personas por turno (`descanso.personas`) y día en el final, y se restan de la franja al medir el ritmo (ajuste 4 de ADR-0013);
  - **§11.2, §11.4 y el esquema:** «dos horas» en `- Entrega:` son dos horas distintas sin contar la zona; manda la primera y la otra va a `otras_entregas`, sin quitar la estimación. Valen «dom 20 sep 09:30» y «dom 20 sep 2026 10:00», y sin zona se hereda la de `Inicio:`. Solo es una entrega la fila de Hitos «Entrega» o «Entrega final…»; una nota dato sale como «(criterios.md, nota de HH:MM)», sin su texto (ajuste 5 de ADR-0013);
  - **§11.2, §11.3 y el esquema:** `tareas[].evidencia` = `{valor, tipo, fuente, observado_en}`, el último sha publicado con su hora; una tarea `parada` o `no_cerrada` tras `hecha_en` sigue contando como hecha (ajuste 6 de ADR-0012);
- 2026-10-14, M8d, §4 y §7: `<git común>/hackathon/os/agente.vivo` (el puerto, mientras el demonio escucha) y `…/arranque.log` (una línea por `SessionStart`: qué hizo el arranque y cuántos ms). En Windows, conectar a un puerto local cerrado tarda ≈2 s, y sin `agente.vivo` el arranque no cabía en el segundo del criterio 6 de M8d.

Los estados de tarea son identificadores sin espacios (`en_curso`, `en_revision`, `no_cerrada`…); la web y el markdown muestran la etiqueta legible («en curso»).

## 0. Interruptor: `.hackathon/os.md`
Versionado, lo escribe una persona (o `hk-os iniciar`). Mismo estilo que `coordinacion.md`. Plantilla: `skills/hack-scaffold/templates/os.md`.

Los hooks lo leen en la **copia principal** del clon (la carpeta del git común), no en el worktree en que corren: los worktrees de los workers salen de `origin/main` y podrían no tenerlo. Activo = una línea `activa:` con `sí`, `si` o `yes`; se toleran BOM, UTF-16, `
` y un comentario `# …` detrás del valor. Sin `os.md` activo, todo hook del OS sale sin red ni escritura (R-01).

```
# Hackathon OS
activa: sí
relay: http://<ip-lan-o-tailnet>:7777
publicar_wip: no          # ADR-0007, nivel 2
github: sí                # no = modo sin GitHub: tareas de plan.md y remoto del equipo (§9; M8h)
repo_tareas:              # vacío = el repo de coordinacion.md
umbral_parada_min: 20
umbral_viejo_s: 300
datos_excluidos: data/, datos/   # ADR-0007: nunca se publican en refs/hackathon/wip/*
puerto_agente:            # vacío = 47100 + (cksum del git común) % 900 (ADR-0004)
apagado_min: 30           # el demonio sale tras este tiempo sin eventos ni sesiones
web_nueva: no             # sí = la web de trabajo de M9a, servida por el demonio de cada persona (§4, ADR-0010)
```

El token del relay **no** va aquí: va en `<git común>/hackathon/os/token` (fuera de git).

**`web_nueva:`** (M9a; por defecto, `no`; mismos valores que `activa:`), versionado y para todo el equipo. Cada pieza lo lee de su copia: el relay de la suya, cada demonio y cada hook de la principal de su clon. Una persona con un `os.md` sin actualizar se queda con lo de siempre. Con `no` (o sin la línea) no se produce nada de M9a, y todo queda como en M8h:
- el demonio no sirve web ni rutas de datos o de acción (`404`), no se suscribe al SSE del relay y no comprueba servicios;
- el relay no emite `eventos` ni calcula `servicios`;
- `prueba.sh` sale sin escribir.

La web clásica del relay (`GET /` del relay) se sirve siempre: es el respaldo.

## 1. Forma cruda (lo que escriben los hooks)
`emite.sh` añade una línea por evento a `<git común>/hackathon/os/eventos/<session_id>.jsonl`. El `session_id` es el de la sesión madre también en los subagentes (P4), así que un JSONL junta la sesión o el orquestador y sus workers, que se distinguen por `agent_id`.

- **Los JSONL nunca se reescriben ni se truncan**: solo se les añaden líneas, o se borra el fichero entero. El `id` de un evento normalizado depende del número de línea (§2).
- **Tope por línea: 1.000 bytes con el salto**, contados en bytes (`LC_ALL=C`), escritos con un solo `printf` en modo `O_APPEND`. Los hooks `async` de la sesión, el orquestador y los workers escriben a la vez en el mismo fichero. Si una línea no cabe, se escribe solo el sobre mínimo (`v`, `ts`, `persona`, `tipo`, `session_id`, `agent_id`) con `"truncado":true`; `arbol` antes recorta sus listas.
- **Es un límite medido, no una garantía.** En Linux, una escritura `O_APPEND` de menos de 4 KB es atómica. En Windows con Git Bash (MSYS), el `printf` de bash escribe en trozos de 1 KB, y las líneas más largas de hooks simultáneos se mezclan. Medido el 2026-10-14 (procesos bash a la vez sobre el mismo fichero):

  | Líneas | Rondas × procesos | Enteras |
  |---|---|---|
  | 500, 1.000 y 1.020 bytes | 10 × 20 cada una | 200/200 cada una |
  | 1.030, 2.000 y 3.500 bytes | 10 × 20 cada una | 176, 188 y 175 de 200 |
  | `emite.sh` real, ~3,2 KB | 5 × 20 | 81/100 |
  | 100–1.000 bytes mezcladas | 50 × 20 | 1.000/1.000 |

  Por eso quien lee los JSONL (`normaliza.py` y el demonio) tolera líneas rotas: las salta sin cortar la lectura, conserva la numeración de las demás y las cuenta (§2).
- **Un clon, una persona**: el git común es de una sola persona (`diseno.md` §3).

```json
{"v":1,"ts":"2026-11-25T18:02:11.123456Z","persona":"mveradc","tipo":"PostToolUse","session_id":"…","agent_id":"a17759f71a1625d5c","agent_type":"hackathon-kit:worker","cwd":"C:\…\.claude\worktrees\agent-a17759f71a1625d5c","tool_name":"Edit","tool_use_id":"toolu_…","ruta":"C:\…\src\a.py"}
```

**Lista blanca** (ADR-0004): el emisor no guarda la entrada del hook, solo estos campos. Un campo que no viene se omite.

| Campo | De dónde | Cuándo |
|---|---|---|
| `v`, `ts`, `persona`, `tipo` | Sobre: `ts` en UTC con microsegundos (`$EPOCHREALTIME` y `TZ=UTC0 printf '%(…)T'`); `persona` de la caché de `hk_yo` (`""` si no existe: lo resuelve el demonio); `tipo` = `hook_event_name` | Siempre |
| `session_id`, `cwd` | Entrada | Siempre |
| `agent_id`, `agent_type` | Entrada | Si vienen (subagentes; `agent_type` también en sesiones `--agent`) |
| `source` | Entrada | `SessionStart` (`startup`, `resume`, `clear`, `compact`: la compactación reinicia el tope de R-25) |
| `tool_name`, `tool_use_id` | Entrada | Eventos de herramienta |
| `ruta` | `tool_input.file_path` o `tool_input.notebook_path` | Edit, Write, MultiEdit, NotebookEdit |
| `git` | `tool_input.command`, **solo** si contiene `git` seguido de `update-ref`, `merge --ff-only`, `push` o `commit` (también con `git -C <ruta>`); recortado a 200 caracteres | Bash y PowerShell |
| `subagent_type` | `tool_input.subagent_type` | PreToolUse y PostToolUse de `Agent` (worker o revisor) |
| `id`, `base` | Del `tool_input.prompt`, solo las líneas `ID: (T[0-9]{2,3})` y `Base: ([0-9a-f]{7,40})` | PreToolUse de `Agent` |
| `transcript_path` | Entrada (el transcript de la sesión madre) | `SubagentStart`: el demonio lee la primera línea del del worker (§2) |
| `veredicto`, `fusion` | De `last_assistant_message`, solo `Veredicto: (APROBADO\|CAMBIOS)` y `Fusión: ([0-9a-f]{7,40})` (la «ó» puede venir como UTF-8 o como `\u00f3`) | `SubagentStop` con `agent_type` revisor |

Reglas del emisor:
- Solo builtins de bash, con el estilo de `valor()` de `scripts/orquestador/comun.sh` (regex sobre la entrada; una clave escrita dentro de una cadena va escapada, `\"clave\"`, y no coincide).
- Los valores de texto se copian **tal como vienen escapados** en la entrada, sin desescapar, así que la línea sigue siendo JSON válido sin volver a escaparla. Al recortar `git` a 200 caracteres, se quita del final cualquier secuencia de escape incompleta: una `\` suelta (un número impar de barras al final) o un `\u` seguido de menos de 4 dígitos hexadecimales.
- Las rutas van **absolutas y como vienen** (en Windows, con `\`). Las normaliza el demonio a relativas con `/` (con el `cwd` y `git rev-parse --show-toplevel`).
- Nada de `tool_response`, `content`, `old_string`, `new_string`, `prompt` ni `last_assistant_message` completos.
- Solo busca en los primeros 16 KB de la entrada (el sobre y `tool_input` van delante; `tool_response` se descarta) y, para `tool_use_id`, en los últimos 400 caracteres. Lee la entrada hasta el final con `read -N` en bloques: en Windows, `read -d ''` la lee byte a byte (534 ms con 226 KB) y `/dev/stdin` no existe con la tubería de Claude Code. Un campo que caiga más allá de los 16 KB (un `prompt` con `ID:` lejos del principio) se omite.

Otros productores de forma cruda:
- `arbol.sh` (`PostToolBatch`, `Stop`, `SubagentStop`) escribe `{"v":1,"ts":…,"persona":…,"tipo":"arbol","session_id":…,"agent_id":…,"cwd":"…","base":"<sha de origin/main>","porcelain":["M src/a.py","?? b.txt"],"diff":["src/a.py","src/c.py"]}`. Solo si el árbol de ese actor (`agent_id`, o la sesión) ha cambiado desde su último `arbol`. Si las listas no caben en la línea, se recortan y la línea lleva `"truncado":true`.
- `compuerta.sh` escribe `{"v":1,…,"tipo":"compuerta","resultado":"ok|ko","agent_id":"…","motivos":[…]}`, y `"tope":true` en el tercer intento, que deja pasar sin evidencias (es `ko`).
- `prueba.sh` (M9a; `PostToolUse` y `PostToolUseFailure` con `matcher: Bash`, `async`, solo con el OS activo y `web_nueva: sí`) escribe `{"v":1,"ts":…,"persona":…,"tipo":"prueba","session_id":…,"agent_id":…,"cwd":"…","comando_sha":"<12 hex>","resultado":"pasa|falla","codigo":3}`, **solo** si el comando es exactamente la Prueba de una conexión de la sección `## Conexiones` de `.hackathon/servicios.md` de la copia principal (§10).
  - **Comparación:** el comando del hook se compara tal como viene escapado en la entrada, sin espacios a los extremos. La Prueba del fichero se compara sin espacios a los extremos ni las comillas invertidas que la rodean, y escapada como JSON (`\` → `\\`, `"` → `\"`).
  - **Resultado:** `PostToolUse` → `pasa`; `PostToolUseFailure` → `falla`, con `codigo` sacado de `error` = `Exit code N` (sin él, se omite; con `is_interrupt: true`, no escribe nada). Lo comprobó el Paso 0 de M9a: entradas en `evals/coordinacion/entradas/m9a-bash/`.
  - **Huella:** `comando_sha` son los 12 primeros hex del sha256 de la Prueba tal como está en el fichero, sin espacios a los extremos ni comillas invertidas, en UTF-8. Solo se calcula si hay coincidencia (`sha256sum`, un proceso). **Nunca se escribe el comando**: el relay lo empareja por la huella con su copia de `origin/main` (§3).
  - **Como `JSON.parse`** (tras congelar, 2026-10-18, PR #28, issue #23, hallazgo 19: con `tool_input` como lista escribía «pasa», y con claves repetidas miraba la primera): con una Prueba encontrada, `descartar` recorre como JSON, token a token, los primeros 16 KB de la entrada y decide al final con la **última** aparición de cada clave; un `tool_input` o un `tool_response` repetido sustituye entero al anterior. No escribe nada si `tool_input` no es un objeto, si su último `command` (crudo y sin espacios a los extremos) no es esa Prueba, si `run_in_background` acaba en `true` (o `"true"`) o si `tool_response.backgroundTaskId` acaba con un valor que no es vacío, `null` ni `false`: en segundo plano, `PostToolUse` llega al arrancar el proceso y no dice si pasó. Si la entrada no cabe en esos 16 KB, `backgroundTaskId` se busca también al final.
  - Cualquier otro comando no deja nada.

## 2. Evento normalizado
Esquema: [eventos.schema.json](eventos.schema.json). Lo produce `hkos/normaliza.py`. El `id` es `<session_id>-<nº de línea del JSONL, desde 1>`. Una línea que no es JSON válido se salta sin cortar la lectura: las demás conservan su número de línea real y se lleva la cuenta de las rotas (en M8d sale en `/salud` y en `estado.json` como discrepancia `linea_corrupta`). Correspondencia con la forma cruda:

| Forma cruda | Evento normalizado |
|---|---|
| `SessionStart` | `sesion.inicio` |
| `SessionEnd` | `sesion.fin` |
| `PostToolUse` con `tool_name` Edit/Write/MultiEdit/NotebookEdit | `edicion`, `rutas` = `ruta`, relativa y con `/` |
| `arbol` | `arbol`, `rutas` = unión de `porcelain` y `diff` |
| `PreToolUse` `Agent` del orquestador con `subagent_type` worker | `encargo.lanzado`, `tarea` = `id`, `datos.base` = `base` |
| `SubagentStart` / `SubagentStop` worker | `worker.inicio` / `worker.fin`. `SubagentStart` no trae el prompt (P3): el demonio toma `ID:` y `Base:` de la primera línea del transcript del worker, `<carpeta de transcript_path>/<session_id>/subagents/agent-<agent_id>.jsonl`, y no lee nada más de él. Es un formato interno de Claude Code: si cambia, la tarea del worker queda sin asignar hasta su `fusion.creada` |
| `compuerta` | `compuerta.ok` / `compuerta.ko` con `datos.motivos` (y `datos.tope`) |
| `PostToolUse` Bash del orquestador con `git` = `git update-ref refs/hackathon/fusion/<T>` | `fusion.creada` (`tarea`, `datos.sha`) |
| `SubagentStop` revisor | `revision.veredicto` (`datos.veredicto` = `veredicto`, `datos.sha` = `fusion`) |
| `PostToolUse` Bash del orquestador con `git` = `git merge --ff-only <sha>` | `fusion.aprobada`, solo si el demonio confirma que `main` contiene el sha (la forma cruda no lleva la salida del comando) |
| `PostToolUse` Bash del orquestador `git update-ref -d refs/hackathon/fusion/<T>` sin aprobada previa | `fusion.descartada` |
| `PostToolUse` Bash `git push` / sondeo de `origin/main` | `push` (fuente `hook` o `git`). Con fuente `git`, `datos.sha` = punta nueva de `origin/main` y `datos.incluye` = shas de fusiones y de commits con ID de tarea que ya se alcanzan desde ella (los calcula el demonio con `merge-base --is-ancestor`) |
| Sondeo de git del demonio | `arbol`, `commit` (`tarea` si el mensaje cita un ID, `datos.sha` y `datos.alcanzable` si ya se alcanza desde `origin/main`), `push`, `fusion.*` de reconciliación (fuente `git`) |
| MCP `reclamar`, `reservar`, `liberar` | `reclamo`, `reserva`, `liberacion` (fuente `mcp`) |
| `prueba` (M9a) | `prueba` (fuente `hook`), `datos` = `{comando_sha, resultado, codigo?}` |
| Salud de los servicios del demonio (M9a, §4) | `servicio.estado` (fuente `demonio`, actor `demonio`), `datos` = `{servicio, clave, puerto, escucha, salud}`. `salud` es el código HTTP de `GET <Salud>`, o `null` sin Salud o sin respuesta. ID `demonio-<persona>-servicio-<clave>-<época en ms>` |
| Reclamar desde la web (M9a, §4) | `reclamo` (fuente `web`, actor `humano`, `tarea`). ID `web-<persona>-reclamo-<tarea>-<época en ms>`. El motor (`hkos/estados.py`, regla 10) lo trata como el `reclamo` del MCP: estado `reclamada` con la fuente del evento (`web`) y `declarado: true`. Hoy pone `mcp` fijo y no marca `declarado`; se cambia en K-93. Si GitHub ya trae la asignación y es anterior, manda esa (fuente `github`, derivado) |

Los eventos de un worker (`edicion`, `worker.fin`…) llevan la tarea de su encargo, la de su `worker.inicio` con el mismo `agent_id`. Salida esperada con las entradas reales: `evals/coordinacion/entradas/normalizadas.json`.

**Forma del `id`** (tras congelar, 2026-10-18, decisión del usuario en el PR #13, issue #2, hallazgo 12): `^[A-Za-z0-9._:-]{1,200}$` en [eventos.schema.json](eventos.schema.json). Lo cumplen todos los productores: `<session_id>-<n>[.<k>]` de `normaliza.py` (el hook solo acepta un `session_id` `^[A-Za-z0-9_-]+$`; el de Claude Code es un UUID), los `git-<persona>-…` y `demonio-<persona>-servicio-…` del demonio, el `web-<persona>-reclamo-…` de Reclamar y los `reserva-…`, `liberacion-…` y `latido-…` del relay. Un evento con otro `id` no pasa el esquema: el demonio no lo envía (lo cuenta como inválido) y el relay responde `400`. Así el `id` que sale en el SSE `eventos` (§3) no puede llevar texto arbitrario (rutas, texto de un issue); la tarea y la clave de servicio sí siguen en él.

Regla: si un evento de hook y uno de git dicen cosas distintas, gana git, y la discrepancia se registra en `discrepancias` de `estado.json`, agrupada por (tipo, tarea, persona) con contador y primera y última vez.

Atribución (paso previo al motor, `diseno.md` §5): un evento sin `tarea` (`edicion`, `arbol`) cuenta para la tarea de su persona solo si esa persona tiene exactamente una tarea `reclamada`, `en_curso` o `parada`; con varias, no cuenta y queda en `discrepancias`; con ninguna, va a `sin_tarea`. El mapeo por carpetas queda para M8e.

## 3. API del relay
Base: `relay:` de `os.md`. Todas las peticiones llevan `Authorization: Bearer <token>`. JSON en UTF-8.

| Método y ruta | Qué hace | Respuesta |
|---|---|---|
| `POST /v1/eventos` | Lote de eventos normalizados (≤ 200), `{"eventos":[…]}`. Idempotente por `id`. | `{"aceptados":n,"repetidos":m}` |
| `POST /v1/latido` | `{persona, actores:[{papel,sesion,agente,worktree,tarea,ficheros,ultima_senal}], lineas_corruptas?}`. Cada 15 s por demonio. | `204` |
| `GET /v1/estado` | Último `estado.json`. Admite `If-None-Match`. | `200` + `ETag`, o `304` |
| `GET /v1/stream` | SSE. Evento `estado` con el `estado.json` completo cuando cambia y, detrás, `vista` (desde M8f) con el mismo `id`; `ping` cada 20 s. | `text/event-stream` |
| `POST /v1/reservas` | `{persona, actor?, rutas, ttl_s, modo}` (M8g). `persona`, de la tabla de `coordinacion.md`; `rutas`, de 1 a 50, relativas a la raíz del repo con `/` (una carpeta acaba en `/`; nada absoluto ni con `..`); `ttl_s` de 30 a 7200 (900 por defecto); `modo` `compartida` (por defecto) o `exclusiva`, que en la v1 solo cambia la etiqueta del aviso. Crea el evento `reserva` con la hora del relay. | `{"id":…,"hasta":…}`; `400` si algo no vale |
| `DELETE /v1/reservas/{id}?persona=<usuario>` | Libera (evento `liberacion`). Solo quien reservó. (M8g.) | `204`, o `404` si no existe o no es suya |
| `GET /v1/vista` | La vista de `hkos/proyeccion.py` (columnas, colisiones, personas, novedades, sin tarea), `{servido_en, vista}`. Admite `If-None-Match` (misma versión que `/v1/estado`). (M8f.) | `200` + `ETag`, o `304` |
| `GET /` | Web de solo lectura (`hkos/web/index.html`, HTML y JS en un fichero, sin datos). **Sin token**: el token va en el fragmento (`/#t=<token>`), que el navegador no envía; la página pide con él `/v1/stream` (con `fetch`, porque `EventSource` no admite cabeceras) y, si el stream se corta, `/v1/vista` cada 3 s. (M8f.) | HTML |

Errores: `401` sin token o con uno que no es el del equipo; `400` con `{"error":…,"campo":…,"indice":…}` si un evento del lote no valida contra [eventos.schema.json](eventos.schema.json) (o el cuerpo no es JSON, o el lote pasa de 200); nunca `500` por un evento malo (se descarta y se registra).

Reglas (fijadas al congelar, M8d):
- **Lote entero o nada.** Si un evento del lote no valida, el relay responde `400` con el `indice` del primero que falla y no guarda ninguno. El demonio valida cada evento con el mismo esquema antes de enviarlo y aparta los que no validan (los cuenta en `/salud`): un evento malo no bloquea su cola.
- **Persistencia.** Cada evento nuevo se añade a `relay/eventos.jsonl` y se vuelca a disco antes de responder. Al arrancar, el relay lo vuelve a leer (saltando líneas rotas): los repetidos se reconocen también tras reiniciar. Los latidos no se guardan.
- **Token.** Se genera la primera vez y se guarda en `relay/token`; un reinicio reutiliza el mismo, para que los demonios sigan entrando sin volver a unirse. Se compara en tiempo constante.
  - **Sin «-» delante** (tras congelar, 2026-10-18, PR #25 y PR #28: `token_urlsafe` da uno así de cada 64, y argparse lo tomaba por una opción en `hk-os unir <url> <token>`; nota del PR #24). `Relay._token` repite `secrets.token_urlsafe(24)` hasta que no empiece por «-». Un token guardado de antes no se cambia; si empieza por «-», la orden que imprime el relay para copiar (`relay.orden_unir`) lleva `--` delante del token. `hk-os unir` acepta el token empiece o no por «-», con o sin `--` delante (`cli._args_unir`: lo que no sea `--persona`, `--remoto`, `-h` o `--help` es posicional). Si el token lo crea antes `hk-os remoto` (§9, `remoto.token_del_equipo`), sale sin ese bucle y puede empezar por «-».
- **Dónde escucha.** En `127.0.0.1`, en una IP privada (10/8, 172.16/12, 192.168/16) o en una de Tailscale (100.64/10). Nunca en `0.0.0.0` ni en una IP pública: si no encuentra una válida, no arranca y lo dice. Sin cabeceras CORS.
- **Latido.** Cada latido sustituye al anterior de esa persona: es la lista completa de sus actores abiertos. Cada actor cuenta como un evento `latido` con `ts` = su `ultima_senal` (la hora de su última señal que vio el demonio, no la de llegada): así el latido no alarga la presencia más allá de los 90 s de R-18.
- **Estado.** Lo calcula `hkos/modelo.py` (el mismo de M8b, no una copia) con los eventos recibidos, los actores del último latido de cada persona y el equipo de `coordinacion.md` de la copia del relay. Las tareas y los issues llegan en M8e; hasta entonces, la lista de tareas va vacía. Las líneas rotas que declara cada demonio en su latido van a `discrepancias` como `linea_corrupta`.
- **Versión.** El relay recalcula tras cada lote (como mucho 4 veces por segundo) y cada 5 s, para que la presencia caduque sola. Solo hay versión nueva si el estado cambia sin contar `generado_en`. El `ETag` es esa versión, y cada mensaje SSE lleva `id: <versión>`. Al conectarse, un cliente SSE recibe primero el estado actual.
- **Historia real** (tras congelar, 2026-10-17, PR #21, y 2026-10-18, PR #28: un `git replace --graft` hacía que un commit sin padres pareciera crear `servicios.md` y añadir todas sus filas, issue #18, hallazgo 6). El relay lee git sin objetos de reemplazo: `git --no-replace-objects` en `relay._git` y en `Novedades._texto`, y `hk-os relay` arranca con `GIT_NO_REPLACE_OBJECTS=1` (`cli.main`), así que también los git de `compilar.py` y `colisiones_merge.py` que corren en su proceso. Si existe el fichero de injertos (`git rev-parse --git-path info/grafts`), el clon cuenta como superficial con bordes desconocidos (`Novedades._bordes` da `None`, §10): ninguna fila es de `/hack-scaffold` y no cuenta ninguna versión.

TTL: actor sin latido en 90 s → `activo: false` (R-18). Reserva vencida → se borra.

**M9a, solo con `web_nueva: sí` en el `os.md` del relay** (ADR-0009, ADR-0011):
- **SSE `eventos`.** Tras guardar un lote (`POST /v1/eventos` o una reserva), el relay manda a cada cliente de `/v1/stream` un `event: eventos` con `data: {"eventos":[…]}`. No va ligado a la versión ni lleva `id:`. Cada elemento sigue una **lista blanca**: `{id, tipo, persona, papel, ts}`, sin rutas, `datos` ni tarea. Los latidos no son eventos y no salen. Cuando el sondeo de GitHub trae un cambio que saca versión nueva, sale un elemento `{id: "github-<versión>", tipo: "github.sondeo", persona: null, papel: null, ts}`.
  - Un cliente que se conecta no recibe los anteriores: un paquete solo anima lo que llega mientras se mira (ADR-0009).
  - Se emiten hasta 200 por mensaje; si se juntan más, solo los 200 últimos, con `"recortados": n`.
  - Quien solo lee `estado` y `vista` (la web clásica, `carga.py`) ignora el evento nuevo.
- **`servicios` en `estado.json`.** Se calcula en el mismo bucle que las novedades y los contratos (tras el `git fetch` de cada 60 s y, además, a los ≤ 2 s de recibir un push de un demonio; tras congelar, 2026-10-18, K-99), a partir de:
  - `.hackathon/servicios.md` de `origin/main` del clon del relay (formato en §10), su `git log -p` (hasta 200 commits) y el commit que lo creó;
  - `.hackathon/autoridad.md` (carpetas de cada dueño, con el mismo lector que `hkos/contratos.py`) y los títulos `##` de `docs/contratos.md`;
  - `git ls-tree -r --name-only origin/main` y las rutas del último `arbol` de cada actor;
  - los eventos `commit` (sha → persona), `servicio.estado` (el último por `clave`) y `prueba` (el último por `comando_sha`) del registro.

  Las reglas de confirmación y de desajustes son las de ADR-0011; el esquema, [estado.schema.json](estado.schema.json). Sin `servicios.md` en `origin/main`, `servicios` no aparece. Si `servicios.md` de `origin/main` no se puede leer (una lectura de git que falla, no «el fichero ya no está»), el relay conserva el último `servicios` bueno, y pasados `umbral_viejo_s` sin una lectura buena lo dice en `fuentes.git`: `{"valor": "sin leer servicios", "fuente": "git", "observado_en": <hora de la última lectura buena>}`, como `sin fetch` (que manda si fallan los dos). La vista lo marca `viejo`. (Tras congelar, 2026-10-18, decisión 15B del usuario en el PR #13; PR #34: `Novedades.sondear`, `servicios_ok`, `servicios_fallando` y `Novedades.fuente`. Sin ninguna lectura buena, el plazo cuenta desde el arranque, como el del fetch. El esquema no cambia: `fuentes.git` es un `dato` con `valor` libre.)

  **Último bueno** (tras congelar, 2026-10-17, PR #21, issue #18, hallazgo 7): si `servicios.md` no se puede leer (falla la ref, `git ls-tree`, `git show` o `git log`), `Novedades._leer_servicios` devuelve `FALLO` y `Novedades.sondear` conserva el último `servicios` bueno; antes, el bloque desaparecía. Solo desaparece si el fichero ya no está (`ls-tree` sin salida). En el propio bloque, el último bueno **no** se marca como viejo: `fichero.observado_en` sigue siendo la hora del commit de `servicios.md` de esa lectura, no la de la lectura, y no queda aviso ni línea en el log. Lo dice `fuentes.git` (`sin leer servicios`, arriba; decisión 15B), y la vista y la web, no el md (`proyeccion.avisos` no saca línea `>` para `git`, como con `sin fetch`).

**M10, solo con `vista_jurado: sí` o `ruta_critica: sí` en el `os.md` del relay** (tras congelar, 2026-10-19, M10; ADR-0012, ADR-0013; detalle en §11.2):
- En el mismo bucle que las novedades y `servicios` (tras el fetch de cada 60 s y a los ≤ 2 s de un push), el relay lee de `origin/main` de su clon `.hackathon/criterios.md` (las notas, con su clave), `.hackathon/plan.md` (con `compilar.leer_plan`: etiquetas `(criterios: …)`, `Hasta`, franjas, orden, Hitos y Descansos), `.hackathon/pitch.md` (etiquetas) y `.hackathon/equipo.md` (Inicio, Entrega y zona horaria). Pone en `estado.json` `jurado`, `ruta` y los campos nuevos de las tareas, con la hora del commit de cada fichero. Si una lectura falla, conserva el último bueno y lo dice `fuentes.git`, como con `servicios`.
- Reconstruye la historia de transiciones de cada tarea (`tareas[].historia`) al arrancar, desde `relay/eventos.jsonl` y `relay/github.json`, y la lleva por incrementos tras cada lote. Rellena `tareas[].evidencia`.
- Con los dos interruptores apagados, nada de esto: `estado.json` sale byte a byte como antes.

Colisiones (M8g): las calcula `modelo.calcular` con `hkos/colisiones.py` y `hkos/contratos.py` (niveles 1 y 3, a partir de los eventos y de `docs/contratos.md` y `.hackathon/autoridad.md` de `origin/main` del clon del relay, leídos en el mismo bucle que las novedades). Con `publicar_wip: sí` en el `os.md` del relay y Git ≥ 2.38, un hilo trae `refs/hackathon/wip/*` a `refs/hackathon/relay-wip/*` de su clon cada 30 s y calcula el nivel 2 con `git merge-tree --write-tree --name-only` por pares de personas (`hkos/colisiones_merge.py`). Con un git más viejo, lo dice una vez al arrancar y sigue con los niveles 1 y 3. Un contrato sin dueño (o con más de una candidata) también se dice una vez. Definiciones en `diseno.md` §7.

## 4. Demonio local (`hk-os agente`)
- Sigue `<git común>/hackathon/os/eventos/*.jsonl` (posición por fichero en `<git común>/hackathon/os/posiciones.json`: bytes y nº de línea ya enviados). **No consume la última línea de un JSONL mientras no acabe en salto**: puede estar a medio escribir. Al arrancar vuelve a normalizar cada fichero desde la primera línea, para recuperar lo que el normalizador sabe (la tarea de cada worker por su `agent_id`), pero solo envía lo que va detrás de su posición.
- **Persona.** Una línea con `persona` vacía (el primer `SessionStart` de un clon, `api.md` §1) toma la persona del clon, que le pasa `sesion.sh` al lanzarlo (`--persona`, de `hk_yo`).
- **Envío.** Junta lo nuevo de todos los JSONL, lo ordena por (`ts`, `id`), valida cada evento contra [eventos.schema.json](eventos.schema.json) y lo manda en lotes de ≤ 200. Solo avanza la posición cuando el relay responde `200`. Si el relay no responde o da error, reintenta con espera creciente (hasta 30 s), sin perder la posición. Cada 15 s manda un latido con sus actores abiertos (los que tienen una señal en los últimos 90 s y no han cerrado) y la cuenta de líneas rotas.
- **Relay y token** de `<git común>/hackathon/os/relay.url` y `…/token`, que deja `hk-os unir` con permisos 0600 desde que se crean (un `.tmp` con `O_CREAT|O_EXCL` y `os.replace`; uno de antes pasa a 0600 al volver a unir; tras congelar, 2026-10-17, PR #19, issue #15, hallazgo 12) (la carpeta `…/os/relay/` es la del registro del relay, §7); si no está el primero, el `relay:` de `os.md`. Sin token, no envía nada (todo sigue en disco). `hk-os unir` escribe `relay.url` y `token` **los dos o ninguno** (tras congelar, 2026-10-18, PR #31, issue #27: si fallaba `token`, quedaba la URL nueva con el token viejo): primero los dos temporales y después los dos `os.replace` (`permisos.escribe_privados`, `cli.unir`). Si no se puede (en Windows, uno abierto por otro proceso más de 2 s, §7), sale con 1 y el mensaje «no he podido guardar relay.url y token…; se quedan como estaban», sin traceback: los dos quedan como estaban (o, si no existían, sin crear) y sin `.tmp`.
- Cada 15 s: `git worktree list --porcelain`; por worktree, `git status --porcelain` y `git diff --name-only <origin/main>...HEAD`; `git for-each-ref refs/hackathon/`; si hay `origin`, `git fetch --quiet` cada 60 s y `git merge-base --is-ancestor` de las fusiones aprobadas.
- **Implementado en M8e** (lo que exigen sus criterios):
  - cada 15 s, y `git fetch --quiet origin` cada 60 s;
  - **`commit`** por cada commit nuevo de una rama local que no está en `origin/main` y que se hizo **en este clon** con `git commit` o `git revert` (la regla del reflog, abajo) (fuente `git`, actor `humano`; en una rama `worktree-agent-<id>`, actor `worker` con la tarea de su encargo), con `tarea` si el asunto **empieza** por un `Txx` (`T07 · …`, ADR-0002; una mención en medio no cuenta) y `datos` = `{sha, rama, alcanzable: false}`. Los merges no se emiten como commits;
  - **cuando cambia `origin/main`**, primero los `commit` del tramo nuevo que se hicieron en este clon (la misma regla) y aún no ha emitido (`alcanzable: true`). Los demás (de otras personas o de otro clon) no se emiten como suyos, aunque lleven el correo de esta persona: solo entran en el `incluye` del `push`. Después, `push` (actor `demonio`, `datos.sha` = punta nueva, `datos.incluye` = los shas del tramo que citan un ID o son fusiones aprobadas que ha visto);
  - **qué commits son de este clon** (tras congelar, 2026-10-17, PR #12: el correo del committer atribuía por el autor de git, issue #2, hallazgos 2 y 5; PR #20: una rama fusionada y borrada antes de la vuelta, y los worktrees de otra persona, issue #15, hallazgos 1, 7 y 8): solo los shas que tienen una entrada `commit:`, `commit (initial):`, `commit (amend):` o `revert:` en el reflog de **HEAD de la copia principal** o en el de una rama **`worktree-agent-<id>`** (está en el git común). No se lee el reflog de las demás ramas: no dice desde qué worktree se hizo el commit. Nunca se miran el autor ni el committer de git. Por eso:
    - **salen** los `git commit` y `git revert` hechos en la copia principal, en cualquier rama o con HEAD suelto (si después llegan a una rama local o a `origin/main`), antes o después de subirlos, aunque la rama ya se haya borrado (fusionada en local y borrada antes de la vuelta) y aunque el demonio estuviera apagado; el `--amend`; los de los workers en su rama `worktree-agent-<id>`; y un `git commit` que copia contenido ajeno (`merge --squash` + `commit`, `checkout otra -- fichero` + `commit`), que para git es un commit hecho aquí;
    - **no salen** los commits de un worktree que no es el principal ni de worker (puede ser de otra persona); los traídos con `fetch` y `checkout`, `merge` o `pull`; los shas nuevos de `cherry-pick`, también de commits propios (no se distingue si lo aplicado es propio o ajeno), y los de un rebase, salvo lo de la viñeta siguiente; los de un `reset` a otro sha; los merges, como antes. Sin reflog, o si git no puede leerlo, ninguno;
    - **un rebase** (tras congelar, 2026-10-18, PR #29, issue #23: `pull --rebase`, `rebase --continue` y `rebase -i` no dejan `commit:`, y los commits propios reescritos se perdían): un sha que deja un rebase en esos reflogs (`pull … (pick):` o `rebase (pick|continue|fixup|squash|reword|edit):`, `REESCRITO_AQUI`) cuenta **solo** si su `git patch-id --stable` es el de un commit propio (`commit:`, `revert:`…) de los 500 más nuevos de alguno de esos reflogs (`MAX_PARCHES`, `SondeoGit._creados` y `_mismo_parche`). Los patch-id se calculan solo cuando hay un sha reescrito que mirar y se guardan en memoria; si git falla, esa vuelta no sale. Por eso **salen** los commits propios reescritos por `pull --rebase` o `rebase -i` (pick, reword) y los que siguen a un `--continue`; **no salen** el commit resuelto tras un conflicto (la resolución cambia su diff), un fixup o un squash (aunque junte solo commits propios), uno cuyo original es más viejo que esos 500, ni un rebase dentro de un worktree de worker (sus picks quedan en el reflog de HEAD de ese worktree, que no se lee). Un `edit` + `commit --amend` deja `commit (amend):` y cuenta como antes. Al revés, un commit ajeno reescrito por un rebase en este clon con el mismo diff que uno propio sale como propio;
    - una entrada `commit:` escrita en esos reflogs por otro medio (`update-ref -m "commit: …"` sobre HEAD o sobre una rama `worktree-agent-<id>`, una línea añadida a mano, `GIT_REFLOG_ACTION=commit`) hace pasar por propio un sha ajeno: el demonio no lo distingue;
  - horas en UTC con `Z`; IDs deterministas (`git-<persona>-commit-<sha12>`, `git-<persona>-push-<sha12>`). Un commit o la punta nueva solo quedan vistos (`<git común>/hackathon/os/git.json`) cuando el relay los confirma: si el demonio se reinicia antes, los vuelve a emitir con el mismo ID y el relay los descarta;
  - **cada reflog se lee por separado** (tras congelar, 2026-10-18, PR #29, issue #23: si una rama `worktree-agent-*` desaparecía entre `for-each-ref` y `log -g`, git salía con 128 y se perdía la vuelta entera, con lo que se subía en ella): `git log -g` ref a ref, el de HEAD y el de cada rama `worktree-agent-<id>` (`SondeoGit._creados`). Una ref que ya no existe se ignora y las demás cuentan;
  - la primera vez, lo que ya estaba en `origin/main` no es un push nuevo.
    - salvo lo que subió este clon (tras congelar, 2026-10-18, PR #29: lo subido antes de la primera vuelta del demonio, o con el demonio apagado y sin `git.json`, no salía nunca y la tarea no llegaba a `publicada`; nota del PR #24): sin `git.json`, el punto de partida es la punta de `refs/remotes/origin/main` de antes de la última entrada `update by push` de su reflog, la que deja un `git push` hecho en este clon. Sin esa entrada, sin reflog o si esa punta ya no es un commit, la punta de ahora (`SondeoGit._partida`). Los commits del tramo siguen pasando por la regla del reflog y por `vistos`, con los mismos IDs.
- **Desde el 2026-10-16:** tras el `push`, el `arbol` de la copia principal (nota de arriba).
- **Aplazado:** el `arbol` de git por worktree (en las sesiones lo da `arbol.sh`), `refs/hackathon/` y la reconciliación de `fusion.*` por refs.
- Con `publicar_wip: sí`: cada 60 s, commit del árbol con un índice temporal (`GIT_INDEX_FILE`, `add -A`, exclusiones de ADR-0007, `write-tree`, `commit-tree -p HEAD`; `HEAD` si no hay cambios) y `git push --force origin <sha>:refs/hackathon/wip/<persona>` **solo** si cambió el sha. (M8g.)
- **Implementado en M8g** (`hkos/colisiones_merge.py`, clase `Publicador`, en un hilo propio del demonio; decisiones del usuario):
  - solo la copia principal (los worktrees de los workers no publican);
  - todos los `git` con `GIT_OPTIONAL_LOCKS=0`, `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, `GIT_SSH_COMMAND="ssh -o BatchMode=yes"` y `-c credential.interactive=false`;
  - antes de nada: si `origin` es de GitHub, `gh repo view <dueño/repo> --json visibility` una vez; público sin `publicar_wip: sí, incluso público`, o sin respuesta: no publica, y lo dicen `/salud` y una línea `>` de `estado-equipo.md`. Un remoto que no es de GitHub (un `bare` local, la LAN) publica;
  - con `MERGE_HEAD`, `REBASE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `rebase-merge/`, `rebase-apply/` o entradas sin fusionar en el índice, no publica ni avisa;
  - índice temporal = copia del índice de la persona (solo se lee) en `wip.index`; `git add -A` con pathspecs (`--pathspec-from-file`) que excluyen `.env*`, `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `*.pfx`, `credentials*.json`, `secrets*` (en cualquier carpeta, sin distinguir mayúsculas), las carpetas de `datos_excluidos:`, `.claude/worktrees/` y los ficheros de más de 1 MB (medidos en disco antes de añadir): lo excluido nunca llega a ser un objeto de git. Un `git add` que sale con 1 solo vale si lo único que dice es que una de esas exclusiones nombra una ruta ya ignorada por `.gitignore`;
  - lo excluido que ya estaba en el índice o en la base vuelve a su versión de la base (o se quita);
  - el padre es `merge-base HEAD origin/main`, no HEAD (los commits locales sin subir no viajan como ancestros); autor «hk-os wip», sin coautoría;
  - árbol igual al de la base: no hay trabajo en curso y, si había ref publicada, se borra (`git push origin :refs/hackathon/wip/<persona>`); también al arrancar con `publicar_wip: no` si `wip.json` dice que publicó. Árbol igual al último publicado: nada;
  - `git push --force --no-verify` (el `pre-push` de la persona no corre en este push, que no es a una rama);
  - si el push falla por autenticación, espera 10 min; por otra cosa, espera creciente (hasta 10 min);
  - lo publicado se ve: `wip.json` (sha, árbol, base, hora y la lista completa de ficheros), la línea `wip:` de `/salud` y una línea en `agente.log` por publicación.
- Escribe `<git común>/hackathon/os/estado-equipo.md` (formato §6) y `estado.json` local cada vez que recibe uno del relay. (M8f.) **Implementado en M8f:** `GET /v1/estado` con `If-None-Match` cada 3 s; el md se reescribe al llegar un estado nuevo, al caer o volver el relay y cada 30 s (las horas y lo «viejo» cambian con el tiempo; las firmas, no). Escrituras atómicas (`os.replace`). Con el relay caído, el md lo dice (`relay=viejo` y una línea «Relay sin respuesta desde hh:mm», R-29).
- Sin relay: sigue con lo local y marca `fuentes.relay` como viejo.
- Lo lanza `SessionStart` (`sesion.sh`, detrás del interruptor y de la coordinación activa) si nadie responde en su puerto, desacoplado de la sesión. Siempre con `uv run --no-project` (ADR-0005). Lanzador:
  - Windows (Git Bash): `powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden …"`, síncrono (≈0,5 s): un hijo con `nohup … &` muere al acabar el hook (ADR-0004);
  - Linux: `setsid -f nohup …`;
  - sin `setsid` (macOS): `nohup … &` y el propio demonio se desacopla al arrancar (`--desacoplar`: `fork` y `os.setsid()`).
  - Sin `uv` en el `PATH`, no lanza nada y lo avisa una vez por sesión, como el puerto ocupado.
- **`agente.vivo`.** Al conseguir el puerto, el demonio escribe su puerto en `<git común>/hackathon/os/agente.vivo` y lo borra al salir (también al apagarse por `apagado_min`). Desde M8f, una segunda línea con la hora (época), renovada cada 15 s. En Windows el arranque solo conecta directamente al puerto si ese fichero existe; si no, el sondeo (tope de 0,1 s) lo hace el mismo PowerShell que lanza el demonio. Cada `SessionStart` deja una línea en `…/arranque.log`. `delta.sh` da por muerto el demonio (y, si sabe la persona del clon, borra `agente.vivo` y llama a `arranque.sh`) si falta la hora, si tiene más de 60 s o, desde el 2026-10-18 (tras congelar, PR #28, issue #23, hallazgo 1), si está más de 5 s en el futuro (`VIVO_S`, `FUTURO_S`, con `EPOCHSECONDS`; la hora, de 1 a 15 cifras y leída en base 10). `arranque.sh` no lanza otro si el de antes sigue contestando `/salud`.
- **Bloqueo: el puerto.** Escucha en `127.0.0.1:<puerto>` (`puerto_agente:` de `os.md`, o `47100 + (cksum del git común) % 900`, con el git común escrito como lo da `git rev-parse --path-format=absolute --git-common-dir` y sin salto: `printf '%s' "$ruta" | cksum`). Si el `bind` falla, sale. `GET /salud` responde en texto plano, sin token (solo escucha en `127.0.0.1`), con las reglas de `Host` y `Origin` de M9a (si no, `403`): la primera línea es `hk-os <ruta del git común>` (con `/`); detrás, líneas `clave: valor` (`pendientes`, `lineas_corruptas`, `invalidos`, `relay`). **Reto** (tras congelar, 2026-10-18, decisión 7B del usuario en el PR #13; PR #33: `Agente.prueba`, `Manejador._salud`, `_host_local`, `RETO`). Si la petición lleva la cabecera `X-HK-Reto` con exactamente 64 caracteres hexadecimales en minúsculas (32 bytes aleatorios, `secrets.token_hex(32)`), el demonio tiene `web.token`, `Host` es `127.0.0.1:<puerto>` o `localhost:<puerto>` y `Origin`, si viene, es `http://127.0.0.1:<puerto>` o `http://localhost:<puerto>`, la respuesta lleva además la cabecera `X-HK-Prueba` con `HMAC-SHA256` en hexadecimal en minúsculas (64 caracteres). La clave es `web.token` (sus 64 caracteres hex, en ASCII) y el mensaje es el valor de `X-HK-Reto` (en ASCII). Si falta alguna de esas condiciones, la respuesta es la de siempre, sin `X-HK-Prueba`. El código es siempre `200` y el cuerpo no cambia: el arranque, que no manda reto, sigue igual. El arranque solo da por vivo un demonio cuya primera línea es esa con su mismo git común (sin distinguir mayúsculas en Windows). El arranque manda `Host: 127.0.0.1:<puerto>`.
- **`reflog: no`** (tras congelar, 2026-10-18, PR #29, issue #23): sin reflog, ningún commit nuevo sale como propio (abajo) y antes nada lo decía. En cada vuelta de git (detrás de la comprobación de `origin/main`), el demonio mira `git config --get core.logAllRefUpdates` (`false`, `no`, `off` o `0`) y si existe `<git común>/logs/HEAD` (`SondeoGit._reflog`). Mientras falte, `/salud` lleva la línea `reflog: no` (si lo hay, ninguna línea; `Agente.salud`), y cuando cambia deja una línea en `agente.log`: «reflog: no (core.logAllRefUpdates=false): los commits nuevos no se pueden dar por propios y no salen; la configuración de git no se toca» (o «falta logs/HEAD»), o «reflog: sí» al volver. No toca la configuración de git.
- **Puerto ocupado por otro programa** (el puerto acepta conexiones, pero `/salud` no responde con nuestro git común): `SessionStart` no lanza el demonio y lo avisa **una vez**: «el puerto N está ocupado por otro programa; pon `puerto_agente:` en `.hackathon/os.md`». A la persona, con `systemMessage`; al modelo, en una línea factual. Anota `puerto_ocupado` en `entregado/<session_id>` para no volver a intentarlo ni a avisar en esa sesión. Los eventos siguen esperando en disco. `sesion.sh` sale en JSON (`systemMessage` y `hookSpecificOutput.additionalContext`) solo en ese caso; si no, su salida es la de siempre.
- **Apagado:** sale tras `apagado_min` sin eventos nuevos en los JSONL y sin ninguna sesión activa (una sesión deja de estar activa con su `sesion.fin` o tras 90 s sin señales).

### Web de trabajo (M9a; solo con `web_nueva: sí`; ADR-0009, ADR-0010, ADR-0011)
**Token local.** Al arrancar, si no existe, el demonio crea `<git común>/hackathon/os/web.token` con 32 bytes aleatorios en hex (`secrets.token_hex(32)`). Se reutiliza en cada arranque y se compara en tiempo constante. `hk-os web` lo lee y comprueba el demonio en dos pasos (tras congelar, 2026-10-18, decisión 7B del usuario en el PR #13; PR #33: `cli._puerto_fiable`, `cli.web`, `NO_DEMOSTRADO`). Primero, la hora de `agente.vivo` (ni más de 60 s ni más de 5 s en el futuro) y, en Linux, el dueño del puerto en `/proc/net/tcp{,6}`. Después, `GET /salud` con un `X-HK-Reto` nuevo en cada llamada: la primera línea tiene que ser `hk-os <git común>` y `X-HK-Prueba` tiene que coincidir con `HMAC-SHA256(web.token, reto)`, comparadas con `hmac.compare_digest`. Si la cabecera falta (un demonio antiguo) o no coincide, no manda el token, no abre el navegador y dice «el demonio no ha demostrado que es el tuyo; reinícialo con la versión nueva». Si todo pasa, abre `http://127.0.0.1:<puerto>/#t=<token>` en el navegador (`webbrowser`). También imprime la URL **sin** el token y cómo volver a abrirla.
- **Fuera de Windows** (Linux y macOS; tras congelar, 2026-10-17, PR #11: otros usuarios ven los argumentos de cualquier proceso en `/proc/*/cmdline` o con `ps`, issue #6), el navegador no recibe la URL con el token. `hk-os web` escribe `<git común>/hackathon/os/web.html`, con permisos 0600 desde que se crea (temporal con `O_CREAT|O_EXCL` y `os.replace`), una página que redirige a la URL con el token (`meta refresh` y un enlace, `referrer` `no-referrer`), y al navegador solo le pasa `file:///…/web.html`. Si no hay navegador, dice qué fichero abrir a mano, sin imprimir el token. En Windows no cambia nada: la línea de órdenes de un proceso de otro usuario solo la leen los administradores.

- **Antes de mandar el token** (tras congelar, 2026-10-17, PR #19: quien conteste `/salud` en el puerto de un `agente.vivo` que se quedó en disco recibiría el token, issue #15, hallazgo 4), `hk-os web` lee `agente.vivo` y no sigue si le falta la hora, si tiene más de 60 s o si está más de 5 s en el futuro (el criterio de `delta.sh`, en segundos enteros: `VIVO_S`, `FUTURO_S`; lo del futuro, tras congelar, 2026-10-18, PR #28, issue #23, hallazgo 1), ni, en Linux, si en `/proc/net/tcp` y `tcp6` no hay nadie en escucha en ese puerto (en `127.0.0.1`, `0.0.0.0`, `::` o las mapeadas) o alguno es de otro uid. Si no puede leer `/proc`, solo cuenta la hora; en Windows y macOS, también solo la hora. Entonces no pide ni `/salud`. En cada rechazo, también en los de `/salud`, no manda el token, no abre el navegador y sale con 1 diciendo su motivo (`cli._puerto_fiable` y `cli.web`; tras congelar, 2026-10-18, PR #28, issue #23, hallazgo 17; antes, siempre «no está en marcha»):
  - sin `agente.vivo` o sin hora, o si `/salud` no responde: «el demonio de este clon no está en marcha…», como antes;
  - la hora vieja: «el demonio de este clon no ha latido en N s; si acabas de despertar el portátil, espera 15 s y vuelve a probar…»;
  - la hora en el futuro: «la hora de agente.vivo está N s en el futuro…»;
  - en Linux, nadie en escucha en ese puerto: «no encuentro el puerto N en escucha en /proc/net/tcp (¿el demonio corre en otro espacio de nombres de red…?)»;
  - en Linux, de otro uid: «el puerto N es de otro usuario (uid X)…», y con 65534, que puede ser otro espacio de nombres de usuario;
  - si `/salud` contesta, pero con otra primera línea: «en el puerto N contesta otro programa, no el demonio de este clon… pon puerto_agente: en .hackathon/os.md».
- **«Abre a mano»** (tras congelar, 2026-10-17, PR #19: un navegador snap no lee repos fuera de `/home` ni bajo carpetas ocultas, issue #15, hallazgo 11): fuera de Windows, cuando el navegador abre, `hk-os web` también dice «Abre a mano `file:///…/web.html` si el navegador no puede leerla (lleva el token: no la compartas)», sin imprimir el token.

**Reglas comunes a todas las rutas de M9a**:
- **`Host`** igual a `127.0.0.1:<puerto>` o `localhost:<puerto>`; si no, `403` (contra DNS rebinding). En `/salud`, igual: `403 {"error":"origen"}`, también sin `web_nueva: sí`, y sin nada del cuerpo (tras congelar, 2026-10-18, decisión 5A del usuario en el PR #13; PR #35).
- **`Origin`**, si viene, igual a `http://127.0.0.1:<puerto>` o `http://localhost:<puerto>`; si no, `403`.
- **Sin cabeceras CORS** en ninguna respuesta. `OPTIONS` a cualquier ruta da `405` sin cabeceras `Access-Control-*`.
- **El token**, solo en la cabecera `X-HK-Token`. Las rutas de datos y de acción sin ella, o con otra, dan `401`. Un `t=` o `token=` en la query no cuenta y da también `401`: nunca se acepta por la query.
- Respuestas JSON en UTF-8, con `Cache-Control: no-store`.

| Método y ruta | Token | Qué hace | Respuesta |
|---|---|---|---|
| `GET /` y `GET /assets/<fichero>` | No | Los ficheros de `hkos/web/nueva/` (el compilado). Lista blanca: `index.html` en `/` y lo que exista en `assets/`, sin `..` ni subcarpetas fuera de ella. Tipos por extensión (`.js`, `.css`, `.woff2`, `.svg`, `.png`). El HTML no lleva datos ni el token | `200`, o `404` |
| `GET /v1/vista` | Sí | `{servido_en, persona, relay: {conectado, desde}, vista}`. `vista` = `proyeccion.vista(estado.json local, ahora)`, con `servicios` (§3) y `umbrales.fuente_s` = `umbral_viejo_s`. `relay` es del transporte (el demonio oye o no al relay), como `relay=ok\|viejo` en la cabecera de `estado-equipo.md` y con el mismo valor | `200`; `503` `{"error":"sin estado"}` si aún no hay `estado.json` |
| `GET /v1/stream` | Sí | SSE. Al conectar, `event: vista` con lo mismo que `/v1/vista`. Después, `vista` cada vez que llega un estado nuevo del relay o cambia `relay.conectado`; `eventos` tal como llegan del relay (§3), sin cambiarlos; `ping` cada 20 s sin nada más, precedido de otra `vista` calculada en ese momento, para que `servido_en` y lo «viejo» avancen con el tiempo como en `/v1/vista` y `estado-equipo.md` (tras congelar, 2026-10-17, PR #12, issue #6). Sin `estado.json`, la `vista` no se manda y solo van los `ping`. Como mucho 8 clientes a la vez | `text/event-stream`; `429 {"error":"demasiados clientes"}` con 8 ya conectados (el hueco se libera al cortarse uno) |
| `POST /v1/anotar` | Sí | Anotar (abajo) | `200 {"ok":true,"sha":…}`; `400` con el campo que no vale; `409` si el push se rechaza dos veces; `429` por encima del tope; `502` si git falla por otra cosa (con el motivo en una línea); `503 {"error":"ocupado"}` si otra acción no ha terminado en 5 s |
| `POST /v1/reclamar` | Sí | Reclamar (abajo) | `200 {"ok":true,"issue":n\|null}`; `404` si la tarea no existe; `409` si no está libre o es de otro dueño; `429` por encima del tope; `502` si `gh` falla; `503 {"error":"ocupado"}` si otra acción no ha terminado en 5 s |

El hueco de un cliente de `/v1/stream` que cierra se libera en 1 s, sin esperar al `ping` (tras congelar, 2026-10-17, PR #20, issue #15, hallazgo 9): entre `ping` y `ping`, cada segundo sin nada que mandar, el demonio mira si la conexión da EOF o un error y, si es así, termina el stream. Lo que el cliente mande de más se lee y se descarta, para ver el EOF que venga detrás; pasados 64 KB en total, se cierra el stream (`DESCARTE_MAX`). Lo mira con un `selectors.DefaultSelector` por stream, no con `select.select`, que con un descriptor ≥ 1024 cerraba cada stream al segundo. Un cierre de escritura (`shutdown(SHUT_WR)`) da el mismo EOF que un cierre y cuenta como cierre (`_cerrado`; tras congelar, 2026-10-18, PR #29, issue #23: con `MSG_PEEK`, un byte de más tapaba el EOF hasta el `ping`).

Las acciones exigen además `Content-Type: application/json` (si no, `415`) y un cuerpo de 4 KB como mucho (si no, `413`).

Anotar y Reclamar van de una en una. Cada una espera a la otra 5 s como mucho; si no, `503 {"error":"ocupado"}` sin hacer nada (ni `git`, ni `gh`, ni `acciones.jsonl`) (tras congelar, 2026-10-18, decisión 13B del usuario en el PR #13; PR #32: `Acciones.__call__`, `CERROJO_S`). En Anotar, el orden es `503` → `400` → `429` → git.

Cada conexión con el demonio tiene un plazo de socket de 10 s (tras congelar, 2026-10-17, PR #12, issue #6): un `POST` cuyo cuerpo prometido (`Content-Length`) no llega en ese plazo recibe `408 {"error":"cuerpo"}` y se cierra la conexión; si ni siquiera llega la línea de la petición, la conexión se cierra sin respuesta.

**Cómo lee la web** (ADR-0010):
- Toma el token del fragmento, lo quita de la URL con `history.replaceState` y lo guarda solo en memoria.
- Lee `/v1/stream` con `fetch` y un `ReadableStream`, con `X-HK-Token`: `EventSource` no admite cabeceras.
- Si el stream se corta, reconecta con espera creciente (1 s → 30 s) y, mientras, pide `/v1/vista` cada 3 s.
- **Atrás y la bfcache** (tras congelar, 2026-10-18, PR #26, issue #23: una seguidora no se restauraba al volver con Atrás). En `pagehide`, la pestaña cierra el canal entre pestañas y sale de la cola del cerrojo; si es la líder, lo suelta y corta su stream. En `pageshow` con `persisted`, vuelve a abrir el canal, manda `hola` y se pone en la cola (`useDemonio`: `para`, `arranca`). El token se queda en la memoria de la pestaña, que la caché conserva; no se guarda en ningún almacenamiento. Lo que el demonio responde lleva `Cache-Control: no-store` (`index.html`, `/v1/vista`, `/v1/stream`), y Chrome no guarda en la bfcache una página que ha recibido por `fetch` una respuesta así: una pestaña que ha sido líder no se restaura, recarga sin token y hay que volver a `hk-os web`. Una seguidora que nunca ha pedido nada al demonio sí se restaura (comprobado en Chrome 155 con `scripts/pestanas_chrome.mjs`, PR #26).
- Sin nada del demonio (ni vista, ni `eventos`, ni `ping`) durante `max(umbral_viejo_s, 40 s)`, pasa a «sin conexión» (ADR-0009). Los 40 s son el doble del `ping` de 20 s: un `ping` perdido no basta para que la página salga «sin conexión». Con el `umbral_viejo_s` por defecto (300 s) manda este; los 40 s solo cuentan si alguien lo baja en `os.md`.
- **Un solo `/v1/stream` por navegador y origen** (tras congelar, 2026-10-17, PR #17: Chrome abre como mucho 6 conexiones por host y, con un stream por pestaña, desde la 7.ª la página no cargaba, issue #15, hallazgo 3). Con `navigator.locks`, `BroadcastChannel` y `crypto.subtle`, solo la pestaña que tiene el cerrojo `hk-os-stream-<SHA-256 del token>` (la líder) habla con el demonio (stream, sondeo y reconexión) y reparte por el canal del mismo nombre, tal cual, lo que recibe: la vista, los `eventos` y los `ping`, con la hora a la que los recibió (así «sin conexión» se mide igual en todas), y el modo y los fallos. Una pestaña que llega pide con `hola` la última vista, el modo y el fallo (los `eventos` no). Si la líder se cierra, otra coge el cerrojo y abre el stream. Solo comparten stream las pestañas con el mismo token; `127.0.0.1` y `localhost` son orígenes distintos, cada uno con su líder. Sin esas APIs, o si falla la huella, cada pestaña lee su propio stream.
- **Con un `429`** del stream, la web dice «sin stream: tu demonio no admite más (demasiadas pestañas o clientes abiertos); pidiendo cada 3 s» y sigue pidiendo `/v1/vista` cada 3 s y reintentando el stream con espera creciente; el aviso se va cuando vuelve el stream (PR #17, issue #15, hallazgo 10).

**Pestaña líder: latido y relevo** (tras congelar, 2026-10-18, PR #26: una líder congelada o colgada no soltaba el cerrojo, y una oculta más de 5 min tiene los timers frenados por Chrome, issue #23). La líder manda un `latido` por el canal cada 2 s, con si está visible y cuánto lleva oculta (`LATIDO_MS`). Una pestaña **visible** que no la oye en 8 s más un azar de hasta 1,5 s (`RELEVO_MS`, `RELEVO_AZAR_MS`), o que ve que lleva oculta 20 s (`CEDE_MS`, más el mismo azar), le quita el cerrojo (`navigator.locks.request(…, {steal: true})`) y abre el stream. La líder que lo pierde (su petición acaba en `AbortError`, también al despertar) corta su stream y vuelve a la cola. Cada líder firma lo que manda con su `era` (la hora a la que cogió el cerrojo, siempre mayor que la última que oyó): lo de una era anterior no se pinta, y una líder que oye una era más nueva deja de serlo. Solo releva una pestaña visible; con todas ocultas no releva ninguna, y la primera que vuelve a verse lo mira en el acto (`visibilitychange`). Todo en `datos/demonio.js` (`useDemonio`: `vigila`, `pide`, `alMensaje`, `alVerse`).

**Suscripción al relay.** Con `web_nueva: sí`, el demonio deja el sondeo de `GET /v1/estado` cada 3 s (M8f) y lee `GET /v1/stream` del relay en un hilo: `estado` sustituye a la respuesta del sondeo (mismo `estado.json`, mismo `estado-equipo.md`) y `eventos` se reenvía a sus clientes. Si el stream se corta, vuelve al sondeo cada 3 s hasta que reconecta (espera creciente hasta 30 s). `relay.conectado` es `false` desde el corte hasta el primer mensaje nuevo, y `relay.desde` es la hora del último mensaje bueno.

**Jurado y ruta** (tras congelar, 2026-10-19, M10; ADR-0009, ADR-0012, ADR-0013; detalle en §11). El demonio no lee los interruptores: si su `estado.json` trae `jurado` o `ruta`, `proyeccion.vista` añade los bloques `jurado` y `ruta`, y salen en `/v1/vista` y en la `vista` del SSE de su web, sin rutas nuevas. La web los pinta (dos vistas propias o, si se recortan, secciones de la cabina) y no calcula nada: ni cobertura, ni orden, ni rango, ni veredicto, ni «viejo»; solo formatea «hace X» y coloca en la línea de tiempo las horas que ya trae la vista. Lo que es estimación se pinta distinto de los hechos, y lo declarado, con su marca. Sin los bloques, la web es la de M9a. Con `web_nueva: no`, los bloques siguen en el md (§6) y en el MCP (§11.5).

**Salud de los servicios.** Cada 15 s, para cada servicio de `estado.json` → `servicios.lista` con `confirmacion.valor = confirmada`, `dueno_autoridad` = esta persona y un Puerto válido:
- conecta por TCP a `127.0.0.1:<Puerto>` (0,5 s como mucho) y, si acepta y hay una Salud válida (§10), hace `GET <Salud>` en `127.0.0.1:<Puerto>`, con 2 s como mucho, sin seguir redirecciones, sin cuerpo y leyendo como mucho 4 KB;
- emite `servicio.estado` una vez al arrancar, cuando cambia (`escucha`, `salud`) respecto de lo último que emitió para esa `clave` y, sin cambios, cada N s, con N = `umbral_viejo_s / 2` (el `umbral_viejo_s` de `os.md`, el mismo de la proyección: 150 s con el valor por defecto de 300). Como comprueba cada 15 s, sale en la primera vuelta en que se ha cumplido el plazo. Un cambio emite enseguida y la cuenta vuelve a empezar. Así «viejo» quiere decir «sin comprobar»: un portátil cerrado deja de emitir y se nota (tras congelar, 2026-10-18, decisión 1B del usuario en el PR #13; PR #33: `SaludServicios.ciclo`, `latido_s`, `emitido_en`);
- nunca consulta otra IP, nunca ejecuta Arranque ni Prueba, y no consulta filas sin confirmar, de otra persona o con un formato que no vale.

**Anotar** (`POST /v1/anotar`):
- **Cuerpo:**
  - `papel` (`jurado` | `mentor` | `organizacion`);
  - `quien` (opcional, ≤ 80);
  - `que_dijo` (1–500);
  - `literal` (booleano);
  - `fuerza` (`dato` | `obligatorio` | `se valora` | `nos gustaría ver` | `comentario suelto` | `sin precisar`);
  - `donde` (opcional, ≤ 80).

  Un campo de más, o fuera de su lista o de su longitud, da `400`.
- **Tope** (tras congelar, 2026-10-18, decisión 12A del usuario en el PR #13; PR #32): 30 notas por persona y hora, contadas en `<git común>/hackathon/os/acciones.jsonl`. Cada nota que entra en `origin/main` añade la línea `{"tipo":"nota","sha":"<sha>","ts":"<UTC>"}`, con un solo `write` en modo append. Va sin `id`, así que el monitor no la lee. Una nota repetida que ya estaba en `origin/main` no sube nada y no añade línea. Con 30 líneas `nota` de la última hora, `429 {"error":"30 notas por hora"}` antes de cualquier `git`. Como en Reclamar, una línea con la hora más de 5 min en el futuro no cuenta. (`TOPE_NOTAS_HORA`, `NOTA_SUBIDA`, `reciente`, `Acciones._registro` y `Acciones.anotar`; las líneas `reclamo` y `reclamo_fallido` no cuentan para este tope, ni las `nota` para el de Reclamar. Un `400` va antes que el `429`.)
- **Saneado:** saltos de línea y tabuladores, a un espacio; espacios repetidos, a uno; un `#` o `>` al principio se quita; ningún carácter de control. Además (tras congelar, 2026-10-17, PR #16, issue #10):
  - fuera toda la categoría `Cf` (formato: los invisibles de dirección, U+061C, U+200B, U+200E, U+200F, U+202A–202E, U+2060–2064, U+2066–2069, U+FEFF, U+FFF9–FFFB, y también U+00AD, U+180E, las etiquetas U+E0001 y U+E0020–E007F…) salvo U+200C (ZWNJ) y U+200D (ZWJ), que se quedan (persa, hindi, emojis; `QUEDAN`; tras congelar, 2026-10-18, decisión 16B del usuario en el PR #13, PR #32), los surrogates sueltos (`Cs`, que `json.loads` deja pasar: `\udcc2\udcbb` llegaba a main como `»`) y U+034F, U+115F, U+1160, U+3164 y U+E0000–E007F (`acciones.sanear`, `QUITAR`, `INVISIBLES`; tras congelar, 2026-10-17, PR #24, issue #18, hallazgos 1 y 5). Una bandera de subdivisión pierde sus etiquetas (🏴 con las de Inglaterra queda en 🏴). Se quedan 👩‍💻 (ZWJ), ❤️ (VS16, que es `Mn`) y el ZWNJ de «می‌خواهم» y «क्‌ष». Se hace en `validar_nota`, antes de cualquier fetch, y la nota se codifica en estricto (`anadir`): de ella no sale un byte que no sea UTF-8 válido;
  - fuera `«` y `»`, también escritas como entidad (`&laquo;`, `&raquo;`, `&#171;`, `&#187;`, `&#xab;`, `&#xbb;`, sin distinguir mayúsculas y con ceros delante o sin ellos): una nota no puede cerrar sus comillas en `estado-equipo.md` (constitución V);
  - el HTML no se borra (tras congelar, 2026-10-17, PR #24, issue #18, hallazgo 6: `a<b y c>d` quedaba en `ad`): un `<` seguido de una letra ASCII, `/`, `!` o `?`, que es lo único que abre HTML en CommonMark, pasa a ser `‹` (U+2039), salvo en un autoenlace (`<esquema:…>`, con un esquema de 2 a 32 caracteres y sin espacios ni `<>` dentro), que se deja (`acciones.HTML`). `si a<b y c>d` queda en `si a‹b y c>d`; `<https://e.com/x?a=1&b=2>` y `<mailto:a@b.c>` se quedan; `<a:b onerror=x>` queda en `‹a:b onerror=x>`. `3 < 4` y `<3` se quedan;
  - las comillas y el HTML se tratan una y otra vez hasta que no cambia nada (`&la&laquo;quo;` deja otro `&laquo;`, que también se quita; `<«!--` deja otro `<!--`, que queda en `‹!--`).
- **Nota**, con el formato de la plantilla de `/hack-note`:
  ```
  ## <AAAA-MM-DD HH:MM local> · <quien o —> (<jurado|mentor|organización>)
  - Dónde: <donde o —>
  - Qué dijo: «<que_dijo>» si literal; si no, (paráfrasis) <que_dijo>
  - Fuerza: <fuerza>
  - Afecta a: — (anotada desde la web; la revisa /hack-check)
  - Anotado por: @<persona>
  ```
- **Escritura**, sin tocar la copia ni el índice de la persona (ADR-0010):
  1. `git fetch origin`;
  2. con `GIT_INDEX_FILE` = `<git común>/hackathon/os/nota.index`, `read-tree origin/main`;
  3. el contenido de `.hackathon/criterios.md` de `origin/main` (si no existe, la plantilla de `skills/hack-note/templates/criterios.md`), con una línea en blanco y la nota al final; `hash-object -w` y `update-index --cacheinfo`;
  4. si a `.gitattributes` le falta `.hackathon/criterios.md merge=union`, se añade igual;
  5. `write-tree` y `commit-tree -p origin/main -m "Criterio: <papel> · <primeros 50 caracteres de que_dijo>"`, con la identidad de git del clon y sin coautoría;
  6. `git push --no-verify origin <sha>:refs/heads/main`.

  Si el push se rechaza por no ser avance rápido, repite una vez desde el paso 1. Si vuelve a fallar, `409` y la web lo dice.
  - «Se rechaza por no ser avance rápido» (tras congelar, 2026-10-17, PR #16, issue #10) es lo que dice la línea `!` de `refs/heads/main` en la salida de `push --porcelain`; el stderr no se mira. Cuenta como carrera `[rejected] …` o `[remote rejected] (failed to update ref | failed to lock | cannot lock ref … | incorrect old value … | reference already exists)`. Cualquier otro rechazo (por ejemplo, un hook que lo rechaza) da `502` sin reintento.
  - Los motivos del remoto también salen con su disco lleno o con un `main.lock` huérfano, así que el reintento comprueba tras su `fetch` que `origin/main` ya no es el padre del commit rechazado (con cualquiera de los motivos de carrera). Si no se ha movido, no era una carrera: `502` con el motivo, sin volver a subir.
  - Cada orden de git tiene un plazo de 60 s. Pasado, se mata el árbol de procesos entero (`taskkill /F /T` en Windows; en Linux y macOS, su grupo de procesos con `SIGKILL`) y da `502 {"error":"git <orden>: sin respuesta en 60 s"}`.

  Nunca hay merge, rebase, checkout ni stash en la copia. Mismo entorno de git sin preguntas que el publicador de M8g (`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, `GIT_ASKPASS` vacío, `ssh -o BatchMode=yes`, `credential.interactive=false`).
- **Después:** no emite evento ni avisa por GitHub. Los demás la ven en novedades cuando el relay hace su fetch, y la propia persona, en el siguiente `git pull`. Si la línea de `acciones.jsonl` no se puede escribir, la nota ya está en `origin/main`: responde `200` y lo deja en `agente.log`.
- **Espera por la base y push sin informe** (tras congelar, 2026-10-17, PR #24, issue #18, hallazgos 2, 3 y 8):
  - si el push se rechaza con un motivo de carrera y `origin/main` no se ha movido, el reintento espera 1 s y vuelve a hacer el fetch, como mucho 3 veces (`ESPERAS_BASE`, `ESPERA_BASE_S`, `Acciones._base`): otro push puede tener aún `main.lock`. Las esperas no pasan de 60 s desde que empezó Anotar (`self.limite`); el resto de Anotar no tiene ese tope. Si la base se mueve, reintenta; si no, `502` con el motivo, como antes;
  - un push que falla sin ser una carrera (plazo vencido o salida distinta de 0) no da `502` sin mirar antes: hace un fetch y, si el commit ya está en `origin/main` (`merge-base --is-ancestor`), responde `200` con ese sha (`Acciones._subio`). Un push **sin informe** del remoto (el plazo vencido, o una salida sin la línea `!` de `main`) se comprueba durante 10 s, no una vez (tras congelar, 2026-10-18, PR #31, issue #27: un pre-receive lento actualiza `main` después del primer fetch, y al repetir la nota salía duplicada): vuelve a mirar cada 1,5 s (`SUBIO_S`, `SUBIO_ESPERA_S`), cada fetch con el plazo que quede; un fetch que falla (la red) se deja en `agente.log` y se vuelve a probar, y deja de mirar si `origin/main` se ha movido a algo que no tiene el commit. Con informe del remoto (una línea `!` que no es de carrera, por ejemplo un hook que rechaza), mira una sola vez;
  - **una nota repetida no se duplica** (tras congelar, 2026-10-18, PR #31, issue #27): antes de cada commit, si `criterios.md` de `origin/main` ya tiene un bloque igual al de la nota nueva (la misma cabecera sin la hora, es decir, quién y papel; las mismas líneas, con el mismo «Anotado por: @persona») y su hora está a menos de 10 min (`REPETIDA_S`), responde `200` con ese `origin/main` como `sha`, sin commit ni push (`ya_anotada`, `Acciones._intento`). Lee UTF-8 o UTF-16 y CRLF igual que al añadir (`codificacion`). Dos notas iguales de verdad de la misma persona en menos de 10 min se quedan en una;
  - si `origin/main` no tiene `criterios.md`, la plantilla se sube con LF aunque la copia del kit tenga CRLF (`Acciones._intento`).

**Reclamar** (`POST /v1/reclamar`):
- **Cuerpo:** `{"tarea":"T12"}`, con `^T[0-9]{2,3}$`.
- **Comprobaciones** (sobre `estado.json` local):
  - la tarea existe (si no, `404`);
  - su estado es `lista` o `pendiente` y no tiene asignación (si no, `409`);
  - su `dueno` es esta persona o está vacío. Si es de otro dueño, `409` «es de @x según el plan» (regla de §5).
- **Tope:** 10 reclamos por persona y hora, contados en `<git común>/hackathon/os/acciones.jsonl`. Pasado el tope, `429`. Además (tras congelar, 2026-10-17, PR #16, issue #10):
  - cuentan también los `gh issue edit` que fallaron (la línea `reclamo_fallido` de abajo); como están en el fichero, siguen contando tras reiniciar el demonio;
  - una línea cuenta si `-300 s ≤ ahora − ts < 1 h`: una con el `ts` más de 5 min en el futuro (el reloj iba adelantado y se corrigió) no cuenta.
- **Con GitHub** (`github: sí` y la tarea con `issue`):
  - `repo_tareas` (o, si está vacío, el `repo` de `coordinacion.md`) tiene que tener la forma `dueño/repo`: `^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$`, y el repo no puede ser `.` ni `..`. Si no, `502` y no se llama a `gh` (PR #16);
  - `gh api user` debe ser esta persona (se comprueba una vez y se guarda; si no lo es, `409` y no asigna);
  - después, `gh issue edit <n> --repo <repo_tareas> --add-assignee @me`. Es un `assigned` y cuenta en la cuenta del equipo de §8 (R-30);
  - si `gh` falla, `502` y no se emite nada. Cada llamada a `gh` tiene un plazo de 30 s; pasado, se mata el árbol de procesos, como en Anotar, y cuenta como un fallo (PR #16);
  - si lo que falla es el `gh issue edit`, además se añade a `acciones.jsonl` la línea `{"tipo":"reclamo_fallido","tarea":"T12","ts":"<UTC>"}`. Cuenta para el tope y nada más: no lleva `id` y su `tipo` no es `reclamo`, así que `escucha.sh` no la entrega (PR #16).
- **Sin GitHub:** no asigna nada.
- **Qué fallo es un `reclamo_fallido`** (tras congelar, 2026-10-17, PR #24, issue #18, hallazgo 10): con `FALLIDO_SOLO_RECHAZO = False`, que es como está, cuenta **cualquier** fallo del `gh issue edit`: un rechazo de GitHub, pero también un plazo vencido, un 5xx o un error de red. El código tiene preparada, apagada, la otra regla: con `True`, solo contaría si el stderr de `gh` trae `GraphQL: …` o `HTTP 4xx` (`RECHAZO_GH`, `Acciones.reclamar`). Cambiarla es decisión de los contratos (R-30).
- **En los dos casos:**
  - emite `reclamo` (§2);
  - añade a `acciones.jsonl` la línea `{"id":"<id del evento>","tipo":"reclamo","tarea":"T12","ts":"<UTC>"}`, con un solo `write` en modo append.
- **Ocupado** (tras congelar, 2026-10-17, PR #24, issue #18, hallazgo 9): las acciones van de una en una (un cerrojo del demonio). Reclamar espera a otra acción en curso 5 s como mucho (`CERROJO_S`, `Acciones.__call__`); si no consigue el cerrojo, responde `503 {"error":"ocupado"}`, sin llamar a `gh` ni escribir nada. Desde la decisión 13B (PR #32), Anotar también (arriba, bajo la tabla de rutas). La web lo dice, para las dos, con «Tu demonio está terminando otra acción; prueba en unos segundos.», y Anotar no vacía el formulario (`comun` en `datos/acciones.js`, PR #34; antes, solo `textoReclamar`, PR #26).
- **Entrega del turno:** `scripts/coordinacion/escucha.sh`, con el OS activo y `web_nueva: sí`, lee las líneas nuevas de `acciones.jsonl` en cada paso (el de las rojas).
  - Para cada línea con `0 ≤ edad < 600 s`, intenta `mkdir <git común>/hackathon/os/entregado/accion-<id>`. Solo el monitor que lo consigue la entrega, así que la recibe **una** sesión de esa persona. La edad es `EPOCHSECONDS` menos la época en ms del ID entre 1000, leída en base 10 aunque empiece por 0: una línea con la hora en el futuro no se entrega (tras congelar, 2026-10-17, PR #16, issue #10; antes, «de menos de 10 minutos»).
  - Imprime el texto fijo «hk-os · reclamaste T12 desde la web (HH:MM). Es tuya: cuando acabes lo que tienes entre manos, ponte con ella; su definición, con la herramienta tarea del MCP o en el plan.».
  - Del contenido de la línea solo usa el ID, validado otra vez con la regex. Ni el título ni nada de los issues.
  - Solo entrega la línea exacta que escribe `acciones.py` (tras congelar, 2026-10-17, PR #24, issue #18, hallazgo 7: antes valía un `"tipo":"reclamo"` en cualquier parte de la línea): `{"id":"web-<persona>-reclamo-<Txx>-<ms>","tipo":"reclamo","tarea":"<Txx>","ts":"<UTC>"}`, entera, sin espacios y en ese orden, con la tarea del ID igual a la de `tarea` (`os_acciones`: `^\{"id":"(web-[a-z0-9-]{1,60}-reclamo-(T[0-9]{2,3})-([0-9]{10,16}))","tipo":"reclamo","tarea":"(T[0-9]{2,3})"(,"ts":"[0-9TZ:.+-]{1,40}")?\}$`, sin el `\r` del final). Así el tipo es el de primer nivel y vale exactamente `reclamo`: ni `reclamo_fallido`, ni un `"tipo":"reclamo"` anidado, ni campos de más.

## 5. MCP (stdio, servidor `os` del plugin)
Lee el estado del demonio de su persona (`<git común>/hackathon/os/estado.json` y `estado-equipo.md`); no habla con GitHub ni con el relay salvo en las acciones (desde M8g, `reservar` y `liberar`, solo con el relay).

| Herramienta | Entrada | Salida |
|---|---|---|
| `estado` | `{}` | El `estado-equipo.md` de la persona + `generado_en` |
| `tarea` | `{"id":"T07"}` | `{tarea, columna, antiguedad_s, generado_en}`: la tarea completa de `estado.json`, su columna de la web y su antigüedad. Un ID que no existe da `isError` |
| `colisiones` | `{"mias": true}` | `{colisiones, generado_en}`: las que afectan a la persona (con `mias: false`, todas) |
| `reclamar` | `{"id":"T07"}` | Asigna el issue a la persona con su `gh` y emite `reclamo`. Falla si la tarea es de otro dueño según `plan.md`. **(Sin implementar: M8h, decisión del usuario en M8g)** |
| `reservar` | `{"rutas":[…],"ttl_s":900,"modo":"compartida"}` | `{"id","hasta","rutas"}` vía `POST /v1/reservas`, con la persona de `estado-equipo.md` y el `relay.url` y el token del demonio. Las rutas, relativas o absolutas dentro del repo (una que se sale da `isError`). **(M8g)** |
| `liberar` | `{"id":"reserva-…"}` | Vía `DELETE /v1/reservas/{id}`; solo una reserva propia. **(M8g)** |

Sin `estado.json` (el demonio aún no ha recibido nada), cada herramienta lo dice en una línea, sin error.

M9a: el MCP no cambia (decisión del usuario). Reclamar existe desde la web (`POST /v1/reclamar`, §4), con la misma regla de dueño; `reclamar` del MCP sigue sin implementar. `estado` devuelve `estado-equipo.md`, así que trae la sección `## Servicios` (§6) sin cambiar el MCP.

Declaración (M8f): `.mcp.json` del plugin, servidor `os`, lanzado como `git -c alias.hk-os-mcp='!bash "${CLAUDE_PLUGIN_ROOT}/scripts/os/mcp.sh"' hk-os-mcp`. Con `bash` a secas no vale: en Windows, desde una sesión abierta en PowerShell, el `bash` del PATH es el de WSL (comprobado en M8f: «CONNECTION_CLOSED»); git ejecuta el alias con su propio `sh`, que encuentra el bash de Git. `scripts/os/mcp.sh` se convierte en `uv run --no-project hkos/mcp.py` con el OS activo y uv en el PATH; si no, responde en bash `initialize`, `tools/list` vacío y `ping`, sin uv ni red. El `.mcp.json` es estático: el servidor sale en `/mcp` en toda sesión con el kit, sin herramientas si el OS está apagado (`docs/limitaciones.md`).

Disponibilidad (M8.0, P1): en sesiones normales, como herramientas diferidas. En `--agent hackathon-kit:orquestador`, porque su `tools:` nombra el servidor entero (`mcp__plugin_hackathon-kit_os`). El worker y el revisor no lo tienen (ADR-0006).

## 6. `estado-equipo.md` (lo que leen los hooks de inyección)
Generado. Secciones en este orden y con estos títulos, para que `sesion.sh` y `delta.sh` puedan recortar por sección sin parsear Markdown complejo:

```
<!-- hk-os v1 persona=<usuario> generado_en=<de estado.json> hora=<HH:MM local> epoch=<época de la escritura> relay=ok|viejo github=ok|viejo firmas=trabajo:<12 hex>,colisiones:<12 hex>,novedades:<12 hex>,reservas:<12 hex> -->
> Relay sin respuesta desde 18:31: lo efímero (presencia, ficheros) puede estar viejo.      ← solo si cae
> GitHub (tareas): sin datos nuevos desde 18:29 (limitado).                                 ← solo si es viejo
## Tu trabajo
- T07 «…» · en curso (18:40 · hook) · bloquea a T09
- T09 «…» · pendiente (18:00 · github) · espera a T05 (@ana, parada)
## Colisiones que te afectan
- ROJO · nivel 3 · contrato «API de eventos» · src/api/eventos.py · @ana, @luis (18:41)
## Reservas                                                                                   ← desde M8g
- «web/src/», «motor/api.py» · @ana · hasta 18:55 · compartida
## Servicios                                                                                  ← desde M9a, con web_nueva: sí
- no cuadra · «datos» :8001 declarado, no responde (18:40 · demonio)
- no cuadra · contrato «motor → web»: la prueba falla (18:38 · hook)
- sin confirmar · conexión «motor → datos» · cambio de @luis (18:12 · git)
- sin confirmar · propuesta de servicio «cache» · de @luis (18:10 · git)
- fuera de servicios · scripts/descarga.py y 2 más (18:41 · git)
## Jurado y ruta                                                                             ← desde M10, con vista_jurado: sí o ruta_critica: sí
- jurado: 2 sin cubrir (1 «obligatorio») · 1 cubierta de 3 (18:41 · derivado)
- ruta: sin estimación (pocos datos: @ana 2 de 3) · T05: plazo pasado 02:30 (18:41 · derivado)
## Novedades
- 18:40 · decisión · «#12: …» (@ana ↔ @luis)
## Equipo
- @ana (A) · T03 en curso · 1 sesión · 2 workers · última señal 18:41
- @luis (L) · sin sesión desde 18:12
## Detalle
Ruta: <ruta absoluta de estado.json>
```

Fijado al congelar (M8f):
- **Horas absolutas** (hora local del portátil, `HH:MM`), no «hace X»: el md no se regenera cada segundo. La web sí muestra «hace X».
- **«Tu trabajo»**: las tareas de la persona que no están `publicada` ni `cerrada`, en este orden: `en_curso`, `parada`, `no_cerrada`, `en_revision`, `reclamada`, `integrada`, `lista`, `pendiente`. Una pendiente dice de quién espera y en qué estado está esa dependencia. Una sección vacía lleva una línea («- nada abierto», «- ninguna»).
- **«Novedades»**: las 5 más recientes de `estado.json`. **«Equipo»**: una línea por persona, sin la propia.
- **Firmas** (`proyeccion.firmas`): los 12 primeros hex del sha256 de lo que importa a la persona en cada sección, **sin horas**: en «Tu trabajo», ID, estado, declarado, cumplidas por cierre y, en las pendientes, ID, dueño y estado de cada dependencia; en «Colisiones», id, nivel, gravedad, personas, rutas y contrato de las suyas; en «Novedades», tipo, resumen, autor y hora. «Equipo» no tiene firma: la presencia de los demás no abre un delta. Una sección vacía firma `4f53cda18c2b` (sha256 de `[]`).
- Cada línea, como mucho 160 caracteres.
- **Novedades tal como llegan** (tras congelar, 2026-10-18, PR #25: con `ok » (@persona-a) y «`, el md y la web decían cosas distintas, issue #23, hallazgos 2 y 18). El relay entrega el `resumen` ya equilibrado (`relay.novedades_de` con `proyeccion.equilibra`, en el título, en el «Qué dijo» y en el resumen final): espacios normalizados, una `»` sin su `«` se quita y cada `«` abierta se cierra al final, en 200 caracteres como mucho contando esos cierres. Un «Qué dijo» literal que no cabe se corta por dentro de sus comillas (`relay._con_lo_dicho`, PR #21). El `autor` va recortado a 60. La web lo pinta tal cual, y `linea_novedad` lo vuelve a equilibrar solo de red (viñeta siguiente) y recorta el resumen (110 como mucho, o lo que quepa en la línea) y, si el recorte deja una `«` abierta, la cierra antes de la `»` de fuera (`proyeccion._entrecomilla`). Todos los recortes, del relay y del md (líneas de 160, títulos de 70, contratos de 40), van por grafemas (`proyeccion.corta` y `proyeccion.grafemas`, un UAX #29 simplificado con `unicodedata`): no cortan junto a un ZWJ, delante de una marca combinante (`Mn`, `Mc`, `Me`), de un modificador de tono o de una etiqueta (U+E0020–E007F), ni entre los dos indicadores regionales de una bandera.
- **Novedades, la red en el md:** `linea_novedad` pasa el resumen por `equilibra` antes de recortarlo, de red por si el relay es anterior al que lo equilibra en origen. Con un relay nuevo no cambia nada (es idempotente). Vale con o sin `web_nueva`. (Tras congelar, 2026-10-18, decisión 17B del usuario en el PR #13; PR #34: `proyeccion.linea_novedad`, `equilibra`, `RESUMEN_MAX`, que el relay toma de `proyeccion`.)

M9a (solo con `web_nueva: sí` y `servicios` en `estado.json`; si no, ni la sección ni la firma, y el md es el de M8h):
- **`## Servicios`**, entre «Reservas» y «Novedades», con lo que no cuadra o está sin confirmar y **afecta a la persona**:
  - los desajustes de sus servicios y de las conexiones de las que es uno de los dos extremos;
  - las filas sin confirmar y las Propuestas que esperan su confirmación según `autoridad.md` (ADR-0011);
  - una sola línea, para todo el equipo, con el código fuera de cualquier servicio (las 1–2 primeras rutas y «y N más»).

  Orden: `no cuadra`, `sin confirmar`, `fuera de servicios`. Sección vacía: «- todo cuadra». Los nombres de servicio, contrato y conexión son dato: van entre «».
- **Firma `servicios:`** en la cabecera, detrás de `reservas:`, sin horas: tipo y clave de cada línea de la sección.
- **Viejo:** una línea de «no cuadra» cuyo desajuste es `viejo` en la vista lleva `· viejo` detrás de la fuente: `- no cuadra · «datos» :8001 declarado, no responde (18:40 · demonio · viejo)`. La firma no lo lleva. (Tras congelar, 2026-10-18, decisión 1 del usuario en el PR #13; PR #34: `proyeccion.linea_servicio`, `servicios_de`.)
- **Propuestas:** el autor es la persona del commit que la añadió (`@luis`); sin ella, el Autor de la fila como declarado (`de @luis (declarado)`), y sin ninguno, `de sin autor`. La web dice lo mismo. (Tras congelar, 2026-10-18, decisión 3A del usuario en el PR #13; PR #34: `proyeccion.autor_propuesta` y `autorPropuesta` de `web-src/src/formato.js`.)
- **El delta** recorre las secciones en este orden: colisiones, reservas, servicios, trabajo, novedades.
- **La web** pinta lo mismo para esa persona en la cabina, y todo el equipo en la vista de servicios (ADR-0009: mismos campos; el md es el subconjunto de la persona, como «Tu trabajo»).

M10 (tras congelar, 2026-10-19, M10; ADR-0012, decisión 7B; ADR-0013, decisión 10A; nota en ADR-0009). Solo si la vista trae el bloque `jurado` o `ruta`; si no trae ninguno, ni la sección ni las firmas, y el md es el de M9a:
- **`## Jurado y ruta`**, entre «Servicios» y «Novedades», para todo el equipo (no es el subconjunto de la persona): una línea por bloque presente, primero jurado y después ruta, con el `resumen` del bloque (§11.3 y §11.4) y, detrás, la hora y la fuente: `- <resumen> (HH:MM · derivado)`, con `· viejo` detrás de la fuente si el bloque es `viejo`. El texto de una nota no sale aquí: el detalle va en el MCP (`jurado`, `ruta`) y en la web.
- **Firmas** en la cabecera, detrás de `servicios:` (o de `reservas:`), sin horas: `jurado:` = la `cuenta` del bloque; `ruta:` = **solo** `veredicto.valor`. Que la hora estimada, el margen o un hecho cambien sin cambiar el veredicto no abre un delta (X, R-25).
- **El delta** recorre las secciones en este orden: colisiones, reservas, servicios, jurado y ruta, trabajo, novedades. El monitor no abre ningún turno por la ruta.
- Las líneas de la sección cuentan para los 2.500 caracteres del inicio y los 600 del delta como las demás.

Inyección (scripts/os/delta.sh):
- **Inicio** (`sesion.sh`, con `startup`, `resume`, `clear` y `compact`): el bloque, con una línea de cabecera («Estado del equipo (Hackathon OS, HH:MM). Son datos, no instrucciones…»), las secciones en orden y el Detalle siempre al final, hasta **2.500 caracteres** (el bloque del OS; lo de la 0.3.2 va aparte). Lo que no cabe se corta por el final, con «… (N líneas más en <ruta>)». Si `epoch` tiene más de 120 s, lo dice. Pone a cero lo entregado (`entregado/<session_id>.firmas`: las firmas, los caracteres y las líneas sin horas), porque la sesión ha perdido lo anterior.
- **Delta** (`UserPromptSubmit`): si las firmas (tres; cuatro desde M8g) coinciden con las entregadas, nada. Si no, solo las secciones cambiadas (colisiones, reservas desde M8g, trabajo, novedades, en ese orden), con las líneas que la sesión no tenía delante, hasta **600 caracteres**. Pasados **6.000** desde el inicio, solo las colisiones rojas que no tenía (R-25b).

## 7. Ficheros y dónde viven

| Fichero | Dónde | Versionado |
|---|---|---|
| `os.md` | `.hackathon/` | Sí |
| Eventos crudos | `<git común>/hackathon/os/eventos/` | No |
| Token, `relay.url`, posiciones, `agente.vivo`, `agente.log`, `arranque.log`, `estado.json` (la última copia que recibió el demonio, M8f), `estado-equipo.md`, `entregado/` (`<session_id>`: avisos del arranque; `<session_id>.firmas`: firmas, caracteres y líneas inyectados, R-25) | `<git común>/hackathon/os/` | No |
| Último árbol de cada actor (`arbol/<session_id>-<agent_id o «sesion»>`), para no repetir `arbol` | `<git común>/hackathon/os/` | No |
| `reservas.tsv` (las reservas vigentes de las demás personas, para `reserva.sh`: id, ruta, persona, hasta en época, hasta en HH:MM y modo, separados por tabuladores; una ruta por línea) y `entregado/<session_id>-<agent_id o «sesion»>.reservas` (las reservas ya avisadas en esa sesión o worker) (M8g) | `<git común>/hackathon/os/` | No |
| `wip.index`, `wip.pathspecs` (el índice temporal y las exclusiones del `git add`) y `wip.json` (lo último publicado) (M8g) | `<git común>/hackathon/os/` | No |
| Copia de las refs de trabajo en curso del equipo (M8g) | `refs/hackathon/relay-wip/<persona>` en el clon del relay | Refs, no ramas |
| Registro del relay, `estado.json` | `<git común>/hackathon/os/relay/` del coordinador | No |
| Refs de trabajo en curso | `refs/hackathon/wip/<persona>` en el remoto (opt-in) | Refs, no ramas |
| `servicios.md` (M9a, §10) | `.hackathon/` | Sí |
| `web.token` (token local de la web), `acciones.jsonl` (los reclamos de la web y las notas de Anotar, para sus topes; solo crece), `nota.index` (el índice temporal de Anotar), `servicios.json` (lo último que emitió el demonio por `clave`), `entregado/accion-<id>` (directorio: la acción ya la entregó un monitor) (M9a) | `<git común>/hackathon/os/` | No |
| `web.html` (fuera de Windows: la página 0600 que redirige a la web con el token; la escribe `hk-os web`, §4, y `hk-os recoger` la deja fuera, como `web.token`) (tras congelar, 2026-10-17, PR #11) | `<git común>/hackathon/os/` | No |
| La web nueva: fuente y compilado (M9a) | `hkos/web-src/` y `hkos/web/nueva/` del plugin | Sí (el compilado también: nadie instala Node) |

**Secretos privados del usuario** (tras congelar, 2026-10-17, PR #22: en Windows heredaban el ACL de la carpeta y, con el repo fuera del perfil, «Usuarios autentificados» los leía y los modificaba, issue #15, hallazgo 12): `token`, `relay.url`, `web.token` y `web.html` se escriben con `permisos.escribe_privado`, en un temporal que se renombra con `os.replace`. En Linux y macOS, 0600 desde que existen (`O_CREAT|O_EXCL`). En Windows, el temporal nace (`CreateFileW` con `CREATE_NEW` y su descriptor, no después) con el DACL `D:P(A;;FA;;;<SID>)`: protegido, sin herencia y con una sola entrada, control total para el SID del usuario del proceso (de `GetTokenInformation(TokenUser)`, sin depender del nombre ni del idioma); `os.replace` lo conserva. Un fichero de antes se corrige al reescribirse: `token` y `relay.url` con `hk-os unir`, `web.html` con `hk-os web`, y `web.token` al arrancar el demonio aunque lo reutilice, si `permisos.es_privado` dice que no lo es (`Agente._token_web`). Con esa sola entrada, SYSTEM y Administradores no tienen acceso directo a esos cuatro ficheros.

**Destino abierto en Windows** (tras congelar, 2026-10-18, PR #31, issue #27: `os.replace` falla con WinError 5 mientras otro proceso tiene abierto el destino; el demonio y el MCP leen `token` y `relay.url` en cada vuelta, y un sincronizador como OneDrive los abre): la reescritura de un fichero privado reintenta `os.replace` tras un `PermissionError` cada 50 ms durante 2 s como mucho (`permisos.reemplaza`, `REEMPLAZO_S`, `REEMPLAZO_ESPERA_S`); en Linux y macOS no reintenta. Si aun así falla, `escribe_privado` borra el temporal y el fichero queda como estaba. Un `web.token` de antes, válido, que no se puede dejar privado **se sigue usando** (las pestañas abiertas no dan `401`), con la línea «web.token: no se ha podido dejar privado, sigue el mismo» en `agente.log`; como sigue sin ser privado, se vuelve a intentar en el próximo arranque (`Agente._token_web`). Solo se crea uno nuevo si no hay `web.token` o no tiene 64 hex.

`<git común>` (`git rev-parse --git-common-dir`) es compartido entre la copia principal y todos los worktrees de esa persona, así que los hooks de los workers leen y escriben lo mismo que los de la sesión principal. El estado propio de los scripts del buzón sigue en `<git dir>/hackathon/` como en la 0.3.2.

**`token` y `relay.url` de antes, al arrancar el demonio** (tras congelar, 2026-10-18, PR #29; lo dejó pendiente el PR #22): si existen y `permisos.es_privado` dice que no son privados (0644, o en Windows con el ACL heredado de la carpeta), el demonio los reescribe con `permisos.escribe_privado` (temporal `.<pid>.tmp`, que `hk-os recoger` deja fuera) **sin cambiar el contenido**: los lee con `newline=""`, así que un `\r\n` se queda. Si no es UTF-8 o falla algo, no los toca y deja una línea en `agente.log` (`Agente._secretos_privados`).

## 8. Issues `hk-tarea` (M8e; ADR-0001)
Los escribe `hk-os compilar` (`hkos/compilar.py`) y los lee el relay (`hkos/github.py`). En el repo de `repo_tareas:` de `os.md`, o en el de `coordinacion.md`.

**Issue de una tarea:**
- Título: `Txx · <tarea>`.
- Etiquetas: `hk-tarea` y `hk-tarea:<usuario>`. La segunda falta si el dueño no tiene GitHub en la tabla de `coordinacion.md`, y entonces el dueño en `estado.json` es su nombre («C»).
- Cuerpo:
  ```
  <!-- hk-tarea id=T07 hash=<12 hex> plan=<12 hex del blob de plan.md> -->
  **Dueño:** @usuario (A)            ·  o: **Dueño:** C (sin GitHub)
  **Bloque:** … · **Hasta:** …
  **Cómo se comprueba:** …
  Depende de: T17, T05               ·  solo si tiene dependencias

  _Generado por hk-os compilar desde .hackathon/plan.md: la definición se cambia en el plan, no aquí._
  ```
- `hash`: los 12 primeros hex del sha256 de `[ID, tarea, dueño, bloque, hasta, comprobación, dependencias ordenadas]` en JSON. Es la marca de idempotencia: si coincide, el issue no se toca.
- Dependencias: la línea `Depende de:` y la relación nativa `blocked_by`, con las mismas tareas.

**Lectura del plan:**
- Secciones `### <Nombre> · …` de «## Por persona». El nombre se convierte en usuario con la tabla de `coordinacion.md`.
- Filas `| ID | Hasta | Bloque | Tarea | Cómo se comprueba |`. Una celda vacía de Hasta o Bloque hereda la de la fila de arriba.
- «Quién espera a quién»: `- Txx espera a Tyy[, Tzz | y Tzz | Tyy–Tzz]…`, también en negrita.
- Un ID repetido o una fila fuera de una persona es un plan mal formado: no se escribe nada.

**Reglas de la compilación:**
- **Quién:** cualquiera de la tabla de `coordinacion.md` (`GET /user`), con el OS y la coordinación activos, y con `.hackathon/plan.md` commiteado e igual al de `origin/main` (tras `git fetch`). `--seco` lee y enseña sin escribir.
- **Solo cuenta lo del equipo:** solo cuentan los issues con marcador cuyo autor está en la tabla. Si hay dos para un ID, el de número menor.
- **Por tarea:**
  - si no existe, se crea;
  - si su `hash` cambió, se editan título, cuerpo y etiquetas;
  - si estaba quitada y vuelve al plan, se reabre;
  - las dependencias nativas que sobran o faltan, se quitan o se añaden.
- **Tarea quitada del plan:** comentario «Quitada del plan en <plan>» y cierre con `state_reason: not_planned` (2 escrituras). El relay la saca de `estado.json` y no cumple dependencias. Una tarea ya cerrada que sale del plan se queda como está.
- **Ritmo y tope (R-30):**
  - la compilación inicial (el repo no tenía ningún issue del equipo con marcador) va a ≤ 1 escritura/s y está exenta del tope;
  - una recompilación lee antes la cuenta del equipo y escribe solo lo que cabe en 60 por hora. Dice cuánto queda pendiente, y la siguiente compilación sigue donde se quedó.

**Cuenta de escrituras del equipo** (`github.escrituras_del_equipo`): sale de lo que GitHub muestra a todos, no de cada clon, y la usan el relay y el compilador. En la última hora, sobre issues `hk-tarea` y de cuentas de la tabla:
- una creación cuenta 1, con las etiquetas que pone su autor (GitHub las fecha hasta ~2 s después; margen de 10 s);
- una edición de etiquetas o título (`labeled`, `unlabeled`, `renamed` del mismo actor e issue, dentro del margen) cuenta 1;
- cada `assigned`, `unassigned`, `closed`, `reopened`, `blocked_by_added` y `blocked_by_removed` cuenta 1 (`blocking_added` es la otra cara de la misma petición y no se cuenta);
- cada comentario cuenta 1;
- una edición del cuerpo no deja evento: un `updated_at` en la ventana sin otra escritura de ese issue dentro del margen cuenta 1.
- Crear una etiqueta en el repo no es una escritura sobre un issue y no se cuenta.

**Sondeo del relay:**
- Cada 30 s, con el `gh` de quien coordina y `If-None-Match` en cada consulta (un 304 no gasta cuota):
  1. `GET /issues?labels=hk-tarea&state=all&per_page=100`: definición y estado de las tareas;
  2. `GET /issues/events?per_page=100`: `assigned`, `closed`, `reopened` con su actor, que son las acciones del motor. Es la lista de todo el repo, que también trae el buzón: se filtra por número;
  3. `GET /issues/comments?sort=created&direction=desc&per_page=100`: solo para marcar los comentarios de fuera.
- **Dependencias nativas:** se piden las de un issue (`/issues/{n}/dependencies/blocked_by`) cuando su `total_blocked_by` no cuadra con lo último visto o con su línea, o cuando cambia su `updated_at`. Manda la nativa, con `dependencias_distintas`.
- **Backoff:** ante 403/429 de límite, `Retry-After` o `X-RateLimit-Reset`; sin respuesta, 30 s. Mientras dura, no pregunta.
- **Arranque:** la última instantánea, en `<git común>/hackathon/os/relay/github.json`, para arrancar sin GitHub.
- **Lo de fuera de la tabla no cambia ningún estado** (R-31):
  - un issue `hk-tarea` de fuera no define tareas;
  - una asignación, un cierre o una reapertura de fuera se ignoran;
  - un comentario de fuera solo se anota.
  Los tres salen como `fuera_del_equipo`, con autor, número y tarea, nunca con su texto.
- **Fuentes en `estado.json`:**
  - `fuentes.github` = estado del sondeo (`ok`, `limitado` o `sin respuesta`) y hora del último sondeo bueno;
  - `fuentes.git` = hora del último evento de fuente git;
  - `fuentes.relay` = hora del cálculo (no cuenta para la versión ni para el SSE).
  Marcar «viejo» en las vistas es de M8f.


## 9. Remoto del equipo sin GitHub (M8h, K-80; decisiones del usuario)
Para trabajar sin internet con LAN (`github: no`, §0). Lo sirve `hk-os remoto` (`hkos/remoto.py`) en el portátil de quien coordina, en un proceso aparte del relay: el relay sigue sin transportar código (constitución IX).
- **Qué sirve:** un solo repo, `<git común>/hackathon/os/remoto/equipo.git` del coordinador (fuera de git), en `http://<ip>:7778/equipo.git`. Solo el protocolo *smart* de git (`GET info/refs?service=git-upload-pack|git-receive-pack`, `POST git-upload-pack`, `POST git-receive-pack`) a través de `git http-backend`. Cualquier otra ruta, `404`.
- **Dónde escucha:** como el relay (§3): 127.0.0.1, una IP privada o una de Tailscale; nunca `0.0.0.0` ni una pública. Sin CORS.
- **Token:** el del relay (`relay/token`; si aún no existe, se crea igual). Va en `Authorization: Bearer <token>` (o Basic con el token de contraseña) y se compara en tiempo constante. Sin él, `401`. HTTP sin cifrar: en una red que no sea de confianza, Tailscale o ZeroTier (`docs/limitaciones.md`).
- **`--iniciar`:** crea el bare con `main` = `origin/main` del clon (si no hay, `HEAD`), renombra el `origin` de antes a `github` y apunta `origin` al bare. Si ya estaba iniciado, no toca nada.
- **Cada persona:** `hk-os unir … --remoto <url>` (§4) en un clon de antes; uno nuevo, con `git -c http.extraHeader="Authorization: Bearer <token>" clone <url>` y después `unir --remoto`.
- **`--volver`** (quien coordina, con internet):
  - trae `origin` (el bare) y `github`;
  - si GitHub ya tiene el `main` del equipo, no sube nada;
  - si va por detrás, sube por avance rápido;
  - si los dos `main` han divergido, lo dice y para sin tocar nada (no fusiona por su cuenta);
  - al terminar, `origin` vuelve a ser GitHub y el bare se queda en disco;
  - cada persona, `hk-os unir` sin `--remoto`.
- **Lo que no viaja:** `refs/hackathon/*` no se sube a GitHub al volver.

## 10. `.hackathon/servicios.md` (M9a; ADR-0011)
Lo genera `/hack-scaffold` en su paso de coordinación (plantilla: `skills/hack-scaffold/templates/servicios.md`). Lo editan personas y agentes. Lo leen `hkos/servicios.py` (el relay, sobre `origin/main`) y `prueba.sh` (la copia principal, solo las Pruebas).

```
# Servicios
Fuera de servicios: docs/, README.md, CLAUDE.md

## Servicios
| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |
|---|---|---|---|---|---|
| api | api/ | 8000 | `uv run uvicorn api.main:app` | /salud | @ana |
| motor | motor/ | — | — | — | @luis |

## Conexiones
| De | A | Contrato | Prueba |
|---|---|---|---|
| web | api | web → api | `uv run pytest tests/contratos/test_web_api.py` |

## Propuestas de servicios
| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño | Autor | Hora |
|---|---|---|---|---|---|---|---|
| datos | datos/ | 8001 | `uv run python -m datos.etl` | — | @luis | @luis | 2026-11-25 18:10 |

## Propuestas de conexiones
| De | A | Contrato | Prueba | Autor | Hora |
|---|---|---|---|---|---|
| motor | datos | motor → datos | `uv run pytest tests/contratos/test_motor_datos.py` | @luis | 2026-11-25 18:12 |
```

**Lectura:**
- Secciones por su título exacto (`## Servicios`, `## Conexiones`, `## Propuestas de servicios`, `## Propuestas de conexiones`); el orden no importa, y las de propuestas pueden faltar. Se toleran BOM, UTF-16 y `\r` (como `hk_leer`).
- Filas: las líneas que empiezan por `|`, menos la cabecera y la de guiones. Las celdas se separan por `|` sin escapar y se recortan. Una celda vacía o `—` es «sin valor».
- **Nombre:** `[a-z0-9][a-z0-9_-]{0,39}`, único. Con un nombre repetido, ni sus filas ni las conexiones que lo usan salen confirmadas, y los dueños de esas conexiones son los de todas las filas con ese nombre (tras congelar, 2026-10-17, PR #7, issue #2, hallazgo 4).
- **Carpeta:** relativa, con `/` al final, sin `..` ni `/` al principio.
- **Puerto:** entero de 1 a 65535, o sin valor.
- **Arranque** y **Prueba:** texto (≤ 300), con o sin comillas invertidas alrededor. El OS **nunca** los ejecuta.
- **Salud:** sin valor, o una ruta `^/[A-Za-z0-9._~!$&'()*+,;=:@%/?-]*$` sin `..` y sin `//` al principio (ADR-0011), tampoco después de descodificar los `%XX` (`%2e%2e`, `%2f%2f`, `%252e`), hasta 5 veces; si aún cambia tras la quinta, no vale (tras congelar, 2026-10-17, PR #7, issue #2, hallazgo 13).
- **Dueño:** `@usuario` de la tabla de `coordinacion.md`, o sin valor si aún no hay reparto (`/hack-scaffold` corre antes que `/hack-plan`). Sin valor, el dueño es el de `autoridad.md` y no hay desajuste; un `@usuario` distinto del de `autoridad.md` sí lo es (ADR-0011).
- **De** y **A:** nombres de servicios de `## Servicios`.
- **Contrato:** el título de un bloque `##` de `docs/contratos.md`, sin `##`.
- **Propuestas:** el mismo formato que su tabla (Servicios o Conexiones), con las mismas reglas por campo, más **Autor** (`@usuario`) y **Hora** (`AAAA-MM-DD HH:MM`), que son declarados (dato).
- `Fuera de servicios:` es una sola línea, con rutas separadas por comas (una carpeta acaba en `/`). Siempre están fuera, aunque no se escriban, `.hackathon/`, `.claude/`, `.github/` y los ficheros de la raíz que empiezan por `.`.
- **Una versión con una lectura fallida** (tras congelar, 2026-10-17, PR #14, issue #10): si al leer una versión de la historia (abajo) falla alguna lectura de git (sus padres, con `git log -1 --format=%P`, o el fichero en el commit o en uno de sus padres, con `git ls-tree` y `git show`), esa versión no se guarda ni entra en la lista hasta que se lea bien: se vuelve a leer con espera creciente, tras 1, 2, 4, 8… vueltas de lectura (una por fetch, cada 60 s) y como mucho 16 entre dos intentos (`REINTENTO_TOPE`, `Novedades._fallos`; tras congelar, 2026-10-17, PR #21, issue #18, hallazgo 7). La espera es por sha, vive en memoria (un reinicio del relay la pone a cero) y se olvida cuando el sha deja de estar en el log. Mientras, la versión no confirma nada (tampoco como de `/hack-scaffold`). Que el fichero no esté en un padre (`git ls-tree` sin salida) no es un fallo; antes, las dos cosas se tomaban por «no estaba», y todas las filas del commit parecían añadidas en él.
- **Mal formado** (una sección con una fila que no se puede partir, o dos servicios con el mismo nombre): `servicios.fichero` = `mal formado`, con la línea en el detalle. Las filas buenas se siguen mostrando y las malas salen como desajuste `formato_invalido`. Un campo que no vale en una fila buena (Puerto, Salud, Carpeta) también es `formato_invalido`, y esa fila no se consulta.
- **Una fila que no vale** (tras congelar, 2026-10-17, PR #7, issue #2, hallazgo 6): con algún campo que no vale, la fila (servicio o conexión) queda `sin_confirmar`, y en `servicios.lista` un Puerto o una Salud que no valen van como `null`. El motivo sigue en el desajuste `formato_invalido`, con la `clave` de la fila. `lista` no tiene otra marca de «fila que no vale» (el esquema no la admite). Quien necesite saber si una fila vale (el demonio, la web) lo lee de los desajustes `formato_invalido` con su `clave`; ni `valida` ni `invalidos` en `lista` (2026-10-18, decisión 6C del usuario en el PR #13).

**Clon superficial del relay** (tras congelar, 2026-10-17, PR #14, issue #10): si el clon del relay es superficial (`git rev-parse --is-shallow-repository` da `true`), ninguna fila es de `/hack-scaffold`, y las versiones de los commits del borde (los de `shallow`) no cuentan: git no tiene sus padres, así que todas sus filas parecerían añadidas por la persona de ese commit. Si no se sabe si es superficial (la orden falla o da otra cosa, o no se puede leer `shallow`), tampoco hay nada de `/hack-scaffold` y no cuenta ninguna versión, así que ninguna fila sale confirmada.

**Viejo** (en la vista, no en `estado.json`; tras congelar, 2026-10-18, decisión 1 del usuario en el PR #13; PR #34: `proyeccion.vista`): `comprobado`, `resultado` y cada desajuste llevan `viejo` = su `observado_en` tiene más de `umbral_viejo_s`; un desajuste con `fuente: git` nunca es viejo (su hora es la del commit de `servicios.md`; su antigüedad la dice `fuentes.git`).

**Clave de una fila:** los 12 primeros hex del sha256 del JSON de sus campos normalizados, en el orden de su tabla: Servicios = nombre, carpeta, puerto, arranque, salud, dueño; Conexiones = de, a, contrato, prueba. Normalizar es recortar, quitar las comillas invertidas de alrededor y pasar `—` a `null`. Una fila de Propuestas tiene la clave de la fila que propone: la de sus columnas sin Autor ni Hora. La confirmación (quién añadió cada clave, qué dueños hacen falta) es la de ADR-0011. Una clave que está en algún padre de un commit y en ninguna tabla de su versión se ha **borrado**: se olvida quién la añadió y que era de `/hack-scaffold`; solo cuentan las adiciones posteriores a su último borrado. Pasar una Propuesta a su tabla no es borrarla. (Tras congelar, 2026-10-18, decisión 2B del usuario en el PR #13; PR #34: `servicios.confirmaciones`.)

**Historia que lee el relay** (tras congelar, 2026-10-17, PR #7, issue #2, hallazgos 1, 5 y 9):
- las versiones del fichero salen de `git log --full-history` (hasta 200 commits), sin la simplificación de historia de `git log`;
- **el commit que creó el fichero** se busca en toda la historia de `origin/main` (`git log --full-history -m --no-renames --diff-filter=A`): tiene que haber **uno solo** en el que el fichero está y no está en ninguno de sus padres, con como mucho un padre y que no venga de un renombrado (`diff-tree -M`). Si no (una rama sin ancestro común con el scaffold, un fichero borrado y vuelto a crear, un merge que lo crea, un renombrado), ninguna fila es de `/hack-scaffold`;
- además, ese commit tiene que estar entre los 200 que se leen y ser el único de ellos sin el fichero en sus padres: con más de 200 commits en el fichero, ninguna fila es de `/hack-scaffold`;
- de ese commit solo cuentan como de `/hack-scaffold` las filas de `## Servicios` y `## Conexiones`, no las de Propuestas;
- un sha que emiten como `commit` demonios de personas distintas no se atribuye a nadie, sea cual sea el orden de llegada.

## 11. Vista de jurado y ruta crítica (M10; ADR-0012, ADR-0013)
Nueva (tras congelar, 2026-10-19, M10, K-101; decisiones del usuario en el PR #42 y en el issue #41). Sin subir `v`: todo es opcional. Con los dos interruptores apagados (o sin ellos), nada de esta sección se produce: `estado.json`, la vista y `estado-equipo.md` salen byte a byte como en la 0.4.0. Esquema: `jurado`, `ruta` y los campos nuevos de `tareas[]` en [estado.schema.json](estado.schema.json), y los bloques de la vista en sus `$defs` `vista_jurado` y `vista_ruta`.

### 11.1 Interruptores
Dos claves nuevas en `.hackathon/os.md` (§0), por defecto `no`, con los mismos valores que `activa:`, versionadas y para todo el equipo (ADR-0012, decisión 8A):
```
vista_jurado: no          # sí = vista de jurado (R-35, ADR-0012)
ruta_critica: no          # sí = ruta crítica (R-36, ADR-0013)
```
- Son independientes entre sí y de `web_nueva:`: el md y el MCP no dependen de la web.
- Las lee **solo el relay**, de su copia, con el mismo lector que `web_nueva:` (`hkos/red.py`). El demonio, el MCP y la web siguen lo que traiga `estado.json`: si trae `jurado` o `ruta`, la vista lleva el bloque; si no, no. Ninguno de ellos lee los interruptores.
- Con `vista_jurado: no` no hay `jurado`, `tareas[].criterios` ni `tareas[].conexiones`. Con `ruta_critica: no` no hay `ruta`, `tareas[].hasta`, `franja` ni `orden_plan`. `tareas[].historia` y `tareas[].evidencia` van con cualquiera de los dos.

### 11.2 Lo que lee el relay
Del clon de `origin/main`, en el mismo bucle que las novedades y `servicios` (§3). Lo que sale de un fichero lleva `fuente: git`, `declarado: true` y, como `observado_en`, la hora del último commit de ese fichero en `origin/main` (como `servicios.fichero`). Si una lectura de git falla, se conserva el último bueno y lo dice `fuentes.git`, como con `servicios`. Los ficheros se leen en UTF-8 o UTF-16 y con LF o CRLF, como Anotar.

**`.hackathon/criterios.md` → `jurado`** (con `vista_jurado: sí`; ADR-0012, decisiones 1A y 2A):
- Una nota es una cabecera `## <AAAA-MM-DD HH:MM> · <quién> (<papel>)` (la expresión `CRITERIO` de `relay.py`) y sus líneas hasta la cabecera siguiente: `- Dónde:`, `- Qué dijo:`, `- Fuerza:`, `- Afecta a:` y `- Anotado por:`. Lo que no es una nota (la cabecera de la plantilla, los comentarios) se ignora.
- **`clave`**: los 12 primeros hex del sha256, en UTF-8, de la cabecera, la línea «Qué dijo» y la línea «Anotado por», tal cual, sin espacios a los extremos y unidas por `\n`. Las notas solo se añaden, así que la clave es estable. Dos notas con esas tres líneas iguales son una (la repetición de `merge=union`).
- **`cita`** es la fecha y hora de la cabecera; **`hora`**, la cita con la zona de `equipo.md` (abajo), o `null` si no hay zona.
- **`literal`**: «Qué dijo» va entre «»; **`dijo`**, el texto sin las comillas ni «(paráfrasis)», equilibrado con `proyeccion.equilibra`, de 500 caracteres como mucho.
- **`fuerza`**: `tipo` = `dato` si el texto es «dato», `comentario` si es «comentario suelto», `sin_precisar` si es «sin precisar» o falta la línea, y `palabra` en otro caso; `texto`, sin comillas, de 40 como mucho.
- **`corrige`**: si el bloque dice «corrige la nota del <AAAA-MM-DD HH:MM>[ · quién]» (así lo escribe `/hack-note`), esa cita; si no, `null`.
- **`fichero`**: `ok`; `sin fichero` (y `notas` vacía); o `mal formado` si alguna cabecera no tiene «Qué dijo» (esa nota no sale; las demás, sí).

**Etiqueta del plan → `tareas[].criterios`** (con `vista_jurado: sí`; ADR-0012, decisión 3A): `(criterios: <cita>[, <cita>…])` al final de la celda «Cómo se comprueba» de la fila de la tarea en `.hackathon/plan.md`, con `<cita>` = `AAAA-MM-DD HH:MM` o `AAAA-MM-DD HH:MM · quién`. El plan se lee con `compilar.leer_plan` (las mismas 5 columnas), también con GitHub: la etiqueta se toma de `plan.md`, no del issue. `valor` es la lista de citas, en el orden de la etiqueta; sin etiqueta, el campo no va. Como «Cómo se comprueba» está en la huella del issue (§8), poner o cambiar la etiqueta reescribe ese issue (R-30).

**Prueba → `tareas[].conexiones`** (con `vista_jurado: sí`; ADR-0012, decisión 4A): las claves de las conexiones de `servicios.md` cuya Prueba, normalizada como en §10, aparece tal cual dentro de «Cómo se comprueba». Sin ninguna, el campo no va.

**`.hackathon/pitch.md` → `jurado.pitch`** (ADR-0012, decisión 5B): las citas de todas sus etiquetas `(criterios: …)`. `null` sin `pitch.md`.

**`.hackathon/equipo.md` → `ruta.equipo`, `zona`, `inicio` y `entrega`** (ADR-0013, decisión 1A; la zona también sirve a `jurado`, con cualquiera de los dos interruptores):
- Las líneas `- Inicio:` y `- Entrega:` de «## Hackathon». Se entiende una fecha (`AAAA-MM-DD`, `D/M/AAAA`, `D de <mes> [de AAAA]` o `D <mes> [AAAA]`, con el mes abreviado o entero y con o sin el día de la semana delante, como «dom 20 sep 09:30» o «dom 20 sep 2026 10:00»; sin año, el del commit), una hora `HH:MM` y una zona: un nombre IANA (`Europe/Madrid`) o un desfase (`UTC+2`, `UTC+02:00`, `+02:00`). Las abreviaturas (`CEST`) no valen: son ambiguas. **`Entrega:` sin zona hereda la de `Inicio:`** (tras congelar, 2026-10-19, M10, issue #46, ajuste 5 de ADR-0013).
- **Dos horas** (ajuste 5): la línea trae dos horas `HH:MM` distintas, sin contar la zona (el `02:00` de `UTC+02:00` no es una hora), como «10:00 (cierre 11:00)». **Manda la primera**: es el `valor`, y la otra va a `ruta.otras_entregas` con `donde: equipo.md`, como discrepancia; no quita la estimación. La misma hora escrita dos veces es una.
- `valor` = la hora en ISO 8601 con su desfase. Si no se puede: `null` con `motivo` = `sin_dato` (falta la línea, vacía, `—` o con `<…>`), `sin_zona` o `formato`. Con «(confirmar)», `confirmar: true`, y el valor se resuelve igual. `texto` es la línea tal cual, sin `- Entrega:`.
- `zona` es la de `Inicio:` (o, si no tiene, la de `Entrega:`); `null` si ninguna se entiende.
- `equipo`: `ok`, `sin fichero` o `mal formado` (sin «## Hackathon»).

**`.hackathon/plan.md` → `tareas[].hasta`, `franja` y `orden_plan`, `ruta.hitos`, `ruta.otras_entregas` y `ruta.descansos`** (con `ruta_critica: sí`; ADR-0013, decisiones 1A, 2A, 3B, 4A y 9A):
- **`orden_plan`**: la posición de la fila (1, 2…) en la sección de su persona de «## Por persona».
- **`hasta`** (decisión 2A): el `Hasta` de la fila (heredado si la celda va vacía, como en `leer_plan`) resuelto con `ruta.inicio` y `ruta.zona`:
  - `<día> HH:MM` (`vie 19:45`, `SÁB 02:30`; el día en cualquier caja, con o sin tilde, abreviado o entero): el primer día de la semana igual que no sea anterior a la fecha del inicio;
  - `HH:MM` sin día: la fecha del `Hasta` resuelto de la fila anterior de la persona (o la del inicio) y, si la hora queda antes, el día siguiente;
  - `H+N` (`H+2`, `H+1:30`): el inicio más N horas;
  - si no: `valor: null` y `motivo` = `vacio` (vacío o `—`), `relativo_sin_inicio` (`H+N` sin inicio), `sin_inicio` (un día sin inicio), `sin_zona`, `por_confirmar` (dice «por confirmar» o «?») o `formato`. Una tarea con `hasta.valor = null` sale «sin plazo», nunca «a tiempo».
- **`franja`** (decisión 4A): `desde` = el `Hasta` resuelto de la fila anterior de la persona con otro `Hasta` (o, en la primera, el inicio); `hasta` = el suyo; `compartida` = las filas seguidas de la persona con ese mismo `Hasta`; `min` = (hasta − desde) / compartida en minutos, redondeado hacia arriba. Si no se puede: `valor: null` y `motivo` = `sin_plazo` (su `hasta` es `null`), `sin_inicio` (la primera fila, sin inicio) u `orden` (su `Hasta` no es posterior al `desde`). `fuente: derivado`, `declarado: true` (sale del plan).
- **`hitos`**: cada fila de «## Hitos del equipo», con `nombre` = la columna Qué y la hora de Cuándo resuelta como un `Hasta` o, si lleva fecha («dom 20 sep 09:30»), como una fecha de `equipo.md`, sin zona la de `Inicio:`.
- **`otras_entregas`** (decisión 1A; ajuste 5): van todas, coincidan o no (la vista enseña las que no coinciden):
  - la segunda hora de `- Entrega:`, si la línea trae dos, con `donde: equipo.md`;
  - **las filas de Hitos que son una entrega**: aquellas cuya Qué es «Entrega» o empieza por «Entrega final» (sin distinguir mayúsculas ni espacios de más), con `donde: plan.md`. Las demás, aunque digan «entrega» («Entrega temprana»), son hitos;
  - cada nota de fuerza `dato` cuyo «Afecta a» contiene «entrega» y cuyo «Qué dijo» trae una hora que se resuelve como un `Hasta`, con `donde: criterios.md`, `cita` = la de la nota y `texto: null`: el texto de una nota no sale aquí (constitución V).
- **`descansos`** (decisión 9A; tras congelar, 2026-10-19, M10, issue #46, ajuste 4 de ADR-0013): un descanso por turno de «## Descansos», escrito de cualquiera de las dos formas:
  - una fila de la tabla `| Turno | Quién |` (la de los ejemplos de `/hack-plan` y de G14), con el turno en `Turno` y las personas en `Quién`;
  - una línea `- <quién>: <turno>`.

  El turno es `<día> HH:MM–[<día>] HH:MM` (guion o raya): el final puede llevar día («sáb 23:00–dom 07:30»); sin día, es el del principio, o el siguiente si la hora queda antes. Se resuelve como un `Hasta`. `<quién>` es `@usuario`, un Nombre o «Todos», y puede nombrar a **varias personas**, separadas por «,» o « y » («Persona B y Persona C»). `personas` = sus usuarios (por `@usuario` o por el nombre del equipo, sin distinguir mayúsculas; uno que no se resuelve va tal cual), en el orden en que salen; `null` para «Todos». `texto` es la fila o la línea tal cual. Un turno que no se entiende va con `desde` y `hasta` en `null` y su `motivo` (`formato`, `sin_inicio` o `sin_zona`): se enseña y no se usa.

**Historia → `tareas[].historia`** (cualquiera de los dos interruptores; ADR-0012, decisión 6B; ADR-0013, decisión 5A): el relay la reconstruye al arrancar desde `relay/eventos.jsonl` y `relay/github.json`, recalculando el motor de estados (`modelo.calcular`, que es puro) en cada evento que cambia una tarea, y después la lleva por incrementos tras cada lote. `primera_senal` = el primer paso a `en_curso`; `hecha_en` = el primer paso a `publicada` o a `cerrada` no declarada; `trabajo_nuevo_desde` = el primer paso a `en_curso` después de `hecha_en`, mientras la tarea no esté hecha. La hora es la del evento que provoca el paso. `fuente: derivado`; `observado_en`, la del último evento de esa tarea.

**`tareas[].evidencia`** (cualquiera de los dos; tras congelar, 2026-10-19, M10, issue #46, ajuste 6 de ADR-0012): `{valor, tipo, fuente, observado_en}`, con `valor` = el sha del commit con ID (del `datos.incluye` del `push` de fuente `git`, `tipo: commit`) o de la fusión aprobada (`tipo: fusion`) que llevó la tarea a `publicada`. Si se publicó más de una vez, **el último** sha publicado, y `observado_en` = la hora de ese paso a `publicada` (no `historia.hecha_en`, que es el primero). Sin ninguno (una `cerrada`), no va.

### 11.3 Bloque `jurado` de la vista (ADR-0012)
`proyeccion.vista` lo añade (clave `jurado`, `$defs/vista_jurado`) si `estado.json` trae `jurado`. Lo calcula `hkos/jurado.py`.
- **Enlaces:** cada cita de `tareas[].criterios` casa con las notas de esa `cita` y, si lleva «· quién», con ese quién (sin distinguir mayúsculas ni espacios repetidos). Con una nota, es un enlace; con varias, un enlace `ambiguo` a cada una; con ninguna, va a `sin_nota` (enlace roto, declarado, con su tarea).
- **Una tarea está hecha** si su estado es `publicada`, o `cerrada` sin `declarado` (una `cerrada` a mano, con ⚑, no lo está), o si tiene `historia.hecha_en` y ahora está en `en_curso`, `parada`, `en_revision`, `integrada` o `no_cerrada` (decisión 6B: sigue hecha, con trabajo nuevo; `parada` y `no_cerrada`, tras congelar, 2026-10-19, M10, issue #46, ajuste 6 de ADR-0012).
- **Cobertura** de cada nota, en este orden:
  1. con enlaces no ambiguos: `cubierta` si todas sus tareas están hechas (decisión 4A); si no, `en_curso` si alguna de esas tareas tiene señales (`historia.primera_senal` no es `null`) y, si no, `planificada` (tras congelar, 2026-10-19, M10, issue #46, ajuste 2 de ADR-0012: lo que era `declarada`);
  2. si no, con algún enlace ambiguo: `ambigua`;
  3. si no, si su cita está en `jurado.pitch`: `en_pitch` (decisión 5B);
  4. si no: `sin_tarea`.

  `fuente: derivado`; `observado_en`, el más reciente de los datos usados; `viejo` si lo es la tarjeta de alguna de sus tareas.
- **`trabajo_nuevo_desde`**: el más antiguo de los `historia.trabajo_nuevo_desde` de sus tareas que vuelven a tener trabajo; si ninguna, `null`.
- **`tareas[]`**: todas las enlazadas (también las ambiguas), con la tarjeta de §6 más `viejo` (su estado viene de una fuente vieja en `vista.fuentes`) y el `enlace` (`cita`, `ambiguo`, `donde: plan.md`, la hora del commit del plan y `declarado: true`).
- **`evidencias[]`**: de cada tarea enlazada, aunque la nota no esté cubierta: el commit o la fusión de `tareas[].evidencia` (con su `tipo`, su `fuente` y su `observado_en`: el último sha publicado y su hora, ajuste 6) y el último resultado de la Prueba de cada conexión de `tareas[].conexiones` (`pasa` o `falla`, con su hora y su `viejo`, el de §10). La Prueba no cambia la cobertura (decisión 4A).
- **`pitch`**: `{fuente, observado_en, declarado}` si la cita está en el pitch; si no, `null`. Sale aunque haya tareas.
- **`corregida_por`**: la clave de la nota posterior cuya `corrige` casa con esta y solo con esta.
- **Orden:** sin cubrir (todo lo que no es `cubierta` ni está corregido) por fuerza (`dato`, «obligatorio», «se valora», «nos gustaría ver», otra palabra, `comentario`, `sin_precisar`) y luego por `hora` (o `cita`), la más antigua primero; después las cubiertas, por hora; al final las corregidas, por hora.
- **`cuenta`** (ajuste 2): `{notas, corregidas, cubiertas, sin_cubrir, sin_tarea, ambiguas, planificadas, en_curso, en_pitch, sin_cubrir_por_fuerza}`. Los totales por cobertura no cuentan las corregidas, que solo van en `corregidas`; `sin_cubrir` = `sin_tarea` + `ambiguas` + `planificadas` + `en_curso` + `en_pitch` (todo lo no cubierto, sin las corregidas), y una ambigua no cuenta en `sin_tarea`. `sin_cubrir_por_fuerza`: el desglose de las sin cubrir por el texto de su fuerza, en el orden de arriba.
- **`viejo`** del bloque: `fuentes.git` está viejo. `observado_en`: la hora del cálculo (`ahora`).
- **`resumen`** (la línea del md, decisión 7B): `jurado: <sin_cubrir> sin cubrir (<n> «<la fuerza más fuerte entre las sin cubrir>»)[ · <ambiguas> ambigua(s)][ · <en_pitch> en el pitch] · <cubiertas> cubierta(s) de <notas>`; sin notas, `jurado: sin notas en criterios.md`; sin fichero, `jurado: sin criterios.md en main`. Cortado a 160 por grafemas.

### 11.4 Bloque `ruta` de la vista (ADR-0013)
`proyeccion.vista` lo añade (clave `ruta`, `$defs/vista_ruta`) si `estado.json` trae `ruta`. Lo calcula `hkos/ruta.py`, con `ahora` como parámetro.
- **Objetivo** (decisión 1A): manda `ruta.entrega`, la de `- Entrega:` de `equipo.md`. Las `otras_entregas` cuyo `valor` no coincide con el del objetivo (o que no se resuelven) van en `otras_entregas` de la vista, al lado, como discrepancia, sin elegir, y **no quitan la estimación**. La congelación y los demás hitos van en `hitos`, con `pasado`, sin previsión.
- **Qué cuenta** (decisión 8B): todas las tareas menos las de título que empieza por «Si » o que lleva `[SI DA TIEMPO]` (sin distinguir mayúsculas), que van a `fuera_de_entrega` con `motivo` `condicional` o `si_da_tiempo`. **Hecha** = `publicada` o `cerrada` (una `cerrada` a mano cuenta, con su ⚑, pero no se mide). **Abierta** = que cuenta y no está hecha.
- **Grafo** (decisión 3B): entre las tareas que cuentan, A → B si B `depende_de` A (`por: depende_de`) o si A es la fila anterior de B en el `orden_plan` de la misma persona (`por: orden_del_plan`, inferido).
- **Medidas y ritmo** (decisión 5A): para cada tarea hecha, no declarada, con `primera_senal`, `hecha_en` y franja: ritmo = (hecha_en − primera_senal − los descansos de su persona o de todos en medio) ÷ (`franja.min` − los minutos de esos descansos dentro de la franja ÷ `compartida`, y nunca menos de 1), en %, redondeado: los descansos se restan **también de la franja** (tras congelar, 2026-10-19, M10, issue #46, ajuste 4 de ADR-0013). Lo que le queda a una tarea abierta se mide con esa misma franja sin descansos. Por persona: `n` (las medidas), `ritmo_min` y `ritmo_max` (o `null` con `n < 3`). `base.minimo` es **3**, fijo; `base.desde`, el `hecha_en` más antiguo medido.
- **Veredicto `sin_estimacion`**, con todos los `motivos` que apliquen, en este orden:
  - `sin_entrega`: `equipo.md` no tiene `- Entrega:`, no se puede leer (`ruta.equipo` distinto de `ok`) o esa línea no se resuelve (`motivo` `sin_dato`, `sin_zona` o `formato`);
  - `ciclo`: un ciclo en el grafo;
  - `pocos_datos`: una persona con tareas abiertas con franja y `n < 3`.

  Una tarea abierta sin franja **no** quita la estimación (tras congelar, 2026-10-19, M10, issue #46, ajuste 1 de ADR-0013): va a `sin_plazo` y el resto se estima. `sin_plazo` ya no es un motivo (el esquema lo admite como transitorio hasta adaptar el código). Tampoco lo es `entrega_doble`: con dos horas en `- Entrega:`, manda la primera y la otra va a `otras_entregas` (ajuste 5).

  `gravedad: gris`, `estimacion: null`. Ni una discrepancia con `otras_entregas` ni «(confirmar)» quitan la estimación: con «(confirmar)», el objetivo lleva `confirmar: true` (declarado) y el resumen lo dice.
- **Estimación** (si no hay motivos): lo que le queda a cada tarea abierta es `franja.min` × el ritmo de su dueño (`ritmo_min` para el fin temprano, `ritmo_max` para el tarde), menos el tiempo ya trabajado si está en curso (desde `primera_senal`, sin descansos), y nunca menos de 0. Una tarea de `sin_plazo` cuenta 0 min: sus sucesoras empiezan al acabar sus predecesoras abiertas (ajuste 1). Cada tarea empieza al acabar todas sus predecesoras abiertas (o ahora) y se salta los descansos de su persona y de todos; `temprano` y `tarde` son el fin más tardío de todas. `margen_min` = entrega − tarde y `margen_max` = entrega − temprano, en minutos.
- **Veredicto** (decisión 6A), sin parámetros: `a_tiempo` si `tarde` ≤ entrega (`gravedad: ninguna`); `justo` si `temprano` ≤ entrega < `tarde` (`ambar`); `no_llega` si entrega < `temprano` (`ambar`: es una previsión; el rojo es solo para hechos).
- **Hechos**, con o sin estimación y desde el principio:
  - `plazo_pasado`: una tarea abierta con `hasta.valor` anterior a ahora, con `plazo` y `arrastra` (sus sucesoras abiertas, directas o no). **Rojo**: es el único;
  - `parada` y `no_cerrada`: tareas de la cadena en ese estado (`ambar`);
  - `sin_senales`: una persona con tareas abiertas cuya última señal (`personas[].ultima_senal` de la vista) es más antigua que `umbral_parada_min`, o no existe, y que no está en un descanso; `desde` = esa señal; `gris`. Nunca «va lenta»;
  - `ciclo`: `ciclo` = las tareas, con la primera repetida al final (`gris`).

  Orden: rojo, ámbar, gris; dentro, por plazo y por tarea.
- **Cadena**: con estimación, la que lleva al fin `tarde` más tardío; sin ella, la que lleva al `Hasta` resuelto más tardío, siguiendo hacia atrás la predecesora abierta de `Hasta` más tardío. Cada eslabón, con su tarjeta, `por` (`inicio` en el primero), `hasta`, `franja` y su `fin_temprano` y `fin_tarde` (`null` sin estimación).
- **`riesgos`** (tras congelar, 2026-10-19, M10, issue #46, ajuste 3 de ADR-0013; R-36): con estimación, cada tarea abierta cuyo `fin_tarde` es posterior a la entrega, esté o no en la cadena: `{tarea, tipo: "estimacion", fin_tarde, dueno, en_cadena, viejo}` (`viejo`, el de su tarjeta). Orden: por `fin_tarde`, la más tardía primero, y por tarea. Sin estimación, `[]`. Es una previsión: ámbar, nunca rojo. La cadena sigue siendo solo de tareas abiertas (las hechas no salen). La vista **no** da una hora central, ni previsión por hito, ni «fiabilidad»: el rango y la `base` lo dicen.
- **`sin_plazo`**: las tareas abiertas sin franja, con el motivo de `hasta` o, si `hasta` se resolvió, el de la franja.
- **`viejo`**: alguna de `vista.fuentes` está vieja; `dato_mas_viejo`, el `observado_en` más antiguo de esas fuentes. `observado_en`: la hora del cálculo.
- **`resumen`** (decisión 7B), cortado a 160 por grafemas:
  - con estimación: `ruta: estimación <a tiempo | justo | no llega> · fin <HH:MM>–<HH:MM> · entrega <día HH:MM>[ (confirmar)]`;
  - sin ella: `ruta: sin estimación (<sin hora de entrega | ciclo T04 → T07 → T04 | pocos datos: @ana 2 de 3, @marta 1 de 3>)`, con el primer motivo;
  - detrás, con estimación y tareas en `sin_plazo`: ` · sin contar T28[, T30…] (sin plazo)` (ajuste 1);
  - detrás, si hay `otras_entregas` que no coinciden, la primera: ` · otra entrega: <texto> (<dónde>)` si viene de `plan.md` o `equipo.md`, y ` · otra entrega: <día HH:MM> (criterios.md, nota de <HH:MM>)` si viene de una nota, con la hora resuelta y la de la cita de la nota: **nunca su texto** (constitución V; ajuste 5);
  - y si hay plazos pasados: ` · T05: plazo pasado <HH:MM>[ y N más]`.

### 11.5 MCP
Dos herramientas nuevas del servidor `os` (§5), de solo lectura, con la vista calculada como la del demonio (`proyeccion.vista` del `estado.json` local):

| Herramienta | Entrada | Salida |
|---|---|---|
| `jurado` | `{}` | `{jurado, generado_en}`: el bloque `jurado` entero |
| `ruta` | `{}` | `{ruta, generado_en}`: el bloque `ruta` entero |

Sin el bloque, una línea sin error: «la vista de jurado no está activa (vista_jurado: no en el os.md del relay)», o lo mismo con la ruta. Los textos de las notas van tal cual en el JSON: son dato (constitución V). `estado` sigue devolviendo el md, con la línea de resumen (§6).

### 11.6 Vista de ejemplo
Reto 03, sábado a las 11:00 (Europe/Madrid), con pocos datos. Es la que usa K-106 para empezar la web y la que valida el esquema (`$defs/vista_jurado` y `$defs/vista_ruta`).

```json
{
  "jurado": {
    "observado_en": "2026-09-19T09:00:00Z", "fuente": "derivado", "viejo": false, "fichero": "ok",
    "cuenta": {"notas": 3, "corregidas": 0, "cubiertas": 1, "sin_cubrir": 2, "sin_tarea": 1, "ambiguas": 0, "planificadas": 0, "en_curso": 1, "en_pitch": 0,
               "sin_cubrir_por_fuerza": [{"texto": "obligatorio", "n": 1}, {"texto": "nos gustaría ver", "n": 1}]},
    "notas": [
      {"nota": {"clave": "3f9a1c07b2e4", "cita": "2026-09-19 10:40", "hora": "2026-09-19T10:40:00+02:00", "quien": "Marta (Embat)", "papel": "jurado",
                "donde": "mesa 4", "dijo": "Queremos ver la validación con datos reales", "literal": true, "fuerza": {"tipo": "palabra", "texto": "obligatorio"},
                "afecta_a": "plan, pitch", "anotado_por": "@ana", "corrige": null, "fuente": "git", "observado_en": "2026-09-19T08:52:10Z", "declarado": true},
       "cobertura": {"valor": "sin_tarea", "fuente": "derivado", "observado_en": "2026-09-19T08:52:10Z", "viejo": false},
       "corregida_por": null, "trabajo_nuevo_desde": null, "tareas": [], "evidencias": [], "pitch": null},
      {"nota": {"clave": "a1b2c3d4e5f6", "cita": "2026-09-18 21:15", "hora": "2026-09-18T21:15:00+02:00", "quien": "Luis (mentor)", "papel": "mentor",
                "donde": null, "dijo": "estaría bien ver el informe en PDF", "literal": false, "fuerza": {"tipo": "palabra", "texto": "nos gustaría ver"},
                "afecta_a": "plan", "anotado_por": "@luis", "corrige": null, "fuente": "git", "observado_en": "2026-09-19T08:52:10Z", "declarado": true},
       "cobertura": {"valor": "en_curso", "fuente": "derivado", "observado_en": "2026-09-19T08:40:00Z", "viejo": false},
       "corregida_por": null, "trabajo_nuevo_desde": null,
       "tareas": [{"tarjeta": {"id": "T12", "titulo": "Informe PDF", "dueno": "marta", "estado": "en_curso", "etiqueta": "en curso", "fuente": "hook",
                               "observado_en": "2026-09-19T08:40:00Z", "viejo": false},
                   "enlace": {"cita": "2026-09-18 21:15", "ambiguo": false, "donde": "plan.md", "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true}}],
       "evidencias": [], "pitch": null},
      {"nota": {"clave": "0c9d8e7f6a5b", "cita": "2026-09-18 20:30", "hora": "2026-09-18T20:30:00+02:00", "quien": null, "papel": "organización",
                "donde": "charla de apertura", "dijo": "La API devuelve JSON con el esquema publicado", "literal": true, "fuerza": {"tipo": "dato", "texto": "dato"},
                "afecta_a": "contratos", "anotado_por": "@ana", "corrige": null, "fuente": "git", "observado_en": "2026-09-19T08:52:10Z", "declarado": true},
       "cobertura": {"valor": "cubierta", "fuente": "derivado", "observado_en": "2026-09-19T01:10:00Z", "viejo": false},
       "corregida_por": null, "trabajo_nuevo_desde": null,
       "tareas": [{"tarjeta": {"id": "T03", "titulo": "Esquema de la API", "dueno": "ana", "estado": "publicada", "etiqueta": "publicada", "fuente": "git",
                               "observado_en": "2026-09-19T01:10:00Z", "viejo": false},
                   "enlace": {"cita": "2026-09-18 20:30", "ambiguo": false, "donde": "plan.md", "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true}}],
       "evidencias": [{"tipo": "commit", "tarea": "T03", "valor": "9e1f2a3b4c5d", "fuente": "git", "observado_en": "2026-09-19T01:10:00Z", "viejo": false}],
       "pitch": null}
    ],
    "sin_nota": [],
    "resumen": "jurado: 2 sin cubrir (1 «obligatorio») · 1 cubierta de 3"
  },
  "ruta": {
    "observado_en": "2026-09-19T09:00:00Z", "fuente": "derivado", "viejo": false, "dato_mas_viejo": "2026-09-19T08:58:30Z",
    "objetivo": {"valor": "2026-09-20T10:00:00+02:00", "texto": "2026-09-20 10:00, Europe/Madrid", "confirmar": false, "motivo": null, "donde": "equipo.md",
                 "fuente": "git", "observado_en": "2026-09-18T18:05:00Z", "declarado": true},
    "otras_entregas": [{"nombre": "Entrega final", "valor": "2026-09-20T11:00:00+02:00", "texto": "dom 11:00", "motivo": null, "donde": "plan.md",
                        "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true}],
    "veredicto": {"valor": "sin_estimacion", "motivos": ["pocos_datos"], "gravedad": "gris", "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z"},
    "estimacion": null,
    "base": {"minimo": 3, "desde": "2026-09-18T21:40:00Z", "personas": [
      {"persona": "ana", "n": 2, "ritmo_min": null, "ritmo_max": null, "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z"},
      {"persona": "luis", "n": 3, "ritmo_min": 110, "ritmo_max": 160, "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z"},
      {"persona": "marta", "n": 1, "ritmo_min": null, "ritmo_max": null, "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z"}]},
    "hechos": [
      {"tipo": "plazo_pasado", "gravedad": "rojo", "tarea": "T05", "persona": "ana", "plazo": "2026-09-19T02:30:00+02:00", "arrastra": ["T06", "T16"],
       "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z", "viejo": false},
      {"tipo": "sin_senales", "gravedad": "gris", "persona": "luis", "desde": "2026-09-19T08:35:00Z", "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z", "viejo": false}],
    "cadena": [
      {"tarjeta": {"id": "T05", "titulo": "Motor de detección", "dueno": "ana", "estado": "en_curso", "etiqueta": "en curso", "fuente": "hook",
                   "observado_en": "2026-09-19T08:50:00Z", "viejo": false},
       "por": "inicio",
       "hasta": {"valor": "2026-09-19T02:30:00+02:00", "texto": "sáb 02:30", "motivo": null, "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true},
       "franja": {"valor": {"desde": "2026-09-18T23:00:00+02:00", "hasta": "2026-09-19T02:30:00+02:00", "min": 210, "compartida": 1}, "motivo": null,
                  "fuente": "derivado", "observado_en": "2026-09-19T07:30:00Z", "declarado": true},
       "fin_temprano": null, "fin_tarde": null},
      {"tarjeta": {"id": "T06", "titulo": "Ajuste con datos de Embat", "dueno": "ana", "estado": "lista", "etiqueta": "lista", "fuente": "github",
                   "observado_en": "2026-09-19T07:31:00Z", "viejo": false},
       "por": "orden_del_plan",
       "hasta": {"valor": "2026-09-19T13:00:00+02:00", "texto": "sáb 13:00", "motivo": null, "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true},
       "franja": {"valor": {"desde": "2026-09-19T07:00:00+02:00", "hasta": "2026-09-19T13:00:00+02:00", "min": 360, "compartida": 1}, "motivo": null,
                  "fuente": "derivado", "observado_en": "2026-09-19T07:30:00Z", "declarado": true},
       "fin_temprano": null, "fin_tarde": null}],
    "riesgos": [],
    "sin_plazo": [{"tarea": "T21", "motivo": "por_confirmar"}],
    "fuera_de_entrega": [{"tarea": "T09", "motivo": "condicional"}],
    "hitos": [{"hito": {"nombre": "Congelación", "valor": "2026-09-19T22:00:00+02:00", "texto": "sáb 22:00", "motivo": null, "donde": "plan.md",
                        "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true}, "pasado": false}],
    "descansos": [{"personas": null, "desde": "2026-09-19T03:00:00+02:00", "hasta": "2026-09-19T07:00:00+02:00", "texto": "- Todos: sáb 03:00–07:00",
                   "motivo": null, "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true},
                  {"personas": ["luis", "marta"], "desde": "2026-09-19T23:00:00+02:00", "hasta": "2026-09-20T07:30:00+02:00",
                   "texto": "| sáb 23:00–dom 07:30 | Luis y Marta |",
                   "motivo": null, "fuente": "git", "observado_en": "2026-09-19T07:30:00Z", "declarado": true}],
    "resumen": "ruta: sin estimación (pocos datos: @ana 2 de 3, @marta 1 de 3) · otra entrega: dom 11:00 (plan.md) · T05: plazo pasado 02:30"
  }
}
```

La fila «Entrega final» de Hitos (dom 11:00) no coincide con `equipo.md` (dom 10:00): sale al lado y no es la causa de «sin estimación» (lo es `pocos_datos`). Con 3 o más medidas por persona, el mismo bloque llevaría, por ejemplo, `"veredicto": {"valor": "justo", "motivos": [], "gravedad": "ambar", …}`, `"estimacion": {"temprano": "2026-09-20T05:40:00Z", "tarde": "2026-09-20T08:50:00Z", "margen_min": -50, "margen_max": 140}`, en `riesgos` las tareas cuyo `fin_tarde` pasa de las 08:00Z (por ejemplo, `{"tarea": "T16", "tipo": "estimacion", "fin_tarde": "2026-09-20T08:50:00Z", "dueno": "ana", "en_cadena": true, "viejo": false}`) y `"resumen": "ruta: estimación justo · fin 07:40–10:50 · entrega dom 10:00 · otra entrega: dom 11:00 (plan.md) · T05: plazo pasado 02:30"`, contra la entrega de `equipo.md`.
