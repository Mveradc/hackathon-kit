# Revisor C1–C6 · 06-commahack · segunda pasada

Cadena nueva (`prueba-m4-06-v2`) tras las correcciones del 2026-10-05, con la rúbrica y el prompt nuevos. Comparación en `../criterio.md`.

## Resultado
| # | Resultado | Evidencia |
|---|---|---|
| C1 | Falla (leve) | `analisis.md`: «todas las horas del enunciado son locales» se da como hecho, y el enunciado no lo dice |
| C2 | Falla (leve) | `enfoques.md`: C puntúa «Utilidad para openpilot: **bajo**» en el texto y «bajo (openpilot) / alto (chestnut)» en la tabla |
| C3 | Falla (grave) | `inferencia-chestnut.md`: «No se escribe código de entrenamiento […] (decisión)». La decisión solo excluye «entrenar un modelo desde cero» |
| C4 | Falla (grave) | `plan.md`: hito «vie 21:00 · Modelo base corriendo en comma four con chestnut», pero el modelo base (B) y `bench.py` (C) se entregan «vie 24:00» |
| C5 | Falla (leve) | `pitch.md`: «¿Esto puede entrar en openpilot? \| A», y `equipo.md` dice que A no presenta y prefiere no hacerlo |
| C6 | Falla (grave) | Todo el material da por hecho que hay un comma four para el equipo, rutas con «trayectoria real» y un modelo «ampliado sin entrenar» que mejora al base, y nada de eso está en el enunciado |

## Fallos encontrados

### Graves

1. **Grave · C3 (se arrastra a C4, C5 y C6) · `reglas/inferencia-chestnut.md`, `plan.md`, `pitch.md`.**
   - **Qué dice:** «No se escribe código de entrenamiento: el modelo ampliado se obtiene a partir de modelos que ya existen […] (decisión)». En el plan pasa a «Variante ampliada (más resolución o más frames), sin entrenar» y en el pitch a «(más resolución o frames, sin entrenar)».
   - **Qué dice la fuente:** `decision.md` solo deja fuera «entrenar un modelo desde cero». No prohíbe ajustar un modelo existente (fine-tuning). La etiqueta «(decisión)» amplía lo que se decidió.
   - **Por qué importa:** un modelo de conducción ya entrenado no acepta sin reentrenar más resolución ni más contexto temporal (es conocimiento técnico externo, pero es el núcleo del enfoque). El equipo puede pasar el sábado construyendo un «ampliado» que no corre o que da peor resultado. El pitch también daría por supuestos «casos donde el ampliado acierta y el base no» que quizá no existan.

2. **Grave · C3 y C4 (y C5) · `CLAUDE.generado.md`, reglas, `plan.md`, `pitch.md`.**
   - **Qué dice:** todo se mide y se demuestra «en el comma four». Ejemplos: la regla 10 del CLAUDE.md («Las medidas de rendimiento se toman en el comma four»), `replay-y-metricas.md` («La latencia se mide por frame en el comma four») y las tareas de C en el plan.
   - **Qué dice el enunciado:** la organización pone «el hardware de comma». No dice que haya un comma four por equipo. El análisis lo marca «(inferido)», pero no abre ninguna ambigüedad: la 5 pregunta por GPUs y chestnuts, no por el comma four.
   - **Por qué importa:** algo inferido pasa a ser un hecho del que dependen el enfoque, las reglas y todos los hitos de medida. Si no hay comma four disponible, no hay plan B salvo en la demo final.

3. **Grave · C4 · `plan.md`.**
   - **Qué dice:** el hito «vie 21:00 · Modelo base corriendo en comma four con chestnut · Una latencia medida con chestnut», a cargo de C.
   - **El problema:** depende de «Cargar el modelo de conducción de openpilot» (B, hasta vie 24:00) y de `bench.py` (C, hasta vie 24:00). El hito vence antes que sus dependencias.
   - **Por qué importa:** el repliegue («Seguir sin chestnut») puede saltar a las 21:00 por un error del calendario, no porque chestnut falle. El equipo podría abandonar la pieza central sin motivo.

4. **Grave · C4 y C3 · `plan.md`, `CLAUDE.generado.md` regla 7.**
   - **Qué dice:** la regla 7 da por hecho que «no habrá rutas disponibles durante el evento» y que las rutas «se consiguen y se guardan en `datos/` antes de empezar a programar». El plan, en cambio, pone «Descargar 2 rutas de comma a `datos/rutas/`» entre las 18:00 y las 19:00, es decir, ya en el evento, y pregunta la ambigüedad 4 a las 18:30.
   - **El problema:** nadie dice de dónde salen las rutas. Además, «Todos esperan a A» y no hay repliegue si no se consiguen.
   - **Por qué importa:** sin rutas no hay replay, comparativa ni demo.

