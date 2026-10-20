<!--
Plantilla del CLAUDE.md del proyecto. Menos de 100 líneas en total.
Cabe solo lo que el agente no puede deducir mirando el código: qué puntúa, invariantes del dominio,
contratos, límites y convenciones. Lo que se ve en el código (dependencias, scripts) no se repite.
Quita todos estos comentarios al generar.
-->

# <Nombre del proyecto> · <Hackathon> · reto «<nombre del reto>»

<Una frase: qué se construye y para quién.> **<Tesis del enfoque en una línea, en negrita: la decisión de diseño que todo el equipo debe respetar.>**

## Qué puntúa (léelo antes de proponer nada)
<!-- De analisis.md: lo obligatorio primero, luego criterios con pesos, preferencias y bonus, con la misma palabra
que usa el análisis (obligatorio no es «eliminatorio»; una preferencia no es «desempate»). 3–5 viñetas. -->

## Comandos
| Qué | Cómo |
|---|---|
| Instalar y arrancar | `<comando único>` |

## Estructura
<!-- Árbol de lo generado, una línea de explicación por carpeta. Con varias piezas: una carpeta por pieza, con su stack y cómo se hablan entre ellas. -->

## Reglas de equipo
<!--
Convierte cada contrato, trampa o riesgo del análisis (y cada matiz de la decisión) en una invariante:
algo concreto que el código debe cumplir siempre y que se puede comprobar.
- Contrato de entrega del reto → formato exacto que no se puede romper.
- Riesgo o trampa del análisis → lo que el código hace siempre para no caer en él.
- Ambigüedad abierta → comportamiento por defecto hasta que la organización responda, como supuesto.
Cada regla termina con su origen entre paréntesis: (enunciado), (análisis: <sección>), (análisis: riesgo típico),
(decisión), (supuesto: ambigüedad N, confirmar con la organización) o (conocimiento externo, verificar).
Una ambigüedad nunca es la fuente de algo que se da por cierto.
Si una regla no sale de ahí, no va: nada de buenas prácticas genéricas ni de lecciones de otros retos.
-->
1. 

## Fuera de alcance
<!-- Lo que la decisión deja fuera a propósito. Si alguien lo propone, se remite aquí. -->

## Convenciones
<!-- Idioma de código y docs, commits, secretos en .env. Breve: el detalle está en .claude/rules/convenciones.md.
La frase de los commits va siempre, tal cual. -->
Cada commit empieza por el ID de su tarea en `.hackathon/plan.md`: `Txx · …` (por ejemplo, `T05 · …`).

## Fechas
<!-- Hitos del reto con hora y zona horaria, sacados del análisis. "No especificado" si no hay. -->

## Contexto
- Reto analizado: `.hackathon/analisis.md`
- Enfoques considerados: `.hackathon/enfoques.md`
- Decisión del equipo: `.hackathon/decision.md`
- Contratos (campos y ejemplo): `docs/contratos.md`
- Reglas por carpeta: `.claude/rules/` · Guías de pasos: `.claude/skills/`
<!-- La viñeta siguiente, tal cual y solo con la coordinación activa (Paso 3b); sin ella, quítala. -->
- Si te preguntan por el estado del equipo (criterios, entrega, quién va tarde), usa las herramientas `jurado` y `ruta` del MCP y contesta solo con lo que digan: cita de qué fichero y de qué hora sale cada dato, no añadas recomendaciones y, si la ruta no tiene estimación, no hagas previsiones de margen.
