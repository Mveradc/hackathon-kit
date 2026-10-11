# Enfoques — 500 Sombras de Alberto

Sin contexto de equipo: cada enfoque indica qué perfil necesita. Los tres cumplen el contrato JSONL, el repo de entrega con «exactamente» tres ficheros y el PDF con Arquitectura + 2–5 ADRs.

### A — Pipeline determinista, LLM solo para leer
- **Idea**: una cadena por lotes, barata y reproducible, en la que el LLM solo extrae campos de los PDF y un motor de reglas explícito decide. Pensado para quien opera el sistema y para defender coste y escala.
- **Qué se construye**: CLI por etapas idempotentes (ingesta → extracción texto/OCR → extracción estructurada → consulta ERP → reglas → JSONL). Almacén de estado local con una fila por factura y etapa, caché por hash de documento y versión de reglas. Las reglas del Excel se escriben como código versionado. Un cliente del ERP con sesión única, reintentos y límite de concurrencia.
- **Cómo puntúa**:
  - Producto/arquitectura/ADRs (35): fuerte en ADRs claros («reglas en código vs. LLM decide», «caché por hash», «extracción por texto antes que visión»). Más flojo en «producto para Alberto» porque una CLI se defiende peor como herramienta de confianza.
  - Escalabilidad y coste (25): **fuerte**. El coste es casi lineal y fácil de convertir en fórmula (n.º de páginas escaneadas × coste de extracción + llamadas al ERP × latencia medida). Se puede medir de verdad con el ERP lento y separarlo de lo estimado.
  - Trazabilidad (20): medio-alto. Cada decisión apunta a qué regla se disparó, con qué campos y qué respuesta del ERP. Se ve en logs y en un comando `explain <file_id>`, no en una interfaz.
  - Resiliencia (10): fuerte. Etapas idempotentes, reanudación desde el estado y sin duplicados por diseño. Si cae el LLM, la extracción se degrada a solo texto/reglas o se marca como pendiente.
  - Ejecución (10): medio. Es clara pero menos «agradable de operar» para alguien no técnico.
- **Qué se deja fuera**: interfaz gráfica, agentes autónomos, chat con Alberto.
- **Demo/defensa**: lanzar el lote, cortar el proveedor LLM a mitad y reanudar sin duplicados. Ejecutar `explain` sobre una factura real. Cambiar el dato de la Caja → reprocesar solo las facturas afectadas (por dependencia ERP→factura). Mostrar la fórmula de coste con cifras medidas.
- **Equipo y esfuerzo**: 2–3 personas con perfil backend/datos y una que lleve el PDF desde el viernes. Es el más acotado: debería quedar núcleo funcional el sábado por la mañana y margen para el lote 2.
- **Riesgos**: si las normas tienen casos grises, codificar reglas a mano es frágil (ambigüedad 1). La regla nueva del sábado obliga a tocar código (ambigüedad 2). Le afecta poco que el LLM no sea obligatorio (6), pero si se esperaba un LLM «protagonista», el ADR tiene que justificarlo.
- **Bonus posible**: detección de instrucciones inyectadas en PDF o de facturas duplicadas/fraude entre proveedores, implementada y mostrada.

### B — Agentes con herramientas y supervisión humana
- **Idea**: un agente por factura razona con herramientas (leer PDF, consultar ERP, consultar normas) y produce decisión + evidencia citada. ESCALAR va a una cola de revisión humana. Pensado para casos grises y para un Alberto que delega con supervisión.
- **Qué se construye**: un orquestador que reparte facturas a agentes con un conjunto cerrado de herramientas, un validador de salida (esquema + reglas duras que el agente no puede saltarse), un registro de cada paso del agente (llamadas, prompts, versión de modelo, tokens) y una cola de excepciones. Formato: backend + herramienta para agentes, con CLI o una vista mínima para revisar.
- **Cómo puntúa**:
  - Producto/arquitectura/ADRs (35): fuerte en el reparto «agentes, modelos y personas», que el enunciado pide de forma explícita. ADRs interesantes (autonomía vs. reglas duras, modelo grande vs. pequeño por paso).
  - Escalabilidad y coste (25): **más débil**. El coste por factura es variable (n.º de pasos × tokens), y cuesta dar una fórmula estable y defender 10× de volumen. Hay que medir mucho para no quedarse en estimaciones.
  - Trazabilidad (20): alto si se registra cada paso, porque la cadena de razonamiento y las citas son evidencia. Riesgo: trazas largas y difíciles de seguir en 4 minutos.
  - Resiliencia (10): medio. Hay muchos puntos de fallo del proveedor LLM. Hace falta reintento por paso, presupuesto por factura y degradar a ESCALAR. Se puede demostrar, pero exige trabajo.
  - Ejecución (10): medio-alto si la cola de revisión es cómoda.