### Leves

5. **Leve · C1 · `analisis.md`.** «todas las horas del enunciado son locales» se presenta como hecho. Es una inferencia razonable, pero el enunciado no lo dice. El dato pasa a la regla 9 del CLAUDE.md y a `convenciones.md`.

6. **Leve · C1 · `analisis.md`.** «el toolchain de openpilot pueden no funcionar igual en Windows o macOS» es conocimiento externo sin marcar, dentro de un «riesgo típico».

7. **Leve · C1 · `analisis.md`.** «Que aporte a openpilot» aparece como rasgo de un proyecto ganador. Se apoya en una frase que el propio análisis interpreta como criterio de admisión (ambigüedad 9). Además, la sección «Qué distinguiría a un proyecto ganador» es inferida entera y no lo marca.

8. **Leve · C2 · `enfoques.md`.** Para el enfoque C, el texto dice «Utilidad: bajo» y la tabla «bajo (openpilot) / alto (chestnut)». Es una incoherencia menor entre tabla y texto.

9. **Leve · C3 · `CLAUDE.generado.md` regla 10 y `replay-y-metricas.md`.** El análisis dice que los drivers «pueden no funcionar igual»; la regla lo convierte en «no funcionan igual en Windows ni en macOS (análisis: riesgo típico)». La etiqueta refuerza lo que dice la fuente. Además, el motivo real de medir en el comma four es la decisión, no el riesgo.

10. **Leve · C3 · `reglas/convenciones.md`.** «el inglés, por la utilidad para openpilot: decisión»: `decision.md` no dice nada del idioma («Matices del equipo: Ninguno»).

11. **Leve · C3 · `CLAUDE.generado.md` regla 6 e `inferencia-chestnut.md`.** La regla exige que todo lo traído de antes tenga «una alternativa hecha durante el evento». El enfoque parte del modelo de openpilot ya existente, que no puede rehacerse en el evento si no se entrena. Es una regla imposible de cumplir. La respuesta del pitch («Lo traído y su alternativa están en el README») se apoya en ella.

12. **Leve · C3 · `plan.md`.** Cita las guías `/montar-chestnut` y `/respuesta-organizacion`, que no están en el material revisado. No se puede comprobar que existan ni que cubran esos momentos.

13. **Leve · C4 · `plan.md`.** Hay problemas de dueños:
    - `src/mas_modelo/` se reparte «un dueño por fichero», así que la carpeta no tiene un solo dueño.
    - `compare.py` (A) escribe el mp4 en `salidas/`, que es de C.
    - No se dice dónde escribe `quality.py` su CSV.
    - `.env.example` y la raíz del repo no tienen dueño.

14. **Leve · C4 · `plan.md`.** Entre las 18:00 y las 19:00, A tiene que preguntar a la organización, descargar 2 rutas y definir `Frame`. Es un margen mínimo para el hito de contratos.

15. **Leve · C5 · `pitch.md`.** A responde una pregunta del jurado, aunque `equipo.md` dice «Presenta el pitch o la defensa: no».

16. **Leve · C5 · `pitch.md`.** Las preguntas probables del jurado no atacan el punto más débil del enfoque: cómo mejora un modelo sin reentrenar, o qué pasa si el ampliado es peor. Además, «trayectoria real del log» es conocimiento externo sin marcar. Este fallo también afecta a `plan.md` y a `replay-y-metricas.md`.

17. **Leve · C5 · `pitch.md`.** Hay frases que prometen más de lo que hay:
    - «código en inglés, listo para proponer», cuando el PR va como [SI DA TIEMPO].
    - «enlace al repo», cuando la publicación depende de las ambigüedades 2 y 8.

## C6: justificación
En parte sí. Cada persona tiene ficheros, contratos (`Frame`, `load_model`/`run`, fila de métricas) y comprobaciones concretas. Las dependencias usan un modelo falso para no bloquear a nadie, y las ambigüedades tienen dueño y hora. Las cifras están bien protegidas con [CIFRA].

Pero en la primera hora el equipo tropezaría con tres cosas que el material da por resueltas y no lo están:
- De dónde salen las rutas.
- Si hay un comma four para el equipo.
- Si un modelo «ampliado sin entrenar» puede existir.

La tercera puede obligar a deshacer el trabajo del sábado. El hito de las 21:00 es imposible con el propio calendario y puede hacer que C abandone chestnut antes de tiempo.

Echaría en falta:
- Una fuente concreta de rutas con repliegue.
- Una pregunta a la organización sobre el comma four.
- Que la decisión diga si se permite el fine-tuning.
- Las guías de pasos citadas.

Sobran la regla 6, que no se puede cumplir, y las etiquetas que atribuyen al análisis o a la decisión más de lo que dicen.