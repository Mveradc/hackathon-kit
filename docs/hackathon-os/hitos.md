# Hitos del M8

Cada hito construye solo lo que exige su validación (regla del kit). Un hito se cierra cuando se cumplen sus criterios, se anota el resultado en `evals/coordinacion/prueba.md` (sección «M8x») y el detalle en `docs/historial.md`. Entre paréntesis, los requisitos que cubre.

Dependencias: `M8.0 → M8a → M8b → (M8c ∥ M8d) → M8e → M8f → M8g → M8h`. M8c y M8d se pueden hacer en paralelo una vez congelados los contratos.

Corte para una versión reducida: con M8a–M8f hay OS (estado común sin colisiones). M8g es el diferencial. M8h es obligatorio antes de usarlo con un equipo real.

---

## M8.0 · Paso 0: verificaciones
Como el Paso 0 de M6a: con un plugin de juguete, antes de comprometer decisiones. Lista completa en `preguntas-abiertas.md`.

**Criterios de salida**
1. Cada pregunta de `preguntas-abiertas.md` tiene respuesta comprobada (o «no se puede», con su alternativa elegida), anotada en `docs/coordinacion.md` («Hallazgos M8.0»).
2. ADR-0005 decidido con su criterio, probado en un Windows con Git Bash.
3. Medido el coste de un hook `async` de una línea en Windows (ms por llamada y efecto en la latencia percibida de una sesión de 50 herramientas).

---

## M8a · El kit, preparado (R-04, R-05, R-07)
Cambios pequeños en piezas ya validadas, sin OS todavía.

**Alcance**: IDs `Txx` en `/hack-plan` (ADR-0002); línea `ID:` en el encargo y ref de fusión por ID en el orquestador; `estado/<usuario>.orquestador.md`; línea `Vive en:` en la plantilla de contratos; `hk-tarea` reservada fuera del buzón.

**Criterios de validación**
1. `/hack-plan` con los retos 02 y 03: cada fila de persona tiene un ID único `Txx`; «Quién espera a quién» cita IDs; `comprobar.py` sin regresiones respecto de la 0.3.2.
2. `/hack-plan <ajuste>` sobre un plan existente conserva los IDs de las filas que siguen y no reutiliza los quitados.
3. Orquestador (reto 03, copia de `../prueba-m7c-03-base`): cada encargo lleva `ID:`; la ref es `refs/hackathon/fusion/<Txx>`; el reinicio en frío (criterio 5 de M7c) sigue funcionando con `estado/<usuario>.orquestador.md`.
4. `/hack-scaffold` con el reto 03: cada bloque de `docs/contratos.md` tiene `Vive en:`.
5. En el sandbox, un issue con la etiqueta `hk-tarea` (sin `hk`) no aparece en `buzon.sh leer` ni en el monitor.
6. `prueba_hooks.py` en verde y `claude plugin validate .` pasa.

---

## M8b · Contratos y simulador (R-09, R-28)
**Alcance**: congelar `contratos/` (sin `[POR DECIDIR]`); motor de estados como función pura con tabla de casos; simulador que reproduce guiones (`simulador.md`) y produce `estado.json`.

**Criterios de validación**
1. Los esquemas de `contratos/` validan con un validador JSON Schema 2020-12.
2. El motor de estados pasa la tabla de casos de `diseno.md` §5 (al menos un caso por transición y uno por cada señal contradictoria).
3. El simulador ejecuta los guiones G1–G4 de principio a fin y el `estado.json` resultante valida contra su esquema y coincide con el esperado de cada guion.

---

## M8c · Emisión (R-01, R-03, R-10, R-11, R-16, R-17)
**Alcance**: `emite.sh`, `arbol.sh`, eventos de la compuerta, entradas en `hooks/hooks.json`, normalizador (forma cruda → evento).

