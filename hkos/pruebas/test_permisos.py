"""Issue #15 (hallazgo 12) y PR #19: los ficheros privados del OS (token, relay.url, web.token, web.html) solo los lee y
escribe su usuario. En Linux y macOS, 0600; en Windows, un DACL sin herencia con una sola entrada, la del usuario. Las
pruebas de Windows trabajan en una carpeta «fuera del perfil»: una temporal con el ACL de C:\\ (Usuarios
autentificados con modificar y Usuarios con leer, heredables) y, si se puede crear, una de verdad en la raíz de la
unidad del sistema. El ACL se lee con ctypes (permisos.acl) y, aparte, con icacls.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import contextlib
import io
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import agente as agente_mod  # noqa: E402
import cli  # noqa: E402
import permisos  # noqa: E402

WINDOWS = os.name == "nt"
CONTROL_TOTAL = 0x1F01FF
SECRETOS = ("token", "relay.url", "web.token", "web.html")


def git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True)


def unir(repo, token):
    with socket.socket() as s:                                  # un puerto cerrado: el relay no responde
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    with contextlib.redirect_stderr(io.StringIO()):
        return cli.unir(f"http://127.0.0.1:{puerto}", token, cwd=repo, salida=lambda *_: None)


def demonio(repo):
    os.makedirs(os.path.join(repo, ".hackathon"), exist_ok=True)
    with open(os.path.join(repo, ".hackathon", "os.md"), "w", encoding="utf-8") as f:
        f.write("# Hackathon OS\nactiva: sí\nweb_nueva: sí\n")
    return agente_mod.Agente(repo, "persona-b", reloj=lambda: 1000.0, ahora=lambda: "2026-10-17T10:00:00Z")


def escribe_normal(ruta, texto):
    """Como se escribían antes: open(…, "w"), con lo que herede de la carpeta (o 0644 con umask 022)."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    if not WINDOWS:
        os.chmod(ruta, 0o644)


if WINDOWS:
    import ctypes
    from ctypes import wintypes

    _SetFileSecurityW = ctypes.WinDLL("advapi32", use_last_error=True).SetFileSecurityW
    _SetFileSecurityW.restype = wintypes.BOOL
    _SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    _LocalFree = ctypes.WinDLL("kernel32").LocalFree
    _LocalFree.argtypes = [ctypes.c_void_p]

    def como_la_raiz(carpeta):
        """El ACL que hereda una carpeta creada en C:\\ por un usuario: la suya, más Usuarios autentificados (AU) con
        modificar y Usuarios (BU) con leer y ejecutar, heredables por los ficheros (OI) y las carpetas (CI)."""
        sd = permisos.descriptor(f"D:PAI(A;OICI;FA;;;{permisos.sid_propio()})(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
                                 "(A;OICI;0x1301bf;;;AU)(A;OICI;0x1200a9;;;BU)")
        try:
            if not _SetFileSecurityW(carpeta, 0x4, sd):              # DACL_SECURITY_INFORMATION
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            _LocalFree(sd)

    def icacls(ruta):
        """Las entradas que da icacls («nombre:(permisos)»), sin depender del idioma de sus mensajes."""
        r = subprocess.run(["icacls", ruta], capture_output=True, text=True, errors="replace", check=True)
        lineas = r.stdout.replace(ruta, "", 1).splitlines()
        return [ln.strip() for ln in lineas if re.search(r":\([A-Z]", ln.strip())]


