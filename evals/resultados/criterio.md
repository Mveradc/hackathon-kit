# Resultados · comprobaciones de criterio C1–C6 (revisor independiente)

2026-10-05. Primera pasada, la del agente revisor. Falta la revisión del usuario. Los informes completos están en `criterio/<reto>.md` y el prompt del revisor, en `criterio/prompt-revisor.md`.

## Montaje

- Una carpeta temporal por reto, fuera del repo, con solo: `enunciado.md` (de `evals/retos/`), `criterios.md` (la sección C1–C6 de la rúbrica) y `salidas/`. En `salidas/` van `hackathon/*.md`, el CLAUDE.md generado (renombrado a `CLAUDE.generado.md`) y `.claude/rules/` (en `reglas/`). Se renombraron para que el `claude -p` del revisor no los cargara como instrucciones propias.
- `claude -p` sin el plugin, con solo `Read`, `Grep` y `Glob`. El prompt pide Pasa/Falla/N/A con evidencia y que busque sobre todo afirmaciones sin base, aunque lleven etiqueta de origen.
- Coste del revisor: 02 0,69 · 03 0,59 · 04 0,67 · 05 0,65 · 06 0,53 USD (3,13 en total), de 2 a 2,5 min por reto.

**De dónde salen las salidas revisadas**
| Reto | Carpeta | Ojo |
|---|---|---|
| 02 | `prueba-m3a` | Salidas del 2026-09-27: anteriores al origen por viñeta de las reglas (2026-10-04) y a la corrección del plan (2026-10-05). Nombres reales anonimizados en el informe |
| 03 | Copia de `prueba-m2b` + plan y pitch generados hoy | No había cadena completa del 03: `prueba-m2b` acaba en el scaffold, y el plan y el pitch de `examples/` salen de cadenas distintas («Consola» y «Radar de cartera»). Escribí un `equipo.md` ficticio, igual que la cabecera del plan de ejemplo (3 personas, C llega el sábado a las 10:00, presenta B), y lancé `/hack-plan` y `/hack-pitch` con los prompts actuales (0,54 + 0,43 USD). En `-p`, `/hack-plan` no puede preguntar antes de editar el CLAUDE.md y devuelve la sección `## Dueños` para pegarla: la pegué a mano. El análisis y el scaffold son de M2b |
| 04 | `prueba-m4-04` | Plan del 2026-10-04, anterior a la corrección del «;» |
| 05 | `prueba-m4-05` | Plan del 2026-10-04, anterior a la corrección del «;» |
| 06 | `prueba-m4-06` | — |

**Artefacto del montaje:** el revisor no recibió `.claude/skills/`, porque no estaba en lo pedido, y en los cinco retos marca que «las guías de pasos no existen». No es un fallo del kit y no cuenta en los patrones. Si C3 tiene que juzgar las guías, en la próxima pasada hay que incluirlas.

**Incidencia:** el primer intento del 03 se lanzó con `--plugin-dir /c/Users/...`. Con `MSYS_NO_PATHCONV=1`, Git Bash no convierte esa ruta, el plugin no se carga y el modelo escribe el plan «a mano» sin avisar más que en el chat. Se descartó. Hay que pasar la ruta como `C:/Users/...`.

## Tabla

| Reto | C1 Análisis | C2 Enfoques | C3 Scaffolding | C4 Plan | C5 Pitch | C6 ¿Empezaría antes? |
|---|---|---|---|---|---|---|
| 02 Facturas (Maisa) | Falla | Falla | Falla | Falla | Falla | Falla |
| 03 X Ray (Embat) | Falla | Falla | Falla | Falla | Falla | Pasa |
| 04 Edge AI (hardware) | Pasa | Pasa | Falla | Falla | Falla | Pasa |
| 05 UTP (sin datos) | Pasa | Pasa | Falla | Falla | Falla | Pasa |
| 06 COMMA_HACK (vago) | Falla | Falla | Falla | Falla | Falla | Pasa |

Una línea por celda:
- **02:** C1 «ERP local obligatorio como fuente», sin base · C2 «créditos de LLM, que el reto no ofrece» · C3 «ESCALAR en la duda» etiquetado «(ambigüedad 1)», que es justo la pregunta abierta · C4 tareas con «;» y sin tarea para el teamId · C5 el bonus «ya implementado» sin tarea en el plan · C6 los comandos no traen `make erp` y el ESCALAR por defecto habría que deshacerlo.
- **03:** C1 «la valoración se centra en el producto» frente a «mismo peso» · C2 «el comprador externo pesa menos», sin base · C3 «Eliminatorio» donde el enunciado dice «Obligatorio» · C4 la demo mínima del sáb 12:00 depende de la web de C, que llega a las 10:00 · C5 «Embat presta o asegura… que hoy no tiene», inventado.
- **04:** C3 «Evaluación 1, hora no especificada», cuando el enunciado da 14:00–20:00 · C4 cuatro tareas en una celda y paso del `modelo.h` imposible · C5 «autonomía medida, no estimada» cuando la tabla la estima; ninguna pregunta sobre la alerta que solo llega a un receptor cercano.
- **05:** C3 reglas con `paths: app/**` que gobiernan `lib/` y `content/` · C4 tareas con «;» y sin dueño para `package.json`/`datos/` · C5 «una prueba real de la carrera» con testimonios ficticios; los miedos «salen del enunciado», pero no salen de él.
- **06:** C1 «openpilot es open source» y «premian una demo en directo» sin marcar · C2 la tabla y el texto no coinciden en B · C3 «filtro eliminatorio (enunciado)» y «MIT (ambigüedad 7)» · C4 ninguna tarea construye el «fork de openpilot» de la decisión · C5 «el cuello es USB, no el cómputo», presupuesto antes de medir.

Comprobé contra los enunciados las afirmaciones clave: «Obligatorio» frente a «eliminatorio» (03 y 06), la hora de la Evaluación 1 (04), el ERP y el ESCALAR (02) y el MIT (06). Lo que dicen los revisores se sostiene. La frase «valora sobre todo el producto» del 03 está en la nota del equipo que trae el fichero del enunciado: el fallo es atribuirla al enunciado oficial, no inventarla.

## Patrones (en 2 o más retos)

