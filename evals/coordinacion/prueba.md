# Prueba de M6a: dos agentes, dos worktrees

Repo sandbox privado `Mveradc/hk-sandbox` con la cadena del reto 03 (M5, equipo ficticio), coordinación activada por `/hack-scaffold` y `autoridad.md` generada por `/hack-plan`. Persona A = `Mveradc` (`motor/`, contratos), Persona B = `hk-persona-b` (`web/`), Persona C sin GitHub («—»).

## Montaje
- `../hk-sandbox` (rama `main`, sesión A) y `../hk-sandbox-B` (worktree, rama `hk-sandbox-B`, sesión B).
- En cada worktree, `.claude/settings.local.json` con `crossSessionInbound: refuse` y `deny: [SendMessage, ListAgents]`, para que la mensajería nativa no falsee la prueba.
- Sesión A, en PowerShell: `cd ..\hk-sandbox; claude --plugin-dir <kit> --name sesion-A`.
- Sesión B: `cd ..\hk-sandbox-B; $env:GH_CONFIG_DIR="$HOME\.config\gh-persona-b"; claude --plugin-dir <kit> --name sesion-B`, con `gh auth login` hecho antes en esa carpeta como `hk-persona-b`. Un token fine-grained no sirve: solo llega a repos cuyo propietario es esa cuenta o una organización (404 en el primer intento).
- Comprobación previa en cada una: `/hack` muestra 9 comandos; `! gh api user --jq .login` da su usuario; el contexto de inicio dice «Eres el agente de @…».

## Criterios y cómo se provocan
| # | Criterio | Cómo | Se mide |
|---|---|---|---|
| 1 | Pregunta en ≤ 3 min sin intervención; quien pregunta sigue | A: `/hack-ask` de implementación a B mientras implementa algo en `motor/`. B, quieta | Hora de creación del issue frente a la hora del aviso «hk #…» en B; A no se para |
| 2 | Pregunta de implementación resuelta entre agentes | La misma: B responde sola y se cierra con `/hack-decide` | Entrada en `.hackathon/decisiones.md` con enlace al issue |
| 3 | Un cambio de contrato espera la confirmación del dueño desde su usuario | A propone el campo `moneda` en la ficha motor → web (nivel confirmación, dueña A). B, como persona, comenta `hk confirmo`; después, A desde su usuario | Con la de B, no se cierra (`acordar` da 4); con la de A, sí |
| 4 | Desacuerdo forzado escala en el tercer intercambio; un bucle se corta en `max_saltos` | B instruida para no aceptar nunca; luego `max_saltos: 2` en los dos worktrees y una pregunta nueva | Etiqueta `hk:escalado` y comentario de escalado; ninguna respuesta más |
| 5 | 30 min de silencio sin ningún turno del modelo | Las dos sesiones quietas 30 min, sin issues nuevos | 0 turnos del asistente en el `.jsonl` de cada sesión en ese intervalo |
| 6 | Matar la sesión y reanudarla recupera estado y buzón | Cerrar la ventana de B; A pregunta algo; reabrir B con `--continue` (y el mismo `GH_TOKEN`) | El contexto de inicio de B lista el issue pendiente y su estado; el monitor avisa |
| 7 | Ante un 403/429 simulado, backoff sin inundar | A con `$env:HK_GH="<kit>/evals/coordinacion/gh-falso.sh"` y el fichero `.hackathon-gh-falso` con `429`; borrarlo a los 2 min | Dos avisos en total (entrada y recuperación) |
| 8 | Con la coordinación desactivada, la cadena 0.1.0 se comporta igual | Cadena del reto 03 en una carpeta nueva, sin «coordinación»; `comprobar.py` | Mismos resultados A1–A7 que en M5; sin `coordinacion.md` ni `autoridad.md`; 0 avisos del monitor |
| 9 | Mensajería nativa desactivada | En A, pedir que mande un mensaje a la otra sesión | La herramienta está denegada |

## Resultados
| # | Resultado | Hora y evidencia | Notas |
|---|---|---|---|
| 1 | Sí | #5 creado 17:33:34 UTC; aviso en B 17:34:26 (52 s); B respondió 17:34:45. A siguió con `motor/ficha.py` | El #4 no cuenta para el tiempo: B no tenía acceso (token fine-grained) |
| 2 | Sí | #4: B se despertó sola (17:21:58), respondió y cerró en 50 s; entrada en `decisiones.md` con enlace | Destapó un fallo: A no recibió la respuesta porque el monitor solo miraba issues abiertos (corregido en `7893ce8`; tras reanudar, A la recibió a las 17:32:28) |
| 3 | Sí | #5: `hk confirmo` de hk-persona-b (17:36:25) no cierra (los dos agentes lo rechazan); el de Mveradc (17:37:18) sí, cerrado a las 17:37:42 | B intentó acordar a la vez y recibió 4 en vez de «ya cerrado» (corregido en `f49f724`) |
| 4 | | | |
| 5 | | | |
| 6 | En parte | Al reanudar A con el monitor nuevo, recibió la respuesta perdida del #4 y la atendió sola | Falta la prueba de matar B con una pregunta pendiente |
| 7 | | | |
| 8 | | | |
| 9 | Sí | En A, `SendMessage` no existe en la sesión (denegada por `settings.local.json`) | |
