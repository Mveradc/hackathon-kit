# Enfoques — 500 Sombras de Alberto

Basado en `.hackathon/analisis.md`. Los tres cumplen lo obligatorio: dos JSONL con un registro único por `file_id`, `albertitos_plan.pdf` con Arquitectura y 2–5 ADRs, repo de entrega separado con exactamente esos tres ficheros, uso del ERP local y absorción del lote del sábado. Ninguno necesita despliegue: la organización no ejecuta el código y la demo se hace en vivo en la defensa.

---

### A — Pipeline determinista con libro de estado
- **Idea**: un procesador por lotes donde las normas de pago son reglas explícitas y el LLM solo extrae datos de los PDF escaneados. Para Alberto como operador que lanza lotes y audita resultados.
- **Qué se construye**: CLI con etapas separadas (ingesta → extracción de texto/visión → cruce con Excel y ERP → motor de reglas → decisión). Un libro de estado persistente por factura (etapa, evidencia, versión de regla, versión de datos del ERP, intentos). Caché de extracciones para no volver a pagar el LLM. Comando de reproceso que, ante una regla nueva o un dato del ERP cambiado, recalcula solo las facturas afectadas. Exportador de JSONL e informe de trazas.
- **Cómo puntúa**:
  - Producto/arquitectura/ADRs (35): alto. ADRs naturales y fáciles de defender: «reglas en código vs. LLM decide», «extracción cacheada», «estado en libro vs. reprocesar todo».
  - Escalabilidad y coste (25): alto. La fórmula de coste es simple y medible (coste LLM ≈ nº escaneados × coste por extracción; el resto es casi gratis). Primer desempate.
  - Trazabilidad (20): alto. Cada decisión apunta a la regla que la disparó y al dato concreto de Excel/ERP. «Seguid una decisión real» sale directo del libro.
  - Resiliencia (10): alto. El estado por etapa permite reanudar sin duplicados; si el LLM cae, solo se bloquean los escaneados y el resto avanza (degradación).
  - Calidad de ejecución (10): medio. Una CLI clara es «proporcionada», pero menos «agradable» de enseñar.
  - Bonus (+10): medio. Espacio para algo original (p. ej. detectar facturas duplicadas o importes incoherentes entre proveedores), siempre que no sea parte del flujo principal.
- **Qué se deja fuera**: interfaz gráfica, agentes autónomos, razonamiento del LLM sobre las normas.
- **Qué se enseña en la demo/defensa**: lanzar un lote, seguir una factura de PDF a decisión con su regla y evidencia, matar el proveedor de LLM a mitad y reanudar sin duplicados, y que Alberto cambie un dato de la Caja y ver qué se reprocesa.
- **Equipo y esfuerzo**: 2–3 perfiles de backend/datos y uno que lleve el PDF y la defensa. Esfuerzo medio: la mayor parte del tiempo va a traducir las normas del Excel a reglas y a pelear con el ERP (sesiones, latencia). Cabe en las ~40 h con margen para el lote 2.
- **Encaje con vuestro equipo**:
  - Persona A: ERP, estado y reproceso; Persona B: extracción de escaneados; Persona C: pruebas de reglas y validación de JSONL.
  - Persona E puede traducir las normas de pago a reglas con criterio financiero, sin programar.
  - Persona D llega el sábado a las 10:00: el diseño inicial y los primeros ADRs arrancan sin ella.
  - Defensa: Persona A, D o E la pueden presentar.
- **Riesgos**:
  - Si las normas tienen casos grises que no se pueden expresar como reglas, el motor falla y peligra el APTO (ambigüedad 1: ESCALAR vs. NO_PAGAR, ERP vs. Excel).
  - Si la organización espera un LLM en el centro, el enfoque puede parecer poco ambicioso (ambigüedad 6).
  - La regla nueva del sábado hay que programarla a mano con poco tiempo, de noche.

---

