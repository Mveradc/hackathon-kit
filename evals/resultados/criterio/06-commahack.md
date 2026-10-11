# Revisor C1–C6 · 06-commahack

Informe literal del revisor independiente (`claude -p` sin el plugin, 2026-10-05). Resumen y patrones en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla | `analisis.md`: «el que se convierte mal es el plazo de solicitud», pero el plazo («8 de septiembre») no tiene hora. «openpilot es open source» y «premian una demo convincente en directo» aparecen como hechos y no están en el enunciado |
| C2 | Falla | `enfoques.md`: en el texto B tiene «Cómputo extra: media-alta» y «Encaje: medio-alto», pero en la tabla comparativa sale «medio» en los dos |
| C3 | Falla | `CLAUDE.generado.md`: «Filtro eliminatorio: que haya demo en directo… (enunciado)» y regla 7 «licencia… de openpilot (MIT)… (ambigüedad 7)» |
| C4 | Falla | `plan.md`: no hay ninguna tarea que haga el «fork de openpilot» de la decisión. La entrega de `big.py` en chestnut (B) y el hito de C que lo usa vencen los dos el «Sáb 20:00», y esa dependencia no aparece. Pregunta «¿…con licencia MIT?» |
| C5 | Falla | `pitch.md`: «El fork conserva licencia MIT» y «el cuello es USB…, no el cómputo» como respuestas al jurado. «Fork de openpilot» aparece pero el plan no lo construye |
| C6 | Pasa | `plan.md`: en la primera hora cada persona tiene carpeta propia, tarea y desbloqueo («`Frame` falso con un array aleatorio»), aunque con lagunas (ver abajo) |

## Fallos encontrados
1. **Licencia MIT inventada y atribuida a una ambigüedad** (C3, C4, C5)
   - Dónde: `CLAUDE.generado.md`, regla 7: «conserva la licencia y los avisos de openpilot (MIT)… (ambigüedad 7)». `plan.md`: «7. ¿Hay que publicar el fork con licencia MIT?». `pitch.md`: «El fork conserva licencia MIT».
   - Qué dice el enunciado: nada sobre licencias. La ambigüedad 7 del análisis precisamente dice que no se sabe.
   - Por qué importa: la etiqueta apunta a una fuente que dice lo contrario, y el dato acaba como afirmación ante el jurado.
2. **«Filtro eliminatorio» con la etiqueta «(enunciado)»** (C3)
   - Dónde: `CLAUDE.generado.md`: «Filtro eliminatorio: que haya demo en directo el domingo a las 15:00 y sea «algo que merezca la pena enseñar» (enunciado)».
   - Qué dice el enunciado: no habla de eliminatorios ni publica criterios. El propio análysis lo trata como criterio «probablemente pesa (inferido)».
   - Por qué importa: convierte una inferencia en una regla dura atribuida a la fuente de verdad. Además saca ese criterio de la lista de lo que puntúa.
3. **El plan no construye lo que dicen la decisión y el pitch** (C4, C5)
   - Dónde: `decision.md` dice «un fork de openpilot que manda la inferencia a la eGPU». `plan.md` solo organiza un paquete propio, `src/musculo/`, que lee rutas y compara modelos. No hay ninguna tarea para hacer el fork ni para integrarlo en openpilot.
   - Arrastre: `pitch.md` dice «Fork de openpilot, … inferencia desviada a chestnut» y «Enlace al repo del fork».
   - Qué dice el enunciado: no aplica; es una incoherencia interna entre ficheros.
   - Por qué importa: el pitch promete algo que nadie tiene asignado.
4. **Resultados presupuestos en el pitch** (C5)
   - Dónde: `pitch.md`: «el cuello es USB ([CIFRA]), no el cómputo», «Más cómputo, mejor percepción» y «El modelo de openpilot está limitado por el cómputo del comma four».
   - Qué dice el enunciado: nada de esto. Son conclusiones que aún no se han medido.
   - Por qué importa: la cifra queda como hueco, pero la conclusión ya está escrita; si la medición sale al revés, el guion es falso.
