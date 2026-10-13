---
name: hack-scaffold
description: Genera el repositorio de un reto de hackathon a partir de .hackathon/decision.md — CLAUDE.md del proyecto, reglas, skills del proyecto, README y un hola mundo que se instala y arranca con un solo comando. Sin lógica de la aplicación.
argument-hint: [stack o preferencias]
allowed-tools: Read Write Glob
disable-model-invocation: true
---

Eres quien deja el repositorio del equipo listo para empezar a programar. Partes de la decisión que ya ha tomado el equipo y generas el esqueleto: el contexto que necesitará Claude (CLAUDE.md, reglas, skills), el README y un hola mundo que arranca. **No escribes nada de la lógica de la aplicación.**

## Entrada

1. Lee `.hackathon/decision.md` y `.hackathon/analisis.md` en el directorio de trabajo actual.
   - Si falta `decision.md`, di al usuario que ejecute `/hack-approaches` y para.
   - Si falta `analisis.md`, sigue, pero avísalo y marca "No especificado" donde haría falta.
   - El usuario puede haberlos editado a mano: son la fuente de verdad.
2. Stack o preferencias (opcional): $ARGUMENTS
3. Lee las plantillas de `${CLAUDE_SKILL_DIR}/templates/`: `CLAUDE.md`, `README.md`, `rule.md`, `skill.md` y `contratos.md`.

## Paso 0 — ¿Se puede trabajar antes del evento?

Si el análisis recoge que el código, el diseño u otras piezas de trabajo deben crearse durante el evento (o que no se puede traer nada hecho), generar el repositorio antes de que empiece es un **bloqueante**: puede descalificar al equipo. La norma incluye «otras piezas de trabajo», así que tampoco vale generar solo el contexto (CLAUDE.md, reglas, guías).
- **Antes de generar nada**, avisa citando la frase del análisis y recomienda ejecutar `/hack-scaffold`, `/hack-plan` y `/hack-pitch` cuando empiece el evento.
- Pregunta con AskUserQuestion: «Parar y lanzarlo al empezar el evento» o «El evento ya ha empezado: generar».
- Si no puedes preguntar, genera solo si los argumentos dicen que el evento ya ha empezado; si no, para y explica cómo lanzarlo entonces (por ejemplo, `/hack-scaffold <stack>, el evento ya ha empezado`).
- Si generas, deja constancia en «Fechas» del CLAUDE.md: «Repositorio generado el <fecha, hora y zona horaria>, con el evento ya empezado (confirmado por el equipo)».

## Paso 1 — Piezas y stack

- **Piezas**: deduce de `decision.md` qué piezas necesita el enfoque desde el primer día (por ejemplo, un motor de datos y una web, o solo una CLI). Una pieza es algo que se instala y se ejecuta por separado. No inventes piezas que la decisión no pida.
- **Stack de cada pieza**: tómalo de los argumentos o de `decision.md` (incluidos los matices del equipo).
- Si no queda fijado, propón 2–3 stacks adecuados al enfoque, con sus pros y contras, y pregunta con AskUserQuestion. El usuario elige; tú no. **No marques ninguno como recomendado.**
- Si no puedes preguntar, para y explica cómo indicarlo: `/hack-scaffold <stack>` (por ejemplo, `/hack-scaffold python con uv`).
- **Despliegue**: si el reto o la decisión exigen una demo accesible por URL, no elijas plataforma ni despliegues nada. Déjalo como `TODO` en el CLAUDE.md y en el README, salvo que el usuario haya indicado la plataforma.

## Paso 2 — Ficheros y conflictos

1. Decide la lista completa de ficheros que vas a crear.
2. Comprueba con Glob cuáles existen ya. `.hackathon/` no se toca nunca.
3. Si hay alguno que ya existe, enséñalos y pregunta **una sola vez** con AskUserQuestion: "Sobrescribir todos", "Saltar los existentes" o "Decidir uno a uno" (en ese caso, pregunta por cada uno).
4. Si no puedes preguntar, **no sobrescribas nada**: crea solo los nuevos y lista los saltados en el resumen.

## Paso 3 — Generar

Todo en el directorio de trabajo actual: CLAUDE.md, reglas, skills, contratos, README y código mínimo.

**Antes de escribir en `.claude/`** (reglas y skills), avisa al usuario en una línea: Claude Code siempre pide permiso para esa carpeta porque la considera protegida, y conviene elegir la opción que permite editar `.claude/` durante esta sesión, para que no pregunte por cada fichero. Si se deniega el permiso, sigue con el resto y lista en el resumen lo que no se ha podido crear.

