# ADR-0015 · El resultado de la Prueba desde CI: cómo se identifica, quién lo lee, cómo se sabe que es de `main` y cómo convive con el de la sesión

Estado: **Propuesto** (2026-10-25, especificación de M12). Lo decide el usuario con la tabla «Por decidir» de abajo (y del PR). Amplía ADR-0011 («el resultado desde CI queda para después»), que no cambia: **el OS sigue sin ejecutar nada**. Toca ADR-0012 solo en las evidencias. Lo que cambiaría en `api.md` y en `estado.schema.json` se describe aquí («Qué cambiaría en los contratos») y se escribe en K-116, después de decidir.

## Contexto
R-37 (nuevo): «DONDE el resultado de la Prueba desde CI esté activo, CUANDO el CI del equipo termine en `main` un trabajo que declara la Prueba de una conexión de `servicios.md`, el sistema DEBE mostrar […] su resultado, el sha sobre el que corrió y su hora, con procedencia «ci» y aparte del resultado de las sesiones de Claude Code, sin ejecutar nunca la Prueba». Lo que hay hoy (0.6.1):
- **La Prueba solo se ve si la corre una sesión de Claude Code** (ADR-0011): `scripts/os/prueba.sh` detecta en el Bash de la sesión el comando exacto de una conexión de `## Conexiones` y deja una línea `prueba` con `comando_sha` (12 hex del sha256 de la Prueba), `pasa`/`falla` y el código (`api.md` §1). El relay se queda con **el último por `comando_sha`** en orden de llegada (`relay.py`, `pruebas[comando_sha]`) y lo pone en `servicios.conexiones[].resultado` con `fuente: hook`. Ese resultado no dice sobre qué sha corrió: es el del árbol de trabajo de alguien, quizá con cambios sin subir.
- **Lo que corre en CI o en una terminal no se ve** (riesgo aceptado de ADR-0011). La vista de jurado enseña la Prueba como evidencia, no como condición (ADR-0012, decisión 4A), justamente porque «solo se ve si se corre en Claude Code».
- **El relay ya lee GitHub** con el `gh` de quien coordina (`relay.sondeo_de`, `github.Cliente`): issues `hk-tarea` cada 30 s con `If-None-Match`, backoff ante `403`/`429` (`github.Limitado`) y una instantánea a disco para arrancar sin GitHub. Los demonios no leen GitHub (solo Reclamar escribe, con el `gh` de su persona).
- **Lo que dijo el Paso 0** (`preguntas-abiertas.md`, P18–P21, con `gh api` de solo lectura sobre el repo del kit, 2026-10-25):
  - los jobs de una ejecución (`GET /actions/runs/<id>/jobs`) traen `name`, `conclusion`, `head_sha`, `head_branch`, `run_attempt` y sus pasos; el id del job es el del check-run;
  - las ejecuciones de un flujo (`GET /actions/workflows/<fichero>/runs`) traen `path`, `event`, `head_branch`, `head_sha`, `head_repository`, `actor`, `triggering_actor` y `run_attempt`;
  - un `304` con ETag no gasta cuota;
  - **no todo commit de `main` tiene ejecución** (filtros `paths`), y en un `push` de una etiqueta `head_branch` es el nombre de la etiqueta: `head_branch: main` no prueba que el sha esté en `main`;
  - las salidas de un workflow no salen por la API REST; los artefactos, solo como zip.
- **Quedan para K-115** (sandbox con Actions): P22 (check-runs y *statuses* creados desde otra rama, una etiqueta llamada `main`), P23 (conclusiones con `continue-on-error`, matrices, `timed_out`, *re-runs*), P24 (latencia) y la parte de P19 con tokens *fine-grained* y SSO.

Valen la constitución I (apagado, todo como en la 0.6.1), II (el resultado sale de una señal de GitHub, no de que alguien lo diga), III (procedencia y antigüedad: aquí, además, el sha), IV y ADR-0009 (las vistas igual), V (el nombre de un job es dato), VIII (sin GitHub, se degrada), IX (nada nuevo sale del portátil) y X (un resultado que no cambia no inyecta nada).

