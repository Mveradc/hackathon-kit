# ADR-0006 · Una sola proyección para personas y agentes

Estado: **propuesta**.

## Decisión
- El relay calcula `estado.json` (esquema en `contratos/estado.schema.json`). Es la única fuente de las vistas.
- Vistas, generadas por el mismo módulo (`proyeccion`):
  - **web** de solo lectura servida por el relay (HTML estático + SSE; sin framework ni build);
  - **`estado-equipo.md`** por persona, escrito por su demonio, que leen los hooks de inyección;
  - **MCP**: `estado()`, `tarea(id)`, `colisiones()`, más `reclamar(id)` y `reservar(rutas, ttl)`.
- Un test de igualdad en el simulador: para cada guion, las tres vistas dan los mismos estados, dueños, colisiones y antigüedades (R-28).

## Alternativas descartadas
- **TUI**: quien no use Claude Code o no esté en su terminal no la ve.
- **GitHub Projects como interfaz principal**: no ve lo efímero ni las colisiones; sirve como vista secundaria gratis sobre los issues.
- **Que cada vista calcule el estado por su cuenta**: divergen.

## Por qué el MCP no contradice `docs/coordinacion.md`
Allí se descartó un MCP **compartido** como canal entre agentes (no cruza cuentas, experimental). Este MCP es local a cada persona, solo lee de su demonio, y el canal entre personas sigue siendo GitHub y el relay. Falta verificar en M8.0 que una sesión `--agent hackathon-kit:orquestador` ve los MCP del plugin (los agentes de plugin ignoran `mcpServers` en su cabecera, pero los del plugin son de sesión).
