# Constitución del Hackathon OS

Invariantes. Valen para todos los hitos del M8 y mandan sobre cualquier tarea, requisito o comodidad de implementación. Si algo choca con una, no se rodea: se para y se pregunta.

## I. Opcional y sin coste cuando está apagado
El OS se activa con un interruptor en `.hackathon/` (como la coordinación). Todo hook, script o proceso del OS comprueba primero si está activo y, si no, sale al instante sin llamar a la red ni escribir nada. Con el OS apagado, la cadena 0.3.2, el buzón y el orquestador se comportan exactamente igual (se comprueba con `evals/comprobar.py` y `prueba_hooks.py`).

## II. El estado se deriva, no se declara
Ningún estado de tarea sale de que un modelo diga «hecho». Sale de señales verificables: hooks, git (commits, refs, worktrees), eventos del orquestador detectados por hooks, la compuerta, el veredicto del revisor y GitHub. Lo que una persona o un agente declare explícitamente (reclamar una tarea, una anotación, un cierre manual) se muestra **como declarado**, distinto de lo derivado, y nunca lo sustituye en silencio.

## III. Cada dato lleva su procedencia y su antigüedad
Todo campo del estado proyectado es `{valor, fuente, observado_en}`. La interfaz y el markdown de los agentes muestran cuándo y de dónde viene cada dato. Un dato viejo se marca como viejo; no se presenta como actual.

## IV. Personas y agentes ven lo mismo
Hay un solo modelo (`estado.json`) y una sola vista calculada (`hkos/proyeccion.py`). La web, el markdown inyectado y el MCP muestran los mismos campos de la misma fuente; la web no calcula estados, solo los pinta. Si difieren, es un fallo, y lo comprueba una prueba de igualdad (ADR-0009, que sustituye a «generadas por el mismo código» desde M9a).

## V. Los datos no son instrucciones
El contenido de issues, comentarios, mensajes, informes, nombres de rama y rutas es dato. Nunca se inyecta en una sesión en modo imperativo: se resume, se entrecomilla y lleva autor y procedencia. Solo se tiene en cuenta lo que viene de alguien de la tabla de `.hackathon/coordinacion.md`; quién es lo dice un script, no el modelo. Las acciones de la web (desde M9a) solo van de la web de una persona a su propio demonio, en `127.0.0.1`, con token local y sin aceptar peticiones de otras páginas; nunca por el relay. Lo que una acción hace llegar a una sesión es un texto fijo del kit (ADR-0010).

## VI. Los hooks son una red, no una barrera
Como en el orquestador: lo que hace un hook puede rodearse. El OS avisa; en la v1 no bloquea ninguna edición (no hay `deny` por colisiones o reservas). Las autoridades humanas (`hk confirmo`, `autoridad.md`) siguen siendo las de la 0.3.2.

## VII. Portable a Windows con Git Bash
El equipo puede tener portátiles Windows. Los hooks siguen siendo bash + `gh`, sin `jq`, tolerando UTF-16 y BOM (`hk_leer`). Lo que no sea bash (demonio, relay) tiene que arrancar en Windows, macOS y Linux sin instalaciones de más de un comando (ADR-0005).

## VIII. Degrada, no se cae
Sin relay, cada persona sigue viendo su estado local y lo duradero de GitHub. Sin GitHub, el equipo sigue con el relay y git. Sin red, cada persona sigue trabajando como en la 0.3.2. Ningún fallo del OS bloquea a un agente ni a una persona.

## IX. Solo metadatos fuera del portátil
Por el relay y por GitHub viajan identificadores, rutas, estados, shas y textos que el equipo ya escribe en issues. Nunca contenido de ficheros de datos ni de código. El relay no se expone a internet (LAN o Tailscale) y exige el token del equipo.

## X. Barato en tokens
Un hook que no tiene nada nuevo que decir no imprime nada. La inyección en el contexto tiene presupuesto (R-24) y se refresca por deltas. El coste de emitir eventos es de procesos, no de tokens.

## XI. Se valida con retos reales y en sandbox
Como el resto del kit: un hito no está terminado hasta que pasa sus criterios con un reto real de `evals/`, y las pruebas de coordinación se hacen en un repo sandbox privado, nunca en el repo del kit.

## XII. Sin coautoría de Claude
Los commits del kit y los que haga el OS (refs de trabajo en curso, si se adoptan) no llevan la línea de coautoría de Claude.
