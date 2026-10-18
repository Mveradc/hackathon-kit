# ADR-0011 · `servicios.md`: formato, quién lo escribe y quién lo confirma

Estado: **aceptada** (2026-10-17, por el usuario al abrir M9a).

## Contexto
La vista de servicios de M9a enseña qué hay en marcha (servicios con su carpeta, su puerto y su dueño), cómo se hablan entre sí (conexiones con su contrato) y qué no cuadra. Hace falta un fichero que lo declare, que lo puedan editar personas y agentes, y una regla verificable para distinguir lo confirmado de lo que un agente ha propuesto.

## Decisión
- **Dónde y quién lo genera:** `.hackathon/servicios.md`, versionado. Lo genera `/hack-scaffold` en su paso de coordinación (sin coordinación no se crea: el núcleo del kit no cambia). Después lo pueden editar personas y agentes.
- **Formato:** tres secciones con tablas, más una línea:
  - `## Servicios`: Nombre | Carpeta | Puerto | Arranque | Salud | Dueño. Puerto y Salud son opcionales (`—`). Puerto es un entero de 1 a 65535. **Salud solo admite una ruta** que empieza por `/`, sin esquema, sin host, sin `..` y sin espacios (`/salud`, `/api/health?x=1`); cualquier otra cosa (`http://…`, `//host/…`, `/../`) hace de la fila un desajuste, y el demonio no la consulta. Lo mismo después de descodificar los `%XX` (`/%2e%2e/`, `%252e`; PR #7, issue #2, hallazgo 13). Una fila con un campo que no vale queda sin confirmar, y su Puerto y su Salud no salen en la lista (PR #7, hallazgo 6).
  - `## Conexiones`: De | A | Contrato | Prueba. «Contrato» es el título de un bloque de `docs/contratos.md`; «Prueba» es un comando.
  - `## Propuestas de servicios` y `## Propuestas de conexiones`: el mismo formato que Servicios y Conexiones, más Autor y Hora, para lo que declara un agente sin confirmar (`api.md` §10). Al confirmarse, la fila pasa a Servicios o Conexiones (sin Autor ni Hora).
  - `Fuera de servicios:` las carpetas que no cuentan para «código fuera de cualquier servicio» (`docs/`, `.hackathon/`…).
- **El OS nunca ejecuta** «Arranque» ni «Prueba». De la Prueba solo lee el resultado cuando alguien la corre: un hook (`scripts/os/prueba.sh`) detecta en el Bash de una sesión de Claude Code el comando exacto de una conexión y deja si pasó o falló. La web enseña el comando junto al resultado, con procedencia y antigüedad. Lo que una persona corre en su propia terminal no se ve (el resultado desde CI queda para después).
- **Salud:** el demonio del dueño comprueba, solo para **sus** servicios confirmados con una Salud válida y solo en `127.0.0.1:<Puerto>`, si el puerto acepta conexiones y qué responde `GET <Salud>` (con tiempo máximo y sin seguir redirecciones). Lo emite como evento `servicio.estado` solo cuando cambia.
- **Quién confirma:** la regla está en `autoridad.md`: un servicio lo confirma su dueño; una conexión, los dueños de sus dos extremos. El dueño de un servicio es la persona cuyas carpetas de `autoridad.md` contienen la carpeta del servicio, no la columna «Dueño». Si la columna dice otra persona, es un desajuste y la fila no está confirmada. Sin valor («—», porque `/hack-scaffold` corre antes del reparto de `/hack-plan`), manda `autoridad.md` y no hay desajuste. Si `autoridad.md` tampoco da dueño a esa carpeta:
  - antes del reparto (sin `autoridad.md` o sin ninguna persona en él), la fila es «sin dueño», sin desajuste, y solo está confirmada si viene de `/hack-scaffold`;
  - con el reparto hecho, es un desajuste y queda sin confirmar.
- **Qué significa «confirmado»:** **hecho desde el portátil del dueño** (la persona o sus agentes). **No** significa «decidido por una persona». Basta para el mapa de los propios servicios. Lo que necesite una decisión humana según `autoridad.md` (por ejemplo, cambiar un contrato) sigue con `hk confirmo`, como en la 0.3.2.
- **Cómo se calcula** (en el relay, sobre `origin/main` de su clon, en el mismo bucle que las novedades y los contratos):
  - la clave de una fila son todos sus campos normalizados (sin espacios de más ni comillas invertidas);
  - para cada fila de Servicios o Conexiones, se reúnen las personas cuyos commits **añadieron** una fila con esa misma clave, en cualquier sección (`git log -p` del fichero);
  - la fila está confirmada si ese conjunto incluye al dueño (servicio) o a los dos dueños (conexión). Si no, es «declarado por @x, sin confirmar», donde @x es quien la añadió;
  - en un clon superficial del relay, o si no se sabe si lo es, ninguna fila es de /hack-scaffold (abajo) y las versiones del borde no cuentan: sin sus padres, todas sus filas saldrían añadidas por la persona de ese commit. Si no se sabe, no cuenta ninguna versión (PR #14, issue #10);
  - cambiar cualquier campo da una clave nueva, así que la fila vuelve a «sin confirmar». En particular, si cambia el comando de Prueba de una fila confirmada: la Prueba es código ejecutable;
  - una versión del fichero con alguna lectura de git fallida no cuenta hasta que se lea bien (se vuelve a leer con espera creciente: tras 1, 2, 4… vueltas, como mucho 16; PR #21, issue #18). Un fallo no se toma por «el fichero no estaba en el padre», que haría parecer añadidas todas sus filas (PR #14, issue #10);
  - la persona de cada commit sale **solo** de los eventos `commit` de los demonios (sha → persona), **nunca** del autor de git, que cualquiera puede poner. Si un rebase o un squash cambian los shas, la fila puede salir «sin confirmar» por error, pero nunca «confirmada» por error;
  - **commits de los workers** (comprobado en el código el 2026-10-17): el sondeo de git del demonio (`hkos/agente.py`, `SondeoGit.ciclo`) recorre todas las ramas locales, incluidas las `worktree-agent-<id>` de los worktrees (comparten refs con la copia principal). Emite con la persona del demonio y el actor `worker` cada commit nuevo que su rama `worktree-agent-<id>` recibió con `git commit` o `git revert` (lo dice el reflog de esa rama, que está en el git común); los de la persona salen del reflog de HEAD de la copia principal, y el de las demás ramas no se lee (PR #12 y PR #20, `api.md` §4). Cubierto por `hkos/pruebas/test_sondeo_git.py`. El orquestador integra con `merge --no-ff` y después `merge --ff-only` (`agents/orquestador.md`), así que los shas de los workers llegan intactos a `origin/main` y se atribuyen a la persona. El merge no se emite como commit, pero la fila la añade el commit del worker, no el merge. Quedan dos huecos: lo que solo esté en la resolución de un conflicto de merge, y un commit de worker cuya rama se borre antes del siguiente ciclo (15 s): con la rama se va su reflog, y desde el PR #12 tampoco se recupera cuando llega a `main`. En los dos, la fila sale sin confirmar, nunca confirmada por error. La tabla de casos de K-92 incluye una fila añadida por un worker;
  - las filas que estaban en el commit que creó el fichero cuentan como «de /hack-scaffold», confirmadas;
    - solo si ese commit es seguro (PR #7, issue #2, hallazgo 1): el único de toda la historia de `origin/main`, sin la simplificación de historia de `git log`, en el que el fichero está y no está en ninguno de sus padres, con como mucho un padre y sin venir de un renombrado. Si no, ninguna fila es de /hack-scaffold;
    - con más de 200 commits en el fichero (los que lee el relay), tampoco ninguna;
    - solo las de Servicios y Conexiones de ese commit, no las de Propuestas (PR #7, hallazgo 9);
  - una fila de Propuestas siempre es «declarado, sin confirmar». Su Autor y su Hora son dato; si no coinciden con la persona del commit, se enseña la del commit;
  - un nombre de servicio repetido no dice de qué fila se habla: ni sus filas ni las conexiones que lo usan salen confirmadas (PR #7, issue #2, hallazgo 4);
  - un sha que emiten como `commit` demonios de personas distintas no es de nadie, sea cual sea el orden de llegada (PR #7, issue #2, hallazgo 5).
- **Desajustes que salen en la vista:**
  - puerto declarado sin nadie escuchando, o una salud que no responde 2xx;
  - Puerto o Salud con un formato que no vale (la fila no se consulta);
  - código fuera de cualquier servicio: ficheros de `origin/main` y del último `arbol` de cada persona que no están en la carpeta de ningún servicio ni en «Fuera de servicios»;
  - contrato con la Prueba fallando en su último resultado;
  - dueño de la columna distinto del de `autoridad.md`;
  - una conexión cuyo contrato no existe en `docs/contratos.md`.

## Alternativas descartadas
- **Columna «Confirma»:** se puede escribir desde cualquier portátil; lo verificable es de dónde viene el commit.
- **`hk confirmo` en un issue para cada fila:** más fuerte (un agente no lo falsifica), pero no funciona sin GitHub (modo de K-80) y enlazar un issue con una fila es frágil. Se mantiene para las decisiones humanas.
- **`docs/servicios.md`, junto a `contratos.md`:** es estado del equipo durante el evento, como `autoridad.md`; va en `.hackathon/`.
- **Que el OS ejecute la Prueba o el Arranque:** sería ejecutar código que un agente puede haber cambiado.

## Riesgos aceptados
- «Confirmado» no prueba que una persona lo haya revisado: lo hizo su portátil, quizá un agente suyo.
- Las filas iniciales de `/hack-scaffold` se dan por confirmadas sin atribución por evento.
- Rebase y squash pueden dejar filas sin confirmar hasta que el dueño las vuelva a tocar. Lo mismo, una fila que solo aparece en la resolución de un conflicto de merge, o el commit de un worker cuya rama se borra antes de que el demonio la vea. El ensayo mira si pasa.
- Las pruebas corridas fuera de Claude Code no se ven.
- **Casos legítimos que la regla del reflog deja sin confirmar** (PR #12, `api.md` §4). En todos, el commit no se atribuye y la fila sale sin confirmar, nunca confirmada por error; la tarea sigue pudiendo llegar a `publicada`, porque el `incluye` del `push` no depende de la persona:
  1. **El mismo dueño con dos clones:** lo emite solo el demonio del clon donde se hizo el commit; si ese demonio no llegó a estar en marcha, nadie lo emite.
  2. **`git pull --rebase` o `git rebase` con commits locales sin subir:** los shas nuevos no se emiten (los viejos sí, si el demonio los vio antes, pero no llegan a `main`). Es el riesgo de rebase de arriba, que antes el correo tapaba en parte.
  3. **El commit de un worker cuya rama se borra antes de la siguiente vuelta (15 s):** con la rama se va su reflog, y ya no se recupera cuando llega a `main`. **El hueco de los workers crece:** ya no hace falta que el commit no llegue a `main`.
  4. **Commits hechos fuera de un clon con demonio:** la web de GitHub, CI, otra máquina, o un clon con `core.logAllRefUpdates=false` o con el reflog expirado (90 días por defecto).
  5. **Las notas de Anotar** (`commit-tree` y push directo a `refs/heads/main`, sin pasar por una rama local) no salen como `commit` de la persona. Solo tocan `criterios.md`: no cuentan para `servicios.md`.
- **Con el token del equipo, cualquier miembro puede enviar un evento `commit` en nombre de otro** (ADR-0008: el token es único para el equipo; issue #2, hallazgo 3). El relay valida el esquema, pero no puede saber de qué portátil viene un evento ni vincular `actor.persona` con nadie: quien lea `<git común>/hackathon/os/token` y `relay.url` (también un agente con Bash) puede mandar un `commit` «de» otra persona con el sha de un commit suyo y confirmar sus filas. Lo mismo con `servicio.estado` y `prueba`. «Hecho desde el portátil del dueño» vale frente a quien no tiene el token, no entre miembros del equipo.
