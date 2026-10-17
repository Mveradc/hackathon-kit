"""M9a, K-93: el relay con `web_nueva` (api.md §3): SSE `eventos` y `servicios` en estado.json; sin ella, como en M8h.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import relay as relay_mod  # noqa: E402
import servicios  # noqa: E402
from esquema import Esquema  # noqa: E402
from red import Servidor  # noqa: E402

PERSONAS = [{"persona": "ana", "nombre": "Ana"}, {"persona": "luis", "nombre": "Luis"}]
AUTORIDAD = "# Autoridad\n## Por dueño\n### Ana (@ana) · `api/`, `web/`\n### Luis (@luis) · `motor/`\n"
CONTRATOS = "# Contratos\n## web → api\nVive en: api/esquema.py\n"
CABECERA = ("# Servicios\nFuera de servicios: docs/\n\n## Servicios\n| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |\n"
            "|---|---|---|---|---|---|\n| api | api/ | 8000 | — | /salud | — |\n| web | web/ | — | — | — | — |\n")
CONEXIONES = "\n## Conexiones\n| De | A | Contrato | Prueba |\n|---|---|---|---|\n| web | api | web → api | `pytest t.py` |\n"


def evento(n, persona="ana", tipo="sesion.inicio", papel="principal", ts=None, **extra):
    e = {"v": 1, "id": f"s-{persona}-{n}", "ts": ts or relay_mod.ahora_iso(),
         "actor": {"persona": persona, "papel": papel, "sesion": f"s-{persona}"}, "tipo": tipo, "fuente": "hook"}
    e.update(extra)
    return e


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)


class EventosSinWebNueva(Base):
    def test_no_guarda_eventos_para_el_sse(self):
        r = relay_mod.Relay(self.dir, PERSONAS)
        r.recibir({"eventos": [evento(1), evento(2)]})
        r._pulso_github = True
        r.recalcular()
        self.assertEqual((r.seq, r.recientes), (0, []))
        self.assertNotIn("servicios", r.estado)


class EventosSSE(Base):
    def setUp(self):
        super().setUp()
        self.relay = relay_mod.Relay(os.path.join(self.dir, "relay"), PERSONAS, web_nueva=True)
        self.srv = Servidor(("127.0.0.1", 0), relay_mod.manejador(self.relay))
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def conecta(self):
        req = urllib.request.Request(self.url + "/v1/stream", headers={"Authorization": f"Bearer {self.relay.token}"})
        r = urllib.request.urlopen(req, timeout=10)
        self.addCleanup(r.close)

        def mensaje():
            campos = {}
            while True:
                l = r.readline().decode("utf-8").rstrip("\n")
                if not l:
                    return campos
                k, _, v = l.partition(": ")
                campos[k] = v
        self.assertEqual(mensaje()["event"], "estado")
        self.assertEqual(mensaje()["event"], "vista")
        return mensaje

    def envia(self, eventos):
        req = urllib.request.Request(self.url + "/v1/eventos", data=json.dumps({"eventos": eventos}).encode(),
                                     headers={"Authorization": f"Bearer {self.relay.token}"}, method="POST")
        urllib.request.urlopen(req, timeout=5).read()

    def test_eventos_con_lista_blanca_solo_los_nuevos(self):
        uno = self.conecta()
        self.envia([evento(1), evento(2, tipo="edicion", rutas=["api/a.py"]), evento(3, persona="luis", papel="worker")])
        m = uno()
        self.assertEqual(m["event"], "eventos")
        self.assertNotIn("id", m)                        # no va ligado a la versión
        cuerpo = json.loads(m["data"])
        self.assertEqual([e["id"] for e in cuerpo["eventos"]], ["s-ana-1", "s-ana-2", "s-luis-3"])
        self.assertTrue(all(set(e) == {"id", "tipo", "persona", "papel", "ts"} for e in cuerpo["eventos"]))
        self.assertEqual(cuerpo["eventos"][2]["papel"], "worker")
        self.assertNotIn("api/a.py", m["data"])          # sin rutas ni datos (constitución IX)
        # un latido no es un evento; un cliente nuevo no recibe los de antes
        seq = self.relay.seq
        self.relay.latido({"persona": "ana", "actores": [{"papel": "principal", "sesion": "s-ana", "ultima_senal":
                                                           relay_mod.ahora_iso()}]})
        self.assertEqual(self.relay.seq, seq)
        dos = self.conecta()
        self.envia([evento(4)])
        self.assertEqual([e["id"] for e in json.loads(dos()["data"])["eventos"]], ["s-ana-4"])
        self.assertEqual([e["id"] for e in json.loads(uno()["data"])["eventos"]], ["s-ana-4"])

    def test_pulso_de_github_solo_con_version_nueva(self):
        r = self.relay
        r._pulso_github = True
        r.recalcular()                                   # sin cambios: no hay paquete
        self.assertEqual(r.recientes, [])
        self.assertFalse(r._pulso_github)
        r.recibir({"eventos": [evento(9)]})
        r._pulso_github = True
        r.recalcular()
        ultimo = r.recientes[-1][1]
        self.assertEqual((ultimo["id"], ultimo["tipo"], ultimo["persona"]), (f"github-{r.version}", "github.sondeo", None))

    def test_recortados_por_encima_de_200(self):
        r = self.relay
        with r.lock:
            for i in range(250):
                r._reciente({"id": str(i), "tipo": "edicion", "persona": "ana", "papel": "principal", "ts": "x"})
            seq, nuevos, recortados = r.recientes_desde(0)
        self.assertEqual((seq, len(nuevos), recortados, nuevos[-1]["id"]), (250, 200, 50, "249"))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout.strip()


class Servicios(Base):
    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.dir, "repo")
        os.makedirs(os.path.join(self.repo, ".hackathon"))
        os.makedirs(os.path.join(self.repo, "docs"))
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "x"); git(self.repo, "config", "user.email", "x@example.com")
        self.escribe(".hackathon/autoridad.md", AUTORIDAD)
        self.escribe("docs/contratos.md", CONTRATOS)
        self.escribe(".hackathon/servicios.md", CABECERA + CONEXIONES)
        self.escribe("api/main.py", "x\n")
        self.sha_scaffold = self.commit("scaffold")
        self.escribe(".hackathon/servicios.md", CABECERA + "| cache | api/cache/ | 6379 | — | — | @ana |\n" + CONEXIONES)
        self.escribe("scripts/descarga.py", "x\n")
        self.sha_ana = self.commit("cache")

    def escribe(self, ruta, texto):
        p = os.path.join(self.repo, ruta)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def commit(self, m):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", m)
        return git(self.repo, "rev-parse", "HEAD")

    def relay(self, web_nueva=True):
        n = relay_mod.Novedades(self.repo, 300, web_nueva=web_nueva)
        n.sondear()                                      # sin origin: el fetch falla y lee HEAD
        return relay_mod.Relay(os.path.join(self.dir, "relay"), PERSONAS, novedades=n, web_nueva=web_nueva)

    def test_servicios_en_el_estado(self):
        r = self.relay()
        clave_api = servicios.leer(CABECERA)["filas"][0]["clave"]
        ts = relay_mod.ahora_iso()
        commit = {"v": 1, "id": "git-ana-commit-1", "ts": ts, "actor": {"persona": "ana", "papel": "humano"},
                  "tipo": "commit", "fuente": "git", "datos": {"sha": self.sha_ana, "rama": "main", "alcanzable": True}}
        caido = {"v": 1, "ts": ts, "actor": {"persona": "ana", "papel": "demonio"}, "tipo": "servicio.estado",
                 "fuente": "demonio", "datos": {"servicio": "api", "clave": clave_api, "puerto": 8000, "escucha": False,
                                                "salud": None}}
        ajeno = dict(caido, actor={"persona": "luis", "papel": "demonio"}, datos=dict(caido["datos"], escucha=True))
        prueba = evento(5, tipo="prueba", datos={"comando_sha": servicios.huella_prueba("pytest t.py"), "resultado": "falla",
                                                 "codigo": 1})
        r.recibir({"eventos": [commit, dict(caido, id="dem-ana-1"), dict(ajeno, id="dem-luis-1"), prueba]})
        r.recalcular()
        s = r.estado["servicios"]
        lista = {x["nombre"]: x for x in s["lista"]}
        self.assertEqual(lista["cache"]["confirmacion"]["por"], ["ana"])
        self.assertEqual(lista["cache"]["confirmacion"]["valor"], "confirmada")
        self.assertTrue(lista["api"]["confirmacion"]["de_scaffold"])
        self.assertEqual(lista["api"]["comprobado"]["valor"], {"escucha": False, "salud": None})   # el de ana, no el de luis
        self.assertEqual(s["conexiones"][0]["resultado"]["valor"], "falla")
        tipos = sorted(d["tipo"] for d in s["desajustes"])
        self.assertEqual(tipos, ["codigo_fuera", "prueba_falla", "puerto_sin_respuesta"])
        fuera = next(d for d in s["desajustes"] if d["tipo"] == "codigo_fuera")
        self.assertEqual(fuera["rutas"], ["scripts/descarga.py"])
        self.assertIsNone(Esquema("estado.schema.json").error(r.estado))

    def test_arbol_suma_rutas_y_sha_desconocido_no_confirma(self):
        r = self.relay()
        arbol = evento(7, tipo="arbol", rutas=["notas.txt", "api/b.py"])
        r.recibir({"eventos": [arbol]})
        r.recalcular()
        s = r.estado["servicios"]
        cache = next(x for x in s["lista"] if x["nombre"] == "cache")
        self.assertEqual(cache["confirmacion"]["valor"], "sin_confirmar")   # sin el evento commit de ana
        fuera = next(d for d in s["desajustes"] if d["tipo"] == "codigo_fuera")
        self.assertEqual(fuera["rutas"], ["notas.txt", "scripts/descarga.py"])

    def test_sin_web_nueva_no_hay_servicios(self):
        r = self.relay(web_nueva=False)
        r.recalcular()
        self.assertNotIn("servicios", r.estado)
        self.assertIsNone(r.novedades.servicios)


INTRUSO = "| intruso | api/intruso/ | 9999 | — | /x | — |\n"


class CreacionDelFichero(Base):
    """Issue #2, hallazgo 1 (y sección 6, casos 1, 7 y 8): «el commit que creó servicios.md» sin depender de la
    simplificación de historia de git log. Si no se sabe con certeza, ninguna fila es de /hack-scaffold."""

    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.dir, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        for k, v in (("user.name", "x"), ("user.email", "x@example.com"), ("core.autocrlf", "false")):
            git(self.repo, "config", k, v)
        self.escribe(".hackathon/autoridad.md", AUTORIDAD)
        self.escribe("docs/contratos.md", CONTRATOS)
        self.commit("raiz", "2026-11-25T17:00:00Z")

    def escribe(self, ruta, texto):
        p = os.path.join(self.repo, ruta)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def commit(self, m, cuando):
        env = dict(os.environ, GIT_AUTHOR_DATE=cuando, GIT_COMMITTER_DATE=cuando)
        subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.repo, "commit", "-qm", m], check=True, capture_output=True, env=env)
        return git(self.repo, "rev-parse", "HEAD")

    def scaffold(self):
        self.escribe(".hackathon/servicios.md", CABECERA + CONEXIONES)
        return self.commit("scaffold", "2026-11-25T18:00:00Z")

    def servicios(self, eventos=()):
        n = relay_mod.Novedades(self.repo, 300, web_nueva=True)
        n.sondear()
        r = relay_mod.Relay(os.path.join(self.dir, "relay"), PERSONAS, novedades=n, web_nueva=True)
        r.recibir({"eventos": list(eventos)})
        r.recalcular()
        self.assertIsNone(Esquema("estado.schema.json").error(r.estado))
        return {x["nombre"]: x["confirmacion"] for x in r.estado["servicios"]["lista"]}, r

    def commit_de(self, persona, sha):
        return {"v": 1, "id": f"git-{persona}-commit-{sha[:7]}", "ts": relay_mod.ahora_iso(),
                "actor": {"persona": persona, "papel": "humano"}, "tipo": "commit", "fuente": "git",
                "datos": {"sha": sha, "rama": "main", "alcanzable": True}}

    def nada_de_scaffold(self, lista):
        for nombre, c in lista.items():
            self.assertEqual((c["valor"], c["de_scaffold"]), ("sin_confirmar", False), nombre)

    def test_historia_lineal_si_es_de_scaffold(self):
        self.scaffold()
        lista, _ = self.servicios()
        self.assertEqual((lista["api"]["valor"], lista["api"]["de_scaffold"]), ("confirmada", True))

    def test_merge_que_deja_el_fichero_de_una_rama_esconde_el_scaffold(self):
        # [reproducido] main: raiz → scaffold. @luis, desde raiz, crea su servicios.md con «intruso»; merge --no-ff
        # en el que el fichero queda como el de su rama (-X theirs). git log -- <ruta> ya no enseña el scaffold.
        for cuando_luis in ("2026-11-25T18:30:00Z", "2026-11-25T17:30:00Z"):   # después o antes del scaffold
            with self.subTest(cuando_luis=cuando_luis):
                git(self.repo, "checkout", "-q", "main")
                git(self.repo, "reset", "-q", "--hard", git(self.repo, "rev-list", "--max-parents=0", "HEAD"))
                self.scaffold()
                git(self.repo, "checkout", "-q", "-B", "luis", "HEAD~1")
                self.escribe(".hackathon/servicios.md", CABECERA + INTRUSO + CONEXIONES)
                sha_luis = self.commit("luis", cuando_luis)
                git(self.repo, "checkout", "-q", "main")
                git(self.repo, "merge", "-q", "--no-ff", "-X", "theirs", "luis", "-m", "merge")
                simplificada = git(self.repo, "log", "--format=%H", "--", ".hackathon/servicios.md").split()
                self.assertEqual(simplificada, [sha_luis])                  # el caso del issue, tal cual
                lista, _ = self.servicios([self.commit_de("luis", sha_luis)])
                self.nada_de_scaffold(lista)
                self.assertEqual(lista["intruso"]["faltan"], ["ana"])

    def test_rama_sin_ancestro_comun(self):
        self.scaffold()
        git(self.repo, "checkout", "-q", "--orphan", "luis")
        git(self.repo, "rm", "-rq", "--cached", ".")
        self.escribe(".hackathon/servicios.md", CABECERA + INTRUSO + CONEXIONES)
        sha_luis = self.commit("luis", "2026-11-25T18:30:00Z")
        git(self.repo, "checkout", "-q", "-f", "main")
        git(self.repo, "merge", "-q", "--no-ff", "--allow-unrelated-histories", "-X", "theirs", "luis", "-m", "merge")
        lista, _ = self.servicios([self.commit_de("luis", sha_luis)])
        self.nada_de_scaffold(lista)

    def test_merge_que_crea_el_fichero(self):
        git(self.repo, "checkout", "-q", "-b", "otra")
        self.escribe("otra.txt", "x\n")
        self.commit("otra", "2026-11-25T17:30:00Z")
        git(self.repo, "checkout", "-q", "main")
        self.escribe("main.txt", "x\n")
        self.commit("main", "2026-11-25T17:40:00Z")
        git(self.repo, "merge", "-q", "--no-ff", "--no-commit", "otra")
        self.escribe(".hackathon/servicios.md", CABECERA + CONEXIONES)
        self.commit("merge con servicios.md", "2026-11-25T18:00:00Z")
        self.assertEqual(len(git(self.repo, "log", "-1", "--format=%P").split()), 2)
        lista, _ = self.servicios()
        self.nada_de_scaffold(lista)

    def test_borrado_y_vuelto_a_crear(self):
        self.scaffold()
        git(self.repo, "rm", "-q", ".hackathon/servicios.md")
        self.commit("fuera", "2026-11-25T18:10:00Z")
        self.escribe(".hackathon/servicios.md", CABECERA + INTRUSO + CONEXIONES)
        self.commit("otra vez", "2026-11-25T18:20:00Z")
        lista, _ = self.servicios()
        self.nada_de_scaffold(lista)

    def test_renombrado_a_servicios_md(self):
        self.escribe("notas/servicios.md", CABECERA + INTRUSO + CONEXIONES)
        self.commit("notas", "2026-11-25T17:30:00Z")
        git(self.repo, "mv", "notas/servicios.md", ".hackathon/servicios.md")
        self.commit("mv", "2026-11-25T18:00:00Z")
        lista, _ = self.servicios()
        self.nada_de_scaffold(lista)

    def test_mas_commits_de_los_que_se_leen(self):
        from unittest import mock
        self.scaffold()
        for i in range(3):
            self.escribe(".hackathon/servicios.md", CABECERA + CONEXIONES + "\n" * (i + 1))
            self.commit(f"espacios {i}", f"2026-11-25T18:1{i}:00Z")
        with mock.patch.object(relay_mod, "SERVICIOS_COMMITS", 3):        # el scaffold queda fuera de los que se leen
            lista, _ = self.servicios()
        self.nada_de_scaffold(lista)
        lista, _ = self.servicios()
        self.assertTrue(lista["api"]["de_scaffold"])

    def test_la_cache_de_confirmaciones_ve_un_nacimiento_nuevo(self):
        # Un merge (igual a sus dos padres) trae otro commit que crea el fichero, más viejo que los que se leen: la
        # lista de shas no cambia, pero el scaffold deja de ser seguro.
        from unittest import mock
        self.scaffold()
        with mock.patch.object(relay_mod, "SERVICIOS_COMMITS", 1):
            lista, r = self.servicios()
            self.assertTrue(lista["api"]["de_scaffold"])
            shas = [v["sha"] for v in r.novedades.servicios["versiones"]]
            git(self.repo, "checkout", "-q", "-B", "luis", "HEAD~1")
            self.escribe(".hackathon/servicios.md", CABECERA + CONEXIONES)
            self.commit("luis", "2026-11-25T17:30:00Z")
            git(self.repo, "checkout", "-q", "main")
            git(self.repo, "merge", "-q", "--no-ff", "luis", "-m", "merge")
            r.novedades.sondear()
            self.assertEqual([v["sha"] for v in r.novedades.servicios["versiones"]], shas)
            r.recalcular()
        self.nada_de_scaffold({x["nombre"]: x["confirmacion"] for x in r.estado["servicios"]["lista"]})


if __name__ == "__main__":
    unittest.main()
