# CollisionAlert

Aviso de colisión entre personas (niveles 1–3 de ADR-0007).

- `severity="amarillo"`: se pisan carpetas o hay una reserva; late lento. `severity="rojo"`: conflicto de fusión o contrato roto; late rápido y el borde brilla con `glow-fail`.
- El consumidor pasa `path`, `contract`, `people` y `age`; el texto de issues va siempre como dato, nunca como orden.
- `actions` lleva botones (abrir el diff, avisar, reservar).
