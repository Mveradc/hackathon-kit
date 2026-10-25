"""M11, K-111: nivel 2b de colisiones (ADR-0014) en `colisiones_merge.Calculo`, con repos de verdad y un remoto `bare`
local. Los casos del criterio 2 de M11, con un `mergiraf` falso (mergiraf_falso.py) y, si hay uno en el PATH, con el
de verdad (con el falso de pasarela delante, que anota las llamadas). Sin el real, esos casos se saltan y lo dicen.
Sin red ni GitHub.

Uso: python -m unittest hkos.pruebas.test_colisiones_2b -v
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colisiones_merge as cm  # noqa: E402
import mergiraf_falso  # noqa: E402

MERGIRAF_REAL = shutil.which("mergiraf")            # el del PATH al cargar las pruebas, antes del falso

APP = "import os\nimport sys\n\n\ndef f():\n    return 1\n"
JSON = '{\n  "a": 1\n}\n'
BASE = {
    "app.py": APP,
    "datos.json": JSON,
    "conf.py": "X = 1\nY = 2\n",
    "notas.txt": "uno\ndos\n",
    "raro.zzz": "uno\ndos\n",
    "latin.py": b"# caf\xe9\nimport os\nimport sys\n\n\ndef f():\n    return 1\n",
    "roto.py": "import os\nimport sys\n\n\ndef f(:\n    return 1\n",
    "borra.py": "A = 1\nB = 2\n",
    "util.py": "".join(f"def u{i}():\n    return {i}\n\n\n" for i in range(10)),
    "enlace": ("120000", "destino-base"),
    "lento.py": APP,
    "-x.py": APP,                                   # una ruta que empieza por «-» (#88)
    "importa.txt": APP,                             # Python en un .txt: rojo salvo que un atributo diga otra cosa
    **{f"m{i}.py": APP for i in range(6)},
}
EN_EL_MISMO_SITIO = {"ana": "import json\n", "bea": "import re\n"}
CLAVES = {"ana": '{\n  "a": 1,\n  "b": 2\n}\n', "bea": '{\n  "a": 1,\n  "c": 3\n}\n'}
VALORES = {"ana": "X = 10\nY = 2\n", "bea": "X = 20\nY = 2\n"}


def git(repo, *args, entrada=None, env=None):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, input=entrada,
                       env=dict(os.environ, **(env or {})))
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr.decode()}")
    return r.stdout.decode().strip()


def con_import(persona, texto=APP):
    return texto.replace("import sys\n", "import sys\n" + EN_EL_MISMO_SITIO[persona])


def latin(persona):
    return BASE["latin.py"].replace(b"import sys\n", b"import sys\n" + EN_EL_MISMO_SITIO[persona].encode())


class Horas:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f"2026-11-20T10:{self.n:02d}:00Z"


class Escenario:
    """Remoto `bare` con la base, el clon del relay y commits de trabajo en curso hechos con plumbing (sin la copia de
    nadie: así valen enlaces simbólicos y renombrados en Windows). Con el entorno aislado: PATH con el `mergiraf` falso
    delante, XDG_DATA_HOME y APPDATA de «la persona» y el directorio temporal, vacíos y comprobados al final."""
    REAL = None                                     # ruta del mergiraf real para la pasarela; None: el falso

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="hk-2b-prueba-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.remoto = os.path.join(self.tmp, "remoto.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remoto], check=True)
        self.taller = os.path.join(self.tmp, "taller")
        subprocess.run(["git", "init", "-q", "-b", "main", self.taller], check=True)
        for k, v in (("user.email", "x@example.com"), ("user.name", "X"), ("core.autocrlf", "false")):
            git(self.taller, "config", k, v)
        self.base = self.commit(BASE, padre=None)
        git(self.taller, "push", "-q", self.remoto, f"{self.base}:refs/heads/main")
        self.relay = os.path.join(self.tmp, "relay")
        subprocess.run(["git", "clone", "-q", "-c", "core.autocrlf=false", self.remoto, self.relay], check=True,
                       capture_output=True)
        # Lo que se comprueba que queda vacío: el temporal de Calculo y las carpetas de datos de «la persona».
        self.temporal = os.path.join(self.tmp, "temporal")
        self.usuario_xdg = os.path.join(self.tmp, "usuario-xdg")
        self.usuario_appdata = os.path.join(self.tmp, "usuario-appdata")
        for d in (self.temporal, self.usuario_xdg, self.usuario_appdata):
            os.makedirs(d)
        self.config = os.path.join(self.tmp, "falso.json")
        self.log = os.path.join(self.tmp, "llamadas.jsonl")
        self.configurar(rc={"app.py": 0, "datos.json": 0}, por_defecto=1)
        entorno = mergiraf_falso.instalar(os.path.join(self.tmp, "bin"), self.config)
        entorno.update(XDG_DATA_HOME=self.usuario_xdg, APPDATA=self.usuario_appdata)
        p = mock.patch.dict(os.environ, entorno)
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(tempfile, "tempdir", self.temporal)
        p.start()
        self.addCleanup(p.stop)
        self.avisos = []

    def configurar(self, **conf):
        datos = {"log": self.log, "version": "mergiraf 0.20.0", "rc": {}, "por_defecto": 0, "espera": {}}
        if os.path.exists(self.config):
            with open(self.config, encoding="utf-8") as f:
                datos.update(json.load(f))
        datos.update(conf)
        if self.REAL:
            datos["real"] = self.REAL
        with open(self.config, "w", encoding="utf-8") as f:
            json.dump(datos, f)

    def llamadas(self):
        """Las llamadas `merge` al mergiraf (falso o pasarela), sin las de --version."""
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    def commit(self, ficheros, padre="base"):
        """Un commit con `ficheros` ({ruta: texto | bytes | (modo, texto) | None para borrar}) sobre la base."""
        indice = os.path.join(self.tmp, "indice")
        env = {"GIT_INDEX_FILE": indice}
        if os.path.exists(indice):
            os.remove(indice)
        if padre:
            git(self.taller, "read-tree", self.base, env=env)
        info = []
        for ruta, valor in ficheros.items():
            if valor is None:
                info.append(f"0 {'0' * 40}\t{ruta}")
                continue
            modo, valor = valor if isinstance(valor, tuple) else ("100644", valor)
            datos = valor if isinstance(valor, bytes) else valor.encode("utf-8")
            sha = git(self.taller, "hash-object", "-w", "--stdin", entrada=datos)
            info.append(f"{modo} {sha}\t{ruta}")
        subprocess.run(["git", "-C", self.taller, "update-index", "--add", "--index-info"], check=True,
                       input=("\n".join(info) + "\n").encode("utf-8"), env=dict(os.environ, **env))
        arbol = git(self.taller, "write-tree", env=env)
        return git(self.taller, "commit-tree", arbol, *(["-p", self.base] if padre else []), "-m", "wip")

    def wip(self, persona, ficheros):
        sha = self.commit(ficheros)
        git(self.taller, "push", "-q", "--force", self.remoto, f"{sha}:refs/hackathon/wip/{persona}")
        return sha

    def calculo(self, equipo=("ana", "bea"), **kw):
        kw.setdefault("fusion_estructural", True)
        c = cm.Calculo(self.relay, set(equipo), aviso=self.avisos.append, ahora=Horas(), **kw)
        return c

    def foto_relay(self):
        return (git(self.relay, "status", "--porcelain=v2", "--untracked-files=all", "--ignored"),
                git(self.relay, "for-each-ref", "--format=%(refname) %(objectname)"))

    def assertLimpio(self):
        """Tras cada llamada: nada en el temporal ni en XDG_DATA_HOME ni APPDATA de la persona (P12, P17)."""
        for d in (self.temporal, self.usuario_xdg, self.usuario_appdata):
            self.assertEqual(os.listdir(d), [], d)

    def un_par(self, c):
        self.assertEqual(len(c.conflictos), 1, c.conflictos)
        return c.conflictos[0]


class CasosComunes(Escenario):
    """Los casos del criterio 2 que valen igual con el falso y con el real."""

    def test_imports_y_claves_json_bajan_a_2b_sin_2(self):
        self.wip("ana", {"app.py": con_import("ana"), "datos.json": CLAVES["ana"]})
        self.wip("bea", {"app.py": con_import("bea"), "datos.json": CLAVES["bea"]})
        c = self.calculo()
        self.assertTrue(c.fusion_estructural)
        self.assertTrue(c.sondear())
        self.assertEqual(self.un_par(c), {"personas": ["ana", "bea"], "rutas": [], "rutas_2b": ["app.py", "datos.json"],
                                          "desde": None, "desde_2b": "2026-11-20T10:01:00Z"})
        self.assertEqual(sorted(l["ruta"] for l in self.llamadas()), ["app.py", "datos.json"])
        self.assertLimpio()

    def test_la_misma_linea_con_valores_distintos_sigue_roja(self):
        self.wip("ana", {"conf.py": VALORES["ana"]})
        self.wip("bea", {"conf.py": VALORES["bea"]})
        c = self.calculo()
        c.sondear()
        self.assertEqual(self.un_par(c), {"personas": ["ana", "bea"], "rutas": ["conf.py"], "rutas_2b": [],
                                          "desde": "2026-11-20T10:01:00Z", "desde_2b": None})
        self.assertEqual([l["ruta"] for l in self.llamadas()], ["conf.py"])
        self.assertLimpio()

    def test_un_par_con_un_fichero_de_cada(self):
        self.wip("ana", {"app.py": con_import("ana"), "conf.py": VALORES["ana"]})
        self.wip("bea", {"app.py": con_import("bea"), "conf.py": VALORES["bea"]})
        c = self.calculo()
        c.sondear()
        par = self.un_par(c)
        self.assertEqual((par["rutas"], par["rutas_2b"]), (["conf.py"], ["app.py"]))
        self.assertTrue(par["desde"] and par["desde_2b"])
        self.assertLimpio()

    def test_add_add_modify_delete_renombrado_y_enlace_siguen_rojos_sin_mergiraf(self):
        self.wip("ana", {"nuevo.py": "A = 1\n", "borra.py": "A = 10\nB = 2\n", "util.py": None,
                         "util_a.py": BASE["util.py"], "enlace": ("120000", "destino-ana")})
        self.wip("bea", {"nuevo.py": "A = 2\n", "borra.py": None, "util.py": None,
                         "util_b.py": BASE["util.py"], "enlace": ("120000", "destino-bea")})
        c = self.calculo()
        c.sondear()
        par = self.un_par(c)
        self.assertEqual(par["rutas_2b"], [])
        for ruta in ("nuevo.py", "borra.py", "enlace", "util.py", "util_a.py", "util_b.py"):
            self.assertIn(ruta, par["rutas"])
        self.assertEqual(self.llamadas(), [])
        self.assertLimpio()

    def test_lo_que_no_analiza_sigue_rojo(self):
        """Un .txt, una extensión desconocida, un fichero no UTF-8 y uno con error de sintaxis."""
        lados = {}
        for p in ("ana", "bea"):
            lados[p] = {"notas.txt": f"uno\ndos\ntres de {p}\n", "raro.zzz": f"uno\ndos\ntres de {p}\n",
                        "latin.py": latin(p), "roto.py": con_import(p, BASE["roto.py"])}
            self.wip(p, lados[p])
        c = self.calculo()
        c.sondear()
        par = self.un_par(c)
        self.assertEqual((par["rutas"], par["rutas_2b"]), (["latin.py", "notas.txt", "raro.zzz", "roto.py"], []))
        self.assertEqual(sorted(l["ruta"] for l in self.llamadas()), ["latin.py", "notas.txt", "raro.zzz", "roto.py"])
        self.assertLimpio()

    def test_mismos_blobs_una_sola_llamada_tambien_para_el_no(self):
        self.wip("ana", {"app.py": con_import("ana"), "conf.py": VALORES["ana"]})
        self.wip("bea", {"app.py": con_import("bea"), "conf.py": VALORES["bea"]})
        self.wip("cris", {"app.py": con_import("bea"), "conf.py": VALORES["bea"]})   # los mismos blobs que bea
        c = self.calculo(equipo=("ana", "bea", "cris"))
        c.sondear()
        self.assertEqual([(x["personas"], x["rutas"], x["rutas_2b"]) for x in c.conflictos],
                         [(["ana", "bea"], ["conf.py"], ["app.py"]), (["ana", "cris"], ["conf.py"], ["app.py"])])
        self.assertEqual(len(self.llamadas()), 2)
        self.wip("bea", {"app.py": con_import("bea"), "conf.py": VALORES["bea"], "otro.py": "Z = 1\n"})  # shas nuevos
        self.assertFalse(c.sondear())
        self.assertEqual(len(self.llamadas()), 2)
        self.assertLimpio()

    def test_2b_vuelve_a_rojo_y_desde_2b_quieto_si_no_cambia_el_conjunto(self):
        self.wip("ana", {"app.py": con_import("ana")})
        self.wip("bea", {"app.py": con_import("bea")})
        c = self.calculo()
        c.sondear()
        desde_2b = self.un_par(c)["desde_2b"]
        self.assertEqual(self.un_par(c)["rutas_2b"], ["app.py"])
        self.wip("bea", {"app.py": con_import("bea"), "otro.py": "Z = 1\n"})        # otro sha, mismo conjunto
        self.assertFalse(c.sondear())
        self.assertEqual(self.un_par(c)["desde_2b"], desde_2b)
        # Las dos cambian además la misma línea: Mergiraf ya no lo resuelve.
        self.marcar_rojo("app.py")
        self.wip("ana", {"app.py": con_import("ana").replace("return 1", "return 2")})
        self.wip("bea", {"app.py": con_import("bea").replace("return 1", "return 3")})
        self.assertTrue(c.sondear())
        par = self.un_par(c)
        self.assertEqual((par["rutas"], par["rutas_2b"], par["desde_2b"]), (["app.py"], [], None))
        self.assertNotEqual(par["desde"], desde_2b)
        self.assertLimpio()

    def test_nada_nuevo_en_el_clon_del_relay(self):
        self.wip("ana", {"app.py": con_import("ana"), "conf.py": VALORES["ana"]})
        self.wip("bea", {"app.py": con_import("bea"), "conf.py": VALORES["bea"]})
        self.calculo(fusion_estructural=False).sondear()      # el fetch de la 0.5.0
        antes = self.foto_relay()
        c = self.calculo()
        c.sondear()
        self.assertEqual(len(self.llamadas()), 2)
        self.assertEqual(self.foto_relay(), antes)
        self.assertLimpio()
        for l in self.llamadas():
            self.assertEqual(l["XDG_DATA_HOME"], l["APPDATA"])
            self.assertFalse(os.path.abspath(l["XDG_DATA_HOME"]).startswith(os.path.abspath(self.relay)))
            self.assertEqual(os.path.dirname(os.path.abspath(l["XDG_DATA_HOME"])), self.temporal)

    def test_ruta_que_empieza_por_guion_baja_a_2b(self):
        """#88: con `-p -x.py`, Mergiraf 0.20.0 lee la ruta como opción (rc 2) y el fichero se queda rojo sin motivo."""
        self.configurar(rc={"app.py": 0, "datos.json": 0, "-x.py": 0})
        self.wip("ana", {"-x.py": con_import("ana")})
        self.wip("bea", {"-x.py": con_import("bea")})
        c = self.calculo()
        c.sondear()
        self.assertEqual((self.un_par(c)["rutas"], self.un_par(c)["rutas_2b"]), ([], ["-x.py"]))
        (l,) = self.llamadas()
        self.assertIn("--path-name=-x.py", l["args"])
        self.assertLimpio()

    def test_cerrar_mata_el_mergiraf_en_marcha_y_borra_el_temporal(self):
        """#88: lo que hace el relay al parar con un Mergiraf en marcha (en todos los sistemas; las señales, abajo)."""
        if self.REAL:
            self.skipTest("hace falta un Mergiraf lento: con el falso")
        self.configurar(espera={"app.py": 30})
        self.wip("ana", {"app.py": con_import("ana")})
        self.wip("bea", {"app.py": con_import("bea")})
        c = self.calculo()
        c.PLAZO_PROCESO_S = 60
        hilo = threading.Thread(target=c.sondear, daemon=True)
        hilo.start()
        espera(lambda: self.llamadas() and os.listdir(self.temporal), 30)
        t = time.monotonic()
        c.cerrar()
        hilo.join(10)
        self.assertFalse(hilo.is_alive())
        self.assertLess(time.monotonic() - t, 10)
        self.assertEqual(os.listdir(self.temporal), [])
        self.assertEqual(c._cache_2b, {}, "lo que cortó la parada no se guarda")
        self.assertIsNone(c._mergiraf("app.py", ["0" * 40] * 3, 1), "ya no se lanza ninguno más")
        if os.name != "nt":
            espera(lambda: not vivo(self.llamadas()[0]["pid"]), 5)
        self.assertLimpio()

    def marcar_rojo(self, ruta):
        """Con el falso, la ruta pasa a dar rc 1; con el real, lo decide el contenido."""


