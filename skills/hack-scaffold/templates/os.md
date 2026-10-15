# Hackathon OS
activa: no
relay: http://<ip-lan-o-tailnet>:7777
publicar_wip: no          # ADR-0007, nivel 2. Lee el aviso de abajo antes de ponerlo a «sí»
# Aviso de publicar_wip: con «sí», el demonio sube al remoto (refs/hackathon/wip/<usuario>, no una rama) el trabajo
# sin commit de la copia principal: lo versionado cambiado y lo nuevo que .gitignore no ignore. Excluye .env*, claves
# y credenciales comunes, datos_excluidos y lo de más de 1 MB, pero ninguna lista es completa: revisa el .gitignore
# antes. Borrar la ref no borra lo subido (GitHub sigue sirviendo los objetos por su sha): una clave que suba, rótala.
# Con el repo público no publica, salvo «publicar_wip: sí, incluso público». Lo publicado: wip.json y /salud del demonio.
github: sí                # no = modo sin GitHub: tareas de plan.md y remoto del equipo (docs/hackathon-os/arranque.md)
repo_tareas:              # vacío = el repo de coordinacion.md
umbral_parada_min: 20
umbral_viejo_s: 300
datos_excluidos: data/, datos/   # ADR-0007: nunca se publican en refs/hackathon/wip/*
puerto_agente:            # vacío = 47100 + (cksum del git común) % 900 (ADR-0004)
apagado_min: 30           # el demonio sale tras este tiempo sin eventos ni sesiones
