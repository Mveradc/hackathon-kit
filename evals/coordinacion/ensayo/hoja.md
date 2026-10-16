# Hoja de observación del ensayo (M8h, criterio 4)

Para imprimir o rellenar en el portátil. Una hoja por ensayo; la rellena la persona observadora y cada persona apunta sus propias preguntas en la tabla 1 (o se las dice a quien observa). Usad la hora del reloj de la pared o la del relay, siempre la misma. **En `prueba.md` va anonimizada** (Persona A, B…): aquí podéis poner nombres.

## Cabecera
| Campo | Valor |
|---|---|
| Fecha | |
| Reto | 03 (Embat) |
| Personas (nombre → letra) | A: · B: · C: · D: · E: |
| Quién coordina (relay) | |
| Quién observa | |
| Bloque 0 · cadena del kit | de __:__ a __:__ |
| Bloque 1 · **control, OS apagado** (60 min) | de __:__ a __:__ |
| Arranque del OS (criterio 3) | de __:__ a __:__ → ___ min (todos en la web a las __:__) |
| Bloque 2 · **con el OS** (≥ 3 h) | de __:__ a __:__ |
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

| Hora | Tarea o persona | Lo que mostraba | Lo que era de verdad | Explicación (o «pendiente») |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |
| | | | | |

## 5. Avisos que sobran (solo bloque 2)
Avisos del OS que no servían para nada, sobre todo los de contrato (nivel 3), que van a «el resto del equipo». Cada persona marca los suyos.

| Hora | Quién lo recibió | Aviso (nivel, contrato o ficheros) | Útil / sobra | Por qué |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 6. Incidencias
El demonio que no arranca, el relay caído, la red, el cortafuegos, el alias de `hk-os`, una sesión que no aparece…

| Hora | Quién | Qué pasó | Cuánto tiempo costó | Cómo se resolvió |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 7. Idas a la terminal (bloques 1 y 2)
Una fila cada vez que alguien tiene que ir a la terminal **fuera de la conversación con Claude**: `git`, `hk-os`, `gh` o editar a mano un fichero de `.hackathon/`. Lo que Claude ejecuta dentro de su sesión no cuenta. Sirve para decidir qué botones de la web se hacen primero (`docs/hackathon-os/hitos.md`, «Después del M8»). Cada persona apunta las suyas o se las dice a quien observa.

| Bloque (1/2) | Hora | Quién | Herramienta (git / hk-os / gh / fichero) | Para qué, en pocas palabras | ¿Se rompió algo? (no / sí: qué y cuánto costó) |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

Recuento (lo rellena quien observa al final):

| Bloque | git | hk-os | gh | fichero a mano | Total | Con algo roto |
|---|---|---|---|---|---|---|
| 1 · control | | | | | | |
| 2 · con OS | | | | | | |
