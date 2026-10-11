# Revisor C1–C6 · 03-xray-embat-real

Informe literal del revisor independiente (`claude -p` sin el plugin, 2026-10-05). Resumen y patrones en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla | `analisis.md`: «el enunciado insiste en que […] la valoración se centra en el producto», pero el enunciado dice «Tres bloques con el **mismo peso**» |
| C2 | Falla | `enfoques.md` (C): «El comprador no es Embat directamente, lo que pesa menos que "el candidato obvio"». El enunciado no dice cómo pesa el comprador |
| C3 | Falla | `CLAUDE.generado.md`: «Eliminatorio: **demo navegable** […] y **producto encima del score**». El enunciado dice «Obligatorio», nunca «eliminatorio» |
| C4 | Falla | `plan.md`: demo mínima «sáb 12:00 […] ranking → ficha → alerta», y la web es de C, que llega el «sáb 10:00» |
| C5 | Falla | `pitch.md`: «un aviso a tiempo para decidir a quién presta o asegura, que hoy no tiene». Ni que Embat preste o asegure ni lo que «no tiene» sale del enunciado |
| C6 | Pasa | `plan.md` asigna carpeta exclusiva por persona y contrato de 4 endpoints a las vie 20:00; hay huecos, pero ninguno obliga a deshacer trabajo |

## Fallos encontrados
1. **C3. «Eliminatorio» inventado.** En `CLAUDE.generado.md` pone «Eliminatorio: demo navegable […] y producto encima del score». La tabla de la sección 5 marca esos requisitos como «Obligatorio» y en ningún sitio habla de eliminación. Importa porque el CLAUDE.md lo carga cada sesión de código y presenta como regla del jurado algo que el jurado no ha dicho.

2. **C4. La demo mínima depende de quien llega dos horas antes.** El hito de `plan.md` «sáb 12:00 · Demo mínima: URL pública → ranking → ficha → alerta» tiene como dueño a B. Pero las tres vistas son de C («Demo fea», hasta sáb 12:00: ranking, ficha y feed de alertas), y C llega a las 10:00 y además tiene que revisar el contrato a las 10:30. El repliegue («Score provisional de una sola señal») cubre el motor, no la web. Es justo el patrón de fallo del ejemplo de C4. Además, B tiene que «Desplegar motor y web en una URL pública» antes del sáb 01:00, cuando todavía no existe nada en `web/`.

3. **C1 → C5. Embat como prestamista o aseguradora.** En `analisis.md` aparece «Para quién: quien decide "a quién presta o a quién asegura" y, como comprador más obvio, Embat». En `pitch.md` (tramo 3:50) se convierte en «Embat […] para decidir a quién presta o asegura, que hoy no tiene», y en el tramo 0:00 en «se entera de quién se tuerce cuando ya es evidente». El enunciado usa «a quién presta o a quién asegura» de forma genérica (3.3). No dice que Embat preste o asegure, ni qué herramientas tiene hoy. El pitch inventa la situación del cliente justo en el tramo de Comprador, que ya es el más flojo.

4. **C5 (y C3/C4). El bonus Monitor se reclama con una reproducción temporal.** El enunciado define el monitor así: «El sistema no espera a que le pregunten: levanta la mano». Lo que se construye es un «Selector de mes que reproduce el tiempo en ranking y alertas» (`plan.md`, C), es decir, un feed que hay que abrir para verlo. Aun así, `pitch.md` titula el tramo «el monitor avisa solo» y lo cuenta como «Monitor (bonus)», y `CLAUDE.generado.md` dice «avisa sola». Ninguna pregunta del jurado ataca este punto débil.

5. **C3. Dato sobre el jurado inventado.** `reglas/convenciones.md` dice: «El jurado y Embat son hispanohablantes y el pitch es en español». El enunciado no dice nada del idioma del jurado ni del pitch. Se presenta como hecho y no como inferencia.

6. **C1. Pesos distorsionados.** En `analisis.md` (Riesgos) pone: «el enunciado insiste en que "el score solo no es la entrega" y que la valoración se centra en el producto». Lo de «valora sobre todo el producto» viene de la nota del equipo, no del enunciado oficial, y choca con «mismo peso». Atribuirlo al enunciado mezcla fuentes en un dato de peso.

7. **C3. «Desempate declarado» inventado.** `CLAUDE.generado.md` dice: «Desempate declarado: "Un modelo sencillo con un producto claro encima interesa más…"». En el enunciado esa frase es una preferencia general de la sección 6, no una regla de desempate.

