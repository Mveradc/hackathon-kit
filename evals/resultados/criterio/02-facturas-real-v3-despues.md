# Revisor C1–C6 · 02-facturas-real · tercera pasada, después de /hack-check aplicar

Copia `../prueba-m4-02-check` tras `/hack-check aplicar`, rúbrica de cierre, 2026-10-06.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (grave) | `analisis.md`: «Piden archivos/s, hardware, fórmula de coste y «Separad mediciones de estimaciones»». Falta «un plan para incorporar más volumen y nuevos tipos de archivo» y «qué cambiaría con emails, imágenes o Excel» |
| C2 | Falla (leve) | `enfoques.md` A, bajo Producto (35): «Más flojo en «agradable de operar», porque es una CLI». Esa frase es del criterio Calidad (10) |
| C3 | Falla (leve) | `CLAUDE.generado.md` regla 13: «El repo de entrega es otro repositorio público con exactamente los tres ficheros». No dice «de GitHub» ni habla de teamId; `verificacion.md` lo marca como bloqueante y no lo corrige |
| C4 | Falla (grave) | `plan.md`: Persona C («Prefiere no hacer / no sabe: backend») lleva `contratos.py` y los cuatro agentes; ninguna tarea cubre «nuevos tipos de archivo», «límites», «versiones» ni «trabajo pendiente» |
| C5 | Falla (grave) | `pitch.md` 6:00–8:00: «estimado aparte: fórmula con rate limits del proveedor». No habla de límites, de «emails, imágenes o Excel», del formato ni de las personas |
| C6 | En parte | Dueños, carpetas y contratos claros en 30 min; el camino crítico de backend recae en quien no quiere hacer backend |

Bloqueantes: ninguno

## Fallos encontrados

**Graves**

1. **Grave, no bloqueante. C1 (se arrastra a C4 y C5).** `analisis.md` resume los criterios con peso y deja fuera parte de lo que pide cada uno.
   - **Escalabilidad y coste (25 pts):** el análisis cita «archivos/s, hardware, fórmula de coste». El enunciado pide además «límites» y «un plan para incorporar más volumen y nuevos tipos de archivo» (rúbrica). En «Escala y fallos» pide «explicad cómo añadiríais nuevos tipos de archivo». En la defensa pide «contad qué cambiaría con emails, imágenes o Excel». Nada de esto aparece en el análisis.
   - **Trazabilidad (20 pts):** faltan «versiones» y «trabajo pendiente».
   - **Por qué importa:** Escalabilidad y coste es el primer criterio de desempate. Este hueco del análisis se traslada sin cambios a `plan.md`, donde `docs/cifras.md` no tiene ni límites ni nuevos tipos de archivo, y a `pitch.md`.

2. **Grave, no bloqueante. C4.** `plan.md` contradice lo que el equipo escribió en `equipo.md`.
   - Persona C («Prefiere no hacer / no sabe: backend») es dueña del hito de contratos de vie 20:00, del que depende todo el equipo. También hace el extractor, el conciliador, el verificador y el auditor, que son el núcleo backend del enfoque C.
   - Persona E, que tampoco quiere hacer backend, lleva `traza/registro.py` y el bonus con LLM.
   - Persona B (negocio, ciberseguridad) lleva el orquestador, el cliente LLM y la máquina de estados, pero no la defensa contra instrucciones escondidas, que es justo lo suyo.
   - `decision.md` pide «3–4 personas con experiencia en LLM, orquestación y backend», y el plan no lo reconcilia con el equipo real.
   - Por qué importa: hay riesgo de rehacer el camino crítico y de quedar NO APTO.

3. **Grave, no bloqueante. C4.** Ninguna tarea cubre puntos que la rúbrica pide de forma explícita:
   - límites del sistema, tanto los de la rúbrica de escala como el «DEBÉIS MOSTRAR … cuáles son los límites del sistema» del lote 2;
   - plan para nuevos tipos de archivo;
   - versiones de prompt o modelo en la traza;
   - vista del trabajo pendiente.

   `verificacion.md` detecta estos huecos («Huecos de cobertura: 5») pero no aplica ningún cambio. Afecta a 25 + 20 pts.

4. **Grave, no bloqueante. C5.** `pitch.md` no cubre partes de criterios con peso:
   - **Producto (35):** no defiende «el formato», no explica el reparto con «personas» ni dice «qué trabajo le ahorra» a Alberto. El enunciado lo pide en la rúbrica y en «Arquitectura y ADRs · 2 min».
   - **Escala (25):** no habla de límites ni de «emails, imágenes o Excel».
   - **Trazabilidad (20):** no enseña versiones, latencia ni trabajo pendiente.

   El pitch afirma «Todos los criterios con peso tienen bloque», pero los bloques no cubren lo que esos criterios piden.

**Leves**

5. **Leve. C1.** `analisis.md`: «si el PDF falta se pierden esos 35 puntos». El enunciado dice que «puede dejar sin puntos», y los 35 pts son de «Producto, arquitectura y ADRs», no solo del PDF. El análisis aumenta la fuerza de lo que dice el enunciado.

6. **Leve. C1.** Formulaciones imprecisas en `analisis.md`:
   - «cuya raíz contenga «exactamente» tres archivos, más el teamId y la URL»: se puede leer como que el teamId va dentro del repositorio, y eso rompería el «exactamente».
   - «Datos obligatorios: PDFs…»: el enunciado no los llama obligatorios.
   - «Alberto recibe 500 facturas»: según el enunciado, «Recibís» (el equipo).