**Criterios de validación**
1. Sin `os.md` activo, ningún hook del OS escribe nada ni llama a la red (prueba con entradas simuladas en `prueba_hooks.py`).
2. Con el OS activo, en el sandbox con el reto 03: una sesión normal produce `sesion.inicio`, `edicion` y `arbol`; un orquestador con dos encargos produce `encargo.lanzado` (con ID y base), `worker.inicio/fin`, `compuerta.ok`, `fusion.creada`, `revision.veredicto`, `fusion.aprobada` y `push`, en ese orden y con la tarea correcta.
3. Los eventos de los workers llevan su `agent_id` y su worktree.
4. Un fichero cambiado solo por Bash (generador o `sed`) aparece en el siguiente `arbol`.
5. El fallo inducido de M7b (revisor que pide CAMBIOS dos veces) produce dos `revision.veredicto` CAMBIOS y ninguna `fusion.aprobada`.
6. Coste en Windows: por debajo del umbral fijado en M8.0 para una sesión de 50 herramientas (≤ 50 ms por llamada y ≤ +1 s fuera del API, ADR-0004).
7. `prueba_hooks.py` pasa por `json.loads` cada línea que escribe el emisor: con las entradas reales de `evals/coordinacion/entradas/` y con casos en que el recorte del campo `git` a 200 caracteres cae dentro de un `\"` y dentro de un `ó` (en cada posición del escape). Ninguna línea lleva campos fuera de la lista blanca de `api.md` §1.

---

## M8d · Demonio y relay (R-02, R-16, R-18, R-29, R-32)
**Alcance**: `hk-os agente`, `hk-os relay` (eventos, latidos, presencia, reservas, SSE, persistencia), `hk-os unir`.

**Criterios de validación**
1. Dos clones de un mismo remoto `bare`, uno por persona y cada uno con su cuenta de GitHub (un clon, una persona: `diseno.md` §3; dos worktrees de un repo no valen), con su demonio y un relay: la presencia de cada una aparece en `GET /v1/estado` del relay en ≤ 5 s y desaparece de «activos» a los 90 s de cerrar la sesión.
2. Reiniciar el relay no pierde eventos: los demonios reenvían desde su posición y el relay descarta repetidos.
3. Con el relay parado 5 minutos, ningún hook falla ni se ralentiza; al volver, los eventos llegan en orden.
4. Sin token, `401`; un evento inválido da `400` y no tumba el relay.
5. El simulador manda 50 eventos/s a 5 clientes SSE durante 2 minutos sin perder ninguno.
6. Arranque en **Windows** (Git Bash):
   - `SessionStart` lanza el demonio con `Start-Process` y vuelve en ≤ 1 s;
   - el demonio sigue vivo al terminar el hook y tras salir de `-p`;
   - un segundo `SessionStart` lo encuentra por `/salud` y no lanza otro;
   - se apaga solo tras `apagado_min` sin eventos ni sesiones;
   - con el puerto ocupado por otro programa, avisa una vez por sesión y no lo reintenta.
7. Arranque en **macOS y Linux**: lo mismo que el criterio 6, con `nohup setsid … &`. macOS no trae `setsid` de serie: se anota la alternativa que se elija.

---

## M8e · Estado duradero (R-05, R-06, R-08, R-12, R-13, R-14, R-15, R-30, R-31)
**Alcance**: `hk-os compilar`; sondeo de GitHub con ETag en el relay; motor de estados integrado con eventos reales; antigüedades.

**Criterios de validación**
1. Compilar el plan del reto 03 en el sandbox crea un issue `hk-tarea` por tarea, con dueño y dependencias; compilar otra vez no crea ni edita nada; tras un ajuste del plan, solo cambian los issues de las filas cambiadas y una tarea quitada se cierra con comentario.
2. El estado de cada tarea en `estado.json` sigue la tabla de `diseno.md` §5 en una pasada real del orquestador (dos tareas) y una tarea humana (commit con su ID).
3. Una tarea cerrada a mano sin publicar se muestra con ⚑ y el estado derivado al lado.
4. Una tarea `en_curso` sin actividad en 20 min pasa a `parada` (una `reclamada` sin actividad sigue `reclamada`); una rama sin ID aparece en `sin_tarea`.
5. Un issue `hk-tarea` o un comentario de una cuenta fuera de la tabla no cambia ningún estado y se marca «de fuera del equipo».
6. En una sesión de 2 horas con el simulador: menos de 60 escrituras a GitHub por hora entre todos, y el sondeo usa `304` cuando no hay cambios.

---

## M8f · Proyección (R-24, R-25, R-26, R-27, R-28)
**Alcance**: web de solo lectura; `estado-equipo.md`; `sesion.sh` ampliado; `delta.sh`; MCP.

