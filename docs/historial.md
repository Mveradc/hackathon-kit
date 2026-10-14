# Historial de hackathon-kit

Registro de lo que se hizo y se aprendió en cada hito, tal como estaba en la sección «Estado» del CLAUDE.md hasta el 2026-09-27. El CLAUDE.md solo conserva lo vigente; aquí queda el detalle, ordenado por hito.

## M0 — Esqueleto (cerrado el 2026-09-26)
- `claude plugin validate .` pasa. Único aviso: este CLAUDE.md en la raíz del plugin (no se carga como contexto del plugin; es solo para desarrollo, es esperado).
- `.claude-plugin/plugin.json` (manifiesto) y `.claude-plugin/marketplace.json` (marketplace local `hackathon-kit-dev`, con `source: "."`).
- `skills/hack-analyze/SKILL.md` (migrado desde `commands/`): analiza el reto sin proponer soluciones y marca lo inferido. Acepta texto o la ruta de un fichero; sin argumentos, pide el enunciado.
- Probado en headless con `evals/retos/01-movilidad-sintetico.md` (sintético), con texto inline, sin argumentos y con `evals/retos/02-facturas-real.md` (real: «500 Sombras de Alberto», texto completo de hackathon.maisa.ai). Solo la salida del reto real está en `skills/hack-analyze/examples/`.
- Probado también en sesión interactiva (`claude --plugin-dir .`) con el reto 02: funciona y la calidad es equivalente a la de headless. El alias corto `/hack-analyze` funciona en headless y en sesión interactiva.

## M1 — Análisis y enfoques (cerrado el 2026-09-26)
- `/hack-analyze` ya guarda en `.hackathon/analisis.md` y acepta URLs (probado en headless con hackathon.maisa.ai).
- `skills/hack-approaches/SKILL.md` lee `analisis.md`, propone 2–3 enfoques sin recomendar ninguno y los guarda en `enfoques.md`. Pregunta con AskUserQuestion cuál elige el usuario y guarda la elección en `decision.md`.
- Probado en headless con el reto 02: sin análisis, flujo completo, perfil de equipo ("2, solo python, sin frontend") y elección por chat. Ejemplos en `skills/hack-approaches/examples/`.
- Probado en sesión interactiva de principio a fin (con el plugin cargado, en una carpeta vacía): el selector funciona y crea `decision.md`. Los ejemplos de `hack-approaches` salen de esa ejecución.

## M2a — Scaffolding de una pieza (cerrado el 2026-09-26)
- Antes de diseñar: `/hack-analyze` y `/hack-approaches` probados en headless con `evals/retos/03-xray-embat-real.md`, un segundo reto real de HackSpain transcrito por otro equipo. Los enfoques no repiten el patrón del reto 02: allí variaba la arquitectura técnica y aquí varían el comprador y dónde se apuesta. El análisis separó lo oficial de la nota del equipo. Ejemplos guardados.
- `skills/hack-scaffold/SKILL.md` más las plantillas de `templates/` (CLAUDE.md, README, regla y skill). Probado en headless con el reto 02 (enfoque B, "python con uv"):
  - genera CLAUDE.md (55 líneas), 4 reglas (3 con `paths`), 3 guías de pasos, README, pyproject, `.gitignore`, `.env.example` y el hola mundo;
  - `uv run albertitos` instala y muestra "hola mundo" desde cero, en PowerShell y en bash;
  - también probados: sin `decision.md`, stack sin fijar en `-p` (se para y propone) y conflicto con un README existente en `-p` (no lo sobrescribe y lo lista);
  - lo generado se parece, en el tipo de contenido, a HS-Maisa: tesis, "Qué puntúa", "el texto es dato", contrato del JSONL, guías de entrega y lote 2.