- **Qué se deja fuera**: optimización de coste fina, interfaz completa, procesamiento masivo sin LLM.
- **Demo/defensa**: seguir una factura gris paso a paso, con herramientas llamadas, evidencia y por qué escala. Provocar timeout o respuesta inválida del modelo y enseñar el reintento o la degradación. Enseñar que una regla dura bloquea al agente cuando intenta pagar algo prohibido.
- **Equipo y esfuerzo**: 3–5 personas, con al menos una con experiencia en LLM/agentes y evaluación. Es el más exigente: hay que iterar prompts contra la validación APTO/NO APTO, que no perdona errores.
- **Riesgos**: no determinismo → resultados que cambian entre ejecuciones, y un solo error es NO APTO. Coste y cuotas del proveedor con 540 PDF justo antes del cierre (créditos: no especificado). Inyección de instrucciones en facturas. Muy expuesto a las ambigüedades 1 (ESCALAR vs. NO_PAGAR) y 6.
- **Bonus posible**: auto-evaluación con un conjunto de facturas etiquetadas por el equipo que detecta regresiones al cambiar de modelo o de prompt.

### C — Consola de operación con reprocesado selectivo
- **Idea**: un servicio con estado orientado a eventos y una consola web donde Alberto ve cada factura, su estado, su evidencia y qué hay pendiente, y puede reprocesar lo que cambia. Se apuesta por «confiaros una operación real» y por los cambios del sábado y del domingo.
- **Qué se construye**: backend con cola de trabajos y registro de eventos (cada cambio de estado es un evento con versión de reglas, de datos ERP y de modelo), un grafo de dependencias factura ↔ proveedor/pedido del ERP para invalidar solo lo afectado y una consola web con métricas (latencia, errores, reintentos, cola pendiente, coste acumulado). La decisión puede ser por reglas con extracción asistida por LLM, como en A, pero no es donde se apuesta. Demo local; la organización no ejecuta código y no se exige despliegue.
- **Cómo puntúa**:
  - Producto/arquitectura/ADRs (35): fuerte en producto, porque es claramente una herramienta para Alberto. ADRs sobre event sourcing frente a estado mutable y sobre la invalidación por dependencias.
  - Escalabilidad y coste (25): medio. La arquitectura de colas escala bien sobre el papel, pero hay más piezas que dimensionar y justificar. La fórmula de coste es viable si la decisión es por reglas.
  - Trazabilidad (20): **fuerte**. «Seguid una decisión real» se enseña visualmente, con historial de versiones de cada decisión.
  - Resiliencia (10): fuerte. El registro de eventos conserva el estado, los trabajos son idempotentes y hay cola de reintentos visible.
  - Ejecución (10): alto si la consola es sobria. Cuidado, porque «El tamaño de la aplicación no puntúa».
- **Qué se deja fuera**: agentes autónomos, razonamiento sofisticado en casos grises, pulido visual.
- **Demo/defensa**: Alberto cambia un dato en la Caja → la consola marca las N facturas afectadas → se reprocesan → se ve el diff de decisiones con versión antigua y nueva. Caída del LLM con la cola de pendientes creciendo y vaciándose al volver.
- **Equipo y esfuerzo**: 3–4 personas: backend, alguien de frontend y una persona para el PDF y las métricas. Esfuerzo medio-alto: la consola compite en tiempo con lo que da APTO. El motor de decisión tiene que estar listo antes de construir la interfaz.
- **Riesgos**: dispersión de alcance, porque se puede acabar con una consola bonita y un JSONL con errores (NO APTO). Encaja muy bien con la ambigüedad 3 (cambio del domingo) y con la 2 (reprocesar el lote 1 con la regla nueva), pero si la respuesta a ambas es «no afecta», pierde parte de su ventaja.
- **Bonus posible**: simulador «¿qué pasaría si…?» que muestra qué decisiones cambiarían ante una regla o un dato ERP hipotético antes de aplicarlo.

## Comparativa

| Criterio | A — Pipeline determinista | B — Agentes + supervisión | C — Consola + reprocesado |
|---|---|---|---|
| Validación APTO (requisito) | alto | medio | alto |
| Producto, arquitectura y ADRs (35) | medio | alto | alto |
| Escalabilidad y coste (25) — 1.er desempate | alto | bajo | medio |
| Trazabilidad y observabilidad (20) | medio | alto | alto |
| Resiliencia y recuperación (10) — 2.º desempate | alto | medio | alto |
| Calidad de ejecución (10) | medio | medio | alto |
| Encaje con cambios sáb./dom. | medio | medio | alto |
| Riesgo de alcance en 40 h | bajo | alto | medio |

## Orientación

- Si priorizáis asegurar el APTO y ganar en el primer desempate (escala y coste) → **A**.
- Si priorizáis casos grises y el reparto agentes/modelos/personas, y tenéis experiencia con LLM → **B**.
- Si priorizáis enseñar trazabilidad y absorber en vivo el cambio del domingo → **C** (se puede montar sobre el motor de A).
