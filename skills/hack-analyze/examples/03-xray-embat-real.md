Fuente: evals/retos/03-xray-embat-real.md

> ⚠️ El fichero es una transcripción hecha por un equipo participante, no el texto oficial. Incluye una **nota del equipo (19 sep)** que anula partes del enunciado y un **«Resumen ejecutivo» escrito por el equipo**, no por la organización. Este análisis usa como base el enunciado y aplica la nota allí donde la cita.

### Reto en una frase
**Reto:** X Ray · Embat · HackSpain 2026, ETSIT UPM (Madrid), 18–20 de septiembre de 2026

- A partir del rastro financiero de 24 meses (banco, facturas, deuda), construir un **score de salud financiera** mensual por empresa y, **encima**, «un producto que se le pueda vender a esas mismas empresas».
- Para quién: el comprador lo elige cada equipo, pero el enunciado insiste en que «la empresa que entrega los datos (Embat) es el comprador más obvio».
- Enfoque: «Esto **no va de predecir quiebras**». Hay que leer el comportamiento «en las dos direcciones» y «antes de que sea evidente».

### Qué hay que entregar
Obligatorio (tabla §5):
- ~~**Predicción sobre el test oculto**~~: «Obligatorio» en el enunciado, pero **quedó sin efecto** según la nota del equipo («Embat confirmó que no tiene script de scoring ni leaderboard»). Es una confirmación verbal que transmite el equipo, no un texto oficial.
- **Señal en las dos direcciones**: «Reconoce la mejora igual que el deterioro».
- **Trayectoria, no foto**: «hacia dónde va la empresa, no solo dónde está el último mes».
- **Explicación**: «por qué saca ese número y qué lo movió».
- **Producto encima del score**: «El score solo no es la entrega».
- **Comprador identificado**: «No hace falta un plan de negocio, hace falta una respuesta».
- **Demo navegable**: «Un notebook que solo corre en el portátil **no cuenta**».

Bonus:
- **Anticipación medida**: «cuántos meses antes detecta el cambio».
- **Monitor que avisa**: «levanta la mano cuando una empresa se mueve de verdad».

Formato y plazo:
- Pitch: «si en cinco minutos no se ve a quién se le vende y por qué, se queda a medias». Que el pitch dure 5 minutos es (inferido): el resumen del equipo lo da por hecho, pero el enunciado no lo dice así.
- Fecha y hora de entrega, repositorio, vídeo o documento: **No especificado**.

### Cómo se evalúa
«Tres bloques con el **mismo peso**: si acierta, si llega a tiempo y si vale algo.»
- **Si acierta (1/3)**: generalización («¿Funciona en las empresas que no ha visto nunca?»), trayectoria, las dos caras.
- **Si llega a tiempo (1/3)**: anticipación («Cuántos meses antes, **medido**»), estabilidad (bache frente a deterioro), monitor («Puntos extra»).
- **Si vale algo (1/3)**: producto, comprador, explicación, artesanía («que la demo se abra y se pruebe»).
- Frase guía: «Un modelo sencillo con un producto claro encima interesa más que uno sofisticado que se queda en el número.»
- Nota del equipo: Embat «valora sobre todo el producto construido encima del score». Choca con el «mismo peso» del enunciado. (inferido) Es probable que en la práctica el bloque «si vale algo» pese más.
- Sin leaderboard, **no se especifica** cómo se medirá ahora la «generalización».
- Composición del jurado: **No especificado**.

### Restricciones
- Tiempo: evento del 18 al 20 de septiembre. Horas de hacking y hora de cierre: **No especificado**.
- Tamaño de equipo: **No especificado**.
- Tecnologías obligatorias o prohibidas: **No especificado**. Solo se exige que la demo sea navegable y no un notebook local.
- Datos: el dataset de Embat, totalmente sintético («Ninguna fila corresponde a una empresa, cuenta o persona real»).
- Licencia y uso de los datos fuera del evento: **No especificado**.
- Propiedad intelectual de lo construido: **No especificado**.

### Recursos disponibles
- **Dataset**: 9 CSV (también en JSON) + `data_dictionary.md`. Ficheros: `groups`, `companies`, `banking_products`, `debt_products`, `debt_schedule_config`, `transactions`, `invoices`, `balances` (foto a 1-sep-2026). La clave común es `company_id`.
- Tamaño: «1.286 empresas sintéticas agrupadas en 250 grupos», de septiembre de 2024 a septiembre de 2026. Los grupos tienen de 1 a 24 empresas (mediana 2).
- Varias monedas y países (campos `país` y `moneda` en `companies.csv`).
- **Equipo de Embat**: «Dos ingenieros rotando en el aula todo el fin de semana y un especialista de datos localizable de noche».
- **Sesión formativa**: sábado por la mañana, media hora sobre «de dónde sale cada fichero y qué significa».
- ~~Test oculto, script de scoring y leaderboard~~: anunciados «desde el viernes», pero según la nota del equipo no existen.

