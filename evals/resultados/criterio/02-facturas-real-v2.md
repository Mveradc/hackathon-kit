# Revisor C1–C6 · 02-facturas-real · segunda pasada

Cadena nueva (`prueba-m4-02-v2`) tras las correcciones del 2026-10-05, con la rúbrica y el prompt nuevos. Comparación en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (grave) | `analisis.md`: en «Descuidar la parte cuantitativa» solo aparecen «archivos/s, hardware, fórmula de coste». Faltan «nuevos tipos de archivo», «emails, imágenes o Excel», «versiones» y «trabajo pendiente», que el enunciado sí pide |
| C2 | Falla (leve) | `enfoques.md` A: el texto pone «Resiliencia (10): medio-alto» y la tabla pone «medio». Además, «el flujo principal cabe en unas 20 h» no tiene base |
| C3 | Falla (grave) | `CLAUDE.generado.md` regla 7: la lista de la traza («factura, agente, modelo, entrada/evidencia citada, salida, tokens, coste y latencia») no incluye versiones ni trabajo pendiente, que la rúbrica de 20 pts pide expresamente |
| C4 | Falla (grave) | `plan.md`: la única tarea de cifras es «`docs/cifras.md`: archivos/s, hardware, fórmula con rate limits». Ninguna tarea cubre el plan para nuevos tipos de archivo (Escalabilidad, 25 pts y primer desempate) |
| C5 | Falla (grave) | `pitch.md`: a «¿Por qué cuatro agentes y no uno, o reglas sin LLM?» responde «Comparativa en ADRs», pero los ADRs previstos son solo «agentes, modelos, auditor» |
| C6 | Falla (leve) | `plan.md`: «Todos → Persona C (`contratos.py`): usar diccionarios falsos del borrador». Ese borrador no existe en nada de lo generado |

## Fallos encontrados

**Graves**

1. **Grave · C1, C4, C5. Se pierde una parte de Escalabilidad y coste.**
   - **Ficheros:** `analisis.md` («Descuidar la parte cuantitativa… Piden archivos/s, hardware, fórmula de coste»), `plan.md` (Persona D: «`docs/cifras.md`: archivos/s, hardware, fórmula con rate limits») y `pitch.md` (bloque 6:00–8:00).
   - **Qué dice el enunciado:** la rúbrica pide «un plan para incorporar más volumen y nuevos tipos de archivo». La defensa pide «contad qué cambiaría con emails, imágenes o Excel». El lote 2 pide mostrar «cuáles son los límites del sistema».
   - **Qué pasa en la cadena:** el análisis, en «Cómo se evalúa», reduce la rúbrica a pesos y pierde ese contenido. Por eso nadie tiene la tarea en el plan y el pitch no lo menciona.
   - **Por qué importa:** es el criterio de 25 pts y el primer desempate.

2. **Grave · C1, C3, C4, C5. La traza no cubre lo que pide la rúbrica de trazabilidad.**
   - **Ficheros:** `CLAUDE.generado.md` regla 7, `reglas/agentes-y-resiliencia.md` («Cada paso registra factura, agente, modelo, evidencia citada, tokens, coste y latencia») y `plan.md` (Persona E: «`traza/registro.py`… Cumple la regla 7 del CLAUDE.md»). En `pitch.md`, el bloque 4:00–6:00 solo enseña «agente, modelo, evidencia citada, tokens y coste».
   - **Qué dice el enunciado:** «mostrad estado, evidencia, versiones, latencia, errores, reintentos y trabajo pendiente». También: «Mostrad cómo detectar errores, reintentos, trabajo pendiente y coste».
   - **Qué falta:** la versión de la regla y de los datos no está en ningún sitio, y es justo lo que hace falta para explicar el reprocesado tras la «regla nueva» del sábado. Tampoco hay ninguna vista de trabajo pendiente.
   - **Por qué importa:** la comprobación del plan da por buena una traza que no cumple la rúbrica. Habrá que rehacer el esquema cuando ya esté en uso.

3. **Grave · C5. El pitch cita un ADR que no está previsto.**
   - **Fichero:** `pitch.md`, respuesta a «¿…o reglas sin LLM?»: «Comparativa en ADRs; ambigüedad 4 abierta».
   - **Qué dice el plan:** `plan.md` solo prevé «`docs/adrs.md`: agentes, modelos, auditor». Ningún ADR compara LLM con reglas.
   - **Por qué importa:** es la pregunta más previsible ante un enfoque que pone el LLM en el núcleo, y el equipo remitiría al jurado a algo que no tiene. El enunciado dice que «El tribunal podrá preguntar por cualquier decisión, alternativa o trade-off registrado».

**Leves**

4. **Leve · C1. Se cambia la fuerza de lo que dice el enunciado.**
   - **Fichero:** `analisis.md`: «El 35 % va al PDF y los ADRs, y si el PDF falta se pierden esos 35 puntos».
   - **Qué dice el enunciado:** «puede dejar sin puntos». Además, los 35 puntos son de «Producto, arquitectura y ADRs», que también se defienden en la sala.
   - **Por qué es leve:** no cambia lo que se construye.

5. **Leve · C1. Una inferencia aparece como hecho.**
   - **Fichero:** `analisis.md`, Restricciones: «la demo tiene que aguantar cambios en vivo».
   - **Qué dice el enunciado:** solo «podrá cambiar un dato de la Caja para comprobar la demo». Ni «en vivo» ni el momento están en el enunciado (es la ambigüedad 5).
   - **Ficheros a los que pasa:** `CLAUDE.generado.md` regla 9 y el bloque de demo de `pitch.md`. Es razonable, pero va sin marca de «inferido».

