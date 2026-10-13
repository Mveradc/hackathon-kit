# ADR-0005 · Lenguaje del demonio y del relay

Estado: **por decidir en M8.0**, con el criterio de abajo.

## Contexto
El kit es solo bash + `gh` para funcionar en Windows con Git Bash sin instalar nada (no hay `jq`). El demonio y el relay necesitan HTTP, SSE, JSON y concurrencia, que no son razonables en bash.

## Opciones
| Opción | A favor | En contra |
|---|---|---|
| **Python ≥ 3.10, solo biblioteca estándar** (`http.server`, `json`, `threading`, `subprocess`) | Se lee y se cambia con Claude Code en minutos; los retos del kit ya usan `uv` | No viene en Windows por defecto; versiones dispares |
| **Python con `uv run`** (script con dependencias en línea) | `uv` resuelve el intérprete y las dependencias en un comando | Requiere `uv` instalado |
| **Go, binarios por plataforma en el repo** | Un ejecutable sin dependencias | Binarios en el plugin (peso, confianza), compilación cruzada en cada cambio |
| **Node** | SSE y JSON nativos | Claude Code ya no exige Node; no está garantizado |

## Criterio de decisión (M8.0)
Gana la opción que cumple, en este orden:
1. Arranca en un Windows limpio con Git Bash, macOS y Linux con **como mucho un comando de instalación** documentado.
2. El relay sirve SSE a 5 clientes y 50 eventos/s sin perder eventos (prueba del simulador).
3. Menos código para el mismo contrato.

Propuesta por defecto si nada lo impide: **Python con `uv run`**, porque `uv` ya aparece en los stacks de los retos validados, con un modo de respaldo en biblioteca estándar pura.
