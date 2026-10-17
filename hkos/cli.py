# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""hk-os: arranque del Hackathon OS (M8d, R-02). Se lanza desde cualquier carpeta del clon.

  hk-os relay [--ip IP] [--puerto 7777]   quien coordina: arranca el relay e imprime la línea para los demás
  hk-os unir <url> <token> [--persona <usuario>] [--remoto <url>]
                                          cada persona, una vez: guarda el relay y el token y prueba la conexión.
                                          Sin GitHub (M8h): --persona fija quién eres y --remoto apunta origin al
                                          remoto del equipo; sin --remoto, deshace lo que hizo un --remoto anterior
  hk-os remoto [--iniciar | --volver]     quien coordina, sin GitHub: el remoto del equipo (remoto.py)
  hk-os compilar [--seco]                 lleva las tareas de .hackathon/plan.md a issues hk-tarea (M8e)
  hk-os recoger [--salida <zip>]          tras el ensayo: los datos del OS de este clon, sin token (M8h)
  hk-os web                               abre la web de trabajo de este clon (M9a, con web_nueva: sí en os.md)
  hk-os agente …                          el demonio (lo lanza sesion.sh; ver agente.py)
"""
import html
import json
import os
import pathlib
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agente  # noqa: E402
import compilar  # noqa: E402
import relay  # noqa: E402
import remoto as remoto_mod  # noqa: E402
from red import equipo, web_nueva  # noqa: E402

USO = __doc__.split("\n\n", 1)[1]
# Lo que `recoger` nunca mete en el zip: secretos, los índices temporales y el remoto (código).
NO_RECOGER = {"token", "relay.url", "wip.index", "wip.pathspecs", "web.token", "nota.index", "web.html", "web.html.tmp",
              "token.tmp", "relay.url.tmp"}
# agente.vivo se renueva cada 15 s: con más de 60, el demonio está muerto. El criterio de scripts/os/delta.sh (VIVO_S,
# línea 22, y la comprobación de la línea 190).
VIVO_S = 60
LINUX = sys.platform.startswith("linux")
TCP_PROC = ("/proc/net/tcp", "/proc/net/tcp6")


def _escribe_privado(ruta, texto):
    """Un secreto en disco, 0600 desde que existe (O_EXCL en un .tmp y os.replace): sin la ventana de umask de
    open(…, "w") ni el modo de un fichero anterior. En Windows, el modo no cambia el ACL que hereda de la carpeta."""
    try:
        os.remove(ruta + ".tmp")
    except OSError:
        pass
    with os.fdopen(os.open(ruta + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as f:
        f.write(texto)
    os.replace(ruta + ".tmp", ruta)


def _principal(comun):
    return comun[:-len("/.git")] if comun.endswith("/.git") else "."


def _git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=60, env=dict(os.environ, **remoto_mod.ENTORNO_GIT))
    return r.returncode, r.stdout.strip()


def desfase(url, token):
    """Segundos que va adelantado este reloj respecto del relay (cabecera Date, resolución de 1 s); None si no responde."""
    req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            fecha = r.headers.get("Date")
    except (OSError, ValueError):
        return None
    try:
        return round(time.time() - parsedate_to_datetime(fecha).timestamp())
    except (TypeError, ValueError):
        return None


def _poner_remoto(principal, url_r, token, salida):
    """origin = el remoto del equipo, con el token en http.<url>.extraHeader (nunca en la URL). El origin de antes
    queda como «github», salvo que el clon ya saliera del remoto."""
    previo = _git(principal, "config", "--get", "hkos.remoto")[1]
    if previo and previo != url_r:
        _git(principal, "config", "--unset-all", f"http.{previo}.extraHeader")
        _git(principal, "config", "--unset-all", f"credential.{previo}.helper")
    rc, origin = _git(principal, "remote", "get-url", "origin")
    if rc == 0 and origin.rstrip("/") != url_r:
        if previo or _git(principal, "remote", "get-url", "github")[0] == 0:
            _git(principal, "remote", "set-url", "origin", url_r)
        else:
            _git(principal, "remote", "rename", "origin", "github")
            _git(principal, "remote", "add", "origin", url_r)
    elif rc != 0:
        _git(principal, "remote", "add", "origin", url_r)
    _git(principal, "config", "--replace-all", f"http.{url_r}.extraHeader", f"Authorization: Bearer {token}")
    _git(principal, "config", "--replace-all", f"credential.{url_r}.helper", "")   # ni guardar ni preguntar
    _git(principal, "config", "hkos.remoto", url_r)
    if _git(principal, "fetch", "-q", "origin")[0] != 0:
        salida(f"origin apunta al remoto del equipo ({url_r}), pero no responde todavía; prueba git fetch más tarde.")
        return
    _git(principal, "branch", "-q", "--set-upstream-to=origin/main", "main")
    salida(f"origin apunta al remoto del equipo ({url_r}); el token va en la configuración del clon, no en la URL.")


def _quitar_remoto(principal, salida):
    """Deshace _poner_remoto: origin vuelve a ser el de antes (GitHub) y se borra el token de la configuración."""
    previo = _git(principal, "config", "--get", "hkos.remoto")[1]
    if not previo:
        return
    _git(principal, "config", "--unset-all", f"http.{previo}.extraHeader")
    _git(principal, "config", "--unset-all", f"credential.{previo}.helper")
    _git(principal, "config", "--unset", "hkos.remoto")
    if _git(principal, "remote", "get-url", "github")[0] == 0:
        _git(principal, "remote", "remove", "origin")
        _git(principal, "remote", "rename", "github", "origin")
        _git(principal, "fetch", "-q", "origin")
        _git(principal, "branch", "-q", "--set-upstream-to=origin/main", "main")
        salida("origin vuelve a ser el de antes (GitHub) y el token del remoto ya no está en la configuración.")
    else:
        salida("El token del remoto ya no está en la configuración. Este clon salió del remoto: para volver a GitHub, "
               "git remote set-url origin <url del repo en GitHub>.")


def persona_del_clon(comun):
    """La persona del clon sin preguntar a nadie si se puede (como os_persona): yo-fijo, o la caché de hk_yo si solo
    hay una; si no, `gh api user`. None si no se sabe."""
    carpeta = os.path.join(comun, "hackathon")
    vistos = set()
    try:
        nombres = sorted(os.listdir(carpeta))
    except OSError:
        nombres = []
    for n in ["yo-fijo"] + [n for n in nombres if n.startswith("yo-") and n != "yo-fijo" and "." not in n]:
        try:
            with open(os.path.join(carpeta, n), encoding="utf-8") as f:
                p = f.read().strip().lower()
        except OSError:
            continue
        if n == "yo-fijo" and p:
            return p
        if p:
            vistos.add(p)
    if len(vistos) == 1:
        return vistos.pop()
    try:
        r = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip().lower() or None if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def estado_inicial(comun, principal, estado, persona):
    """M8h: estado.json y estado-equipo.md con el estado que acaba de dar el relay, igual que los escribe el demonio
    (agente.escribir_md). Así la primera sesión tras unirse ya recibe el bloque «Estado del equipo»: sin esto, el
    demonio que lanza su SessionStart aún no había escrito nada."""
    from datetime import datetime  # noqa: PLC0415
    import proyeccion  # noqa: PLC0415
    from red import conf  # noqa: PLC0415
    carpeta = os.path.join(comun, "hackathon", "os")
    try:
        viejo = float(conf(os.path.join(principal, ".hackathon", "os.md"), "umbral_viejo_s") or 300)
    except ValueError:
        viejo = 300
    tz = datetime.now().astimezone().tzinfo
    v = proyeccion.vista(estado, ahora=agente.ahora_iso(), umbral_viejo_s=viejo)
    textos = {"estado.json": json.dumps(estado, ensure_ascii=False),
              "estado-equipo.md": proyeccion.markdown(v, persona, os.path.join(carpeta, "estado.json").replace("\\", "/"),
                                                      tz=tz, epoch=int(time.time())),
              "reservas.tsv": proyeccion.reservas_tsv(v, persona, tz)}
    for nombre, texto in textos.items():
        ruta = os.path.join(carpeta, nombre)
        with open(ruta + ".tmp", "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        os.replace(ruta + ".tmp", ruta)


def unir(url, token, cwd=".", persona=None, remoto=None, salida=print):
    comun = agente.git_comun(cwd)
    principal = _principal(comun)
    url = url.rstrip("/")
    if not url.startswith("http://"):
        print(f"hk-os unir: «{url}» no es una URL http://<ip>:<puerto>", file=sys.stderr)
        return 2
    if remoto and not re.match(r"^http://[^/@\s]+/[^\s]+\.git$", remoto.rstrip("/")):
        print(f"hk-os unir: «{remoto}» no es la URL del remoto (http://<ip>:<puerto>/equipo.git, sin usuario ni token)",
              file=sys.stderr)
        return 2
    if persona is not None:
        persona = persona.lstrip("@").lower()
        tabla = {p["persona"] for p in equipo(os.path.join(principal, ".hackathon", "coordinacion.md"))}
        if persona not in tabla:
            print(f"hk-os unir: @{persona} no está en la tabla de .hackathon/coordinacion.md.", file=sys.stderr)
            return 2
    carpeta = os.path.join(comun, "hackathon", "os")
    os.makedirs(carpeta, exist_ok=True)
    for nombre, valor in (("relay.url", url), ("token", token)):
        _escribe_privado(os.path.join(carpeta, nombre), valor + "\n")
    if persona is not None:
        # Sin GitHub, la persona se declara (no se verifica): hk_yo la toma de aquí antes de preguntar a gh, y
        # sesion.sh avisa una vez si gh dice otra cosa cuando vuelve la red (ADR-0002, nota de M8h).
        with open(os.path.join(comun, "hackathon", "yo-fijo"), "w", encoding="utf-8", newline="\n") as f:
            f.write(persona + "\n")
        try:
            os.remove(os.path.join(comun, "hackathon", "yo-fijo.comprobado"))
        except OSError:
            pass
        salida(f"Este clon es de @{persona} (declarado con --persona).")
    if remoto:
        _poner_remoto(principal, remoto.rstrip("/"), token, salida)
    else:
        _quitar_remoto(principal, salida)
    req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            estado = json.loads(r.read())
    except urllib.error.HTTPError as ex:
        motivo = "el token no es el del relay" if ex.code == 401 else f"HTTP {ex.code}"
        print(f"Guardado en {carpeta}, pero el relay responde: {motivo}.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as ex:
        print(f"Guardado en {carpeta}, pero el relay no responde ({ex}). El demonio lo reintentará solo.", file=sys.stderr)
        return 1
    personas = ", ".join("@" + p["persona"] for p in estado.get("personas", []))
    salida(f"Unido a {url} (equipo: {personas or 'vacío'}). El demonio envía los eventos desde la próxima sesión.")
    quien = persona or persona_del_clon(comun)
    if quien and any(p["persona"] == quien for p in estado.get("personas", [])):
        estado_inicial(comun, principal, estado, quien)
    else:
        salida("No sé de quién es este clon todavía: el estado del equipo llegará con la primera sesión.")
    d = desfase(url, token)
    if d is not None:
        salida(f"Reloj: {d:+d} s respecto del relay" + (" (más de 30 s: ajusta la hora del portátil)." if abs(d) > 30 else "."))
    return 0


def recoger(cwd=".", destino=None, salida=print):
    """Zip con los datos del OS de este clon para analizar el ensayo (evals/coordinacion/ensayo/resumen.py): la carpeta
    <git común>/hackathon/os/ sin secretos ni el remoto (con sus carpetas vacías, como entregado/accion-<id>), el log
    de git y el desfase del reloj; a quien coordina, además, en contexto/, lo que el relay leía de origin/main y
    .hackathon/criterios.md (las notas de Anotar). No incluye la configuración de git (.git/config, donde va la
    cabecera del remoto)."""
    comun = agente.git_comun(cwd)
    principal = _principal(comun)
    base = os.path.join(comun, "hackathon", "os")
    if not os.path.isdir(base):
        salida("hk-os recoger: este clon no tiene datos del Hackathon OS.")
        return 1
    destino = destino or os.path.abspath(f"hk-os-{time.strftime('%Y%m%d-%H%M%S')}.zip")
    n = vacias = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, dirs, ficheros in os.walk(base):
            rel = os.path.relpath(raiz, base).replace("\\", "/")
            dirs[:] = [d for d in dirs if not (rel == "." and d == "remoto")]
            if rel != "." and not dirs and not ficheros:   # entregado/accion-<id>: la entrega es la carpeta (api.md §4)
                z.writestr(zipfile.ZipInfo.from_file(raiz, f"os/{rel}/"), b"")
                vacias += 1
            for f in ficheros:
                if f in NO_RECOGER:
                    continue
                z.write(os.path.join(raiz, f), "os/" + (f if rel == "." else f"{rel}/{f}"))
                n += 1
        _, log = _git(principal, "log", "--all", "--date=iso-strict", "--format=%H%x09%cd%x09%ae%x09%D%x09%s")
        z.writestr("git-log.tsv", log + "\n")
        if os.path.isdir(os.path.join(base, "relay")):   # quien coordina: lo que el relay leía de origin/main
            for ruta in (".hackathon/coordinacion.md", ".hackathon/plan.md", ".hackathon/autoridad.md", "docs/contratos.md",
                         ".hackathon/criterios.md"):
                rc, texto = _git(principal, "show", f"origin/main:{ruta}")
                if rc == 0:
                    z.writestr("contexto/" + ruta, texto + "\n")
        try:
            with open(os.path.join(base, "relay.url"), encoding="utf-8") as f:
                url = f.read().strip()
            with open(os.path.join(base, "token"), encoding="utf-8") as f:
                token = f.read().strip()
            d = desfase(url, token)
        except OSError:
            d = None
        z.writestr("desfase.txt", f"{d if d is not None else 'sin relay'}\n")
    salida(f"Recogidos {n} ficheros" + (f" y {vacias} carpetas vacías" if vacias else "")
           + f" en {destino} (sin token, sin relay.url, sin el remoto ni la configuración de git).")
    return 0


PAGINA_WEB = ('<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
              '<meta http-equiv="refresh" content="0;url={url}"><title>hk-os web</title>'
              '<a href="{url}">Abrir la web de trabajo</a>\n')


def abrir_navegador(url, carpeta):
    """Abre la web con el token en el fragmento. En Windows, con webbrowser: la línea de órdenes del navegador solo la
    leen el propio usuario y los administradores. En Linux (y macOS) cualquier usuario ve los argumentos de cualquier
    proceso (/proc/*/cmdline, ps; issue #6): el navegador recibe solo la ruta de web.html, una página de este clon,
    0600 como web.token, que redirige a la URL. False si no hay navegador."""
    if os.name == "nt":
        return webbrowser.open(url)
    ruta = os.path.join(carpeta, "web.html")
    _escribe_privado(ruta, PAGINA_WEB.format(url=html.escape(url, quote=True)))
    return webbrowser.open(pathlib.Path(ruta).as_uri())


def _direccion(hexa):
    """La dirección de /proc/net/tcp{,6}: palabras de 32 bits en el orden de bytes de la máquina, en hexadecimal."""
    return b"".join(struct.pack("=I", int(hexa[i:i + 8], 16)) for i in range(0, len(hexa), 8))


# Las direcciones en escucha que reciben una conexión a 127.0.0.1: la propia, 0.0.0.0 y, en tcp6, :: y las mapeadas.
A_127 = {socket.inet_pton(socket.AF_INET, d) for d in ("127.0.0.1", "0.0.0.0")} | {
    socket.inet_pton(socket.AF_INET6, d) for d in ("::", "::ffff:127.0.0.1", "::ffff:0.0.0.0")}


def escucha_mia(puerto, tablas=None, uid=None):
    """Linux: ¿es de este usuario quien escucha (estado 0A) en 127.0.0.1:<puerto>? Mira /proc/net/tcp y tcp6. False si
    no hay nadie o si alguno es de otro uid; None si no se puede leer ninguna tabla (entonces vale solo la hora)."""
    tablas = TCP_PROC if tablas is None else tablas
    uid = os.getuid() if uid is None else uid
    duenos, leida = [], False
    for tabla in tablas:
        try:
            with open(tabla, encoding="ascii", errors="replace") as f:
                lineas = f.read().splitlines()[1:]
        except OSError:
            continue
        leida = True
        for linea in lineas:
            c = linea.split()
            try:
                local, p = c[1].split(":")
                if c[3] == "0A" and int(p, 16) == puerto and _direccion(local) in A_127:
                    duenos.append(int(c[7]))
            except (IndexError, ValueError, struct.error):
                continue
    if not leida:
        return None
    return bool(duenos) and all(d == uid for d in duenos)


def web(cwd=".", abrir=None, salida=print):
    """M9a (api.md §4): abre http://127.0.0.1:<puerto>/#t=<token> si el demonio de este clon responde por /salud con
    su git común y sirve la web. El token va en el fragmento, que el navegador no envía; no se imprime ni va en los
    argumentos del navegador fuera de Windows (abrir_navegador). `abrir` (pruebas) recibe la URL con el token."""
    comun = agente.git_comun(cwd)
    principal = _principal(comun)
    carpeta = os.path.join(comun, "hackathon", "os")
    if not web_nueva(os.path.join(principal, ".hackathon", "os.md")):
        salida("hk-os web: la web de trabajo está apagada en este clon: pon «web_nueva: sí» en .hackathon/os.md "
               "(y súbelo, es para todo el equipo).")
        return 1
    # Issue #15: quien conteste /salud en el puerto de un agente.vivo huérfano (reinicio, kill -9) recibiría el token.
    # Antes de nada, la hora de agente.vivo y, en Linux, que el puerto sea de este usuario. El reto en /salud, que lo
    # cerraría del todo, cambia api.md §4 (pendiente).
    try:
        with open(os.path.join(carpeta, "agente.vivo"), encoding="utf-8") as f:
            puerto = int(f.readline().strip())
            hora = int(f.readline().strip())
        if time.time() - hora > VIVO_S or (LINUX and escucha_mia(puerto) is False):
            raise ValueError("agente.vivo viejo o puerto de otro usuario")
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/salud", timeout=2) as r:
            primera = r.read().decode("utf-8", errors="replace").split("\n", 1)[0]
    except (OSError, ValueError):
        primera, puerto = "", None
    esperada = f"hk-os {comun}"
    if os.name == "nt":                                  # en Windows, sin distinguir mayúsculas (como el arranque)
        primera, esperada = primera.lower(), esperada.lower()
    if primera != esperada:
        salida("hk-os web: el demonio de este clon no está en marcha. Se lanza al abrir una sesión de Claude Code "
               "aquí; después, vuelve a probar.")
        return 1
    try:
        with open(os.path.join(carpeta, "web.token"), encoding="utf-8") as f:
            token = f.read().strip()
    except OSError:
        token = ""
    url = f"http://127.0.0.1:{puerto}/"
    servida = False
    if token:
        req = urllib.request.Request(url + "v1/vista", headers={"X-HK-Token": token})
        try:
            urllib.request.urlopen(req, timeout=2).close()
            servida = True
        except urllib.error.HTTPError as ex:
            servida = ex.code == 503                     # sin estado.json todavía: la web ya está y lo dirá
        except OSError:
            pass
    if not servida:
        salida("hk-os web: el demonio de este clon arrancó antes de «web_nueva: sí». Cierra las sesiones de Claude "
               "Code de este clon y termina el proceso de hkos/agente.py; la próxima sesión lo lanza con la web.")
        return 1
    pagina = None
    if abrir:
        abrir(f"{url}#t={token}")
    else:
        try:
            abierta = abrir_navegador(f"{url}#t={token}", carpeta)
        except OSError as ex:
            salida(f"hk-os web: no he podido preparar la página para el navegador ({ex}).")
            return 1
        pagina = None if os.name == "nt" else pathlib.Path(carpeta, "web.html").as_uri()
        if not abierta:
            salida("hk-os web: no he encontrado un navegador." + ("" if pagina is None else
                   f" Abre a mano {pagina} (lleva el token: no la compartas)."))
            return 1
    salida(f"Web de trabajo: {url} (el token va aparte, en el fragmento; para volver a abrirla, hk-os web).")
    if pagina:                   # un navegador snap no lee repos fuera de /home ni bajo carpetas ocultas (issue #15)
        salida(f"Abre a mano {pagina} si el navegador no puede leerla (lleva el token: no la compartas).")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for flujo in (sys.stdout, sys.stderr):         # la consola de Windows (cp1252) no escribe «→» ni otros del plan
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    if not argv or argv[0] in ("-h", "--help"):
        print(USO)
        return 0
    orden, resto = argv[0], argv[1:]
    if orden == "unir":
        import argparse  # noqa: PLC0415
        p = argparse.ArgumentParser(prog="hk-os unir")
        p.add_argument("url")
        p.add_argument("token")
        p.add_argument("--persona")
        p.add_argument("--remoto")
        a = p.parse_args(resto)
        return unir(a.url, a.token, persona=a.persona, remoto=a.remoto)
    if orden == "relay":
        comun = agente.git_comun(".")
        principal = _principal(comun)
        relay.main(["--dir", os.path.join(comun, "hackathon", "os", "relay"),
                    "--equipo", os.path.join(principal, ".hackathon", "coordinacion.md"),
                    "--os", os.path.join(principal, ".hackathon", "os.md"), *resto])
        return 0
    if orden == "remoto":
        comun = agente.git_comun(".")
        return remoto_mod.main(resto, comun, _principal(comun))
    if orden == "compilar":
        return compilar.main(resto)
    if orden == "recoger":
        destino = resto[1] if len(resto) == 2 and resto[0] == "--salida" else None
        return recoger(destino=destino)
    if orden == "web":
        return web()
    if orden == "agente":
        return agente.main(resto)
    print(USO, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