5. **Dependencia sin declarar y sin margen** (C4)
   - Dónde: `plan.md`. B tiene «Sáb 20:00 · Ejecutar `big.py` en chestnut», justo cuando se va (20:00–23:00). C tiene «Sáb 20:00 · Conectar chestnut al comma four y lanzar `big.py`», que depende de lo anterior.
   - Qué dice el plan: en «Quién espera a quién» solo figura «B espera `device/` de C», no «C espera `big.py` de B».
   - Por qué importa: si B no termina, C se queda sin desbloqueo y B ya no está.
6. **Escrituras fuera de las carpetas con dueño** (C4)
   - Dónde: `plan.md`. A escribe en `rutas/` y `resultados/`, B en `datos/`, y el guion del pitch de B no tiene ubicación. Ninguna de esas carpetas está asignada en el reparto.
   - Además, C tiene «Detectar desconexión… y pasar a serie». Cambiar de modelo toca el encadenado de `__init__.py` (A) o `models/` (B), no solo `device/`.
7. **Supuestos técnicos sin marcar** (C4, C6)
   - Dónde: `plan.md`: «Correr el ejemplo oficial de chestnut».
   - Qué dice el enunciado: no menciona que exista un ejemplo oficial.
   - Además, C tiene portátil Windows (`equipo.md`) y se le asigna `device/run_demo.sh` y USB/drivers, sin tener en cuenta esa limitación.
8. **Comparativa de enfoques incoherente** (C2)
   - Dónde: `enfoques.md`. B pasa de «media-alta» a «medio» en cómputo y de «medio-alto» a «medio» en encaje entre el texto y la tabla.
   - Por qué importa: la tabla es lo que el equipo usa para elegir, y penaliza a B sin motivo. También aparece «viable en ~30 h», una estimación sin base.
9. **Riesgo típico de zona horaria mal justificado** (C1)
   - Dónde: `analisis.md`: «los plazos tienen hora ("18:00", "15:00")… el que se convierte mal es el plazo de solicitud».
   - Qué dice el enunciado: «Solicitudes hasta el 8 de septiembre», sin hora.
   - Por qué importa: la justificación se contradice con el ejemplo que da.
10. **Datos externos o inferencias presentadas como hechos** (C1, C3)
    - En `analisis.md`: «openpilot es open source» (ambigüedad 7), «premian una demo convincente en directo, no solo una idea» y «Una demo en directo» como entregable. Nada de esto está en el enunciado y no va marcado `(inferido)`. «openpilot es open source» es lo que acaba convertido en «MIT».
    - En `reglas/convenciones.md`: «Código… en inglés, como openpilot» es conocimiento externo.
11. **Guías de pasos inexistentes y convenciones genéricas** (C3)
    - Dónde: `CLAUDE.generado.md` remite a «Guías de pasos: `.claude/skills/`», pero no se generó ninguna. No hay guía para momentos clave como la presentación de chestnut, la congelación o el ensayo con fallo provocado.
    - Además, la mitad de `convenciones.md` («Secretos solo en `.env`», prefijos de commit) es genérica del kit y no propia del reto.
12. **Contrato no definido** (C4, C6)
    - Dónde: `plan.md`: «`Frame` falso con un array aleatorio del tamaño acordado».
    - El tamaño y el formato de `Frame` no se fijan en ningún sitio, y los dos desbloqueos de B y C dependen de ellos.

## C6: justificación
Sí, el equipo empezaría antes:
- Hay tres carpetas con dueño y un contrato con nombre (`Frame`, `InferenceResult` con `transfer_ms`/`compute_ms`, `device`).
- Las primeras tareas de cada persona son concretas: A escribe el contrato, B el modelo de serie y C prueba chestnut por USB.
- Hay desbloqueos con datos falsos y un plan B offline con dueño y hora.
- Las reglas de repliegue (caer al modelo de serie, no colgarse) se pueden comprobar.

Lo que echaría en falta:
- El esquema concreto de `Frame` (forma, tipo y formato).
- Cómo llega el código al comma four, y si de verdad hay fork de openpilot o solo un comparador aparte.
- Una salida para el portátil Windows de C.
- La dependencia de C respecto a B a las 20:00 del sábado.

Lo que sobra:
- Las convenciones genéricas del kit.
- La regla de «no LLM externo», que en un enfoque sin LLM no aporta nada.
- Un MIT inventado que puede hacer que el equipo afirme algo falso ante el equipo de comma.