### B — Equipo de agentes con herramientas
- **Idea**: varios agentes LLM especializados (lector de documentos, verificador contra ERP/Excel, decisor, auditor) que usan herramientas y se coordinan por una cola. Para un Alberto que quiere que el sistema se adapte a normas y documentos nuevos sin reprogramarlo.
- **Qué se construye**: herramienta para agentes / backend con: herramientas acotadas (consultar ERP, leer Excel, extraer PDF), un orquestador con cola de trabajo y estado por factura, agentes con roles y modelos distintos según dificultad (modelo barato para lo fácil, más caro para casos dudosos), un agente auditor que revisa una muestra o lo marcado como dudoso, y registro de cada llamada (prompt, versión de modelo, latencia, coste, reintentos). Las normas se pasan como contexto versionado.
- **Cómo puntúa**:
  - Producto/arquitectura/ADRs (35): alto. Encaja de lleno con «reparto entre agentes, modelos y personas»; ADRs ricos (enrutado por modelo, auditor, herramientas acotadas).
  - Escalabilidad y coste (25): medio. La fórmula de coste es más compleja (tokens por rol × facturas × reintentos) y el coste real es mayor; se puede defender con enrutado por modelos, pero hay más que medir.
  - Trazabilidad (20): medio-alto. Cada paso queda registrado, pero la «evidencia» de una decisión del LLM es menos firme que una regla explícita.
  - Resiliencia (10): alto si se trabaja: es donde más brillan los fallos del proveedor (timeouts, rate limit, respuesta inválida) y su recuperación, pero también donde más ocurren.
  - Calidad de ejecución (10): medio. Más piezas móviles que operar.
  - Bonus (+10): medio-alto. Un agente que proponga una regla nueva a partir de un cambio de normas, por ejemplo, puede contar si está implementado y se enseña.
- **Qué se deja fuera**: interfaz gráfica completa; motor de reglas cerrado.
- **Qué se enseña en la demo/defensa**: una factura recorriendo los agentes con su traza de llamadas; el auditor discrepando y escalando; un fallo del proveedor provocado y la cola reanudando; la regla nueva del sábado incorporada cambiando el contexto, no el código.
- **Equipo y esfuerzo**: alguien con experiencia en orquestar LLM y agentes, un perfil de backend para herramientas y estado, y uno para PDF/defensa. Esfuerzo alto: ajustar prompts hasta que los dos lotes sean fiables consume mucho tiempo.
- **Encaje con vuestro equipo**:
  - Persona B cubre agentes y extracción; Persona A, herramientas, cola y estado; Persona C, pruebas de fiabilidad y fallos provocados.
  - Hueco: toda la parte LLM depende de una sola persona (B); nadie más la tiene entre sus puntos fuertes.
  - Persona D (desde el sábado 10:00) encaja con los ADRs de reparto entre agentes; Persona E aporta poco a la construcción.
  - Defensa: Persona A o D pueden defender la parte técnica de agentes.
- **Riesgos**:
  - El APTO es todo o nada y los LLM no son deterministas: un solo resultado erróneo deja sin premio. Hay que fijar resultados y validarlos.
  - Instrucciones escondidas en las facturas pueden alterar decisiones (riesgo típico del análisis).
  - Cuotas y latencia con ~540 PDF justo antes del cierre o en la demo; créditos de API «No especificado».
  - Depende de las ambigüedades 1 (casos grises) y 6 (si el LLM se espera o no).

---

