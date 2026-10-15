# ADR-0007 · Colisiones por niveles, solo avisos

Estado: **aceptada** (2026-10-14, tras el Paso 0 de M8.0; hallazgos P9–P12 en `docs/coordinacion.md`). El nivel 2 sigue siendo opt-in.

## Contexto
El trabajo sin subir de cada persona solo existe en su portátil. Para predecir un conflicto real hace falta tener los dos lados como commits.

## Decisión
- **Nivel 1 (solapamiento)**: cada demonio envía los ficheros cambiados respecto de `origin/main` (commits sin subir + cambios sin commitear) de cada worktree. El relay cruza personas distintas. Barato y sin publicar nada.
- **Nivel 2 (conflicto real)**: opt-in en `os.md` (`publicar_wip: sí`). Cada 60 s, el demonio crea un commit del árbol con un **índice temporal** (`GIT_INDEX_FILE` apuntando a una copia del índice, `git add -A`, `write-tree`, `commit-tree -p HEAD`), que a diferencia de `git stash create` incluye los ficheros sin seguimiento. No toca el árbol, el índice ni HEAD (P9, Windows y Linux). Antes del `write-tree` se excluyen del índice temporal:
  - `.env*` en cualquier carpeta;
  - las carpetas de datos de `os.md` (`datos_excluidos:`, por defecto `data/` y `datos/`);
  - todo fichero de más de 1 MB.

  Lo excluido no se publica aunque esté en git. El commit se sube a `refs/hackathon/wip/<usuario>` con push forzado **solo a esa ref** y solo si cambió el sha (P10: permitido en un repo personal privado sin rulesets). El relay hace `git fetch` de `refs/hackathon/wip/*` y ejecuta `git merge-tree --write-tree --name-only` por pares sobre la base común. Requiere Git ≥ 2.38 en el relay.
- **Nivel 2b**: si está Mergiraf, se reintenta la fusión de los ficheros en conflicto en modo estructural; si la resuelve, baja a amarillo. Extra **fuera de la v1**: P12 no se comprobó.
- **Nivel 3 (contratos)**: cada bloque de `docs/contratos.md` lleva `Vive en: <rutas>`; el dueño sale de `autoridad.md`. Cualquier cambio en esas rutas por otra persona es rojo y avisa a dueño y consumidores.
- **Reservas**: `reservar(rutas, ttl)` por MCP o automáticamente al reclamar una tarea (sus carpetas, compartidas). El hook PreToolUse de Edit/Write informa con `additionalContext`; nunca `deny`.

## Notas de M8g (2026-10-15, decisiones del usuario al implementarlo)
- **Padre del commit de trabajo en curso:** la merge-base de HEAD con `origin/main`, no HEAD. Con HEAD, un commit local sin subir que lleve un fichero excluido (datos, una clave) viajaría al remoto como ancestro del WIP.
- **Exclusiones ampliadas** a `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `*.pfx`, `credentials*.json`, `secrets*` y `.claude/worktrees/`, y aplicadas como pathspecs `:(exclude)` del propio `git add`: lo excluido no llega a ser un objeto de git. Lo excluido que ya estaba en el índice o en la base vuelve a su versión de la base (borrarlo daría falsos conflictos modify/delete).
- **Cerrado ante la duda:** no publica si el repo de GitHub es público (salvo `publicar_wip: sí, incluso público`) ni si no puede saberlo; ni con un merge, rebase o cherry-pick a medias. Git sin diálogos de credenciales; tras un fallo de autenticación, espera 10 min.
- **`--no-verify` en ese push** (una ref que no es una rama): el `pre-push` de la persona no corre cada minuto.
- **Lo publicado se ve** en `wip.json`, en la línea `wip:` de `/salud` y en `agente.log`. Ninguna lista de exclusiones es completa (un `config.py` con una clave sube igual): `os.md` y el README lo avisan, y recuerdan que borrar la ref no borra lo subido (GitHub sigue sirviendo los objetos por su sha), así que una clave que suba hay que rotarla.
- **Solo la copia principal** publica; el trabajo de los workers entra cuando se fusiona en ella.
- **Reservas:** el `additionalContext` de PreToolUse llega al modelo con el resultado de la edición, no antes (paso 0 de M8g, `docs/coordinacion.md`). El aviso previo sale del bloque de inicio y de los deltas (sesión principal) y del `additionalContext` de SubagentStart (workers); el de PreToolUse queda como aviso al editar. Sigue sin haber `deny`.
- **Nivel 3:** los consumidores de un contrato son el resto del equipo; el dueño, el de la fila «`docs/contratos.md`: …» de `autoridad.md` o, sin ella, el de la carpeta de `Vive en:`. Con más de una candidata, el bloque se queda sin dueño.

## Alternativas descartadas
- **Bloquear ediciones con PreToolUse**: bloqueos mutuos entre agentes que esperan reservas cruzadas; y el hook es una red, no una barrera.
- **Análisis por símbolos propio con tree-sitter**: caro de hacer bien; Mergiraf cubre la parte útil.
- **Guard en pre-commit** (como MCP Agent Mail): útil, pero los workers ya están serializados por el orquestador y las personas pueden desactivarlo. Extra.

## Consecuencias
- Con `publicar_wip: sí`, el trabajo a medias de cada persona está en el remoto (en refs que no son ramas). Si las bases exigen confidencialidad del código, se deja en `no` y solo queda el nivel 1.
- El push a `refs/hackathon/wip/*` lo hace el demonio, no un agente: el hook del orquestador no interviene.
