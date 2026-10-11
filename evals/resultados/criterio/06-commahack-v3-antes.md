# Revisor C1–C6 · 06-commahack · tercera pasada, antes de /hack-check

Cadena `../prueba-m4-06-v2` revisada con la rúbrica de cierre (bloqueantes, C6 Sí/En parte/No), 2026-10-06.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (leve) | `analisis.md`: «todas las horas del enunciado son locales» (riesgo típico) se da como hecho, y el enunciado no dice la zona horaria. |
| C2 | Falla (leve) | `enfoques.md`, tabla: para C, «Dependencia de ambigüedades: 5», pero su texto de riesgos cita también «(1, 9)». |
| C3 | Falla (grave) | `reglas/inferencia-chestnut.md`: «No se escribe código de entrenamiento […] (decisión)». `decision.md` solo excluye «entrenar un modelo desde cero». |
| C4 | Falla (grave) | `plan.md`, B: «Variante ampliada (más resolución o más frames), sin entrenar» y la comprobación «≥3 casos donde el ampliado acierta y el base no». |
| C5 | Falla (grave) | `pitch.md`, primera pregunta: «Variante del modelo de openpilot con más resolución o frames, sin entrenar». |
| C6 | En parte | Carpetas, contratos y dueños están claros, pero lo central (el modelo «ampliado») no tiene un camino viable. |

Bloqueantes: ninguno

## Fallos encontrados

**1. Grave, no bloqueante. C3, C4 y C5.** El modelo «ampliado sin entrenar» no tiene base y la regla lo atribuye a la decisión sin que esta lo diga.
- **Dónde:** `reglas/inferencia-chestnut.md` («No se escribe código de entrenamiento: el modelo ampliado se obtiene a partir de modelos que ya existen […] (decisión)»), `plan.md` (B: «Variante ampliada (más resolución o más frames), sin entrenar»; repliegue: «Ampliado = base con más resolución»), `pitch.md` (bloque 2:30: «más resolución o frames, sin entrenar»; primera pregunta del jurado) y `CLAUDE.generado.md` («un modelo de conducción más grande (más resolución, más contexto temporal o más frames)»).
- **Qué dice la fuente:** `decision.md` solo deja fuera «entrenar un modelo desde cero». No prohíbe el ajuste fino. La etiqueta «(decisión)» exagera lo que dice la decisión. El enunciado no dice nada sobre esto.
- **Por qué importa:** esto es conocimiento externo mío y habría que verificarlo. Una red ya entrenada con entradas de tamaño y número de frames fijos no acepta más resolución ni más frames sin cambiar la arquitectura y volver a entrenarla. Si no lo hace, tampoco hay razón para que «acierte donde el base no».
  - La tarea de B y el hito de las 12:00 del sábado pueden acabar en algo que haya que deshacer.
  - La comprobación «≥3 casos» da por hecho un resultado que no está demostrado.
  - En el pitch, el equipo defendería ante el jurado algo que probablemente no tiene.
  - Ninguna pregunta del jurado ataca este punto débil.

**2. Leve. C4.** El hito de las 21:00 del viernes depende de una tarea que acaba a las 24:00.
- **Dónde:** `plan.md`: «vie 21:00 | Modelo base corriendo en comma four con chestnut | C | Una latencia medida con chestnut».
- **El problema:**
  - El modelo base es tarea de B hasta las 24:00 del viernes («Cargar el modelo de conducción de openpilot»).
  - El bloque de C a las 21:00 solo comprueba «El comma four ve la GPU».
  - La medida base de C es para las 12:00 del sábado.
- **Por qué es leve:** el hito no se puede cumplir tal como está escrito, pero tiene repliegue y no afecta a ninguna entrega.

**3. Leve. C3 y C4.** La regla 7 choca con el plan y no dice de dónde salen las rutas.
- **Qué dice la regla:** `CLAUDE.generado.md`, regla 7: «se da por hecho que no habrá rutas disponibles durante el evento: se consiguen y se guardan en `datos/` antes de empezar a programar».
- **Qué dice el plan:** A las descarga durante el evento, en la primera hora («Descargar 2 rutas de comma […] (regla 7)»). No se dice de dónde ni si hace falta un token.
- **Por qué importa:** si hace falta un token, no hay ninguna tarea que lo meta en `.env`. Además, `quality.py` necesita la trayectoria real del log, así que todo depende de este paso.

**4. Leve. C1, C3 y C5.** La hora del Pacífico se da como hecho.
- **Dónde:**
  - `analisis.md`: «todas las horas del enunciado son locales».
  - `CLAUDE.generado.md`: «Obligatorio: una demo el domingo 20/09 a las 15:00 (hora del Pacífico)».
  - Regla 9 del CLAUDE y `convenciones.md`, etiquetadas «(análisis: riesgo típico)».
- **Qué dice el enunciado:** no menciona ninguna zona horaria. Es una inferencia razonable, pero no va marcada como tal.

