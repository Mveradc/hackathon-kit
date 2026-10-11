Fecha: 2026-10-10

## Enfoque elegido

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

## Matices del equipo

Ninguno.

## Ambigüedades abiertas que afectan a esta elección

1. **¿Qué distingue ESCALAR de NO_PAGAR?** ¿El ERP es la fuente de verdad si contradice el Excel? Afecta de lleno a A: las reglas se codifican a mano y los casos grises son su punto frágil.
2. **¿El JSONL del lote 2 se valida contra la regla nueva y el ERP actualizado? ¿Hay que reprocesar el lote 1?** En A, la regla nueva obliga a tocar código y a decidir qué facturas se invalidan por cambio de versión de reglas.
3. **¿Qué «dato de la Caja» puede cambiar el domingo, y cuándo?** La demo de A depende de poder reprocesar solo lo afectado por un dato del ERP.
4. **¿Qué pasa con archivos ilegibles o corruptos?** A necesita saber qué resultado asignarles para no romper el «registro único por archivo».
6. **¿El LLM es obligatorio o esperado?** A reduce el LLM a la extracción; si se esperaba que fuera protagonista, hay que justificarlo en un ADR.
