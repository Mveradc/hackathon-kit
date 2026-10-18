# ADR-0009 · Principio IV: misma fuente y mismos campos

Estado: **aceptada** (2026-10-17, por el usuario al abrir M9a).

## Contexto
El principio IV decía que la web y el markdown inyectado son dos vistas «generadas por el mismo código». Era verdad mientras la web era un HTML sin build que pintaba la vista de `hkos/proyeccion.py`. La web de M9a está en React + Vite y se compila, así que no puede compartir código con el markdown, que genera Python. Lo que importa del principio no es el código, sino que personas y agentes vean lo mismo.

## Decisión
- **Principio IV reformulado:** hay un solo modelo (`estado.json`) y una sola vista calculada (`proyeccion.vista`, en Python). La web, `estado-equipo.md` y el MCP muestran **los mismos campos de la misma fuente**. Si difieren, es un fallo.
- **Qué puede hacer la web:** pintar campos de la vista, incluido el bloque `servicios` (que también se calcula en `proyeccion.py`); agrupar, filtrar u ordenar por un campo (el tablero por persona, «Necesita acción» como unión de campos que ya están); formatear «hace X» a partir de `servido_en` y del `observado_en` de cada dato.
- **Excepción explícita, del transporte:** si la web no recibe nada del demonio (ni vista, ni evento, ni `ping`) en `max(umbral_viejo_s, 40 s)` (`umbral_viejo_s` de `os.md`, que trae la propia vista; los 40 s, el doble del `ping` de 20 s de `/v1/stream`, `api.md` §4), toda la página pasa a **«sin conexión»**: gris, sin animación, con la hora del último dato recibido. No calcula el estado de ningún dato; dice que la propia web ha dejado de recibir. Al volver la conexión, pinta la vista nueva tal cual.
- **Qué no puede hacer la web:** calcular estados, columnas, colisiones, antigüedades, «viejo» o confirmaciones, ni leer de otra fuente que no sea la vista y los `eventos` del SSE (que solo animan, ADR-0010).
- **Prueba doble:**
  1. `evals/coordinacion/simulador/igualdad.py` ampliado: la vista que sirve el demonio, `estado-equipo.md` y el MCP coinciden en estados, dueños, colisiones, antigüedades y servicios (G1–G6 y G12).
  2. Un test de Vitest en `hkos/web-src/` que pinta cada vista con las mismas vistas de G1–G6 y G12 y comprueba que cada estado, dueño, colisión, antigüedad y desajuste aparece en el DOM con el mismo texto.
- **Node** solo hace falta para quien compila la web y en CI (`web-m9a.yml`, que además comprueba que el compilado subido coincide con el fuente). Quien la usa no instala nada (principio VII).

## Nota (2026-10-19, M10: ADR-0012, decisión 7B; ADR-0013)
- Con `vista_jurado: sí` o `ruta_critica: sí`, `estado-equipo.md` lleva **una sola línea de resumen** por vista en la sección `## Jurado y ruta` (`api.md` §6 y §11): la de jurado («2 sin cubrir (1 «obligatorio») · 1 cubierta de 3») y la de ruta (veredicto, rango o motivo de «sin estimación», y el primer plazo pasado). El **detalle** (cada nota con su cobertura, enlaces y evidencias; la cadena, los hechos, la base y los hitos) va en el MCP (herramientas `jurado` y `ruta`) y en la web.
- Es una excepción acotada a «los mismos campos»: la línea sale del campo `resumen` de cada bloque de la vista, y el MCP y la web, del mismo bloque. `igualdad.py` compara la línea del md con `resumen` y el bloque entero entre la vista del demonio y el MCP; Vitest, el bloque con el DOM (G13 y G14).
- Motivo: el presupuesto de inyección (R-24, R-25b) y el principio X. Con 15 notas y una cadena de 10 tareas, el detalle no cabe en 2.500 caracteres junto a lo de siempre.

## Alternativas descartadas
- **Solo igualdad de datos** (sin test del DOM): más barata, pero no detecta que la web oculte o transforme un campo.
- **Mantener «mismo código»** (seguir sin build): el diseño de M9a (grafo, latidos, cuatro vistas, componentes) necesita componentes y estado de interfaz; escrito a mano sin build sería más frágil y no se podría probar con Vitest.
- **Calcular la vista en el navegador** con una copia en JS de `proyeccion.py`: dos implementaciones que divergen (el motivo de ADR-0006).

## Riesgos aceptados
- El test del DOM comprueba que los campos están, no que se vean bien: el diseño se revisa a mano con las pantallas de `docs/hackathon-os/diseno-web/`.
- Un campo nuevo de la vista que la web no pinte no lo detecta el test hasta que se añade a la lista de campos comprobados.
