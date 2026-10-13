# ADR-0004 · Hooks que escriben ficheros; un demonio local que agrega

Estado: **propuesta**.

## Contexto
Los hooks se ejecutan en cada llamada a herramienta de cada sesión y subagente. Tienen que ser baratos, portables (bash, sin `jq`) y no fallar sin red. Claude Code ofrece hooks `http`, pero la documentación no dice que su `url` admita variables (el puerto o la IP del relay cambian) ni que puedan ser `async`. Los procesos de monitor no reciben `CLAUDE_PLUGIN_OPTION_*` y solo existen en sesión interactiva.

## Decisión
- Los hooks del OS son `command` con `async: true` y solo **añaden una línea** a `<git común>/hackathon/os/eventos/<session_id>.jsonl`, envolviendo la entrada original sin parsearla. Sin red, sin `gh`.
- Un **demonio local por persona** (`hk-os agente`) lee esos ficheros, sondea git y habla con el relay. Lo arranca la persona (`hk-os agente`), o el monitor del plugin si no está vivo (decidir en M8.0: un monitor que lanza un proceso hijo de larga duración).
- El mismo binario sirve el **MCP stdio** del plugin (`.mcp.json`), que solo lee el estado del demonio por un fichero o socket local.

## Alternativas descartadas
- **Hook `http` directo al relay**: depende de la red en cada llamada, URL fija y sin `async` documentado.
- **Hook que hace POST con `curl`**: red en cada llamada; en Windows, más lento.
- **Que el monitor actual haga de demonio**: está escrito en bash con `gh`; agregar, seguir ficheros y servir SSE en bash no es razonable. Puede lanzarlo, no serlo.

## Consecuencias
- Si el demonio no corre, no se pierde nada: los eventos esperan en disco.
- Hay que rotar o limitar los JSONL (por sesión, se borran al cerrar el relay o tras 48 h).
