# Enfoques — X Ray · Embat (HackSpain 2026)

Fecha: 2026-10-10

> Avisos heredados del análisis: el fichero del reto es una transcripción de un equipo; la anulación del test oculto llega por una nota de ese equipo, no de la organización. Sin contexto de equipo: cada enfoque indica el perfil que necesita. Las fechas del evento (18–20 sep 2026) ya han pasado respecto a hoy (10 oct 2026).

Base común a los tres (mínimo obligatorio): score mensual por empresa con trayectoria (pendiente y dirección, no solo el último mes), sensible a mejora y a deterioro, suavizado para separar bache de caída, con explicación de qué lo movió; producto encima; comprador nombrado; demo navegable (no notebook local). Si se exige URL pública depende de la ambigüedad 5.

---

### A — Copiloto de salud para el CFO
- **Idea**: cada empresa ve su propio score, hacia dónde va y qué hacer. Es para el CFO o tesorero de las empresas cliente; el comprador es Embat, que lo ofrece como módulo a sus clientes.
- **Qué se construye**: web con una ficha por empresa: score 0–100 (escala inferida, ambigüedad 7), curva de 24 meses, flecha de tendencia, desglose «qué lo movió este mes» (caja, cobros, deuda) y 2–3 acciones sugeridas a partir de reglas (p. ej. «tus cobros se alargan 12 días»).
- **Cómo puntúa**:
  - *Si acierta*: medio. Trayectoria y dos caras bien visibles en la ficha; la generalización solo se defiende si se añade una validación propia (ambigüedad 1).
  - *Si llega a tiempo*: bajo-medio. La estabilidad sale bien con el suavizado; la anticipación medida y el monitor no son el foco.
  - *Si vale algo*: alto. Producto, comprador (Embat, «el más obvio») y explicación son el centro. Encaja con la frase guía y con la nota de que Embat valora «sobre todo el producto».
- **Qué se deja fuera**: vista de cartera, alertas automáticas, backtest de anticipación, consolidación por grupo.
- **Demo/defensa**: abrir una empresa que mejora (tipo 45→65) y otra que cae con buen nivel (tipo 82→68); enseñar por qué se mueve cada una y qué le diría el producto al CFO.
- **Equipo y esfuerzo**: 1 persona de datos (features + score), 1–2 de front/producto, 1 para pitch y narrativa. Esfuerzo medio: el modelo es sencillo y el peso está en la interfaz y el relato. Cabe en el fin de semana con margen para ensayar.
- **Riesgos**: parecer «solo un dashboard» si las acciones son genéricas; floja en el bloque «si llega a tiempo», que oficialmente pesa 1/3 (ambigüedad 4). Si un LLM redacta las recomendaciones a partir de los conceptos bancarios, hay riesgo de instrucciones escondidas y de límites de API en vivo.

### B — Radar de cartera con alertas anticipadas
- **Idea**: vigilar las 1.286 empresas a la vez y avisar cuando una se mueve de verdad, con los meses de adelanto medidos. Es para quien «decide a quién presta o a quién asegura» (financiador o aseguradora de crédito), o para Embat como canal hacia ellos.
- **Qué se construye**: web con ranking de cartera (quién mejora y quién empeora más), feed de alertas con umbral y persistencia (solo salta si el cambio dura más de N meses), ficha explicativa por empresa y una página de validación: backtest sobre empresas apartadas que mide cuántos meses antes salta la alerta respecto a «eventos» definidos con los propios datos (impagos de deuda, caja negativa sostenida, cobros que se alargan; definición propia, inferido, ambigüedad 2).
- **Cómo puntúa**:
  - *Si acierta*: alto. La validación con empresas apartadas da una respuesta propia a la generalización sin leaderboard.
  - *Si llega a tiempo*: alto. Anticipación con cifra, estabilidad (persistencia contra baches) y el bonus del monitor.
  - *Si vale algo*: medio-alto. Comprador claro y explicación por alerta; el producto es más «herramienta de analista» que algo que se venda a las propias empresas.