1. **La etiqueta de origen respalda algo que su fuente no dice. Sobre todo, se cita una ambigüedad abierta como base de una decisión que la cierra.** 5 de 5.
   - 02: «ESCALAR en la duda (ambigüedad 1)» y «sin reprocesar el lote 1 (análisis; ambigüedad 2)».
   - 03: «60–80 empresas (ambigüedad 2)».
   - 04: «alerta por ESP-NOW (ambigüedad 4)»; «(ambigüedad 9)» en el enfoque C.
   - 05: «librerías solo por npm (ambigüedad 6)»; «(decisión)» sin base en `decision.md`.
   - 06: «licencia MIT (ambigüedad 7)».
   La etiqueta, que se añadió para dar trazabilidad, acaba dando apariencia de respaldo. A4 solo comprueba que la etiqueta exista, no que diga la verdad.

2. **Se endurecen las reglas del jurado: lo obligatorio pasa a «eliminatorio», lo descriptivo a «requisito» y una preferencia a «desempate».** 5 de 5.
   - 02: «ERP obligatorio (enunciado)», «el PDF vale 35 puntos», «cifras medidas» donde el enunciado dice «medid o estimad».
   - 03: «Eliminatorio», «Desempate declarado», «el jurado es hispanohablante».
   - 04: «la IA tiene que ejecutarse en el dispositivo».
   - 05: «Descalifica: reutilizar código», causas de revocación ampliadas.
   - 06: «filtro eliminatorio (enunciado)», «premian una demo en directo».
   Ya estaba en observación en el 06 («filtro eliminatorio»). Ahora se repite.

3. **El pitch da por hecho lo que el plan no construye o lo que aún no se ha medido.** 5 de 5.
   - 02: el bonus «ya implementado».
   - 03: «el monitor avisa solo», cuando es un selector de mes.
   - 04: «autonomía medida», y tareas del pitch sin dueño en el plan.
   - 05: «prueba real», «el informe real se conecta cambiando un tipo».
   - 06: el «fork de openpilot» no está en el plan; «el cuello es USB, no el cómputo».
   Los `[CIFRA]` evitan inventar números, pero no conclusiones.

4. **Sin dueño para carpetas, ficheros o el arranque del repo.** 5 de 5.
   - 02: `salida/` con dos dueños, `src/albertito/` con cinco, y nadie crea el proyecto ejecutable.
   - 03: el `package.json` raíz de `npm run arranca`.
   - 04: los proyectos PlatformIO y `arranca.py`.
   - 05: `package.json`, `datos/` y el comando de arranque.
   - 06: `rutas/` y `resultados/`.
   Lo que crea `/hack-scaffold` (el arranque, la raíz) se queda fuera del reparto de `/hack-plan`.

5. **Hitos o dependencias con horas que no cuadran, o a cargo de quien llega tarde.** 4 de 5.
   - 03: la demo mínima depende de C, que llega 2 h antes. Es el mismo fallo que estaba en observación en el plan del 03; se repite con los prompts actuales.
   - 04: la congelación de la Evaluación 1 la decide C, recién llegada; el `modelo.h` se necesita a las 19:00 y llega a las 19:30.
   - 05: horas de las dependencias que no coinciden con las tablas; las preguntas tienen dueños distintos en dos sitios.
   - 06: «C espera `big.py` de B» no está declarado, y vence cuando B se va.

6. **Las preguntas del jurado no atacan el punto débil principal del enfoque elegido.** 3 de 5.
   - 03: la anticipación puede ser circular, y no se dice por qué paga Embat.
   - 04: la alerta solo llega a un receptor cercano; los falsos negativos.
   - 05: el acompañamiento sin personas.

7. **Contrato nombrado pero sin forma concreta: ni campos ni JSON de muestra.** 4 de 5.
   - 02: los campos de `schemas.py`.
   - 03: no hay JSON de ejemplo ni formato de `salidas/`.
   - 05: no hay esquema mínimo de `lib/types.ts`.
   - 06: falta el tamaño y el formato de `Frame`.
   El revisor lo da como lo que más echaría en falta en C6.

8. **El CLAUDE.md contradice el enunciado o `equipo.md` en fechas y horas.** 3 de 5.
   - 02: «defensa por confirmar» frente a las 11:00 del plan.
   - 03: «entrega no especificada» frente a las 10:00 de `equipo.md`.
   - 04: «Evaluación 1, hora no especificada», cuando el enunciado da 14:00–20:00.
   Causa probable: el scaffold se escribe antes de `equipo.md` y `/hack-plan` solo añade `## Dueños`.

9. **La comparativa de enfoques se sesga o no coincide con el texto.** 4 de 5.
   - 02: fila «Encaje con el perfil del jurado (inferido)», que no es un criterio.
   - 03: «el comprador externo pesa menos».
   - 04: A sale «neutro» en el texto y «medio» en la tabla.
   - 06: B tiene dos valoraciones distintas entre texto y tabla, que ya estaba en observación; se repite.

10. **Conocimiento externo presentado como hecho.** 3 de 5.
    - 02: «Maisa, empresa de IA para operaciones».
    - 03: el nombre de campo `group_id`.
    - 06: «openpilot es open source», que acaba en «MIT»; «el ejemplo oficial de chestnut».

11. **En el pitch, responden preguntas personas marcadas como «no presenta».** 2 de 5 (02 y 05). Puede ser un problema de redacción del campo de `equipo.md` más que del pitch: «presenta» no quiere decir «no puede responder».

**Ya corregido o fuera del kit**
- Tareas con «;» en una celda (02, 04, 05): los tres planes son anteriores a la corrección del 2026-10-05. El plan del 03, generado hoy, no lo tiene. No cuenta como patrón nuevo.
- Las convenciones genéricas («convención del kit»: commits, `.env`) las marca como «sobra» el revisor en 02, 04, 05 y 06. La rúbrica las permite a propósito. Decisión del usuario: se mantienen, y C3 lo aclara.

## Lo que más pesa para la decisión

Los patrones 1, 2 y 3 están en los cinco retos y van en la misma dirección: el kit escribe con más certeza de la que da el enunciado, y las etiquetas de origen lo disimulan en vez de impedirlo. C1 pasa en 04 y 05, pero el endurecimiento reaparece después, en el scaffold y el pitch. Por eso C3 y C5 fallan en todos los retos. C6 pasa en 4 de 5: el revisor cree que el equipo arrancaría antes, y lo que más echa en falta es un contrato con forma concreta y un dueño para el arranque.

