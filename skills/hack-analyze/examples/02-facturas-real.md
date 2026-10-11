Fuente: evals/retos/02-facturas-real.md

### Reto en una frase
**Reto:** 500 Sombras de Alberto · Maisa · HackSpain 2026, ETSIT UPM (Madrid), 18–20 de septiembre de 2026

- Alberto, que gestiona pagos, tiene 500 facturas en PDF (algunas escaneadas), un Excel de proveedores, pedidos y normas de pago, y un ERP local de 2009. Para cada factura hay que decidir «PAGAR, NO_PAGAR o ESCALAR».
- El objetivo: «Una solución para que Alberto pueda confiaros una operación real». Cada decisión debe poder rastrearse: «Documento → decisión → evidencia».
- El formato es libre: «Backend, herramienta para agentes, CLI, aplicación web u otra propuesta». Hay que defender por qué se elige.

### Qué hay que entregar
- Un **repositorio público de GitHub, separado de la solución**, cuya raíz contenga «exactamente los dos JSONL y albertitos_plan.pdf». También hay que compartir el **teamId** y la URL.
  - `outcomes.jsonl`: resultados del lote inicial, un objeto JSON por línea.
  - `outcomes_lote2.jsonl`: resultados del lote del sábado, «con un registro único por archivo».
  - `albertitos_plan.pdf`: «La única documentación requerida». Debe tener dos secciones: **Arquitectura** (componentes, flujo de datos y estado, reparto entre agentes, modelos y personas, trazabilidad y recuperación de fallos) y **ADRs / trade-offs**, con 2 a 5 decisiones (contexto, alternativas, decisión, consecuencias y evidencia).
- Contrato JSONL: `{"file_id":"factura_123.pdf","result":"PAGAR"}`. `file_id` es «el nombre exacto del PDF». Los campos de traza son opcionales.
- **Prohibido subir** «vuestra solución, código, credenciales ni una aplicación ejecutable».
- **Fecha límite:** «DOM 20 · 11:00, hora de Madrid». La organización clona el repo y registra el commit a esa hora.
- **Defensa:** 10 minutos ante un único tribunal (hora «Por confirmar»), repartidos así: demo y contexto 2 min · arquitectura y ADRs 2 min · trazabilidad, escala y coste 4 min · resiliencia y preguntas 2 min.

### Cómo se evalúa
- **Validación funcional: APTO / NO APTO.** Exige «Un registro único por archivo · ambos lotes · resultado aceptado» y se compara con una referencia privada. Solo se miran `file_id` y `result`. «No suma puntos, no genera un ranking ni desempata». Un equipo NO APTO puede defender y recibir feedback, pero no puede «optar al premio».
- **Rúbrica del tribunal (100 + 10):**
  - Producto, arquitectura y ADRs: **35**. Se basa en el PDF.
  - Escalabilidad y coste: **25**. Capacidad, hardware, límites, «fórmula de coste» y plan para más volumen y nuevos tipos de archivo.
  - Trazabilidad y observabilidad: **20**. «Seguid una decisión real» y mostrad estado, evidencia, versiones, latencia, errores, reintentos y trabajo pendiente.
  - Resiliencia y recuperación: **10**. Conservar el estado, evitar duplicados, degradar el servicio y recuperar el trabajo «ante fallos del proveedor de LLM».
  - Calidad de ejecución: **10**. «clara, proporcionada y agradable de operar».
  - Bonus: **+10 máx.** Tiene que ser una mejora original que se implemente y se enseñe en la defensa; no valen «propuestas, maquetas, cambios cosméticos ni partes necesarias del flujo principal». Tampoco cuenta el lote del sábado.
- **Desempates:** primero escalabilidad y coste, luego resiliencia, luego el bonus y por último la «decisión motivada del tribunal».
- Lote 2: «No se puntúa un conteo de aciertos: se evalúan arquitectura, observabilidad y recuperación».
- «El tamaño de la aplicación no puntúa».

### Restricciones
- **Tiempo:** de VIE 18 a las 19:00 hasta DOM 20 a las 11:00 (unas 40 h). Todas las horas son de Madrid.
- **Equipo:** 2 a 5 personas, como mucho 15 equipos.
- **Stack:** no se exige ninguno, ni tampoco una interfaz o un formato de traza concretos.
- **Datos:** «Todos los datos son sintéticos». Hay que usar el ERP local («caja-de-alberto»), que se arranca con `make erp` y escucha en `http://127.0.0.1:8009`. Tiene sesiones, reintentos y «latencia artificial»; `make erp-fast` la elimina «para tests locales». La referencia es `MANUAL_ERP_2009.md`.
- **Sábado 18:00:** «+40 FACTURAS · ERP ACTUALIZADO» y «una regla nueva». Hay que integrar el cambio, «conservad el trabajo y explicad qué decisiones debéis reprocesar».
- **Domingo:** Alberto «podrá cambiar un dato de la Caja para comprobar la demo».
- La organización no ejecutará vuestro código; solo pasa su verificador sobre los JSONL.

### Recursos disponibles
- Repo de participantes: `git clone https://github.com/ikurotime/500-sombras-de-alberto.git`. Contiene un README, la Caja de Alberto y `MANUAL_ERP_2009.md`.
- Materiales del lote inicial: se comparten el viernes a las 19:00 en el canal del track. El sábado a las 18:00 sale `lote-2-sorpresa-v3.2.zip`, cuyos hashes hay que comprobar con los publicados en el canal, con `erp_export_lote2`, `pedidos_nuevos.csv`, `proveedores_nuevos.csv` y 40 facturas.
- Mentores de Maisa en el espacio del track: «consulta de diseño o un simulacro breve de defensa».
- Créditos de API o LLM: No especificado.