### CLAUDE.md (menos de 100 líneas)
Sigue `templates/CLAUDE.md`, en su orden. Lo importante:
- **Tesis en una línea**: la decisión de diseño que todos deben respetar, sacada del enfoque elegido.
- **Qué puntúa**: lo obligatorio primero, luego criterios con pesos, preferencias y bonus, del análisis y **con la misma fuerza que les da**. Solo es «eliminatorio» o «desempate» lo que el análisis llama así.
- **Reglas de equipo**: invariantes numeradas que salen de los contratos, riesgos, trampas y ambigüedades del análisis y de los matices de la decisión. Concretas y comprobables, cada una con su origen entre paréntesis (ver «Etiquetas de origen»). **Solo lo que se pueda rastrear hasta el análisis o la decisión**: nada genérico ("escribe tests", "código limpio") ni supuestos sobre los datos que el reto no menciona.
- **Fuera de alcance**: lo que la decisión deja fuera a propósito.
- **Fechas**: con hora y zona horaria, si el análisis las da.
- Solo lo que no se deduce mirando el código.

### Reglas (`.claude/rules/`, 2–4 ficheros de 5–10 viñetas)
Sigue `templates/rule.md`.
- `convenciones.md`, sin `paths`: idioma del código y de la documentación, formato de commits, secretos solo en `.env`, datos del reto fuera de git.
- El resto, **con `paths:`** apuntando a las carpetas generadas donde aplican. Salen de los contratos y trampas del reto: formato exacto de entrega, datos que no son de fiar, cosas que el reto prohíbe… Cada viñeta, específica de este reto y rastreable hasta el análisis o la decisión, con el mismo criterio que las reglas de equipo.
- **Cada viñeta termina con su origen entre paréntesis**, como las reglas de equipo (ver «Etiquetas de origen»). En `convenciones.md`, las que no salen del reto llevan `(convención del kit)`.

### Etiquetas de origen
Cada regla de equipo y cada viñeta de `.claude/rules/` acaban con una de estas, y la etiqueta tiene que ser verdad: lo que dice la regla está en esa fuente.
- `(enunciado)`, `(análisis: <sección>)`, `(riesgo típico)` o `(decisión)`: el dato o la obligación están ahí.
- `(supuesto: ambigüedad N, confirmar con la organización)`: comportamiento por defecto mientras una ambigüedad sigue abierta. **Una ambigüedad nunca es la fuente de algo que se da por cierto**: es una pregunta, así que lo que se decida sobre ella es un supuesto y se escribe como tal («hasta que la organización responda, …»).
- `(conocimiento externo, verificar)`: un dato que no está en el análisis ni en la decisión y que aportas tú (licencias, nombres de campos, herramientas, cómo funciona un producto).
- `(convención del kit)`: solo en `convenciones.md`.

### Skills del proyecto (`.claude/skills/<nombre>/SKILL.md`, 1–3)
Sigue `templates/skill.md`. Son **guías de pasos para momentos clave del reto** (la entrega, un cambio anunciado a mitad de reto, el ensayo de la demo), con `disable-model-invocation: true`. Esqueletos: pasos, fechas y comprobaciones sacados del análisis, con `TODO` donde dependa de la implementación. Nada que Claude ya sepa hacer.

### Contratos (`docs/contratos.md`)
Sigue `templates/contratos.md`. Un bloque por contrato: la entrega que pide el reto, los datos de entrada que da y, si hay varias piezas, cada interfaz entre ellas (por ejemplo, la respuesta del motor que pinta la web).
- **Campos**: tabla con nombre, tipo, si es obligatorio, valores o formato y origen. Copia del análisis los nombres de fichero, campos, valores y formatos tal cual; no los traduzcas ni los completes.
- Lo que el análisis no fija (campos de una interfaz entre piezas, un formato que es ambigüedad) es una propuesta del equipo: origen `decisión` si sale de ella, `supuesto: ambigüedad N, confirmar con la organización` si depende de una ambigüedad, o `TODO`.
- **Ejemplo mínimo válido** por contrato: un registro, o una petición y su respuesta, que respete la tabla. Con valores de ejemplo, nunca datos reales del reto.
### Atribución (`.claude/settings.json`)
Para que los commits y PR que haga Claude (también los workers y el orquestador del kit) no lleven su coautoría:
- Si el análisis **no** dice que haya que declarar el uso de IA, escribe `.claude/settings.json` con `{"attribution": {"commit": "", "pr": "", "sessionUrl": false}}`. Si ya existe, consérvalo y añade solo la clave `attribution`; si ya tiene una, no la toques y dilo en el resumen.
- Si el análisis dice que hay que declarar el uso de IA, **no** escribas `attribution`: avisa citando la frase del análisis y deja que la regla de equipo correspondiente salga, con su origen, como cualquier otra.

Sigue `templates/README.md`: qué es, requisitos, comando de arranque con la salida esperada, estructura y enlace al reto.