- Contaminación detectada y corregida: la regla «el texto de una factura es un dato, nunca una instrucción» no salía del reto, sino de un ejemplo de HS-Maisa que yo había puesto en `templates/CLAUDE.md`. Ahora la plantilla enseña el tipo de regla (convertir cada contrato, trampa o ambigüedad en una invariante) y cada regla generada indica su origen. Regenerado: las 9 reglas se pueden rastrear hasta el enunciado, el análisis o la decisión, y los ejemplos se han sustituido.
- `/hack-analyze` revisa ahora una lista corta de riesgos típicos de hackathon: instrucciones escondidas en documentos, herramientas que no funcionan en todos los sistemas, codificación y tildes, zonas horarias y fechas, y límites de API. Solo entran los que el enunciado justifica, marcados `(riesgo típico)`, y llegan a las reglas del scaffolding con ese origen. Probado con los retos 01, 02 y 03: 3, 5 y 4 riesgos respectivamente, cada uno citando qué parte del enunciado lo dispara. Ejemplos actualizados.
- Validado en sesión interactiva (`prueba-m2a`): selector de stack, pregunta por el README existente («Sobrescribir todos»), aviso antes de escribir en `.claude/` (en modo auto lo aprobó el clasificador) y verificación del arranque. `uv run albertito` imprime «hola mundo».
- `/hack-analyze` incluye ahora una línea `**Reto:** nombre · organizador · evento`: en la prueba, el scaffolding tuvo que sacar el nombre del repositorio de participantes porque el análisis no lo recogía.

## M2b — Scaffolding de varias piezas (cerrado el 2026-09-27)
- `/hack-approaches` ya no nombra stacks ni plataformas: solo dice si hace falta despliegue. Corregido tras la revisión del usuario.
- Decisión de prueba en el reto 03: enfoque A, radar de cartera.
- `/hack-scaffold` admite varias piezas: detecta las piezas a partir de la decisión, crea una carpeta por pieza con su hola mundo (el de la web muestra la respuesta del motor) y un comando único en la raíz que no añade herramientas. El despliegue queda como `TODO` si no hay plataforma elegida.
- Probado en headless con "motor python uv fastapi, web vite react": `npm run arranca` (con `arranca.mjs`: instala las dos piezas, las arranca y en Windows las para todas con `taskkill /T`). Arrancado por mí desde cero en PowerShell: el motor responde, la web devuelve HTTP 200, el proxy de la web al motor funciona y los procesos se detienen.
- Sin stack en `-p`: detecta motor y web, propone 3 stacks sin marcar ninguno y se para.
- Contaminación revisada: ninguna salida copia del repo del equipo de Embat. Las coincidencias (`balances` como foto final, el LLM solo con features agregadas, las monedas) salen del enunciado, de un riesgo típico o de una ambigüedad.
- Validado en sesión interactiva (`prueba-m2b`) con la cadena completa del reto 03: `/hack-analyze` → `/hack-approaches` (eligió A) → `/hack-scaffold`. Salieron dos piezas (`motor/`, `web/`), un arranque único en la raíz, un CLAUDE.md de 57 líneas, 3 reglas y 3 guías de pasos. El usuario confirma que arranca, que la web muestra la respuesta del motor y que Ctrl+C lo para todo.

## M3a — Plan por persona (cerrado el 2026-09-27)
- `skills/hack-plan/` (SKILL.md y plantillas `equipo.md` y `plan.md`). Probado en headless:
  - sin `equipo.md`: crea la plantilla con las fechas del análisis marcadas «(confirmar)» y se para; con la plantilla sin tocar, se vuelve a parar;
  - reto 03 con equipo ficticio (3 personas, una llega el sábado a las 10:00): los tres hitos obligatorios están, la ausencia se respeta, hay 3 dependencias con cómo desbloquearlas, 1.092 palabras y unas 9 líneas por persona; el diff del CLAUDE.md solo añade `## Dueños`;
  - `plan.md` existente en `-p`: no toca ni el plan ni el CLAUDE.md.