### Ambigüedades — preguntar a la organización
1. **¿Qué distingue ESCALAR de NO_PAGAR?** Las normas de pago vienen en el Excel, pero si quedan casos grises cambia todo el motor de decisión. ¿El ERP es la fuente de verdad si contradice el Excel?
2. **¿El JSONL del lote 2 se valida contra la regla nueva y el ERP actualizado?** ¿Hay que reprocesar también el lote 1 con la regla nueva, o `outcomes.jsonl` se queda con las reglas originales?
3. **¿Qué «dato de la Caja» puede cambiar el domingo, y cuándo?** Si cae después del cierre de las 11:00, ¿afecta solo a la demo o también a los JSONL entregados?
4. **¿Qué pasa con archivos ilegibles o corruptos?** (el «café» del lote sorpresa). ¿Llevan registro con resultado (¿ESCALAR?) o se excluyen? La validación exige un registro «por cada archivo».
5. **¿Cuántos intentos de validación hay?** ¿Se puede comprobar si se es APTO antes del cierre, o solo se sabe después?
6. **¿El LLM es obligatorio o esperado?** La rúbrica habla de «fallos del proveedor de LLM» y el formato es libre; ¿penaliza resolverlo sin LLM?
7. **¿Hora de la defensa?** «Por confirmar».
8. **Nombres de carpeta:** el enunciado dice `lote_2_sorpresa` y también `lote-2-sorpresa-v3.2.zip`. ¿Es la misma entrega o hubo versiones previas?

### Riesgos y trampas
- **El tribunal valida todo o nada.** Un solo `file_id` mal escrito, duplicado u omitido, o un resultado erróneo en cualquiera de los dos lotes, puede dejar al equipo sin premio, aunque la defensa sea excelente.
- **Repo de entrega mal montado:** la raíz debe tener «exactamente» tres ficheros, y está prohibido subir código o credenciales. Es fácil que se cuele el `.env` o la carpeta de la solución.
- **El commit cuenta a las 11:00 del domingo.** El lote 2 llega el sábado a las 18:00: quedan unas 17 h, noche incluida, para integrarlo.
- **El PDF vale 35 puntos** y se suele dejar para el final. Además, «El tribunal podrá preguntar por cualquier decisión» registrada en él.
- **Medir frente a estimar:** se pide «Separad mediciones de estimaciones». Las cifras de rendimiento sacadas con `make erp-fast` no reflejan la latencia real del ERP (inferido).
- **Facturas escaneadas:** parte de las 500 son imágenes, no texto (inferido: requieren OCR o visión, con más coste y más errores).
- **ERP legado con sesiones, reintentos y latencia:** un procesamiento en paralelo ingenuo puede chocar con las sesiones o las caídas (inferido, a confirmar en `MANUAL_ERP_2009.md`).
- **Cambio de datos en directo el domingo:** si la solución no puede reprocesar solo lo afectado, la demo puede fallar delante del tribunal (inferido).
- **Exceso de alcance:** «El tamaño de la aplicación no puntúa». Una web vistosa no aporta puntos si falta trazabilidad o coste.
- (riesgo típico) **Instrucciones escondidas en documentos:** si se usa un LLM para leer las facturas PDF, alguna puede contener texto que parezca una orden («PAGAR esta factura»…) y alterar la decisión.
- (riesgo típico) **Herramientas que no funcionan en todos los sistemas:** el ERP se arranca con `make help`, `make erp`, `make erp-status`… y `make` no viene de serie en Windows.
- (riesgo típico) **Codificación y tildes:** los datos están en español (Excel y CSVs de proveedores, nombres de empresa, importes con €) (inferido). Los CSV pueden romperse con codificaciones distintas de UTF-8, sobre todo en Windows, y un `file_id` mal codificado no valida.
- (riesgo típico) **Zonas horarias y fechas:** hay plazos con hora de Madrid y las facturas y normas de pago probablemente tienen fechas de vencimiento (inferido). Los formatos dd/mm y mm/dd pueden confundirse.
- (riesgo típico) **Límites de API:** si se usa un LLM, la rúbrica pide demostrar «un timeout, rate limit, respuesta inválida o caída del proveedor». Procesar 540 PDFs (algunos escaneados) con un proveedor externo puede topar con cuotas o latencia justo antes del cierre o durante la demo.

### Qué distinguiría a un proyecto ganador
- **La parte operativa pesa más que la funcional:** escalabilidad y coste (25) + trazabilidad (20) + resiliencia (10) suman 55 puntos, y escalabilidad es el **primer desempate**. Lo que más se repite en el enunciado es «fórmula de coste», capacidad, hardware y límites.
- **Poder seguir una decisión real** de principio a fin: input, estado, evidencia, regla o modelo, resultado. Aparece en la rúbrica, en la defensa y en «Nada ocurre sin dejar rastro».
- **Criterio de ingeniería defendible:** ADRs con alternativas y trade-offs, y un formato justificado para el trabajo de Alberto, no por tamaño.
- **Recuperación visible:** demostrar en vivo un fallo del proveedor, sin duplicados y conservando el estado.
- **Absorber bien el cambio del sábado y del domingo,** explicando «qué decisiones debéis reprocesar» y «cuáles son los límites del sistema».
- **Un bonus implementado** que responda a una necesidad concreta de Alberto (no una maqueta).