6. **Leve · C1. Hay afirmaciones sin marca de origen.**
   - **Fichero:** `analisis.md`.
   - **Qué pasa:** «`make` no viene de serie en Windows» es conocimiento externo y no va marcado como tal. «Datos obligatorios: PDFs…, Excel, ERP» tampoco tiene base, porque el enunciado no dice que su uso sea obligatorio.

7. **Leve · C2. Hay incoherencias y una estimación sin base.**
   - **Fichero:** `enfoques.md`.
   - **Qué pasa:** en A, el texto da la Resiliencia «medio-alto» y la tabla da «medio». La cifra «unas 20 h» para el flujo principal va sin marcar como estimación.
   - **Por qué es leve:** no altera la elección.

8. **Leve · C3. Una etiqueta de origen es falsa.**
   - **Fichero:** `CLAUDE.generado.md` regla 12: «se reprocesa solo lo afectado… (enunciado…)».
   - **Qué dicen las fuentes:** el enunciado solo dice «explicad qué decisiones debéis reprocesar». El reprocesado selectivo venía del enfoque A, y `decision.md` (enfoque C) no lo menciona.
   - **Por qué es leve:** la idea es razonable, pero es un supuesto, no un dato del enunciado.

9. **Leve · C3. Otra etiqueta apunta a una fuente que no lo dice.**
   - **Fichero:** `reglas/agentes-y-resiliencia.md`: «su detección queda en la traza (análisis: riesgo típico)».
   - **Qué dice el análisis:** no dice nada de registrar la detección.

10. **Leve · C3. Las guías de pasos no se pueden evaluar.**
    - **Qué pasa:** `plan.md` cita `.claude/skills/lote-2` y `.claude/skills/ensayo-defensa/SKILL.md`, y además manda «Cerrar los TODO de `.claude/skills/`». Esas guías no están en `salidas/`, así que no se puede comprobar que cubran el lote 2 ni la defensa.

11. **Leve · C4. El lote 2 no tiene tarea propia y choca con los dueños.**
    - **Fichero:** `plan.md`.
    - **Qué pasa:** el hito «sáb 23:00 `outcomes_lote2.jsonl`, reprocesado y re-entrega» es de Persona A, pero ninguna tarea de su tabla genera ese JSONL; la última es «Cargar export del ERP y CSV nuevos». Además, la «re-entrega» toca el repo de entrega, cuyo dueño es Persona D.

12. **Leve · C4. El reparto no encaja con los perfiles del equipo.**
    - **Ficheros:** `plan.md` y `equipo.md`.
    - **Persona C:** su perfil dice «Prefiere no hacer: backend», y sin embargo es dueña de `contratos.py` (hito de las vie 20:00) y de los cuatro agentes.
    - **Persona B:** su perfil es «negocio, ciberseguridad». Tiene el orquestador, el cliente LLM y la máquina de estados, pero no la defensa contra instrucciones incrustadas, que va a Persona C.
    - **Créditos de LLM:** si la organización no da créditos, la tarea de Persona B de las 19:30 («Ambas claves responden») no tiene ninguna forma de desbloquearse.

13. **Leve · C4/C5. Parte de lo que se enseña no tiene tarea.**
    - **Qué pasa:** el «Diagrama» que sale en pantalla en el pitch y la actualización del PDF final con cifras y lote 2 solo existen como hito («dom 09:30 Ensayo 2 + PDF final»). Ninguna tarea los cubre.

14. **Leve · C5. El pitch se aparta de la estructura de la defensa.**
    - **Fichero:** `pitch.md`.
    - **Bonus:** el enunciado lo coloca en «Demo y contexto», y el pitch lo mete en el bloque 4:00–6:00, que resta tiempo a trazabilidad, escala y coste.
    - **Producto:** el contexto no dice «quién lo usa y qué trabajo le ahorra».
    - **Preguntas del jurado:** ninguna ataca el punto débil que la propia decisión reconoce: «Medio en producto si Alberto no ve nada usable».
    - **Quién responde:** Persona C y Persona B figuran como «Presenta: no» en `equipo.md`.

## C6: justificación
Lo generado da a cada persona carpeta, dueño, comando de arranque y reglas operativas concretas: JSONL, prompt injection, resiliencia y `make erp-fast`. Las ambigüedades van bien marcadas como supuestos, así que el equipo empezaría antes que sin ello.

Aun así, en los primeros 30 minutos nadie tiene un contrato contra el que programar. `contratos.py` no existe hasta las 20:00 y el «borrador» al que remite el plan no está en ningún sitio. Además, el contrato depende de quien prefiere no hacer backend.

**Qué echaría en falta:**
- Un esquema mínimo de estado y traza, con versión de regla y de datos y estado pendiente.
- Las tareas sobre nuevos tipos de archivo y límites del sistema.
- Una tarea explícita para generar `outcomes_lote2.jsonl`.
- Un ADR que compare LLM con reglas.
- Un plan B si no hay créditos de LLM.

**Qué sobra:** el riesgo de zonas horarias del análisis y la duplicación de las mismas reglas entre `CLAUDE.md` y `.claude/rules/`.

Con la regla 7 tal como está, Persona E construiría una traza que después tendría que ampliar.