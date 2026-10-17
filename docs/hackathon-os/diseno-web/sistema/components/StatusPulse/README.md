# StatusPulse

Punto de estado con su palabra. Es la unidad de toda la señalización del OS.

- `live` respira en `relay` solo mientras hay actividad real reciente.
- `wait` late lento en `state-wait`: algo necesita acción o está en espera.
- `fail` late rápido en `state-fail`: un fallo o una colisión roja.
- `ok` es verde y quieto; `stale` es gris, discontinuo y quieto; `idle` es un aro hueco.
- Lleva siempre palabra (`label`); quítala (`label={false}`) solo si al lado ya hay texto que dice el estado. El verde y el rojo no se distinguen bien por claridad: la palabra y el ritmo del latido son los que los separan.