- Reto 02 con el equipo real, en sesión interactiva (`prueba-m3a`): hitos al 40 % (sábado 11:00), entrega temprana, lote 2, congelación con dos ensayos y descansa primero quien defiende. Comparado con el reparto real de HS-Maisa: coincide en el tipo (contratos primero, ficheros por dueño, entrega temprana, documentación y defensa juntas) y difiere donde debe (enfoque B, de agentes, frente al motor de reglas real). Ejemplo guardado anonimizado (Persona A–E).
- Fallo de diseño corregido: el prompt decía «avisa en una línea y hazlo», así que modificó el CLAUDE.md sin dar opción a negarse (y el CLAUDE.md no es ruta protegida, así que no hubo permiso). Ahora enseña la sección `## Dueños` y pregunta con AskUserQuestion; si no puede preguntar, no lo toca y deja la sección en el resumen.
- Prueba interactiva repetida con la corrección: pregunta antes de sobrescribir `plan.md` y enseña la sección `## Dueños` antes de sustituirla en el CLAUDE.md. En `-p` no toca el CLAUDE.md y deja la sección en el resumen.

## M3b — Pitch (cerrado el 2026-09-27)
- `skills/hack-pitch/` (SKILL.md y plantilla `pitch.md`). Probado en headless:
  - sin `equipo.md`: crea la plantilla y se para;
  - reto 02 (equipo real y su plan): sigue la defensa del análisis (2′·2′·4′·2′), con los criterios y pesos idénticos a la rúbrica de `analisis.md`; presentan quienes dice `equipo.md` y responden los dueños del plan; las preguntas incluyen los puntos débiles del enfoque B; cada `[CIFRA]` tiene fila con su hito. No aparece ninguna frase ni comando del guion real de HS-Maisa;
  - reto 03 (equipo ficticio y su plan): estructura por defecto, porque el análisis no recoge ninguna; los tres criterios de 1/3, el comprador y la anticipación como hueco con su hito;
  - reto 01 sin `plan.md`: estructura por defecto en 3 minutos, aviso de que falta el plan y «—» en dueños e hitos;
  - `pitch.md` existente en `-p`: no lo sobrescribe.
- Tamaño corregido: la primera versión dio 1.092 y 1.113 palabras en los retos 02 y 03 (dos de dos, por encima de ~900). Se han añadido al prompt límites por campo y ha quedado en 834, 768 y 893.
- Ejemplos de los retos 02 (anonimizado) y 03 guardados.
- Prueba interactiva del usuario en `prueba-m3a`: genera `pitch.md` y pregunta antes de sobrescribirlo.

## M4 — Validación con `evals/` (parte automática cerrada el 2026-10-10; falta la pasada interactiva cronometrada)
- 2026-10-04/05:
  - rúbrica A1–A6 y C1–C6 y `evals/comprobar.py`;
  - retos nuevos 04 (hardware), 05 (sin datos) y 06 (mal especificado);
  - primera revisión C1–C6 con un revisor independiente sobre los retos 02 a 06 (`evals/resultados/criterio.md`).
- 2026-10-05: tras la revisión del usuario, etiquetas honestas (supuesto y conocimiento externo, comprobadas en A4), fuerza del enunciado, cruce del pitch con el plan y dueños de la raíz y el arranque. La segunda pasada (02 y 06) los quita, pero los graves no bajan.
- 2026-10-06:
  - Cambio de estrategia: no más reglas en los prompts. Nuevo `/hack-check`, que verifica contra la fuente, y A7 (citas literales).
  - La rúbrica distingue grave, leve y bloqueante (seguridad o descalificación), y C6 se contesta Sí / En parte / No.
  - Tercera pasada con los cinco retos: el cierre de M4 **no se cumple** (4 bloqueantes confirmados y C6 «En parte» en los cinco).
  - Las propuestas quedan para que decida el usuario.
