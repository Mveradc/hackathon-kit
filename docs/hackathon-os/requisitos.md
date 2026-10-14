# Requisitos

Qué tiene que hacer el Hackathon OS y por qué. Sin el *cómo* (eso está en `diseno.md` y `adr/`).

Formato de los criterios (EARS, en español):
- **Siempre**: «El sistema DEBE …».
- **Evento**: «CUANDO <evento>, el sistema DEBE …».
- **Estado**: «MIENTRAS <estado>, el sistema DEBE …».
- **No deseado**: «SI <condición>, ENTONCES el sistema DEBE …».
- **Opcional**: «DONDE <funcionalidad activa>, el sistema DEBE …».

Cada criterio es comprobable y lo cubre al menos un guion de `simulador.md` o un criterio de `hitos.md`. Prioridad: **N** núcleo (sin él no hay OS), **D** diferencial, **E** extra (tras flag).

## Historias de uso
- **HU-1** Como persona del equipo, quiero ver en una pantalla qué está haciendo cada persona y cada agente, qué está hecho y qué falta, sin preguntar a nadie.
- **HU-2** Como agente de una persona, quiero saber al empezar y durante la sesión qué hacen los demás y si algo de lo que voy a tocar choca con otro, para no pisar trabajo ajeno.
- **HU-3** Como persona, quiero saber si mi trabajo o el de mis workers va a chocar con el de otro antes de fusionar o subir.
- **HU-4** Como equipo, quiero que el estado de cada tarea salga de lo que ha pasado de verdad (commits, revisor, compuerta), no de lo que alguien diga.
- **HU-5** Como equipo, quiero seguir trabajando si se cae la red del evento, GitHub o el relay.

## Activación (N)
- **R-01** El sistema DEBE activarse solo si `.hackathon/os.md` existe con `activa: sí` y, para la parte de equipo, la coordinación está activa (`hk_conf_activa`). MIENTRAS no esté activo, todo hook y proceso del OS DEBE salir sin red ni escritura.
- **R-02** CUANDO el OS se active por primera vez en un repo, el sistema DEBE dejar el arranque del equipo en un solo comando por persona (`hk-os unir <relay>`), y en uno más para quien hace de coordinador (`hk-os relay`).

## Identidad y actores (N)
- **R-03** El sistema DEBE identificar cada actor con: persona (usuario de GitHub de `coordinacion.md`), sesión (`session_id`), papel (`principal`, `orquestador`, `worker`, `revisor`, `humano`) y, en subagentes, `agent_id`.
- **R-04** El sistema DEBE usar el usuario de GitHub en minúsculas como clave única de persona en todos los ficheros y eventos (ver ADR-0002).

## Tareas (N)
- **R-05** El sistema DEBE dar a cada tarea de `plan.md` un identificador estable (`T01`, `T02`…) que no cambia al regenerar o ajustar el plan y no se reutiliza.
- **R-06** CUANDO una persona ejecute la compilación del plan, el sistema DEBE crear o actualizar un issue por tarea en el repo de la coordinación, con dueño, bloque, comprobación y dependencias, de forma idempotente: compilar dos veces sin cambios en el plan no crea ni modifica nada.
- **R-07** Los issues de tarea NO DEBEN aparecer en el buzón: el monitor y `/hack-inbox` los ignoran (ADR-0001).
- **R-08** El sistema DEBE calcular «lista» para cada tarea pendiente cuyas dependencias estén todas cerradas.

## Estado derivado (N)
- **R-09** El sistema DEBE derivar el estado de cada tarea según la máquina de estados de `diseno.md` §5, a partir de señales, sin aceptar como estado lo que un modelo escriba en texto libre.
- **R-10** CUANDO el orquestador lance un worker, cree una referencia de fusión, reciba un veredicto del revisor o avance `main` por `ff-only`, el sistema DEBE emitir el evento correspondiente a partir de los hooks y de git, sin depender de que el orquestador lo narre.
- **R-11** CUANDO la compuerta acepte o rechace un informe, el sistema DEBE emitir el evento con el motivo.
- **R-12** El sistema DEBE marcar cada dato con su fuente y su hora de observación, y mostrar como «viejo» todo dato de presencia con más de 3 minutos y todo dato de GitHub o del relay con más de 5.
- **R-13** SI una persona marca una tarea a mano (cierre o estado forzado), ENTONCES el sistema DEBE mostrarla como declarada (⚑) junto al estado derivado, sin ocultar la discrepancia.
- **R-14** SI una tarea está «en curso» y no hay actividad de su actor (latido, edición, commit) en 20 minutos, ENTONCES el sistema DEBE marcarla «parada».
- **R-15** CUANDO aparezca actividad (rama, worktree, fusión) que no corresponde a ninguna tarea, el sistema DEBE mostrarla como «sin tarea».

