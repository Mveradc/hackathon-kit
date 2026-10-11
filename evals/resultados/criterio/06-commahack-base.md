# Revisor C1–C6 · 06-commahack · línea base (rúbrica con grave/leve)

Salidas antiguas (`prueba-m4-06`) revisadas con la rúbrica y el prompt nuevos, 2026-10-05. Comparación en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (leve) | `analisis.md`: «openpilot es open source» sin marcar como conocimiento externo, y «el que se convierte mal es el plazo de solicitud», aunque ese plazo no tiene hora en el enunciado |
| C2 | Falla (leve) | `enfoques.md`: en B, el texto dice «Cómputo extra: **media-alta**» y «Encaje con comma: **medio-alto**», pero la tabla pone «medio» en los dos |
| C3 | Falla (grave) | `CLAUDE.generado.md`: «Filtro eliminatorio: que haya demo en directo…» atribuido a «(enunciado)»; además, regla 7: «licencia y los avisos de openpilot (MIT)» con la etiqueta «(ambigüedad 7)» |
| C4 | Falla (leve) | `plan.md`: A escribe «solo en `src/musculo/…`», pero sus tareas escriben en `rutas/` y `resultados/`, y las de B en `datos/`; `pyproject.toml` no tiene dueño |
| C5 | Falla (grave) | `pitch.md`: «Fork de openpilot, pesos existentes…», «Enlace al repo del fork» y «El fork conserva licencia MIT», pero ninguna tarea de `plan.md` hace el fork |
| C6 | Falla (leve) | `plan.md`: contrato `Frame` «del tamaño acordado», sin tamaño fijado; la métrica por fotograma está sin definir; las guías `.claude/skills/` se citan pero no se entregan |

## Fallos encontrados

**Graves**

1. **Grave · C3 · `CLAUDE.generado.md`**
   - Cita: «Filtro eliminatorio: que haya demo en directo el domingo a las 15:00 y sea «algo que merezca la pena enseñar» (enunciado).»
   - Qué dice el enunciado: «construir algo que merezca la pena enseñar el domingo» y «domingo 15:00 demos y jurado». No habla de filtro ni de eliminatorio, y no publica ningún criterio.
   - El propio `analisis.md` lo dejó como criterio «probable» `(inferido)`. El CLAUDE.md lo sube a eliminatorio y le pone la etiqueta «(enunciado)», que es falsa.
   - Por qué importa: es justo el cambio de fuerza que prohíbe C1/C3, en el fichero que el agente lee primero («léelo antes de proponer nada»).

2. **Grave · C3 y C5 · `CLAUDE.generado.md` (regla 7), `reglas/convenciones.md` (último punto, sin MIT pero con la misma idea), `plan.md` y `pitch.md`**
   - Citas:
     - CLAUDE.md: «conserva la licencia y los avisos de openpilot (MIT) … (ambigüedad 7)».
     - `plan.md`: «¿Hay que publicar el fork con licencia MIT?».
     - `pitch.md`, respuesta al jurado: «El fork conserva licencia MIT».
   - Qué dice el enunciado: no menciona ninguna licencia.
   - La ambigüedad 7 del análisis solo dice «openpilot es open source; ¿hay que publicar con su licencia?». Ni la ambigüedad 7 ni el enunciado dicen «MIT», así que la etiqueta apunta a una fuente que no dice eso.
   - Es conocimiento externo (probablemente correcto, pero sin verificar) presentado como hecho. Además, en el pitch se dice ante el jurado sobre una cuestión que el propio análisis deja abierta.

3. **Grave · C5 · `pitch.md` y `CLAUDE.generado.md` (tesis)**
   - Citas:
     - Pitch: «Fork de openpilot, pesos existentes, inferencia desviada a chestnut», «Enlace al repo del fork» y «siguiente paso: abrir el PR».
     - Tesis del CLAUDE.md: «Fork de openpilot que ejecuta…».
   - Qué pasa en el plan: construye un paquete independiente `src/musculo/` (`routes/`, `compare/`, `models/`, `device/`). Ninguna tarea hace el fork, toca el código de openpilot ni publica un repo.
   - Por qué importa:
     - Se enseña como construido algo que nadie construye, y no va marcado como `[SI DA TIEMPO]`.
     - La persona A, que conoce openpilot, acaba dedicada a lectores de rutas y a la vista.
     - Si el jurado (equipo de comma, inferido) pregunta por el fork, no hay nada que enseñar.

**Leves**

4. **Leve · C5 · `pitch.md`**
   - Citas: «El modelo de openpilot está limitado por el cómputo del comma four» y, en el cierre, «Más cómputo, mejor percepción, medido y comparado».
   - Qué dice el enunciado: solo «ver qué puede hacer openpilot con más capacidad de cómputo». No afirma que haya un límite.
   - «Mejor percepción» es un resultado que depende de medir. Debería ir condicionado o como `[CIFRA]`, igual que las métricas del resto del guion.
   - Lo clasifico como leve porque las cifras concretas sí van como `[CIFRA]`. Pero, si la métrica no mejora, el cierre afirma algo falso.