### Ambigüedades — preguntar a la organización
1. **¿Cómo se valorará «generalización» y «anticipación medida» sin test oculto ni scoring?** ¿Hay que traer una validación propia (por ejemplo, empresas apartadas) o lo juzga el jurado en la demo?
2. **¿Existe alguna etiqueta o «verdad» de salud financiera en los datos?** El enunciado habla de un test «sin resultado», lo que implica que hay un resultado en otra parte, pero ningún fichero lo contiene. Sin etiqueta, ¿qué cuenta como acertar?
3. **¿El score es por empresa (1.286) o por grupo (250)?** El enunciado usa «250 empresas» y «1.286 empresas en 250 grupos» como si fueran lo mismo. Además, el ejemplo del §1 pone nombre de grupo/empresa al score.
4. **¿Sigue valiendo el «mismo peso» de los tres bloques** o, como dijo Embat según el equipo, prima el producto?
5. **¿Cuándo y cómo se entrega?** Hora límite, URL de la demo, repositorio, ¿hace falta un deploy público?
6. **¿Cuánto dura exactamente el pitch?** ¿Hay turno de preguntas?
7. **¿Escala de 0 a 100?** Los ejemplos (45→65, 82→68) lo sugieren (inferido), pero no se fija.
8. **¿Cómo se tratan las varias monedas?** ¿Se convierten a una sola? ¿Con qué tipo de cambio?

### Riesgos y trampas
- **Base documental poco fiable**: la anulación del test oculto llega por una nota de otro equipo y el «Resumen ejecutivo» no es oficial (sigue citando el leaderboard como obligatorio, aunque la nota lo anula). Es fácil mezclar texto oficial, nota y resumen.
- **Quedarse en el número**: el enunciado repite que «el score solo no es la entrega» y que el producto y el comprador pesan tanto como el modelo.
- **Demo que no se abre**: un notebook local «no cuenta», y la artesanía incluye «que la demo se abra y se pruebe».
- **Anticipación «medida»**: no basta con decir que se anticipa; hay que mostrar meses de adelanto. Sin etiquetas, cuesta definir contra qué se mide (inferido).
- **Bache frente a caída**: es una pregunta explícita (§2.4) y un criterio (estabilidad). Un score que oscile con la caja de cada mes penaliza.
- **Holdings con filiales**: hasta 24 empresas por grupo. Si se mezclan niveles de empresa y grupo, las señales pueden duplicarse o diluirse (inferido).
- **El ejemplo es ilustrativo**: Northbrook y Velasco no tienen por qué estar en el dataset.
- **Instrucciones escondidas en documentos (riesgo típico)**: `transactions.csv` incluye «concepto del banco» y contraparte, que son texto libre. Si un LLM los lee (por ejemplo, en un «agente de recomendaciones»), alguno podría contener texto que parezca una orden.
- **Codificación y tildes (riesgo típico)**: los CSV tienen conceptos bancarios, nombres de contraparte y varios países. Es probable que haya caracteres no ASCII (inferido), con riesgo de que se rompan en Windows si no se lee en UTF-8.
- **Zonas horarias y fechas (riesgo típico)**: hay fechas de transacción, emisión, vencimiento, cobro, «próxima fecha de pago» y un corte a «1 de septiembre de 2026». El rango «septiembre de 2024 a septiembre de 2026» suma 25 meses nominales frente a los «24 meses» anunciados. Con varios países, el formato de fecha puede ser ambiguo.
- **Límites de API (riesgo típico)**: el enunciado sugiere un «agente». Si se usa un LLM en la demo en vivo, las cuotas, la latencia o el coste pueden fallar justo delante del jurado.

### Qué distinguiría a un proyecto ganador
- **Producto y comprador claros**: es lo que más se repite (§3.4, §5, §6.3, §7, §8), y la nota del equipo dice que Embat lo valora «sobre todo».
- **Embat como comprador**: aparece como «el comprador más obvio» en tres sitios distintos.
- **Trayectoria y dos direcciones**: el ejemplo que abre el reto (45→65 frente a 82→68) es justo el caso que hay que resolver.
- **Explicación**: «Nadie compra una caja negra para decidir a quién presta o a quién asegura».
- **Anticipación con cifra**: «cuántos meses antes, **medido**», más el bonus del monitor autónomo.
- **Demo y pitch ensayados**: «La demo cuenta tanto como el producto… Guardad tiempo para ensayar el pitch.»
- **Simplicidad**: un modelo sencillo con un producto claro encima interesa más que uno sofisticado.