---

# Segunda pasada: retos 02 y 06 tras las correcciones (2026-10-05)

## Qué se cambió

- **Etiquetas honestas** (`/hack-analyze`, `/hack-approaches`, `/hack-scaffold` y sus plantillas, `/hack-plan` y `/hack-pitch`): lo decidido sobre una ambigüedad abierta lleva `(supuesto: ambigüedad N, confirmar con la organización)`; lo que aporta el modelo, `(conocimiento externo, verificar)`. Una ambigüedad nunca es la fuente de algo que se da por cierto. A4 lo comprueba: si una etiqueta nombra una ambigüedad, tiene que decir «supuesto» y «confirmar»; si es conocimiento externo, «verificar». Control positivo: las salidas antiguas del 06 fallan ahora en 5 etiquetas, entre ellas «(ambigüedad 7)» en la regla del MIT.
- **Fuerza del enunciado** (`/hack-analyze`, `/hack-approaches`, `/hack-scaffold` y la plantilla del CLAUDE.md): lo obligatorio, lo preferible y el bonus no se endurecen. Solo es «eliminatorio» o «desempate» lo que el enunciado llama así.
- **`/hack-pitch`**: cruza cada cosa que se enseña o se da por construida con `plan.md`. Si no tiene tarea, va como `[SI DA TIEMPO]` o se quita. Los resultados que dependen de medir van como `[CIFRA]`.
- **`/hack-plan`**: todo lo que creó el scaffold tiene dueño (raíz, arranque, `.claude/`, carpetas de datos y salida), y también toda carpeta en la que escribe una tarea.
- **Rúbrica**: C3 aclara que las convenciones genéricas «(convención del kit)» no son fallo. Se añade la distinción entre grave y leve, y C1, C3, C4 y C5 recogen las reglas nuevas.

## Cómo se comparó

- **Línea base:** las salidas de esta mañana (`prueba-m3a` y `prueba-m4-06`), revisadas otra vez con la rúbrica y el prompt nuevos, para comparar con la misma vara. El cambio de vara ya mueve resultados: C6 del 06 pasa de «Pasa» a «Falla (leve)», porque ahora «Pasa» exige cero fallos. Informes: `criterio/*-base.md`.
- **Segunda pasada:** cadena completa en headless en `../prueba-m4-02-v2` y `../prueba-m4-06-v2`, con el mismo enunciado, stack («python con uv, una sola pieza») y `equipo.md` que la primera. Los enfoques salen distintos en cada ejecución, así que elegí el más parecido al de la primera pasada:
  - 02: C, «Equipo de agentes resiliente»; antes había sido B, «Pipeline agéntico».
  - 06: A, «Más modelo en el coche»; antes, «openpilot con más músculo».
  - En `-p`, `/hack-plan` devuelve la sección `## Dueños` sin editar el CLAUDE.md; la pegué a mano en los dos.
  - Informes: `criterio/*-v2.md`.
- **Coste de la cadena:** 02, 521 s y 3,06 USD; 06, 513 s y 2,39 USD. **Revisores:** base 0,68 + 0,50 USD; segunda pasada 0,82 + 0,60 USD.
- **Ojo:** la cadena es otra (análisis, enfoque y plan nuevos), así que los fallos no se corresponden uno a uno. Lo que se puede medir es si desaparecen los **tipos** de fallo corregidos y qué aparece en su lugar.

## Automáticas

| | A1 | A2 | A3 | A4 | A5 |
|---|---|---|---|---|---|
| 02 v2 | Pasa (plan 973 palabras, pitch 735) | Pasa | Pasa | **Falla**: 1 de 36 etiquetas, regla 12 «(enunciado; …: supuesto, ambigüedad 3)», sin «confirmar» y mezclada con «enunciado» | Pasa |
| 06 v2 | Pasa (842, 701) | Pasa | Pasa | Pasa (31 etiquetas) | Pasa |

Etiquetas nuevas en el CLAUDE.md y las reglas: 02, 4 supuestos y 1 conocimiento externo; 06, 8 supuestos y 2 conocimiento externo. `[SI DA TIEMPO]` en el pitch: 02, 1; 06, 2. «Eliminatorio»: 0 en los dos.

## Criterio: base frente a segunda pasada

| | C1 | C2 | C3 | C4 | C5 | C6 | Graves / leves |
|---|---|---|---|---|---|---|---|
| 02 base | grave | leve | grave | grave | grave | leve | 4 / 14 |
| 02 v2 | grave | leve | grave | grave | grave | leve | 3 / 11 |
| 06 base | leve | leve | grave | leve | grave | leve | 3 / 9 |
| 06 v2 | leve | leve | grave | grave | leve | grave | 4 / 13 |

La tabla casi no se mueve. Los fallos que se corrigieron desaparecen, pero aparecen otros graves de otro tipo.

## Los tipos de fallo corregidos

