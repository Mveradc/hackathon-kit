"""PR #11 (hkos/cli.py): lo que se comprobó con un script temporal, como pruebas fijas. `hk-os recoger` guarda las
carpetas vacías de entregado/ y, a quien coordina, criterios.md en contexto/, y deja fuera los secretos, web.html y
el remoto; `abrir_navegador`, fuera de Windows, solo pasa al navegador la ruta de web.html (0600, con la URL).

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import html
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import cli  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
