"""PR #11 (hkos/cli.py): lo que se comprobó con un script temporal, como pruebas fijas. `hk-os recoger` guarda las
carpetas vacías de entregado/ y, a quien coordina, criterios.md en contexto/, y deja fuera los secretos, web.html y
el remoto; `abrir_navegador`, fuera de Windows, solo pasa al navegador la ruta de web.html (0600, con la URL).
Issue #15: `hk-os web` no manda web.token si agente.vivo es viejo o, en Linux, si el puerto es de otro usuario; dice
dónde está web.html aunque haya navegador; `hk-os unir` deja token y relay.url en 0600.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import contextlib
import hashlib
import hmac
import html
import http.server
import io
import os
import pathlib
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from unittest import mock

VIVO_S = 60   # el de delta.sh y cli.VIVO_S
FUTURO_S = 5  # el de delta.sh y cli.FUTURO_S
HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import cli  # noqa: E402
import permisos  # noqa: E402

CRITERIOS = "# Criterios\n\n## 2026-11-25 18:00 · Ana (jurado)\n- Qué dijo: que se vea el reparto\n"
ENTREGAS = ("accion-web-ana-anotar-1", "accion-web-ana-reclamo-T42-2")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout.strip()


class Recoger(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.repo = os.path.join(self.dir, "repo")
        git(self.dir, "init", "-q", "-b", "main", "repo")
        for k, v in (("user.name", "x"), ("user.email", "x@example.com"), ("core.autocrlf", "false")):
            git(self.repo, "config", k, v)
        self.escribe(os.path.join(self.repo, ".hackathon", "criterios.md"), CRITERIOS)
        self.escribe(os.path.join(self.repo, ".hackathon", "coordinacion.md"), "# Coordinación\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "inicio")
        git(self.repo, "update-ref", "refs/remotes/origin/main", "HEAD")      # sin red: origin/main es HEAD
        self.os = os.path.join(self.repo, ".git", "hackathon", "os")
        for ruta, texto in (("estado.json", "{}"), ("token", "secreto-relay"), ("web.token", "secreto-web"),
                            ("web.html", "<a href='#t=secreto-web'>"), ("web.html.tmp", "x"),
                            ("relay/eventos.jsonl", "{}\n"), ("relay/token", "secreto-relay"),
                            ("remoto/equipo.git/HEAD", "ref: refs/heads/main\n")):
            self.escribe(os.path.join(self.os, ruta), texto)
        for e in ENTREGAS:
            os.makedirs(os.path.join(self.os, "entregado", e))

    @staticmethod
    def escribe(ruta, texto):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def recoger(self):
        destino, salida = os.path.join(self.dir, "r.zip"), []
        self.assertEqual(cli.recoger(self.repo, destino, salida.append), 0)
        self.salida = salida
        return zipfile.ZipFile(destino)

    def test_carpetas_vacias_de_entregado(self):
        with self.recoger() as z:
            for e in ENTREGAS:
                self.assertTrue(z.getinfo(f"os/entregado/{e}/").is_dir(), e)
            self.assertNotIn("os/entregado/", z.namelist())                  # no está vacía: tiene las entregas
        self.assertIn("y 2 carpetas vacías", self.salida[-1])

    def test_criterios_en_contexto_a_quien_coordina(self):
        with self.recoger() as z:
            self.assertEqual(z.read("contexto/.hackathon/criterios.md").decode("utf-8"), CRITERIOS)
            self.assertIn("contexto/.hackathon/coordinacion.md", z.namelist())
        shutil.rmtree(os.path.join(self.os, "relay"))                          # sin relay/: no es quien coordina
        with self.recoger() as z:
            self.assertFalse([n for n in z.namelist() if n.startswith("contexto/")])

    def test_fuera_secretos_web_html_y_remoto(self):
        with self.recoger() as z:
            nombres = z.namelist()
            self.assertFalse([n for n in nombres if n.rsplit("/", 1)[-1] in ("token", "web.token", "web.html",
                                                                              "web.html.tmp")])
            self.assertFalse([n for n in nombres if n.startswith("os/remoto")])
            self.assertFalse([n for n in nombres if b"secreto" in z.read(n)])
            self.assertIn("os/estado.json", nombres)
            self.assertIn("os/relay/eventos.jsonl", nombres)

    def test_relay_url_que_no_es_una_url(self):
        """PR #22: con un relay.url que no es una URL, urllib lanza ValueError (no OSError) y recoger se caía."""
        for url in ("no-es-una-url", "ftp//x", ""):
            self.escribe(os.path.join(self.os, "relay.url"), url + "\n")
            with self.recoger() as z:
                self.assertEqual(z.read("desfase.txt"), b"sin relay\n", url)