class Comun:
    """Lo mismo en todos los sistemas; `self.carpeta` la pone cada subclase."""

    def ruta(self, *partes):
        return os.path.join(self.carpeta, *partes)

    def assertPrivado(self, ruta):
        self.assertTrue(permisos.es_privado(ruta), ruta)
        if WINDOWS:
            protegido, entradas = permisos.acl(ruta)
            self.assertTrue(protegido, f"{ruta}: hereda de la carpeta")
            self.assertEqual(entradas, [(0, 0, CONTROL_TOTAL, permisos.sid_propio())], ruta)
            usuario = os.environ.get("USERNAME", "")
            vistas = icacls(ruta)
            self.assertEqual(len(vistas), 1, vistas)
            self.assertNotIn("(I)", vistas[0])
            self.assertIn(usuario.lower(), vistas[0].lower())
            self.assertTrue(vistas[0].endswith(":(F)"), vistas)
        else:
            self.assertEqual(stat.S_IMODE(os.stat(ruta).st_mode), 0o600, ruta)

    def test_la_carpeta_deja_leer_a_otros(self):
        """Control: un fichero escrito como antes no es privado aquí (si no, las demás pruebas no dicen nada)."""
        escribe_normal(self.ruta("normal"), "x")
        self.assertFalse(permisos.es_privado(self.ruta("normal")))
        if WINDOWS:
            _, entradas = permisos.acl(self.ruta("normal"))
            self.assertIn("S-1-5-11", [sid for *_, sid in entradas])        # Usuarios autentificados

    def test_nuevo_solo_para_el_usuario(self):
        permisos.escribe_privado(self.ruta("secreto"), "hola\n")
        self.assertPrivado(self.ruta("secreto"))
        with open(self.ruta("secreto"), "rb") as f:
            self.assertEqual(f.read(), b"hola\n")
        self.assertEqual(sorted(os.listdir(self.carpeta)), ["secreto"])

    def test_el_de_antes_se_corrige_al_reescribirse(self):
        escribe_normal(self.ruta("secreto"), "viejo\n")
        escribe_normal(self.ruta("secreto.tmp"), "de un corte\n")
        self.assertFalse(permisos.es_privado(self.ruta("secreto")))
        permisos.escribe_privado(self.ruta("secreto"), "nuevo\n")
        self.assertPrivado(self.ruta("secreto"))
        with open(self.ruta("secreto"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "nuevo\n")
        self.assertEqual(sorted(os.listdir(self.carpeta)), ["secreto"])

    def test_unir_deja_token_y_relay_url_privados(self):
        repo = self.ruta("repo")
        git("init", "-q", repo)
        os_dir = os.path.join(repo, ".git", "hackathon", "os")
        escribe_normal(os.path.join(os_dir, "token"), "viejo\n")             # uno de antes, heredado
        self.assertEqual(unir(repo, "secreto-equipo"), 1)
        for nombre in ("token", "relay.url"):
            self.assertPrivado(os.path.join(os_dir, nombre))
        with open(os.path.join(os_dir, "token"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "secreto-equipo\n")

    def test_web_token_privado_al_crearse_y_el_de_antes_se_corrige(self):
        repo = self.ruta("repo")
        git("init", "-q", repo)
        ruta = os.path.join(repo, ".git", "hackathon", "os", "web.token")
        a = demonio(repo)
        self.assertPrivado(ruta)
        os.remove(ruta)
        escribe_normal(ruta, a.web_token + "\n")                            # el de un demonio anterior a esto
        self.assertFalse(permisos.es_privado(ruta))
        otro = demonio(repo)
        self.assertEqual(otro.web_token, a.web_token)                       # se reutiliza, pero ya privado
        self.assertPrivado(ruta)
        self.assertEqual(sorted(n for n in os.listdir(os.path.dirname(ruta)) if n.startswith("web.token")),
                         ["web.token"])

    @unittest.skipIf(WINDOWS, "en Windows el navegador recibe la URL y no hay web.html")
    def test_web_html_privado(self):
        escribe_normal(self.ruta("web.html"), "viejo")
        from unittest import mock
        with mock.patch.object(cli.webbrowser, "open", return_value=True):
            cli.abrir_navegador("http://127.0.0.1:7801/#t=tok", self.carpeta)
        self.assertPrivado(self.ruta("web.html"))


class Temporal(Comun, unittest.TestCase):
    """Una carpeta temporal; en Windows, con el ACL que tendría en C:\\ (la del perfil ya es solo del usuario)."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.carpeta, True)
        if WINDOWS:
            como_la_raiz(self.carpeta)
        else:
            previa = os.umask(0o022)
            self.addCleanup(os.umask, previa)

    def test_recoger_deja_fuera_los_temporales_de_los_secretos(self):
        repo = self.ruta("repo")
        git("init", "-q", repo)
        os_dir = os.path.join(repo, ".git", "hackathon", "os")
        nombres = [*SECRETOS, *(n + ".tmp" for n in SECRETOS), "web.token.4242.tmp", "token.7.tmp"]
        for n in nombres:
            escribe_normal(os.path.join(os_dir, n), "secreto\n")
        with socket.socket() as s:                              # desfase() lee relay.url: un puerto cerrado
            s.bind(("127.0.0.1", 0))
            escribe_normal(os.path.join(os_dir, "relay.url"), f"http://127.0.0.1:{s.getsockname()[1]}\n")
        escribe_normal(os.path.join(os_dir, "estado.json"), "{}")
        destino = self.ruta("r.zip")
        self.assertEqual(cli.recoger(repo, destino, lambda *_: None), 0)
        with zipfile.ZipFile(destino) as z:
            self.assertEqual([n for n in z.namelist() if n.startswith("os/")], ["os/estado.json"])


@unittest.skipUnless(WINDOWS, "solo Windows: una carpeta de verdad en la raíz de la unidad del sistema")
class FueraDelPerfil(Comun, unittest.TestCase):
    """Como en el issue: C:\\hk-permisos-…\\, con el ACL que da Windows, sin tocarlo."""

    def setUp(self):
        raiz = os.environ.get("SystemDrive", "C:") + "\\"
        self.carpeta = os.path.join(raiz, f"hk-permisos-{os.getpid()}-{os.urandom(4).hex()}")
        try:
            os.mkdir(self.carpeta)          # no mkdtemp: con 0o700, Python ≥ 3.12.4 le pone un ACL solo del usuario
        except OSError as ex:
            self.skipTest(f"no se puede crear una carpeta en {raiz}: {ex}")
        self.addCleanup(shutil.rmtree, self.carpeta, True)
        escribe_normal(os.path.join(self.carpeta, "sonda"), "x")
        privado = permisos.es_privado(os.path.join(self.carpeta, "sonda"))
        os.remove(os.path.join(self.carpeta, "sonda"))
        if privado:
            self.skipTest(f"en {raiz} los ficheros ya nacen solo para el usuario")


if __name__ == "__main__":
    unittest.main()
