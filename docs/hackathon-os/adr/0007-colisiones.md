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

## Alternativas descartadas
- **Bloquear ediciones con PreToolUse**: bloqueos mutuos entre agentes que esperan reservas cruzadas; y el hook es una red, no una barrera.
- **Análisis por símbolos propio con tree-sitter**: caro de hacer bien; Mergiraf cubre la parte útil.
- **Guard en pre-commit** (como MCP Agent Mail): útil, pero los workers ya están serializados por el orquestador y las personas pueden desactivarlo. Extra.

## Consecuencias
- Con `publicar_wip: sí`, el trabajo a medias de cada persona está en el remoto (en refs que no son ramas). Si las bases exigen confidencialidad del código, se deja en `no` y solo queda el nivel 1.
- El push a `refs/hackathon/wip/*` lo hace el demonio, no un agente: el hook del orquestador no interviene.