class Navegador(unittest.TestCase):
    URL = "http://127.0.0.1:7801/#t=tok-123_abc"

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.carpeta, True)
        self.ruta = os.path.join(self.carpeta, "web.html")

    def abrir(self, url=URL, hay_navegador=True):
        with mock.patch.object(cli.webbrowser, "open", return_value=hay_navegador) as abre:
            return cli.abrir_navegador(url, self.carpeta), [c.args for c in abre.call_args_list]

    def leer(self):
        with open(self.ruta, encoding="utf-8") as f:
            return f.read()


@unittest.skipIf(os.name == "nt", "en Windows el navegador recibe la URL y no hay web.html")
class AbrirNavegadorFueraDeWindows(Navegador):
    def test_al_navegador_solo_le_llega_la_ruta_de_web_html(self):
        abierta, llamadas = self.abrir()
        self.assertTrue(abierta)
        self.assertEqual(llamadas, [(pathlib.Path(self.ruta).as_uri(),)])
        self.assertTrue(llamadas[0][0].startswith("file:///") and llamadas[0][0].endswith("/web.html"))
        self.assertNotIn("tok-123_abc", llamadas[0][0])

    def test_pagina_0600_con_la_url(self):
        self.abrir()
        self.assertEqual(stat.S_IMODE(os.stat(self.ruta).st_mode), 0o600)
        self.assertIn(f'content="0;url={html.escape(self.URL, quote=True)}"', self.leer())
        self.assertIn(f'href="{html.escape(self.URL, quote=True)}"', self.leer())

    def test_segunda_llamada_sobrescribe_sin_dejar_tmp(self):
        self.abrir()
        os.chmod(self.ruta, 0o644)
        with open(self.ruta + ".tmp", "w") as f:                               # uno que quedó de un corte
            f.write("viejo")
        otra = "http://127.0.0.1:7802/#t=otro-token"
        self.abrir(otra)
        self.assertIn(otra, self.leer())
        self.assertNotIn("tok-123_abc", self.leer())
        self.assertEqual(stat.S_IMODE(os.stat(self.ruta).st_mode), 0o600)
        self.assertEqual(os.listdir(self.carpeta), ["web.html"])

    def test_sin_navegador_da_false(self):
        abierta, llamadas = self.abrir(hay_navegador=False)
        self.assertIs(abierta, False)
        self.assertEqual(len(llamadas), 1)
        self.assertTrue(os.path.exists(self.ruta))                              # para abrirla a mano


@unittest.skipUnless(os.name == "nt", "solo en Windows")
class AbrirNavegadorEnWindows(Navegador):
    def test_webbrowser_con_la_url_y_sin_web_html(self):
        self.assertEqual(self.abrir(), (True, [(self.URL,)]))
        self.assertEqual(self.abrir(hay_navegador=False), (False, [(self.URL,)]))
        self.assertEqual(os.listdir(self.carpeta), [])


def tabla_tcp(filas, v6=False):
    """Un /proc/net/tcp (o tcp6) falso: filas (ip, puerto, estado, uid), con las direcciones como las escribe Linux
    (cada palabra de 32 bits en el orden de bytes de la máquina, en hexadecimal)."""
    lineas = ["  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode"]
    for i, (ip, puerto, estado, uid) in enumerate(filas):
        crudo = socket.inet_pton(socket.AF_INET6 if v6 else socket.AF_INET, ip)
        hexa = "".join("%08X" % struct.unpack("=I", crudo[j:j + 4])[0] for j in range(0, len(crudo), 4))
        cero = "0" * len(hexa)
        lineas.append(f"{i:4}: {hexa}:{puerto:04X} {cero}:0000 {estado} 00000000:00000000 00:00000000 00000000 "
                      f"{uid:5}        0 {1000 + i} 1 0000000000000000 100 0 0 10 0")
    return "\n".join(lineas) + "\n"


