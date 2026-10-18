# Diseño de la web del Hackathon OS (M9a)

Referencia de diseño para la web nueva. Es la fuente de verdad visual: el código de `hkos/web` la sigue, no la copia tal cual.

## Qué hay

- `sistema/README.md`: las reglas. Léelo primero: color por procedencia, rojo, ámbar y verde solo para estado, latidos (ámbar lento = necesita acción, rojo rápido = fallo) y «la animación dice la verdad».
- `sistema/tokens.json`: los tokens (colores en tema oscuro y claro, tipografía, espaciado, radios, sombras y brillos). `sistema/tokens.css` es lo mismo compilado como variables CSS.
- `sistema/components/`: los siete componentes de referencia (`Panel`, `StatusPulse`, `ProvenanceTag`, `Button`, `TaskCard`, `CollisionAlert`, `TeamGraph`).
  - `bundle.js` está escrito a mano con `React.createElement`, sin build.
  - `bundle.css` lleva las animaciones y `prefers-reduced-motion`.
  - `index.d.ts` documenta las props.
  - Cada carpeta trae un `README.md` con las reglas de uso y un `preview.html`, que necesita que se carguen antes `tokens.css`, `bundle.css`, React 18 y `bundle.js`.
- `pantallas/`: las cuatro vistas en el formato del lienzo de diseño (`.dc.html`). Sirven para leer la estructura, el contenido y los datos de ejemplo; no se abren solas en un navegador (cargan `./support.js` y `ds/hkos/…` del lienzo).
  - `red.dc.html`: el grafo del equipo como centro, con cifras, hitos y «Necesita acción».
  - `tablero.dc.html`: una columna por persona más «Sin dueño», con la banda de colisión y la actividad.
  - `cabina.dc.html`: la vista de una persona (vista por defecto). Incluye Reclamar y Anotar.
  - `servicios.dc.html`: los servicios de `servicios.md`, sus contratos, lo propuesto sin confirmar y lo que no cuadra.
  - 0.5.0: `jurado.dc.html` (R-35) y `ruta-critica.dc.html` (R-36), cada una con la prop `estado` (`inicio`, `mitad`, `riesgo`); `ver.html` abre las seis fuera del lienzo (`python -m http.server 8000 -d docs/hackathon-os/diseno-web` y `/pantallas/ver.html?p=jurado&estado=riesgo`), y `capturas/` guarda sus capturas.

## Para la implementación

- Los componentes se reescriben en React + Vite dentro del kit. Mantén los nombres, las props y las clases `hk-*` siempre que se pueda.
- Las fuentes (Space Grotesk, IBM Plex Sans, JetBrains Mono) van dentro del repo, no desde Google Fonts (principio VIII). Las pilas de reserva ya están en los tokens.
- En las pantallas, los eventos del grafo están simulados con un temporizador. En la web real llegan del relay; nunca de un temporizador.
- Los datos de ejemplo (@ana, @luis, @marta, @pablo, T07…) son inventados.
