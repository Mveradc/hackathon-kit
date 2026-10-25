# Changelog

## 0.6.0 — 2026-10-25

Nivel 2b de colisiones con Mergiraf (opcional, experimental), dentro del Hackathon OS. Se enciende con `fusion_estructural: sí` en el `.hackathon/os.md` del relay, y solo cuenta con `publicar_wip: sí` y Mergiraf 0.20.0 o posterior en el `PATH` del portátil de quien coordina. Apagado (o sin Mergiraf), `estado.json`, la vista y `estado-equipo.md` son byte a byte los de la 0.5.0 con los mismos datos.

- **Nivel 2b** (R-34, ADR-0014): en cada ciclo del nivel 2, el relay intenta [Mergiraf](https://codeberg.org/mergiraf/mergiraf) sobre cada fichero en conflicto con sus tres versiones. Si lo fusiona sin conflictos, la colisión baja de rojo a amarillo (`2b`, «fusión estructural sin conflictos»); un conflicto de verdad, un error o un plazo vencido siguen en rojo. **El kit nunca fusiona** ni enseña la fusión: avisa, como el nivel 1, de que hay que mirarlo. «Amarillo» no quiere decir que la fusión funcione. Caché por contenido y plazos de 5 s por fichero, 10 s por proceso y 20 s por ciclo; las copias que guarda Mergiraf van a un temporal que se borra siempre.
- **Mergiraf solo en el portátil del relay, instalado a mano:** el binario de la release oficial en Windows (x86_64) y Linux, `brew install mergiraf` en macOS o `cargo install --locked mergiraf`. **El kit no lo instala ni lo pide.** Sin él, o con una versión menor que la 0.20.0, el relay lo dice una vez al arrancar y sigue con el nivel 2 en rojo. La plantilla `os.md` de `/hack-scaffold` trae `fusion_estructural: no`. Solo baja lo que Mergiraf analiza (Python, JavaScript, TypeScript, JSON, YAML, TOML, HTML, Markdown, Java, Go, Rust…); CSS, SQL, `.txt` e `.ipynb` siguen en rojo.
- **Dónde sale:** en `estado-equipo.md` (`- AMARILLO · nivel 2b · fusión estructural sin conflictos · …`), en `/v1/vista`, en la herramienta `colisiones` del MCP `os` (la frase del nivel 2b en su descripción, solo con `fusion_estructural: sí`) y en las dos webs, con el mismo texto que el md. El esquema no cambia.
- **Silencio:** bajar de rojo a 2b no abre turno; volver de 2b a rojo sí. Arreglado `escucha.sh`: recordaba para siempre las rojas vistas, así que una roja que bajaba a 2b, o se iba, y volvía con el mismo texto no avisaba.
- **Arreglos del issue #77** (PR #79 y #80). Ruta crítica: sin tareas abiertas que cuenten, «pocos datos» y nunca «a tiempo» sin medidas; con todo hecho, «a tiempo» o «no llega» según el último `hecha_en`; la web decide el rango como `ruta.py`; se descartan las medidas imposibles; las dependencias se recorren sin recursión; y un plazo pasado lleva el día si no es el de hoy. Jurado y lo viejo: el md dice con su hora cuándo el remoto del equipo lleva rato sin leerse, las notas viejas salen como viejas, `criterios.md` mal formado se dice, los controles bidi se quitan también de los campos cortos del bloque jurado (quién, papel, dónde, lo dicho…) y, en Windows, escribir `estado.json` reintenta el reemplazo y no deja temporales.
- Validado sin modelo (más de 600 pruebas, el guion G15 del simulador y la igualdad web, md y MCP) y en vivo con `evals/coordinacion/colisiones_2b_vivo.py`: dos personas y el relay con Mergiraf de verdad, en Linux y en runners de GitHub Actions con Windows y macOS (amarillo a los 23–31 s de publicar; rojo y la línea del monitor a los 24–31 s): [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md) (M11). **Sin probar:** un portátil real con Windows o macOS (solo runners), el código de un equipo en un reto real, más de dos personas a la vez y el ensayo con un equipo (sigue aplazado). Ver [docs/limitaciones.md](docs/limitaciones.md).

## 0.5.0 — 2026-10-21

Vista de jurado y ruta crítica (opcionales, experimentales), dentro del Hackathon OS. Cada una se enciende con su interruptor en `.hackathon/os.md` (`vista_jurado: sí`, `ruta_critica: sí`); apagadas, `estado.json`, la vista, `estado-equipo.md`, el MCP y la web son byte a byte los de la 0.4.0.

- **Vista de jurado** (R-35, ADR-0012): por cada nota de `criterios.md`, qué tarea la recoge (la etiqueta `(criterios: <fecha hora>[ · quién])` que pone `/hack-plan` o `/hack-check aplicar` en «Cómo se comprueba») y su cobertura: sin tarea, ambigua, planificada, en curso, en el pitch, cubierta (todas sus tareas publicadas, con el último sha como evidencia) o corregida. Nunca «cubierta» porque algo lo declare.
- **Ruta crítica** (R-36, ADR-0013): los plazos pasados (en rojo, el único rojo) y lo que arrastran por dependencias y por el orden del plan, la cadena hasta la entrega y, con 3 o más tareas medidas por persona, una estimación con rango, margen y base contra la `Entrega:` de `equipo.md`: `a_tiempo`, `justo` o `no_llega` (los dos últimos en ámbar). Con menos, «sin estimación · pocos datos» y ninguna hora. Los descansos no hunden el ritmo; las horas van con la zona del equipo, también a través del cambio de hora. Las tareas sin plazo y las de quien no tiene usuario de GitHub salen aparte y no se miden.
- **Dónde sale:** dos pantallas nuevas en la web de trabajo, una línea cada una en `## Jurado y ruta` de `estado-equipo.md` (el delta solo la inyecta cuando cambia la cobertura o el veredicto) y las herramientas `jurado` y `ruta` del MCP `os`, que solo aparecen con su interruptor encendido.
- **Constitución V:** ningún texto de un fichero del equipo llega al md, al MCP o a la web sin «», su fichero y su recorte; el resumen nunca se corta dentro de una parte y los controles bidi se quitan.
- `/hack-scaffold` recuerda `Txx ·` al inicio de cada commit y, con la coordinación activa, que las preguntas sobre el estado del equipo se contestan solo con lo que digan `jurado` y `ruta`, con fichero y hora.
- Validado sin modelo (más de 550 pruebas, los guiones G13 y G14 del simulador y la igualdad web, md y MCP) y con modelo en el sandbox: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md) (M10). **Sin datos reales:** en el sandbox la ruta no llegó a estimar, así que el mínimo de 3 medidas, los umbrales del veredicto y el ritmo medido están sin probar con un equipo. Ver [docs/limitaciones.md](docs/limitaciones.md).