## Decisión (común, con las recomendaciones de «Por decidir»)
- **El OS nunca ejecuta la Prueba** (ADR-0011). La corre el CI del equipo, con un flujo que escribe el equipo; el kit da un ejemplo en la documentación y no genera nada en `.github/` (decisión 9).
- **Detrás de su interruptor**, `prueba_ci:` en el `os.md` del relay (decisión 7), apagado por defecto. Solo cuenta con `web_nueva: sí` (sin ella no hay `servicios`) y `github: sí`. **Con `prueba_ci: no`, sin la línea, con `github: no` o con `web_nueva: no`**, el relay no llama a ninguna ruta de Actions ni escribe nada nuevo, y `estado.json`, la vista, `estado-equipo.md`, el MCP y la web salen byte a byte como en la 0.6.1 (constitución I). Con `prueba_ci:` puesto y `github: no` o `web_nueva: no`, el relay lo dice **una vez** al arrancar.
- **Quién lee:** **el relay**, con el `gh` de quien coordina, en el mismo proceso que el sondeo de issues (decisión 6). Una sola lectura para todo el equipo; los demonios no cambian.
- **Cómo se identifica** (decisión 1): un job cuyo `name` contiene la etiqueta **`hk-prueba:<comando_sha>`**, con `<comando_sha>` = los 12 hex de la Prueba (la misma huella de `prueba.sh`, `api.md` §1). Ejemplo: `name: Prueba web → api (hk-prueba:3f2a9c1b7d4e)`. La etiqueta se busca con `hk-prueba:([0-9a-f]{12})` y es lo **único** que se lee del nombre: el resto no sale en ninguna vista (constitución V). La web enseña la etiqueta de cada conexión para copiarla (es dato derivado de `servicios.md`, no hace falta calcular nada a mano).
- **Qué resultado da** (decisión 2): la `conclusion` del job entero: `success` → `pasa`; `failure` o `timed_out` → `falla`; lo demás (`cancelled`, `skipped`, `neutral`, `action_required`, `stale`, `startup_failure`, sin terminar) **no da resultado** (se queda el anterior). Varios jobs con la misma etiqueta en una ejecución (una matriz): `falla` si alguno falla; `pasa` si todos los que dan resultado pasan. De un *re-run*, solo el último intento (`jobs?filter=latest`). Los pasos no se leen.
- **Qué ejecuciones cuentan** (decisión 3; constitución II y R-31). Todas estas condiciones:
  - el `path` de la ejecución está en la lista de `prueba_ci:` (ficheros de `.github/workflows/`);
  - `event` es `push`, `workflow_dispatch` o `schedule` (nunca `pull_request`, `pull_request_target` ni `workflow_run`) y `head_branch` es `main`;
  - `head_repository` es el repo (no un fork);
  - **`head_sha` se alcanza desde `origin/main` del clon del relay** (`git merge-base --is-ancestor`, sin objetos de reemplazo, como el resto del relay). Es la condición que importa: en un `push` el flujo que corre es el de ese sha, así que lo que corrió es código de `main`. `head_branch` no basta (P21: una etiqueta llamada `main`). Un sha que aún no está en el clon (el fetch va por detrás) se vuelve a mirar en la vuelta siguiente;
  - `triggering_actor` es de la tabla de `coordinacion.md` (R-31). Si no, se ignora y el relay lo deja en su registro;
  - **comprobación literal** (decisión 3A): el fichero del flujo **en ese sha** (`git show <sha>:<path>` en el clon del relay) tiene una línea que, sin espacios a los extremos, sin un `run:` o `- run:` delante y sin las comillas que la rodeen, es la Prueba normalizada como en `api.md` §10. Si no, el job no da resultado y sale el desajuste `prueba_ci_no_verificada` («el CI declara la prueba de «motor → web» pero el flujo no la contiene»). Comprueba que el job anunciado ejecuta ese comando en algún sitio, no que el job sea ese (riesgo aceptado);
  - un job con una etiqueta que no es la huella de ninguna Prueba de `## Conexiones` de `origin/main` sale como desajuste `prueba_ci_sin_conexion` (lo normal tras cambiar una Prueba sin cambiar el CI).

  Los check-runs sueltos, los *statuses*, los artefactos y los ficheros del repo **no cuentan** (alternativas descartadas): solo los jobs de una ejecución que pasa todo lo de arriba.