| Patrón | Base | Segunda pasada | Valoración |
|---|---|---|---|
| 1. Ambigüedad citada como fuente | 02: «sin reprocesar el lote 1 (ambigüedad 2)», grave. 06: «MIT (ambigüedad 7)», grave | Ninguna. El revisor del 02: «las ambigüedades van bien marcadas como supuestos» | **Corregido.** Queda 1 etiqueta mal formada en el 02, que A4 detecta |
| 1b. Etiqueta que dice más que su fuente (no ambigüedad) | 02: «ERP obligatorio (enunciado)», grave | 06: «No se escribe código de entrenamiento (decisión)», cuando la decisión solo excluye entrenar «desde cero», **grave**; «no funcionan igual (riesgo típico)», donde el análisis dice «pueden no funcionar», leve; «inglés (decisión)», leve. 02: «reprocesa solo lo afectado (enunciado)», leve; «(análisis: riesgo típico)» sin base, leve | **Sigue.** Ha pasado de las ambigüedades a «(decisión)» y «(análisis)». A4 no puede verlo: comprueba la forma, no la verdad |
| 2. Fuerza endurecida | 02: «ERP obligatorio», grave; «cifras medidas», leve; «ficheros de más = NO APTO», leve. 06: «filtro eliminatorio (enunciado)», grave | 02: «si el PDF falta se pierden esos 35 puntos» (el enunciado dice «puede dejar sin puntos»), leve; «datos obligatorios: … ERP», leve. 06: ninguno | **Mejora:** desaparecen los graves y quedan leves en el 02. La frase de los 35 puntos se repite en las dos pasadas |
| 3. Pitch que promete lo que no se construye | 02: bonus «ya implementado», grave. 06: «fork» sin tarea, grave; «mejor percepción», leve | 02: remite al jurado a «Comparativa en ADRs», pero el ADR no está en el plan, **grave**; «Diagrama» sin tarea, leve. 06: «listo para proponer», «enlace al repo», leve | **Mejora parcial:** el cruce funciona con lo que se enseña en pantalla, pero no con las respuestas a las preguntas, que remiten a documentos que nadie escribe |
| 4. Sin dueño para lo que creó el scaffold | 02: raíz, arranque, `salida/`, `datos/`, leve. 06: `pyproject.toml`, `rutas/`, `resultados/`, leve | 02: la tabla de dueños cubre `pyproject.toml`, el arranque, `.gitignore`, `.claude/`, `estado/`, `salida/`… El único choque, la re-entrega del lote 2 (leve). 06: `src/mas_modelo/` repartido por fichero, `salidas/` escrita por dos personas, leve | **Corregido en lo pedido** (raíz y arranque). Repartir una carpeta por ficheros vuelve a dejar carpetas con dos personas escribiendo. (El revisor del 06 también señala `.env.example` sin dueño, pero ese fichero no existe: es un error del revisor) |

## Graves nuevos en la segunda pasada

Son de tipos que esta corrección no tocaba:
- **06: hito antes de sus dependencias.** «vie 21:00 · Modelo base corriendo en comma four con chestnut», cuando el modelo base y `device.py` vencen a las 24:00. Su repliegue («seguir sin chestnut») puede saltar por un error del calendario. Comprobado en `plan.md`. Es el patrón 5 de la primera pasada (horas que no cuadran), que ya estaba en 4 de 5 retos.
- **06: una inferencia pasa a ser un hecho operativo.** «Hardware de comma, incluido el comma four (inferido)» en el análisis acaba en reglas que lo miden todo en el comma four, sin abrir ninguna ambigüedad ni dar plan B. Las rutas de conducción son el mismo caso: la regla 7 dice que no habrá y el plan las descarga a las 18:00.
- **02: el análisis pierde contenido de la rúbrica.** «Plan para nuevos tipos de archivo», «emails, imágenes o Excel», «versiones» y «trabajo pendiente» no están en el análisis, y por eso faltan en las reglas, el plan y el pitch. **No es nuevo:** el análisis de `prueba-m3a` tampoco lo tenía, y el revisor de la primera pasada ya lo marcó en C5. Esta vez lo pone en C1, como grave.

## Repetidos en las dos pasadas, aún sin corregir

- Las tablas de enfoques no coinciden con el texto: 02 v2, 06 v2 y 06 base (patrón 9).
- Responde preguntas del jurado quien está marcado como «no presenta»: 02 y 06 v2 (patrón 11).
- Las preguntas del jurado no atacan el punto débil reconocido en la decisión: 02 v2 y 06 v2 (patrón 6).
- El reparto choca con los perfiles de `equipo.md`: 02 en las dos pasadas.

## Conclusión

- **Lo pedido funciona:**
  - No queda ninguna ambigüedad citada como fuente, y A4 detecta la única etiqueta mal formada.
  - Desaparece «eliminatorio».
  - El pitch usa `[SI DA TIEMPO]`.
  - La raíz y el arranque tienen dueño.
- **El número de fallos graves no baja**, por dos motivos:
  - El tipo de fallo de fondo, «escribir con más certeza de la que da la fuente», se ha desplazado de «(ambigüedad N)» a «(decisión)», «(análisis)» y «(inferido)» convertido en hecho.
  - Asoman fallos de calendario y de cobertura de la rúbrica que ya existían.
- **Candidatos para la siguiente ronda**, si los ves bien:
  - que lo `(inferido)` del análisis que sostiene el enfoque se convierta en ambigüedad o en supuesto al bajar al scaffold;
  - que `/hack-plan` compruebe que ningún hito vence antes que sus dependencias;
  - que `/hack-pitch` cruce también las respuestas con el plan;
  - que `/hack-analyze` copie en «Cómo se evalúa» lo que pide cada criterio, no solo su peso.

---

# Tercera pasada: `/hack-check` y criterio de cierre (2026-10-06)

## Qué se cambió

- **Estrategia:** no hay reglas nuevas en los prompts. Se añade `/hack-check` (`skills/hack-check/SKILL.md`), que se lanza al final de la cadena y escribe `.hackathon/verificacion.md`:
  - cada afirmación del CLAUDE.md, las reglas, el plan y el pitch, con la frase literal que la sostiene, o rebajada a supuesto o conocimiento externo, o quitada;
  - la fuerza de las palabras;
  - los `(inferido)` convertidos en hechos;
  - los hitos que vencen antes que sus dependencias (solo informe);
  - las referencias sin tarea (en el pitch, `[SI DA TIEMPO]`);
  - los bloqueantes de entrega;
  - la cobertura de la rúbrica (solo informe).

  Pregunta antes de aplicar; con `/hack-check aplicar`, aplica sin preguntar. Las cuatro propuestas de la segunda pasada: las tres primeras las cubre el check (pasos 3, 4 y 5) y la cuarta pasa a ser su paso 7 (cobertura), en lugar de una regla en `/hack-analyze`.
- **Rúbrica:**
  - A1 acepta de 2 a 10 viñetas por regla.
  - A6 incluye `/hack-check`.
  - **A7**: las citas de `verificacion.md` tienen que ser literales. Probado con una cita alterada, que da fallo.
  - C6 se contesta Sí / En parte / No.
  - Nueva definición de **bloqueante** (seguridad o descalificación).
  - Nueva sección «Cierre de M4».
  - La pasada interactiva cronometrada incluye `/hack-check`.
- **Revisor:** recibe `verificacion.md`, marca los bloqueantes y contesta C6 con Sí / En parte / No.

## Montaje