## 0.4.0 — 2026-10-18

Hackathon OS (opcional, experimental): el equipo ve en todo momento quién hace qué, qué está en `main` y dónde va a chocar, sin preguntarlo en voz alta. Se enciende con `activa: sí` en `.hackathon/os.md`; apagado, la cadena se comporta como en la 0.3.2.

- **Estado del equipo.** Un demonio por persona (sin modelo) emite lo que pasa en su clon y un relay en el portátil de quien coordina lo junta. Cada sesión recibe al empezar un bloque «Equipo» (≤ 2.500 caracteres) y, en cada turno, solo lo que ha cambiado y la afecta. Un servidor MCP `os` (`estado`, `tarea`, `colisiones`) para la sesión y el orquestador. Todo lo viejo se dice como viejo, con su hora.
- **Colisiones**, siempre como aviso: dos personas en el mismo fichero (nivel 1), cambios incompatibles antes de fusionar (nivel 2, opcional con `publicar_wip: sí`) y contratos tocados por quien no es su dueño (nivel 3). Reservas de ficheros y un turno solo cuando sale una roja nueva.
- **Robustez:** modo sin GitHub (remoto `bare` y tareas desde `plan.md`), guion de arranque en 10 minutos (`docs/hackathon-os/arranque.md`) y evals de caídas, inyección y arranque.
- **Web de trabajo** (`web_nueva: sí`): React + Vite, compilada y subida al repo (nadie instala Node), servida por el demonio de cada persona en `127.0.0.1`. Cuatro vistas (cabina, red, tablero y servicios). La animación solo se mueve con eventos reales. El token solo en memoria, y un solo stream por navegador.
- **`.hackathon/servicios.md`** (lo genera `/hack-scaffold`): puertos, salud, conexiones y su Prueba. Una fila solo sale confirmada si su dueño la escribió en un commit hecho en su portátil (ADR-0011). Los desajustes (puerto sin respuesta, Prueba que falla, código fuera de todo servicio) salen en la vista.
- **Dos acciones desde la web:** Anotar (una nota en `criterios.md` de `origin/main` sin tocar tu copia) y Reclamar (asigna el issue con tu `gh` y abre un turno en tu sesión con texto fijo). Con topes por hora, saneado y sin coautoría (ADR-0010).
- **Seguridad** (ADR-0010): el demonio solo escucha en `127.0.0.1`, comprueba `Host` y `Origin`, no da CORS y demuestra con un HMAC que es el tuyo antes de que `hk-os web` le mande el token. Los secretos, privados del usuario también en Windows.
- Contratos y decisiones en `docs/hackathon-os/` (constitución, ADR-0005–0011 y `contratos/api.md`).
- Validado sin modelo (más de 400 pruebas y las evals de `evals/coordinacion/`) y con modelo en un sandbox con una persona simulando al equipo: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md) (M8 y M9a). **Sin ensayo con un equipo real todavía** (criterio 4 de M8h, aplazado): ver [docs/limitaciones.md](docs/limitaciones.md).

## 0.3.2 — 2026-10-13