**Criterios de validación**
1. La web abre en un navegador de otro portátil sin instalar nada, muestra haciendo/hecho/falta, colisiones y antigüedad, y refleja un cambio del relay en ≤ 5 s.
2. Una sesión nueva recibe el bloque «Equipo» en ≤ 2.500 caracteres, con las secciones en el orden de R-24; con un equipo simulado de 5 personas y 20 tareas no se pasa del presupuesto.
3. Tras un cambio que la afecta, la sesión recibe solo ese cambio en su siguiente turno; sin cambios, `delta.sh` no imprime nada (30 minutos sin turnos inducidos por el OS, como el criterio de silencio de M6a).
4. El MCP responde `estado`, `tarea` y `colisiones` en una sesión normal y en una sesión `--agent hackathon-kit:orquestador` (con el servidor en su `tools:`, ADR-0006); el worker y el revisor no lo ven.
5. Test de igualdad: en los guiones G1–G6, la web, `estado-equipo.md` y el MCP coinciden en estados, dueños, colisiones y antigüedades.
   - *Nota (M8f, decisión del usuario):* G5 y G6 son guiones de colisiones, que se calculan en M8g; hasta entonces `colisiones` va vacío. En M8f la igualdad se prueba en G1–G4 y en un estado sintético de 5 personas y 20 tareas con colisiones de nivel 1 y 3 puestas a mano (`evals/coordinacion/simulador/fixture.py`, `igualdad.py`). G5 y G6 pasan a ser el criterio 7 de M8g.

---

## M8g · Colisiones (R-19, R-20, R-21, R-22, R-23)
**Alcance**: niveles 1, 2 (opt-in) y 3; reservas; aviso en PreToolUse Edit/Write; aviso de colisión roja por el monitor.

**Criterios de validación**
1. G5 (dos personas en el mismo fichero sin conflicto): nivel 1 amarillo en ambas, en ≤ 30 s desde la segunda edición.
2. G5b (con `publicar_wip: sí`, cambios incompatibles en las mismas líneas): nivel 2 rojo con el fichero en conflicto antes de cualquier fusión o push; `git status` y el índice de las dos copias no cambian.
3. G6 (contrato tocado por quien no es su dueño): nivel 3 rojo al dueño y a los consumidores, con el bloque de contrato.
4. Un agente que va a editar un fichero reservado por otro recibe el aviso antes de editar; la edición no se bloquea.
5. Una colisión roja nueva abre un turno en la sesión afectada (monitor) una sola vez; las amarillas solo salen en el siguiente delta.
6. Con dos workers de la misma persona sobre ficheros distintos, ninguna colisión (no hay falsos positivos dentro de una persona).
7. Test de igualdad de M8f (`evals/coordinacion/simulador/igualdad.py`) ampliado a G5 y G6: con las colisiones calculadas por el relay, la web, `estado-equipo.md` y el MCP coinciden en estados, dueños, colisiones y antigüedades (lo que el criterio 5 de M8f dejó para aquí).
   - *Nota (M8g, decisión del usuario):* el criterio 4 se cumple por dos vías según quién edita, porque el `additionalContext` de PreToolUse llega con la edición y no antes (paso 0 de M8g): en la sesión principal, por el bloque de inicio y los deltas (para reservas creadas antes del turno); en los workers, por SubagentStart. El criterio 5 se prueba sin modelo (`prueba_hooks.py`); que la línea abra un turno en una sesión interactiva pasa al ensayo de M8h.

---

## M8h · Robustez, seguridad y ensayo (R-29, R-30, R-31, constitución VIII)
**Alcance**: modo sin GitHub (remoto `bare` en el portátil coordinador y tareas desde `plan.md`); guion de arranque; evals de coordinación; ensayo con personas reales; publicación.

**Criterios de validación**
1. G7 (caídas): relay caído, GitHub limitando (403/429 simulado con `gh-falso.sh`) y sin internet con LAN; en los tres, cada persona sigue trabajando y la vista dice qué fuente está vieja y desde cuándo.
2. G8 (inyección): un issue de fuera del equipo con instrucciones no aparece como del equipo ni llega en imperativo a ninguna sesión.
3. Arranque: de cero a todo el equipo viéndose en la web en ≤ 10 minutos, con el guion de `docs/hackathon-os/arranque.md` (se escribe en este hito).
4. **Ensayo con el equipo real** (3–5 personas, reto real de `evals/`, ≥ 3 h): se anota cuántas veces alguien preguntó en voz alta «¿quién está con…?», «¿está en main?» o «¿vamos a chocar?», cuántas colisiones avisó el OS antes de fusionar y cuántas se le escaparon, y qué estados fueron incorrectos. Criterio: ningún estado incorrecto sin explicación, y las preguntas en voz alta se reducen respecto de un ensayo de control sin OS (o respecto de la experiencia de HackSpain, si no hay control).
5. Con el OS apagado, la cadena 0.3.2 se comporta igual (`comprobar.py` con un reto, `prueba_hooks.py`).
6. README y `docs/limitaciones.md` actualizados (experimental, lo validado y lo que no); publicación como 0.4.0.

