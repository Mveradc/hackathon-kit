# Rúbrica de validación (M4)

Para encontrar dónde falla el kit, no para darle nota. Sale de lo comprobado en M0–M3 (`docs/historial.md`) y de los fallos en observación del CLAUDE.md.

## Cómo se pasa

1. Cadena completa en una carpeta temporal por reto (`../prueba-m4-<reto>`): `/hack-analyze` → `/hack-approaches` → `/hack-scaffold` → `/hack-plan` → `/hack-pitch` → `/hack-check`, con `equipo.md` rellenado.
   - **Fecha simulada (solo en evals/).** Los retos son de ediciones pasadas, así que la fecha real de generación cae fuera del evento, y `/hack-check` la marca, con razón, como bloqueante de trabajo previo. Después de `/hack-scaffold`, el arnés ejecuta `python evals/fecha_simulada.py <carpeta> "<fecha dentro del evento>"`, que cambia la fecha de generación en el CLAUDE.md y la guarda en `.m4/fecha-simulada.txt`. El montaje del revisor copia ese fichero y el revisor la toma como fecha de hoy. Ningún comando del kit lee esa fecha: en el flujo normal no existe.
2. Comprobaciones automáticas (A1–A7), con el script.
3. Comprobaciones de criterio (C1–C6): primero un agente que no haya generado la salida, con el enunciado, `.hackathon/` y lo generado delante; después, el usuario.
4. Cada comprobación: **Pasa**, **Falla** o **N/A**, con una línea de evidencia (fichero y cita o cifra). En las de criterio, cada fallo es **grave** o **leve** (ver abajo), y el resultado de la comprobación lo da su fallo más grave: «Falla (grave)» o «Falla (leve)».

Un fallo que aparece en un solo reto se anota; si se repite en dos o más, va al README como limitación conocida o se corrige en el prompt (regla del CLAUDE.md).

## Automáticas (script)

