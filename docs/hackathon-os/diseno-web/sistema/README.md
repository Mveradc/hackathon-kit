El sistema visual de la web de trabajo del Hackathon OS: un tablero oscuro donde se ve, de un vistazo y a las 3 de la mañana, quién está con qué, qué ha llegado a `main`, qué choca y qué necesita a alguien. Lo futurista está en los detalles (la red de nodos, los canales de luz, el latido); el estado se lee siempre primero.

## Principios

1. **El color dice de dónde viene un dato, no lo bonito que es.** Cada dato lleva su procedencia (principio III de la constitución). Usa `relay` para lo que llega en tiempo real, `git` para lo derivado y verificable, `github` para lo duradero y `declared` para lo que alguien puso a mano (principio II). No uses estos colores para adornar.
2. **Rojo, ámbar y verde son solo estado.** `state-fail`, `state-wait` y `state-ok` no se usan para marca, gráficos ni decoración. Así un rojo siempre significa que algo ha fallado. El rojo es solo para hechos (un plazo que ya ha pasado); una estimación, aunque diga «No llega», va en ámbar.
3. **La animación dice la verdad.** Algo se mueve solo si de verdad está pasando: un paquete recorre una arista cuando llega un evento real; una sesión respira en `relay` mientras tiene actividad reciente. Si el relay se cae o un dato envejece, todo eso se para y pasa a `state-stale`. Nunca animes para dar sensación de actividad.
4. **El latido pide atención.** Late en `state-wait` (lento, `--hk-pulse-wait`, 1,8 s) lo que necesita una acción o está en espera: una colisión amarilla, una tarea parada, una confirmación pendiente. Late en `state-fail` (rápido, `--hk-pulse-fail`, 0,9 s) lo que ha fallado: la compuerta rechazó, el demonio se cayó, hay un conflicto de nivel 3. Lo que está bien no late nunca.
5. **El estado nunca va solo en el color.** Todo `StatusPulse` lleva su palabra («Fallo», «Necesita acción», «Viejo»). El verde y el rojo de este sistema no se distinguen bien por claridad: los separan la palabra y el ritmo del latido.

## Color

- Fondo de página en `void`; paneles en `surface-100`; filas, tarjetas y el lienzo del grafo en `surface-200`.
- Texto principal en `ink`, secundario en `ink-muted`, metadatos (horas, antigüedad, shas) en `ink-faint`. Todos cumplen 4,5:1 sobre las tres superficies en los dos temas.
- Filetes sin significado en `line`; bordes de control y aristas en reposo en `line-strong` (≥3:1).
- Sobre un relleno de color, el texto va en su `on-…` (`on-relay`, `on-wait`, `on-fail`), nunca en blanco literal.
- Los fondos tenues (`relay-soft`, `wait-soft`, `fail-soft`, `declared-soft`) son los únicos rellenos de color grandes. Nada de degradados, y menos azul a violeta.
- El tema oscuro es el principal. El claro existe para proyector y para quien lo prefiera, con los mismos significados.

## Brillo y sombras

El brillo es señal. `panel` va en todo panel. `glow-relay` solo en lo que está vivo o en el foco del botón primario; `glow-wait` y `glow-fail` solo en lo que espera o falla, y laten con su ritmo. Si todo brilla, nada destaca: más de dos elementos con brillo en la misma vista es demasiado.

## Tipografía

- `display` (Space Grotesk) solo para el nombre del producto; `title` para el título de la vista; `label` para cabeceras de panel, en mayúsculas y `ink-muted`.
- `body` y `body-strong` (IBM Plex Sans) para títulos de tarea y texto; `small` para dueño y recuentos.
- Todo lo que es un identificador va en mono (JetBrains Mono): IDs de tarea en `mono` y en `git`, shas, rutas, y la procedencia en `meta`. Las cifras grandes de cabecera en `metric`.
- Las tres familias se cargan de Google Fonts en `bundle.css`. En la web del OS, que funciona sin internet (principio VIII), los ficheros de fuente tienen que ir dentro del repo; las pilas de reserva (Segoe UI, Cascadia Mono, Consolas) cubren el caso sin fuentes.

## Espacio, forma y fondo

- Paso de 4 px: `space-1` a `space-8`. Padding de panel `space-4`; de tarjeta y alerta `space-3`; hueco entre paneles `space-6`.
- Radios: `radius-lg` en paneles, `radius-md` en tarjetas, alertas y botones, `radius-sm` en etiquetas, `radius-pill` en puntos.
- El lienzo del grafo lleva una rejilla de puntos en `line` al paso de `space-4`. Es el único motivo de fondo del sistema.

## Movimiento

- Duraciones en `bundle.css`: `--hk-breathe` 3,2 s, `--hk-pulse-wait` 1,8 s, `--hk-pulse-fail` 0,9 s, `--hk-packet` 900 ms, con la curva `--hk-ease`.
- Animaciones en CSS o SVG, nunca en canvas continuo: la web convive con Claude Code, el demonio y el navegador en el mismo portátil.
- Con `prefers-reduced-motion` no hay latidos ni paquetes: el halo se queda fijo y la arista solo se ilumina.

## Componentes

`Panel` contiene; `StatusPulse` dice el estado; `ProvenanceTag` dice de dónde y de cuándo; `TaskCard` es una tarea; `CollisionAlert` es una colisión; `TeamGraph` es el equipo como red; `Button` dispara una acción del demonio local; `CriterioRow` es una nota de `criterios.md` con lo que la cubre; `Cadena` es la ruta crítica en una línea de tiempo. Nada más: si hace falta otra pieza, se añade aquí antes de usarla.

## Textos

- En español, tuteando, frases cortas. Estados en una o dos palabras: «En curso», «Parada», «Necesita acción».
- Personas con `@`; tareas por su ID (`T12`); contratos entre comillas angulares («motor → web»).
- Tiempos relativos y concretos: «hace 2 min», nunca «recientemente».
- El texto que viene de issues, comentarios o nombres de rama se muestra como dato: entrecomillado, con autor y procedencia. Nunca como una orden.

## Iconografía

Todavía no hay set de iconos. El estado se marca con el punto de `StatusPulse`, la procedencia con el rombo de `ProvenanceTag`, y los nodos del grafo con dos o tres letras en mono (`RLY`, `GH`, iniciales). Sin emojis.