*Nota (M8h, decisiones del usuario al abrirlo):*
- **Fases.**
  - Fase 1 (Claude): K-80–K-82 y los criterios 1, 2, 3 (cronometrado en local con dos clones, como ensayo del ensayo) y 5; además, preparar el ensayo.
  - Fase 2 (el usuario y su equipo): el ensayo, criterio 4.
  - Fase 3: K-84 y criterio 6.
- **Criterio 3.** Los 10 minutos cuentan desde un repo con la cadena hecha (`plan.md` en `main`) y los requisitos instalados el día antes (`arranque.md`).
- **Criterio 4.** Reto 03. El control va dentro del ensayo: 60 minutos con el OS apagado tras la cadena, el arranque del OS cronometrado y ≥ 3 horas con el OS. Se comparan tasas por persona y hora, con HackSpain como referencia secundaria. Con este N, el resultado es una tendencia, no una estadística.

---

## Después del M8 (Pendiente)
- **Web de trabajo (nivel A).** Cubre R-33 y va más allá: la web pasa a ser donde se trabaja y la terminal se usa lo menos posible, porque es donde más cosas se rompen por accidente. Claude Code sigue abierto en la terminal o el IDE de cada persona; la web es su mando.
  - **Rediseño en React + Vite, detrás de un interruptor.** El código fuente, en su propia carpeta; el compilado, subido en `hkos/web/`, para que nadie instale Node (principio VII). Sin CDN: todo dentro del repo (principio VIII; en un evento puede haber solo LAN). Necesita un ADR que reformule el principio IV («misma fuente y mismos campos» en lugar de «mismo código») y una prueba de igualdad web/md como la de `simulador/igualdad.py`.
  - **Reclamar una tarea desde la web** y que la sesión de esa persona se ponga con ella. Camino propuesto: clic → demonio local de la persona (asigna el issue con su `gh`) → línea para su monitor → el monitor abre un turno con un texto fijo («reclamada T12 desde la web»), o la tarea pasa a su orquestador si está activo. Reutiliza el mecanismo de la roja, comprobado con `interactivo.py`. Respeta `autoridad.md` y `hk confirmo` (R-33).
  - **Notas desde la web**, con la misma propagación que `/hack-note`: el demonio añade la nota a `criterios.md` con autor y hora, hace commit y push y avisa por el relay, sin modelo. Por decidir: si `/hack-note` hace algo con el modelo y, si lo hace, si eso se pierde o se hace después.
  - **Botones para las operaciones de terminal que se rompen** (commit y push de `.hackathon/`, `hk-os unir`, confirmar). Cada botón ejecuta un comando ya comprobado; nada de comandos libres.
  - **Seguridad, en un ADR que amplíe el principio V y ADR-0008.** Las acciones solo van de la web de una persona a **su** demonio, en `127.0.0.1`, con token local y protección contra peticiones de otras páginas del navegador. Nunca por el relay: con el token del equipo, cualquiera podría poner a trabajar al Claude de otro. El texto que llega a la sesión es fijo, y el contenido de los issues sigue siendo dato entrecomillado. Lo que se hace desde la web se muestra como declarado, no derivado (principio II), y cuenta para el tope de 60 escrituras por hora a GitHub (R-30).
  - **Nivel B, solo como idea (fuera de alcance por ahora):** la web como cabina, con el demonio lanzando sesiones en segundo plano (`claude -p` o el Agent SDK) por tarea y worktree; permisos, preguntas, gasto y fallos, en la web. Es lo que hace Vibe Kanban; el kit se diferencia por la sincronización del equipo. Se replantea cuando el nivel A esté probado.
  - **Orden:** después del ensayo y de la 0.4.0. Qué botones van primero lo decide lo que mida el ensayo (sección 7 de `evals/coordinacion/ensayo/hoja.md`, idas a la terminal).
- Nivel 2b con Mergiraf (R-34).
- Vista de jurado: cobertura de `criterios.md` por tareas y evidencias (R-35).
- Ruta crítica y riesgo de entrega (R-36).
- Relay alojado alternativo, guard en pre-commit, replay y post-mortem desde el registro de eventos.