- 2026-10-10:
  - Cambios decididos por el usuario: `/hack-check` amplía los bloqueantes a todas las causas de descalificación y revisa también las guías y los contratos; aplica con confirmación los cambios de calendario y normaliza las etiquetas. `/hack-scaffold` genera `docs/contratos.md`.
  - El bloqueante del 03 era un error del revisor: el enunciado no exige LLM.
  - Nuevo criterio de cierre: 0 bloqueantes, C6 nunca «No» y confirmación de una persona real.
  - Última ronda (03, 04, 05 y 06; 14,47 USD): 0 bloqueantes salvo en el 05, donde el consentimiento queda a la hora del inicio y el kit genera código antes del evento aunque las bases lo prohíben. El cierre **no se cumple**.
  - Decisiones del usuario: con trabajo previo prohibido, el scaffold para y solo genera con el evento empezado; los plazos «antes del inicio» sin fecha van antes del primer acto de la agenda; A1 mide el plan por persona. Al repetir el 05, el scaffold paró sin confirmación, y con ella A1–A7 pasan. Pero quedan un bloqueante que se sostiene y otro a medias, que el check detecta sin proponer la fila del plan: el cierre sigue sin cumplirse.
  - Después, el check propone siempre una fila del plan (con una ausencia, el plan B) y exige que la fecha de generación caiga dentro del evento. Además, una fecha simulada solo en el arnés. Al repetir el check y el revisor del 05, queda 1 bloqueante a medias (el plan B de C, con el plan contradiciéndose). El usuario lo reclasifica como leve (el riesgo queda cubierto por la fila del plan y la pregunta; lo que queda es una incoherencia interna). **Parte automática del cierre de M4 cumplida**; limitaciones conocidas en el README. Falta la pasada interactiva con una persona real.
- Detalle (antes en el CLAUDE.md):
  - `evals/comprobar.py`, probado sobre `prueba-m3a` y con controles positivos (frase copiada, peso cambiado, cifra sin fila y `.gitignore` en UTF-16). A6 (`--relanzar`) cuesta unos 1,4 USD.
  - Retos 04 (hardware, Edge AI BIO-06), 05 (sin datos, UTP Journey Vocacional) y 06 (mal especificado, COMMA_HACK 7; texto facilitado por el usuario porque el agregador corta el TLS), con la cadena completa en `../prueba-m4-04`, `../prueba-m4-05` y `../prueba-m4-06` (equipos ficticios). Primera pasada automática (`evals/resultados/`): el 05 y el 06 pasan todo; el 04 falla en A1 y A4.
  - Segunda pasada en `../prueba-m4-02-v2` y `../prueba-m4-06-v2`. Tercera, con los cinco retos en `../prueba-m4-0X-v2`, y `../prueba-m4-02-check` y `../prueba-m4-06-check` para comparar antes y después del check. Cuarta (03 solo check, 04–06 desde el scaffold) en `../prueba-m4-0X-v3`, 14,47 USD. Quinta, solo el 05, en `../prueba-m4-05-v4`, 5,29 USD. Sexta, solo el check y el revisor del 05, 1,94 USD; la fecha simulada está en `evals/fecha_simulada.py`.

## M5 — Publicación (cerrado el 2026-10-11 con el commit de la v0.1.0)
- 2026-10-10: hito abierto; la pasada interactiva de M4 queda pendiente y la hace el usuario en paralelo.
  - Ejemplos regenerados con el kit actual: retos 02 y 03, equipo ficticio desde el principio (Persona A–E y A–C) y enfoque A en los dos, elegido por el usuario. Nuevo ejemplo de `/hack-check`. Las citas de dos frases se recortaron a mano.
  - README en inglés y en español, limitaciones completas en `docs/limitaciones.md`, licencia MIT, `CHANGELOG.md` y versión 0.1.0. El marketplace pasa a llamarse `hackathon-kit` (`Mveradc/hackathon-kit`).
  - Auditoría de lo publicable: sin enunciados de terceros (una cita de dos frases parafraseada), sin nombres reales y sin secretos; `.gitignore` ampliado. El proyecto no es un repo git: no hay historial que auditar.
  - Detalle (antes en el CLAUDE.md): cadenas en `../prueba-m5-02` y `../prueba-m5-03`; 4,7 USD por cadena sin el scaffold, que se cortó por el límite de gasto, y unos 15 minutos de comandos. `comprobar.py`: A1, A3 y A4 pasan en los dos y A2 en el 02; A2 falla en el 03 (raíz 404, repetido), A5 por la cabecera común del evento y A7 por las filas sin cita. Auditoría de 72 ficheros (lista con `git add --dry-run` en una copia): `.gitignore` con `__pycache__`, `.env` y `.m4/`; la cita parafraseada está en `criterio/05-v6.md`. Los ejemplos anteriores quedaron en el scratchpad de aquella sesión.
- 2026-10-11: repo git creado y commit inicial de la v0.1.0 (remoto `Mveradc/hackathon-kit`).

