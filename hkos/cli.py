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
  hk-os agente …                          el demonio (lo lanza sesion.sh; ver agente.py)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agente  # noqa: E402
import compilar  # noqa: E402
import relay  # noqa: E402
import remoto as remoto_mod  # noqa: E402
from red import equipo  # noqa: E402

USO = __doc__.split("\n\n", 1)[1]
# Lo que `recoger` nunca mete en el zip: secretos, el índice temporal y el remoto (código).
NO_RECOGER = {"token", "relay.url", "wip.index", "wip.pathspecs"}


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
        with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
            f.write(valor + "\n")
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
    d = desfase(url, token)
    if d is not None:
        salida(f"Reloj: {d:+d} s respecto del relay" + (" (más de 30 s: ajusta la hora del portátil)." if abs(d) > 30 else "."))
    return 0


def recoger(cwd=".", destino=None, salida=print):
    """Zip con los datos del OS de este clon para analizar el ensayo (evals/coordinacion/ensayo/resumen.py): la carpeta
    <git común>/hackathon/os/ sin secretos ni el remoto, el log de git y el desfase del reloj. No incluye la
    configuración de git (.git/config, donde va la cabecera del remoto)."""
    comun = agente.git_comun(cwd)
    principal = _principal(comun)
    base = os.path.join(comun, "hackathon", "os")
    if not os.path.isdir(base):
        salida("hk-os recoger: este clon no tiene datos del Hackathon OS.")
        return 1
    destino = destino or os.path.abspath(f"hk-os-{time.strftime('%Y%m%d-%H%M%S')}.zip")
    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, dirs, ficheros in os.walk(base):
            rel = os.path.relpath(raiz, base).replace("\\", "/")
            dirs[:] = [d for d in dirs if not (rel == "." and d == "remoto")]
            for f in ficheros:
                if f in NO_RECOGER:
                    continue
                z.write(os.path.join(raiz, f), "os/" + (f if rel == "." else f"{rel}/{f}"))
                n += 1
        _, log = _git(principal, "log", "--all", "--date=iso-strict", "--format=%H%x09%cd%x09%ae%x09%D%x09%s")
        z.writestr("git-log.tsv", log + "\n")
        if os.path.isdir(os.path.join(base, "relay")):   # quien coordina: lo que el relay leía de origin/main
            for ruta in (".hackathon/coordinacion.md", ".hackathon/plan.md", ".hackathon/autoridad.md", "docs/contratos.md"):
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
    salida(f"Recogidos {n} ficheros en {destino} (sin token, sin relay.url, sin el remoto ni la configuración de git).")
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
    if orden == "agente":
        return agente.main(resto)
    print(USO, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