- **Cuál es el último** de una conexión: el de la ejecución cuyo `head_sha` está más cerca de la punta de `origin/main` (menos commits por detrás) y, con el mismo sha, el de `completed_at` más reciente. Un *re-run* de un sha viejo que termina tarde no tapa el resultado de un sha más nuevo.
- **Viejo y otro sha** (decisión 4; constitución III). El resultado lleva su `sha` y **`detras`**: cuántos commits de `origin/main` hay después de él (`git rev-list --count <sha>..origin/main`), `0` si es la punta. Es un dato aparte de `viejo`, que sigue queriendo decir «la fuente no se ha podido leer»: `viejo` = `fuentes.ci` no tiene una lectura buena desde hace más de `umbral_viejo_s`. Un `pasa` de hace tres commits sigue siendo verdad para ese sha, y la vista lo dice así («en a1b2c3d, 3 commits por detrás»), sin llamarlo viejo ni actual.
- **Convivencia con la sesión** (decisión 5): **dos resultados, nunca mezclados.** `resultado` (el de siempre, `fuente: hook`) no cambia; `resultado_ci` es nuevo (`fuente: ci`). Responden a dos preguntas distintas: «¿pasó en el árbol de alguien?» y «¿pasa en `main` en el sha X?». Cada uno da su propio desajuste `prueba_falla` (con su `fuente`), así que un `pasa` de una fuente no tapa un `falla` de la otra (constitución II: la discrepancia se ve). Ninguno es «el que gana»: la web los pone uno al lado del otro con su hora, y el más reciente se ve por la hora.
- **Cadencia y límites** (decisión 6):
  - en el hilo del sondeo de GitHub del relay, **cada 60 s**, por cada flujo de la lista (**3 como mucho**): `GET /repos/<r>/actions/workflows/<fichero>/runs?branch=main&status=completed&per_page=20` con `If-None-Match`. Sin cambios, `304`, que no gasta cuota (P19);
  - por cada ejecución nueva que pasa los filtros de la ejecución (o con un `run_attempt` nuevo), **una** petición `GET /actions/runs/<id>/jobs?filter=latest&per_page=100`; como mucho 10 por vuelta, el resto en la siguiente;
  - en el peor caso, 180 peticiones por hora más una por ejecución nueva, frente a las 5.000/h de un token de usuario; **ninguna escritura**, así que no cuenta para R-30;
  - ante un límite o un error, el backoff de `github.Limitado`, y `fuentes.ci` lo dice. Lo leído se guarda en `relay/ci.json` (ETags, ejecuciones vistas, últimos resultados) para arrancar sin GitHub, como `relay/github.json`.
- **Modo sin GitHub** (P20): con `github: no` no hay Actions; nada de M12 se produce y sigue el resultado de la sesión. Otros CI (GitLab, Jenkins…) quedan fuera.
- **Qué sale en cada vista** (ADR-0009: las tres de la misma vista):
  - **`estado.json`:** `servicios.conexiones[].resultado_ci` y `fuentes.ci`; los desajustes `prueba_falla` (con `fuente: ci`), `prueba_ci_no_verificada` y `prueba_ci_sin_conexion`;
  - **`/v1/vista`:** lo mismo, con `viejo` en `resultado_ci` (el de `fuentes.ci`);
  - **`estado-equipo.md`**, sección `## Servicios`, como hoy solo lo que no cuadra: `- no cuadra · contrato «motor → web»: la prueba falla en CI (a1b2c3d, 2 commits por detrás) (18:38 · ci)`. La **firma `servicios:`** lleva tipo, clave y fuente de cada línea, sin sha, sin `detras` y sin hora: una ejecución nueva con el mismo resultado sobre otro sha **no abre delta** (X); pasar de `pasa` a `falla` sí (≤ 600 caracteres, R-25);
  - **MCP:** sin herramienta nueva (decisión 10): `estado` devuelve el md con esa línea, y `jurado` trae la evidencia (abajo). `tools/list` no cambia;
  - **Vista de jurado** (ADR-0012): en `evidencias[]`, además de la Prueba de la sesión, la de CI (`tipo: prueba`, `fuente: ci`, con `sha` y `detras`). Sigue siendo **evidencia, no condición** (decisión 4A de ADR-0012 no cambia);
  - **Web de trabajo:** en la conexión, junto al comando, «sesión: pasa (18:38 · hook)» y «CI: falla · a1b2c3d · 2 commits por detrás (18:40 · ci)», y la etiqueta `hk-prueba:<comando_sha>` para copiar. Sin enlace a GitHub ni el nombre del job (dato); la web no calcula `detras` ni `viejo`, los pinta. **La web clásica** no enseña servicios: no cambia.