class ConFalso(CasosComunes, unittest.TestCase):

    def marcar_rojo(self, ruta):
        rc = {"app.py": 0, "datos.json": 0}
        rc[ruta] = 1
        self.configurar(rc=rc)

    def test_argumentos_de_la_llamada(self):
        self.wip("ana", {"app.py": con_import("ana")})
        self.wip("bea", {"app.py": con_import("bea")})
        self.calculo().sondear()
        (l,) = self.llamadas()
        args = l["args"]
        self.assertEqual(args[0], "merge")
        self.assertEqual(l["entradas"], [True, True, True])
        self.assertEqual([os.path.basename(a) for a in args[1:4]], ["1", "2", "3"])
        # #88: la ruta con `=` (una que empiece por «-» no se lee como opción), los errores de sintaxis apagados aunque
        # un atributo de git los encienda y el temporal de cwd (fuera de cualquier repo: ni la copia del coordinador).
        self.assertEqual(args[4:], ["--path-name=app.py", "--allow-parse-errors=false", "-t", "5000", "-o",
                                    os.path.join(os.path.dirname(args[1]), "salida")])
        self.assertNotIn("-p", args)
        self.assertNotIn("--fast", args)
        self.assertEqual(os.path.realpath(l["cwd"]), os.path.realpath(os.path.dirname(args[1])))
        self.assertEqual(l["XDG_DATA_HOME"], os.path.dirname(args[1]))
        self.assertEqual(l["APPDATA"], os.path.dirname(args[1]))
        self.assertLimpio()                         # el falso dejó copias en los dos con rc 0: borradas

    def test_255_plazo_del_proceso_y_no_se_puede_lanzar_dan_rojo_y_el_ciclo_sigue(self):
        self.configurar(rc={"app.py": 255, "lento.py": 0, "datos.json": 0}, espera={"lento.py": 3})
        lados = {p: {"app.py": con_import(p), "lento.py": con_import(p), "datos.json": CLAVES[p]} for p in ("ana", "bea")}
        for p in lados:
            self.wip(p, lados[p])
        c = self.calculo()
        c.PLAZO_PROCESO_S = 0.5
        t = time.monotonic()
        c.sondear()
        self.assertLess(time.monotonic() - t, 3)
        par = self.un_par(c)
        self.assertEqual((par["rutas"], par["rutas_2b"]), (["app.py", "lento.py"], ["datos.json"]))
        self.assertEqual(len(self.llamadas()), 3)
        self.wip("bea", {**lados["bea"], "otro.py": "Z = 1\n"})
        c.sondear()
        self.assertEqual(len(self.llamadas()), 3, "el plazo vencido y el 255 también van a la caché")
        # No se puede lanzar: rojo, sin excepción y sin caché (se reintenta).
        c2 = self.calculo()
        c2.mergiraf = os.path.join(self.tmp, "no-existe")
        c2.sondear()
        self.assertEqual(self.un_par(c2)["rutas_2b"], [])
        self.assertEqual(self.un_par(c2)["rutas"], ["app.py", "datos.json", "lento.py"])
        self.assertEqual(c2._cache_2b, {})
        time.sleep(3)                               # en Windows el falso sigue durmiendo tras matar su lanzador
        self.assertLimpio()

    def test_sin_temporal_rojo_sin_cache_y_el_ciclo_sigue(self):
        """#88: si no se puede crear el temporal, ese fichero sigue rojo y sin caché, y `conflictos` no se congela."""
        self.wip("ana", {"app.py": con_import("ana"), "conf.py": VALORES["ana"]})
        self.wip("bea", {"app.py": con_import("bea"), "conf.py": VALORES["bea"]})
        c = self.calculo()
        c.sondear()
        self.assertEqual((self.un_par(c)["rutas"], self.un_par(c)["rutas_2b"]), (["conf.py"], ["app.py"]))
        # Bea deshace app.py y cambia conf.py; el temporal ya no existe (TMPDIR inválido, carpeta borrada…).
        self.wip("bea", {"conf.py": "X = 30\nY = 2\n"})
        with mock.patch.object(tempfile, "tempdir", os.path.join(self.tmp, "no-existe")):
            self.assertTrue(c.sondear())
            self.assertEqual((self.un_par(c)["rutas"], self.un_par(c)["rutas_2b"]), (["conf.py"], []))
            # Y uno nuevo que bajaría a 2b: rojo mientras dure.
            self.wip("bea", {"app.py": con_import("bea", APP.replace("return 1", "return 1  # bea")),
                             "conf.py": "X = 30\nY = 2\n"})
            self.assertTrue(c.sondear())
            self.assertEqual((self.un_par(c)["rutas"], self.un_par(c)["rutas_2b"]), (["app.py", "conf.py"], []))
        self.assertEqual(len(c._cache_2b), 2, "solo las del primer ciclo; lo que no tuvo temporal no se guarda")
        self.assertTrue(c.sondear())                         # vuelve el temporal: app.py baja a 2b
        self.assertEqual((self.un_par(c)["rutas"], self.un_par(c)["rutas_2b"]), (["conf.py"], ["app.py"]))
        self.assertLimpio()

    def test_cache_2b_lru_no_pierde_la_que_se_consulta_cada_ciclo(self):
        """#88: el recorte de la caché de 2b se queda con las usadas, no con las últimas insertadas. Si se perdiera,
        un fichero al filo de `-t` podría cambiar de color sin que cambie nada (aquí, la 2.ª llamada da rc 1)."""
        self.wip("ana", {"app.py": con_import("ana")})
        self.wip("bea", {"app.py": con_import("bea")})
        c = self.calculo()
        c.sondear()
        self.assertEqual(self.un_par(c)["rutas_2b"], ["app.py"])
        self.marcar_rojo("app.py")
        for ciclo in range(8):                               # 100 entradas nuevas de otros ficheros por ciclo
            for i in range(100):
                c._cache_2b[("a" * 40, "b" * 40, f"{ciclo:02d}{i:038d}", f"otro{i}.py")] = True
            self.assertFalse(c.sondear())
            self.assertEqual(self.un_par(c)["rutas_2b"], ["app.py"], ciclo)
        self.assertEqual(len(self.llamadas()), 1)
        self.assertLessEqual(len(c._cache_2b), 600)
        self.assertLimpio()

    def test_no_busca_mergiraf_en_el_directorio_actual(self):
        """#88: un `mergiraf` en el cwd del relay (la copia del coordinador: uno versionado en la raíz) no se ejecuta,
        ni con «.», una entrada vacía o una relativa en el PATH. En Windows, shutil.which mira el cwd de todos modos."""
        copia = os.path.join(self.tmp, "copia")
        marca = os.path.join(self.tmp, "ejecutado")
        plantado(copia, marca)
        bueno = os.path.join(self.tmp, "bin", "mergiraf.exe" if os.name == "nt" else "mergiraf")
        anterior = os.getcwd()
        os.chdir(copia)
        self.addCleanup(os.chdir, anterior)
        git_dir = os.path.dirname(shutil.which("git"))      # para el `git --version` del nivel 2
        for path in (os.pathsep.join(["", ".", "copia", os.path.join(self.tmp, "bin"), git_dir]),
                     os.pathsep.join([os.path.join(self.tmp, "bin"), ".", git_dir])):
            with mock.patch.dict(os.environ, {"PATH": path}):
                self.avisos.clear()
                c = self.calculo()
            self.assertEqual(os.path.normcase(c.mergiraf), os.path.normcase(bueno))
            self.assertEqual(self.avisos, ["Nivel 2b activo: mergiraf 0.20.0"])
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join(["", ".", "copia", git_dir])}):
            self.avisos.clear()
            c = self.calculo()
        self.assertFalse(c.fusion_estructural)
        self.assertEqual(self.avisos, ["Nivel 2b desactivado: mergiraf no está en el PATH. Sigue el nivel 2."])
        self.assertFalse(os.path.exists(marca), "se ejecutó el mergiraf del directorio actual")

    @unittest.skipUnless(os.name == "nt", "solo en Windows (lo corre el CI de Windows)")
    def test_windows_solo_un_mergiraf_exe(self):
        """#88: en Windows, un mergiraf.bat o .cmd del PATH no vale (pasaría la ruta por cmd.exe): solo el .exe."""
        marca = os.path.join(self.tmp, "ejecutado")
        scripts = os.path.join(self.tmp, "scripts")
        os.makedirs(scripts)
        for ext in (".bat", ".cmd"):
            with open(os.path.join(scripts, "mergiraf" + ext), "w", encoding="utf-8") as f:
                f.write(f'@echo mergiraf 0.20.0\r\n@echo x> "{marca}"\r\n')
        bueno = os.path.join(self.tmp, "bin", "mergiraf.exe")
        git_dir = os.path.dirname(shutil.which("git"))
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([scripts, os.path.join(self.tmp, "bin"), git_dir])}):
            c = self.calculo()
        self.assertEqual(os.path.normcase(c.mergiraf), os.path.normcase(bueno))
        self.avisos.clear()
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([scripts, git_dir]), "PATHEXT": ".COM;.EXE;.BAT;.CMD"}):
            c = self.calculo()
        self.assertFalse(c.fusion_estructural)
        self.assertEqual(self.avisos, ["Nivel 2b desactivado: mergiraf no está en el PATH. Sigue el nivel 2."])
        self.assertFalse(os.path.exists(marca))

    @unittest.skipIf(os.name == "nt", "SIGTERM no se puede atrapar en Windows; cerrar() se prueba arriba")
    def test_el_relay_parado_con_mergiraf_en_marcha_no_deja_temporal_ni_hijo(self):
        """#88: Ctrl+C (SIGINT) y SIGTERM al relay de verdad con un Mergiraf lento en marcha: sale enseguida, sin
        `hk-2b-*` en el temporal y sin el hijo vivo. Con SIGTERM, sale por la señal, como antes."""
        self.configurar(espera={"app.py": 60})
        self.wip("ana", {"app.py": con_import("ana")})
        self.wip("bea", {"app.py": con_import("bea")})
        os.makedirs(os.path.join(self.relay, ".hackathon"))
        equipo_md = os.path.join(self.relay, ".hackathon", "coordinacion.md")
        os_md = os.path.join(self.relay, ".hackathon", "os.md")
        with open(equipo_md, "w", encoding="utf-8") as f:
            f.write("| Persona | GitHub |\n|---|---|\n| Ana | @ana |\n| Bea | @bea |\n")
        with open(os_md, "w", encoding="utf-8") as f:
            f.write("# Hackathon OS\nactiva: sí\npublicar_wip: sí\nfusion_estructural: sí\n")
        for n, senal in enumerate((signal.SIGINT, signal.SIGTERM)):
            if os.path.exists(self.log):
                os.remove(self.log)
            salida = os.path.join(self.tmp, f"relay-{n}.log")
            with open(salida, "wb") as f:
                p = subprocess.Popen([sys.executable, os.path.join(HKOS, "relay.py"), "--dir",
                                      os.path.join(self.tmp, f"dir-relay-{n}"), "--equipo", equipo_md, "--os", os_md,
                                      "--ip", "127.0.0.1", "--puerto", "0", "--sin-github"], stdout=f,
                                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                     env=dict(os.environ, TMPDIR=self.temporal))
            self.addCleanup(p.kill)
            espera(lambda: self.llamadas() and os.listdir(self.temporal), 60)
            (llamada,) = self.llamadas()
            self.assertTrue(vivo(llamada["pid"]))
            t = time.monotonic()
            p.send_signal(senal)
            rc = p.wait(15)
            self.assertLess(time.monotonic() - t, 10)
            self.assertEqual(rc, -signal.SIGTERM if senal == signal.SIGTERM else 0, leer(salida))
            self.assertEqual(os.listdir(self.temporal), [], leer(salida))
            espera(lambda: not vivo(llamada["pid"]), 5)
        self.assertLimpio()

    def test_mas_ficheros_de_los_que_caben_en_el_ciclo(self):
        n = 6
        nombres = [f"m{i}.py" for i in range(n)]
        self.configurar(por_defecto=0, rc={}, espera={r: 0.5 for r in nombres})
        for p in ("ana", "bea"):
            self.wip(p, {r: con_import(p) for r in nombres})
        c = self.calculo()
        c.PLAZO_CICLO_S = 1.2
        vistos = []
        for _ in range(12):
            t = time.monotonic()
            c.sondear()
            dura = time.monotonic() - t
            self.assertLess(dura, c.PLAZO_CICLO_S + 1.5)
            self.assertLess(dura, c.CADA_S)
            vistos.append(len(self.un_par(c)["rutas_2b"]))
            if vistos[-1] == n:
                break
        self.assertTrue(0 < vistos[0] < n, vistos)          # el primero no llega a todos, pero intenta alguno
        self.assertEqual(vistos[-1], n, vistos)              # los que no cupieron se intentan en los siguientes
        self.assertEqual(vistos, sorted(vistos))
        self.assertLimpio()

    def test_sin_el_interruptor_todo_como_en_la_050(self):
        self.wip("ana", {"app.py": con_import("ana"), "conf.py": VALORES["ana"]})
        self.wip("bea", {"app.py": con_import("bea"), "conf.py": VALORES["bea"]})
        llamadas_git = []
        real = cm.ejecutar

        def espia(repo, *args, **kw):
            llamadas_git.append(args)
            return real(repo, *args, **kw)

        with mock.patch.object(cm, "ejecutar", espia):
            for kw in ({}, {"fusion_estructural": False}):
                llamadas_git.clear()
                c = cm.Calculo(self.relay, {"ana", "bea"}, aviso=self.avisos.append, ahora=Horas(), **kw)
                self.assertFalse(c.fusion_estructural)
                c.sondear()
                self.assertEqual(c.conflictos, [{"personas": ["ana", "bea"], "rutas": ["app.py", "conf.py"],
                                                 "desde": "2026-11-20T10:01:00Z"}])
                self.assertEqual([a[0] for a in llamadas_git], ["version", "fetch", "for-each-ref", "merge-tree"])
                self.assertIn("--name-only", llamadas_git[-1])
            self.assertEqual(self.llamadas(), [])
            # Con 2b: merge-tree sin --name-only.
            llamadas_git.clear()
            self.calculo().sondear()
            mt = [a for a in llamadas_git if a[0] == "merge-tree"]
            self.assertEqual(len(mt), 1)
            self.assertNotIn("--name-only", mt[0])
        self.assertEqual(len(self.avisos), 1)               # solo el de «Nivel 2b activo» del último
        self.assertLimpio()

    def test_deteccion_y_aviso_una_vez(self):
        self.wip("ana", {"app.py": con_import("ana")})
        self.wip("bea", {"app.py": con_import("bea")})
        casos = [("mergiraf 0.20.0", True, "Nivel 2b activo: mergiraf 0.20.0"),
                 ("mergiraf 0.21.3", True, "Nivel 2b activo: mergiraf 0.21.3"),
                 ("mergiraf 0.19.1", False, "Nivel 2b desactivado: mergiraf 0.19.1 < 0.20.0. Sigue el nivel 2."),
                 (None, False, "Nivel 2b desactivado: mergiraf --version no responde. Sigue el nivel 2.")]
        for version, activo, aviso in casos:
            self.configurar(version=version)
            self.avisos.clear()
            c = self.calculo()
            self.assertEqual(c.fusion_estructural, activo, version)
            c.sondear()
            c.sondear()
            self.assertEqual(self.avisos, [aviso])
            if not activo:
                self.assertEqual(c.conflictos[0], {"personas": ["ana", "bea"], "rutas": ["app.py"],
                                                   "desde": "2026-11-20T10:01:00Z"})
        self.avisos.clear()
        with mock.patch.object(cm.shutil, "which", return_value=None):
            c = self.calculo()
        self.assertFalse(c.fusion_estructural)
        self.assertEqual(self.avisos, ["Nivel 2b desactivado: mergiraf no está en el PATH. Sigue el nivel 2."])
        # Con git viejo no hay nivel 2 y ni se busca Mergiraf.
        self.avisos.clear()
        with mock.patch.object(cm.shutil, "which") as which:
            c = self.calculo(version=(2, 37))
        which.assert_not_called()
        self.assertFalse(c.fusion_estructural)
        self.assertEqual(len(self.avisos), 1)
        n = len(self.llamadas())
        self.assertEqual(n, 2)                               # solo las dos versiones válidas fusionaron app.py
        self.assertLimpio()


