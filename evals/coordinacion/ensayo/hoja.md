# Hoja de observación del ensayo (M8h, criterio 4)

Para imprimir o rellenar en el portátil. Una hoja por ensayo; la rellena la persona observadora y cada persona apunta sus propias preguntas en la tabla 1 (o se las dice a quien observa). Usad la hora del reloj de la pared o la del relay, siempre la misma. **En `prueba.md` va anonimizada** (Persona A, B…): aquí podéis poner nombres. **En el ensayo realista** no hay bloque 1: todas las filas llevan «2» en la columna de bloque y la fila «1 · control» de los recuentos se queda vacía.

## Cabecera
| Campo | Valor |
|---|---|
| Fecha | |
| Variante | completo (con control) / realista (sin control) |
| Reto | 03 (Embat) / 07 (GA2MODEL) / otro: |
| Web | nueva (`web_nueva: sí`, cada persona la suya con `hk-os web`) / solo la clásica del relay. Pantalla común con la del relay: sí / no |
| Personas (nombre → letra) | A: · B: · C: · D: · E: |
| Quién coordina (relay) | |
| Quién observa | |
| Bloque 0 · cadena del kit | de __:__ a __:__ → ___ min (en el realista, cronometrado; cada comando: analyze __ · approaches __ · scaffold __ · plan __) |
| Bloque 1 · **control, OS apagado** (60 min; no hay en el realista) | de __:__ a __:__ |
| Arranque del OS (criterio 3) | de __:__ a __:__ → ___ min (todos en la web del relay a las __:__; cada persona con su web nueva abierta: A __:__ · B __:__ · C __:__ · D __:__ · E __:__) |
| Bloque 2 · **con el OS** (≥ 3 h; en el realista, lo que dure el trabajo) | de __:__ a __:__ |
| Desfase de reloj de cada portátil (lo dice `hk-os unir`) | A: ___ s · B: ___ s · C: ___ s · D: ___ s · E: ___ s |

## 1. Preguntas en voz alta
Una fila cada vez que alguien pregunta en voz alta (o por el chat del equipo) algo que el OS debería contestar. Tipos: **Q** = «¿quién está con…?», **M** = «¿esto ya está en main?», **C** = «¿vamos a chocar?» / «¿quién toca este fichero?», **E** = otra pregunta de estado («¿qué falta?», «¿en qué estás?»).

| Bloque (1/2) | Hora | Quién pregunta | Tipo (Q/M/C/E) | Pregunta, en pocas palabras | ¿Lo decía el OS? (sí/no/no sé) |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

Recuento (lo rellena quien observa al final):

| Bloque | Minutos | Personas | Q | M | C | E | Total | Por persona y hora |
|---|---|---|---|---|---|---|---|---|
| 1 · control | | | | | | | | |
| 2 · con OS | | | | | | | | |

## 2. Colisiones que el OS avisó antes de fusionar o subir (solo bloque 2)
| Hora | Nivel (1 amarillo / 2 rojo / 3 contrato / reserva) | Ficheros o contrato | Personas | ¿Qué hicisteis? (hablar, esperar, nada) | ¿Se evitó un conflicto? (sí/no/no hacía falta) |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

## 3. Colisiones que se le escaparon al OS
Un conflicto al fusionar o al hacer push, o dos personas en lo mismo, **sin** aviso previo (en el bloque 1 se apuntan también: así se ve qué habría avisado).

| Bloque | Hora | Ficheros | Personas | Cómo se notó (conflicto de git, revisión, de palabra) | Por qué no avisó (si se sabe) |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |

## 4. Estados incorrectos (solo bloque 2)
Una tarea (o una persona) que la web o el estado de la sesión mostraba mal. **Criterio 4: ninguno sin explicación.** La explicación puede llegar después, con `resumen.py`.

| Hora | Tarea o persona | Dónde (web nueva: cabina / red / tablero / servicios · web del relay · sesión) | Lo que mostraba | Lo que era de verdad | Explicación (o «pendiente») |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

## 5. Avisos que sobran (solo bloque 2)
Avisos del OS que no servían para nada, sobre todo los de contrato (nivel 3), que van a «el resto del equipo». Cada persona marca los suyos.

| Hora | Quién lo recibió | Aviso (nivel, contrato o ficheros) | Útil / sobra | Por qué |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 6. Incidencias
El demonio que no arranca, el relay caído, la red, el cortafuegos, el alias de `hk-os`, una sesión que no aparece, `hk-os web` que no abre, una web en gris «sin conexión» (con la hora que decía la banda), «Tu demonio no oye al relay»…