- **Seguridad** (ADR-0010, ADR-0011):
  - nada nuevo llega a una sesión salvo la línea fija del md (texto del kit con el nombre del contrato, que ya salía). El nombre del job no sale: solo la etiqueta validada, el sha (hex), `detras` (entero), el `path` del flujo (validado con `^\.github/workflows/[A-Za-z0-9._-]+\.ya?ml$`) y el id de la ejecución (entero);
  - ninguna acción web nueva; el demonio no cambia;
  - el resultado de CI **no confirma** nada: las filas de `servicios.md` se siguen confirmando como dice ADR-0011, y un resultado de CI no cambia `confirmacion`;
  - sale lo mismo que antes del portátil del coordinador (constitución IX): el relay solo lee de GitHub;
  - el token es el `gh` de quien coordina, el mismo del sondeo de issues; no se pide ni se guarda ninguno nuevo.
- **Prueba doble de ADR-0009:** `igualdad.py` con un guion nuevo **G16** (Prueba desde CI), y Vitest pinta G16.

## Qué cambiaría en los contratos
No se escribe hasta que el usuario decida (K-116). Todo con notas «tras congelar, M12», sin subir `v`: son campos opcionales, una clave nueva de `os.md` y valores nuevos de enumeraciones que hoy nadie produce.
- **`api.md` §0:** la clave `prueba_ci: no` en la plantilla (`no`, o la lista de ficheros de flujo separados por comas), que solo lee el relay, de su copia; con qué otras claves cuenta (`web_nueva: sí`, `github: sí`) y el aviso de una vez.
- **`api.md` §3:** un párrafo «M12, solo con `prueba_ci:`»: las dos rutas de la API, cadencia, topes, ETag, filtros, comprobación literal, cuál es el último, `detras`, `relay/ci.json` y `fuentes.ci`.
- **`api.md` §6:** la línea de ejemplo `… la prueba falla en CI (<sha7>, N commits por detrás) (HH:MM · ci)` y que la firma `servicios:` no lleva sha, `detras` ni hora.
- **`api.md` §7:** `relay/ci.json`.
- **`api.md` §10:** que la etiqueta de cada conexión es `hk-prueba:<comando_sha>` y que su huella es la de §1.
- **`api.md` §11.3:** `evidencias[]` con la Prueba de CI (con `sha` y `detras`).
- **`api.md` §5:** sin cambios (decisión 10).
- **`estado.schema.json`:**
  - `$defs/fuente`: el valor `ci`;
  - `fuentes.ci` (opcional, un `dato`: `ok`, `limitado`, `sin respuesta`);
  - `servicios.conexiones[].resultado_ci` (opcional; `null` o `{valor: pasa|falla, fuente: ci, observado_en, sha (40 hex), detras (entero ≥ 0, o null si el sha no se pudo medir), flujo, ejecucion, intento}`);
  - `servicios.desajustes[].tipo`: `prueba_ci_no_verificada` y `prueba_ci_sin_conexion`, y `sha` opcional en el desajuste;
  - en `$defs/vista_jurado`, `evidencias[]` con `sha` y `detras` opcionales (hoy `additionalProperties: false`).
- **`eventos.schema.json`:** no cambia (el relay no crea eventos: lo leído va a `estado.json`, como las tareas de GitHub).
- **`requisitos.md`:** R-37 (nuevo). R-12 vale tal cual para `fuentes.ci` (5 min).
- **ADR-0011 y ADR-0012:** no cambian; se les añade una línea «ver ADR-0015» al aceptarse.

