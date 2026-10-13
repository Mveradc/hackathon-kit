# ADR-0003 · Relay propio en el portátil coordinador (HTTP + SSE)

Estado: **propuesta**.

## Contexto
El estado efímero (presencia, ficheros tocados, reservas) cambia cada pocos segundos y no puede ir por GitHub (límites de escritura). El equipo trabaja en la misma sala, con una red de evento de calidad desconocida (NAT, portal cautivo, puertos bloqueados).

## Decisión
- Un proceso `hk-os relay` en el portátil de quien coordina: HTTP para recibir eventos y SSE para empujar `estado.json`.
- Alcance de red: LAN del evento o, si la red aísla clientes, Tailscale (cada persona instala el cliente; el relay escucha en su IP de tailnet). Nunca expuesto a internet.
- Token del equipo generado al arrancar (`hk-os relay` lo imprime; `hk-os unir <url> <token>` lo guarda en `<git común>/hackathon/os/`, fuera de git).
- Persistencia mínima: registro de eventos en JSONL y último `estado.json`, para reiniciar el relay sin perder la sesión.
- El relay es también quien sondea GitHub (un solo token, el del coordinador), para no multiplicar peticiones por persona.

## Alternativas descartadas
- **Supabase Realtime, Firebase, Ably, Pusher, Cloudflare Durable Objects / PartyKit**: presencia hecha, pero cuenta y claves de un tercero, metadatos fuera de la sala y dependencia de internet. Queda como plan B alojado si ningún portátil puede ser servidor (extra, tras M8h).
- **MQTT / NATS**: Last Will es elegante para presencia, pero añade un broker.
- **GitHub como bus**: límites de escritura.
- **Sin relay, cada demonio sondea a los demás**: N² conexiones y descubrimiento.

## Consecuencias
- Un punto único: si el portátil coordinador se duerme, cae lo efímero (R-29 cubre la degradación). Mitigación: `hk-os relay` se puede arrancar en otro portátil con el JSONL copiado.