8. **C2. Comparativa sesgada por un comportamiento del jurado inventado.** Al enfoque C se le dice que el comprador externo «pesa menos que "el candidato obvio"» y por eso recibe «Comprador: medio». El enunciado admite cualquier comprador: «Si hay alguien dispuesto a pagarlo, entra». En menor medida, A cita entre comillas «"herramienta interna"», que no aparece en ninguna fuente.

9. **C3/C4. La hora de entrega no cuadra con `equipo.md`.** `CLAUDE.generado.md` dice «Entrega: hora límite no especificada (análisis: ambigüedad 4)». Pero el CLAUDE.md ya usa `equipo.md` (tabla de Dueños), donde pone «Entrega: dom 20 sep 2026 10:00», y `plan.md` trabaja con esa hora. El fichero que se lee en cada sesión contradice al plan.

10. **C3/C4. Nombre de campo inventado.** En `reglas/motor.md` aparece «Separación train/validación **por `group_id`**», en `reglas/convenciones.md` «nombres de campo del dataset tal cual (`company_id`, `group_id`…)» y en `plan.md` «Partición por `group_id`». El enunciado solo nombra `company_id`; de `companies.csv` dice «grupo», sin dar el nombre del campo.

11. **C3. Una ambigüedad se convierte en hecho.** `reglas/motor.md` dice: «El enunciado no da etiqueta ni leaderboard». Lo de la etiqueta es la ambigüedad 1 del análisis, que de hecho apunta lo contrario: «"sin resultado" […] sugiere que existe un resultado».

12. **C4. Una dependencia sin tarea.** En «Quién espera a quién»: «A deja el sáb a las 09:00 un score provisional (una señal)». En la tabla de A no hay ninguna tarea así: a las 09:00 solo cierra «Señales», y el Score es para las 12:00. B conecta la API real contra algo que no figura en el plan de nadie.

13. **C5. Mediana presentada como media.** El tramo 2:50 de `pitch.md` dice «[CIFRA: mediana de meses de antelación] meses de media». Sería una cifra mal etiquetada delante del jurado.

14. **C5. Preguntas que faltan.** No se prepara la pregunta más previsible del enfoque: si el «evento» lo define el propio equipo con las mismas señales, la anticipación medida puede ser circular. Tampoco se responde de verdad por qué le sale a cuenta a Embat: «el modelo de cobro está en el README» esquiva una respuesta que el enunciado exige («por qué le sale a cuenta»).

15. **C3. Guías de pasos no verificables.** `CLAUDE.generado.md` remite a `.claude/skills/` y `plan.md` a la guía `respuesta-organizacion`, pero no se entregó ninguna. No puedo comprobar que cubran los momentos clave.

16. **C1. Datos en la sección equivocada y atribuciones dudosas.** En `analisis.md`, el «Pitch de ~5 minutos» está bajo «Obligatorios (tabla de la sección 5)», y esa tabla no lo incluye. Además, la frase de la sección 6 se presenta como «Mensaje explícito del jurado», cuando el enunciado no la atribuye al jurado.

17. **C3. Huecos y etiquetas imprecisas.** La «Estructura» de `CLAUDE.generado.md` no incluye `salidas/`, `pitch/` ni `.hackathon/`, aunque tienen dueño y reglas. La regla 5 («60–80 empresas, como el test oculto») cita «(análisis: ambigüedad 2)», pero esa ambigüedad es una pregunta, no la fuente de esa decisión.

## C6: justificación
Sí, un equipo empezaría antes con esto. Las carpetas de A, B y C no se solapan, los cuatro endpoints quedan nombrados desde el viernes, B sirve una API falsa para que C no se bloquee y las tareas de A son concretas (corte mensual, test de no fuga, evento en una sola función). En los primeros 30 minutos cada persona sabe qué hacer y dónde.

Echaría en falta:
- **Un ejemplo de contrato.** No hay ningún JSON de muestra ni el formato de `salidas/`, así que la primera hora depende de que A y B lo acuerden bien.
- **Un dueño para el arranque.** Nadie se encarga del `package.json` raíz que necesita `npm run arranca`.
- **Una demo mínima realista.** Habría que retrasarla o darle a B una vista mínima propia, porque C no puede montarla en dos horas.
- **Un monitor que avise de verdad**, por ejemplo con una notificación saliente, para no reclamar un bonus que no se tiene.

Sobra el tono de certeza sobre el jurado: «eliminatorio», «desempate», «hispanohablantes». El riesgo es que el equipo tome decisiones con reglas que nadie ha dicho.