## Por decidir

| # | Decisión | Opciones | Recomendada | Por qué |
|---|---|---|---|---|
| 1 | **Cómo se identifica qué Prueba ha corrido** | **A.** Etiqueta `hk-prueba:<comando_sha>` en el `name` del job · **B.** La etiqueta en el nombre de un paso · **C.** Un artefacto JSON con `{comando_sha, resultado}` · **D.** Un check-run o un *status* que crea el flujo · **E.** Un fichero de resultados en el repo | **A** | La huella es la de `prueba.sh`, así que la sesión y el CI se emparejan igual, y cambiar la Prueba obliga a cambiar la etiqueta (una Prueba cambiada no hereda el resultado de la vieja). El job y su conclusión los pone GitHub, no el flujo. B depende de cómo informa la API un paso con `continue-on-error` (P23). C exige descargar y abrir un zip y su contenido lo escribe el flujo. D y E se pueden crear desde cualquier rama (abajo) |
| 2 | **Qué conclusión cuenta** | **A.** La del job entero (`success` pasa; `failure`, `timed_out` falla; lo demás, sin resultado), matriz: falla si alguna pata falla · **B.** La del paso etiquetado · **C.** La de la ejecución entera | **A** | Es lo que GitHub enseña en el commit. C mezcla la Prueba con todo lo demás del flujo. Cancelado o saltado no dice si pasa: mejor el resultado anterior con su sha que uno inventado. Se confirma con P23 |
| 3 | **Autenticidad** | **A.** Filtros (flujo listado, evento, `main`, sin fork, sha alcanzable desde `origin/main`, del equipo) **y** comprobación literal de la Prueba en el flujo de ese sha · **B.** Solo los filtros · **C.** A, y además que el último commit que tocó el fichero del flujo esté atribuido (sha → persona, ADR-0011) a alguien del equipo · **D.** C con los dos dueños de la conexión | **A** | El sha alcanzable desde `main` es lo que impide fingir desde una rama: lo que corre es código de `main`, el mismo que confirma ADR-0011. La literal evita el error honrado (un job etiquetado que no corre esa Prueba), barata y sin YAML. C y D no paran a un agente con Bash en un portátil del equipo (ADR-0011 ya lo acepta con el token) y dejarían sin resultado los flujos editados desde la web de GitHub; se puede añadir después |
| 4 | **Resultado de otro sha** | **A.** `sha` y `detras` aparte de `viejo` (que es «sin leer») · **B.** Viejo en cuanto no es la punta · **C.** Solo se enseña si es de la punta | **A** | Con filtros `paths` muchos commits no tienen ejecución (P21): con B casi todo saldría viejo y con C casi nunca habría resultado. «En a1b2c3d, 3 commits por detrás» es verdad y no hace falta interpretarlo |
| 5 | **Sesión y CI a la vez** | **A.** Dos campos, un `prueba_falla` por fuente, ninguno gana · **B.** Gana el más reciente · **C.** Gana el CI si es de la punta; si no, el más reciente | **A** | Miden cosas distintas (un árbol de trabajo frente a un sha de `main`). B y C esconden una discrepancia (constitución II): un `pasa` en la sesión con cambios sin subir taparía un `falla` en `main` |
| 6 | **Quién lee el CI** | **A.** El relay, con el `gh` de quien coordina · **B.** El demonio de cada persona, con su `gh` · **C.** Los dos (el demonio, sin relay) | **A** | El relay ya lee GitHub con ese `gh`, guarda instantánea y calcula `servicios`; una lectura para el equipo. B multiplica las peticiones por persona, da vistas distintas según quién lee (contra ADR-0009) y los demonios hoy no sondean GitHub. Sin relay, el resultado de CI se ve en GitHub; no hace falta C |
| 7 | **Interruptor** | **A.** `prueba_ci:` en el `os.md` del relay: `no` o la lista de flujos (3 como mucho), con `web_nueva: sí` y `github: sí` · **B.** `prueba_ci: sí` y cualquier flujo de `.github/workflows/` · **C.** Dos claves, `prueba_ci: sí/no` y `prueba_ci_flujos:` | **A** | Una sola clave, apagada por defecto (constitución I), y la lista acota las peticiones (3 flujos, 60 s) y lo que cuenta: un flujo de otra cosa con la etiqueta por error no entra. B hace una petición por flujo del repo. C es lo mismo con una línea más |
| 8 | **Procedencia** | **A.** Fuente nueva `ci` · **B.** `github` | **A** | La web y el md dicen de dónde viene cada dato (III); `github` ya quiere decir «issues». Es un valor más del enum: lo pintan la web y el md con la misma etiqueta |
| 9 | **Flujo de ejemplo** | **A.** Un ejemplo en la documentación (`docs/limitaciones.md` o el README del OS) que el equipo copia · **B.** `/hack-scaffold` genera `.github/workflows/pruebas.yml` · **C.** Nada | **A** | El kit no escribe CI que ejecute comandos de `servicios.md` (sería el kit poniendo a correr código que un agente puede cambiar, lo que descarta ADR-0011). Sin ejemplo, la etiqueta y la literal se equivocan fácil |
| 10 | **MCP** | **A.** Sin herramienta nueva: `estado` (md) y `jurado` (evidencias) · **B.** Una herramienta `servicios` con el bloque entero | **A** | Como en M9a (el MCP no cambió). `tools/list` sigue igual; B sería útil, pero es otra superficie y otra prueba de igualdad, y R-37 se cumple sin ella |

