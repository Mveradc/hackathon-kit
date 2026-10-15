"""M8g, nivel 2: publicación del trabajo en curso (Publicador) y conflictos con merge-tree (Calculo), sobre repos de
verdad con un remoto `bare` local. Sin red ni GitHub.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import colisiones_merge as cm  # noqa: E402

APP = "".join(f"linea {i}\n" for i in range(20))


def git(repo, *args, entrada=None):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, input=entrada)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr.decode()}")
    return r.stdout.decode().strip()


def escribe(repo, ruta, texto, modo="w"):
    p = os.path.join(repo, ruta)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, modo, newline="\n" if "b" not in modo else None) as f:
        f.write(texto)


def huella_indice(repo):
    with open(os.path.join(repo, ".git", "index"), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def foto(repo):
    """Lo que la persona ve: índice (bytes), status, stash y HEAD."""
    return (huella_indice(repo), git(repo, "status", "--porcelain=v2", "--untracked-files=all"),
            git(repo, "stash", "list"), git(repo, "rev-parse", "HEAD"))


class Reloj:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hk-wip-")
        self.remoto = os.path.join(self.tmp, "remoto.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remoto], check=True)
        semilla = os.path.join(self.tmp, "semilla")
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", self.remoto, semilla], check=True, capture_output=True)
        self._identidad(semilla)
        escribe(semilla, "app.py", APP)
        escribe(semilla, ".gitignore", "ignorado.txt\ndata/\n.claude/worktrees/\n")   # excluidas y ya ignoradas
        escribe(semilla, ".env.example", "CLAVE=\n")
        git(semilla, "add", "-A")
        git(semilla, "commit", "-qm", "inicio")
        git(semilla, "push", "-q", "origin", "HEAD:main")
        self.clones = {}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _identidad(repo):
        git(repo, "config", "user.email", "x@example.com")
        git(repo, "config", "user.name", "X")
        git(repo, "config", "core.autocrlf", "false")

    def clon(self, persona):
        repo = os.path.join(self.tmp, persona)
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", self.remoto, repo], check=True, capture_output=True)
        self._identidad(repo)
        d = os.path.join(repo, ".git", "hackathon", "os")
        os.makedirs(d, exist_ok=True)
        self.clones[persona] = repo
        return repo

    def publicador(self, persona, conf=None, visibilidad=lambda r: "PRIVATE"):
        repo = self.clones[persona]
        valores = {"publicar_wip": "sí", "datos_excluidos": "data/, datos/"}
        valores.update(conf or {})
        self.log = []
        reloj = Reloj()
        p = cm.Publicador(repo, os.path.join(repo, ".git", "hackathon", "os"), persona, valores.get,
                          log=self.log.append, reloj=reloj, visibilidad=visibilidad)
        p.reloj_prueba = reloj
        return p

    @staticmethod
    def otra_vuelta(p):
        p.reloj_prueba.t += p.CADA_S + 1
        return p.ciclo()

    def en_remoto(self, ref):
        r = subprocess.run(["git", "-C", self.remoto, "rev-parse", "--verify", "-q", ref], capture_output=True)
        return r.stdout.decode().strip() if r.returncode == 0 else None

    def hay_blob(self, repo, texto):
        sha = subprocess.run(["git", "hash-object", "--stdin"], input=texto.encode(), capture_output=True).stdout.decode().strip()
        return subprocess.run(["git", "-C", repo, "cat-file", "-e", sha], capture_output=True).returncode == 0


class Publicacion(Base):
    def test_publica_sin_tocar_nada_de_la_persona_y_sin_secretos(self):
        a = self.clon("ana")
        # Un commit local sin subir con un fichero de datos: no debe viajar por la historia.
        escribe(a, "datos/privado.csv", "dni,saldo\n1,secreto-del-commit\n")
        git(a, "add", "datos/privado.csv")
        git(a, "commit", "-qm", "datos locales")
        escribe(a, "app.py", APP.replace("linea 3\n", "linea 3 de ana\n"))
        escribe(a, "nuevo.py", "print('nuevo')\n")
        escribe(a, "staged.py", "x = 1\n")
        git(a, "add", "staged.py")                                   # algo en el índice de la persona
        secretos = {".env": "TOKEN=secreto-env\n", "sub/.ENV.local": "TOKEN=secreto-env-mayus\n",
                    "clave.pem": "-----BEGIN secreto-pem\n", "id_rsa": "secreto-ssh\n",
                    "credentials-gcp.json": '{"secreto": "gcp"}\n', "secrets.yaml": "secreto: yaml\n",
                    "data/muestra.csv": "secreto-data\n", "datos/otro.csv": "secreto-datos\n",
                    "ignorado.txt": "secreto-ignorado\n"}
        for ruta, texto in secretos.items():
            escribe(a, ruta, texto)
        escribe(a, "grande.bin", "secreto-grande" + "x" * (1024 * 1024 + 10))
        os.makedirs(os.path.join(a, ".git", "hooks"), exist_ok=True)
        escribe(a, ".git/hooks/pre-push", "#!/bin/sh\nexit 1\n")       # --no-verify: no se ejecuta
        antes = foto(a)
        p = self.publicador("ana")
        self.assertEqual(p.ciclo(), "publicada")
        self.assertEqual(foto(a), antes, "el índice, el status, el stash o HEAD de la persona han cambiado")
        sha = self.en_remoto("refs/hackathon/wip/ana")
        self.assertTrue(sha)
        ficheros = set(git(self.remoto, "ls-tree", "-r", "--name-only", sha).split("\n"))
        self.assertTrue({"app.py", "nuevo.py", "staged.py", ".gitignore", ".env.example"} <= ficheros)
        self.assertFalse(ficheros & (set(secretos) | {"grande.bin", "datos/privado.csv"}), ficheros)
        base = git(self.remoto, "rev-parse", "main")
        self.assertEqual(git(self.remoto, "rev-parse", f"{sha}^"), base)     # el padre es la base, no HEAD
        for texto in [*secretos.values(), "dni,saldo\n1,secreto-del-commit\n"]:
            self.assertFalse(self.hay_blob(self.remoto, texto), f"en el remoto: {texto!r}")
        # Lo excluido no llega a ser objeto en el repo de la persona (salvo lo que ella misma commiteó).
        for ruta in (".env", "sub/.ENV.local", "clave.pem", "id_rsa", "credentials-gcp.json", "secrets.yaml",
                     "data/muestra.csv", "datos/otro.csv", "ignorado.txt"):
            self.assertFalse(self.hay_blob(a, secretos[ruta]), f"objeto local de {ruta}")
        # Lo publicado se ve: wip.json, /salud (salud) y el log.
        self.assertIn("nuevo.py", p.publicado["ficheros"])
        self.assertNotIn(".env", p.publicado["ficheros"])
        self.assertIn("ficheros", p.salud)
        self.assertTrue(any("nuevo.py" in l for l in self.log))

    def test_igual_no_vuelve_a_subir_y_limpio_borra_la_ref(self):
        a = self.clon("ana")
        p = self.publicador("ana")
        self.assertEqual(p.ciclo(), "limpio")                      # nada en curso: no publica
        self.assertIsNone(self.en_remoto("refs/hackathon/wip/ana"))
        escribe(a, "app.py", APP + "fin\n")
        self.assertEqual(self.otra_vuelta(p), "publicada")
        self.assertEqual(p.ciclo(), "espera")                      # como mucho una vez por minuto
        self.assertEqual(self.otra_vuelta(p), "igual")
        escribe(a, "app.py", APP)                                  # vuelve a la base
        self.assertEqual(self.otra_vuelta(p), "borrada")
        self.assertIsNone(self.en_remoto("refs/hackathon/wip/ana"))
        self.assertEqual(p.publicado, {})

    def test_apagar_borra_lo_publicado(self):
        a = self.clon("ana")
        escribe(a, "app.py", APP + "fin\n")
        p = self.publicador("ana")
        self.assertEqual(p.ciclo(), "publicada")
        p.conf = {"publicar_wip": "no"}.get
        self.assertEqual(self.otra_vuelta(p), "borrada")
        self.assertIsNone(self.en_remoto("refs/hackathon/wip/ana"))

    def test_a_medias_no_publica(self):
        a = self.clon("ana")
        escribe(a, "app.py", APP + "fin\n")
        escribe(a, ".git/MERGE_HEAD", git(a, "rev-parse", "HEAD") + "\n")
        p = self.publicador("ana")
        self.assertEqual(p.ciclo(), "a medias")
        self.assertEqual(self.log, [])                             # sin ruido
        os.remove(os.path.join(a, ".git", "MERGE_HEAD"))
        # Un conflicto de verdad: entradas sin fusionar en el índice.
        git(a, "checkout", "-q", "-b", "otra")
        escribe(a, "app.py", APP.replace("linea 1\n", "otra\n"))
        git(a, "commit", "-qam", "otra")
        git(a, "checkout", "-q", "main")
        escribe(a, "app.py", APP.replace("linea 1\n", "main\n"))
        git(a, "commit", "-qam", "main")
        subprocess.run(["git", "-C", a, "merge", "-q", "otra"], capture_output=True)
        self.assertTrue(git(a, "ls-files", "-u"))
        os.remove(os.path.join(a, ".git", "MERGE_HEAD"))           # aunque falte MERGE_HEAD, el índice lo dice
        self.assertEqual(self.otra_vuelta(p), "a medias")
        self.assertIsNone(self.en_remoto("refs/hackathon/wip/ana"))

    def test_repo_publico_o_desconocido_no_publica(self):
        a = self.clon("ana")
        git(a, "remote", "set-url", "origin", "https://github.com/alguien/reto.git")
        escribe(a, "app.py", APP + "fin\n")
        p = self.publicador("ana", visibilidad=lambda r: "PUBLIC")
        self.assertEqual(p.ciclo(), "no permitido")
        self.assertIn("público", p.salud)
        self.assertTrue(p.aviso and p.aviso.startswith("> "))
        p = self.publicador("ana", visibilidad=lambda r: None)
        self.assertEqual(p.ciclo(), "no permitido")
        self.assertIn("no sé si", p.salud)
        vistos = []
        p = self.publicador("ana", conf={"publicar_wip": "sí, incluso público"},
                            visibilidad=lambda r: vistos.append(r) or "PUBLIC")
        self.assertTrue(p._permitido(True))
        p._permitido(True)
        self.assertEqual(vistos, ["alguien/reto"])                 # una sola consulta
        p = self.publicador("ana", visibilidad=lambda r: "PRIVATE")
        self.assertTrue(p._permitido(False))
        self.assertEqual(cm.modo_publicar("sí, incluso público"), (True, True))
        self.assertEqual(cm.modo_publicar("sí   # ADR-0007"), (True, False))
        self.assertEqual(cm.modo_publicar("no"), (False, False))

    def test_salida_1_de_add_solo_por_exclusiones_ya_ignoradas(self):
        """Ajuste del usuario: `git add` con 1 vale solo si lo único que dice es que nuestras exclusiones nombran rutas
        ya ignoradas. Cualquier otro error, otra ruta u otro código: no se publica."""
        ok = f"{cm.IGNORADAS}\ndatos\n.claude/worktrees\n"
        self.assertTrue(cm.add_aceptable(0, "", []))
        self.assertTrue(cm.add_aceptable(1, ok, ["datos/", ".claude/worktrees/"]))
        self.assertTrue(cm.add_aceptable(1, "warning: in the working copy of 'a.py', LF will be replaced by CRLF the "
                                            "next time Git touches it\n" + ok, ["datos/", ".claude/worktrees/"]))
        self.assertFalse(cm.add_aceptable(1, ok, [".claude/worktrees/"]))           # «datos» no es una exclusión nuestra
        self.assertFalse(cm.add_aceptable(1, ok + "error: open(\"x.py\"): Permission denied\n", ["datos/", ".claude/worktrees/"]))
        self.assertFalse(cm.add_aceptable(1, "error: open(\"x.py\"): Permission denied\n", []))
        self.assertFalse(cm.add_aceptable(1, "", []))
        self.assertFalse(cm.add_aceptable(128, ok, ["datos/", ".claude/worktrees/"]))

    def test_add_que_falla_por_otro_motivo_no_publica(self):
        a = self.clon("ana")
        escribe(a, "app.py", APP + "fin\n")
        p = self.publicador("ana")
        # El índice temporal bloqueado: `git add` falla con «Unable to create … .lock» (y no es lo de las exclusiones).
        escribe(a, ".git/hackathon/os/wip.index.lock", "")
        self.assertEqual(p.ciclo(), "error")
        self.assertIsNone(self.en_remoto("refs/hackathon/wip/ana"))
        self.assertTrue(any("git add" in l for l in self.log), self.log)
        os.remove(os.path.join(a, ".git", "hackathon", "os", "wip.index.lock"))
        self.assertEqual(self.otra_vuelta(p), "publicada")

    def test_fallo_de_autenticacion_espera_10_min(self):
        a = self.clon("ana")
        p = self.publicador("ana")
        p._fallo("fatal: Authentication failed for 'https://github.com/x/y.git/'")
        self.assertEqual(p.espera_hasta - p.reloj(), p.ESPERA_AUTH_S)
        self.assertIn("autenticación", p.salud)
        self.assertEqual(self.otra_vuelta(p), "espera")
        p2 = self.publicador("ana")
        git(a, "remote", "set-url", "origin", os.path.join(self.tmp, "no-existe.git"))
        escribe(a, "app.py", APP + "fin\n")
        git(a, "update-ref", "refs/remotes/origin/main", git(a, "rev-parse", "HEAD"))
        self.assertEqual(p2.ciclo(), "error")
        self.assertGreater(p2.espera_hasta, p2.reloj())


class MergeTree(Base):
    def test_conflicto_en_las_mismas_lineas_y_nada_si_son_compatibles(self):
        a, b, r = self.clon("ana"), self.clon("bea"), self.clon("relay")
        escribe(a, "app.py", APP.replace("linea 5\n", "linea 5 de ana\n"))
        escribe(b, "app.py", APP.replace("linea 5\n", "linea 5 de bea\n"))
        escribe(b, "web.js", "x\n")
        for p in ("ana", "bea"):
            self.assertEqual(self.publicador(p).ciclo(), "publicada")
        horas = iter(["2026-11-20T10:00:00Z", "2026-11-20T10:01:00Z"])
        c = cm.Calculo(r, {"ana", "bea"}, aviso=self.fail, ahora=lambda: next(horas))
        self.assertTrue(c.sondear())
        self.assertEqual(c.conflictos, [{"personas": ["ana", "bea"], "rutas": ["app.py"], "desde": "2026-11-20T10:00:00Z"}])
        self.assertFalse(c.sondear())                              # sin cambios: misma lista y misma hora
        # Compatibles: B cambia otra línea.
        escribe(b, "app.py", APP.replace("linea 15\n", "linea 15 de bea\n"))
        pb = self.publicador("bea")
        self.assertEqual(pb.ciclo(), "publicada")
        self.assertTrue(c.sondear())
        self.assertEqual(c.conflictos, [])
        # Fuera del equipo: no cuenta.
        c2 = cm.Calculo(r, {"ana"}, aviso=self.fail)
        c2.sondear()
        self.assertEqual(c2.conflictos, [])

    def test_git_viejo_desactiva_el_nivel_2(self):
        avisos = []
        c = cm.Calculo(self.tmp, {"ana"}, aviso=avisos.append, version=(2, 37))
        self.assertFalse(c.activo)
        self.assertFalse(c.sondear())
        self.assertIn("2.37 < 2.38", avisos[0])
        self.assertGreaterEqual(cm.version_git(), cm.VERSION_MIN)  # el git de esta máquina


if __name__ == "__main__":
    unittest.main()