## M6a — Canal entre agentes (cerrado el 2026-10-11, v0.2.0)
- Verificación previa en la documentación oficial: hooks de plugin, Monitor, asyncRewake y userConfig (detalle en `docs/coordinacion.md`). Paso 0 con un plugin de juguete: un monitor que termina, aunque sea sin imprimir, cuesta un turno, así que el monitor del buzón no termina nunca mientras viva su sesión.
- Scripts en bash + `gh` (`scripts/coordinacion/`), monitor y hook de plugin, `/hack-ask`, `/hack-inbox` y `/hack-decide` (invocables por el modelo), paso 3b de `/hack-scaffold` y `autoridad.md` en `/hack-plan`.
- Prueba en `Mveradc/hk-sandbox` (privado) con la cadena del reto 03, dos worktrees (`../hk-sandbox` y `../hk-sandbox-B`) y dos cuentas (`Mveradc` y `hk-persona-b`): los 9 criterios de `docs/coordinacion.md` se cumplen (`evals/coordinacion/prueba.md`). Coste en headless: 0,44 + 0,35 USD (scaffold y plan con coordinación) y 1,61 USD (criterio 8).
- Fallos encontrados y corregidos durante la prueba:
  - `/hk confirmo` llegaba a GitHub como `C:/Program Files/Git/hk confirmo` (Git Bash convierte los argumentos que empiezan por «/»): la marca pasa a `hk confirmo`;
  - el listado de GitHub tarda unos segundos en incluir un issue nuevo: la deduplicación usa también un registro local;
  - `read` con tabulador junta los campos vacíos: separador «unit separator» (0x1F);
  - el monitor solo miraba issues abiertos y A perdió una respuesta que B cerró en 16 s: ahora mira también los cerrados;
  - en Windows, cerrar la sesión no mata al monitor: los huérfanos seguían consultando y uno se quedó un aviso. Ahora el monitor termina si su proceso padre ha muerto;
  - un token fine-grained de una colaboradora da 404 en un repo personal ajeno: la sesión B usa `gh auth login` con `GH_CONFIG_DIR`;
  - errores de acceso repetidos en stderr cada minuto: un solo aviso;
  - `/hack-plan` no generaba la autoridad si el plan ya existía.

## M6b-1 — Criterios del jurado (cerrado el 2026-10-12)
- `/hack-note` anota en `.hackathon/criterios.md` lo que dicen el jurado, los mentores o la organización durante el evento: quién, su papel, dónde, sus palabras (o paráfrasis marcada) y su fuerza (`dato`, la palabra que usó, comentario suelto o `sin precisar`). Solo lo lanza una persona; solo se añade (`merge=union`). `/hack-pitch` recoge las notas con `(criterios: <fecha hora>)`; `/hack-check` las usa como fuente después del enunciado y añade «Criterios del jurado». `/hack-decide` y `/hack-note` terminan con el comando de commit y push.
- Validado con el reto 03 (`../prueba-m6b-03`): cuatro notas en headless (completa, fuerza débil, sin papel, en choque con el análisis y posterior al pitch) y una en sesión interactiva. `comprobar.py`: A1–A4 y A7 pasan (A5, el falso positivo conocido).
- Hallazgos: una cabecera YAML con «: » sin comillas hace que la skill cargue sin metadatos (lo detecta `claude plugin validate .`); una duración dicha por el jurado acababa como supuesto hasta añadir la fuerza `dato`; A2 del 03 fallaba por la URL raíz que imprime uvicorn (corregido en `comprobar.py`); A7 acepta ya citas de `criterios.md` en los bloqueantes.

## M6b-2 — Aviso de las notas por issue (cerrado el 2026-10-12)
- Con la coordinación activa, `/hack-note` publica la nota con `buzon.sh avisar` (issue `hk:tipo-nota` + `hk:para-todos`, cerrado al momento); el monitor avisa a todos menos a quien la escribe; `/hack-inbox` se la cuenta a su persona con `git pull`, sin escribir en `criterios.md`. Que el autor sea del equipo lo dice `buzon.sh ver`, no el modelo.
- Validado en el sandbox con dos sesiones: los 5 criterios (`evals/coordinacion/prueba.md`). Dos correcciones durante la prueba: la línea del aviso dice qué hacer (B no lanzaba `/hack-inbox` sola, cuatro veces) y la comprobación del autor pasa al script (B la dedujo de `autoridad.md`).

