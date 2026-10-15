"""K-80 (M8h): el remoto del equipo sin GitHub (hkos/remoto.py, api.md §9) y lo que hace `hk-os unir --remoto`.
Clonar, push de más de 1 MB (git lo manda troceado), fetch, 401 sin token o con otro, rutas fuera del repo, el token
fuera de la URL, `--volver` (avance rápido y divergencia) y deshacer el remoto en cada clon. Sin red: 127.0.0.1.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import cli  # noqa: E402
import remoto  # noqa: E402
from red import Servidor  # noqa: E402

TOKEN = "token-de-prueba-1234"
# Ni diálogos de credenciales ni el gestor del sistema: una prueba que falla no debe abrir una ventana.
ENTORNO = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_CONFIG_NOSYSTEM="1", GIT_ASKPASS="",
               SSH_ASKPASS="")


def git(cwd, *args, ok=True):
    r = subprocess.run(["git", "-c", "credential.helper=", "-c", "core.askPass=", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENTORNO, timeout=60)
    if ok and r.returncode:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr}")
    return r


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


class Remoto(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.github = os.path.join(self.d, "github.git")         # hace de GitHub
        self.coord = os.path.join(self.d, "coord")
        git(self.d, "init", "-q", "--bare", "-b", "main", self.github)
        git(self.d, "clone", "-q", self.github, self.coord)
        self.identidad(self.coord)
        with open(os.path.join(self.coord, "README.md"), "w", encoding="utf-8") as f:
            f.write("hola\n")
        git(self.coord, "add", ".")
        git(self.coord, "commit", "-qm", "T01 · inicio")
        git(self.coord, "push", "-q", "origin", "HEAD:main")
        self.comun = os.path.join(self.coord, ".git")
        salida = []
        self.bare = remoto.iniciar(self.coord, self.comun, salida=salida.append)
        self.assertTrue(self.bare and os.path.isdir(self.bare), salida)
        srv = Servidor(("127.0.0.1", 0), remoto.manejador(os.path.dirname(self.bare), TOKEN))
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        self.url = f"http://127.0.0.1:{srv.server_address[1]}/equipo.git"

    def identidad(self, r):
        git(r, "config", "user.email", "x@y")
        git(r, "config", "user.name", "x")

    def clonar(self, nombre, cabecera=f"Authorization: Bearer {TOKEN}", ok=True):
        destino = os.path.join(self.d, nombre)
        r = git(self.d, "-c", f"http.extraHeader={cabecera}", "clone", "-q", self.url, destino, ok=ok)
        if ok:
            self.identidad(destino)
        return destino, r

    def pedir(self, ruta, auth=None, metodo="GET"):
        req = urllib.request.Request(self.url.rsplit("/", 1)[0] + ruta, method=metodo, data=b"" if metodo == "POST" else None,
                                     headers={"Authorization": auth} if auth else {})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as ex:
            return ex.code

    def test_iniciar_deja_origin_en_el_bare_y_github_aparte(self):
        self.assertEqual(os.path.normcase(git(self.coord, "remote", "get-url", "origin").stdout.strip()),
                         os.path.normcase(self.bare))
        self.assertEqual(git(self.coord, "remote", "get-url", "github").stdout.strip(), self.github)
        self.assertEqual(git(self.bare, "rev-parse", "main").stdout, git(self.coord, "rev-parse", "HEAD").stdout)
        salida = []
        self.assertEqual(remoto.iniciar(self.coord, self.comun, salida=salida.append), self.bare)   # idempotente
        self.assertIn("ya está iniciado", salida[0])

    def test_clonar_push_grande_y_fetch(self):
        b, _ = self.clonar("b")
        with open(os.path.join(b, "grande.bin"), "wb") as f:
            f.write(os.urandom(3 * 1024 * 1024))                  # sin comprimir: > 1 MB en el push (chunked)
        git(b, "add", ".")
        git(b, "commit", "-qm", "T02 · datos")
        git(b, "-c", f"http.extraHeader=Authorization: Bearer {TOKEN}", "push", "-q", "origin", "HEAD:main")
        sha = git(b, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(git(self.bare, "rev-parse", "main").stdout.strip(), sha)
        git(self.coord, "fetch", "-q", "origin")
        self.assertEqual(git(self.coord, "rev-parse", "origin/main").stdout.strip(), sha)
        c, _ = self.clonar("c")                                   # y un clon nuevo trae el fichero grande
        self.assertEqual(os.path.getsize(os.path.join(c, "grande.bin")), 3 * 1024 * 1024)
        # Una ref de trabajo en curso forzada (Publicador de M8g) también entra.
        git(b, "-c", f"http.extraHeader=Authorization: Bearer {TOKEN}", "push", "-q", "--force", "origin",
            f"{sha}:refs/hackathon/wip/persona-b")
        self.assertEqual(git(self.bare, "rev-parse", "refs/hackathon/wip/persona-b").stdout.strip(), sha)

    def test_401_sin_token_o_con_otro(self):
        _, r = self.clonar("sin", cabecera="X-Nada: 1", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.d, "sin", "README.md")))
        _, r = self.clonar("otro", cabecera="Authorization: Bearer otro-token", ok=False)
        self.assertNotEqual(r.returncode, 0)
        q = "/equipo.git/info/refs?service=git-upload-pack"
        self.assertEqual(self.pedir(q), 401)
        self.assertEqual(self.pedir(q, "Bearer otro"), 401)
        self.assertEqual(self.pedir(q, "Bearer " + TOKEN), 200)
        basic = base64.b64encode(f"hk:{TOKEN}".encode()).decode()
        self.assertEqual(self.pedir(q, "Basic " + basic), 200)
        self.assertEqual(self.pedir("/equipo.git/info/refs?service=git-receive-pack", "Bearer x", "GET"), 401)

    def test_rutas_fuera_del_repo(self):
        auth = "Bearer " + TOKEN
        for ruta in ("/otro.git/info/refs?service=git-upload-pack", "/equipo.git/HEAD", "/equipo.git/config",
                     "/equipo.git/objects/info/packs", "/equipo.git/info/refs", "/equipo.git/info/refs?service=otro",
                     "/equipo.git/../github.git/info/refs?service=git-upload-pack", "/", "/equipo.git"):
            self.assertEqual(self.pedir(ruta, auth), 404, ruta)
        self.assertEqual(self.pedir("/equipo.git/git-upload-pack", auth, "GET"), 404)

    def test_unir_pone_el_token_fuera_de_la_url_y_lo_quita(self):
        # Clon de antes del evento (de GitHub): --remoto lo cambia y sin --remoto vuelve a GitHub.
        a = os.path.join(self.d, "a")
        git(self.d, "clone", "-q", self.github, a)
        salida = []
        cli._poner_remoto(a, self.url, TOKEN, salida.append)
        self.assertEqual(git(a, "remote", "get-url", "origin").stdout.strip(), self.url)
        self.assertEqual(git(a, "remote", "get-url", "github").stdout.strip(), self.github)
        self.assertNotIn(TOKEN, git(a, "remote", "-v").stdout)
        self.assertEqual(git(a, "rev-parse", "origin/main").stdout, git(self.bare, "rev-parse", "main").stdout)
        self.assertEqual(git(a, "config", "--get", f"http.{self.url}.extraHeader").stdout.strip(),
                         f"Authorization: Bearer {TOKEN}")
        r = git(a, "fetch", "origin")                              # sin -c: con la configuración del clon
        self.assertEqual(r.returncode, 0, r.stderr)
        cli._quitar_remoto(a, salida.append)
        self.assertEqual(git(a, "remote", "get-url", "origin").stdout.strip(), self.github)
        self.assertNotEqual(git(a, "remote", "get-url", "github", ok=False).returncode, 0)
        self.assertNotIn(TOKEN, leer(os.path.join(a, ".git", "config")))
        # Clon hecho durante el evento (del remoto): no hay GitHub al que volver; se quita el token y se dice.
        b, _ = self.clonar("b")
        cli._poner_remoto(b, self.url, TOKEN, salida.append)
        self.assertNotEqual(git(b, "remote", "get-url", "github", ok=False).returncode, 0)
        cli._quitar_remoto(b, salida.append)
        self.assertIn("salió del remoto", salida[-1])
        self.assertNotIn(TOKEN, leer(os.path.join(b, ".git", "config")))

    def test_volver_avance_rapido(self):
        b, _ = self.clonar("b")
        with open(os.path.join(b, "x.txt"), "w") as f:
            f.write("x\n")
        git(b, "add", ".")
        git(b, "commit", "-qm", "T03 · x")
        git(b, "-c", f"http.extraHeader=Authorization: Bearer {TOKEN}", "push", "-q", "origin", "HEAD:main")
        salida = []
        self.assertEqual(remoto.volver(self.coord, salida=salida.append), 0, salida)
        self.assertEqual(git(self.github, "rev-parse", "main").stdout, git(b, "rev-parse", "HEAD").stdout)
        self.assertEqual(git(self.coord, "remote", "get-url", "origin").stdout.strip(), self.github)
        self.assertNotEqual(git(self.coord, "remote", "get-url", "github", ok=False).returncode, 0)
        self.assertTrue(os.path.isdir(self.bare))                  # el bare se queda, por si acaso

    def test_volver_con_main_divergido_para_sin_tocar_nada(self):
        b, _ = self.clonar("b")
        git(b, "commit", "-q", "--allow-empty", "-m", "T04 · en el remoto")
        git(b, "-c", f"http.extraHeader=Authorization: Bearer {TOKEN}", "push", "-q", "origin", "HEAD:main")
        g = os.path.join(self.d, "g")                               # alguien sube a GitHub por otro lado
        git(self.d, "clone", "-q", self.github, g)
        self.identidad(g)
        git(g, "commit", "-q", "--allow-empty", "-m", "T05 · en GitHub")
        git(g, "push", "-q", "origin", "HEAD:main")
        antes = git(self.github, "rev-parse", "main").stdout
        salida = []
        self.assertEqual(remoto.volver(self.coord, salida=salida.append), 1)
        self.assertIn("divergido", salida[-1])
        self.assertEqual(git(self.github, "rev-parse", "main").stdout, antes)
        self.assertEqual(os.path.normcase(git(self.coord, "remote", "get-url", "origin").stdout.strip()),
                         os.path.normcase(self.bare))
        self.assertEqual(git(self.coord, "remote", "get-url", "github").stdout.strip(), self.github)

    def test_autorizado(self):
        self.assertTrue(remoto.autorizado(f"Bearer {TOKEN}", TOKEN))
        self.assertTrue(remoto.autorizado("Basic " + base64.b64encode(f"x:{TOKEN}".encode()).decode(), TOKEN))
        for mala in (None, "", "Bearer", f"Token {TOKEN}", "Basic !!!", "Basic " + base64.b64encode(b"x").decode()):
            self.assertFalse(remoto.autorizado(mala, TOKEN), mala)


if __name__ == "__main__":
    unittest.main()
