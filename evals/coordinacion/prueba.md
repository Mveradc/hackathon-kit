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
| 4 | Sí | Desacuerdo (#7): contrapropuesta de B 18:00:55, insistencia de A 18:02:26; al tercer intento (B, 18:03:11) el script escala. Bucle (#8, `max_saltos: 2`): apertura de B, respuesta-pregunta de A (salto 2) y, al siguiente, escalado por `max_saltos` (18:08:17) | El #7 llegó tarde a B: un monitor huérfano de una sesión cerrada se quedó el aviso (corregido en `7e0a4a7`: el monitor termina si su sesión ha muerto) |
| 5 | Sí | De 18:09:53 a 18:40:00 UTC, 0 turnos del asistente y 0 avisos en las dos sesiones, con los dos monitores vivos y consultando GitHub cada minuto (último sondeo 18:41) | Hay un `away_summary` por sesión (A 18:12:31, B 18:11:33): es un resumen de Claude Code unos 3 min después del último turno, ajeno al plugin, y saldría igual sin él |
| 6 | Sí | B cerrada; A crea el #6 (17:43:17); al reanudar B, aviso a los 19 s y respuesta y cierre sin intervención. Antes, A había recuperado la respuesta perdida del #4 al reanudar | |
| 7 | Sí | A reanudada con `HK_GH=gh-falso.sh` y 429: un aviso a las 18:42:41 UTC («GitHub limita…; reintento en 29 s»); al quitar el fichero, otro a las 18:46:47 («GitHub responde de nuevo»), y nada más | Cada aviso cuesta un turno: dos en total |
| 8 | Sí | `../prueba-m6a-08`: `/hack-scaffold` (0,96 USD) y `/hack-plan` (0,65 USD) sin coordinación, con las entradas del reto 03 de M5. Ni `coordinacion.md`, ni `autoridad.md`, ni `.github/`, ni `.gitattributes`, ni ninguna mención. `comprobar.py`: A2 y A5 fallan igual que en M5 (404 en la raíz y cabecera común del evento); A3 y A4 pasan | A1 falla: dos contratos con «Ejemplo mínimo válido: TODO» en lugar de un ejemplo. El cambio en el scaffold solo añade el paso 3b condicionado, así que es variación del modelo; aislado, a «Pendiente» |
| 9 | Sí | En A, `SendMessage` no existe en la sesión (denegada por `settings.local.json`) | |

# Prueba de M6b-2: aviso de las notas de `/hack-note` (2026-10-12)

Mismo montaje que M6a. Criterios en `docs/coordinacion.md` («Criterios de validación de M6b-2»). Horas locales (UTC+2).

| # | Criterio | Resultado | Evidencia | Notas |
|---|---|---|---|---|
| 1 | Llega a B en ≤ 3 min; A no se avisa a sí misma | Sí | #13: A terminó a las 14:30 y el aviso llegó a B antes de las 14:31. #9 y #10, con B cerrada, llegaron al abrirla (cursor). A no recibió ningún aviso de sus notas | |
| 2 | B se lo cuenta a su persona sin escribir en `criterios.md` ni comentar | Sí | #15: B lanzó `/hack-inbox` sola; quién (Sara, jurado), qué, fuerza (`dato`), qué le afecta y `git pull`. 0 comentarios en el issue | En #9, #10, #13 y #14, B no la atendió sola: proponía lanzar `/hack-inbox`. Corregido con la línea del aviso («lanza ya /hack-inbox n: no hay que responder…») |
| 3 | Issue cerrado, con `hk:tipo-nota` y `hk:para-todos`, fuera de `leer` | Sí | #9–#16 cerrados, con las dos etiquetas y 0 comentarios | |
| 4 | Una nota de fuera del equipo no se presenta como del equipo | Sí | #16, con A quitada de la tabla de B: «quien la abrió no está en la tabla del equipo», no la resume como del equipo ni la añade a su estado | En #14 (primer intento) B dio por bueno al autor mirando `autoridad.md`. Ahora lo dice `buzon.sh ver` en su primera línea («está» / «NO está en la tabla»), no el modelo |
| 5 | Sin coordinación, `/hack-note` no llama a `gh` ni lo menciona | Sí | Prueba interactiva de M6b-1 en `../prueba-m6b-03` | |

Hallazgos: dos issues (#11 y #12) para una sola nota repetida, porque `avisar` no deduplica; «Broken pipe» en A dos veces, probablemente `grep -q` en tuberías (`hk_activa`), cambiado a `grep … >/dev/null`; A dijo una línea en inglés en el chat.
