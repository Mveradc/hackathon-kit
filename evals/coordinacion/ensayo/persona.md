# Ensayo del Hackathon OS: lo que hace cada persona

Una página para quien programa en el ensayo y no coordina. Quien coordina sigue el [`README.md`](README.md) y [`arranque.md`](../../../docs/hackathon-os/arranque.md); tú solo necesitas esto.

**Qué se mide.** Si el equipo se pregunta menos cosas («¿quién está con…?», «¿está en main?», «¿vamos a chocar?») cuando ve el estado de todos en una web. No se mide tu código ni lo rápido que vas: trabaja como lo harías en una hackathon.

## El día antes (unos 15 minutos)
1. **Git.** En Windows, [Git for Windows](https://git-scm.com/download/win) (trae Git Bash). En macOS, además, `brew install bash` (el bash de serie es demasiado viejo y el OS se quedaría apagado en tu portátil).
2. **uv**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` en Windows; `curl -LsSf https://astral.sh/uv/install.sh | sh` en macOS y Linux.
3. **Claude Code con el kit.** Dentro de `claude`:
   ```
   /plugin marketplace add Mveradc/hackathon-kit
   /plugin install hackathon-kit@hackathon-kit
   ```
   Si ya lo tenías instalado, desinstálalo (`/plugin uninstall hackathon-kit@hackathon-kit`) y vuelve a instalarlo: la versión no ha cambiado y podrías quedarte con el código viejo.
4. **GitHub.** `gh auth login` con tu cuenta, y acepta la invitación al repo del ensayo (te llega por correo o en github.com/notifications).
5. **`hk-os` en tu terminal.** En Git Bash (o en tu shell), añade esta línea a `~/.bashrc` y abre una terminal nueva:
   ```bash
   alias hk-os='uv run --no-project --quiet "$(ls -d ~/.claude/plugins/cache/*/hackathon-kit/*/ | tail -1)hkos/cli.py"'
   ```
   Comprueba: `hk-os --help` tiene que listar `recoger`. Si no lo lista, tienes el kit viejo (paso 3).
6. **Red.** Si no vais a estar en la misma wifi, o quien coordina te lo pide: instala **Tailscale** (o ZeroTier) y entra en la red que te diga. Hazlo antes: la primera conexión necesita internet.

## El día

Es el ensayo realista: el día como sería en la hackathon, desde el enunciado.

| Momento | Qué haces |
|---|---|
| **Cadena del kit** (30–40 min, se cronometra) | Quien coordina lanza los comandos del kit con el enunciado. Tú lees el análisis y los enfoques y elegís juntos; si te lo pide, le das tus datos para `.hackathon/equipo.md` (puntos fuertes, lo que prefieres no hacer, disponibilidad, sistema del portátil, si presentas el pitch). Cuando el plan esté subido: `git clone <repo>` y entra en la carpeta. |
| **Arranque del OS** (≤ 10 min, se cronometra) | Quien coordina pega en el chat dos líneas: la de `hk-os unir` y la de la web. Tú: `git pull`, pega la línea `hk-os unir <url> <token>` en tu terminal (te dice tu desfase de reloj: si pasa de 30 s, ajusta la hora del portátil). Abre `claude` en tu clon (si ya tenías una sesión abierta, ciérrala y abre una **nueva**). Abre la web y búscate en «Equipo». |
| **Trabajo** (lo que acordéis; ≥ 2 h) | Tus tareas de `.hackathon/plan.md`, con Claude Code, como en la hackathon. La web, a la vista. |
| **Cierre** (15 min) | El cuestionario que te pase quien coordina, y `hk-os recoger` en tu clon. |

Si quien coordina hace el ensayo completo, hay además un bloque de 60 minutos **sin OS** antes del arranque: trabajas igual, sin `hk-os unir` todavía.

**Mientras trabajáis:**
- **Tus tareas.** Al empezar una, asígnate su issue `hk-tarea` en GitHub; al acabarla, ciérralo. Si puedes, empieza el asunto de tus commits con el ID de la tarea: `T07 · formulario de alta`.
- **Apunta tus preguntas.** Cada vez que preguntes algo al resto (en voz alta o por chat) sobre quién hace qué, qué está subido o si vais a tocar lo mismo, apúntalo con la hora, o díselo a quien observa. Es lo más importante que mide el ensayo.
- **Apunta tus idas a la terminal.** Cada vez que salgas de Claude Code a la terminal o a GitHub (un `git`, un `gh`, un `hk-os`, editar un fichero a mano): la hora, para qué, y si se rompió algo.
- **No preguntes cómo funciona el OS** mientras trabajáis. Si algo no lo entiendes o te parece mal, apúntalo (hora y qué veías en la web): un estado incorrecto es justo lo que el ensayo busca.
- **Cierra las sesiones como siempre** (con `/exit` o cerrando la terminal, lo que hagas normalmente).

## Si algo falla
- **No apareces en la web:** ¿abriste una sesión **nueva** después de `hk-os unir`? ¿`hk-os unir` dijo «Unido a…»? Lo que hace tu demonio queda en `.git/hackathon/os/agente.log`.
- **La web no carga:** la red. Prueba con la IP de Tailscale que te pase quien coordina.
- **`hk-os: command not found`:** el alias (paso 5). Dentro de una sesión de `claude` funciona siempre: `! hk-os unir …`.
- **«el puerto N está ocupado»** al abrir la sesión: díselo a quien coordina (se cambia `puerto_agente` en `.hackathon/os.md`).

## Al terminar
- `hk-os recoger` deja un zip con los datos del OS de tu clon: tiempos, estados, avisos. **No lleva tu código ni el token**, pero sí nombres de usuario de GitHub. Pásaselo a quien coordina por un canal privado; nunca al repo.
- El token del ensayo no vale fuera de él, pero no lo publiques.
- Si el ensayo usa el reto real de una hackathon a la que os vais a presentar, lo que hagáis hoy es **trabajo previo**: no lo copies al repo del evento sin declararlo como diga la organización.