### C — Mesa de control para Alberto
- **Idea**: el sistema decide lo claro y Alberto resuelve lo dudoso en una mesa de trabajo con colas, evidencia y panel de operación. Para Alberto como persona que firma los pagos y necesita confiar.
- **Qué se construye**: aplicación web local con: un motor de decisión sencillo (reglas + extracción) que deja en cola de revisión todo lo que no tiene claro; vista por factura con PDF, datos extraídos, cruce con ERP/Excel y motivo; panel de observabilidad (pendiente, errores, reintentos, latencia, coste acumulado, versiones); acciones de reproceso y registro de quién decidió qué (máquina o persona). Los JSONL se exportan desde aquí.
- **Cómo puntúa**:
  - Producto/arquitectura/ADRs (35): medio-alto. Responde directamente a «que Alberto pueda confiaros una operación real» y al reparto con personas; el formato es fácil de justificar.
  - Escalabilidad y coste (25): medio. La fórmula de coste tiene que incluir el tiempo humano en revisión; a más volumen, la cola de revisión es el cuello de botella y hay que explicarlo bien.
  - Trazabilidad (20): alto. El panel es justo lo que pide «mostrad estado, evidencia, versiones, latencia, errores, reintentos y trabajo pendiente».
  - Resiliencia (10): medio. Se puede degradar a «todo a revisión» si cae el LLM, pero hay que construir la recuperación igual que en A.
  - Calidad de ejecución (10): alto. «Agradable de operar» se enseña solo.
  - Bonus (+10): medio. La interfaz en sí no cuenta (cosmético o parte del flujo); el bonus tendría que ser otra cosa.
- **Qué se deja fuera**: agentes autónomos, optimización fina de coste, automatizar los casos dudosos.
- **Qué se enseña en la demo/defensa**: el panel con el lote cargado; abrir una decisión real y ver su evidencia; Alberto cambia un dato de la Caja y la factura vuelve a la cola; fallo del LLM y degradación visible.
- **Equipo y esfuerzo**: perfil de frontend, uno de backend/datos para motor y ERP, y uno para PDF/defensa. Esfuerzo alto: hay que hacer el motor y además la interfaz.
- **Encaje con vuestro equipo**:
  - Hueco: nadie tiene frontend entre sus puntos fuertes; Persona A no quiere diseño visual y Persona B no quiere frontend.
  - Persona A: motor y ERP; Persona B: extracción; Persona C: pruebas y reproceso.
  - Persona E encaja como «Alberto» en la demo y para resolver la cola de revisión con criterio financiero.
  - Defensa: Persona E puede contar muy bien la historia de operación.
- **Riesgos**:
  - Para el APTO, los JSONL no pueden contener decisiones «pendientes de Alberto»: alguien del equipo tiene que resolver la cola antes de las 11:00, y eso hay que explicarlo sin que parezca trampa.
  - «El tamaño de la aplicación no puntúa»: tiempo en interfaz que no se recupera si falla la trazabilidad o el coste.
  - Ambigüedad 1: si ESCALAR es justo «lo que va a Alberto», el enfoque encaja muy bien; si no, la cola y el resultado ESCALAR se confunden. Ambigüedad 3: el cambio del domingo es su mejor momento de demo.

---

### Tabla comparativa

| Criterio | A — Pipeline determinista | B — Equipo de agentes | C — Mesa de control |
|---|---|---|---|
| Validación APTO (riesgo) | riesgo bajo | riesgo alto | riesgo medio |
| Producto, arquitectura y ADRs (35) | alto | alto | medio-alto |
| Escalabilidad y coste (25) | alto | medio | medio |
| Trazabilidad y observabilidad (20) | alto | medio-alto | alto |
| Resiliencia y recuperación (10) | alto | alto | medio |
| Calidad de ejecución (10) | medio | medio | alto |
| Bonus (+10) | medio | medio-alto | medio |
| Esfuerzo | medio | alto | alto |
| Encaje con el equipo | alto | medio | bajo |

- Si priorizáis asegurar el APTO y el primer desempate (escalabilidad y coste) → A.
- Si priorizáis una arquitectura ambiciosa de agentes y modelos, y aceptáis más riesgo en el APTO → B.
- Si priorizáis que Alberto opere y confíe, y la observabilidad visible en la demo → C.
- Si no queréis que toda la parte LLM dependa solo de Persona B → A o C.
