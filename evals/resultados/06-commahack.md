# Resultados · 06 COMMA_HACK 7 (mal especificado)

Cadena en headless (`../prueba-m4-06`), 2026-10-05. El texto lo facilitó el usuario; el original está en un agregador (ver `evals/retos/fuentes.md`). Enfoque A (openpilot con más músculo), stack «python con uv, una sola pieza» (opción 1 de las que propuso `/hack-scaffold`), equipo ficticio de 3 personas (Persona B ausente el sábado de 20:00 a 23:00).

## Automáticas

| # | Resultado | Evidencia |
|---|---|---|
| A1 | Pasa | `plan.md`: 814 palabras con 3 personas; pitch: 750; CLAUDE.md: 55 líneas; 2 reglas, 2 skills |
| A2 | Pasa | `uv run musculo` imprime «hola mundo» con código 0 en una copia limpia |
| A3 | Pasa | Todo en UTF-8; git ignora `.env` |
| A4 | Pasa | 8 reglas de equipo y 14 viñetas de `.claude/rules/` con origen; cifras con fila. **Pesos: N/A**, porque el análisis no publica rúbrica, y el guion no inventa ninguno |
| A5 | Pasa | Sin copias de los ejemplos de otros retos. Sin repositorio de referencia |
| A6 | Pasa | Relanzados los cinco comandos: nada cambia salvo lo permitido (1,36 USD) |

A4 tenía un hueco: sin rúbrica, el guion no tenía criterios con peso, A4 no comprobaba nada y pasaba sin decirlo («0 menciones»). Ahora, si «Cómo se evalúa» no tiene pesos, lo marca como N/A y falla si el guion del pitch tiene alguno. Control positivo: un «C2 (40 %)» metido en el guion da fallo («peso de relleno»).

## Lo que había que vigilar en un reto vago

- **`/hack-analyze`**:
  - marca como **No especificado** los entregables más allá de la demo, la duración de la demo, los criterios y pesos, el tamaño del equipo, las licencias y los datasets;
  - los «criterios que probablemente pesen» van marcados `(inferido)` y sin peso;
  - deja 7 preguntas concretas para la organización: rúbrica, entregables, coches o datasets, chestnuts por equipo, licencia, tamaño de equipo y edición nueva;
  - detecta que las fechas ya pasaron y que la fuente no es oficial;
  - interpreta que lo de «se valoran positivamente» se refiere a la selección de participantes, no al proyecto, y lo marca como inferido.
- **`/hack-approaches`**:
  - no inventa criterios: avisa de que el análisis no los da y compara los enfoques con los tres inferidos, marcados así en la tabla;
  - añade dos filas, «Riesgo técnico» y «Margen de tiempo», que no son criterios del jurado;
  - pequeña incoherencia: en el texto, el enfoque B puntúa «media-alta» en cómputo y «medio-alto» en encaje, pero en la tabla pone «medio» en las dos.
- **`/hack-pitch`**:
  - usa la estructura por defecto y lo dice («el análisis no da ninguna»);
  - la duración queda como `[CONFIRMAR: duración]` (ambigüedad 4);
  - los criterios C1–C3 aparecen citados del análisis, «todos inferidos y sin peso»;
  - el plan B y los ensayos van antes de las demos del domingo a las 15:00.
- **Hechos que no salen del enunciado**:
  - la regla 7 del CLAUDE.md y el pitch afirman que openpilot es **MIT**;
  - el dato es correcto, pero viene del conocimiento del modelo, no del enunciado ni del análisis;
  - la regla lo etiqueta «(ambigüedad 7)», pero esa ambigüedad pregunta por la licencia, no la fija. Se revisa en C1.
- El CLAUDE.md llama a la demo **«filtro eliminatorio»** citando el enunciado, y el enunciado no dice que sea eliminatoria. Es una exageración leve; se revisa en C1.
- El scaffold no incluye openpilot: el fork se trae aparte. Lo dice en el resumen y en el README.

## De criterio

Pendientes (agente revisor y usuario).

## Métricas

| Comando | Tiempo | Coste |
|---|---|---|
| `/hack-analyze` | 42 s | 0,25 USD |
| `/hack-approaches` + elección | 57 + 19 s | 0,27 + 0,35 USD |
| `/hack-scaffold` sin stack + con stack | 24 + 90 s | 0,21 + 0,44 USD |
| `/hack-plan` (crear `equipo.md` + plan) | 17 + 94 s | 0,22 + 0,37 USD |
| `/hack-pitch` | 52 s | 0,33 USD |
| **Total de comandos** | 6,6 min | 2,44 USD |

Tiempo de las personas (leer, decidir, rellenar `equipo.md`): no medido; requiere la pasada interactiva.