@unittest.skipUnless(MERGIRAF_REAL, "mergiraf no está en el PATH: casos con el real saltados")
class ConReal(CasosComunes, unittest.TestCase):
    REAL = MERGIRAF_REAL

    def setUp(self):
        super().setUp()
        self.assertTrue(cm.version_mergiraf(MERGIRAF_REAL) >= cm.MERGIRAF_MIN, "hace falta mergiraf ≥ 0.20.0")

    def test_ningun_atributo_de_git_cambia_el_resultado(self):
        """#88: Mergiraf lee `mergiraf.allow-parse-errors` y `linguist-language` con `git check-attr` en su cwd si la
        línea de órdenes no los fija. Con el relay en su clon, un .gitattributes de main, .git/info/attributes o el
        core.attributesFile global volvían a bajar a 2b un fichero con errores de sintaxis (o un .txt como Python)."""
        lados = {p: {"roto.py": con_import(p, BASE["roto.py"]), "importa.txt": con_import(p)} for p in ("ana", "bea")}
        for p in lados:
            self.wip(p, lados[p])
        atributos = "*.py mergiraf.allow-parse-errors\n*.txt linguist-language=Python mergiraf.language=python\n"
        anterior = os.getcwd()
        os.chdir(self.relay)                                # el cwd del relay de verdad: su clon
        self.addCleanup(os.chdir, anterior)

        def rojo(caso):
            with self.subTest(caso):
                c = self.calculo()
                c.sondear()
                par = self.un_par(c)
                self.assertEqual((par["rutas"], par["rutas_2b"]), (["importa.txt", "roto.py"], []))

        rojo("sin atributos")
        info = os.path.join(git(self.relay, "rev-parse", "--absolute-git-dir"), "info", "attributes")
        os.makedirs(os.path.dirname(info), exist_ok=True)
        with open(info, "w", encoding="utf-8") as f:
            f.write(atributos)
        rojo(".git/info/attributes")
        os.remove(info)
        con = self.commit({".gitattributes": atributos})          # versionado en main y en el checkout del relay
        git(self.taller, "push", "-q", self.remoto, f"{con}:refs/heads/main")
        git(self.relay, "pull", "-q", "--ff-only")
        rojo(".gitattributes de main")
        git(self.relay, "rm", "-q", ".gitattributes")
        git(self.relay, "-c", "user.email=x@example.com", "-c", "user.name=X", "commit", "-q", "-m", "sin")
        global_ = os.path.join(self.tmp, "gitconfig")
        fichero = os.path.join(self.tmp, "atributos")
        with open(fichero, "w", encoding="utf-8") as f:
            f.write(atributos)
        git(self.tmp, "config", "--file", global_, "core.attributesFile", fichero)
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": global_}):
            rojo("core.attributesFile global")
        self.assertLimpio()


