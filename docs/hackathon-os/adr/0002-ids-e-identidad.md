# ADR-0002 · IDs de tarea estables y una sola clave de persona

Estado: **aceptada** (2026-10-14, por el usuario al abrir M8b).

## Contexto
- Las tareas de `plan.md` son filas de tabla sin identificador. Sin ID no se pueden relacionar issues, encargos, refs de fusión, commits y eventos con una tarea.
- `.hackathon/estado/` tiene dos convenciones: `/hack-ask` y `sesion.sh` usan `<usuario de GitHub>.md`; el orquestador usa `<persona>.md` (el nombre de la sección del plan). Con coordinación y orquestador a la vez, son dos ficheros distintos o uno pisado.

## Decisión
- `/hack-plan` añade una columna `ID` a cada tabla «Por persona»: `T01`, `T02`…, en orden de aparición. Al ajustar un plan existente, conserva los IDs de las filas que siguen y da números nuevos a las nuevas; nunca reutiliza uno.
- «Quién espera a quién» cita IDs (`T05 espera a T02`).
- El encargo del orquestador lleva `ID: <Txx>`; la ref de fusión pasa a `refs/hackathon/fusion/<Txx>`; los commits de fusión empiezan por `Txx ·`. Las personas pueden citar el ID en sus commits para que el OS los asocie.
- Clave única de persona: usuario de GitHub en minúsculas. La tabla de `coordinacion.md` mapea nombre ↔ usuario. Ficheros de estado:
  - `estado/<usuario>.md`: el agente principal (`/hack-ask`, buzón). Como ahora.
  - `estado/<usuario>.orquestador.md`: el orquestador. Cambia el nombre actual.
- Sin coordinación (sin usuarios), el orquestador sigue usando `estado/<persona>.md` y el OS no se activa.

## Alternativas descartadas
- **IDs por hash** (como beads): evitan colisiones entre escritores concurrentes, pero `plan.md` tiene un solo escritor y un `T07` se dice en voz alta mejor que `hk-a3f8`.
- **ID con la inicial de la persona** (`A3`): cambia si se reasigna la tarea.
- **Fusionar los dos ficheros de estado**: dos escritores que reescriben el mismo fichero.

## Consecuencias
- Hay que regenerar los ejemplos de `skills/hack-plan/examples/` y repetir la validación de `/hack-plan` con los retos 02 y 03 (M8a).
- La prueba de reinicio en frío del orquestador (M7c, criterio 5) se repite con el nombre nuevo del estado.