## M7 — Orquestador (cerrado el 2026-10-13, v0.3.0)
- **M7a**: `agents/orquestador.md` (Opus, sesión principal con `--agent`) y `agents/worker.md` (Sonnet, `isolation: worktree`), máximo dos workers a la vez. `solo-orquestar.sh` (PreToolUse filtrando por `agent_type`) impide al orquestador editar código. Como los worktrees de subagentes salen de `origin/main`, cada encargo lleva `Base: <sha local>`.
- **M7b**: revisor independiente (Sonnet) que revisa cada fusión en su propio worktree y vuelve a ejecutar la comprobación sin ver el informe del worker. Compuerta de evidencias sobre `SubagentHandback`, con SubagentStop de respaldo. Push del orquestador solo con fusiones aprobadas y sin commits de la persona.
- **M7c**:
  - la fusión se hace en un worktree temporal y se guarda en `refs/hackathon/fusion/<tarea>`; `main` solo avanza por `ff-only` hasta una fusión aprobada, y con CAMBIOS no hay nada que deshacer;
  - reinicio en frío desde `estado/<persona>.md`, las referencias y los worktrees;
  - `sin-confirmo.sh` impide a cualquier agente publicar «hk confirmo» con `gh`;
  - recomendación de reiniciar el orquestador al terminar cada bloque.
- Validado con el reto 03 en copias de prueba (`../prueba-m7*-03*`) y en el sandbox de la coordinación (`evals/coordinacion/prueba.md`). Coste: unos 0,9–1,6 USD por bloque de uno o dos encargos.
- Hallazgos:
  - los worktrees de subagentes salen del remoto, no del HEAD local;
  - Claude Code lanza agentes internos cuyo SubagentStop llega con el `agent_type` del worker;
  - los workers honestos se niegan a mentir aunque su prompt se lo pida, y corrigen un sabotaje que encuentran mientras trabajan;
  - el patrón de `--force` cogía el «-f» de un nombre como `fusion-textos-ficha`;
  - tras un corte, Claude Code deja el worktree del worker bloqueado con el pid muerto;
  - el contexto del orquestador crece por la orquestación misma (68–74 k en dos bloques), no por leer código: de ahí el reinicio por bloque;
  - al cerrar una sesión de Claude Code, un `claude -p` lanzado en segundo plano sigue vivo.

## v0.3.1 — Atribución y contexto del orquestador (en curso, 2026-10-13)
- **Atribución.** `/hack-scaffold` escribe `.claude/settings.json` con `{"attribution": {"commit": "", "pr": "", "sessionUrl": false}}`; es la forma compatible con versiones anteriores a la 2.1.281, que no admiten `attribution: false`. Si el análisis dice que hay que declarar el uso de IA, no la escribe y lo avisa. `/hack-analyze` recoge en «Restricciones» lo que digan las bases del uso de IA. `/hack-check` da bloqueante si la declaración no tiene tarea con dueño; si `settings.json` oculta la atribución, es un aviso, y solo bloqueante si el enunciado menciona los commits o el historial de git.
- Validado (6,78 USD):
  - **reto 03** (`../prueba-v031-03`): `settings.json` correcto; `comprobar.py` A2 y A3 pasan (A1 y A4 fallan por no tener plan ni pitch, y A5 es el falso positivo conocido). Prueba con control y `--setting-sources project,local`, porque el `~/.claude/settings.json` del usuario ya oculta la atribución: sin el fichero, el commit lleva `Co-Authored-By: Claude Opus 5.5`; con él, no;
  - **reto 01** (sintético, `../prueba-v031-01*`): el análisis recoge «Permitida, con declaración obligatoria en el README»; el `scaffold` no crea `settings.json`, cita la frase y genera la regla con origen `enunciado`. En `/hack-check`:
    - con la tarea en el plan, el `settings.json` sale solo como aviso (A);
    - con una frase sobre el historial de git añadida al enunciado, pasa a bloqueante (B);
    - sin ninguna tarea ni guía para la declaración, sale el bloqueante con la fila propuesta (C).
  - En B, el check dio la declaración por cubierta con el hito de entrega y la guía `/entrega`: una tarea dentro de una guía con dueño cuenta como cubierta.