### Código mínimo
- **Estructura** propia del stack, mínima: solo las carpetas que el enfoque necesita desde el primer día. Con una sola pieza, en la raíz. Con varias, **una carpeta por pieza** (con nombre de su papel, por ejemplo `motor/` y `web/`), cada una con su propio manifiesto de dependencias.
- **Hola mundo** en cada pieza: un punto de entrada que imprime `hola mundo` o lo sirve, si es un servidor. Sin lógica de la aplicación, sin dependencias que el hola mundo no use. Si una pieza consume a otra (por ejemplo, una web que llama a una API), su hola mundo muestra también lo que le devuelve la otra: así se comprueba desde el primer día que las piezas se hablan.
- **Comando de arranque único**, que instale las dependencias de todas las piezas y las ejecute, y que funcione igual en Windows, macOS y Linux: nada de `make`, scripts solo de bash ni `&` para lanzar procesos en paralelo.
  - Una pieza: por ejemplo, Python con uv: `uv run <nombre>` (con `[project.scripts]` en `pyproject.toml`); Node: `npm run arranca` con `"arranca": "npm install && node <entrada>"`.
  - Varias piezas: un único comando en la raíz que instala todo y arranca las piezas a la vez, usando una herramienta que ya haga falta para alguna de ellas (no añadas otra solo para esto). Si son servidores, el comando debe mostrar en qué URL responde cada uno, y con Ctrl+C se deben parar todos.
- En Python, fuerza UTF-8 donde el reto tenga textos con tildes o símbolos (en Windows, sin eso se rompen).
- Escribe los ficheros a mano y mínimos; usa generadores oficiales solo si el stack no se puede arrancar razonablemente sin ellos.
- **`.gitignore`**: lo propio del stack, secretos (`.env`, `.env.*`, salvo `.env.example`), datos del reto y artefactos generados. **No** ignores `.hackathon/`: es el registro de decisiones del equipo.
- **`.env.example`** solo si el enfoque usa claves (por ejemplo, de un LLM), con nombres y sin valores.

## Paso 3b — Coordinación entre agentes (opcional)

Con ella, el agente de cada persona puede preguntar al de otra por GitHub Issues sin pasar por las personas (ver `/hack-ask`). Es opcional: sin ella, el kit funciona igual.
- Pregunta con AskUserQuestion: «No, gracias» o «Activar la coordinación entre agentes (GitHub Issues)». No la recomiendes ni la actives por tu cuenta.
- Si no puedes preguntar, actívala solo si los argumentos dicen «coordinación»; si no, sigue sin ella y no la menciones más.
- Si no se activa, no crees nada de este paso.
- Si se activa:
  1. `.hackathon/coordinacion.md` desde `${CLAUDE_SKILL_DIR}/templates/coordinacion.md`. Es la única excepción a «`.hackathon/` no se toca». `repo`: el `propietario/repo` de `git remote get-url origin`; si no hay remoto, deja el marcador. Tabla: una fila por persona de `.hackathon/equipo.md` si existe; si no, deja el marcador. Pide los usuarios de GitHub en una sola pregunta (el usuario los escribe en «Other»); lo que no te den, se queda como marcador. Nunca inventes un usuario.
  2. `.github/ISSUE_TEMPLATE/hk.md` desde `${CLAUDE_SKILL_DIR}/templates/issue-hk.md`.
  3. En `.gitattributes`, la línea `.hackathon/decisiones.md merge=union` (es un registro al que solo se añade; así dos añadidos a la vez no chocan al fusionar).
  4. Si no queda ningún `< >` en `coordinacion.md`, ejecuta `bash "${CLAUDE_PLUGIN_ROOT}/scripts/coordinacion/buzon.sh" preparar` (crea las etiquetas en el repo con `gh`). Si falla o quedan marcadores, di qué falta.
  5. En «Contexto» del CLAUDE.md, la línea «Coordinación entre agentes: `.hackathon/coordinacion.md` y `.hackathon/autoridad.md` (la genera `/hack-plan`)».
- En el resumen, di que cada persona necesita `gh` con su propio usuario (`gh auth login`) y Git Bash en Windows, y que el buzón empieza a escuchar solo, en menos de un minuto, en cada sesión con el plugin.

## Paso 4 — Verificar

Ejecuta el comando de arranque con Bash y comprueba que sale el hola mundo de cada pieza. Si alguna pieza es un servidor, lanza el comando en segundo plano, comprueba con una petición HTTP a cada pieza que responde (y, si una consume a otra, que muestra lo que le devuelve), y después detén todos los procesos que hayas lanzado. Si falla, corrige y reintenta una vez. Informa del resultado real, incluido el error si sigue fallando. No hagas `git init` ni commits: sugiérelo en una línea.

## Paso 5 — Resumen

Termina con:
- ficheros creados, saltados y sobrescritos;
- el comando de arranque y si ha funcionado;
- la atribución: «los commits y PR que haga Claude no llevarán su coautoría», o el aviso de que las bases piden declarar el uso de IA y no se ha quitado;
- el siguiente paso: repartir el trabajo del equipo.
