# Enfoques — X Ray · Embat

> Base: `.hackathon/analisis.md`. La transcripción no es oficial y la nota del equipo anula el test oculto: ningún enfoque depende de un leaderboard.
> Los tres comparten un núcleo mínimo, que es obligatorio: score mensual por empresa (0–100, ambigüedad 7), con tendencia y explicación de qué lo movió. Lo que cambia es **a quién sirve el producto y dónde se apuesta**.
> «Generalización» y «anticipación medida» no tienen métrica oficial (ambigüedad 1). En los tres, la forma de defenderlas es traer una validación propia: apartar empresas que el modelo no ve y contar cuántos meses antes salta la señal respecto al cambio visible en caja o en impagos (inferido).

---

### A — Radar de cartera para Embat
- **Idea**: un monitor que vigila las 1.286 empresas y avisa a Embat de cuáles se mueven de verdad, hacia arriba o hacia abajo, para que actúe antes que nadie. Es para el equipo de cuentas/riesgo de Embat.
- **Qué se construye**: web navegable con (1) vista de cartera ordenada por cambio de tendencia, no por nivel; (2) cola de alertas «mejora» / «deterioro» con filtro bache frente a cambio sostenido; (3) ficha de empresa con la curva de 24 meses y los 3–4 factores que la movieron; (4) panel de validación: empresas apartadas y meses de adelanto medidos. La demo tiene que ser accesible por URL o, como mínimo, abrirse fuera de un notebook (ambigüedad 5).
- **Cómo puntúa**:
  - *Si acierta*: trayectoria y dos caras están en el centro del producto (alerta de mejora y de deterioro). Generalización se defiende con el panel de validación.
  - *Si llega a tiempo*: es el enfoque más fuerte aquí. El monitor (bonus) es el propio producto, y la anticipación medida se enseña en pantalla. La estabilidad se trabaja con la regla de «cambio sostenido» de las alertas.
  - *Si vale algo*: comprador = Embat, «el comprador más obvio» según el enunciado. Explicación en cada alerta. Punto débil: «venderlo a esas mismas empresas» queda indirecto (Embat lo usa para venderles algo), hay que contarlo bien en el pitch.
- **Qué se deja fuera**: la vista para la propia empresa, cualquier recomendación de acciones, la agregación por grupo (se muestra el grupo, no se puntúa).
- **Qué se enseña en la demo**: «esta semana se han movido 12 empresas»; abrir una que mejora y otra que empeora; ver qué factores lo explican; enseñar que la alerta saltó N meses antes de que la caja lo hiciera evidente.
- **Equipo y esfuerzo**: una persona de datos (features y score), una de backend/datos para alertas y validación, una de frontend para cartera y ficha, y quien prepare el pitch. Esfuerzo medio: el modelo puede ser sencillo; el trabajo está en el filtro de alertas y en medir la anticipación.
- **Encaje con vuestro equipo**:
  - Persona A: score, filtro de alertas y anticipación (series temporales, su terreno).
  - Persona B: cartera y ficha; Persona C: caso de negocio con Embat como comprador.
  - Hueco: backend de alertas y panel de validación; nadie lo tiene y C prefiere no hacerlo, así que carga a A.
  - Defensa: C puede sostener el comprador; B, la demo.
- **Riesgos**: muchas alertas falsas si el filtro bache/deterioro falla; anticipación difícil de medir sin etiqueta (ambigüedad 2); confusión empresa/grupo en holdings (ambigüedad 3); si la generalización la juzga el jurado sin datos propios, el panel de validación debe ser muy claro (ambigüedad 1).

---

### B — Copiloto financiero para la propia empresa
- **Idea**: cada empresa ve su salud financiera, hacia dónde va y qué está empujando el número, para actuar antes de que sea evidente. Es para el CFO o el tesorero de la empresa cliente; Embat lo vende como módulo de pago.
- **Qué se construye**: web con login simulado por empresa: (1) score actual y trayectoria con proyección corta; (2) «qué lo movió este mes» en lenguaje claro (cobros que se alargan, deuda que vence, concentración de clientes…); (3) comparación con empresas parecidas (sector/tamaño/país); (4) 2–3 palancas sugeridas a partir de reglas sobre los factores. Si se usa un LLM para redactar explicaciones, solo sobre datos estructurados, nunca sobre el texto libre de `transactions.csv` (riesgo de instrucciones escondidas). Demo navegable, idealmente por URL (ambigüedad 5).
- **Cómo puntúa**:
  - *Si acierta*: trayectoria y dos caras visibles (la empresa ve si mejora). Generalización igual que el resto, con validación propia.
  - *Si llega a tiempo*: medio. La anticipación se puede enseñar en la ficha («este factor empezó a moverse hace 4 meses»), pero el monitor (bonus) no es el foco.
  - *Si vale algo*: el más fuerte en «producto que se le pueda vender a esas mismas empresas», que es literal del enunciado. La explicación es el centro. El comprador es doble (la empresa paga, Embat lo distribuye), y eso hay que contarlo en una frase.