- **Contexto del orquestador.** El worker deja su informe en `<git común>/hackathon/informes/<rama>.md` y devuelve una línea; la compuerta lo lee y solo acepta esa carpeta. El orquestador lee solo su sección del plan y lo que necesita de los contratos. Se descartó `bashOutputMaxChars`: su mínimo es 4.000, solo habría recortado la lectura inicial del plan y vale también para workers y revisor. Con la misma sesión de dos bloques de M7c, el contexto final pasa de 68–74 k a 58 k (2,40 USD; `evals/coordinacion/prueba.md`, «v0.3.1»).
- **Limpieza (2026-10-13).** Se borraron las carpetas de prueba de `Proyectos/` (39 carpetas, 12 remotos bare y 68 ficheros sueltos de salidas en bruto). Sus resultados quedan en este historial, en `evals/resultados/` y en `evals/coordinacion/prueba.md`. Se conservan `../prueba-m5-02`, `../prueba-m6b-03`, `../prueba-m7c-03-base` y el sandbox de coordinación.

## `/hack-approaches` con `equipo.md` (2026-10-13)
- Paso nuevo, «Encaje con el equipo»: guarda `enfoques.md` solo con el análisis, **después** lee `equipo.md` y, con Edit, añade a cada enfoque «Encaje con vuestro equipo» (unas 60 palabras: quién hace qué, huecos, ausencias en fases críticas y defensa) y a la tabla la fila «Encaje con el equipo». El encaje evalúa, no filtra: no se descarta ni se suaviza ningún enfoque. `allowed-tools` incluye ahora Edit.
- Validado con los retos 02 y 03 (copias de `../prueba-m5-02` y `../prueba-m6b-03`), en siete pasadas que costaron 3,00 USD:
  - **Orden**: `Write enfoques.md` → leer `equipo.md` → `Edit`, en las cuatro pasadas con equipo.
  - **Mismos enfoques**: el 03, sin `equipo.md` dos veces y con él dos veces, da los mismos tres conceptos (CFO, cartera para Embat y solvencia para quien presta), con los mismos criterios priorizados. Solo cambian el orden y los nombres. La pasada con la plantilla vacía cambió un enfoque, así que esa es la variación natural; la pasada con equipo no se separa de las otras más que eso.
  - **Huecos y ausencias reales**: frontend sin dueño en el 02; backend sin dueño en el 03 (no estaba previsto); y quien no presenta tendría que defender las métricas. Sin recomendaciones ni stacks, y `decision.md` intacto.
  - Con la plantilla sin rellenar lo dice, no añade el encaje y no inventa personas.
- **Longitud**: la primera versión añadía unas 390 palabras (25 %). Con el tope de ~60 palabras queda en 51–65 por enfoque en el 03 y en 71–81 en el 02 (cinco personas). Sin el encaje, la salida mide lo mismo que antes.
- Los ejemplos `examples/0{2,3}-*-enfoques.md` se regeneraron con las pasadas recortadas (los equipos ya eran Persona A, B…). Los `decision.md` de ejemplo vienen de una pasada anterior.

## M8.0 — Paso 0 del Hackathon OS (cerrado el 2026-10-14)
- Especificación en `docs/hackathon-os/` (commit `af2a1a4`).
- Paso 0 con plugins de juguete: hallazgos P1–P16 en `docs/coordinacion.md` («Hallazgos M8.0»).
- ADR-0001, 0004, 0005, 0006 y 0007 aceptados por el usuario; contratos sin `[POR DECIDIR]` (commit `28afd35`).
- Gasto en `-p`: 0,31 USD.

