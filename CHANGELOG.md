# Changelog

## 0.2.0 — 2026-10-11

Coordinación entre agentes, opcional.

- Nuevos comandos `/hack-ask`, `/hack-inbox` y `/hack-decide`: los agentes de cada persona se preguntan por GitHub Issues, con cabecera de saltos, escalado a las personas, deduplicación y backoff.
- Monitor de plugin que escucha el buzón sin coste de tokens mientras no hay novedades, y hook de inicio que reinyecta el estado propio y el buzón.
- `/hack-scaffold` pregunta si activarla (`.hackathon/coordinacion.md`, plantilla de issue, `.gitattributes`) y `/hack-plan` genera `.hackathon/autoridad.md`.
- Sin la coordinación activada, la cadena se comporta como en la 0.1.0.
- Validado con dos sesiones en dos worktrees de un repo sandbox y dos cuentas de GitHub: [evals/coordinacion/prueba.md](evals/coordinacion/prueba.md).

## 0.1.0 — 2026-10-10

Primera versión pública.

- Seis comandos: `/hack-analyze`, `/hack-approaches`, `/hack-scaffold`, `/hack-plan`, `/hack-pitch` y `/hack-check`, con el estado compartido en `.hackathon/`.
- Ejemplos de salida de dos retos reales en `skills/*/examples/`.
- Validado con seis retos (cinco reales y uno sintético) y una rúbrica de comprobaciones automáticas y de criterio (`evals/`).
- Limitaciones conocidas: [docs/limitaciones.md](docs/limitaciones.md).
