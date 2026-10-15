# Arranque del Hackathon OS

Cómo pasar de un repo con el plan hecho a todo el equipo viéndose en la web **en 10 minutos o menos** (criterio 3 de M8h, R-02). El reloj empieza con la cadena del kit ya hecha (`.hackathon/plan.md` en `main` y la coordinación activa) y con lo de «El día antes» instalado.

Hay dos papeles: **quien coordina** (su portátil hace de relay y, sin GitHub, de remoto) y **cada persona** (también quien coordina, que además es una persona del equipo).

## El día antes (cada persona, unos 15 minutos)
1. **Git.** En Windows, Git for Windows (el portátil de quien coordina, 2.38 o más). En macOS, además, `brew install bash`: el OS necesita bash 5 y el de serie es el 3.2 (sin él, el OS se queda apagado en ese portátil y el kit funciona como siempre).
2. **uv** (un comando): `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` en Windows, `curl -LsSf https://astral.sh/uv/install.sh | sh` en macOS y Linux.
3. **Claude Code con el kit**: `/plugin marketplace add Mveradc/hackathon-kit` y `/plugin install hackathon-kit@hackathon-kit`.
4. **GitHub**: `gh auth login` con tu cuenta, y la invitación al repo del equipo (privado) aceptada.
5. **`hk-os` en tu terminal.** En Git Bash (o en tu shell), añade a `~/.bashrc`:
   ```bash
   alias hk-os='uv run --no-project --quiet "$(ls -d ~/.claude/plugins/cache/*/hackathon-kit/*/ | tail -1)hkos/cli.py"'
   ```
   Comprueba que funciona: `hk-os --help`. Si usas el kit con `claude --plugin-dir <carpeta>`, pon esa carpeta en lugar del `ls`.
6. **Red.** Si la wifi del evento puede aislar los portátiles entre sí o no es de confianza (el token viaja sin cifrar), instalad **Tailscale** o **ZeroTier** y entrad todos en la misma red **antes** del evento: los dos necesitan internet para la primera conexión.
7. **Quien coordina**: arranca una vez `hk-os relay` (y `hk-os remoto --iniciar` si vais a probar el modo sin GitHub) y acepta el aviso del cortafuegos de Windows («redes privadas»). Después, Ctrl+C.

## Los 10 minutos

| Min. | Quien coordina | Cada persona |
|---|---|---|
| 0–2 | En `.hackathon/os.md` (plantilla en el kit, `skills/hack-scaffold/templates/os.md`), `activa: sí`. `git add .hackathon/os.md && git commit -m "Hackathon OS activo" && git push` | Espera |
| 2–3 | En otra terminal, `hk-os relay`. Imprime la URL, el token, la línea de `hk-os unir` y la de la web. Déjala abierta | Espera |
| 3–4 | `hk-os compilar` (las tareas del plan pasan a issues `hk-tarea`; ~1 min con 28 tareas). Pega en el chat del equipo la línea de `hk-os unir` y la de la web | Espera |
| 4–7 | `hk-os unir <url> <token>` en su clon (también es una persona) | `git pull`, y `hk-os unir <url> <token>` (dice tu desfase de reloj con el relay: más de 30 s, ajusta la hora) |
| 7–9 | Abre (o reinicia) su sesión: `claude` en la carpeta del repo | Igual: una sesión **nueva** de `claude` en tu clon. Al empezar, lanza tu demonio |
| 9–10 | Abre la web (la URL con `#t=…`) | Abre la web y búscate en «Equipo» |

**Hecho cuando** la web muestra a todas las personas con una sesión activa y las tareas en sus columnas.

## Variante sin GitHub (sin internet, con LAN)
Las tareas salen de `.hackathon/plan.md` y el código va por un remoto en el portátil de quien coordina. Sin issues no se asigna ni se cierra nada: una tarea avanza por sus commits (con su ID al principio del asunto, `T07 · …`) y su push; una tarea sin código se da por hecha con `git commit --allow-empty -m "T07 · hecha"` y push.

| Min. | Quien coordina | Cada persona |
|---|---|---|
| 0–2 | En `os.md`, `activa: sí` y `github: no`; commit (el push, después) | Espera |
| 2–3 | En una terminal, `hk-os remoto --iniciar`: crea el remoto del equipo con vuestro `main`, apunta su `origin` a él (el de GitHub pasa a llamarse `github`) y lo sirve. `git push` (va al remoto). En otra terminal, `hk-os relay` | Espera |
| 3–4 | Pega en el chat la línea de `hk-os unir … --remoto …` que imprime el remoto, el token y la web | Espera |
| 4–7 | `hk-os unir <url> <token> --persona <tu usuario>` | `hk-os unir <url> <token> --persona <tu usuario> --remoto <url del remoto>` y `git pull`. ¿No tienes clon? `git -c http.extraHeader="Authorization: Bearer <token>" clone <url del remoto>`, y después el `unir` |
| 7–10 | Sesión nueva de `claude` y la web | Igual |

`--persona` declara quién eres, porque sin internet `gh` no puede decirlo; cuando vuelva la red, la sesión avisa si no coincide. El token no queda en la URL del remoto: va en la configuración del clon.

**Volver a GitHub**: con internet, quien coordina lanza `hk-os remoto --volver` (sube vuestro `main` a GitHub; si alguien subió a GitHub mientras tanto, para y te dice qué hacer) y cada persona, `hk-os unir <url> <token>` sin `--remoto`. Después, `github: sí` en `os.md`, reiniciad el relay y `hk-os compilar`. **Si nadie lo hace, el trabajo se queda solo en el portátil de quien coordina.**

## Si algo falla
- **La web no carga desde otro portátil**: el cortafuegos de quien coordina (paso 7 del día antes), o la red aísla los clientes: usad la IP de Tailscale o ZeroTier (`hk-os relay --ip <esa IP>`, y lo mismo en `hk-os remoto`). Sin ninguna de las dos, el móvil de alguien como punto de acceso, aunque no tenga datos.
- **«el puerto N está ocupado por otro programa»** al abrir la sesión: pon `puerto_agente: <otro>` en `os.md`.
- **No apareces en la web**: ¿has abierto una sesión **nueva** después de `hk-os unir`? ¿`hk-os unir` dijo «Unido a…»? El demonio deja lo que hace en `.git/hackathon/os/agente.log`.
- **`hk-os: command not found`**: el alias del día antes (paso 5), o la ruta completa: `uv run --no-project <carpeta del kit>/hkos/cli.py …`. Dentro de una sesión de Claude Code no hace falta: el kit pone `bin/hk-os` en su PATH (`! hk-os unir …`, comprobado en M8h). Para el relay y el remoto, mejor una terminal aparte: no acaban nunca.
- **macOS sin `brew install bash`**: la sesión avisa una vez y el OS sigue apagado en ese portátil; el resto del equipo no se entera de lo suyo.

## Al terminar
Cada persona, `hk-os recoger`: deja un zip con los datos del OS de su clon (sin el token ni el código) para analizarlo después (`evals/coordinacion/ensayo/`). Quien coordina para el relay (y el remoto) con Ctrl+C. Si usasteis `publicar_wip: sí`, borrad las refs que queden: `git push origin --delete refs/hackathon/wip/<usuario>`.