- **Qué se deja fuera**: vista de cartera, sistema de alertas en cola, agregación por grupo.
- **Qué se enseña en la demo**: entrar como una empresa que va mal pero aún no lo parece; ver por qué; entrar como otra que se recupera y ver que el score lo reconoce; enseñar la palanca sugerida.
- **Equipo y esfuerzo**: una persona de datos para score y factores, una de frontend/producto con buen ojo para UX y textos, una que lleve backend ligero y la comparación entre pares, y quien defienda el pitch. Esfuerzo medio: la carga está en la explicación y en la UX, no en el modelo.
- **Encaje con vuestro equipo**:
  - Persona A: score y factores; Persona B: UX, textos y producto, su punto fuerte.
  - Persona C: palancas sugeridas y comparación entre pares desde finanzas.
  - Hueco: el backend ligero; nadie lo tiene entre sus puntos fuertes.
  - Defensa: B y C presentan y ambos encajan con un producto para el CFO.
- **Riesgos**: que la explicación sea genérica y no convenza («nadie compra una caja negra»); recomendaciones que suenen a consejo financiero sin base; si se usa LLM en vivo, cuotas/latencia ante el jurado (riesgo típico); comparar empresas de varias monedas (ambigüedad 8).

---

### C — Pasaporte financiero para conseguir financiación
- **Idea**: la empresa obtiene un informe verificable de su salud y trayectoria que comparte con un banco, aseguradora o proveedor para conseguir mejores condiciones. El usuario es la empresa; quien lo lee es un tercero que decide si presta o asegura.
- **Qué se construye**: (1) generador de informe por empresa: score, curva de 24 meses, factores, estabilidad (bache frente a tendencia); (2) enlace o documento compartible con vista de lectura para el financiador; (3) API sencilla que devuelve score + trayectoria + explicación para una empresa; (4) apartado de validación con empresas apartadas. Demo navegable y enlace compartible: si se usa como argumento, necesita URL pública (ambigüedad 5).
- **Cómo puntúa**:
  - *Si acierta*: la estabilidad y la trayectoria son el argumento de venta («no te juzgo por un mes malo»), y las dos caras le dan valor a la empresa que mejora.
  - *Si llega a tiempo*: medio-bajo. La anticipación se puede medir y mostrar en el informe, pero no hay monitor (bonus perdido).
  - *Si vale algo*: comprador claro (la empresa paga para financiarse mejor) y alineado con «nadie compra una caja negra para decidir a quién presta o a quién asegura», que es literal del enunciado. Exige explicar bien por qué un financiador confiaría en el informe.
- **Qué se deja fuera**: alertas, vista de cartera, recomendaciones de acciones.
- **Qué se enseña en la demo**: una empresa que tuvo un bache y se recuperó genera su pasaporte; el financiador lo abre y ve que es un bache, no un deterioro; la misma pantalla para una empresa en caída muestra la diferencia.
- **Equipo y esfuerzo**: una persona de datos para score y estabilidad, una de backend para API e informe compartible, una de frontend para el informe, y quien defienda el modelo de negocio. Esfuerzo medio-alto: el informe tiene que parecer creíble y la validación tiene que sostenerlo.
- **Encaje con vuestro equipo**:
  - Persona A: score y estabilidad; Persona B: informe y vista del financiador.
  - Hueco grande: API, enlace compartible y despliegue público son backend; nadie lo tiene y C prefiere no hacerlo.
  - Defensa: C, con perfil de finanzas, puede defender bien el caso de financiación.
- **Riesgos**: que el jurado no vea el comprador tan claro como con Embat; credibilidad del informe sin una «verdad» con la que validarlo (ambigüedad 2); compartir por enlace añade despliegue público (ambigüedad 5); multimoneda en el informe (ambigüedad 8).

---

## Tabla comparativa

| Criterio | A — Radar de cartera | B — Copiloto empresa | C — Pasaporte financiero |
|---|---|---|---|
| Generalización | medio | medio | medio |
| Trayectoria | alto | alto | alto |
| Dos caras | alto | alto | medio |
| Anticipación medida | alto | medio | medio |
| Estabilidad (bache vs. deterioro) | alto | medio | alto |
| Monitor (bonus) | alto | bajo | bajo |
| Producto | medio | alto | alto |
| Comprador | alto | medio | medio |
| Explicación | medio | alto | alto |
| Artesanía (demo que se abre) | medio | alto | medio |
| Encaje con el equipo | medio | alto | bajo |

Si priorizáis el bloque «si llega a tiempo» y el bonus del monitor → A.
Si priorizáis el producto que se vende a las propias empresas (lo que, según la nota, Embat valora «sobre todo») → B.
Si queréis apostar por la estabilidad y un caso de uso de financiación con un comprador diferenciador → C.
Si no queréis depender de que alguien cubra backend sin tenerlo entre sus puntos fuertes → B, que es el que menos backend necesita.