**5. Leve. C1 y C3.** La demo pasa a ser «obligatoria».
- **Dónde:** `analisis.md` la pone bajo «Qué hay que entregar» sin marcarla, y `CLAUDE.generado.md` dice «Obligatorio: una demo».
- **Qué dice el enunciado:** «domingo 15:00 demos y jurado» y «algo que merezca la pena enseñar el domingo». No dice «obligatorio».
- **Matiz:** en la misma línea, el análisis también endurece «traen su portátil» a «deben llevar».

**6. Leve. C3.** Un «pueden» del análisis se convierte en un hecho.
- **Qué dice el análisis:** «pueden no funcionar igual en Windows o macOS».
- **Qué dice la regla:** regla 10 de `CLAUDE.generado.md`: «no funcionan igual en Windows ni en macOS (análisis: riesgo típico)».
- **Lo mismo en otra regla:** `replay-y-metricas.md` usa ese riesgo típico para justificar medir en el comma four, cosa que el riesgo no dice.

**7. Leve. C3.** Se da por hecha una «GPU del comma four».
- **Dónde:** `inferencia-chestnut.md`: «chestnut, la GPU del comma four o la CPU».
- **El problema:** el enunciado no dice que el comma four tenga GPU propia, y la afirmación no va marcada como conocimiento externo.

**8. Leve. C5.** La licencia lleva una etiqueta equivocada.
- **Dónde:** `pitch.md`: «aviso de licencia MIT conservado (supuesto, ambigüedad 8)».
- **El problema:** la ambigüedad 8 no dice MIT. En el análisis, lo de MIT es «conocimiento externo, verificar».

**9. Leve. C5.** Algunas frases del pitch prometen más de lo que hay.
- **Qué prometen:**
  - «listo para proponer», cuando el PR es [SI DA TIEMPO].
  - «cualquier ruta», cuando solo se prueba con 2.
  - «enlace al repo», cuando no hay ninguna tarea para publicar el repo y la licencia sigue abierta (ambigüedad 8).
  - «el README del repo» como material de impacto, cuando la tarea de B solo anota lo traído de antes.
- **Por qué es leve:** son matices de redacción, no resultados inventados.

**10. Leve. C4.** `salidas/` es de C, pero escriben en ella otros.
- **El problema:** `compare.py` de A escribe el mp4 en `salidas/` («mp4 en `salidas/`»). Además, `.env.example`, que mencionan las convenciones, no tiene dueño.

**11. Leve. C3.** Hay partes que no se pueden comprobar o que faltan.
- **Guías de pasos:** el plan cita `/montar-chestnut` y `/respuesta-organizacion`, y el CLAUDE.md remite a `.claude/skills/`, pero no están entre las salidas. No he podido comprobar si cubren los momentos clave.
- **Comandos:** la tabla de comandos del CLAUDE.md solo tiene `uv run mas-modelo`. Faltan `compare` y `replay`, aunque los usa el plan.
- **`.gitignore`:** ninguna tarea comprueba lo que contiene (`.env`, `datos/`, `salidas/`). No lo marco como bloqueante porque no hay ningún secreto concreto expuesto.

**12. Leve. C2.** La tabla comparativa no cuadra del todo con el texto de los enfoques.
- **El problema:** la fila «Dependencia de ambigüedades» omite la 1 y la 9, que el texto de A y de C sí cita.
- **Matiz:** C mezcla «bajo (openpilot) / alto (chestnut)» en un criterio que el análisis plantea como uno solo.
- **Por qué es leve:** no altera la elección. Por lo demás, C2 está bien: los enfoques difieren en el fondo, no nombran stacks y ninguno se recomienda.

**Comprobado sin fallo:**
- **Fechas y horas:** coinciden con el enunciado en todos los ficheros: viernes 18:00, chestnut a las 19:00, demos el domingo a las 15:00, ganadores a las 18:00 y 45 h de trabajo.
- **Entregables:** no se inventa ninguno; la falta de entregables y de criterios queda como ambigüedad.
- **Fechas pasadas:** se avisa de que ya han pasado (ambigüedad 10) y se pregunta «antes de nada».
- **Disponibilidad de B:** su ausencia del sábado de 20:00 a 23:00 está respetada.
- **`verificacion.md`:** no existe.

## C6: justificación
En parte. Lo que funciona:
- Cada persona sabe en los primeros 30 minutos qué ficheros son suyos, contra qué contrato trabaja (`Frame`, `load_model`/`run`, la fila de métricas) y qué hacer mientras espera a los demás.
- La estructura es muy accionable: hitos, repliegues, reparto de descansos y el plan B de la demo.

Lo que falla es la pieza central. «Modelo ampliado sin entrenar, más resolución o más frames» casi seguro no se puede hacer así. B trabajaría hasta el sábado a las 12:00 en algo que luego habría que replantear, y A y C acabarían comparando dos variantes sin una diferencia real.

Lo que echaría en falta:
- Una decisión explícita sobre cómo se consigue el modelo ampliado: ajuste fino, otro modelo ya existente o más cómputo por frame (ensembles, más frecuencia).
- De dónde salen las rutas y si hace falta un token para descargarlas.
- Las guías de pasos que el plan cita y no están.

Sobra repetir el aviso de fechas en cada fichero, y también parte de la tabla de enfoques que no cuadra con el texto.