- **02 y 06:** la cadena de la segunda pasada (`prueba-m4-0X-v2`), revisada antes y después de `/hack-check aplicar` sobre una copia (`prueba-m4-0X-check`). Así se aísla el efecto del check.
- **03, 04 y 05:** cadena completa con el kit actual en `prueba-m4-0X-v2`, eligiendo A en los tres, como en la primera pasada:
  - stacks: 03, «motor en Python con uv y FastAPI, web en React con Vite»; 04 y 05, los de entonces;
  - `equipo.md` de entonces; en el 03, el ficticio de la primera pasada de C1–C6.
  - En `-p`, `## Dueños` se pegó a mano.
- **Incidencia:** se agotó el límite de gasto a mitad de la noche. Los checks del 03 y el 04 ya habían aplicado los cambios y escrito el informe (solo se cortó el mensaje final). El pitch del 05 estaba completo y su check se relanzó.
- **Coste:**

  | Reto | Cadena | Revisores |
  |---|---|---|
  | 03 | 816 s, 3,71 USD | 0,87 USD |
  | 04 | 836 s, 3,63 USD | 0,83 USD |
  | 05 | 1.071 s, 4,56 USD | 0,83 USD |
  | 02 | `/hack-check`: 244 s, 1,33 USD | antes y después: 0,77 + 1,03 USD |
  | 06 | `/hack-check`: 226 s, 1,09 USD | antes y después: 0,62 + 0,70 USD |

## Automáticas (después del check)

| | A1 | A2 | A3 | A4 | A5 | A7 |
|---|---|---|---|---|---|---|
| 02 | Pasa | — | Pasa | Falla: regla 12, etiqueta mixta «(enunciado; …: supuesto, ambigüedad 3)» sin «confirmar»; el check la dio por buena | Pasa | Pasa (69 citas) |
| 03 | Pasa (1.035 palabras) | **Falla**: el arranque anuncia `http://127.0.0.1:8000`, que da 404; `/api/hola` y la web sí responden | Pasa | Falla: una viñeta de `web-demo.md` sin etiqueta válida | Pasa | Pasa (61) |
| 04 | Pasa | Pasa | Pasa | Falla: «(decisión, marcada inferido; … es la ambigüedad 2)», etiqueta mixta | Pasa | Pasa (48) |
| 05 | Pasa (1.093) | Pasa | Pasa | Pasa | Pasa | Pasa (60) |
| 06 | Pasa | — | Pasa | Pasa | Pasa | Pasa (45) |

- **A7:** pasa en los cinco. Las citas del check son literales.
- **A4:** en tres retos aparecen etiquetas mixtas («enunciado» o «decisión» mezcladas con una ambigüedad), y el check no corrige su formato.

## Criterio

| Reto | C1 | C2 | C3 | C4 | C5 | C6 | Graves / leves | Bloqueantes |
|---|---|---|---|---|---|---|---|---|
| 02 antes del check | grave | leve | grave | grave | grave | En parte | 4 / 16 | 0 |
| 02 después | grave | leve | leve | grave | grave | En parte | 4 / 11 | 0 |
| 06 antes del check | leve | leve | grave | grave | grave | En parte | 1 / 11 | 0 |
| 06 después | leve | Pasa | grave | grave | leve | En parte | 3 / 12 | 1 |
| 03 | grave | leve | grave | grave | grave | En parte | 6 / 11 | 1 (dudoso) |
| 04 | grave | leve | leve | grave | leve | En parte | 2 / 13 | 1 |
| 05 | leve | leve | grave | grave | grave | En parte | 3 / 13 | 2 |

**Ruido del revisor.** La misma cadena del 06 (v2) dio 4 graves en la segunda pasada y 1 grave en esta. Con una sola revisión por reto, las diferencias de 1–2 graves no significan nada. Lo que se repite entre revisiones sí.

## Bloqueantes, comprobados contra el enunciado

| Reto | Bloqueante | ¿Se sostiene? | ¿Lo vio el check? |
|---|---|---|---|
| 03 | Seguridad: ninguna regla dice que el texto libre del banco (contraparte, concepto) se trate como dato y nunca como orden, aunque el análisis lo avisa | **Dudoso:** el análisis lo condiciona a «si se usa un LLM», y el enfoque elegido no usa ninguno | No: no revisa omisiones de riesgos |
| 04 | Descalificación: el enunciado tiene «Team & member verification» el 4 oct a las 11:00, y C (en `equipo.md`) no llega hasta el 5. El análisis omite la verificación y el plan no la trata | Sí | No: el paso 6 solo mira entregables, fecha y formato de entrega |
| 05 | Descalificación: «consentimiento informado, firmado previo al inicio del concurso» sin tarea ni dueño | Sí | No (mismo motivo) |
| 05 | Descalificación: «No estar conectado a todas las fechas pactadas», y el plan acepta una ausencia de C el sábado sin tratarla como riesgo de descalificación | Sí | No (mismo motivo) |
| 06 | Descalificación: la guía `.claude/skills/demo-domingo` dice «la demo es lo único que el enunciado exige», cuando el enunciado no dice qué se entrega (ambigüedad) | Sí | Lo citó, pero no lo corrigió: las guías no están en su alcance |
| 02 | Ninguno marcado. El check sí marcó como bloqueantes dos omisiones (teamId y GitHub; el contenido obligatorio del PDF), y el revisor las rebajó a leves porque el check las deja a la vista | — | Sí, informadas |

## Efecto de `/hack-check` (02 y 06, misma cadena antes y después)

- **Lo que hace bien:**
  - Las citas son literales (A7).
  - Rebaja a supuesto las afirmaciones sin respaldo: 7 y 14 supuestos en el 02 y el 06.
  - Encuentra los choques de calendario que ya conocíamos (el hito del vie 21:00 del 06), el comma four sin pregunta, el MIT y los huecos de cobertura del 02.
  - El revisor rebaja a leve lo que el check deja a la vista del equipo (el calendario del 06, los bloqueantes de entrega del 02).
- **Lo que no cambia:**
  - Los graves de fondo siguen: el reparto contra los perfiles (02), un enfoque técnicamente dudoso (06, «modelo ampliado sin entrenar») y la cobertura de la rúbrica (02).
  - El check los informa, pero no son afirmaciones que se puedan rebajar.