def leer(ruta):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        return f.read()


def espera(condicion, segundos):
    limite = time.monotonic() + segundos
    while not condicion():
        if time.monotonic() > limite:
            raise AssertionError(f"no pasó en {segundos} s")
        time.sleep(0.05)


def vivo(pid):
    """¿Sigue vivo (y no es un zombi) el proceso? Solo fuera de Windows."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def plantado(directorio, marca):
    """Un `mergiraf` que no debe ejecutarse (en la copia del coordinador): responde a --version y deja `marca`. En
    Windows, un .exe, un .bat y un .cmd."""
    os.makedirs(directorio)
    script = os.path.join(directorio, "plantado.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(f"open({marca!r}, 'w').close()\nprint('mergiraf 0.20.0')\n")
    if os.name == "nt":
        mergiraf_falso.exe(os.path.join(directorio, "mergiraf.exe"), script)
        for ext in (".bat", ".cmd"):
            with open(os.path.join(directorio, "mergiraf" + ext), "w", encoding="utf-8") as f:
                f.write(f'@"{sys.executable}" "{script}" %*\r\n')
    else:
        ruta = os.path.join(directorio, "mergiraf")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\nexec '{sys.executable}' '{script}' \"$@\"\n")
        os.chmod(ruta, 0o755)


if __name__ == "__main__":
    unittest.main()
