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
   Comprueba: `hk-os --help` tiene que listar `recoger` y `web`. Si falta alguno, tienes el kit viejo (paso 3).
6. **Red.** Si no vais a estar en la misma wifi, o quien coordina te lo pide: instala **Tailscale** (o ZeroTier) y entra en la red que te diga. Hazlo antes: la primera conexión necesita internet.

## El día

Es el ensayo realista: el día como sería en la hackathon, desde el enunciado.

| Momento | Qué haces |
|---|---|
| **Cadena del kit** (30–40 min, se cronometra) | Quien coordina lanza los comandos del kit con el enunciado. Tú lees el análisis y los enfoques y elegís juntos; si te lo pide, le das tus datos para `.hackathon/equipo.md` (puntos fuertes, lo que prefieres no hacer, disponibilidad, sistema del portátil, si presentas el pitch). Cuando el plan esté subido: `git clone <repo>` y entra en la carpeta. |
| **Arranque del OS** (≤ 10 min, se cronometra) | Quien coordina sube `.hackathon/os.md` con `activa: sí` y `web_nueva: sí`, y pega en el chat la línea de `hk-os unir`. Tú, en este orden: **`git pull`** (antes de abrir `claude`: el demonio lee `web_nueva` al arrancar); pega la línea `hk-os unir <url> <token>` en tu terminal (te dice tu desfase de reloj: si pasa de 30 s, ajusta la hora del portátil); abre `claude` en tu clon (si ya tenías una sesión abierta, ciérrala y abre una **nueva**: es la que lanza tu demonio); y, en otra terminal en el clon (o dentro de `claude` con `! hk-os web`), **`hk-os web`**. Se abre en tu navegador la web de **tu** demonio, en la cabina; arriba sale tu `@usuario`. |
| **Trabajo** (lo que acordéis; ≥ 2 h) | Tus tareas de `.hackathon/plan.md`, con Claude Code, como en la hackathon. Tu web, a la vista. |
| **Cierre** (15 min) | El cuestionario que te pase quien coordina, y `hk-os recoger` en tu clon. |

Si quien coordina hace el ensayo completo, hay además un bloque de 60 minutos **sin OS** antes del arranque: trabajas igual, sin `hk-os unir` todavía.

**Tu web.** Es tuya y solo sirve en tu portátil:
- La sirve tu demonio en `127.0.0.1`, con un token que `hk-os web` pone en la URL al abrirla; la página lo quita de la URL enseguida y lo guarda solo en esa pestaña.
- **En otro dispositivo no funciona** (un móvil, otro portátil, la pantalla de la sala): el demonio no escucha fuera de tu portátil y el token no pasa al copiar la URL. Para eso está la web de solo lectura del relay, la que quien coordina pone en una pantalla.
- **Si recargas la página o la cierras**, vuelve a abrirla con `hk-os web`.
- Tiene cuatro vistas, arriba: **Cabina** (lo tuyo; se abre con esta), **Red** (el equipo y por dónde llegan los datos), **Tablero** (las tareas por persona) y **Servicios** (lo de `.hackathon/servicios.md` y lo que no cuadra).
- Cada dato dice de dónde viene y «hace X». Lo viejo sale en gris.