- **Lo que no ve:**
  - Las guías de `.claude/skills/`.
  - Las causas de descalificación que no son entrega: consentimiento, asistencia, verificación de miembros.
  - El formato de las etiquetas mixtas.

## Cierre de M4: **no se cumple**

- **Bloqueantes:** 4 confirmados (04, 05 ×2, 06) y 1 dudoso (03). El criterio pide cero.
- **C6 = Sí:** 0 de 5. Todos «En parte». El criterio pide al menos 3.

**Por qué C6 se queda en «En parte»** (lo que el revisor echa en falta en más de un reto):
- contratos con nombre pero sin campos: 02, 03, 05 y 06;
- choques de calendario que el check informa pero no resuelve: 03, 04 y 06;
- tesis o reglas que se contradicen: 05;
- reparto contra los perfiles: 02;
- enfoque técnicamente dudoso: 06.

## Propuestas para que decidas (sin aplicar)

1. **Ampliar el paso 6 de `/hack-check` a todas las causas de descalificación del enunciado**, no solo a la entrega: consentimientos, asistencia, verificación de miembros, plazos de inscripción. Cada una se coteja con el plan (tarea con dueño) y con las ausencias de `equipo.md`. Cubriría 3 de los 4 bloqueantes confirmados (04 y 05).
2. **Meter las guías de `.claude/skills/` en el alcance del paso 1** de `/hack-check`. Cubriría el bloqueante del 06.
3. **Que `/hack-check` aplique, con confirmación, las propuestas de calendario** (mover un hito o adelantar una tarea) en vez de solo informarlas. Hoy el equipo tiene que hacerlo a mano, y el revisor sigue viendo el choque.
4. **Contratos con forma:** es lo que más pesa en C6 (4 de 5). No se resuelve verificando: haría falta que `/hack-plan` o `/hack-scaffold` dejen un esqueleto de contrato (campos y ejemplo). Eso es una regla nueva en un prompt, o código en el scaffold, así que **lo tienes que decidir tú**.
5. **Etiquetas mixtas** (A4 en 02, 03 y 04): que el paso 1 del check normalice también el formato de la etiqueta. Es barato.
6. **Ruido del revisor:** para decidir el cierre, dos revisiones por reto, quedándose con lo que coincide.

**Limitaciones candidatas para el README** (se repiten y no son bloqueantes; queda pendiente redactarlas cuando se cumpla el cierre):
- la tabla de enfoques no coincide con el texto (02, 03, 04 y 06);
- responden preguntas del jurado personas que no presentan (02, 05 y 06);
- las preguntas del jurado no atacan el punto débil (02, 03 y 06);
- las estimaciones de horas no tienen base (02 y 05);
- el análisis endurece la fuerza en detalles leves (02, 03 y 05);
- el reparto choca con los perfiles (02).

## Pasada interactiva cronometrada (la haces tú)

1. `claude --plugin-dir .` en una carpeta vacía (por ejemplo, `../prueba-m4-int`) y comprobar que `/hack` muestra **seis** comandos.
2. Cronómetro desde `/hack-analyze <reto>` (reto 02 o 06), separando el tiempo de los comandos del de las personas. Pasos: leer el análisis → `/hack-approaches` y elegir → `/hack-scaffold` (dar permiso en `.claude/`) → rellenar `equipo.md` → `/hack-plan` (aceptar `## Dueños`) → `/hack-pitch` → **`/hack-check`** (leer el informe y elegir aplicar, revisar uno a uno o solo informe).
3. Anotar dos tiempos: hasta poder programar (fin de `/hack-plan`) y total (fin de `/hack-check`). Después, `/cost`.

# Cuarta pasada: decisiones del usuario y última ronda (2026-10-10)

## Decisiones

- **Propuestas aplicadas** (1, 2, 3, 4 y 5 de la tercera pasada):
  1. El paso 6 de `/hack-check` busca **todas las condiciones del enunciado que pueden descalificar**, no solo la entrega: inscripción, verificación de miembros, consentimientos, asistencia, composición del equipo. Coteja cada una con el plan (tarea con dueño) y con las ausencias de `equipo.md`. Si lo que falta es una fila del plan, la propone y la aplica solo con confirmación.
  2. El paso 1 revisa también lo que afirman del reto las guías de `.claude/skills/` y `docs/contratos.md`.
  3. Los choques de calendario del paso 4 llevan un cambio concreto (mover el hito, adelantar la tarea o pasarla a alguien disponible) que se aplica con confirmación, uno a uno; el argumento `aplicar` cuenta como confirmación. Nunca mueve hitos que fija el enunciado.
  4. **Contratos con forma, como salida del scaffold:** `/hack-scaffold` genera `docs/contratos.md` (plantilla nueva), con un bloque por contrato (entrega, datos de entrada, interfaces entre piezas), una tabla de campos (tipo, obligatorio, valores, origen) y un ejemplo mínimo válido, sacados del análisis. A1 comprueba que existe y que cada contrato tiene tabla y ejemplo.
  5. El paso 1 normaliza el formato de las etiquetas: una sola etiqueta por viñeta, de las formas permitidas; las mixtas se reescriben según el veredicto.
- **Propuesta 6** (dos revisiones por reto): no se aplica. La sustituye el nuevo criterio de cierre.
- **Revisor:** recibe también las guías (`salidas/guias/`) y `salidas/contratos.md`; un bloqueante tiene que poder ocurrir con el enfoque elegido y, si es de descalificación, citar la frase del enunciado que da la consecuencia.
- **Nuevo criterio de cierre** (en `evals/rubrica.md`, con sus razones): 0 bloqueantes, C6 nunca «No» y confirmación en la pasada interactiva con una persona real.

## El bloqueante dudoso del 03: error del revisor

El revisor marcó como bloqueante de seguridad que ninguna regla trate como dato el texto libre del banco. Contra el enunciado:
- El enunciado **no exige un LLM**. El agente aparece solo como una idea entre otras, en una «lista abierta»: «**Agente de recomendaciones** | Un agente que lee el rastro y dice qué hacer esta semana…».
- El análisis condiciona el riesgo: «si se usa un LLM o un agente (idea «Agente de recomendaciones») para leer esos textos libres».
- El enfoque elegido (A, radar de cartera) no usa ningún LLM: «un score sencillo e interpretable con suavizado temporal»; y deja fuera las «recomendaciones de acción».

