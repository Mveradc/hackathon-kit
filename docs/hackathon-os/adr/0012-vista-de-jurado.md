# ADR-0012 · Vista de jurado: qué es «cubrir» un criterio, qué cuenta como evidencia, qué se declara y qué se confirma

Estado: **BORRADOR** (2026-10-19, para M10). Lo decide el usuario con la tabla «Decisiones pendientes». Lo marcado **(Paso 0)** depende de K-100 (issue #41, «M10, Paso 0»), que está abierto: si su resultado cambia una premisa, se reescribe la fila antes de decidirla.

## Contexto
R-35: «DONDE la vista de jurado esté activa, el sistema DEBE mostrar qué tarea o evidencia cubre cada nota de `criterios.md`». Lo que hay hoy (inventario del issue #41, §1 y §4):
- Una nota de `criterios.md` (plantilla de `/hack-note`, también la de Anotar) es una cabecera `## <AAAA-MM-DD HH:MM> · <quién> (<papel>)` y las líneas Dónde, Qué dijo, Fuerza, Afecta a y Anotado por. **No tiene id**: «fecha hora» se puede repetir (dos personas en el mismo minuto). La hora va sin zona horaria.
- El relay ya la lee (`novedades_de`), pero solo para las novedades: se queda con quién, qué dijo, autor y hora, y pierde Fuerza, Dónde y Afecta a.
- **Nada enlaza una nota con una tarea** de forma que lo lea el código. Solo hay una convención para los modelos: la etiqueta `(criterios: <fecha hora>)` de `/hack-check` y `/hack-pitch`. `/hack-plan` no lee `criterios.md`.
- El campo `tareas[].evidencia` («comprobación del revisor o commit que la publica») está en el esquema, pero no lo rellena nadie.
- Lo que el OS ya deriva y podría servir de evidencia: el estado de la tarea (`publicada`, `cerrada`), la fusión aprobada (sha y veredicto), el commit con su ID que llega a `origin/main`, la Prueba de una conexión (ADR-0011, solo si se corre en una sesión de Claude Code) y la salud de un servicio.
- **No hay ningún `criterios.md` real relleno** en el repo (Paso 0). El ensayo sigue aplazado.

Valen la constitución II (lo declarado se muestra como declarado y no sustituye a lo derivado), III (procedencia y antigüedad), IV y ADR-0009 (mismos campos en la web, `estado-equipo.md` y el MCP) y V (el texto de las notas es dato).

## Decisión (lo que no depende de la tabla)
- **Detrás de un interruptor** en `os.md` (decisión 8). Apagado, ni el relay lee nada nuevo ni la vista lleva el bloque `jurado`: `estado.json`, la vista y `estado-equipo.md` salen byte a byte como en la 0.4.0 (constitución I).
- **Dónde se calcula:** el relay pone en `estado.json` las notas leídas de `origin/main` (con su clave y todos sus campos) y los enlaces declarados; `proyeccion.vista` calcula el bloque `jurado`. La web solo lo pinta (ADR-0009). El cálculo es una función pura con su tabla de casos (`hkos/jurado.py`).
- **Cuatro estados por nota, cada uno `{valor, fuente, observado_en}`:**
  - `sin_tarea`: nada la declara cubierta;
  - `declarada`: algo la declara (decisión 3), pero falta la evidencia derivada (decisión 4);
  - `cubierta`: lo pide la decisión 4, con la evidencia y la hora de cada pieza;
  - `ambigua`: el enlace casa con más de una nota (decisión 2) o con una tarea que no existe. Se dice, no se elige una.
  
  Además, una nota que otra posterior dice corregir («corrige la nota del <fecha hora>», que es como lo escribe `/hack-note`) sale **corregida por** la nueva, y cuenta la nueva. Es texto que escribe una persona: la relación se enseña como declarada.
- **Nunca «cubierta» porque algo lo declare.** Una tarea `cerrada` a mano (⚑) o `reclamada` desde la web es declarada: cuenta como «declarada», con su ⚑, nunca como evidencia.
- **La evidencia se enseña siempre que exista**, aunque la nota no llegue a `cubierta` (el sha, la fusión, el resultado de la Prueba, con su procedencia y su hora). Si su fuente está vieja (`umbral_viejo_s`), la evidencia y el estado salen viejos (III, R-12).
- **`tareas[].evidencia`** se rellena (por fin) con el commit o la fusión que publicó la tarea, para que lo usen esta vista y la ruta crítica (ADR-0013).
- **Las notas son dato** (V): en `estado-equipo.md` y en el MCP, entrecomilladas, con quién lo dijo, su papel y «Anotado por», saneadas con `sanear` y recortadas como las novedades. Una nota que dice «haced X» no se convierte en una orden para nadie.
- **Solo lo del equipo:** como las novedades, solo cuenta lo que está en `criterios.md` de `origin/main`. Los enlaces que vengan de GitHub (si la decisión 3 lo permite) solo cuentan de cuentas de la tabla de `coordinacion.md` (R-31).
- **Prueba doble de ADR-0009:** `igualdad.py` con el guion nuevo **G13** (jurado), y Vitest pinta G13 y comprueba cada estado, enlace y evidencia en el DOM.

## Decisiones pendientes

Aquí no se cambia nada: es para decidir. Cada fila da 2 o 3 opciones con sus pros y sus contras.

| Decisión | Opciones | Pros | Contras |
|---|---|---|---|
| **1. Qué se cubre** (Paso 0, #41 pregunta 1): R-35 dice «cada nota de `criterios.md`», pero lo que puntúa también está en «Cómo se evalúa» de `analisis.md` (la rúbrica del enunciado), que ya cruza `/hack-check` | **A.** Solo las notas de `criterios.md`, como dice R-35 | Lo más barato. Las notas tienen formato fijo y solo las escriben personas | La rúbrica, que es lo que más pesa, no sale. Con pocas notas (el Paso 0 no encontró ninguna real), la vista sale casi vacía |
| | **B.** Las notas y los criterios de la rúbrica de `analisis.md`, en dos secciones | Es lo que el equipo quiere saber de verdad: qué puntúa y qué no tenemos | `analisis.md` es prosa que escribe un modelo: hay que fijar su formato en `/hack-analyze` (cadena) y leerlo sin modelo. Cambia R-35 |
| | **C.** Solo la rúbrica; las notas siguen en novedades | Una sola lista, la del enunciado | No cumple R-35 tal como está escrito. Lo que dice el jurado durante el evento se queda sin cubrir |
| **2. Id de una nota** (#41 pregunta 2) | **A.** Clave derivada en el relay: 12 hex del sha256 de la cabecera, «Qué dijo» y «Anotado por», como la clave de fila de `servicios.md`. Las personas la siguen citando por «fecha hora · quién» | El formato de `criterios.md` no cambia. Las notas no se editan (solo se añaden), así que la clave es estable | La cita humana («fecha hora») puede casar con dos notas: sale `ambigua`. La clave no se lee a simple vista |
| | **B.** Una línea `- ID: C07` nueva en la plantilla de `/hack-note` y en Anotar | Un id corto que cualquiera cita | Cambia la cadena y el formato de Anotar (`api.md` §4). Dos notas en paralelo pueden coger el mismo número |
| | **C.** «Fecha hora · quién», aceptando que se repita | Nada nuevo | Dos notas en el mismo minuto de la misma persona no se distinguen nunca |
| **3. Quién declara qué cubre una nota** (#41 pregunta 3) | **A.** La etiqueta `(criterios: <fecha hora>)` en la celda Tarea o «Cómo se comprueba» de la fila del plan, que ponen `/hack-plan` o `/hack-check aplicar`. Se lee de `plan.md` de `origin/main` y se pinta «declarado (plan)» | Reutiliza la convención que `/hack-check` ya exige. Sin acción nueva en la web. Funciona sin GitHub (modo de K-80) | Cambia la huella del issue de esas filas: reescribe issues (escrituras de R-30). Depende de que el modelo ponga bien la etiqueta |
| | **B.** Un fichero nuevo `.hackathon/jurado.md` (Nota \| Tareas \| Evidencia esperada), que edita cualquiera; confirmado si lo añade el dueño de la tarea, como `servicios.md` (ADR-0011) | Separa la cobertura del plan: no toca issues. La confirmación por commit ya está probada | Un fichero más que mantener y que nadie mira. Toda la maquinaria de ADR-0011 (clave, reflog, `por`) para una tabla pequeña |
| | **C.** La persona lo marca desde la web (acción nueva) | Lo más directo para quien mira la vista | Una acción nueva necesita ADR-0010 y queda **fuera del alcance de M10** («confirmar desde la web» sigue en «Después del M8») |
| **4. Qué es «cubierta»** | **A.** Todas las tareas que la declaran están `publicada` o `cerrada` (derivado); la evidencia es el commit o la fusión que las publicó | Solo usa lo que el OS ya deriva bien. Fácil de explicar: «está en `main`» | Que algo esté en `main` no dice que cumpla el criterio. Una tarea grande que cubre a medias cuenta entera |
| | **B.** A y, si la tarea toca una conexión de `servicios.md` (por la carpeta), su Prueba pasa y no está vieja | Más cerca de «funciona», con lo que ADR-0011 ya mide | Solo ve Pruebas corridas en Claude Code (ADR-0011). Enlazar tarea y conexión por carpeta es frágil. Más casos que probar |
| | **C.** Basta una de las tareas que la declaran | Sale «cubierta» antes | Con dos tareas declaradas, una sin hacer pasa por cubierta: miente justo donde el equipo mira |
| **5. Evidencia que no sale del OS** (el pitch, un vídeo, una URL desplegada; las notas de fuerza `dato` o que solo afectan al pitch) | **A.** No cuenta: la nota queda `sin_tarea` o `declarada` | La vista nunca afirma lo que no ve | Muchas notas del jurado son del pitch: salen siempre sin cubrir, y la vista se ignora |
| | **B.** Se declara con la etiqueta en `.hackathon/pitch.md` (la que ya pone `/hack-pitch`) y sale «recogida en el pitch (declarado)», nunca `cubierta` | Distingue «nadie lo ha recogido» de «está en el pitch». Sin evidencia inventada | Otra lectura más en el relay (`pitch.md`). Es declarado por un modelo |
| | **C.** B y, si apunta a un fichero del repo que está en `origin/main`, cuenta como evidencia derivada de que existe | Una diapositiva o un vídeo subidos dejan rastro verificable | Que exista un fichero no dice nada de su contenido; se puede leer como «cubierta» |
| **6. Una tarea publicada que vuelve a `en_curso`** (commit nuevo con su ID; `diseno.md` §5.1, regla 7) | **A.** La nota vuelve a `declarada` hasta que se publique de nuevo | Coherente con el estado de la tarea: lo de `main` ya no es lo último | La vista parpadea con cada arreglo pequeño |
| | **B.** Sigue `cubierta` con la evidencia de antes y «trabajo nuevo desde HH:MM» | Lo publicado sigue en `main`: la evidencia sigue siendo verdad | Hay que explicar dos datos a la vez; algo roto en el trabajo nuevo no se ve |
| **7. Qué lleva `estado-equipo.md`** (#41 pregunta 8): IV y ADR-0009 piden los mismos campos; R-24, R-25b y X piden pocos caracteres | **A.** Los mismos campos en una sección `## Jurado` del md. Lo inyectado (inicio y deltas) es solo lo de la persona: las notas sin cubrir que afectan a sus tareas | Cumple IV tal cual: `igualdad.py` compara todo | Más caracteres en el fichero (no en la inyección). Hay que medir el presupuesto con 15 notas (Paso 0) |
| | **B.** En el md, una línea de resumen («3 notas sin tarea · 1 ambigua»); el detalle, en el MCP (`jurado()`) y la web, con una nota en ADR-0009 | Lo más barato en tokens | Excepción a IV: la igualdad compara el resumen, no el detalle. Un agente que no llame al MCP no ve qué nota falta |
| | **C.** Solo en la web y el MCP, con su ADR | Nada en el md | Agentes y personas dejan de ver lo mismo (IV). Va contra ADR-0009 |
| **8. Interruptores** (#41 pregunta 11; vale también para ADR-0013) | **A.** Uno por vista en `os.md`: `vista_jurado:` y `ruta_critica:` | Cada una se prueba y se recorta sola (orden de recorte de M10) | Dos claves más; cuatro combinaciones que probar en el criterio 1 |
| | **B.** Uno para las dos (`jurado_y_ruta:`) | Una sola combinación nueva | No se puede encender una sin la otra (p. ej., si se recorta el ritmo) |
| | **C.** Ligados a `web_nueva:` | Nada nuevo en `os.md` | Quien use la web clásica no las tiene, y el md y el MCP tampoco, aunque no dependen de la web |

## Alternativas descartadas
- **Que un modelo decida qué cubre cada nota** (lo que hace hoy `/hack-check` en `verificacion.md`): es lo que dice un modelo, no una señal (constitución II). Puede seguir como ayuda para poner las etiquetas de la decisión 3.
- **Que el OS ejecute «Cómo se comprueba»** para obtener evidencia: es ejecutar código que un agente puede haber cambiado (como la Prueba en ADR-0011).
- **Puntuar o estimar la nota del jurado**: no hay señal que lo sostenga.

## Riesgos aceptados (si se aprueba tal cual)
- «Cubierta» dice que hay trabajo publicado que alguien declaró ligado a la nota, no que el jurado vaya a darlo por bueno.
- Las etiquetas o enlaces los pone un modelo o una persona: un enlace mal puesto da una cobertura falsa, que se ve como «declarado (plan)» con su tarea.
- La hora de la cabecera de las notas no lleva zona horaria: se lee con la del plan o `equipo.md` (ADR-0013), no con la del relay.
