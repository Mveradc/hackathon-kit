# Resultados · 05 Hackathon UTP 2026, Reto 1 Journey Vocacional (diseño o impacto sin datos)

Cadena en headless (`../prueba-m4-05`), 2026-10-04. Enfoque A (ruta guiada), stack «nextjs con typescript», equipo ficticio de 5 personas (Persona C ausente el sábado de 09:00 a 15:00).

## Automáticas

| # | Resultado | Evidencia |
|---|---|---|
| A1 | Pasa | `plan.md`: 986 palabras con 5 personas; pitch: 737; CLAUDE.md: 63 líneas; 3 reglas, 2 skills |
| A2 | Pasa | `npm run arranca` sirve http://localhost:3000 con HTTP 200 y «hola mundo» en el HTML |
| A3 | Pasa | Todo en UTF-8; git ignora `.env` |
| A4 | Pasa | 11 reglas de equipo y 20 viñetas de `.claude/rules/` con origen; cifras con fila; criterios sin peso escritos como «sin peso publicado», fiel al análisis |
| A5 | Pasa | Sin copias de los ejemplos de otros retos. Sin repositorio de referencia |
| A6 | Pasa | Relanzados los cinco comandos: nada cambia salvo lo permitido (2,54 USD) |

## Observaciones

- **Next.js 16 escribe en el CLAUDE.md**: `next dev` añade al final un bloque `nextjs-agent-rules` y lo vuelve a añadir si se borra. `/hack-scaffold` lo detectó, lo dejó y lo contó en el resumen. El CLAUDE.md sigue por debajo de 100 líneas, pero ese bloque no lo controla el kit.
- El análisis marca como inferidos la zona horaria (UTC-5) y el carácter online del evento, y convierte la falta de entregables definidos en ambigüedad (3) y en riesgo de descalificación.
- El pitch sigue la estructura de las bases (5 min de presentación + 10 de demo + 5 de preguntas) y la cita.

## De criterio

Pendientes (agente revisor y usuario).

## Métricas

| Comando | Tiempo | Coste |
|---|---|---|
| `/hack-analyze` | 66 s | 0,35 USD |
| `/hack-approaches` + elección | 77 s | 0,71 USD |
| `/hack-scaffold` sin stack + con stack | 24 + 297 s | 0,23 + 0,61 USD |
| `/hack-plan` (crear `equipo.md` + plan) | 27 + 111 s | 0,23 + 0,57 USD |
| `/hack-pitch` | 65 s | 0,42 USD |
| **Total de comandos** | 11,1 min | 3,11 USD |

Tiempo de las personas (leer, decidir, rellenar `equipo.md`): no medido; requiere la pasada interactiva.