## Alternativas descartadas
- **Que el OS ejecute la Prueba** (en el demonio, en el relay o lanzando el CI): ADR-0011. Tampoco lanza ejecuciones (`workflow_dispatch`): sería escribir en GitHub y ejecutar a demanda.
- **Check-runs o *statuses* por nombre:** según la documentación, cualquier flujo con `checks: write` o `statuses: write` (desde cualquier rama) y cualquiera con permiso de escritura puede crearlos sobre cualquier sha con el nombre que quiera. Lo confirma K-115 (P22). Los jobs de una ejecución los crea GitHub al ejecutar el flujo de ese sha.
- **Artefactos:** hay que descargar un zip, caducan (retención configurable desde 1 día) y su contenido lo escribe el flujo: es leer un fichero de datos que dice «pasa».
- **Un fichero de resultados en el repo:** el CI tendría que hacer commits en `main` (ruido, carreras, `contents: write`), y una rama cualquiera puede llevar uno.
- **Salidas del flujo (`outputs`):** no salen por la API REST.
- **Que el resultado de CI confirme filas o cubra notas:** confirmar sigue siendo «hecho desde el portátil del dueño» (ADR-0011) y la Prueba sigue siendo evidencia, no condición (ADR-0012).
- **Resultados de `pull_request`:** el código de una rama no es el de `main`; fuera de M12.

## Riesgos aceptados
- **La literal comprueba que el flujo contiene la Prueba, no que el job etiquetado la ejecute** ni que el resultado dependa de ella (`|| true`, `continue-on-error` en el paso). Es código de `main`, como la Prueba misma.
- **Quien puede hacer commits en `main` puede hacer que la Prueba «pase» en CI** (cambiar el flujo o la Prueba). Es la misma garantía que ADR-0011: «nunca confirmado por error» frente a quien no escribe en `main`; un agente con Bash en un portátil del equipo queda fuera.
- **La cuenta de quien coordina:** si su `gh` no ve Actions (token *fine-grained* sin «Actions: read», SSO sin autorizar), no hay resultado de CI y `fuentes.ci` lo dice (P19).
- **Latencia:** entre que termina el job y la vista lo enseña, hasta un sondeo (60 s) más lo que tarde GitHub en listarlo (P24).
- **Sin ejecución en la punta** (filtros `paths`, flujos manuales): el resultado se queda en su sha con `detras` creciendo.
- **Otros CI** (GitLab, Jenkins) y el modo sin GitHub: sin resultado de CI.
- **Un resultado de CI de hace días** sigue saliendo con su sha y su `detras`; no caduca por la hora.