| Hora | Quién | Qué pasó | Cuánto tiempo costó | Cómo se resolvió |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 7. Idas a la terminal, con Anotar y Reclamar en la web (bloques 1 y 2)
Una fila cada vez que alguien sale de la conversación con Claude **y** de su web: a la terminal (`git`, `hk-os`, `gh`), a GitHub en el navegador o a editar a mano un fichero de `.hackathon/`. Lo que Claude ejecuta dentro de su sesión no cuenta. En el bloque 2 la web ya tiene **Anotar** (una nota a `criterios.md` de `main`) y **Reclamar** (asignarse una tarea libre); lo que se mide es lo que se sigue haciendo fuera y qué botón lo habría evitado. Con esto se decide qué botones van después (`docs/hackathon-os/hitos.md`, «Después del M8»). Cada persona apunta las suyas o se las dice a quien observa.

Para la columna del botón, con las mismas palabras cada vez: **cerrar tarea** (cerrar su issue), **commit y push de `.hackathon/`**, **confirmar** (`hk confirmo`, o pasar una Propuesta a su tabla en `servicios.md`), **`hk-os unir`**, **`git pull`**, **reabrir la web** (`hk-os web`), otro (escríbelo) o **ninguno** (fuera es mejor).

| Bloque (1/2) | Hora | Quién | Herramienta (git / hk-os / gh / GitHub web / fichero) | Para qué, en pocas palabras | ¿Lo hacía la web? (Anotar / Reclamar / no) y, si lo hacía, por qué fuera (no lo sabía / falló: qué dijo / más rápido) | Botón que habría hecho falta | ¿Se rompió algo? (no / sí: qué y cuánto costó) |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |

**Anotar y Reclamar desde la web** (solo bloque 2). Una fila por uso, sobre todo los que no salieron bien. Los buenos también los cuenta `resumen.py`; los rechazados (la web dice «no se puede», «gh ha fallado», «otra nota se subió a la vez»…) no dejan rastro y solo están aquí.

| Hora | Quién | Acción (Anotar / Reclamar) | Lo que dijo la web | ¿Llegó? (Reclamar: issue asignado y aviso en la sesión; Anotar: el resto la ve en novedades) | ¿Hubo que rematarlo fuera? |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

Recuento (lo rellena quien observa al final):

| Bloque | git | hk-os | gh | GitHub web | fichero a mano | Total | Con algo roto | Lo hacía la web y se hizo fuera |
|---|---|---|---|---|---|---|---|---|
| 1 · control | | | | | | | | — |
| 2 · con OS | | | | | | | | |

Botones pedidos, de más a menos veces (bloque 2): 1. ________ (__) · 2. ________ (__) · 3. ________ (__)

## 8. Vista de servicios (solo bloque 2, con `.hackathon/servicios.md` en `main`)
Lo que pinta la vista **Servicios** sale de `servicios.md` (lo declarado) y de lo que el OS comprueba: el demonio del **dueño** mira el puerto y la Salud de sus servicios confirmados; el resultado de la Prueba de una conexión solo se ve si alguien la corre **dentro de una sesión de Claude Code** (si se corre en una terminal aparte, no sale, y eso no es un fallo). Quien observa la mira con el dueño de cada servicio dos veces, hacia la mitad y al final, y apunta además cualquier desajuste que alguien vea entre medias.

| Momento | ¿Están todos los servicios que hay en marcha, y ninguno de más? | ¿«responde» / «no responde» es lo que hay? | ¿El resultado de cada Prueba es el de la última vez que se corrió en Claude? | Desajustes en «No cuadra» | De ellos, falsos | Lo que no salía y debía salir |
|---|---|---|---|---|---|---|
| Mitad (__:__) | | | | | | |
| Final (__:__) | | | | | | |

Una fila por desajuste falso, por uno que faltaba o por una fila «sin confirmar» que el dueño sí había cambiado (tras un rebase o un squash puede pasar: ADR-0011, y el ensayo mira si pasa):

| Hora | Quién lo vio | Servicio, conexión o fichero | Lo que decía la vista (con su «hace X») | Lo que había de verdad | Tipo (desajuste falso / faltaba uno / sin confirmar por error / fuera de servicios por error) | Explicación (o «pendiente») |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
