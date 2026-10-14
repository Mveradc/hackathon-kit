# ADR-0005 · Lenguaje del demonio y del relay

Estado: **aceptada** (2026-10-14, tras el Paso 0 de M8.0; hallazgos P14 en `docs/coordinacion.md`).

## Contexto
El kit es solo bash + `gh` para funcionar en Windows con Git Bash sin instalar nada (no hay `jq`). El demonio y el relay necesitan HTTP, SSE, JSON y concurrencia, que no son razonables en bash.

## Decisión
- **Python, solo biblioteca estándar** (`http.server`, `json`, `threading`, `socket`, `subprocess`), en scripts con cabecera de dependencias en línea con `requires-python = ">=3.10"` y `dependencies = []`.
- Se lanzan siempre con **`uv run --no-project <script>`**: uv elige o descarga un intérprete que cumpla `requires-python`.
- **uv es requisito del OS** (no de la cadena 0.3.2), instalado con un comando. El guion de arranque (`arranque.md`, M8h) lo dice:
  - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - macOS y Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Criterio de decisión (resultados de M8.0)
| Opción | 1. Windows limpio, ≤ 1 comando | 2. SSE a 5 clientes, 50 ev/s, 2 min | 3. Código |
|---|---|---|---|
| Biblioteca estándar con `uv run` | **Sí**: Windows Sandbox con Git for Windows + uv; `uv run --no-project sse_prueba.py` acaba en `OK` en 38 s, contando la descarga de Python | **Sí**: 6.000/6.000 en orden en cada cliente, p99 < 30 ms (Python 3.12 de uv) | Un script (`evals/coordinacion/paso0-m8/sse_prueba.py`, ~130 líneas con los clientes de prueba) |
| Biblioteca estándar con `python` | **No**: en Windows Sandbox, «python not found» | Sí (Python 3.14 del sistema) | El mismo |
| Go, binarios por plataforma | No probado | No probado | Descartado: binarios en el plugin (peso, confianza) y compilación cruzada en cada cambio |
| Node | No probado | No probado | Descartado: Claude Code ya no exige Node, así que no está garantizado |

## Consecuencias
- Un solo código para los tres sistemas. Sin dependencias de PyPI, `uv run` no necesita red tras la primera descarga del intérprete.
- Quien ya tenga Python ≥ 3.10 podría lanzar los scripts con `python`, pero el OS no lo usa: siempre `uv run`, para que todos los portátiles se comporten igual.
- Pendiente para M8d: comprobar el arranque en macOS y Linux. M8.0 solo probó Windows y Windows Sandbox.