No es un bloqueante: el riesgo no puede ocurrir con el enfoque elegido. Por eso el prompt del revisor dice ahora que un bloqueante tiene que poder ocurrir con el enfoque elegido.

## Última ronda (2026-10-10)

**Montaje.** El tope era de 15 USD y se gastaron 14,47.
- **04, 05 y 06:** se reutilizaron el análisis, los enfoques, la decisión y `equipo.md` de la v2 (los prompts de esos pasos no han cambiado). Desde `/hack-scaffold` se relanzó todo con el kit actual en `../prueba-m4-0X-v3`, incluido `/hack-check aplicar` y, después, una revisión por reto.
- **03:** para no pasarse del tope, solo el check nuevo y el revisor, sobre una copia de la cadena v2. Por eso no tiene `docs/contratos.md`.
- **Incidencia:** se agotó el límite de gasto mensual después del scaffold del 06. Se reanudó cuando se renovó.
- **Informes:** `criterio/0X-v4.md`.

**Coste:**

| Reto | Cadena | Revisor |
|---|---|---|
| 04 | 3,30 USD | 0,93 USD |
| 05 | 3,61 USD | 0,88 USD |
| 06 | 2,60 USD | 0,83 USD |
| 03 | solo el check, 1,45 USD | 0,89 USD |

| Reto | C1 | C2 | C3 | C4 | C5 | C6 | Bloqueantes (revisor) | Bloqueantes contra el enunciado | Automáticas que fallan |
|---|---|---|---|---|---|---|---|---|---|
| 03 | grave | leve | grave | grave | grave | En parte | 0 | 0 | — (no se pasaron: cadena v2) |
| 04 | leve | Pasa | leve | grave | leve | En parte | 0 | 0 | A4 (una CIFRA sin fila), A5 (frase de convenciones igual a la del ejemplo del 03), A7 (una cita de cobertura no literal) |
| 05 | leve | leve | grave | grave | leve | En parte | 3 | **2** | A1 (plan de 1.192 palabras, con 5 personas) |
| 06 | leve | Pasa | grave | leve | leve | En parte | 0 | 0 | A4 (una CIFRA sin fila) |

**Lo que han cambiado las propuestas:**
- **Bloqueantes del 04 y el 06, resueltos:**
  - 04: el check encontró la verificación de miembros del 4 oct y añadió el hito al plan. La ausencia de C la deja al equipo, y el revisor no la cuenta como bloqueante porque el enunciado no le da consecuencia.
  - 06: la guía ya no da por exigido lo que el enunciado no dice.
- **Bloqueantes del 05, detectados pero no resueltos:** el check encontró el consentimiento y la asistencia y añadió filas al plan. Pero:
  - **Consentimiento** (se sostiene): «firmado previo al inicio del concurso». El check lo puso a la hora exacta del inicio del desarrollo (vie 19:00), cuando la agenda empieza con la inducción del martes 9. «Antes del inicio» tenía que ser antes de la inducción, o preguntar cuándo empieza el concurso.
  - **Trabajo previo al evento** (se sostiene, y **es del kit**): «El código, diseño y otras piezas de trabajo deben ser creados durante el evento». El scaffold y `docs/contratos.md` (con el modelo de datos del producto) se generan antes. El check lo vio y rebajó la regla a supuesto, pero `convenciones.md` sigue prohibiéndolo con la etiqueta «(enunciado)» y nadie tiene la tarea de rehacerlo si la organización dice que no.
  - **Asistencia** (dudoso): «No estar conectado a todas las fechas pactadas». La pregunta a la organización ya está en el plan; falta un plan B.
- **Contratos (propuesta 4):** el revisor los valora en el 04 («Contratos, dueños y carpetas claros») y en el 05 («contratos de datos con ejemplo»). Aun así, se echan en falta los contratos de las interfaces internas: la API del 05 y la firma de `infer` del 06. El 03, sin contratos, vuelve a citarlos como lo que más falta.
- **C6:** «En parte» en los cuatro y ningún «No».

## Cierre de M4 (criterio del 2026-10-10): **no se cumple**

- **C6 nunca «No»:** se cumple.
- **0 bloqueantes:** no se cumple, por el 05:
  1. el consentimiento, fijado a la hora del inicio y no antes;
  2. el kit genera código y diseño antes del evento, cuando las bases lo prohíben.
- **Pasada interactiva con una persona real:** pendiente.

**Propuestas para que decidas (sin aplicar):**
1. **Trabajo previo prohibido.** Si el análisis recoge que el trabajo tiene que crearse durante el evento, `/hack-scaffold` avisa antes de generar y propone lanzarse al empezar el evento, o generar solo el contexto (CLAUDE.md, reglas, guías) sin código ni contratos de producto. Es un cambio en el prompt del scaffold, que afecta al kit en sí y no a un reto.
2. **«Antes de X» en el check:** cuando una condición vence «antes del inicio» y el enunciado no fija ese inicio, el check pone la fila antes del primer acto de la agenda (aquí, la inducción) y añade la pregunta a la organización. No la pone a la misma hora.
3. **Contratos de las interfaces internas:** que `docs/contratos.md` incluya siempre la interfaz entre las piezas que crea el scaffold (endpoints, firmas), aunque sea con origen `decisión` o `TODO`. Hoy el prompt ya lo pide («cada interfaz entre ellas») y se cumple a medias: en observación.

# Quinta pasada: reto 05 tras las decisiones del 2026-10-10

## Qué se cambió

- **Trabajo previo prohibido.** Si el análisis recoge que el trabajo se crea durante el evento:
  - `/hack-scaffold` (nuevo paso 0) lo trata como bloqueante: avisa antes de generar, recomienda lanzar scaffold, plan y pitch al empezar el evento y solo genera si el usuario confirma que el evento ha empezado (en `-p`, si lo dicen los argumentos). Deja constancia en «Fechas» del CLAUDE.md.
  - `/hack-check` lo comprueba en el paso 6.
  - Generar solo el contexto no vale.
- **Plazos «antes del inicio» sin fecha:** la fila va antes del primer acto de la agenda y se añade la pregunta a la organización (paso 6 del check).
- **A1** mide el plan por persona: como máximo 10 filas por persona. El total de palabras solo se anota.
- **En observación:** contratos internos; A7 del 04; A4 y A5.

