# Pruebas de la coordinación y del Hackathon OS

Ninguna gasta en modelos. Se lanzan desde la raíz del kit. En Windows, con Git for Windows instalado (los hooks se ejecutan con su `bash`).

| Qué | Comando | Salida |
|---|---|---|
| Motor de estados, modelo y esquemas (`hkos/`) | `uv run --no-project --with "jsonschema[format-nongpl]" -m unittest discover -s hkos/pruebas -v` | 0 OK · 1 falla. Sin jsonschema (o con uno sin Draft 2020-12 y su comprobador de formatos, como la 3.2 o la 4.0), las pruebas de esquema salen como *skipped* y el resto se ejecuta |
| Simulador, guiones G1–G4 | `uv run --no-project --with "jsonschema[format-nongpl]" evals/coordinacion/simulador/prueba_simulador.py` | 0 OK · 1 falla · **77 saltada** (sin jsonschema utilizable) |
| Un guion suelto | `uv run --no-project evals/coordinacion/simulador/simula.py evals/coordinacion/simulador/guiones/G2.json [--salida estado.json]` | 0 OK · 1 algún punto de control no coincide |
| Hooks (orquestador, buzón y Hackathon OS) | `python evals/coordinacion/prueba_hooks.py` | 0 OK · 1 algún caso falla. Tarda 1–2 min: la prueba de escrituras simultáneas lanza 50 rondas de 20 hooks; `HK_RONDAS=2` la acorta |
| Coste por llamada de los hooks del OS | `python evals/coordinacion/coste_hooks.py [N]` | Informe en ms; no compara con un umbral |

Con `--python 3.10` detrás de `--no-project`, las de `uv` se ejecutan con la versión mínima (`requires-python >= 3.10`).

## Qué hay aquí
- `prueba_hooks.py`: los hooks con entradas simuladas y, desde M8c, los del Hackathon OS: interruptor apagado (ni escrituras ni red), entradas reales de `entradas/` pasadas por los hooks que les tocan según `hooks/hooks.json` y normalizadas con `hkos/normaliza.py`, recortes del campo `git`, entradas grandes, escrituras simultáneas, líneas rotas, `arbol.sh` y la línea de la compuerta.
- `entradas/`: entradas reales de los hooks (M8.0, anonimizadas) y `normalizadas.json`, el evento que corresponde a cada una.
- `simulador/`: el simulador del M8 y sus guiones.
- `partida-m8-03/`: estado de partida del orquestador de B para `../prueba-m8-03-base`.
- `coste.py`: coste en USD de una sesión del orquestador (transcripts). `coste_hooks.py`: ms por llamada de los hooks del OS.
- `gh-falso.sh`: `gh` de mentira para las pruebas del buzón.
- `paso0-m8/`: plugins de juguete y scripts del Paso 0 (M8.0).
- `prueba.md`: resultados de cada hito.