## M8a — El kit, preparado para el OS (2026-10-14)
- **K-10, IDs en `/hack-plan`**:
  - columna `ID` (`T01`…) en cada tabla de «Por persona», «Quién espera a quién» por IDs y la línea `IDs usados hasta: Txx`;
  - al ajustar, se conservan los IDs y no se reutilizan los quitados; si la línea falta o es menor que el ID más alto, se parte de ese ID;
  - `comprobar.py` (A1) falla si una fila no tiene ID válido, si hay IDs repetidos o si «Quién espera a quién» cita un ID que no existe, y avisa si la línea falta o es menor;
  - ejemplos del 02 y del 03 regenerados (el del 02 con la línea corregida a T42).
- **`/hack-check`** (decisión del usuario en M8a): las filas que añade al plan reciben el siguiente ID y actualizan la línea.
- **K-11, orquestador**:
  - línea `ID:` en el encargo; referencia y worktree de fusión con el ID exacto; commits `Txx · …` (también el del worker);
  - con la coordinación activa, su estado es `estado/<usuario>.orquestador.md`; sin ella, `estado/<persona>.md`;
  - tras la primera prueba se aclaró que el ID va sin sufijos aunque la tarea vaya en varios encargos.
- **K-12**: `Vive en:` en cada bloque de la plantilla de contratos y en `/hack-scaffold`.
- **K-13**: sin cambios en los scripts (P7); caso de regresión en `prueba_hooks.py`.
- Resultados en `evals/coordinacion/prueba.md` («M8a»): los seis criterios cumplidos (el 2, en interactivo, por el usuario). Gasto: 7,42 USD.

## M8b — Contratos y simulador (2026-10-14)
Primer código Python del kit, en `hkos/` (no `os/`, para no confundirlo con el módulo `os`): biblioteca estándar, `requires-python >= 3.10` y `uv run --no-project`. Las pruebas se ejecutan con unittest; jsonschema solo lo usan ellas (`uv run --with "jsonschema[format-nongpl]"`).
- **K-20, contratos**:
  - ADR-0002, 0003 y 0008 aceptadas;
  - congelados §1, §2 y los esquemas (el resto, al abrir el hito que lo usa);
  - estados como identificadores sin espacios;
  - esquemas estrictos salvo `datos`;
  - `push.datos.incluye`, `commit.datos.alcanzable`, `discrepancias` agrupadas y `cumplidas_por_cierre`;
  - eventos normalizados esperados de las entradas reales, en `evals/coordinacion/entradas/normalizadas.json`.
- **K-21, motor**:
  - primero la tabla (`diseno.md` §5.1 reglas, §5.2 52 casos), revisada por el usuario en dos vueltas; después `hkos/estados.py` (puro, por tarea);
  - la atribución de eventos sin tarea va aparte, en `hkos/modelo.py`, porque depende de varias tareas.
- **K-22, simulador**: `evals/coordinacion/simulador/` con guiones JSON G1–G4 sobre las tareas del 03; `simulador.md` pasa de YAML a JSON.
- **Estado de partida** de `../prueba-m8-03-base` (B con T18 hecha), en `evals/coordinacion/partida-m8-03/`.
- Resultados en `evals/coordinacion/prueba.md` («M8b»): los tres criterios cumplidos, también con Python 3.10. Sin gasto en modelos.

## Aprendizajes transversales
- En headless desde Git Bash con `MSYS_NO_PATHCONV=1`, `--plugin-dir` tiene que ir como `C:/…`. Con `/c/…` el plugin no carga y el modelo hace el comando «a mano» sin avisar.
- Añadir reglas a un prompt para un tipo de fallo lo desplaza a otra forma (de «(ambigüedad N)» a «(decisión)» y a «(inferido)» convertido en hecho) en lugar de eliminarlo.
- Una sola revisión de un agente por reto tiene ruido: la misma salida pasó de 4 graves a 1 entre dos revisiones.
- `.claude/` es una ruta protegida de Claude Code: la escritura siempre pide permiso (en `-p`, sin `bypassPermissions`, se deniega) y ninguna regla de allow la aprueba de antemano. El prompt avisa al usuario antes de escribir ahí.
- Si la sesión no tiene el plugin cargado, Claude puede encontrar el `SKILL.md` en disco y seguirlo a mano. Antes de probar, comprobar que `/hack` muestra los comandos en el menú.
- Cómo probar e instalar: ver «Estado» en el CLAUDE.md.