7. **Leve. C2.** En `enfoques.md`, A y B ponen «agradable de operar» bajo Producto (35), cuando pertenece a Calidad de ejecución (10). En A, Calidad aparece incluso como «alto».
   - En A, la tabla dice Resiliencia «medio» y el texto «medio-alto».
   - «el flujo principal cabe en unas 20 h» y «el ERP con latencia es el cuello de botella real» son estimaciones que no se marcan como tales.

8. **Leve. C3.** `CLAUDE.generado.md` omite tres cosas del enunciado:
   - que el repositorio es «de GitHub»;
   - que hay que compartir el teamId y la URL («Compartid vuestro teamId y la URL de un repositorio público de GitHub»);
   - que el PDF lleva dos secciones y «entre 2 y 5» ADRs.

   `verificacion.md` los marca como «Bloqueantes: 2» pero no los aplica («Cambios aplicados» no incluye la regla 13). No los clasifico como bloqueantes porque `plan.md` los cubre con dueño: Persona D tiene a vie 21:00 «Crear repo de entrega público y enviar teamId y URL», y el hito de sáb 13:00 comprueba «Tiene las dos secciones». Además, la propia verificación reconoce que el PDF no afecta a la elegibilidad. Aun así, ni el plan ni el CLAUDE dicen «GitHub».

9. **Leve. C3.** Los cinco portátiles son Windows y el ERP se arranca con `make`.
   - `convenciones.md` promete que «se documenta su alternativa», pero la sección Comandos de `CLAUDE.generado.md` solo tiene `uv run albertitos`: no hay comando para arrancar el ERP ni para comprobar el JSONL.
   - `.gitignore` no aparece en «Estructura» y ninguna regla avisa del riesgo de UTF-16 al crearlo desde PowerShell. Lo mitiga la comprobación de Persona B («Commit sin `.env` ni datos»).

10. **Leve. C3.** Etiquetas que dicen más que su fuente:
    - Regla 12, «se reprocesa solo lo afectado (enunciado)»: el enunciado pide «explicad qué decisiones debéis reprocesar»; reprocesar solo lo afectado es una decisión del equipo.
    - Regla 7, «(decisión)»: añade campos (agente, modelo, entrada, salida) que `decision.md` no menciona.

11. **Leve. C4.** Problemas de horario y de dueños en `plan.md`:
    - El repliegue de la congelación de dom 02:00 lo decide Persona D, que duerme de sáb 23:30 a 05:30. La verificación no lo detecta.
    - Las cifras de Persona A y Persona D tienen plazo «dom 02:00» en `pitch.md` y los dos están durmiendo. La verificación lo detecta y no lo aplica.
    - El lote 1 se procesa a sáb 13:00, antes de que exista el auditor (14:00). Detectado y no aplicado.
    - El hito de contratos no tiene tarea en la tabla de Persona C.
    - Ninguna tarea genera `outcomes_lote2.jsonl`; solo existe el hito.
    - La «re-entrega» de sáb 23:00 la hace Persona A, pero el repo de entrega es de Persona D.
    - Falta la ambigüedad 4 en las preguntas a la organización.

12. **Leve. C4.** El conciliador de Persona C se comprueba con «Discrepancia → ESCALAR con ambos valores», sin marca de supuesto y con un alcance más amplio que la regla 11, que habla solo de Excel frente a ERP. Leído como «cualquier discrepancia», puede convertir en ESCALAR casos que la referencia espera como NO_PAGAR, y eso pone en riesgo la condición de APTO.

13. **Leve. C4 (seguridad menor).** Persona B tiene la tarea «Proveedor LLM principal y de respaldo en `.env.example`», comprobada con «Ambas claves responden». La redacción invita a poner las claves en un fichero que se commitea. `convenciones.md` lo contradice («sin valores»).

14. **Leve. C5.** En `pitch.md` hay cosas que no encajan con el enunciado ni con el plan:
    - El bonus se enseña en «Trazabilidad», pero el enunciado lo coloca en «Demo y contexto».
    - Las preguntas del jurado las contestan Persona C y Persona B, que en `equipo.md` figuran como «Presenta: no».
    - «Comparativa en ADRs» para la alternativa «reglas sin LLM»: la tarea de ADRs solo cita «agentes, modelos, auditor». La verificación lo detecta y solo informa.

15. **Leve. `verificacion.md`, transversal.**
    - «Rúbrica 35/25/20/10/10 — Sostenida» se apoya en la cita «Rúbrica del tribunal (100 + 10 pts)», que no contiene ninguna de esas cifras.
    - La regla 7 se da por sostenida con una cita que solo cubre «tokens, coste y latencia».
    - Declara bloqueantes y huecos sin aplicar ninguna corrección.

## C6: justificación
En parte. Leyendo solo lo generado, cada persona sabe en sus primeros 30 minutos su carpeta, su primera tarea y contra qué contrato trabaja (`contratos.py` a vie 20:00, contrato JSONL bien copiado). Las fechas y los entregables son correctos, y la defensa contra instrucciones escondidas tiene tarea y prueba. El problema es que el camino crítico del enfoque C (contratos y agentes) recae en Persona C, que declaró no querer hacer backend, en un equipo sin ningún perfil backend. Eso puede obligar a rehacer trabajo o retrasar la demo mínima.

Echaría en falta:
- un comando documentado para arrancar el ERP en Windows;
- tareas para límites, nuevos tipos de archivo, versiones y trabajo pendiente, que suman puntos en criterios de 25 y 20;
- que la verificación aplicara lo que detectó.

Sobra la cantidad de supuestos que llevan a «ante duda, ESCALAR», que sin confirmar pueden costar la condición de APTO, y meter el guion del pitch dentro de un SKILL.md.