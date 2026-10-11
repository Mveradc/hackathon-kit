# Plan del equipo · X Ray · Embat (HackSpain 2026)

39 horas (vie 18 sep 19:00 → dom 20 sep 10:00), 3 personas, hora de Europe/Madrid. Hitos: contratos vie 20:00 · demo mínima sáb 10:30 · congelación dom 05:00 · entrega dom 09:30 (límite 10:00).

## Hitos del equipo
| Cuándo | Qué | Dueño | Cómo se comprueba | Repliegue si no está |
|---|---|---|---|---|
| Vie 20:00 | Contratos acordados: ficha motor → web y ventana de 24 meses | A | `docs/contratos.md` sin TODO en ficha ni en meses | — |
| Sáb mañana (hora por confirmar) | Sesión formativa sobre los datos | A | Respuestas en `docs/contratos.md` | — |
| Sáb 10:30 | **Demo mínima**: `uv run arranca.py` abre la ficha real de dos empresas | A | Score, curva, desglose y acciones salen del motor, no del ejemplo | La ficha usa score sin suavizar y una sola regla de acción; decide A |
| Sáb 16:00 | **Demo por URL** (ambigüedad 5) | A | Se abre desde un móvil en otra red | Demo en local en el portátil de B más vídeo de la ficha; decide C |
| Sáb 20:00 | Entrega temprana, si el canal permite volver a entregar | C | Hay acuse de la organización | — |
| Dom 05:00 | **Congelación**: después, solo arreglos y pitch | C | Último commit de funcionalidad antes de las 05:00 | Se quita de la demo lo que no esté estable; decide C |
| Dom 07:00 | Ensayo 1 completo (guía `ensayo-demo`) | C | Cronometrado ≤ 5 min (inferido, ambigüedad 6) | — |
| Dom 08:30 | Ensayo 2 completo, con la URL pública | B | Sin cortes ni pantallas en blanco | — |
| Dom 09:30 | Entrega final (guía `entrega`) | C | Acuse antes de las 10:00 | — |

## Por persona

### A · escribe solo en `motor/`, `datos/`, `docs/`, `arranca.py`, `.gitignore`
| Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|
| Vie 20:30 | Contratos | Servir en `motor/` la ficha del ejemplo de `docs/contratos.md` | `GET /api/empresas/EJ-0001/ficha` devuelve 24 meses |
| Vie 23:30 | Datos | Cargar los CSV de `datos/` en UTF-8 a tabla mensual por `company_id` | 1.286 empresas × 24 meses |
| | | Calcular caja, días de cobro y deuda por mes, con su `moneda` | Sin nulos ni monedas sumadas |
| Sáb 03:00 | Score | Score 0–100 suavizado a partir de las tres señales | Un bache de un mes no cambia la tendencia |
| | | Calcular `tendencia` y `desglose` del último mes | El desglose explica el cambio del mes |
| Sáb 10:30 | Acciones | Implementar las reglas de C, cada una con su cifra | Las dos empresas de la demo tienen ≥ 2 acciones |
| Sáb 16:00 | Despliegue | Publicar motor y build de la web en una URL (conocimiento externo, verificar plataforma) | La URL abre una ficha real |
| Sáb 22:00 | Robustez | Arreglar errores en 30 empresas al azar | Ninguna da error 500 |
| | | Si Embat pide validación propia: medir estabilidad en empresas apartadas | Cifra apuntada en `docs/contratos.md` |

### B · escribe solo en `web/`
| Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|
| Vie 23:00 | Ficha | Pintar en `web/src/App.jsx` score, curva de 24 meses y flecha | Se ve con el JSON del ejemplo |
| | | Pintar el desglose caja / cobros / deuda con signo | Cada barra muestra puntos de score |
| | | Pintar las acciones con su cifra destacada | 3 acciones visibles |
| Sáb 01:00 | Navegación | Selector de `company_id` que llama a `/api` | Cambiar de empresa cambia la ficha |
| Sáb 09:00 | Integración | Conectar con la ficha real del motor | Dos empresas cargan sin errores en consola |
| Sáb 15:00 | Producto | Inicio con acceso en dos clics a las dos empresas de la demo | Dos clics a cada ficha |
| | | Estados de carga, vacío y sin acciones | Ninguna pantalla en blanco |
| | | `npm run build` listo para que A lo despliegue | Build sin errores |
| Sáb 23:00 | Pulido | Textos para el CFO revisados con C | Ningún texto en inglés ni genérico |
| Dom 07:00 | Pitch | Guion de clics de la demo en vivo | Demo recorrida en ≤ 2 min |

### C · escribe solo en `README.md`, `CLAUDE.md`, `.claude/`, `pitch/`
| Hasta | Bloque | Tarea | Cómo se comprueba |
|---|---|---|---|
| Vie 21:00 | Preguntas | Apuntar las respuestas de Embat en `CLAUDE.md` | Cada supuesto marcado como confirmado o no |
| Vie 23:30 | Reglas | Escribir 5–6 reglas de acción en `.claude/rules/ficha-y-acciones.md` | Cada regla con campo, umbral y texto con cifra |
| Sáb 14:00 | Empresas | Elegir una empresa que mejora (~45→65) y otra que cae (~82→68) | Sus `company_id` en `.claude/skills/ensayo-demo/SKILL.md` |
| | | Escribir qué movió a cada una y qué haría su CFO | 3 frases con cifras por empresa |
| Sáb 19:00 | Pitch | Guion de 5 min en `pitch/guion.md`: comprador Embat, problema, demo, cierre | Leído en voz alta ≤ 5 min |
| | | Diapositivas en `pitch/` | ≤ 6 diapositivas |
| Sáb 22:00 | README | Cómo abrir la demo, URL y comprador en `README.md` | B la abre siguiendo solo el README |
| Dom 04:00 | Cierre | Completar los TODO de la guía `entrega` (canal y comandos) | Guía sin TODO |

`.hackathon/`: no se edita.

## Quién espera a quién
- **B espera la ficha real de A** (sáb 09:00): B trabaja contra el ejemplo que A sirve desde vie 20:30.
- **A espera las reglas de C** (vie 23:30): A empieza por la regla de días de cobro.
- **C espera el score real** (sáb 10:30): A le pasa curvas provisionales a las 03:00.
- **A espera la build de B** (sáb 15:00): A ensaya el despliegue con la web del scaffold.

## Preguntas a la organización
| Ambigüedad | Dueño | Límite |
|---|---|---|
| 5 · Hora, canal y formato de entrega; ¿hace falta URL pública? | C | Vie 20:00 |
| 6 · Duración del pitch y turno de preguntas | C | Vie 20:00 |
| 4 · ¿Mismo peso de los tres bloques o prima el producto? | C | Vie 21:00 |
| 1 y 2 · ¿Validación propia? ¿Hay etiqueta de salud? | A | Sesión formativa del sábado |
| 3 · ¿Score por empresa o por grupo? | A | Sesión formativa del sábado |
| 7 · ¿Escala 0–100? | A | Sesión formativa del sábado |
| 8 · ¿Cómo se tratan las monedas? | A | Sesión formativa del sábado |

## Descansos
| Quién | Noche 1 | Noche 2 |
|---|---|---|
| C (presenta) | Vie 23:30 – sáb 05:30 | Sáb 23:00 – dom 03:30 |
| B (presenta) | Sáb 01:00 – 07:00 (fuera además 09:00–12:00) | Sáb 23:30 – dom 04:00 |
| A | Sáb 03:00 – 08:00 | Dom 05:00 – 08:00 |
