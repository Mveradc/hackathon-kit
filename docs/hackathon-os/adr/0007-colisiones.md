# ADR-0007 · Colisiones por niveles, solo avisos

Estado: **propuesta**. El nivel 2 necesita una decisión aparte sobre publicar el trabajo en curso.

## Contexto
El trabajo sin subir de cada persona solo existe en su portátil. Para predecir un conflicto real hace falta tener los dos lados como commits.

## Decisión
- **Nivel 1 (solapamiento)**: cada demonio envía los ficheros cambiados respecto de `origin/main` (commits sin subir + cambios sin commitear) de cada worktree. El relay cruza personas distintas. Barato y sin publicar nada.
- **Nivel 2 (conflicto real)**: opt-in en `os.md` (`publicar_wip: sí`). Cada 60 s, el demonio crea un commit del árbol con `git stash create` (no toca el árbol ni el índice; verificar en Windows en M8.0) y lo sube a `refs/hackathon/wip/<usuario>` con push forzado **solo a esa ref**. El relay hace `git fetch` de `refs/hackathon/wip/*` y ejecuta `git merge-tree --write-tree --name-only` por pares sobre la base común. Requiere Git ≥ 2.38 en el relay.
- **Nivel 2b**: si está Mergiraf, se reintenta la fusión de los ficheros en conflicto en modo estructural; si la resuelve, baja a amarillo (extra).
- **Nivel 3 (contratos)**: cada bloque de `docs/contratos.md` lleva `Vive en: <rutas>`; el dueño sale de `autoridad.md`. Cualquier cambio en esas rutas por otra persona es rojo y avisa a dueño y consumidores.
- **Reservas**: `reservar(rutas, ttl)` por MCP o automáticamente al reclamar una tarea (sus carpetas, compartidas). El hook PreToolUse de Edit/Write informa con `additionalContext`; nunca `deny`.

## Alternativas descartadas
- **Bloquear ediciones con PreToolUse**: bloqueos mutuos entre agentes que esperan reservas cruzadas; y el hook es una red, no una barrera.
- **Análisis por símbolos propio con tree-sitter**: caro de hacer bien; Mergiraf cubre la parte útil.
- **Guard en pre-commit** (como MCP Agent Mail): útil, pero los workers ya están serializados por el orquestador y las personas pueden desactivarlo. Extra.

## Consecuencias
- Con `publicar_wip: sí`, el trabajo a medias de cada persona está en el remoto (en refs que no son ramas). Si las bases exigen confidencialidad del código, se deja en `no` y solo queda el nivel 1.
- El push a `refs/hackathon/wip/*` lo hace el demonio, no un agente: el hook del orquestador no interviene.