class HkOsWebImpostor(unittest.TestCase):
    """Issue #15 (hallazgo 4): `hk-os web` mandaba web.token a cualquiera que contestara /salud en el puerto de
    agente.vivo. Ahora, antes de nada, la hora de agente.vivo (como delta.sh) y, en Linux, el dueño del puerto."""
    UID = 1000

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.repo = os.path.join(self.dir, "repo")
        git(self.dir, "init", "-q", "-b", "main", "repo")
        Recoger.escribe(os.path.join(self.repo, ".hackathon", "os.md"), "activa: sí\nweb_nueva: sí\n")
        self.comun = cli.agente.git_comun(self.repo)
        self.os = os.path.join(self.comun, "hackathon", "os")
        Recoger.escribe(os.path.join(self.os, "web.token"), "secreto-web\n")
        self.recibidos, self.retos = recibidos, retos = [], []
        self.primera = f"hk-os {self.comun}\n".encode("utf-8")
        self.clave = "secreto-web"          # con la que firma el reto: la de web.token es el demonio de verdad
        prueba = self

        class Impostor(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                recibidos.append((self.path, self.headers.get("X-HK-Token")))
                cuerpo = prueba.primera if self.path == "/salud" else b"{}"
                self.send_response(200)
                reto = self.headers.get("X-HK-Reto")
                if self.path == "/salud" and reto is not None:
                    retos.append(reto)
                    if prueba.clave is not None:
                        self.send_header("X-HK-Prueba", hmac.new(prueba.clave.encode(), reto.encode(),
                                                                 hashlib.sha256).hexdigest())
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *a):
                pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Impostor)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.puerto = self.srv.server_address[1]
        self.tcp = os.path.join(self.dir, "tcp")
        self.tcp6 = os.path.join(self.dir, "tcp6")

    def vivo(self, hace_s=0):
        Recoger.escribe(os.path.join(self.os, "agente.vivo"), f"{self.puerto}\n{int(time.time() - hace_s)}\n")

    def web(self, linux=False, tablas=None):
        abiertas, salida = [], []
        with mock.patch.object(cli, "LINUX", linux, create=True), \
                mock.patch.object(cli, "TCP_PROC", tablas or (self.tcp, self.tcp6), create=True), \
                mock.patch.object(cli.os, "getuid", create=True, return_value=self.UID):
            rc = cli.web(self.repo, abiertas.append, salida.append)
        return rc, abiertas, salida

    def sin_token(self, rc, abiertas, salida, motivo="no está en marcha"):
        self.assertEqual(rc, 1)
        self.assertEqual(abiertas, [])
        self.assertFalse([r for r in self.recibidos if r[1]], "el token llegó al impostor")
        self.assertIn(motivo, salida[-1])
        self.assertTrue(salida[-1].startswith("hk-os web: "), salida[-1])
        self.assertFalse(any("secreto-web" in s for s in salida))

    def test_agente_vivo_viejo_no_manda_el_token(self):
        self.vivo(hace_s=VIVO_S + 30)                       # reinicio o kill -9: el fichero se quedó en disco
        rc, abiertas, salida = self.web()
        self.sin_token(rc, abiertas, salida, "no ha latido en ")                     # issue #23, hallazgo 17
        self.assertRegex(salida[-1], rf"no ha latido en ({VIVO_S + 30}|{VIVO_S + 31}) s")
        self.assertIn("si acabas de despertar el portátil, espera 15 s", salida[-1])
        self.assertEqual(self.recibidos, [])                    # ni siquiera /salud

    def test_agente_vivo_en_el_futuro_no_manda_el_token(self):
        """Issue #23 (hallazgo 1): con la hora en el futuro, time.time() - hora salía negativo y pasaba el filtro."""
        for hace_s in (-3600, -(FUTURO_S + 10)):
            self.vivo(hace_s=hace_s)
            rc, abiertas, salida = self.web()
            self.sin_token(rc, abiertas, salida, " s en el futuro")
            self.assertRegex(salida[-1], rf"\b({-hace_s}|{-hace_s - 1}) s en el futuro")
            self.assertEqual(self.recibidos, [], hace_s)            # ni siquiera /salud

    def test_agente_vivo_un_poco_en_el_futuro_abre(self):
        """El margen: el reloj de quien escribe y el de quien lee pueden ir un segundo descompasados."""
        self.vivo(hace_s=-(FUTURO_S - 3))
        rc, abiertas, _ = self.web()
        self.assertEqual((rc, abiertas), (0, [f"http://127.0.0.1:{self.puerto}/#t=secreto-web"]))

    def test_agente_vivo_sin_hora_no_manda_el_token(self):
        Recoger.escribe(os.path.join(self.os, "agente.vivo"), f"{self.puerto}\n")
        self.sin_token(*self.web())

    def test_sin_agente_vivo_no_esta_en_marcha(self):
        self.sin_token(*self.web())
        self.assertEqual(self.recibidos, [])

    def test_otro_programa_en_el_puerto_no_manda_el_token(self):
        self.vivo()
        self.primera = b"hk-os /otro/clon/.git\n"
        self.sin_token(*self.web(), f"en el puerto {self.puerto} contesta otro programa")
        self.assertEqual(self.recibidos, [("/salud", None)])

    def test_linux_puerto_de_otro_uid_no_manda_el_token(self):
        self.vivo()
        Recoger.escribe(self.tcp, tabla_tcp([("127.0.0.1", self.puerto, "0A", self.UID + 1)]))
        self.sin_token(*self.web(linux=True), f"el puerto {self.puerto} es de otro usuario (uid {self.UID + 1})")
        self.assertEqual(self.recibidos, [])

    def test_linux_puerto_de_otro_uid_en_tcp6_no_manda_el_token(self):
        self.vivo()
        Recoger.escribe(self.tcp, tabla_tcp([("127.0.0.1", self.puerto, "0A", self.UID)]))
        Recoger.escribe(self.tcp6, tabla_tcp([("::", self.puerto, "0A", self.UID + 1)], v6=True))
        self.sin_token(*self.web(linux=True), "es de otro usuario")

    def test_linux_uid_65534_dice_que_puede_ser_otro_espacio_de_nombres(self):
        self.vivo()
        Recoger.escribe(self.tcp, tabla_tcp([("127.0.0.1", self.puerto, "0A", 65534)]))
        self.sin_token(*self.web(linux=True), "otro espacio de nombres de usuario")

    def test_linux_sin_nadie_en_escucha_no_manda_el_token(self):
        self.vivo()
        Recoger.escribe(self.tcp, tabla_tcp([("127.0.0.1", self.puerto, "01", self.UID + 1),     # conexión, no escucha
                                             ("127.0.0.1", self.puerto + 1, "0A", self.UID),
                                             ("10.0.0.5", self.puerto, "0A", self.UID)]))
        self.sin_token(*self.web(linux=True), f"no encuentro el puerto {self.puerto} en escucha")

    def test_linux_puerto_propio_abre(self):
        self.vivo()
        Recoger.escribe(self.tcp, tabla_tcp([("127.0.0.1", self.puerto, "0A", self.UID),
                                             ("127.0.0.1", self.puerto, "01", self.UID + 1)]))
        Recoger.escribe(self.tcp6, tabla_tcp([("::1", self.puerto, "0A", self.UID + 1)], v6=True))   # ::1 no es 127.0.0.1
        rc, abiertas, _ = self.web(linux=True)
        self.assertEqual((rc, abiertas), (0, [f"http://127.0.0.1:{self.puerto}/#t=secreto-web"]))

    def test_linux_sin_proc_solo_la_hora(self):
        self.vivo()
        rc, abiertas, _ = self.web(linux=True, tablas=(os.path.join(self.dir, "no-hay"),))
        self.assertEqual((rc, len(abiertas)), (0, 1))

    def test_hora_reciente_abre(self):
        self.vivo(hace_s=VIVO_S - 15)
        rc, abiertas, salida = self.web()
        self.assertEqual((rc, abiertas), (0, [f"http://127.0.0.1:{self.puerto}/#t=secreto-web"]))
        self.assertIn(("/v1/vista", "secreto-web"), self.recibidos)
        self.assertFalse(any("secreto-web" in s for s in salida))

    def test_impostor_con_la_hora_reciente_no_recibe_nada(self):
        """Decisión 7B (PR #13): en Windows y macOS (o en Linux sin /proc, o con el puerto propio), un impostor en el
        puerto en los 60 s tras morir el demonio pasaba la hora y contestaba /salud con la primera línea buena: recibía
        el token. Ahora tiene que firmar el reto con web.token, que no tiene. Sin X-HK-Prueba (o un demonio antiguo)
        o con una mala, nada: ni el token ni el navegador."""
        Recoger.escribe(self.tcp, tabla_tcp([("127.0.0.1", self.puerto, "0A", self.UID)]))
        for clave, linux in ((None, False), ("otra-clave", False), ("", False), (None, True), ("otra-clave", True)):
            self.clave = clave
            self.recibidos.clear()
            self.vivo(hace_s=VIVO_S - 15)
            self.sin_token(*self.web(linux=linux), "el demonio no ha demostrado que es el tuyo; reinícialo con la "
                                                   "versión nueva")
            self.assertEqual(self.recibidos, [("/salud", None)], (clave, linux))    # solo /salud, sin token
        self.assertEqual(len(self.retos), 5)
        self.assertEqual(len(set(self.retos)), 5)                                     # uno nuevo cada vez
        for reto in self.retos:
            self.assertRegex(reto, r"^[0-9a-f]{64}$")                                 # 32 bytes en hex

    @unittest.skipUnless(sys.platform.startswith("linux"), "el /proc/net/tcp de verdad")
    def test_linux_con_el_proc_de_verdad(self):
        self.vivo()
        with mock.patch.object(cli, "LINUX", True):
            self.assertTrue(cli.escucha_mia(self.puerto))
            self.assertIs(cli.web(self.repo, lambda u: None, lambda *_: None), 0)

    @unittest.skipIf(os.name == "nt", "en Windows no hay web.html")
    def test_con_navegador_dice_tambien_donde_esta_web_html(self):
        """Hallazgo 11: con un navegador snap, webbrowser.open da True aunque no pueda leer web.html."""
        self.vivo()
        salida = []
        with mock.patch.object(cli, "LINUX", False, create=True), \
                mock.patch.object(cli.webbrowser, "open", return_value=True):
            self.assertEqual(cli.web(self.repo, salida=salida.append), 0)
        uri = pathlib.Path(self.os, "web.html").as_uri()
        self.assertTrue(any(s.startswith("Web de trabajo:") for s in salida))
        self.assertTrue(any("Abre a mano " + uri in s for s in salida), salida)
        self.assertFalse(any("secreto-web" in s for s in salida))


