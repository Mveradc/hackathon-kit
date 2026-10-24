# ADR-0014 · Nivel 2b de colisiones: fusión estructural con Mergiraf

Estado: **aceptada** (2026-10-22, por el usuario al decidir la tabla del PR #78 con las siete recomendaciones; propuesta el 2026-10-21). Revoca la decisión del 2026-10-14 (`docs/coordinacion.md`, P12) **solo para el portátil del coordinador**: Mergiraf se instala a mano y es opcional; el kit nunca lo instala ni lo pide. Concreta el «Nivel 2b» de ADR-0007, que no cambia. Contratos en las notas «tras congelar, M11» de `api.md` (K-110).

## Contexto
R-34: «DONDE el análisis estructural esté activo, el sistema DEBE rebajar a amarillo un conflicto de nivel 2 que una fusión estructural (Mergiraf) resuelva sin conflictos». Lo que hay hoy (0.5.0):
- **El nivel 2 lo calcula solo el relay** (`hkos/colisiones_merge.py`, clase `Calculo`): con `publicar_wip: sí` y Git ≥ 2.38, cada 30 s trae `refs/hackathon/wip/*` a `refs/hackathon/relay-wip/*` de su clon y ejecuta `git merge-tree --write-tree --name-only --no-messages` por pares de personas, con una caché por par de shas. Da `conflictos` = `[{personas, rutas, desde}]`, que `hkos/colisiones.py` convierte en colisiones rojas `2:<a>+<b>`. Un fichero en conflicto de nivel 2 no sale además en el nivel 1 entre las mismas personas.
- **El esquema ya admite `2b`**: `estado.schema.json` tiene `"nivel": {"enum": ["1", "2", "2b", "3", "reserva"]}` desde M8b. `diseno.md` §7 lo pinta amarillo. Ningún código lo produce.
- **P12, respondida el 2026-10-21 solo en Linux** (`evals/coordinacion/prueba.md`, «M11, Paso 0»):
  - `mergiraf merge <base> <izq> <der> -o <salida>` funciona fuera de una fusión de git; **rc 0** sin conflictos, **rc 1** con conflictos, **255** si falla una entrada;
  - el lenguaje sale de la extensión: con ficheros temporales hace falta `-p <ruta>`;
  - lo que no sabe analizar (sin lenguaje, no UTF-8, binario, error de sintaxis) o lo que pasa del plazo `-t` vuelve a la fusión por líneas de git y da rc 1: **nunca un falso «sin conflictos»** por fallo;
  - no todo lo compatible baja: dos funciones nuevas al final de un `.js` siguen en conflicto;
  - **guarda una copia** de base, lados y resultado de cada fusión que resuelve en `$XDG_DATA_HOME/mergiraf/merges/` (por defecto, `~/.local/share`), y `XDG_DATA_HOME` la lleva a otro sitio;
  - 9–50 ms por fichero pequeño; 4,7 s con 148 KB de Python.
- **Windows y macOS, sin comprobar** (P17): binario, dónde guarda las copias, tiempos. Respondida en K-109: «Ajuste tras P17», abajo.

Valen la constitución I (apagado, todo como en la 0.5.0), III, IV y ADR-0009 (las tres vistas igual), VI (solo avisos), VII (instalaciones de un comando), VIII (si falla, se degrada) y IX (el contenido no sale del portátil).

## Decisión (común)
- **Solo en el relay.** Mergiraf solo hace falta en el portátil del coordinador, que es quien calcula el nivel 2. Los demás portátiles no cambian: ni demonio, ni hooks, ni web.
- **Detrás de su interruptor** `fusion_estructural:` en el `os.md` del relay (decisión 2), apagado por defecto. Solo cuenta con el nivel 2 activo (`publicar_wip: sí` y Git ≥ 2.38). **Con el interruptor apagado, sin `publicar_wip` o sin Mergiraf**, el relay no busca ni ejecuta nada nuevo, y `estado.json`, la vista, `estado-equipo.md`, el MCP y la web salen byte a byte como en la 0.5.0 (constitución I).
- **Cómo se detecta**, una vez al arrancar el relay: `shutil.which("mergiraf")` y `mergiraf --version` (plazo de 5 s), que debe dar una versión ≥ la mínima (decisión 5). Si el interruptor está en `sí` y Mergiraf no está, no responde o es más viejo, el relay lo dice **una vez** al arrancar, como el aviso de Git < 2.38 («Nivel 2b desactivado: mergiraf no está en el PATH. Sigue el nivel 2.») y sigue como en la 0.5.0. Con Mergiraf bien: «Nivel 2b activo: mergiraf 0.20.0». No se vuelve a buscar hasta reiniciar el relay.
- **Cuándo se ejecuta:** dentro del ciclo del nivel 2 (`Calculo.sondear`, cada 30 s), solo cuando `merge-tree` da conflictos para un par con shas nuevos. El `merge-tree` pasa a ejecutarse **sin `--name-only`** para leer las etapas (`<modo> <blob> <etapa>\t<ruta>`), con el mismo código de salida. Para cada ruta en conflicto:
  - solo se intenta si tiene **las tres etapas** (base, izquierda, derecha) y las tres son ficheros normales (modo `100644` o `100755`). Lo demás sigue rojo sin intentarlo: `add/add`, `modify/delete`, renombrados en conflicto, enlaces simbólicos, submódulos;
  - los tres blobs (`git cat-file blob`) se escriben en un directorio temporal **fuera del clon** (`tempfile.mkdtemp`), y se ejecuta `mergiraf merge 1 2 3 -p <ruta> -t <plazo> -o salida`, sin `--allow-parse-errors` ni `--fast`, con `XDG_DATA_HOME` y `APPDATA` apuntando a ese directorio (P17: `XDG_DATA_HOME` en Linux y macOS, `APPDATA` en Windows; ajuste del 2026-10-22). El directorio se borra después, pase lo que pase;
  - **rc 0** = la fusión estructural lo resuelve: la ruta baja a 2b. **Cualquier otra cosa** (rc 1, 255, plazo del proceso vencido, error al lanzarlo) = sigue roja. La salida no se lee ni se guarda: solo cuenta el código.
- **Caché por contenido:** el resultado de cada ruta se guarda en memoria por `(blob base, blob izq, blob der, ruta)`, también el «no resuelve» y el plazo vencido. Mismos ficheros, mismo color: no parpadea entre rojo y amarillo con la carga del portátil. Se recorta como la caché de pares.
- **Plazos** (decisión 4): `-t 5000` por fichero (el plazo de Mergiraf, que vuelve a git y da rc 1), 10 s por proceso (lo mata el relay) y **20 s por ciclo** para todos los ficheros de todos los pares. Lo que no se llega a intentar en un ciclo sigue rojo y se intenta en el siguiente. Un ciclo del nivel 2 nunca tarda más de su cadencia por culpa de 2b.
- **Qué produce:** `conflictos` pasa a ser `[{personas, rutas, rutas_2b, desde, desde_2b}]`; `rutas` son las que siguen rojas y `rutas_2b`, las que resuelve Mergiraf. `hkos/colisiones.py` da, por par:
  - `2:<a>+<b>` rojo con `rutas`, si hay alguna;
  - `2b:<a>+<b>` amarillo con `rutas_2b`, si hay alguna (`nivel: "2b"`, `gravedad: "amarillo"`, `observado_en` = `desde_2b`, la hora en que ese conjunto de rutas bajó);
  - un par puede tener las dos. Las rutas de las dos tapan el nivel 1 entre esas personas, como hoy las del 2.
  Sin el interruptor, `rutas_2b` no existe y la salida es la de la 0.5.0.
- **Qué se dice en cada vista** (ADR-0009: las tres de la misma vista):
  - **`estado.json` y `/v1/vista`:** la colisión `2b` con los campos de siempre. **El esquema no cambia** (el valor ya estaba). Sin campo nuevo en `fuentes`: si 2b está apagado se sabe solo por el aviso del relay en su terminal, como con Git < 2.38 (decisión 6).
  - **`estado-equipo.md`** (`proyeccion.linea_colision`): `- AMARILLO · nivel 2b · fusión estructural sin conflictos · src/app.py · @ana, @luis (18:41)`. Empieza por `- AMARILLO`, así que `escucha.sh` no abre turno y `delta.sh` no la cuenta como roja (R-25b). La firma de colisiones ya incluye nivel y gravedad: **bajar de rojo a 2b da un delta** (≤ 600 caracteres) y **volver a rojo** (alguien cambia el fichero y Mergiraf ya no lo resuelve) es una roja nueva: delta y línea del monitor, como hoy.
  - **MCP:** `colisiones` devuelve los mismos objetos. Su descripción añade una frase: «nivel 2b: conflicto de git que la fusión estructural (Mergiraf) resuelve; amarillo, revisad la fusión igualmente».
  - **Web** (nueva y clásica): ya pintan `NIVEL {nivel}` con su gravedad, así que `NIVEL 2b` sale en amarillo sin tocar el código. Se añaden el caso a Vitest y el mismo texto «fusión estructural sin conflictos» que el md (decisión 7).
- **Lo que no hace:** no fusiona nada, no escribe en el clon del relay ni en el de nadie, no propone la fusión resuelta ni la enseña. Amarillo quiere decir lo mismo que en el nivel 1: dos personas tocan el mismo fichero y hay que mirarlo. Mergiraf puede resolver sin conflictos algo que no compila o no hace lo que debe (R-34 no dice otra cosa).
- **Constitución IX:** los blobs ya están en el clon del relay (llegaron con el `fetch` del nivel 2). Mergiraf corre en local, sin red, y sus copias quedan en el directorio temporal que se borra. Nada nuevo sale del portátil del coordinador.
- **Prueba doble de ADR-0009:** `igualdad.py` con un guion nuevo **G15** (2b), y Vitest pinta una colisión `2b`.

## Qué cambia en los contratos
Solo notas «tras congelar, M11», sin subir `v` (añaden una clave opcional y fijan un texto):
- **`api.md` §0:** la clave `fusion_estructural: no` en `os.md`, que lee el relay (y el MCP, para la descripción de `colisiones`: ajuste del 2026-10-24).
- **`api.md` §3:** el párrafo de colisiones del relay, con el nivel 2b (cuándo se ejecuta, plazos, caché, aviso).
- **`api.md` §5:** la frase nueva de la descripción de `colisiones`.
- **`api.md` §6:** el ejemplo de la línea `2b` en «Colisiones que te afectan».
- **`estado.schema.json`:** no cambia.
- **`requisitos.md`:** R-34 no cambia.
- **`diseno.md` §7:** la fila 2b («Mergiraf en el relay, sobre los ficheros con tres etapas») y la definición de «Nivel 2b» (tras K-110).

## Decididas (2026-10-22)

Las siete, como se recomendaban en el PR #78 (comentario del usuario del 2026-10-22). La tabla del PR numeraba distinto: allí, 2 era la instalación, 3 `api.md`, 4 el interruptor, 5 los plazos y 6 la versión.

| Decisión | Elegida | Por qué |
|---|---|---|
| **1. La decisión del 2026-10-14 (no instalar nada)** | **A.** Se revoca solo para el portátil del coordinador, a mano y opcional: el kit nunca instala Mergiraf ni lo pide | El nivel 2 ya es opt-in y solo corre en el relay: 2b añade un programa en un portátil, no en el equipo. Que el kit lo instalara (B) metería descargas de binarios en el kit (cadena de suministro, constitución VII). Mantenerla (C) dejaba R-34 fuera de la v1 |
| **2. Interruptor** | **A.** `fusion_estructural: no` en `os.md` (por defecto), y con `sí` solo si Mergiraf está | Como `vista_jurado:` y `ruta_critica:`: un programa que alguien tenga instalado por otra razón no cambia el comportamiento del equipo sin que nadie lo decida, y el apagado se prueba igual que en la 0.5.0. Sin interruptor (B) se usaría con solo estar en el `PATH` |
| **3. Cómo lo instala el coordinador** | **A** en Windows y Linux: el binario de la release oficial (Codeberg), descomprimido en el `PATH`. **C** en macOS: `brew install mergiraf`. **B** (`cargo install --locked mergiraf`, exige Rust) solo como alternativa. Se documentan las que pasen P17 (K-109) | A es un comando (VII) y no exige Rust; B tardó 1,5 min en compilar en el Paso 0 y no cumple VII en Windows |
| **4. Plazos** | **A.** 5 s por fichero (`-t 5000`), 10 s por proceso, 20 s por ciclo y caché por contenido | Un ciclo del nivel 2 dura 30 s: con 20 s de tope, 2b no lo retrasa. 5 s bastó para 148 KB de Python. Un fichero que no llega sigue rojo, que es lo seguro. Plazos en `os.md` (C) serían una cosa más que configurar sin datos |
| **5. Versión mínima** | **A.** 0.20.0, la única probada | Los códigos de salida y `-p` se han comprobado solo en la 0.20.0. Se baja si K-109 prueba otra |
| **6. ¿Se cambia `api.md`?** | **A.** Notas «tras congelar, M11» en §0, §3, §5 y §6 (K-110); `estado.schema.json` sin cambios | El valor `2b` ya estaba en el contrato: solo falta decir quién lo produce y cómo se lee. `fuentes.mergiraf` (B) se puede añadir después si el equipo no entiende por qué no hay 2b. Sin nada en `api.md` (C), una clave de `os.md` y un texto del md quedarían sin contrato |
| **7. Texto de la línea** | **A.** `nivel 2b · fusión estructural sin conflictos`, en el md y en la web | Un modelo que lee «nivel 2b» no sabe qué quiere decir; la frase es corta y cabe en el presupuesto (R-24) |

## Ajuste tras P17 (2026-10-22, K-109 y K-110)
P17, respondida en K-109 (`evals/coordinacion/prueba.md`, «M11, Paso 0», «K-109»): binario oficial y casos de P12 en Windows y macOS (runners de GitHub Actions), tiempos con los ficheros de los retos 02 y 03 y `merge-tree` sin `--name-only` desde Git 2.38. Manda sobre lo de arriba donde lo contradiga. **Ninguna decisión cambia**; se concretan tres cosas que dependían de P17:

| Punto | Queda | Por qué (K-109) |
|---|---|---|
| **Copias de Mergiraf** (constitución IX) | El relay ejecuta Mergiraf con **`XDG_DATA_HOME`** y **`APPDATA`** apuntando al directorio temporal, en todos los sistemas (cada una solo la lee el suyo). El directorio se borra siempre. 2b no se apaga en ningún sistema | Linux y macOS guardan las copias en `~/.local/share/mergiraf/merges/` (estrategia XDG también en macOS, no `~/Library`) y `XDG_DATA_HOME` las lleva al temporal. Windows las guarda en `%APPDATA%\Mergiraf contributors\Mergiraf\data\merges\` y solo **`APPDATA`** las lleva (con `XDG_DATA_HOME`, `LOCALAPPDATA` o `USERPROFILE` seguían en el `APPDATA` de la persona). Con rc 1 no guarda nada |
| **Instalación** (decisión 3) | Igual: binario de la release oficial en Windows (x86_64) y Linux, `brew install mergiraf` en macOS, y `cargo install --locked mergiraf` como alternativa. En macOS el binario oficial (arm64 y x86_64) también vale. Windows en ARM no tiene binario: solo `cargo` | El zip de Windows trae `mergiraf.exe` y arranca sin instalar nada; brew da 0.20.0 en 4 s |
| **Versión mínima** (decisión 5) | Igual: **0.20.0** | Es la única probada en las tres plataformas. 0.19.1 da lo mismo en Linux; 0.16.3, rc 129 donde la 0.20.0 da 1 o 255 |

**Plazos** (decisión 4), sin cambios: los ficheros del árbol de los retos 02 y 03 tardan ≤ 0,2 s en las tres plataformas y 20 ficheros en conflicto a la vez suman ≈ 10 s. `-t 5000` no limita el tiempo total: un `.js` compilado de 299 KB volvió a git en 5,6–6,0 s, así que el plazo de 10 s por proceso es necesario. Un Python de 148 KB está al filo (2,4–5,3 s según la máquina): cuando pasa de 5 s, sigue rojo, y la caché lo deja rojo hasta que cambie un lado.

**`merge-tree`:** sin `--name-only` da las etapas (`<modo> <blob> <etapa>\t<ruta>`) con el mismo código de salida en Git 2.38 (Linux y MinGit de Windows), 2.43, 2.49 (MinGit, la del portátil del usuario), 2.55 y 2.56 (Windows y macOS).

Sigue sin probar en un portátil real de Windows o macOS: lo hace el criterio 6 de M11 (K-114).

## Ajuste del 2026-10-24 (decisión del usuario, tras K-112)
Arriba, «Solo en el relay» habla de Mergiraf y del cálculo, y la descripción del MCP «añade una frase» sin decir cuándo. Queda así, que es lo que hace el código desde K-112 (PR #84, `hkos/mcp.py`): la frase de la descripción de `colisiones` sale **solo con `fusion_estructural: sí`** en el `os.md` de la copia principal de cada persona, como las herramientas `jurado` y `ruta` con sus interruptores (ADR-0012, ADR-0013). Así el MCP con el interruptor apagado es byte a byte el de la 0.5.0 (constitución I), como dice «Detrás de su interruptor». Por eso `fusion_estructural:` lo leen el relay (el cálculo) y el MCP (solo la descripción): `api.md` §0 y §5, notas «tras congelar, 2026-10-24, M11». Ninguna decisión cambia.

## Alternativas descartadas
- **Ejecutar Mergiraf en el demonio de cada persona:** exigiría instalarlo en todos los portátiles y que cada demonio tuviera el trabajo en curso de los demás, que solo trae el relay.
- **Mergiraf como driver de fusión de git** (`merge.mergiraf.driver` en la configuración del clon del relay y `.gitattributes`): `merge-tree --write-tree` usa los drivers de `.gitattributes` del árbol, que escribe el equipo; depender de ese fichero (o tocarlo) es más frágil que llamar a Mergiraf por ruta, y no se ha comprobado con `merge-tree`.
- **Leer la salida de Mergiraf** (contar marcadores, guardar la fusión para enseñarla): el código de salida basta, y guardar la fusión es guardar código de otras personas.
- **`--allow-parse-errors`**: con él, un fichero con un error de sintaxis bajó a amarillo (P12). Un fichero que no se analiza no debe bajar.
- **Análisis por símbolos propio** (tree-sitter en el kit): ya descartado en ADR-0007.

## Riesgos aceptados
- **«Amarillo» no es «fusiona bien»**: Mergiraf puede dar una fusión sin conflictos que no funciona. Se dice en la línea («revisad la fusión igualmente» en el MCP) y en `docs/limitaciones.md`.
- **Lo que no baja**: lenguajes que Mergiraf no conoce (CSS, SQL, `.ipynb`), hermanos que no conmutan (dos funciones al final de un `.js`), ficheros con errores de sintaxis. Siguen rojos, como en la 0.5.0.
- **Solo Linux probado** hasta K-109 (P17). Respondida (ajuste del 2026-10-22): en Windows la copia se lleva al temporal con `APPDATA`, y en macOS con `XDG_DATA_HOME`, como en Linux; 2b no se apaga en ningún sistema. Falta un portátil real de Windows o macOS (K-114).
- **Un programa más en el portátil del coordinador**, fuera del control del kit: la versión se comprueba al arrancar, pero no su procedencia.
- **Coste:** con 5 personas hay 10 pares; en el peor ciclo, 20 s de CPU en el portátil del coordinador cada 30 s. La caché por contenido lo deja en casi nada cuando nadie cambia los ficheros en conflicto.