## Resultado (`../prueba-m4-05-v4`, 5,29 USD)

- **Sin confirmar que el evento ha empezado**, `/hack-scaffold` paró sin crear nada, citando la frase de las bases (0,25 USD).
- **Con la confirmación**, la cadena completa, el check y el revisor:
  - A1–A7 pasan; el plan tiene de 6 a 8 filas por persona;
  - C6 «En parte»;
  - el revisor marca 3 bloqueantes (informe en `criterio/05-v5.md`).

Los 3 bloqueantes, contrastados con las bases:

| Bloqueante del revisor | ¿Se sostiene? |
|---|---|
| Código creado antes del evento: el CLAUDE.md dice «generado el 2026-10-10 con el evento ya empezado» y el desarrollo fue en junio | **No es del kit.** Es efecto de probar en octubre un reto de junio: con un uso real, la fecha cae dentro del evento. Lo del kit está resuelto: sin confirmación, no genera. Queda una mejora menor: el check solo comprueba que la fecha no sea anterior al inicio, no que caiga dentro del evento |
| Ausencia de C el sábado de 09:00 a 15:00, durante «Desarrollo de Ideas», con «No estar conectado a todas las fechas pactadas» y «Todos los miembros inscritos deben participar durante el evento» | **Se sostiene a medias.** El check lo detecta y lo pone arriba, y el plan pregunta a la organización antes de la ausencia. Falta la fila de repliegue («C se conecta aunque no trabaje») por si la respuesta es sí: el check lo deja como «decide el equipo» |
| Nadie verifica los requisitos de inscripción de los miembros («que no cumplan con los requisitos de inscripción»: matrícula, ciclo…) | **Se sostiene.** El check lo detecta, pero no propone la fila del plan, aunque su paso 6 lo pide («Si lo que falta es una tarea o un hito en el plan, propón la fila concreta») |

**Lo que se ha resuelto:**
- El consentimiento va ahora antes de la inducción, con la pregunta sobre cuándo empieza el concurso.
- El scaffold ya no genera antes del evento sin confirmación.

## Cierre de M4: **sigue sin cumplirse**

Quedan 1 bloqueante sostenido (requisitos de los miembros) y 1 a medias (ausencia de C sin repliegue). En los dos, el check detecta el problema pero lo deja al equipo en lugar de proponer la fila del plan. No se ha escrito el README.

**Propuestas para que decidas (sin aplicar):**
1. En el paso 6 del check, **toda condición de descalificación sin tarea con dueño recibe una fila propuesta**, sin excepción («decide el equipo» no basta). Cuando la causa sea una ausencia, la fila es el repliegue: «<persona> se conecta aunque no trabaje», hasta que la organización responda.
2. En el paso 6, la fecha de generación del repositorio tiene que caer **dentro** del evento, no solo después de su inicio.

# Sexta pasada: check y revisor del 05 con las dos propuestas (2026-10-10)

## Qué se cambió

- **`/hack-check`, paso 6:**
  - Toda condición de descalificación sin tarea recibe siempre una fila propuesta en el plan. Si la causa es una ausencia, la fila es el plan B: «<persona> se conecta aunque no trabaje, hasta que responda la organización».
  - La fecha de generación tiene que caer **dentro** del evento. Si el análisis no da las fechas, el check las pregunta.
- **Fecha simulada, solo en el arnés:** `evals/fecha_simulada.py` cambia la fecha de generación en el CLAUDE.md por una dentro del evento y la deja en `.m4/fecha-simulada.txt`. El revisor la toma como fecha de hoy. Ningún comando del kit la lee.

## Resultado

En `../prueba-m4-05-v5`, una copia de la v4 con la fecha simulada «2026-06-12 a las 19:30 (UTC-5)»: check, 1,06 USD; revisor, 0,88 USD. Informe en `criterio/05-v6.md`.

- **A1–A7:** pasan (A2 no se repitió: el código no cambia).
- **C6:** En parte. El revisor dice que sería «Sí» con los contratos completos y la ausencia de C resuelta con la organización.
- **Bloqueantes:**
  - El trabajo previo desaparece.
  - Los requisitos de los miembros tienen ahora una fila con dueño.
  - **Queda 1, según el revisor:** la fila de plan B de C. Contrastado con el enunciado, **se sostiene a medias**:
    - **Correcto:** la fila es exactamente la que se decidió («C se conecta aunque no trabaje, hasta que responda la organización») y la pregunta a la organización va antes de la ausencia (vie 20:00).
    - **Falla en el kit:** el plan se contradice. «Descansos» y «Dependencias» siguen diciendo «C ausente hasta 15:00», y la fila no tiene cómo confirmar con C, antes de la ausencia, que puede conectarse. El check añadió la fila sin actualizar el resto del plan, y `verificacion.md` la marca «Aplicado: Sí».
    - **Lo que queda es del equipo:** si C puede conectarse depende de C, no del kit.

## Cierre: no se da por cumplido

La condición era «si sale sin bloqueantes», y el revisor cuenta 1. La parte que es del kit es pequeña (la contradicción interna del plan); la otra es una decisión del equipo. Lo decide el usuario.

Borrador de las limitaciones: pasado al README tras la decisión del usuario (ver abajo).

## Decisión del usuario: el bloqueante restante del 05 pasa a leve

- **Razonamiento.** El riesgo de descalificación («No estar conectado a todas las fechas pactadas») está cubierto: hay una fila de plan B con dueño en la franja de la ausencia («C se conecta aunque no trabaje, hasta que responda la organización») y la pregunta a la organización vence antes de la ausencia. Lo que queda es una incoherencia interna del plan («Descansos» y «Dependencias» siguen diciendo «ausente») y eso no puede descalificar al equipo. Por eso es un fallo leve. Si C puede conectarse depende del equipo, no del kit.
- **Pendiente** (anotado en el CLAUDE.md): que el check, al añadir una fila, actualice el resto del plan.
- **Cierre de M4, parte automática: cumplida.**
  - 0 bloqueantes en la última ronda (03, 04 y 06 en la cuarta pasada; 05 en la sexta, con esta reclasificación).
  - C6 nunca «No» (En parte en los cuatro).
  - Las limitaciones que se repiten están en el README.
  - Falta la confirmación de una persona real en la pasada interactiva cronometrada.
