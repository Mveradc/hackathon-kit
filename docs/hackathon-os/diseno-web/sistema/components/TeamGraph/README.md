# TeamGraph

El equipo como red: relay en el centro, GitHub aparte, personas alrededor y sus orquestadores y workers en órbita.

- El consumidor da las posiciones (`x`, `y`) y el canal de cada arista: `relay` (cian, tiempo real), `github` (naranja, duradero), `local` (azul, entre una persona y sus agentes).
- Un paquete viaja por una arista solo cuando llega un evento real nuevo en `events`. Sin eventos, el grafo está quieto. Nunca alimentes `events` con un temporizador en producción.
- Un nodo en `wait` late en ámbar con la palabra ESPERA; en `fail`, en rojo y más rápido, con FALLO; en `stale`, gris discontinuo y sin aristas animadas.
- Con `prefers-reduced-motion` no hay paquetes: la arista solo se ilumina un momento.