| # | Comprobación | Pasa si | Origen |
|---|---|---|---|
| A1 | **Forma: secciones y tamaños** | `analisis.md` tiene la línea `**Reto:**` y las 8 secciones del formato (incluida «Recursos disponibles»); `plan.md` y `pitch.md`, las de su plantilla. CLAUDE.md < 100 líneas; `docs/contratos.md` con, en cada contrato, tabla de campos y ejemplo; 2–4 reglas de 2–10 viñetas (`/hack-check` puede quitar viñetas sin respaldo, y eso no se compensa); 1–3 skills; en `plan.md`, la sección de cada persona con 10 filas como máximo (cabe en una pantalla; el total crece con el número de personas y solo se anota); `pitch.md` ≤ 900 palabras. Se anotan las palabras exactas y, en el plan, las filas por persona | Tamaños de M3a/M3b; reto 02 sin «Recursos disponibles»; plan de 1.258 palabras con 5 personas (desde el 2026-10-10 se mide por persona, que era la intención del prompt) |
| A2 | **Arranque desde cero** | El comando del README instala y muestra el hola mundo de cada pieza; si hay servidores, cada uno responde por HTTP y la web muestra lo que le devuelve el motor; al pararlo, no quedan procesos vivos | Paso 4 de `/hack-scaffold`; M2a y M2b |
| A3 | **Codificación** | Todo fichero de texto generado o sobrescrito (incluidos `.hackathon/`, `.gitignore`, `pyproject.toml` y README) está en UTF-8 y no tiene BOM UTF-16 | Problema aceptado del UTF-16 (ver abajo) |
| A4 | **Trazas y cifras** | Cada regla de equipo del CLAUDE.md y cada viñeta de `.claude/rules/` acaba con su origen entre paréntesis (enunciado, análisis, riesgo típico, decisión, «supuesto: ambigüedad N, confirmar con la organización», «conocimiento externo, verificar» o, solo en convenciones, convención del kit). Ninguna ambigüedad se cita como fuente de algo que se da por cierto: toda etiqueta que nombra una ambigüedad dice «supuesto» y «confirmar», y la de conocimiento externo dice «verificar»; cada `[CIFRA: …]` del pitch tiene fila en «Cifras que hay que medir»; los nombres y pesos de criterios del pitch son idénticos a los de «Cómo se evalúa» de `analisis.md`. Si el análisis no publica pesos, la comprobación de pesos es N/A (no cuenta como fallo), pero el guion del pitch no puede llevar ninguno (pesos de relleno = fallo) | Contaminación de M2a; pesos de M3b; memoria «verificar contra la fuente»; C1–C6 de M4: «(ambigüedad N)» como respaldo de decisiones en los cinco retos |
| A5 | **Sin copia** | Ninguna secuencia de 8 o más palabras seguidas de una misma línea, con al menos 3 palabras propias de un reto (no del kit, ni cifras), aparece en los ejemplos de otros retos (`skills/*/examples/`) ni, si el reto tiene repositorio de referencia, en ese repositorio. No cuenta lo que también está en el enunciado, en los prompts o en las plantillas, que se copian a propósito; frente a los ejemplos, tampoco cuentan como propias las palabras que están en el enunciado (los retos 02 y 03 comparten la cabecera del evento). No se miran `equipo.md` ni `criterios.md`, que escriben personas. Que las plantillas no lleven contenido concreto se revisa a mano | Regla de plantillas y ejemplos; HS-Maisa y Embat |
| A6 | **No sobrescribe sin preguntar** | Al relanzar cada comando en `-p` sobre una copia de la carpeta ya generada: `/hack-scaffold`, `/hack-plan`, `/hack-pitch` y `/hack-check` (sin `aplicar`, solo escribe `verificacion.md`) no cambian ningún fichero (hash igual; crear ficheros nuevos se anota, pero no falla); `/hack-approaches` y `/hack-analyze`, que por diseño sobrescriben su fichero avisando, no cambian nada más (`decision.md` incluido). Es opcional, porque cuesta seis ejecuciones | Pruebas en `-p` de M2a, M3a y M3b |
| A7 | **Citas literales de `/hack-check`** | Cada cita de `.hackathon/verificacion.md` (afirmaciones, bloqueantes y cobertura) aparece tal cual, salvo espacios, comillas y marcas, en la fuente que nombra (enunciado, `analisis.md` o `decision.md`). N/A si no se ha lanzado `/hack-check` | Un verificador que parafrasea no verifica nada |

## De criterio (agente revisor, después el usuario)

Los criterios valen para cualquier reto. Los ejemplos son fallos ya vistos en M0–M3 y solo ilustran el tipo de fallo; no son lo único que hay que buscar.