- `/hack-approaches` evalúa el encaje de cada enfoque con el equipo si existe `.hackathon/equipo.md`: quién cubre cada pieza, los huecos, las ausencias que chocan con una fase crítica y quién puede defenderlo, en unas 60 palabras por enfoque, más una fila en la tabla. El orden lo asegura: primero guarda los enfoques, sacados solo del reto, y después lee `equipo.md` y añade el encaje sin tocar lo ya escrito.

## 0.3.1 — 2026-10-13

- `/hack-scaffold` genera `.claude/settings.json` con `attribution` vacía: los commits y PR que haga Claude (también los workers y el orquestador) no llevan su coautoría. Si las bases piden declarar el uso de IA, no la quita y lo avisa. `/hack-analyze` recoge lo que digan las bases sobre el uso de IA, y `/hack-check` comprueba que la declaración que pidan tenga tarea con dueño (y avisa si `settings.json` oculta la atribución).
- Orquestador: el worker deja su informe completo en `<git común>/hackathon/informes/<rama>.md` y devuelve una sola línea; la compuerta lee ese fichero (solo dentro de esa carpeta). El orquestador lee solo su sección del plan y lo que necesita de los contratos. En una sesión de dos bloques, su contexto final baja de 68–74 k a 58 k.

## 0.3.0 — 2026-10-13

Orquestador por persona (experimental) y criterios del jurado.

- Nuevo agente `orquestador` (Opus), que se lanza con `claude --agent hackathon-kit:orquestador`: toma las tareas de una persona en `.hackathon/plan.md`, las parte en encargos y se los da a workers (Sonnet), como mucho dos a la vez y cada uno en su worktree. Él no edita código: un hook se lo impide.
- Un revisor independiente (Sonnet) revisa cada fusión en un worktree propio y vuelve a ejecutar la comprobación sin ver el informe del worker. La fusión se hace fuera de la rama de la persona y la rama solo avanza (en rápido) hasta una fusión aprobada; con CAMBIOS, se relanza una vez y, si vuelve a fallar, la tarea queda sin cerrar y la rama no ha cambiado.
- Una compuerta rechaza los informes de los workers sin evidencias (salida de la comprobación, commits, ficheros declarados, árbol limpio).
- El orquestador sube sus fusiones aprobadas (sin forzar), nunca commits de la persona.
- Reinicio en frío: si la sesión se corta, el orquestador retoma desde `.hackathon/estado/` sin repetir lo fusionado, vuelve a revisar la fusión pendiente y propone qué hacer con el trabajo huérfano sin borrarlo. Al terminar cada bloque, recomienda reiniciarlo, porque su contexto crece con cada encargo.
- La coordinación entre agentes y el orquestador se marcan como experimentales en el README: se han validado en un sandbox con una persona simulando al equipo, todavía no con un equipo real.
- Con la coordinación activa, un hook impide a cualquier agente publicar `hk confirmo` con `gh` (una red, no una garantía: ver limitaciones).
- Nuevo comando `/hack-note`: anota en `.hackathon/criterios.md` lo que dicen el jurado, los mentores o la organización durante el evento (quién, sus palabras y su fuerza). `/hack-pitch` lo recoge y `/hack-check` lo usa como fuente e informa de las notas sin recoger o que chocan con el enunciado.
- `/hack-decide` termina con el comando exacto de commit y push para compartir el acuerdo.
- Con la coordinación activa, cada nota de `/hack-note` se avisa a todo el equipo por un issue (`hk:para-todos`); el agente que la recibe se la cuenta a su persona, sin escribir en `criterios.md`. `buzon.sh ver` dice si quien abrió el issue está en la tabla del equipo.
- Validado con el reto 03: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md) (M6b y M7).

## 0.2.0 — 2026-10-11

Coordinación entre agentes, opcional.

- Nuevos comandos `/hack-ask`, `/hack-inbox` y `/hack-decide`: los agentes de cada persona se preguntan por GitHub Issues, con cabecera de saltos, escalado a las personas, deduplicación y backoff.
- Monitor de plugin que escucha el buzón sin coste de tokens mientras no hay novedades, y hook de inicio que reinyecta el estado propio y el buzón.
- `/hack-scaffold` pregunta si activarla (`.hackathon/coordinacion.md`, plantilla de issue, `.gitattributes`) y `/hack-plan` genera `.hackathon/autoridad.md`.
- Sin la coordinación activada, la cadena se comporta como en la 0.1.0.
- Validado con dos sesiones en dos worktrees de un repo sandbox y dos cuentas de GitHub: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md).

## 0.1.0 — 2026-10-10

Primera versión pública.

- Seis comandos: `/hack-analyze`, `/hack-approaches`, `/hack-scaffold`, `/hack-plan`, `/hack-pitch` y `/hack-check`, con el estado compartido en `.hackathon/`.
- Ejemplos de salida de dos retos reales en `skills/*/examples/`.
- Validado con seis retos (cinco reales y uno sintético) y una rúbrica de comprobaciones automáticas y de criterio (`evals/`).
- Limitaciones conocidas: [docs/limitaciones.md](docs/limitaciones.md).
