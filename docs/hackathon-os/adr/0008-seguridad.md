# ADR-0008 · Seguridad del canal y de la inyección

Estado: **aceptada** (2026-10-14, por el usuario al abrir M8b).

## Decisión
- **Repo privado** por defecto para la coordinación y las tareas (ya lo recomienda el kit para el sandbox).
- **Autoría por script**: un evento o issue solo cuenta si su autor (login de GitHub) está en la tabla de `coordinacion.md`, como hace `buzon.sh ver`. Lo de fuera se muestra como «de fuera del equipo» y no se resume como del equipo (R-31).
- **Inyección factual**: el texto externo va resumido, entrecomillado y con autor; nada en imperativo (guía oficial de hooks: texto con aspecto de orden activa las defensas contra inyección).
- **Relay**: token del equipo en cada petición; sin CORS abierto; escucha en la IP de LAN o tailnet, no en `0.0.0.0` de una red pública; sin contenido de ficheros (R-32).
- **Tokens de GitHub**: el relay usa el `gh` del coordinador; cada demonio, el de su persona y solo para lo que escribe ella (reclamar).
- **Sin secretos en git**: token del relay y estado del demonio en `<git común>/hackathon/os/`.

## Riesgos aceptados
- Quien esté en la tabla puede escribir cualquier cosa en un issue: es del equipo, y lo que dice sigue siendo dato.
- El token del relay viaja de boca en boca o por chat del equipo.