- **Qué se deja fuera**: experiencia para la propia empresa, recomendaciones de acción, consolidación por grupo.
- **Demo/defensa**: la cartera se reproduce mes a mes; salta una alerta; se abre la empresa y se ve qué la provocó; se cierra con la cifra «detecta el cambio X meses antes de media» y su tasa de falsas alarmas.
- **Equipo y esfuerzo**: 2 de datos (eventos, backtest, umbrales), 1 de front, 1 para el pitch. Esfuerzo alto: definir eventos sin etiqueta y validarlos lleva tiempo; hay que recortar pronto para llegar a la demo.
- **Riesgos**: que el jurado no acepte los «eventos» definidos por el equipo como verdad (ambigüedades 1 y 2); los falsos positivos se ven mucho en la demo; el enunciado dice que la entrega es venderle a «esas mismas empresas», y aquí el comprador es otro (es una elección permitida, pero hay que defenderla).

### C — Tesorería de grupo: salud del holding
- **Idea**: el score consolidado de un grupo y de sus filiales, para ver qué filial tira del grupo hacia arriba o hacia abajo. Es para el tesorero o CFO de grupo; el comprador es Embat, que vende a grupos con varias empresas.
- **Qué se construye**: web con vista de grupo (score consolidado + trayectoria), mapa de filiales con su aportación al cambio del grupo, explicación por filial y alerta cuando una filial diverge del resto. Monedas convertidas a una de referencia (criterio propio, ambigüedad 8).
- **Cómo puntúa**:
  - *Si acierta*: medio. Dos caras y trayectoria a dos niveles; la generalización necesita validación propia, como en A.
  - *Si llega a tiempo*: medio. Una filial que diverge sirve de alerta temprana del grupo, pero la anticipación medida no es el foco.
  - *Si vale algo*: alto si el jurado compra el caso de holding. Producto diferenciado y comprador concreto; la explicación de qué filial movió el grupo es fácil de entender.
- **Qué se deja fuera**: backtest formal de anticipación, recomendaciones de acción detalladas.
- **Demo/defensa**: un grupo cuyo score total parece estable pero esconde una filial que se hunde y otra que crece; se ve cómo lo detecta y lo explica.
- **Equipo y esfuerzo**: 1–2 de datos (consolidación, monedas, evitar señales duplicadas entre filiales), 1 de front, 1 para el pitch. Esfuerzo medio-alto por la consolidación.
- **Riesgos**: depende de la ambigüedad 3 (¿score por empresa o por grupo?); la mediana es de 2 empresas por grupo, así que el caso de holding grande es minoritario; si se mezclan los niveles se duplican o se diluyen señales; el tratamiento de monedas puede no ser aceptado.

---

## Comparativa

| Criterio (peso según el análisis) | A — Copiloto CFO | B — Radar de cartera | C — Tesorería de grupo |
|---|---|---|---|
| **Si acierta (1/3)**: generalización | bajo-medio | alto | bajo-medio |
| Trayectoria | alto | medio-alto | alto |
| Las dos caras | alto | medio-alto | alto |
| **Si llega a tiempo (1/3)**: anticipación medida | bajo | alto | medio |
| Estabilidad (bache frente a caída) | medio | alto | medio |
| Monitor (bonus) | bajo | alto | medio |
| **Si vale algo (1/3)** (posiblemente más, inferido): producto | alto | medio | alto |
| Comprador | alto (Embat) | medio-alto (financiador/aseguradora) | alto (Embat → grupos) |
| Explicación | alto | medio-alto | alto |
| Artesanía de la demo | alto | medio (más piezas que pueden fallar) | medio |
| Esfuerzo / riesgo de no llegar | bajo | alto | medio |

---

- Si priorizáis el producto y lo que Embat dice valorar «sobre todo» → **A**.
- Si priorizáis los tres bloques con el mismo peso del enunciado y el bonus del monitor → **B**.
- Si queréis diferenciaros con un caso que pocos equipos tocarán y la organización confirma que el score puede ser por grupo → **C**.