## Actividad efímera (N)
- **R-16** MIENTRAS una sesión esté abierta, el sistema DEBE publicar su presencia y los ficheros que toca (por herramientas de edición y por `git status` del árbol en que trabaja), incluidos los workers en sus worktrees.
- **R-17** El sistema DEBE detectar los ficheros cambiados por Bash (generadores, `sed`, instalaciones) comparando el árbol de trabajo, no solo por las herramientas Edit y Write.
- **R-18** SI una sesión deja de dar señales 90 segundos, ENTONCES el sistema DEBE retirarla de «activos» sin borrar lo que hizo.

## Colisiones (D)
- **R-19** CUANDO dos actores de personas distintas tengan cambios sin fusionar sobre el mismo fichero, el sistema DEBE avisar a ambos (nivel 1, amarillo).
- **R-20** DONDE el trabajo en curso se publique como referencias de trabajo (ADR-0007), CUANDO la fusión prevista de dos de esas referencias tenga conflictos, el sistema DEBE avisar con los ficheros en conflicto (nivel 2, rojo).
- **R-21** CUANDO alguien que no es el dueño de un contrato cambie el bloque de `docs/contratos.md` o un fichero declarado como implementación de ese contrato, el sistema DEBE avisar al dueño y a los consumidores (nivel 3, rojo).
- **R-22** CUANDO un agente vaya a editar un fichero reservado por otro actor, el sistema DEBE decírselo antes de la edición (aviso, no bloqueo), con quién lo reservó y hasta cuándo.
- **R-23** El sistema NO DEBE bloquear ninguna edición por colisiones o reservas en la v1 (constitución VI).

## Proyección (N)
- **R-24** CUANDO empiece, se reanude, se limpie o se compacte una sesión con el OS activo, el sistema DEBE inyectarle el estado del equipo en un máximo de 2.500 caracteres, priorizando: su tarea y bloqueos, colisiones que le afectan, decisiones y criterios nuevos, y una línea por persona.
- **R-25** CUANDO cambie algo de la persona de una sesión (su tarea, una colisión suya, o una decisión o un criterio nuevos), el sistema DEBE inyectarle solo ese cambio en su siguiente turno, en un máximo de **600 caracteres**; SI no cambia nada de eso, ENTONCES no DEBE inyectar nada.
- **R-25b** MIENTRAS lo inyectado por deltas en una sesión, desde su inicio o su última compactación o limpieza, supere **6.000 caracteres**, el sistema DEBE inyectar solo las colisiones rojas nuevas; el resto se consulta por MCP. Motivo (M8.0, P16): cada `additionalContext` queda en el historial y se paga en todos los turnos siguientes hasta compactar (957 caracteres ≈ 420 tokens por turno). 6.000 caracteres son unos 2.600 tokens, más los 2.500 caracteres de R-24 (≈1.100 tokens): en total, unos 3.700 tokens por tramo de sesión.
- **R-26** El sistema DEBE servir una página web de solo lectura, abierta desde el navegador sin instalar nada, con tres columnas (haciendo, hecho, falta), un panel de colisiones y la antigüedad de cada dato, que se actualiza sola en menos de 5 segundos tras un cambio en el relay.
- **R-27** El sistema DEBE ofrecer a los agentes, por MCP, consultas de estado y las acciones `reclamar` y `reservar`, con el mismo modelo que la web.
- **R-28** La web, el markdown de los agentes y el MCP DEBEN coincidir en todos los guiones del simulador.

## Robustez y seguridad (N)
- **R-29** SI el relay no responde, ENTONCES cada persona DEBE seguir viendo su estado local y lo duradero de GitHub, con el aviso «efímero no disponible desde hh:mm».
- **R-30** SI GitHub no responde o limita, ENTONCES el sistema DEBE seguir con el relay y git, aplicar el backoff existente (`hk_gh`) y no superar en ningún caso 60 escrituras por hora a GitHub entre todo el equipo.
- **R-31** El sistema DEBE ignorar, en lo que inyecta y en lo que deriva, cualquier issue o comentario de alguien que no esté en la tabla de `coordinacion.md`, y mostrarlo como «de fuera del equipo».
- **R-32** El relay DEBE escuchar solo en LAN o Tailscale, exigir el token del equipo en cada petición y no guardar contenido de ficheros.

## Extras tras flag (E)
- **R-33** DONDE la escritura desde la web esté activa, el sistema DEBE permitir reclamar, cerrar o escalar desde la web respetando `autoridad.md` y la confirmación `hk confirmo`.
- **R-34** DONDE el análisis estructural esté activo, el sistema DEBE rebajar a amarillo un conflicto de nivel 2 que una fusión estructural (Mergiraf) resuelva sin conflictos.
- **R-35** DONDE la vista de jurado esté activa, el sistema DEBE mostrar qué tarea o evidencia cubre cada nota de `criterios.md`.
- **R-36** DONDE la ruta crítica esté activa, el sistema DEBE estimar, con las dependencias y el ritmo real, si se llega a la entrega y qué tareas la ponen en riesgo.