5. **Leve · C1 · `analisis.md`, riesgo «Zonas horarias»**
   - Cita: «el que se convierte mal es el plazo de solicitud».
   - Qué dice el enunciado: «Solicitudes hasta el 8 de septiembre», sin hora. La justificación del riesgo no se sostiene sobre el texto. Aun así, no cambia nada de lo que se construye.

6. **Leve · C1 · `analisis.md`**
   - Cita de la ambigüedad 7: «openpilot es open source».
   - Qué dice el enunciado: nada sobre eso. Es conocimiento externo sin la marca correspondiente, y es el origen de la cadena que acaba en «MIT» (fallo 2).

7. **Leve · C1 · `analisis.md`, incoherencia interna**
   - En «Cómo se evalúa» infiere que «Se valoran positivamente… contribuciones a openpilot» se refiere a la **selección de participantes**.
   - En «Qué distinguiría a un proyecto ganador» usa «comma valora "contribuciones a openpilot"» como señal de lo que premia el jurado.
   - La misma cita se usa con dos sentidos distintos.

8. **Leve · C2 · `enfoques.md`**
   - El texto y la tabla de B no coinciden: cómputo «media-alta» frente a «medio», y encaje «medio-alto» frente a «medio».
   - B dice «viable en ~30 h» sin base.
   - B menciona «datasets públicos de comma» como conocimiento externo sin marcar, aunque añade «conviene confirmar».
   - Nada de esto cambia la elección. Los tres enfoques sí difieren en una decisión de fondo y ninguno se recomienda.

9. **Leve · C3 · `CLAUDE.generado.md`, «Qué puntúa»**
   - Cita: «Encaje con comma: … puede acabar en PR».
   - «Puede acabar en PR» sale de `enfoques.md` / `decision.md`, no del criterio inferido del análisis. Se mezcla un criterio inferido con un argumento del enfoque elegido.

10. **Leve · C3 · `CLAUDE.generado.md`**
    - Cita: «Guías de pasos: `.claude/skills/`».
    - Entre las salidas no hay ninguna guía, así que no se puede comprobar que cubran los momentos clave: la presentación de chestnut a las 19:00, la congelación y el cambio a plan B.

11. **Leve · C4 · `plan.md`, carpetas sin dueño o fuera de lo declarado**
    - A declara que escribe «solo en `src/musculo/contract.py`, `__init__.py`, `routes/`, `compare/`». Sin embargo, sus tareas escriben en `rutas/` («Descargar 2–3 rutas en `rutas/`») y en `resultados/` («Exportar vídeo… a `resultados/`»).
    - B declara «solo en `src/musculo/models/`», pero deja «Pesos en `datos/`».
    - `pyproject.toml`, creado por el scaffold, no tiene dueño. B tendrá que añadir dependencias de GPU y A el argumento `--route` del comando, así que hay riesgo de conflicto.
    - El guion del pitch de B tampoco tiene carpeta asignada.

12. **Leve · C4 · `plan.md`, hito del contrato**
    - Cita: «Vie 19:00 | Contrato `src/musculo/contract.py`» y, en la misma hora, «Vie 19:00 | Presentación de chestnut (van los tres)».
    - El contrato tiene que estar cerrado en la primera hora, y la tarea de C de acordar los valores de `device` con A vence también a las 19:00. Queda margen cero antes de una presentación a la que van los tres.
    - Algo parecido pasa con el hito de B: «Sáb 20:00 Chestnut» vence justo cuando B se va (20:00–23:00), sin margen. Hay un repliegue previsto (C lanza las pruebas), así que no lo clasifico como grave.

## C6: justificación

Sí, en buena parte. Las reglas de inferencia son concretas y comprobables: misma entrada, `transfer_ms`/`compute_ms` separados, dispositivo por configuración y repliegue sin colgarse. Cada persona sabe en qué subcarpeta trabaja, y las dependencias tienen desbloqueo.

Lo que echaría en falta:
- **Contrato a medio definir.** No se fija la forma de `Frame` («del tamaño acordado») ni qué contiene `InferenceResult` además de las latencias (salidas del modelo para la métrica). La métrica por fotograma «contra el log» no se define, y es lo que sostiene la pregunta «¿es mejor o solo distinto?».
- **Integración con openpilot.** No se dice cómo encaja el modelo de serie fuera de openpilot ni cómo se despliega `big.py` en el comma four. Ese es el corazón del enfoque A, y en su lugar hay un visor independiente que el pitch vende como «fork».
- **Portátiles.** C trabaja en Windows con USB/drivers y un `run_demo.sh`, y B en macOS, sin ninguna nota sobre portabilidad.

Lo que sobra o confunde:
- El «filtro eliminatorio» inventado.
- La «MIT» presentada como hecho.
- La tesis de «fork», que obligaría a reorientar el trabajo a mitad del sábado si alguien la toma al pie de la letra.