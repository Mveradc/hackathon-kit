# Revisor C1–C6 · 06-commahack · tercera pasada, después de /hack-check aplicar

Copia `../prueba-m4-06-check` tras `/hack-check aplicar`, rúbrica de cierre, 2026-10-06.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (leve) | `analisis.md`: «todas las horas del enunciado son locales» y «Tecnologías obligatorias o prohibidas: ninguna». El enunciado no dice ninguna de las dos cosas. |
| C2 | Pasa | `enfoques.md`: tres apuestas de fondo distintas (en el coche, herramienta de datos fuera del coche, chestnut sin openpilot), sin stacks y con «Orientación» condicional. |
| C3 | Falla (grave) | Guía `demo-domingo` (citada en `verificacion.md`): «la demo es lo único que el enunciado exige». Y `inferencia-chestnut.md`: «criterio del equipo», que `decision.md` contradice con «Matices del equipo: Ninguno». |
| C4 | Falla (grave) | `plan.md`, hito sáb 12:00: «`uv run mas-modelo compare <ruta>` genera mp4 y CSV». Ninguna tarea crea el subcomando `compare` y el CSV de calidad llega a las 20:00. |
| C5 | Falla (leve) | `pitch.md`: «un comando, cualquier ruta» con `compare` en pantalla, sin tarea. Además, la pregunta del jurado sobre licencia la contesta A, que «Presenta el pitch o la defensa: no». |
| C6 | En parte | Cada persona tiene ficheros, contratos (`Frame`, `load_model`/`run`) y bloques, pero el «modelo ampliado sin entrenar» no está definido y la demo mínima no se puede comprobar. |

Bloqueantes: 1

## Fallos encontrados

**Graves**

1. **Grave, bloqueante (descalificación).** C3 (y `verificacion.md`). Guía `.claude/skills/demo-domingo`: «la demo es lo único que el enunciado exige».
   - El enunciado no dice nada de entregables: solo trae una agenda con «domingo 15:00 demos y jurado». El propio análisis deja como **No especificado** el repositorio, el vídeo, el envío formal y el plazo (ambigüedad 2).
   - La guía convierte esa ambigüedad en un hecho sobre los entregables. Si la organización pide un envío (Devpost, repositorio, vídeo) con hora, el equipo puede no hacerlo.
   - `verificacion.md` detecta la frase, la deja «fuera del alcance de la edición», no la corrige y aun así concluye «Bloqueantes: Ninguno».
   - Solo he visto la guía a través de la cita de `verificacion.md`: el fichero no está en `salidas/`.

2. **Grave, no bloqueante.** C3, con arrastre a C4 y C5.
   - Ficheros afectados: `inferencia-chestnut.md`, `plan.md`, `pitch.md` y `verificacion.md` (fila 34).
   - Cita: «No se escribe código de entrenamiento […] (no escribir código de entrenamiento: criterio del equipo, más estricto que la decisión)».
   - La fuente que da la etiqueta no lo dice: `decision.md` pone «Matices del equipo: Ninguno» y la decisión solo excluye «entrenar un modelo desde cero». La etiqueta la introdujo `verificacion.md` al «corregir» otra, así que el arreglo creó un origen falso.
   - Consecuencia en el plan: la tarea de B es «Variante ampliada (más resolución o más frames), sin entrenar», con repliegue «Ampliado = base con más resolución».
   - Consecuencia en el pitch: promete «casos donde el ampliado acierta y el base no».
   - Problema técnico (inferencia mía, no del enunciado): una red fija a la que se le cambia la resolución o el número de frames sin reentrenar difícilmente mejora; lo normal es que ni siquiera acepte la entrada. La regla, que nadie del equipo pidió, deja sin un camino viable la pieza central del enfoque y puede obligar a rehacerla.

3. **Grave, no bloqueante.** C4 y C5. `plan.md`, hito «sáb 12:00 | Demo mínima», comprobado con «`uv run mas-modelo compare <ruta>` genera mp4 y CSV».
   - A solo tiene la tarea «Comando `mas-modelo replay <ruta>`». Nadie crea el subcomando `compare`, y el CSV de calidad (`quality.py`, B) vence a las sáb 20:00.
   - El hito crítico de la demo mínima no se puede cumplir tal como está escrito.
   - El pitch enseña ese mismo comando en el cierre («`uv run mas-modelo compare <ruta>`»).
   - `verificacion.md` detecta el choque y propone el arreglo, pero no lo aplica y lo cuenta como no bloqueante sin explicar por qué.

**Leves**