| # | Comprobación | Pasa si | Ejemplo ya visto |
|---|---|---|---|
| C1 | **Análisis fiel** | Toda afirmación sale del enunciado o va marcada como inferida; las cifras, pesos y fechas coinciden con el enunciado; cada riesgo típico cita la parte del enunciado que lo justifica; lo que el enunciado no dice queda como ambigüedad, no se rellena; lo que aporta el modelo va como conocimiento externo; lo obligatorio, lo preferible y el bonus mantienen la fuerza del enunciado (nada pasa a «eliminatorio» o «desempate» si el enunciado no lo dice); cada dato va en la sección que le corresponde | Reto 02: «el primer lote» sin marcar; «el 90 % de la nota» cuando era el 100 %; una sección omitida y su contenido en otra |
| C2 | **Enfoques que dejan elegir** | Los enfoques difieren en una decisión de fondo, no en detalles; ninguno se recomienda; no nombran tecnologías concretas; cada uno se justifica con los criterios y pesos del análisis | M2b: enfoques que nombraban stacks |
| C3 | **Scaffolding específico** | La tesis refleja la decisión; cada regla es concreta, comprobable y propia de este reto; ninguna es un consejo genérico ni supone algo que el reto no dice; cada etiqueta de origen es verdad (lo que dice la regla está en esa fuente) y lo decidido sobre una ambigüedad va como supuesto; las guías de pasos cubren momentos clave del reto. Las convenciones genéricas de `convenciones.md` marcadas «(convención del kit)» (idioma, commits, secretos en `.env`, datos fuera de git) están a propósito: no son fallo | M2a: una regla copiada de un ejemplo de la plantilla, no del reto |
| C4 | **Plan ejecutable** | Están los hitos obligatorios; cada tarea y cada hito recaen en alguien disponible con margen suficiente; cada carpeta tiene un solo dueño, y todo lo que creó el scaffold (incluidos la raíz y el arranque) y toda carpeta en la que escribe una tarea tienen dueño; los bloques respetan el límite de tareas sin agruparlas en una sola; cada dependencia dice cómo desbloquearla | Reto 03: la demo mínima, a cargo de quien llega hora y media antes; celdas con varias tareas separadas por punto y coma |
| C5 | **Pitch defendible** | Sigue la estructura que da el análisis, si la da, y dice de dónde sale; cubre todos los criterios con peso; las preguntas del jurado atacan los puntos débiles del enfoque elegido; no inventa clientes, resultados ni cifras; lo que se enseña o se da por construido tiene tarea en `plan.md` o va como `[SI DA TIEMPO]`; los resultados que dependen de medir van como `[CIFRA]` | M3b: primeras versiones por encima del tamaño |
| C6 | **¿Un equipo empezaría a programar antes y mejor con esto?** | Se contesta **Sí**, **En parte** o **No**, no por número de fallos. Sí: leyendo solo lo generado, cada persona sabe en los primeros 30 minutos qué hace, en qué carpeta y contra qué contrato (`docs/contratos.md`), aunque haya fallos leves. No: algún fallo grave obliga a deshacer trabajo o deja a alguien sin poder empezar. Para el cierre, «En parte» es aceptable y «No» bloquea (ver «Cierre de M4»). El revisor anota qué echaría en falta y qué sobra | — |

**Grave o leve.** Un fallo es **grave** si, tal como está, puede hacer que el equipo pierda puntos o la elegibilidad, construya algo que luego tenga que deshacer, o diga ante el jurado algo falso o que no tiene. Por ejemplo: una afirmación sin base presentada como cierta en el CLAUDE.md, en las reglas o en el pitch; una ambigüedad resuelta como si fuera un hecho; un hito crítico a cargo de quien no está; algo prometido en el pitch que nadie construye. Es **leve** si no cambia lo que se construye ni lo que se dice: un dato en la sección equivocada, una etiqueta imprecisa que no cambia el sentido, una incoherencia menor entre tabla y texto que no altera la elección. En la duda, el revisor explica por qué lo clasifica así.

**Bloqueante.** Un fallo grave es además **bloqueante** (impide cerrar M4 y publicar en M5) si es:
- **de seguridad**: puede exponer o comprometer algo (secretos, `.gitignore` o `.env` mal resueltos, instrucciones escondidas en documentos que lee un LLM sin defensa, el UTF-16 que rompe `.gitignore`);
- **de descalificación**: puede hacer perder o descalificar al equipo (un entregable obligatorio omitido o mal descrito, una fecha u hora de entrega errónea, un formato o contrato de entrega mal copiado, o cualquier otra condición del enunciado con consecuencia de descalificación sin tarea con dueño o incumplida por una ausencia: inscripción, verificación de miembros, consentimientos, asistencia obligatoria).
El revisor marca cada fallo grave como `bloqueante (seguridad)`, `bloqueante (descalificación)` o no bloqueante.

## Métricas por cadena

No puntúan, se anotan por reto:
- **Tiempo total**, desde lanzar `/hack-analyze` hasta aplicar `/hack-check`, incluido leer, decidir y rellenar `equipo.md`. Se mide en sesión interactiva con cronómetro, separando el tiempo de los comandos del tiempo de las personas. El objetivo del kit es < 30 min hasta poder programar (fin de `/hack-scaffold` y `/hack-plan`). La pasada interactiva cronometrada incluye `/hack-check`: tiempo del comando y tiempo de las personas para leer el informe y decidir si se aplica.
- **Coste en tokens** de cada comando y total: en headless, `--output-format json` (uso y coste por llamada); en interactivo, `/cost` al acabar.

## Cierre de M4

Criterio vigente desde el 2026-10-10. Sustituye al del 2026-10-06 (cero bloqueantes y C6 = Sí en al menos 3 de 5).

