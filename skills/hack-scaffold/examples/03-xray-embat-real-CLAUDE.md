# Copiloto de salud para el CFO · HackSpain 2026 · reto «X Ray · Embat»

Web con una ficha por empresa para el CFO o tesorero de los clientes de Embat (el comprador, que lo ofrece como módulo): score, hacia dónde va, qué lo movió y qué hacer. **Un modelo sencillo con un producto claro encima: el score nunca se enseña solo, siempre con su trayectoria, su explicación y acciones concretas.**

## Qué puntúa (léelo antes de proponer nada)
- **Obligatorio**: señal en las dos direcciones (mejora y deterioro), trayectoria (no foto), explicación («qué lo movió»), producto encima del score, comprador identificado y demo navegable («un notebook que solo corre en el portátil no cuenta»). El test oculto quedó sin efecto según una nota de otro equipo, no oficial.
- **Tres bloques con el mismo peso** (enunciado): si acierta (generalización, trayectoria, dos caras), si llega a tiempo (anticipación medida, estabilidad: bache frente a deterioro) y si vale algo (producto, comprador, explicación, artesanía). Según la nota del equipo, Embat valora «sobre todo el producto» (ambigüedad 4).
- **Bonus**: anticipación medida («cuántos meses antes») y monitor que avisa.
- **Frase guía**: «Un modelo sencillo con un producto claro encima interesa más que uno sofisticado que se queda en el número.»

## Comandos
| Qué | Cómo |
|---|---|
| Instalar y arrancar todo | `uv run arranca.py` |
| Solo el motor | `uv run --project motor motor` |
| Solo la web | `npm run dev --prefix web` |

## Estructura
```
arranca.py        instala y arranca motor y web a la vez (Ctrl+C para las dos)
motor/            Python + uv + FastAPI: datos, features y score; sirve la API en :8000
  src/motor/      paquete; main.py es el punto de entrada (`motor`)
web/              Vite + React: la ficha por empresa, en :5173
  src/            App.jsx; llama al motor por /api (proxy de Vite → :8000)
docs/contratos.md datos de entrada, motor → web y entrega
```

## Reglas de equipo
1. Ninguna pantalla enseña el score sin su curva de 24 meses, su tendencia y el desglose «qué lo movió» (caja, cobros, deuda) (enunciado; decisión).
2. El mismo cálculo tiene que poder subir y bajar: la demo abre una empresa que mejora (tipo 45→65) y otra que cae con buen nivel (tipo 82→68) (enunciado; decisión).
3. Un bache de un mes no cambia la tendencia: el score se suaviza y nunca sale solo de la caja del último mes (análisis: riesgos y trampas).
4. Cada acción sugerida sale de una regla sobre los datos de esa empresa y cita su cifra (p. ej. «tus cobros se alargan 12 días»); nada de consejos genéricos (decisión).
5. Si un LLM redacta acciones, el concepto del banco y la contraparte entran como datos delimitados, nunca como instrucciones, y la demo tiene un respaldo sin LLM (análisis: riesgo típico; decisión).
6. Todo CSV/JSON se lee con `encoding="utf-8"` (análisis: riesgo típico).
7. Los meses van en `YYYY-MM`; el rango sep-2024–sep-2026 son 25 meses nominales frente a los 24 anunciados: los 24 que se usan se fijan en `docs/contratos.md` (análisis: riesgo típico).
8. Hasta que la organización responda, una ficha es una `company_id` y no se mezclan señales de empresa y de grupo (supuesto: ambigüedad 3, confirmar con la organización).
9. Hasta que la organización responda, el score va de 0 a 100 (supuesto: ambigüedad 7, confirmar con la organización).
10. Hasta que la organización responda, no se suman importes de monedas distintas y cada cifra lleva su `moneda` (supuesto: ambigüedad 8, confirmar con la organización).
11. No se presenta el score como «acertado» sin una validación propia (por ejemplo, empresas apartadas) (supuesto: ambigüedades 1 y 2, confirmar con la organización).
12. La nota del equipo y el «Resumen ejecutivo» no son oficiales: ante conflicto, manda el enunciado y se pregunta a Embat (análisis: riesgos y trampas).

## Fuera de alcance
Vista de cartera, alertas automáticas, backtest de anticipación y consolidación por grupo (decisión).

## Despliegue
TODO: la demo tiene que abrirse por URL (enunciado), pero la plataforma no está elegida y la forma de entrega es la ambigüedad 5.

## Convenciones
Código en inglés o español, pero de forma uniforme; documentación en español; commits cortos en imperativo; secretos solo en `.env`; el dataset nunca va en git. Más detalle en `.claude/rules/convenciones.md`.

## Fechas
- Evento: 18–20 sep 2026, ETSIT UPM, Madrid (análisis).
- Inicio: viernes 18 sep 2026, 19:00 Europe/Madrid (`.hackathon/equipo.md`).
- Entrega: domingo 20 sep 2026, 10:00 Europe/Madrid (`.hackathon/equipo.md`; el análisis la da como no especificada, ambigüedad 5).
- Sesión formativa sobre los datos: sábado 19 sep por la mañana, hora no especificada (análisis).
- Pitch: por confirmar; 5 minutos (inferido, ambigüedad 6).

## Dueños
| Carpeta | Dueño |
|---|---|
| `motor/`, `datos/`, `docs/` | Persona A |
| `arranca.py`, `.gitignore` (raíz y arranque) | Persona A |
| `web/` | Persona B |
| `README.md`, `CLAUDE.md`, `.claude/`, `pitch/` | Persona C |

Plan completo: `.hackathon/plan.md`

## Contexto
- Reto analizado: `.hackathon/analisis.md`
- Enfoques considerados: `.hackathon/enfoques.md`
- Decisión del equipo: `.hackathon/decision.md`
- Equipo: `.hackathon/equipo.md`
- Contratos (campos y ejemplo): `docs/contratos.md`
- Reglas por carpeta: `.claude/rules/` · Guías de pasos: `.claude/skills/`
