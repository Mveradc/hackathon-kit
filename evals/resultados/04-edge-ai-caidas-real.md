# Resultados · 04 Edge AI Hackathon 2026, BIO-06 (hardware)

Cadena en headless (`../prueba-m4-04`), 2026-10-04. Enfoque A (colgante ESP32, Track 3), stack «platformio arduino + python con uv, receptor ESP32», equipo ficticio de 3 personas (Persona C llega el segundo día).

## Automáticas

| # | Resultado | Evidencia |
|---|---|---|
| A1 | Falla | `plan.md`: 1.104 palabras (máx. 1.100) con 3 personas. Aviso para C4: el bloque «Falsas alarmas» de Persona B tiene 4 tareas separadas por «;». Pitch: 782 palabras; CLAUDE.md: 54 líneas; 3 reglas, 3 skills |
| A2 | Pasa | `uv run arranca.py` compila `colgante/` y `receptor/` y la pieza `datos/` imprime «hola mundo» (86 s con la toolchain en caché; ~6 min la primera vez). **El hola mundo del firmware (serie y ESP-NOW) no se puede comprobar sin placas**; el comando lo dice y da el modo de flasheo |
| A3 | Pasa | Todo en UTF-8; git ignora `.env` |
| A4 | Falla | `.claude/rules/datos.md`: una viñeta acaba en «(Track 3: Code Efficiency, Cost Effectiveness)»: nombra el criterio, no una de las etiquetas de origen. Las otras 18 viñetas y las 9 reglas de equipo, bien. Cifras y pesos del pitch, bien |
| A5 | Pasa | Sin copias de los ejemplos de otros retos. Sin repositorio de referencia |
| A6 | Pasa | Relanzados los cinco comandos: nada cambia salvo lo permitido (2,50 USD) |

## Qué hace `/hack-scaffold` con hardware

- Sin stack, se para y propone tres (PlatformIO + uv, ESP-IDF + uv, Edge Impulse) con pros y contras, y deja el receptor pendiente de la ambigüedad 4.
- Con stack: piezas `colgante/`, `receptor/` y `datos/`; arranque único `uv run arranca.py` (script uv con PlatformIO como dependencia, Python ≤ 3.13 porque PlatformIO no va con 3.14) y modo `uv run arranca.py <pieza> <puerto>` para flashear y abrir el monitor serie.
- La placa queda como `esp32dev` con `TODO` hasta resolver la ambigüedad 2; elige ESP-NOW para que la alerta no dependa del Wi-Fi del recinto (decisión anotada como revisable).
- La verificación del paso 4 se queda en «compila»: lo dice en el resumen y en el README.

## De criterio

Pendientes (agente revisor y usuario). Para C1, el análisis detecta la incoherencia de la fuente (el «60 % restante» suma 100 % y repite «Track-Specific Technical Performance») como ambigüedad 8 y marca como inferidos los pesos sobre el total.

## Métricas

| Comando | Tiempo | Coste |
|---|---|---|
| `/hack-analyze` | 63 s | 0,35 USD |
| `/hack-approaches` + elección | 84 s | 0,75 USD |
| `/hack-scaffold` sin stack + con stack | 27 s + **no fiable** (el JSON solo recoge el último turno; la compilación tardó ~6 min) | 0,21 + 0,79 USD |
| `/hack-plan` (crear `equipo.md` + plan) | 27 + 84 s | 0,20 + 0,47 USD |
| `/hack-pitch` | 56 s | 0,39 USD |
| **Total de comandos** | ≥ 6,6 min (≈ 12 min con la compilación) | 3,15 USD |

Tiempo de las personas (leer, decidir, rellenar `equipo.md`): no medido; requiere la pasada interactiva.
