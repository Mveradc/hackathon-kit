# ADR-0006 · Una sola proyección para personas y agentes

Estado: **aceptada** (2026-10-14, tras el Paso 0 de M8.0; hallazgo P1 en `docs/coordinacion.md`).

## Decisión
- El relay calcula `estado.json` (esquema en `contratos/estado.schema.json`). Es la única fuente de las vistas.
- Vistas, generadas por el mismo módulo (`proyeccion`):
  - **web** de solo lectura servida por el relay (HTML estático + SSE; sin framework ni build);
  - **`estado-equipo.md`** por persona, escrito por su demonio, que leen los hooks de inyección;
  - **MCP**: `estado()`, `tarea(id)`, `colisiones()`, más `reclamar(id)` y `reservar(rutas, ttl)`.
- Un test de igualdad en el simulador: para cada guion, las tres vistas dan los mismos estados, dueños, colisiones y antigüedades (R-28).
- **Quién ve el MCP** (P1): el MCP del plugin está en la sesión normal, en `--agent` y en los subagentes, pero un agente con lista `tools:` solo ve las herramientas MCP que nombra. Sintaxis comprobada en M8.0, las tres válidas en `tools:`: el nombre completo (`mcp__plugin_<plugin>_<servidor>__<herramienta>`, solo esa), el servidor entero (`mcp__plugin_<plugin>_<servidor>`) o el comodín (`mcp__plugin_<plugin>_<servidor>__*`). Las dos últimas dan todas las herramientas del servidor, cargadas sin ToolSearch.
  - El **orquestador** añade a su `tools:` el servidor entero (`mcp__plugin_hackathon-kit_<servidor>`), para que una herramienta nueva no obligue a tocar su cabecera.
  - El **worker** y el **revisor** no lo llevan: lo que necesitan (el aviso de reserva o colisión antes de editar) les llega por el hook PreToolUse de Edit/Write.
  - En las sesiones normales, sin `tools:`, está disponible como herramienta diferida (se carga con ToolSearch).

## Alternativas descartadas
- **TUI**: quien no use Claude Code o no esté en su terminal no la ve.
- **GitHub Projects como interfaz principal**: no ve lo efímero ni las colisiones; sirve como vista secundaria gratis sobre los issues.
- **Que cada vista calcule el estado por su cuenta**: divergen.

## Por qué el MCP no contradice `docs/coordinacion.md`
Allí se descartó un MCP **compartido** como canal entre agentes (no cruza cuentas, experimental). Este MCP es local a cada persona, solo lee de su demonio, y el canal entre personas sigue siendo GitHub y el relay. Comprobado en M8.0 (P1): una sesión `--agent` ve los MCP del plugin, que son de sesión, aunque los agentes de plugin ignoran `mcpServers` en su cabecera, con la condición de `tools:` de arriba.