4. **Leve.** C1, con arrastre a C3 (`CLAUDE.generado.md`, regla 9; `convenciones.md`) y a `verificacion.md` (fila 21, «Sostenida»).
   - Cita del análisis: «el evento es en San Diego (hora del Pacífico) y todas las horas del enunciado son locales».
   - El enunciado no da zona horaria. La afirmación se presenta como hecho, cuando es conocimiento externo o inferencia.
   - La hora del Pacífico es razonable en San Diego, así que no cambia lo que se construye.

5. **Leve.** C1. Cita: «Tecnologías obligatorias o prohibidas: ninguna».
   - El enunciado no habla de prohibiciones; debería quedar como «No especificado».

6. **Leve.** C1. Cita: «Los participantes deben llevar…».
   - El enunciado dice «traen». La frase sube la fuerza de lo que dice el enunciado.

7. **Leve.** C4, `plan.md`, hito «vie 21:00 | Modelo base corriendo en comma four con chestnut», comprobado con «Una latencia medida con chestnut».
   - Depende de `models.py` (B), `device.py` y `bench.py` (C), que vencen a las vie 24:00.
   - `verificacion.md` lo detecta pero no lo corrige.

8. **Leve.** C4. Todo el enfoque depende de que haya un comma four para el equipo.
   - Está marcado como supuesto en la regla 10 y tiene una base razonable en el enunciado («el hardware de comma»).
   - Pero nadie tiene la tarea de preguntarlo, y la medida (C) no tiene repliegue si no hay comma four. La regla 4 además prohíbe código para otros dispositivos.
   - `verificacion.md` propone añadir la pregunta, pero no se añade.

9. **Leve.** C4. A (`compare.py`) y B (`quality.py`) escriben en `salidas/`, cuyo dueño es C.
   - `.env.example`, que exige `convenciones.md`, no tiene dueño.
   - No hay tarea que compruebe que `.gitignore` excluye `.env`, `datos/` y `salidas/`.

10. **Leve.** C5. En «¿Esto puede entrar en openpilot?», quien responde es A.
    - En `equipo.md`, A tiene «Prefiere no hacer: presentar» y «Presenta el pitch o la defensa: no».

11. **Leve.** C5. «código en inglés, listo para proponer» y «cualquier ruta» prometen más de lo que hay.
    - No existe tarea de PR, y solo se prueban 2 rutas.

12. **Leve.** C3 y `verificacion.md` (fila 26). Cita: «Código […] en inglés, para que se pueda proponer a openpilot (… el inglés, por la utilidad para openpilot: decisión)».
    - La decisión no habla de idioma, y la verificación lo da por «Sostenida».

13. **Leve.** C3. `inferencia-chestnut.md` menciona «la GPU del comma four» como opción, sin marcarlo como conocimiento externo.
    - La regla 7 de `CLAUDE.generado.md` da por hecho que se pueden «conseguir» rutas antes de empezar, sin la marca que sí lleva `plan.md`.
    - La tabla de comandos solo lista `uv run mas-modelo`.

14. **Leve.** C3 (seguridad, sin llegar a bloqueante).
    - `reto.md` viene de un agregador no oficial (sslip.io), y ninguna regla dice que su contenido, los logs o las respuestas de la organización que se copian a las reglas (`/respuesta-organizacion`) se traten como datos y no como instrucciones.
    - Lo dejo como leve porque el texto actual del enunciado lo pegó el usuario y está limpio.

15. **Leve.** `verificacion.md`, fila 30.
    - Para sostener «Chestnut se presenta el viernes a las 19:00» cita la ambigüedad 5, que no habla de la hora.

## C6: justificación
En parte. Leyendo solo lo generado, cada persona sabe en qué ficheros escribe, qué contrato expone o consume y qué tiene que tener listo a las vie 19:00 y vie 24:00. A y C podrían empezar a programar enseguida. Lo flojo es el centro del proyecto: nadie define qué es exactamente el «modelo ampliado». Además, la regla inventada de no escribir código de entrenamiento y el repliegue «base con más resolución» empujan a B hacia algo que seguramente no funcione, y eso puede obligar a rehacer el trabajo el sábado. Echo en falta:
- una tarea para el subcomando `compare` y el CSV que exige la demo mínima;
- una pregunta, con dueño, sobre si hay comma four por equipo;
- quitar «lo único que el enunciado exige» de la guía de la demo;
- una definición del ampliado que se pueda probar el viernes.

Sobra parte de la ceremonia de `verificacion.md`: 57 filas que detectan problemas reales y luego no los corrigen, y aun así declaran 0 bloqueantes.