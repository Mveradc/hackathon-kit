# Decisión — X Ray · Embat (HackSpain 2026)

Fecha: 2026-10-10

## Enfoque elegido

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

## Matices del equipo

Ninguno

## Ambigüedades abiertas que afectan a esta elección

1. **¿Cómo se valorará «generalización» y «anticipación medida» sin test oculto ni scoring?** ¿Hay que traer una validación propia (por ejemplo, empresas apartadas) o lo juzga el jurado en la demo? — A es floja aquí; si hace falta validación propia, hay que añadirla.
2. **¿Existe alguna etiqueta o «verdad» de salud financiera en los datos?** Sin etiqueta, ¿qué cuenta como acertar?
3. **¿El score es por empresa (1.286) o por grupo (250)?** A asume una ficha por empresa.
4. **¿Sigue valiendo el «mismo peso» de los tres bloques** o, como dijo Embat según el equipo, prima el producto? — A apuesta por que prime el producto.
5. **¿Cuándo y cómo se entrega?** Hora límite, URL de la demo, repositorio, ¿hace falta un deploy público?
6. **¿Cuánto dura exactamente el pitch?** ¿Hay turno de preguntas?
7. **¿Escala de 0 a 100?** A la usa en la ficha (inferido).
8. **¿Cómo se tratan las varias monedas?** Afecta a las cifras de caja, cobros y deuda que muestra la ficha.