@unittest.skipIf(os.name == "nt", "en Windows los ficheros heredan el ACL de la carpeta (pendiente)")
class UnirPermisos(unittest.TestCase):
    """Issue #15 (hallazgo 12): token y relay.url salían 0644 con umask 022."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.repo = os.path.join(self.dir, "repo")
        git(self.dir, "init", "-q", "-b", "main", "repo")
        self.os = os.path.join(self.repo, ".git", "hackathon", "os")
        previa = os.umask(0o022)
        self.addCleanup(os.umask, previa)

    def unir(self, token):
        with socket.socket() as s:                              # un puerto cerrado: el relay no responde
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.unir(f"http://127.0.0.1:{puerto}", token, cwd=self.repo, salida=lambda *_: None), 1)

    def test_token_y_relay_url_0600(self):
        self.unir("secreto-equipo")
        for nombre, texto in (("token", "secreto-equipo"), ("relay.url", "http://127.0.0.1:")):
            ruta = os.path.join(self.os, nombre)
            self.assertEqual(stat.S_IMODE(os.stat(ruta).st_mode), 0o600, nombre)
            with open(ruta, encoding="utf-8") as f:
                self.assertTrue(f.read().startswith(texto))

    def test_los_de_antes_pasan_a_0600_sin_dejar_tmp(self):
        os.makedirs(self.os)
        for nombre in ("token", "relay.url", "token.tmp"):
            with open(os.path.join(self.os, nombre), "w") as f:
                f.write("viejo\n")
            os.chmod(os.path.join(self.os, nombre), 0o644)
        self.unir("otro")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.os, "token")).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.os, "relay.url")).st_mode), 0o600)
        self.assertEqual(sorted(os.listdir(self.os)), ["relay.url", "token"])
        with open(os.path.join(self.os, "token"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "otro\n")


class UnirTodoONada(unittest.TestCase):
    """Issue #27: unir escribía relay.url y luego token. Si el segundo os.replace fallaba (en Windows, WinError 5 con el
    token abierto por el demonio, el MCP o OneDrive, más allá de los reintentos), quedaban la URL nueva con el token
    viejo, un traceback y token.tmp. Ahora los dos o ninguno, sin .tmp, y un mensaje. Aquí el fallo se simula en todos
    los sistemas; test_permisos.py lo hace en Windows con un open() de verdad."""

    def setUp(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        git(d, "init", "-q", "-b", "main", "repo")
        self.repo = os.path.join(d, "repo")
        self.os = os.path.join(self.repo, ".git", "hackathon", "os")

    def unir_sin_token(self):
        replace = os.replace

        def falla(src, dst):
            if os.path.basename(dst) == "token":
                raise PermissionError(13, "Acceso denegado (simulado: WinError 5)", dst)
            return replace(src, dst)
        err = io.StringIO()
        with socket.socket() as s:                              # un puerto cerrado: el relay no responde
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        with mock.patch("os.replace", falla), mock.patch.object(permisos, "REEMPLAZO_S", 0.2, create=True), \
                contextlib.redirect_stderr(err):
            rc = cli.unir(f"http://127.0.0.1:{puerto}", "nuevo", cwd=self.repo, salida=lambda *_: None)
        self.assertEqual(rc, 1)
        self.assertIn("no he podido guardar relay.url y token", err.getvalue())
        salida = {}
        for n in sorted(os.listdir(self.os)):
            with open(os.path.join(self.os, n), encoding="utf-8") as f:
                salida[n] = f.read()
        return salida

    def test_con_los_de_antes_quedan_los_dos_como_estaban(self):
        os.makedirs(self.os)
        for nombre, texto in (("relay.url", "http://10.0.0.1:7777\n"), ("token", "viejo\n")):
            with open(os.path.join(self.os, nombre), "w", encoding="utf-8") as f:
                f.write(texto)
        self.assertEqual(self.unir_sin_token(), {"relay.url": "http://10.0.0.1:7777\n", "token": "viejo\n"})

    def test_sin_los_de_antes_no_queda_ninguno(self):
        self.assertEqual(self.unir_sin_token(), {})


class UnirArgumentos(unittest.TestCase):
    """PR #24: token_urlsafe da un token que empieza por «-» una vez de cada 64, y argparse lo tomaba por una opción
    («the following arguments are required: token»). La forma documentada, hk-os unir <url> <token>, no cambia."""
    URL = "http://127.0.0.1:7777"

    def unir(self, *argv):
        with mock.patch.object(cli, "unir", return_value=0) as u:
            self.assertEqual(cli.main(["unir", *argv]), 0)
        u.assert_called_once()
        return u.call_args.args, u.call_args.kwargs

    def test_token_con_guion_delante(self):
        sin_mas = {"persona": None, "remoto": None}
        for argv, args, kwargs in (
                ((self.URL, "-Abc123_x"), (self.URL, "-Abc123_x"), sin_mas),
                ((self.URL, "--", "-Abc123_x"), (self.URL, "-Abc123_x"), sin_mas),
                (("--", self.URL, "-Abc123_x"), (self.URL, "-Abc123_x"), sin_mas),
                ((self.URL, "--Abc123_x"), (self.URL, "--Abc123_x"), sin_mas),
                ((self.URL, "-Abc123_x", "--persona", "@ana"), (self.URL, "-Abc123_x"), {"persona": "@ana", "remoto": None}),
                (("--persona", "ana", self.URL, "--", "-Abc123_x"), (self.URL, "-Abc123_x"), {"persona": "ana", "remoto": None}),
                ((self.URL, "--remoto=http://127.0.0.1:7778/equipo.git", "-Abc123_x"), (self.URL, "-Abc123_x"),
                 {"persona": None, "remoto": "http://127.0.0.1:7778/equipo.git"}),
                ((self.URL, "-Abc123_x", "--remoto", "http://127.0.0.1:7778/equipo.git", "--persona", "ana"),
                 (self.URL, "-Abc123_x"), {"persona": "ana", "remoto": "http://127.0.0.1:7778/equipo.git"})):
            self.assertEqual(self.unir(*argv), (args, kwargs), argv)

    def test_lo_que_ya_valia_sigue_igual(self):
        self.assertEqual(self.unir(self.URL, "Abc123_x"), ((self.URL, "Abc123_x"), {"persona": None, "remoto": None}))
        for argv in ((self.URL,), (self.URL, "a", "b"), (self.URL, "a", "--persona")):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), \
                    mock.patch.object(cli, "unir") as u, self.assertRaises(SystemExit) as ex:
                cli.main(["unir", *argv])
            self.assertEqual(ex.exception.code, 2)
            u.assert_not_called()

    def test_el_token_con_guion_llega_al_fichero(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        git(d, "init", "-q", "-b", "main", "repo")
        repo = os.path.join(d, "repo")
        with socket.socket() as s:                              # un puerto cerrado: el relay no responde
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        unir = cli.unir
        with mock.patch.object(cli, "unir", side_effect=lambda *a, **k: unir(*a, cwd=repo, salida=lambda *_: None, **k)), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["unir", f"http://127.0.0.1:{puerto}", "-Abc123_x"]), 1)
        with open(os.path.join(repo, ".git", "hackathon", "os", "token"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "-Abc123_x\n")


class RelaySinReemplazos(unittest.TestCase):
    """PR #21: relay.py lee con --no-replace-objects, pero compilar.py y colisiones_merge.py también leen git en el
    proceso del relay. hk-os relay arranca con GIT_NO_REPLACE_OBJECTS=1, que heredan todos sus git."""

    def test_relay_arranca_con_git_no_replace_objects(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        git(d, "init", "-q", "-b", "main", "repo")
        repo = os.path.join(d, "repo")
        for k, v in (("user.name", "x"), ("user.email", "x@example.com")):
            git(repo, "config", k, v)
        git(repo, "commit", "-q", "--allow-empty", "-m", "real")
        real = git(repo, "rev-parse", "HEAD")
        git(repo, "commit", "-q", "--allow-empty", "-m", "falso")
        git(repo, "replace", real, git(repo, "rev-parse", "HEAD"))
        self.assertEqual(git(repo, "log", "-1", "--format=%s", real), "falso")    # control: el reemplazo se ve
        import colisiones_merge  # noqa: PLC0415
        leido = {}

        def relay_main(argv):
            leido["entorno"] = os.environ.get("GIT_NO_REPLACE_OBJECTS")
            leido["compilar"] = cli.compilar._git(repo, "log", "-1", "--format=%s", real)
            leido["merge"] = colisiones_merge.ejecutar(repo, "log", "-1", "--format=%s", real)[1].strip()
        with mock.patch.dict(os.environ), mock.patch.object(cli.relay, "main", side_effect=relay_main), \
                mock.patch.object(cli.agente, "git_comun", return_value=os.path.join(repo, ".git").replace("\\", "/")):
            os.environ.pop("GIT_NO_REPLACE_OBJECTS", None)
            self.assertEqual(cli.main(["relay", "--puerto", "7777"]), 0)
        self.assertEqual(leido, {"entorno": "1", "compilar": "real", "merge": "real"})


if __name__ == "__main__":
    unittest.main()
