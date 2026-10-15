# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""hk-os remoto (M8h, K-80; api.md §9): el remoto del equipo en el portátil de quien coordina, para trabajar sin
GitHub (sin internet, con LAN). Un repo `bare` servido por HTTP con `git http-backend` (viene con git), con el token
del relay y solo en 127.0.0.1, una IP privada de LAN o una de Tailscale. Es un proceso aparte del relay: el relay
sigue sin transportar código (constitución IX). Solo biblioteca estándar (ADR-0005).

  hk-os remoto --iniciar [--ip IP] [--puerto 7778]   crea el bare desde este clon, cambia origin y lo sirve
  hk-os remoto [--ip IP] [--puerto 7778]              lo sirve (ya iniciado)
  hk-os remoto --volver                               sube el main del equipo a GitHub y deja origin como estaba

El token va en una cabecera (`Authorization: Bearer <token>`, o Basic con el token de contraseña), nunca en la URL:
`hk-os unir … --remoto <url>` la deja en `http.<url>.extraHeader` del clon.
"""
import argparse
import base64
import hmac
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from red import Servidor  # noqa: E402

REPO = "equipo.git"
PUERTO = 7778
CUERPO_MAX = 1024 * 1024 * 1024          # 1 GB: un push de hackathon no llega
# Solo el protocolo «smart» de git sobre ese repo: nada de ficheros sueltos del bare.
RUTAS = {("GET", "/info/refs"), ("POST", "/git-upload-pack"), ("POST", "/git-receive-pack")}
SERVICIOS = {"service=git-upload-pack", "service=git-receive-pack"}
# git sin diálogos de credenciales ni esperas (memoria del kit: «publicar con cierre seguro»). GIT_ASKPASS vacío: con un
# 401, git llama al askpass heredado (el de VS Code, si la sesión viene de allí) y se queda esperando (M8h).
ENTORNO_GIT = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
               "GIT_ASKPASS": "", "SSH_ASKPASS": ""}


def _git(cwd, *args, timeout=120):
    env = dict(os.environ, **ENTORNO_GIT)
    try:
        r = subprocess.run(["git", "-C", cwd, "-c", "credential.interactive=false", "-c", "core.askPass=", *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError) as ex:
        return 1, "", str(ex)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def token_del_equipo(comun):
    """El token del relay (relay/token), creado como lo crea el relay si aún no existe: el remoto y el relay usan el
    mismo, así que cada persona solo recibe uno."""
    carpeta = os.path.join(comun, "hackathon", "os", "relay")
    ruta = os.path.join(carpeta, "token")
    try:
        with open(ruta, encoding="utf-8") as f:
            t = f.read().strip()
        if t:
            return t
    except OSError:
        pass
    os.makedirs(carpeta, exist_ok=True)
    t = secrets.token_urlsafe(24)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(t + "\n")
    return t


def autorizado(cabecera, token):
    """`Bearer <token>` o `Basic base64(<cualquiera>:<token>)`, comparado en tiempo constante."""
    if not cabecera:
        return False
    tipo, _, valor = cabecera.strip().partition(" ")
    valor = valor.strip()
    if tipo.lower() == "basic":
        try:
            valor = base64.b64decode(valor, validate=True).decode("utf-8").partition(":")[2]
        except (ValueError, UnicodeDecodeError):
            return False
    elif tipo.lower() != "bearer":
        return False
    return hmac.compare_digest(valor.encode("utf-8"), token.encode("utf-8"))


def _cuerpo(rfile, cabeceras, destino):
    """Copia el cuerpo de la petición a `destino` (Content-Length o chunked, que git usa en los push de más de 1 MB).
    Devuelve los bytes copiados; ValueError si está mal formado o pasa de CUERPO_MAX."""
    total = 0
    if "chunked" in (cabeceras.get("Transfer-Encoding") or "").lower():
        while True:
            linea = rfile.readline(1024)
            if not linea:
                raise ValueError("chunked cortado")
            n = int(linea.split(b";")[0].strip() or b"0", 16)
            if n == 0:
                while rfile.readline(1024) not in (b"\r\n", b"\n", b""):   # trailers
                    pass
                return total
            total += n
            if total > CUERPO_MAX:
                raise ValueError("cuerpo demasiado grande")
            while n:
                trozo = rfile.read(min(n, 1 << 16))
                if not trozo:
                    raise ValueError("chunked cortado")
                destino.write(trozo)
                n -= len(trozo)
            rfile.readline(1024)                                     # el \r\n de detrás de cada trozo
    n = int(cabeceras.get("Content-Length") or 0)
    if n < 0 or n > CUERPO_MAX:
        raise ValueError("Content-Length no válido")
    while n:
        trozo = rfile.read(min(n, 1 << 16))
        if not trozo:
            raise ValueError("cuerpo cortado")
        destino.write(trozo)
        total += len(trozo)
        n -= len(trozo)
    return total


def manejador(raiz, token, registro=None):
    """raiz: la carpeta que contiene equipo.git. registro(texto): una línea por petición (sin el token)."""
    registro = registro or (lambda s: None)

    class Manejador(BaseHTTPRequestHandler):
        server_version = "hk-os-remoto"
        protocol_version = "HTTP/1.0"                # la respuesta de http-backend acaba al cerrar la conexión

        def log_message(self, *args):
            pass

        def _no(self, codigo, texto, autenticar=False):
            cuerpo = (texto + "\n").encode("utf-8")
            self.send_response(codigo)
            if autenticar:
                self.send_header("WWW-Authenticate", 'Basic realm="hk-os"')
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _servir(self, metodo):
            ruta, _, consulta = self.path.partition("?")
            prefijo = "/" + REPO
            sub = ruta[len(prefijo):] if ruta.startswith(prefijo + "/") else None
            if sub is None or (metodo, sub) not in RUTAS or (sub == "/info/refs" and consulta not in SERVICIOS):
                return self._no(404, "no existe")
            if not autorizado(self.headers.get("Authorization"), token):
                registro(f"{self.client_address[0]} {metodo} {sub} 401")
                return self._no(401, "falta el token del equipo (hk-os unir … --remoto)", autenticar=True)
            env = {k: v for k, v in os.environ.items() if k.upper() in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME",
                                                                        "USERPROFILE", "PATHEXT", "COMSPEC")}
            env.update(GIT_PROJECT_ROOT=raiz, GIT_HTTP_EXPORT_ALL="1", PATH_INFO=prefijo + sub, QUERY_STRING=consulta,
                       REQUEST_METHOD=metodo, REMOTE_USER="hk-os", REMOTE_ADDR=self.client_address[0],
                       CONTENT_TYPE=self.headers.get("Content-Type") or "", GATEWAY_INTERFACE="CGI/1.1",
                       SERVER_PROTOCOL="HTTP/1.0")
            for k in ("Git-Protocol", "Content-Encoding", "Accept-Encoding"):
                if self.headers.get(k):
                    env["HTTP_" + k.upper().replace("-", "_")] = self.headers[k]
            with tempfile.TemporaryFile() as entrada:
                try:
                    n = _cuerpo(self.rfile, self.headers, entrada) if metodo == "POST" else 0
                except ValueError as ex:
                    return self._no(400, str(ex))
                entrada.seek(0)
                env["CONTENT_LENGTH"] = str(n)
                try:
                    p = subprocess.Popen(["git", "http-backend"], stdin=entrada, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, env=env)
                except OSError as ex:
                    return self._no(500, f"no puedo lanzar git http-backend: {ex}")
                # Cabeceras CGI hasta la línea vacía; «Status:» da el código.
                codigo, cabeceras = 200, []
                while True:
                    linea = p.stdout.readline()
                    if not linea or linea in (b"\r\n", b"\n"):
                        break
                    k, _, v = linea.decode("latin-1").rstrip("\r\n").partition(":")
                    if k.lower() == "status":
                        codigo = int(v.strip().split()[0])
                    else:
                        cabeceras.append((k, v.strip()))
                self.send_response(codigo)
                for k, v in cabeceras:
                    self.send_header(k, v)
                self.end_headers()
                shutil.copyfileobj(p.stdout, self.wfile, 1 << 16)
                err = p.stderr.read().decode("utf-8", "replace").strip()
                p.wait()
                p.stdout.close()
                p.stderr.close()
            registro(f"{self.client_address[0]} {metodo} {sub} {codigo}" + (f" · {err[:200]}" if err else ""))

        def do_GET(self):
            self._servir("GET")

        def do_POST(self):
            self._servir("POST")

    return Manejador


def iniciar(principal, comun, salida=print):
    """Crea <git común>/hackathon/os/remoto/equipo.git con el main del equipo (origin/main si existe; si no, HEAD) y
    deja este clon apuntando a él: el origin de GitHub pasa a llamarse `github`. Si ya estaba iniciado, no toca nada."""
    bare = os.path.join(comun, "hackathon", "os", "remoto", REPO)
    _, url, _ = _git(principal, "remote", "get-url", "origin")
    if os.path.isdir(bare) and os.path.normcase(os.path.abspath(url or "")) == os.path.normcase(os.path.abspath(bare)):
        salida(f"El remoto del equipo ya está iniciado en {bare}.")
        return bare
    if os.path.isdir(bare):
        salida(f"hk-os remoto: {bare} ya existe, pero origin no apunta a él. No toco nada.")
        return None
    rc, base, _ = _git(principal, "rev-parse", "--verify", "-q", "refs/remotes/origin/main")
    if rc:
        rc, base, _ = _git(principal, "rev-parse", "--verify", "-q", "HEAD")
    if rc:
        salida("hk-os remoto: este clon no tiene ningún commit.")
        return None
    os.makedirs(os.path.dirname(bare), exist_ok=True)
    rc, _, err = _git(principal, "init", "-q", "--bare", "-b", "main", bare)
    if rc:
        salida(f"hk-os remoto: no puedo crear el bare: {err}")
        return None
    rc, _, err = _git(principal, "push", "-q", bare, f"{base}:refs/heads/main")
    if rc:
        salida(f"hk-os remoto: no puedo copiar main al bare: {err}")
        return None
    rc, _, _ = _git(principal, "remote", "get-url", "github")
    if url and rc:                                   # el origin de siempre se queda como «github»
        _git(principal, "remote", "rename", "origin", "github")
    elif url:
        _git(principal, "remote", "remove", "origin")
    _git(principal, "remote", "add", "origin", bare)
    _git(principal, "fetch", "-q", "origin")
    _git(principal, "branch", "-q", "--set-upstream-to=origin/main", "main")
    salida(f"Remoto del equipo creado en {bare} con main = {base[:12]}; origin apunta a él"
           + (" y el de GitHub se llama ahora «github»." if url else "."))
    return bare


def volver(principal, salida=print):
    """Sube el main del equipo (origin/main del bare) a GitHub y deja origin como estaba. Si los dos main han
    divergido, avisa y para sin fusionar. Devuelve 0 bien, 1 si para."""
    rc, _, _ = _git(principal, "remote", "get-url", "github")
    if rc:
        salida("hk-os remoto --volver: este clon no tiene el remoto «github» (no se inició con hk-os remoto --iniciar).")
        return 1
    for r in ("origin", "github"):
        rc, _, err = _git(principal, "fetch", "-q", r)
        if rc:
            salida(f"hk-os remoto --volver: no puedo traer «{r}»: {err or 'sin respuesta'}. No he cambiado nada.")
            return 1
    _, equipo, _ = _git(principal, "rev-parse", "refs/remotes/origin/main")
    rc, gh, _ = _git(principal, "rev-parse", "--verify", "-q", "refs/remotes/github/main")
    subir = bool(rc)                                 # GitHub sin main: se sube
    if not rc and gh == equipo:
        salida("GitHub ya tiene el main del equipo: no hace falta subir nada.")
    elif not rc and _git(principal, "merge-base", "--is-ancestor", equipo, gh)[0] == 0:
        salida("GitHub ya tiene todo el main del equipo (y algo más): no hace falta subir nada.")
    elif not rc and _git(principal, "merge-base", "--is-ancestor", gh, equipo)[0] != 0:
        salida("hk-os remoto --volver: el main de GitHub y el del equipo han divergido (alguien subió a GitHub "
               "mientras tanto). No fusiono por mi cuenta: fusiona github/main con origin/main, súbelo al remoto "
               "del equipo y vuelve a lanzar hk-os remoto --volver. No he cambiado nada.")
        return 1
    elif not rc:
        subir = True                                 # GitHub va por detrás: avance rápido
    if subir:
        rc, _, err = _git(principal, "push", "-q", "github", f"{equipo}:refs/heads/main")
        if rc:
            salida(f"hk-os remoto --volver: GitHub no acepta el push: {err}. No he cambiado nada.")
            return 1
        salida(f"Subido a GitHub el main del equipo ({equipo[:12]}).")
    _, bare, _ = _git(principal, "remote", "get-url", "origin")
    _git(principal, "remote", "remove", "origin")
    _git(principal, "remote", "rename", "github", "origin")
    _git(principal, "fetch", "-q", "origin")
    _git(principal, "branch", "-q", "--set-upstream-to=origin/main", "main")
    salida(f"origin vuelve a ser GitHub. El bare se queda en {bare} por si acaso. Cada persona: hk-os unir <relay> "
           "<token> (sin --remoto); en os.md, github: sí; reinicia el relay y lanza hk-os compilar.")
    return 0


def servir(raiz, token, ip, puerto, aviso=print):
    import relay   # noqa: PLC0415 (ip_permitida; relay.py importa mucho más, solo hace falta aquí)
    if not relay.ip_permitida(ip):
        raise SystemExit(f"hk-os remoto: {ip} no es 127.0.0.1, una IP privada de LAN ni una de Tailscale; el remoto "
                         "no escucha ahí. Indica otra con --ip.")
    servidor = Servidor((ip, puerto), manejador(raiz, token, registro=lambda s: aviso(f"remoto: {s}")))
    url = f"http://{ip}:{servidor.server_address[1]}/{REPO}"
    aviso(f"Remoto del equipo en {url} (el token es el del relay).")
    aviso(f"Cada persona, en su clon: hk-os unir <relay> <token> --persona <usuario> --remoto {url}")
    aviso(f'Clonar de cero: git -c http.extraHeader="Authorization: Bearer <token>" clone {url}')
    try:
        servidor.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


def main(argv, comun, principal):
    p = argparse.ArgumentParser(prog="hk-os remoto", description="Remoto del equipo sin GitHub (api.md §9)")
    p.add_argument("--iniciar", action="store_true")
    p.add_argument("--volver", action="store_true")
    p.add_argument("--ip")
    p.add_argument("--puerto", type=int, default=PUERTO)
    a = p.parse_args(argv)
    if a.volver:
        return volver(principal)
    bare = os.path.join(comun, "hackathon", "os", "remoto", REPO)
    if a.iniciar and not iniciar(principal, comun):
        return 1
    if not os.path.isdir(bare):
        print("hk-os remoto: no hay remoto del equipo; créalo con hk-os remoto --iniciar.", file=sys.stderr)
        return 1
    import relay   # noqa: PLC0415
    ip = a.ip or relay.ip_de_lan()
    if not ip:
        raise SystemExit("hk-os remoto: no encuentro la IP de la LAN; indícala con --ip.")
    servir(os.path.dirname(bare), token_del_equipo(comun), ip, a.puerto, aviso=lambda s: print(s, flush=True))
    return 0


if __name__ == "__main__":
    print("Se lanza con hk-os remoto (cli.py).", file=sys.stderr)
    sys.exit(2)
