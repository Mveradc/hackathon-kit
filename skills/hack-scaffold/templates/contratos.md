<!--
Plantilla de docs/contratos.md. Un bloque por contrato: la entrega del reto, los datos de entrada
que da el reto y, si hay varias piezas, cada interfaz entre ellas. Sirve para que cada persona
pueda trabajar desde la primera hora contra el contrato, con datos falsos, sin esperar a las demás.
Cada campo sale del análisis o de la decisión, con su origen. Lo que el análisis no fija va como
supuesto o como TODO, nunca inventado como si fuera del reto.
Quita estos comentarios al generar.
-->
# Contratos

Lo que no se puede romper sin avisar al resto del equipo. Si un contrato cambia, se cambia aquí primero.

## <Nombre del contrato: entrega, datos de entrada o «<pieza> → <pieza>»>

<Quién lo produce, quién lo consume y dónde vive (fichero, endpoint, formulario de entrega).> (<origen>)

| Campo | Tipo | Obligatorio | Valores o formato | Origen |
|---|---|---|---|---|
| <nombre> | <texto, número, fecha…> | <sí / no / TODO> | <valores permitidos, unidad, zona horaria> | <enunciado · análisis: <sección> · decisión · supuesto: ambigüedad N, confirmar con la organización · TODO> |

Ejemplo mínimo válido:

```<formato>
<un registro o una petición y su respuesta, con valores de ejemplo que respeten la tabla>
```
