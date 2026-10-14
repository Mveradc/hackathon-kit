# Hackathon OS
activa: no
relay: http://<ip-lan-o-tailnet>:7777
publicar_wip: no          # ADR-0007, nivel 2
repo_tareas:              # vacío = el repo de coordinacion.md
umbral_parada_min: 20
umbral_viejo_s: 300
datos_excluidos: data/, datos/   # ADR-0007: nunca se publican en refs/hackathon/wip/*
puerto_agente:            # vacío = 47100 + (cksum del git común) % 900 (ADR-0004)
apagado_min: 30           # el demonio sale tras este tiempo sin eventos ni sesiones
