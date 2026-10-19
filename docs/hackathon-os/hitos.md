# Hitos del M8

Cada hito construye solo lo que exige su validación (regla del kit). Un hito se cierra cuando se cumplen sus criterios, se anota el resultado en `evals/coordinacion/prueba.md` (sección «M8x») y el detalle en `docs/historial.md`. Entre paréntesis, los requisitos que cubre.

Dependencias: `M8.0 → M8a → M8b → (M8c ∥ M8d) → M8e → M8f → M8g → M8h (fase 1) → M9a → M8h (fases 2 y 3)` (M9a se adelanta al ensayo por decisión del usuario, 2026-10-17; el ensayo, la fase 2 de M8h, queda aplazado sin fecha por decisión del usuario, 2026-10-18). M10 (0.5.0, abierto el 2026-10-19) va detrás de M9a y no espera al ensayo. M8c y M8d se pueden hacer en paralelo una vez congelados los contratos.

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

*Nota (M8h, decisión del usuario, 2026-10-18):* **el ensayo (fase 2, criterio 4, K-83) queda aplazado sin fecha**: ahora no se puede coordinar al equipo. Lo siguiente es cerrar M9a (decidir el borrador de contratos del PR #13, K-99 y anotar el cierre). Al cerrarlo, el usuario decide si la 0.4.0 sale sin ensayo (con el criterio 4 pendiente y dicho en `docs/limitaciones.md`) o espera a que se haga.

*Nota (M8h, decisión del usuario, 2026-10-18, tras cerrar M9a):* **la 0.4.0 sale sin ensayo.** Fase 3 hecha con el criterio 4 pendiente: K-84 (README, `docs/limitaciones.md`, CHANGELOG y `plugin.json` en 0.4.0) y el criterio 5, ya validado en la fase 1. El ensayo sigue aplazado y no bloquea la 0.5.0; cuando se haga, se apunta aquí. M8h queda abierto solo por él.

---

## M9a · Web de trabajo, nivel A (R-33; ADR-0009, ADR-0010, ADR-0011)
Abierto el 2026-10-17 por decisión del usuario: se construye **antes** de la fase 2 de M8h (el ensayo), para ensayar con ella. M8h sigue abierto: su fase 2 (ensayo) y su fase 3 (K-84, criterio 6, 0.4.0) van detrás de M9a. Plan aprobado: `C:/Users/mvera/.claude/plans/streamed-sparking-teacup.md`. Diseño: `docs/hackathon-os/diseno-web/` (sistema y cuatro pantallas).

**Alcance (cerrado por el usuario)**
- Web en React + Vite detrás de `web_nueva:` en `os.md`. El fuente, en `hkos/web-src/`; el compilado, subido en `hkos/web/nueva/`. Nadie instala Node (VII); sin CDN y con las fuentes dentro del repo (VIII). Con el interruptor apagado, todo sigue como hoy y la web clásica del relay es el respaldo.
- La sirve el demonio de cada persona en `127.0.0.1` (ADR-0010). Cuatro vistas sobre el `estado.json` actual: red (grafo del equipo), tablero por persona, cabina personal (por defecto) y servicios. Respeta el sistema de diseño (tokens, componentes, color por procedencia, latidos).
- La animación dice la verdad: un paquete por arista solo con un evento real del relay (SSE `eventos`); lo viejo, gris, discontinuo y quieto; `prefers-reduced-motion` respetado.
- `.hackathon/servicios.md` (ADR-0011): lo genera `/hack-scaffold`; el demonio del dueño comprueba puerto y salud; el resultado de la Prueba de cada conexión se lee cuando alguien la corre (el OS no la ejecuta). Los desajustes salen en la vista; un cambio hecho fuera del portátil del dueño sale «declarado, sin confirmar».
- Dos acciones, y solo dos: **Anotar** (el demonio añade la nota a `criterios.md` de `origin/main` con autor y hora, commit y push, sin modelo y sin tocar la copia de la persona) y **Reclamar** (asigna el issue con el `gh` de la persona y deja una línea para su monitor, que abre un turno con texto fijo).
- Fuera: confirmar desde la web, botones de commit y push, nivel B. Lo que las pantallas enseñan y queda fuera se pinta como texto, no como botón.

**Criterios de validación**
1. Con `web_nueva: no`, todo como hoy: `hkos/pruebas`, `prueba_hooks.py`, `igualdad.py`, `robustez.py` y `colisiones_vivo.py` en verde; el demonio da 404 en `/`, el relay no emite `eventos` y `prueba.sh` no escribe; `comprobar.py` sin regresiones con un reto, sin coordinación.
2. Sin Node ni CDN para quien la usa: `web_vivo.py` carga todo desde el demonio y no encuentra ninguna URL externa en `hkos/web/nueva/`; el CI recompila y el diff con lo subido sale vacío; `claude plugin validate .` pasa.
3. Cuatro vistas, cabina por defecto: Vitest pinta G1–G6 y G12, y cada estado, dueño, colisión, antigüedad y desajuste sale en el DOM igual que en la vista; `igualdad.py` (vista del demonio, `estado-equipo.md` y MCP) coincide también en servicios (ADR-0009).
4. La animación dice la verdad: con temporizadores falsos, sin eventos no hay paquetes; N ids dan N paquetes y un id repetido, ninguno; con `reduced-motion`, ninguno; presencia vieja o relay caído dejan la arista `stale` y quieta; sin nada del demonio en `max(umbral_viejo_s, 40 s)`, toda la página sale «sin conexión», gris y quieta, con la hora del último dato. En vivo (`web_vivo.py`), 5 eventos del simulador llegan a la web del demonio en ≤ 2 s y ninguno más en 60 s.
5. Servicios (`servicios_vivo.py`, remoto `bare` y dos clones), cada caso en ≤ 30 s: puerto declarado sin respuesta; fichero fuera de todo servicio; Prueba corrida y fallando (con comando, procedencia y antigüedad); fila cambiada por otra persona, «declarado por @x, sin confirmar», y confirmada al pasarla su dueño desde Propuestas; comando de Prueba cambiado, sin confirmar; sha reescrito, sin confirmar y nunca confirmado; fila añadida por un worker de su dueño, confirmada; Salud que no es una ruta (`http://…`, `/../`), desajuste y sin consulta.
6. Seguridad (`acciones_seguridad.py`): un token en la query no vale (401); una acción sin token da 401; con `Host` u `Origin` ajenos, 403; como formulario `text/plain`, 415; `OPTIONS` no da cabeceras CORS; el relay no tiene rutas de acción y el demonio solo escucha en `127.0.0.1`.
7. Anotar (dos clones y el sandbox): la nota llega a `criterios.md` de `origin/main` con autor, hora y «Anotado por»; `git status` y el índice de la persona no cambian; la otra persona la ve en novedades en ≤ 60 s; sin coautoría; una entrada con salto de línea o `#` sale saneada; con un push rechazado (otra nota subida antes), reintenta una vez sobre el `origin/main` nuevo y las dos notas quedan; si vuelve a fallar, la web lo dice y la copia de la persona no cambia.
8. Reclamar (sandbox, @hk-persona-b): el issue queda asignado con su `gh` y la tarea sale «reclamada · declarado (web)»; una tarea de otro dueño se rechaza; sin GitHub, solo el evento; la sesión interactiva de esa persona recibe **un** turno con el texto fijo (prueba interactiva del usuario).
9. Cadena: `/hack-scaffold` con el reto 03 y la coordinación genera un `servicios.md` que `hkos/servicios.py` lee sin errores de formato; el `autoridad.md` de `/hack-plan` lleva la regla de servicios; `comprobar.py` sin regresiones.

*Nota (M9a, decisiones del usuario al abrirlo y al revisar los ADR, 2026-10-17):*
- **Fases**, cada una enseñada al usuario antes de seguir: K-90 y K-91 (Paso 0, ADR y contratos); K-92–K-97 (servidor y datos); K-98 (web); K-99 (validación con modelo y en sandbox).
- **Servicios iniciales:** las filas del commit que crea `servicios.md` cuentan como «de /hack-scaffold», confirmadas (ADR-0011).
- **Precisiones de la revisión** (en los ADR):
  - el token nunca va en la query; la página lo quita de la URL al leerlo y lo guarda solo en memoria; `/v1/stream` se lee con `fetch` (ADR-0010);
  - si el push de Anotar se rechaza, reintenta una vez sobre el `origin/main` nuevo y, si falla, lo dice en la web, sin merge en la copia (ADR-0010; criterio 7);
  - sin datos del demonio en `max(umbral_viejo_s, 40 s)` (el doble del `ping` de 20 s como mínimo), toda la página pasa a «sin conexión» (ADR-0009; criterio 4);
  - Salud solo admite una ruta que empieza por `/` (ADR-0011; criterio 5).
- **Orden de recorte si el 28 de octubre va con retraso:**
  1. Primero, la confirmación por commits: `servicios.md` se pinta todo como «declarado», y los desajustes de puerto, salud y contrato siguen. Sale del criterio 5 la parte de confirmación.
  2. Después, la vista de tablero: quedan la cabina, la red y los servicios.

  **No se recortan:** el respaldo de la web clásica, la seguridad de ADR-0010 y las dos acciones.

*Estado: **cerrado el 2026-10-18.***
- Criterios 1, 5, 7, 8 y 9 validados en K-99 (PR #36, `evals/coordinacion/prueba.md`, «M9a, K-99» y «M9a, cierre»); 2, 3, 4 y 6, con las pruebas sin modelo y el CI (K-94, K-98, `acciones_seguridad.py`, `web_vivo.py`).
- El criterio 5 cumplió el tiempo tras el PR #37 (el relay lee `origin/main` a los 2 s de un push; máximo 18,8 s en dos pasadas). El turno de Reclamar en una sesión interactiva lo comprobó el usuario: uno solo, con el texto fijo.
- Contratos y ADR al día con el código (PR #13, con las 21 decisiones del usuario, y PR #35).
- Siguiente: M8h, fase 3 (K-84 y la 0.4.0). El ensayo (fase 2) sigue aplazado; si la 0.4.0 sale sin él lo decide el usuario.

*Estado (2026-10-18, antes del cierre):*
- **Revisiones independientes y arreglos.** Siete revisiones de solo lectura (issues #2, #6, #10, #15, #18, #23 y #27) y sus arreglos, en los PR #7 a #29. Ninguna alta abierta. De la última (#27) quedan medias: un Anotar cuyo push entra después del plazo puede duplicar la nota, `web.token` se regenera si falla la reescritura de uno no privado, `os.replace` falla en Windows con el fichero abierto por otro proceso, y el último `servicios` bueno no sale marcado como viejo (esto último, decisión de contratos).
- **Contratos y ADR al día con el código:** borrador en el PR #13, con su tabla de decisiones pendientes. Lo decide el usuario antes de cerrar M9a.
- **Siguiente:** decidir el PR #13 → K-99 → anotar el cierre de M9a en `evals/coordinacion/prueba.md` y `docs/historial.md`.

*Estado (2026-10-17):*
- **K-95 hecha (PR #8), salvo lo de K-99.** Los criterios 7 y 8 están cubiertos sin sandbox (`test_acciones.py` y `prueba_hooks.py`); falta su parte en `Mveradc/hk-sandbox` con @hk-persona-b y la prueba interactiva del turno, que son de K-99.
- **Revisión independiente (issue #2):** los hallazgos 1, 4, 5, 6, 9 y 13 quedan resueltos por el PR #7. El detalle, en `tareas.md`.

---

## M10 · Vista de jurado y ruta crítica (R-35, R-36; ADR-0012, ADR-0013)
Abierto el 2026-10-19 por decisión del usuario, para la 0.5.0: decididas las tablas de ADR-0012 (jurado) y ADR-0013 (ruta crítica), ya aceptados, y las preguntas del Paso 0 (K-100, issue #41). Contratos en `api.md` §11 (K-101). Mismo método que M9a: Paso 0, ADR y contratos, servidor y datos, web, validación con modelo. Diseño de las pantallas: PR #43 (`docs/hackathon-os/diseno-web/`), ajustado a estas decisiones (margen contra la entrega, franja en lugar de horas declaradas).

**Alcance (cerrado por el usuario)**
- Dos vistas detrás de dos interruptores en `os.md`, `vista_jurado:` y `ruta_critica:`, apagados por defecto e independientes de `web_nueva:` (ADR-0012, decisión 8A). Salen en la web de trabajo, en `estado-equipo.md` (una línea por vista) y en el MCP (el detalle). Apagadas, todo como en la 0.4.0 (constitución I).
- **Vista de jurado (R-35):** por cada nota de `criterios.md` (solo las notas, no la rúbrica), qué tarea la declara con la etiqueta `(criterios: …)` del plan, qué evidencia derivada tiene y su cobertura: `sin_tarea`, `ambigua`, `en_pitch` («recogida en el pitch (declarado)»), `declarada` o `cubierta`, además de «corregida por». Cubierta = todas sus tareas publicadas o cerradas; la Prueba se enseña como evidencia, no es condición. Nunca «cubierta» porque algo lo declare.
- **Ruta crítica (R-36):** con `depende_de`, la cadena de cada persona (orden del plan), los `Hasta` resueltos, la franja del plan, la entrega de `equipo.md`, los descansos y el ritmo medido por persona, qué está atrasado y qué arrastra (hechos, desde el minuto uno) y si se llega a la entrega (estimación con rango, veredicto de cuatro valores y base). Con menos de 3 tareas medidas por persona, lo dice («n de 3») y no da hora.
- Todo se calcula en `proyeccion.vista` (bloques `jurado` y `ruta`), a partir de lo que el relay pone en `estado.json`. La web solo pinta (ADR-0009).
- Fuera: la rúbrica de `analisis.md`, botones, confirmar desde la web, cualquier acción nueva, replay y nivel B (siguen en «Después del M8»). Tampoco se replanifica sola: la ruta avisa y el equipo decide con `/hack-plan`.

**Criterios de validación**
1. Con los interruptores apagados (o sin ellos en `os.md`), todo como hoy: `hkos/pruebas`, `prueba_hooks.py`, `igualdad.py` (G1–G6 y G12), `robustez.py`, `colisiones_vivo.py` y `web_vivo.py` en verde. `estado.json`, la vista y `estado-equipo.md` salen byte a byte como en la 0.4.0 con los mismos datos. Las cuatro combinaciones de los dos interruptores, probadas. `comprobar.py` sin regresiones con un reto, sin coordinación.
2. **G13 (jurado), sin modelo:** guion nuevo del simulador con notas en `criterios.md` (una que corrige a otra, dos en el mismo minuto, una de fuerza `dato` que solo afecta al pitch y está en `pitch.md`, una con texto imperativo) y tareas con la etiqueta `(criterios: …)` en «Cómo se comprueba» que avanzan hasta `publicada`. Para cada paso esperado, la cobertura de cada nota, sus tareas, su evidencia (sha y `observado_en`) y el orden (sin cubrir por fuerza y luego por hora) coinciden con el esperado. Ninguna nota sale `cubierta` sin todas sus tareas hechas. Una tarea `cerrada` a mano deja la nota `declarada`, con ⚑. Una cita con dos notas sale `ambigua`; con «· quién», casa con una. Una publicada que vuelve a `en_curso` deja la nota `cubierta` con «trabajo nuevo desde». Una Prueba que falla se enseña y no cambia la cobertura.
3. **G14 (ruta), sin modelo:** guion largo con el plan del reto 03 (28 tareas, 39 h, con commits, descansos y un ajuste del plan) y el reloj simulado:
   - antes de 3 tareas medidas de cada persona con tareas abiertas, «sin estimación · pocos datos: <n> personas» (el «n de 3» de cada persona, en la vista; tras congelar, 2026-10-19, M10, ajuste 3 de ADR-0013) y ninguna hora prevista;
   - un plazo vencido sale como hecho, rojo, con lo que arrastra (por dependencias y por orden del plan);
   - con 3 o más, la estimación lleva rango, margen contra la entrega, base y veredicto (`a_tiempo`, `justo` o `no_llega`, los dos últimos en ámbar);
   - sin `Entrega:` en `equipo.md`, «sin hora de entrega»; con dos horas en esa línea, las dos, sin elegir; con la fila de Hitos distinta, la discrepancia al lado **y la estimación sigue**; con «(confirmar)», estimación marcada «(confirmar)»; con un ciclo, el ciclo;
   - una tarea «Si …» o `[SI DA TIEMPO]` sale fuera de la entrega; un `Hasta` que no se resuelve, «sin plazo», nunca «a tiempo»;
   - la noche de los Descansos no hunde el ritmo ni saca «sin señales»; una persona sin señales fuera de ellos sale «sin señales desde HH:MM», no en riesgo por lentitud;
   - con el relay caído, la estimación sale vieja con la antigüedad de su dato más viejo.
4. **Igualdad (ADR-0009, con la nota de M10):** `igualdad.py` coincide en G1–G6, G12, G13 y G14: los bloques `jurado` y `ruta` enteros entre la vista del demonio y el MCP, y la línea de `## Jurado y ruta` de `estado-equipo.md` con el `resumen` de cada bloque. Vitest pinta G13 y G14 (y la vista de ejemplo de `api.md` §11.6), y cada campo sale en el DOM con el mismo texto. El CI recompila y el diff con lo subido sale vacío. Ninguna URL externa en `hkos/web/nueva/`.
5. **Honestidad** (tablas de casos de `hkos/jurado.py` y `hkos/ruta.py`):
   - ninguna estimación sin la palabra «estimación», su base y un rango; nunca una sola hora;
   - con menos de 3 tareas medidas de alguna persona con tareas abiertas, ninguna hora prevista: «n de 3»;
   - una tarea sin plazo sale «sin plazo», nunca «a tiempo»;
   - rojo solo para hechos (plazo pasado); «no llega», ámbar;
   - lo declarado (plazos, franjas, orden del plan, entrega, hitos, descansos, enlaces, pitch, cierres a mano) sale como declarado, con su procedencia;
   - el texto de las notas sale entrecomillado y saneado, con autor y papel (constitución V).
6. **Presupuesto y silencio** (R-24, R-25, R-25b, X):
   - con 5 personas, 20 tareas y 15 notas, el bloque de inicio no pasa de 2.500 caracteres (la sección `## Jurado y ruta` son dos líneas);
   - un cambio de cobertura (firma `jurado:`) o de veredicto (firma `ruta:`) da un delta de ≤ 600 caracteres;
   - G10 ampliado: 30 minutos con el reloj corriendo, sin cambios de veredicto ni de cobertura, no inyectan nada (que la hora estimada, el margen o un hecho cambien sin cambiar el veredicto no cuenta).
7. **Como K-99, con modelo y en el sandbox** (`Mveradc/hk-sandbox`, @hk-persona-b, o remoto `bare` y dos clones):
   - `/hack-scaffold` y `/hack-plan` con el reto 03 y la coordinación activa: el `CLAUDE.md` recuerda `Txx ·` en los commits y el plan trae `Hasta` que se resuelven y «## Descansos» en el formato que se lee;
   - dos notas anotadas desde la web y enlazadas con `/hack-check aplicar` (etiqueta `(criterios: …)` en el plan);
   - una tarea publicada con su ID: la nota pasa a `cubierta` en la web de las dos personas en ≤ 60 s;
   - la ruta del plan real, con sus plazos y su entrega;
   - una sesión de Claude Code pregunta por MCP «¿qué criterio no cubrimos?» y «¿qué pone en riesgo la entrega?» y responde con lo que dice la vista, con su procedencia y sin añadir nada (se comprueba contra la vista);
   - `comprobar.py` sin regresiones. Resultados en `evals/coordinacion/prueba.md` («M10»).

*Nota (M10, decisiones del usuario, 2026-10-19):*
- **Jurado (ADR-0012):** J1A solo las notas de `criterios.md`; J2A clave derivada (hash) en el relay, y las personas citan por «fecha hora · quién»; J3A etiqueta `(criterios: <fecha hora>)` al final de «Cómo se comprueba» en la fila del plan, declarada; J4A cubierta = todas sus tareas publicadas o cerradas, con la Prueba como evidencia y no como condición; J5B «recogida en el pitch (declarado)»; J6B sigue cubierta, con «trabajo nuevo desde»; J7B una línea de resumen en `estado-equipo.md` y el detalle en el MCP y la web, con nota en ADR-0009; J8A `vista_jurado:` y `ruta_critica:` en `os.md`.
- **Ruta (ADR-0013):** R1A manda `Entrega:` de `equipo.md`; las discrepancias con Hitos y con notas `dato` se enseñan al lado, sin elegir y sin quitar la estimación (sin estimación solo si falta `Entrega:`, no se lee, trae dos horas o no se resuelve; con «(confirmar)», estimación marcada así); R2A `Hasta` resuelto con `Inicio:` y la zona de `equipo.md`, y si no, «sin plazo», nunca «a tiempo»; R3B `depende_de` y la cadena de cada persona; R4A franja derivada del plan, sin columna Horas; R5A ritmo por persona desde 3 tareas hechas; R6A rango, veredicto de 4 valores y base; R7A con pocos datos, solo hechos y «n de 3»; R8B todas menos «Si…» y `[SI DA TIEMPO]`; R9A leer «## Descansos»; R10A solo un delta, al cambiar el veredicto; R11C recordar `Txx ·` en el `CLAUDE.md` generado y decir «sin señales», no «va lenta».
- **Diseño:** el margen se mide contra la entrega (la congelación es un hito, sin previsión propia); «no llega» es ámbar y el rojo, solo para hechos (un plazo pasado); el umbral de «sin cifra» es 3, fijo en el contrato (`base.minimo`); las notas sin cubrir, por fuerza y luego por hora.
- **Validación sin datos reales** (#41, pregunta 12; constitución XI): guiones largos del simulador (G13, G14) y el sandbox (criterio 7) para cerrar el hito; el ensayo con un equipo, después, revisa el 3 y los umbrales del veredicto. Así se dice en `docs/limitaciones.md`.
- **Requisitos:** ninguna decisión cambia R-35 ni R-36 (solo notas; con ritmo real).
- **Fases**, cada una enseñada al usuario antes de seguir:
  - K-100 (Paso 0: las medidas que quedan) y K-101 (ADR y contratos, en el PR #42);
  - servidor y datos, en dos tandas de tres terminales en paralelo, sin rutas compartidas: K-102 ∥ K-103 ∥ K-104 y, después, K-105 ∥ K-106 ∥ K-107. K-106 es la web: empieza con la vista de ejemplo de `api.md` §11.6 y cierra con las vistas de K-105;
  - K-108 (validación con modelo y en el sandbox).
- **Orden de recorte si va con retraso** (la fecha la pone el usuario):
  1. Primero, el ritmo: la ruta se queda en hechos (atrasadas, lo que arrastran, cadena por dependencias y por persona), siempre «sin estimación». R-36 queda parcial, y se dice. Salen del criterio 3 las viñetas de la estimación.
  2. Después, la Prueba como evidencia en el jurado (`tareas[].conexiones`).
  3. Después, las vistas propias en la web: jurado y ruta quedan como secciones de la cabina.

  **No se recortan:** el apagado sin coste, la igualdad de ADR-0009, la honestidad (con pocos datos lo dice; nunca «cubierta» porque algo lo declare; rojo solo para hechos) y la constitución V para las notas.

---

## Después del M8 (Pendiente)
- **Web de trabajo (nivel A).** La primera parte es M9a (arriba): React + Vite, cuatro vistas, `servicios.md`, Anotar y Reclamar. Queda para después:
  - **Botones para las operaciones de terminal que se rompen** (commit y push de `.hackathon/`, `hk-os unir`, confirmar). Cada botón ejecuta un comando ya comprobado; nada de comandos libres.
  - **Confirmar desde la web** (lo que hoy es `hk confirmo` o pasar una fila de Propuestas en `servicios.md`), con las reglas de seguridad de ADR-0010.
  - **El resultado de la Prueba desde CI** (ADR-0011: en M9a solo se ve lo que corre una sesión de Claude Code).
  - **Que Reclamar pase la tarea al orquestador** si está activo (en M9a, el turno lo abre el monitor de la sesión).
  - **Nivel B, solo como idea (fuera de alcance por ahora):** la web como cabina, con el demonio lanzando sesiones en segundo plano (`claude -p` o el Agent SDK) por tarea y worktree; permisos, preguntas, gasto y fallos, en la web. Es lo que hace Vibe Kanban; el kit se diferencia por la sincronización del equipo. Se replantea cuando el nivel A esté probado.
  - **Orden:** después del ensayo y de la 0.4.0. Qué botones van primero lo decide lo que mida el ensayo (sección 7 de `evals/coordinacion/ensayo/hoja.md`, idas a la terminal), que se hace ya con la web de M9a.
- Nivel 2b con Mergiraf (R-34).
- Vista de jurado: cobertura de `criterios.md` por tareas y evidencias (R-35). En M10 (arriba).
- Ruta crítica y riesgo de entrega (R-36). En M10 (arriba).
- Relay alojado alternativo, guard en pre-commit, replay y post-mortem desde el registro de eventos.