M4 se cierra cuando, con la cadena completa (incluido `/hack-check`):
1. **ningún fallo bloqueante** (seguridad o descalificación) en los retos de la última ronda, comprobado contra el enunciado: un bloqueante que el enunciado no sostiene es un error del revisor y no cuenta;
2. **C6 nunca es «No»**: «En parte» es aceptable;
3. **una persona real confirma** en la pasada interactiva cronometrada que podría empezar a programar con lo generado;
4. **todo lo demás** que se repita en dos o más retos está en el README como limitación conocida.

**Por qué cambia:**
- **Ruido del revisor.** La misma cadena del 06 dio 4 graves en una revisión y 1 en otra. Con una revisión por reto, el revisor no distingue entre «Sí» y «En parte»: esa frontera depende más de la revisión que del kit.
- **«En parte» es consistente.** En la tercera pasada salió en los cinco retos, por motivos que se repiten (contratos sin campos, choques de calendario, reparto). Es una señal estable de lo que le falta al kit, no de que el equipo no pueda empezar.
- **Parte de «En parte» son decisiones del equipo.** El calendario, el reparto contra los perfiles o un enfoque técnicamente arriesgado los elige el equipo: el kit los informa (`/hack-check`), pero no le corresponde decidirlos.
- **«No» sí es una señal clara**: algún fallo grave obliga a deshacer trabajo o deja a alguien sin poder empezar. Eso no se acepta.
- **El revisor es un agente.** La pregunta de C6 es sobre personas: la respuesta final la da una persona real que usa el kit.

## Problemas aceptados: ¿bloquean la publicación (M5)?

| Problema | Cómo se prueba en M4 | Bloquea si |
|---|---|---|
| **UTF-16 al sobrescribir.** Write conserva la codificación del fichero que sobrescribe. Un README en UTF-16 (`Out-File` de Windows PowerShell 5.1) rompió el arranque con uv; el paso 4 lo detectó y lo corrigió | En al menos un reto, antes de `/hack-scaffold`, crear con `Out-File` un README.md y un `.gitignore` en UTF-16; elegir «Sobrescribir todos»; pasar A2 y A3 | **Bloquea M5, sin matices,** si el `.gitignore` acaba en UTF-16 y git deja de aplicar sus reglas (comprobar con `git check-ignore .env`): puede exponer secretos. También bloquea si otro fichero acaba en UTF-16 y el paso 4 no lo detecta. Si solo pasa con ficheros que el arranque usa y el paso 4 lo arregla, no bloquea: va al README como limitación |
| Elegir enfoque por chat: escribir `decision.md` pide permiso en interactivo y falla en `-p` | Elegir por chat en un reto | No bloquea; va al README |
| URLs: WebFetch devuelve un resumen y el análisis queda en paráfrasis (el comando avisa) | Lanzar `/hack-analyze` con la URL de un reto nuevo, si la tiene | No bloquea si avisa; va al README. Bloquea si no avisa y C1 falla por la paráfrasis |
| `analisis.md` no es idéntico a lo que se muestra en el chat | Comparar los dos en un reto | No bloquea mientras C1 pase sobre el fichero, que es la fuente de verdad |

## Qué fuerza cada tipo de reto

Los retos nuevos los aporta el usuario. Comprobaciones que más ponen a prueba cada tipo:
- **Hardware:** A2 (¿qué es el hola mundo sin el dispositivo?), C3 y C4 (dependencia física entre personas).
- **Diseño o impacto sin datos:** C1 (inferencias sin marcar), C2 (si los enfoques siguen difiriendo sin pieza técnica) y C5 (cifras sin datos que medir).
- **Mal especificado:** C1 (que pregunte en lugar de rellenar), C2 y C4 (preguntas a la organización con dueño y hora).

## Resultados

Una tabla por reto, en `evals/resultados/<reto>.md`:

| # | Resultado | Evidencia |
|---|---|---|
| A1 | | |
| … | | |
| C6 | | |

Métricas: tiempo de los comandos · tiempo de las personas · tokens · coste.