**Mientras trabajáis:**
- **Tus tareas.** Al empezar una, pulsa **Reclamar** en su tarjeta de la web: asigna su issue `hk-tarea` con tu `gh` y una sesión tuya de Claude recibe un aviso con un texto fijo. Solo sale en las tareas libres (lista o pendiente, sin asignar) y solo vale si son tuyas o no tienen dueño; si la web dice que no, apunta qué decía. Al acabarla, cierra el issue en GitHub (eso no está en la web). Si puedes, empieza el asunto de tus commits con el ID de la tarea: `T07 · formulario de alta`.
- **Lo que diga el jurado, un mentor o la organización**, con **Anotar** (en la cabina). Va directo a `.hackathon/criterios.md` de `main`, sin tocar tu copia: lo verás en tu carpeta con el próximo `git pull`.
- **Apunta tus preguntas.** Cada vez que preguntes algo al resto (en voz alta o por chat) sobre quién hace qué, qué está subido o si vais a tocar lo mismo, apúntalo con la hora, o díselo a quien observa. Es lo más importante que mide el ensayo.
- **Apunta tus idas a la terminal.** Cada vez que salgas de Claude Code y de tu web a la terminal o a GitHub (un `git`, un `gh`, un `hk-os`, editar un fichero a mano): la hora, para qué, si se rompió algo y **qué botón de la web te lo habría ahorrado** (o «ninguno»). Con esto se decide qué botones vienen después de Anotar y Reclamar.
- **No preguntes cómo funciona el OS** mientras trabajáis. Si algo no lo entiendes o te parece mal, apúntalo (hora y qué veías en la web): un estado incorrecto es justo lo que el ensayo busca.
- **Cierra las sesiones como siempre** (con `/exit` o cerrando la terminal, lo que hagas normalmente).

## Si algo falla
- **No apareces en la web:** ¿abriste una sesión **nueva** después de `hk-os unir`? ¿`hk-os unir` dijo «Unido a…»? Lo que hace tu demonio queda en `.git/hackathon/os/agente.log`.
- **`hk-os web` no abre nada:** lee lo que dice.
  - «la web de trabajo está apagada»: te falta el `git pull` con `web_nueva: sí`.
  - «el demonio de este clon no está en marcha»: abre una sesión de `claude` en el clon y vuelve a probar.
  - «arrancó antes de "web_nueva: sí"»: cierra tus sesiones de `claude` y el proceso de `hkos/agente.py`, abre una sesión nueva y vuelve a probar.
- **«Tu demonio aún no tiene estado del equipo»:** no le llega nada del relay; repasa el `hk-os unir`.
- **«Sin conexión con tu demonio»** (una banda arriba y toda la página en gris y quieta): tu web lleva un rato (5 minutos, con lo de `os.md` por defecto) sin recibir nada de tu demonio.
  - Lo de abajo es de la hora que dice la banda: no te fíes de ello.
  - Lo normal es que el demonio se haya apagado: sale solo tras 30 minutos (`apagado_min`) sin ninguna sesión de `claude` abierta en tu clon.
  - Apunta la hora y qué estabas haciendo, abre (o mantén) una sesión de `claude` en el clon y vuelve a abrir la web con `hk-os web`. Cierra la pestaña vieja.
  - Si `hk-os web` abre y la pestaña nueva sigue sin datos, díselo a quien observa.
- **«Tu demonio no oye al relay desde HH:MM»** (en la cabecera, sin la página gris): tu web sí recibe de tu demonio, pero el estado del equipo (también el de tus tareas) es el último que llegó del relay. El problema es el relay o la red: díselo a quien coordina.
- **La web del relay (la de la pantalla) no carga:** la red. Prueba con la IP de Tailscale que te pase quien coordina.
- **`hk-os: command not found`:** el alias (paso 5). Dentro de una sesión de `claude` funciona siempre: `! hk-os unir …`.
- **«el puerto N está ocupado»** al abrir la sesión: díselo a quien coordina (se cambia `puerto_agente` en `.hackathon/os.md`).

## Al terminar
- `hk-os recoger` deja un zip con los datos del OS de tu clon: tiempos, estados, avisos y lo que reclamaste desde la web. **No lleva tu código ni los tokens** (ni el del relay ni el de tu web), pero sí nombres de usuario de GitHub. Pásaselo a quien coordina por un canal privado; nunca al repo.
- El token del ensayo no vale fuera de él, pero no lo publiques.
- Si el ensayo usa el reto real de una hackathon a la que os vais a presentar, lo que hagáis hoy es **trabajo previo**: no lo copies al repo del evento sin declararlo como diga la organización.
