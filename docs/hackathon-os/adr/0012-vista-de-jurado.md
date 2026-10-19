# ADR-0012 · Vista de jurado: qué es «cubrir» un criterio, qué cuenta como evidencia, qué se declara y qué se confirma

Estado: **aceptada** (2026-10-19, por el usuario al decidir la tabla del PR #42 y las preguntas del issue #41, «M10, Paso 0»). Contratos en `api.md` §11 y `estado.schema.json` (K-101).

## Contexto
R-35: «DONDE la vista de jurado esté activa, el sistema DEBE mostrar qué tarea o evidencia cubre cada nota de `criterios.md`». Lo que hay hoy (inventario del issue #41, §1 y §4):
- Una nota de `criterios.md` (plantilla de `/hack-note`, también la de Anotar) es una cabecera `## <AAAA-MM-DD HH:MM> · <quién> (<papel>)` y las líneas Dónde, Qué dijo, Fuerza, Afecta a y Anotado por. **No tiene id**: «fecha hora» se puede repetir (dos personas en el mismo minuto). La hora va sin zona horaria.
- El relay ya la lee (`novedades_de`), pero solo para las novedades: se queda con quién, qué dijo, autor y hora, y pierde Fuerza, Dónde y Afecta a.
- **Nada enlaza una nota con una tarea** de forma que lo lea el código. Solo hay una convención para los modelos: la etiqueta `(criterios: <fecha hora>)` de `/hack-check` y `/hack-pitch`. `/hack-plan` no lee `criterios.md`.
- El campo `tareas[].evidencia` («comprobación del revisor o commit que la publica») está en el esquema, pero no lo rellena nadie.
- Lo que el OS ya deriva y podría servir de evidencia: el estado de la tarea (`publicada`, `cerrada`), la fusión aprobada (sha y veredicto), el commit con su ID que llega a `origin/main`, la Prueba de una conexión (ADR-0011, solo si se corre en una sesión de Claude Code) y la salud de un servicio.
- **No hay ningún `criterios.md` real relleno** en el repo (Paso 0). El ensayo sigue aplazado.

Valen la constitución II (lo declarado se muestra como declarado y no sustituye a lo derivado), III (procedencia y antigüedad), IV y ADR-0009 (mismos campos en la web, `estado-equipo.md` y el MCP; con la excepción de la decisión 7) y V (el texto de las notas es dato).

## Decisión (común)
- **Detrás de su interruptor**, `vista_jurado:` en `os.md` (decisión 8A). Apagado, ni el relay lee nada nuevo ni la vista lleva el bloque `jurado`: `estado.json`, la vista y `estado-equipo.md` salen byte a byte como en la 0.4.0 (constitución I).
- **Dónde se calcula:** el relay pone en `estado.json` las notas leídas de `origin/main` (con su clave y todos sus campos), las etiquetas del plan y del pitch y la historia de cada tarea; `proyeccion.vista` calcula el bloque `jurado`. La web solo lo pinta (ADR-0009). El cálculo es una función pura con su tabla de casos (`hkos/jurado.py`).
- **Seis estados de cobertura por nota, cada uno `{valor, fuente, observado_en}` y `viejo`:**
  - `sin_tarea`: nada la recoge;
  - `ambigua`: solo la recoge una etiqueta que casa con más de una nota (decisión 2). Se dice, no se elige una;
  - `en_pitch`: solo la recoge el pitch, «recogida en el pitch (declarado)» (decisión 5);
  - alguna tarea la declara (decisión 3), pero falta lo que pide la decisión 4 (ajuste 2: lo que antes era `declarada`, en dos):
    - `planificada`: ninguna de sus tareas ha empezado;
    - `en_curso`: alguna de sus tareas tiene señales;
  - `cubierta`: lo pide la decisión 4, con la evidencia y la hora de cada pieza.

  «Sin cubrir» es todo lo que no es `cubierta`, sin contar las corregidas: `sin_tarea` + `ambigua` + `planificada` + `en_curso` + `en_pitch` (ajuste 2). Una cita de la etiqueta que no casa con ninguna nota sale aparte, como enlace roto (declarado, con su tarea).
- **Corregida por.** Una nota que otra posterior dice corregir («corrige la nota del <fecha hora>», que es como lo escribe `/hack-note`) sale **corregida por** la nueva, y cuenta la nueva. Es texto que escribe una persona: la relación se enseña como declarada, `corregida_por` = `{valor, fuente: "declarado", observado_en}` (issue #46, M20). Si la cita casa con más de una nota, no se marca ninguna.
- **Orden:** primero las sin cubrir, por fuerza (`dato`, «obligatorio», «se valora», «nos gustaría ver», otra palabra, «comentario suelto», «sin precisar») y luego por hora (la más antigua primero); después las cubiertas, por hora; al final las corregidas. La vista llega ordenada: la web no ordena.
- **Nunca «cubierta» porque algo lo declare.** Una tarea `cerrada` a mano (⚑) o `reclamada` desde la web es declarada: deja la nota en `planificada` o `en_curso`, con su ⚑, nunca como evidencia. El pitch tampoco cubre.
- **La evidencia se enseña siempre que exista**, aunque la nota no llegue a `cubierta`: el sha del commit o de la fusión que publicó la tarea y el resultado de la Prueba de sus conexiones, con su procedencia y su hora. Si su fuente está vieja (`umbral_viejo_s`), la evidencia y la cobertura salen viejas (III, R-12).
- **`tareas[].evidencia`** se rellena (por fin) con el sha del commit con ID o de la fusión aprobada que la llevó a `publicada`, para esta vista y para la ruta crítica (ADR-0013). Desde el ajuste 6, `{valor, tipo, fuente, observado_en}`: el último sha publicado, con su hora.
- **Las notas son dato** (V): en la web y en el MCP, entrecomilladas, con quién lo dijo, su papel y «Anotado por», saneadas con `sanear` y equilibradas como las novedades. Una nota que dice «haced X» no se convierte en una orden para nadie.
- **Solo lo del equipo:** como las novedades, solo cuenta lo que está en `criterios.md`, `plan.md` y `pitch.md` de `origin/main`.
- **Prueba doble de ADR-0009:** `igualdad.py` con el guion nuevo **G13** (jurado), y Vitest pinta G13 y comprueba cada estado, enlace y evidencia en el DOM.

## Decididas (2026-10-19)

| Decisión | Elegida | Por qué |
|---|---|---|
| **1. Qué se cubre** | **A.** Solo las notas de `criterios.md`, como dice R-35. La rúbrica de `analisis.md` sigue en `/hack-check` | Lo más barato y R-35 no cambia. Las notas tienen formato fijo y solo las escriben personas; leer la rúbrica exigiría fijar el formato de un texto que escribe un modelo |
| **2. Id de una nota** | **A.** Clave derivada en el relay: 12 hex del sha256 de la cabecera, «Qué dijo» y «Anotado por», como la clave de fila de `servicios.md`. Las personas la siguen citando por «fecha hora» o «fecha hora · quién» | El formato de `criterios.md` no cambia y las notas no se editan (solo se añaden), así que la clave es estable. «· quién» deshace la mayoría de las coincidencias; lo que siga casando con dos sale `ambigua` |
| **3. Quién declara qué cubre una nota** | **A.** La etiqueta `(criterios: <cita>[, <cita>…])` al final de la celda «Cómo se comprueba» de la fila del plan, que ponen `/hack-plan` y `/hack-check aplicar`. Se lee de `plan.md` de `origin/main` y se pinta «declarado (plan)» | Reutiliza la convención que `/hack-check` ya exige, sin acción nueva en la web, y funciona sin GitHub. En «Cómo se comprueba» y no en «Tarea», para que el título de la tarjeta y del issue quede limpio. Cambia la huella del issue (reescribe esos issues, R-30): se acepta |
| **4. Qué es «cubierta»** | **A.** Todas las tareas que la declaran están `publicada` o `cerrada` (derivado; una `cerrada` a mano no cuenta). La Prueba de una conexión de la tarea se enseña **como evidencia, no es condición** | Solo usa lo que el OS ya deriva bien: «está en `main`». La Prueba solo se ve si se corre en Claude Code (ADR-0011); exigirla dejaría notas sin cubrir por falta de una señal que no depende del trabajo |
| **5. Evidencia que no sale del OS** | **B.** La etiqueta en `.hackathon/pitch.md` (la que ya pone `/hack-pitch`) da «recogida en el pitch (declarado)» (`en_pitch`), nunca `cubierta` | Distingue «nadie lo ha recogido» de «está en el pitch» sin inventar evidencia. Un fichero en `main` como evidencia (C) se leería como «cubierta» sin decir nada de su contenido |
| **6. Una tarea publicada que vuelve a `en_curso`** | **B.** La nota sigue `cubierta` con la evidencia de antes y «trabajo nuevo desde HH:MM» | Lo publicado sigue en `main`: la evidencia sigue siendo verdad, y la vista no parpadea con cada arreglo |
| **7. Qué lleva `estado-equipo.md`** | **B.** Una línea de resumen («2 sin cubrir (1 «obligatorio») · 1 cubierta de 3») en la sección `## Jurado y ruta`; el detalle, en el MCP (`jurado`) y la web. Nota en ADR-0009 | Lo más barato en tokens (R-24, R-25b, X). La igualdad compara la línea con la vista, y el detalle del MCP y de la web sale del mismo bloque |
| **8. Interruptores** (vale también para ADR-0013) | **A.** Uno por vista en `os.md`: `vista_jurado:` y `ruta_critica:`, apagados por defecto e independientes de `web_nueva:` | Cada una se prueba y se recorta sola (orden de recorte de M10). El md y el MCP no dependen de la web |

## Ajustes tras la revisión (2026-10-19, issue #46)
Decididos por el usuario sobre las «Decisiones que faltan» de la revisión de los contratos de M10. Mandan sobre lo de arriba donde lo contradigan.

| Ajuste | Elegido | Por qué |
|---|---|---|
| **2. «Sin cubrir» y lo que era `declarada`** | «Sin cubrir» = todo lo no cubierto, sin las corregidas. `declarada` se parte en `planificada` (sus tareas no han empezado) y `en_curso` (alguna tiene señales). `jurado.cuenta` = `{notas, corregidas, cubiertas, sin_cubrir, sin_tarea, ambiguas, planificadas, en_curso, en_pitch, sin_cubrir_por_fuerza}`, con `sin_cubrir` = `sin_tarea` + `ambiguas` + `planificadas` + `en_curso` + `en_pitch`. Una ambigua no cuenta en `sin_tarea` | «Sin cubrir» tenía tres significados (ADR, hechos de G13, pantalla) y así no se cumple md = web (A2). La pantalla distingue «planificada» y «en curso», y la web no puede calcularlo (M8): sale del bloque |
| **6. La evidencia tras volver a publicar** (decisión 6B) | `tareas[].evidencia` = `{valor: sha, tipo: "commit" \| "fusion", fuente, observado_en}`: el **último** sha publicado, con la hora de ese paso a `publicada`. Una tarea `parada` o `no_cerrada` después de `hecha_en` sigue contando como hecha, como `en_curso`, `en_revision` e `integrada` | El sha suelto no decía ni su hora ni si era commit o fusión, y `evidencias[].tipo` lo exige (M6). El último es lo que está en `main` ahora. Sin `parada` ni `no_cerrada`, una tarea publicada que se queda quieta tras un arreglo bajaba la nota de `cubierta`: el parpadeo que 6B quería evitar (M7) |
| **7. Delta y MCP** (decisiones 7B y 8A) | El delta de `## Jurado y ruta` se filtra **por línea y firma**: la línea del jurado solo va si cambia `jurado:`, y la de la ruta solo si cambia su veredicto (ADR-0013, R10A). Las herramientas `jurado` y `ruta` del MCP **solo se listan con su interruptor encendido**: con los dos apagados, `tools/list` es el de la 0.4.0 | Con el filtro por texto, un cambio en el jurado arrastraba la línea de la ruta, que se mueve con el reloj (M18). Con los interruptores apagados, todo tiene que salir como en la 0.4.0 (constitución I, criterio 1 de M10), también el MCP (M19) |

## Alternativas descartadas
- **Que un modelo decida qué cubre cada nota** (lo que hace hoy `/hack-check` en `verificacion.md`): es lo que dice un modelo, no una señal (constitución II). Sigue como ayuda para poner las etiquetas de la decisión 3.
- **Que el OS ejecute «Cómo se comprueba»** para obtener evidencia: es ejecutar código que un agente puede haber cambiado (como la Prueba en ADR-0011).
- **Puntuar o estimar la nota del jurado**: no hay señal que lo sostenga.
- **Una línea `- ID:` en las notas** o **`.hackathon/jurado.md`**: cambian la cadena o añaden un fichero que nadie mira, para lo que la clave derivada y la etiqueta del plan ya dan.
- **Marcar la cobertura desde la web**: acción nueva (ADR-0010), fuera de M10.

## Riesgos aceptados
- «Cubierta» dice que hay trabajo publicado que alguien declaró ligado a la nota, no que el jurado vaya a darlo por bueno.
- Las etiquetas las pone un modelo o una persona: un enlace mal puesto da una cobertura falsa, que se ve como «declarado (plan)» con su tarea.
- La rúbrica del enunciado no sale en la vista: lo que más puntúa sigue en `/hack-check`.
- Un agente que no llame al MCP solo ve la línea de resumen, no qué nota falta.
- La hora de la cabecera de las notas no lleva zona horaria: se lee con la de `equipo.md` (ADR-0013), no con la del relay; sin ella, la nota sale sin hora absoluta.
