"""M9a, K-95: las acciones de la web (api.md §4, ADR-0010), sin modelo ni GitHub.

- Anotar, con un remoto `bare` y dos clones: la nota llega a criterios.md de origin/main con autor, hora y «Anotado
  por», saneada y sin coautoría; la copia, el índice y HEAD de la persona no cambian; la otra persona la ve en las
  novedades que calcula el relay; con el push rechazado, un reintento sobre el origin/main nuevo y las dos notas
  quedan; si vuelve a fallar, 409 y la copia sin tocar.
- Reclamar, con un gh falso: asigna el issue con `--add-assignee @me`, emite `reclamo` (fuente web, válido) y deja la
  línea de acciones.jsonl; otro dueño, no libre, inexistente, tope, gh de otra cuenta o que falla; sin GitHub, solo el
  evento; el motor lo pinta «reclamada», declarada y con fuente web.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import hashlib
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import acciones as acciones_mod  # noqa: E402
import agente as agente_mod  # noqa: E402
import relay as relay_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import derivar  # noqa: E402
from red import Servidor  # noqa: E402

A, B = "persona-a", "persona-b"
AHORA = "2026-11-20T10:05:00.000000Z"
ENTORNO = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_ASKPASS="", SSH_ASKPASS="")


def git(cwd, *args, entrada=None):
    r = subprocess.run(["git", "-c", "credential.helper=", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENTORNO, timeout=60, input=entrada)
    if r.returncode:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


def escribe(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


NOTA = {"papel": "jurado", "quien": "Ana", "que_dijo": "Valoraremos la demo con datos reales", "literal": True,
        "fuerza": "se valora", "donde": "apertura"}


class Base(unittest.TestCase):
    os_md = "# Hackathon OS\nactiva: sí\nweb_nueva: sí\ngithub: no\n"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bare = os.path.join(self.tmp, "equipo.git").replace("\\", "/")
        git(self.tmp, "init", "-q", "--bare", "-b", "main", self.bare)
        semilla = os.path.join(self.tmp, "semilla")
        git(self.tmp, "init", "-q", "-b", "main", semilla)
        self.identidad(semilla, "semilla")
        escribe(os.path.join(semilla, ".hackathon", "os.md"), self.os_md)
        escribe(os.path.join(semilla, ".hackathon", "coordinacion.md"),
                f"activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| A | @{A} |\n| B | @{B} |\n")
        escribe(os.path.join(semilla, "app.py"), "print('hola')\n")
        git(semilla, "add", "-A")
        git(semilla, "commit", "-qm", "inicio")
        git(semilla, "push", "-q", self.bare, "main")
        self.ca, self.cb = self.clon("a", A), self.clon("b", B)
        self.ag = agente_mod.Agente(self.ca, A, reloj=lambda: 1_800_000_000.0, ahora=lambda: AHORA)
        self.ag.tz = timezone.utc

    def identidad(self, repo, nombre):
        git(repo, "config", "user.name", nombre)
        git(repo, "config", "user.email", f"{nombre}@example.com")

    def clon(self, nombre, persona):
        destino = os.path.join(self.tmp, nombre).replace("\\", "/")
        git(self.tmp, "clone", "-q", self.bare, destino)
        self.identidad(destino, persona)
        return destino

    def main_remoto(self, ruta):
        return git(self.bare, "show", f"main:{ruta}")


def huella(repo):
    """Lo que Anotar no puede tocar: el estado de la copia, el índice (bytes) y HEAD."""
    with open(os.path.join(repo, ".git", "index"), "rb") as f:
        indice = hashlib.sha256(f.read()).hexdigest()
    return git(repo, "status", "--porcelain", "--untracked-files=all"), indice, git(repo, "rev-parse", "HEAD")


class Anotar(Base):
    def copia_con_cambios(self):
        """La persona tiene trabajo a medias: uno en el índice, uno sin añadir y uno nuevo."""
        escribe(os.path.join(self.ca, "app.py"), "print('adiós')\n")
        git(self.ca, "add", "app.py")
        escribe(os.path.join(self.ca, "app.py"), "print('otra')\n")
        escribe(os.path.join(self.ca, "nuevo.txt"), "x\n")
        return huella(self.ca)

    def test_llega_a_main_sin_tocar_la_copia(self):
        antes = self.copia_con_cambios()
        base = git(self.bare, "rev-parse", "main")
        cuerpo = dict(NOTA, que_dijo="línea uno\nlínea\t\tdos\x07", quien="## Ana\n> García", donde=None,
                      papel="organizacion")
        codigo, r = self.ag.accion("/v1/anotar", cuerpo)
        self.assertEqual(codigo, 200, r)
        self.assertEqual(r, {"ok": True, "sha": git(self.bare, "rev-parse", "main")})
        self.assertEqual(huella(self.ca), antes)                       # ni la copia, ni el índice, ni HEAD
        self.assertFalse(os.path.exists(os.path.join(self.ag.dir, "nota.index")))
        criterios = self.main_remoto(".hackathon/criterios.md")
        self.assertTrue(criterios.startswith("# Criterios del jurado"))  # sin criterios.md: la plantilla
        self.assertTrue(criterios.endswith(
            "\n\n## 2026-11-20 10:05 · Ana > García (organización)\n- Dónde: —\n- Qué dijo: «línea uno línea dos»\n"
            "- Fuerza: se valora\n- Afecta a: — (anotada desde la web; la revisa /hack-check)\n- Anotado por: @persona-a"),
            criterios)
        self.assertIn(".hackathon/criterios.md merge=union", self.main_remoto(".gitattributes").splitlines())
        mensaje = git(self.bare, "log", "-1", "--format=%P%n%an <%ae>%n%B", "main").splitlines()
        self.assertEqual(mensaje[0], base)                             # padre: el origin/main de entonces
        self.assertEqual(mensaje[1], f"{A} <{A}@example.com>")         # la identidad de git del clon
        self.assertEqual(mensaje[2], "Criterio: organización · línea uno línea dos")
        self.assertNotIn("co-authored-by", "\n".join(mensaje).lower())
        self.assertEqual(git(self.bare, "diff", "--name-only", f"{base}..main").splitlines(),
                         [".gitattributes", ".hackathon/criterios.md"])
        # La otra persona: en las novedades del relay (que lee origin/main) y en su próximo git pull.
        nov = relay_mod.novedades_de("", criterios, tz=timezone.utc)
        self.assertEqual([(n["tipo"], n.get("autor"), n["observado_en"]) for n in nov],
                         [("criterio", "@persona-a", "2026-11-20T10:05:00Z")])
        self.assertIn("«línea uno línea dos»", nov[0]["resumen"])
        git(self.cb, "pull", "-q")
        with open(os.path.join(self.cb, ".hackathon", "criterios.md"), encoding="utf-8") as f:
            self.assertEqual(f.read().rstrip("\n"), criterios)

    def test_se_anade_al_final_y_no_repite_gitattributes(self):
        escribe(os.path.join(self.cb, ".hackathon", "criterios.md"), "# Criterios del jurado\n\n## 2026-11-20 09:00 · Luis (mentor)\n- Qué dijo: (paráfrasis) algo\n")
        escribe(os.path.join(self.cb, ".gitattributes"), "*.sh text eol=lf\n.hackathon/criterios.md   merge=union\n")
        git(self.cb, "add", "-A")
        git(self.cb, "commit", "-qm", "criterios")
        git(self.cb, "push", "-q")
        codigo, r = self.ag.accion("/v1/anotar", dict(NOTA, literal=False))
        self.assertEqual(codigo, 200, r)
        criterios = self.main_remoto(".hackathon/criterios.md")
        self.assertTrue(criterios.startswith("# Criterios del jurado\n\n## 2026-11-20 09:00 · Luis (mentor)\n"
                                             "- Qué dijo: (paráfrasis) algo\n\n## 2026-11-20 10:05 · Ana (jurado)\n"))
        self.assertIn("- Qué dijo: (paráfrasis) Valoraremos la demo con datos reales\n", criterios)
        self.assertIn("- Dónde: apertura\n", criterios)
        self.assertEqual(git(self.bare, "diff", "--name-only", "main~1..main"), ".hackathon/criterios.md")

    def test_push_rechazado_reintenta_una_vez(self):
        antes = self.copia_con_cambios()
        veces = []

        def otra_nota_antes():
            """Mientras el demonio de A prepara su nota, B sube la suya (con /hack-note)."""
            veces.append(1)
            if len(veces) == 1:
                ruta = os.path.join(self.cb, ".hackathon", "criterios.md")
                escribe(ruta, "# Criterios del jurado\n\n## 2026-11-20 10:04 · Luis (mentor)\n- Anotado por: @persona-b\n")
                git(self.cb, "add", "-A")
                git(self.cb, "commit", "-qm", "Criterio: mentor")
                git(self.cb, "push", "-q")
        self.ag.acciones.antes_del_push = otra_nota_antes
        codigo, r = self.ag.accion("/v1/anotar", NOTA)
        self.assertEqual((codigo, len(veces)), (200, 2), r)
        criterios = self.main_remoto(".hackathon/criterios.md")
        self.assertIn("## 2026-11-20 10:04 · Luis (mentor)", criterios)       # las dos notas quedan
        self.assertIn("## 2026-11-20 10:05 · Ana (jurado)", criterios)
        self.assertEqual(git(self.bare, "log", "-1", "--format=%P", "main"), git(self.cb, "rev-parse", "HEAD"))
        self.assertEqual(huella(self.ca), antes)

    def test_rechazado_dos_veces_409_sin_tocar_la_copia(self):
        antes = self.copia_con_cambios()
        veces = []

        def siempre_otra():
            veces.append(1)
            escribe(os.path.join(self.cb, f"otra{len(veces)}.txt"), "x\n")
            git(self.cb, "add", "-A")
            git(self.cb, "commit", "-qm", f"otra {len(veces)}")
            git(self.cb, "push", "-q")
        self.ag.acciones.antes_del_push = siempre_otra
        codigo, r = self.ag.accion("/v1/anotar", NOTA)
        self.assertEqual((codigo, len(veces)), (409, 2), r)
        self.assertIn("error", r)
        self.assertEqual(git(self.bare, "rev-parse", "main"), git(self.cb, "rev-parse", "HEAD"))
        self.assertEqual(huella(self.ca), antes)
        self.assertFalse(os.path.exists(os.path.join(self.ag.dir, "nota.index")))

    def test_git_falla_502(self):
        git(self.ca, "remote", "set-url", "origin", os.path.join(self.tmp, "no-existe.git"))
        antes = huella(self.ca)
        codigo, r = self.ag.accion("/v1/anotar", NOTA)
        self.assertEqual(codigo, 502, r)
        self.assertTrue(r["error"].startswith("git fetch"), r)
        self.assertNotIn("\n", r["error"])
        self.assertEqual(huella(self.ca), antes)

    def test_campos(self):
        largo = "x" * 501
        casos = [
            ({**NOTA, "otro": 1}, "otro"), ({**NOTA, "papel": "jurado2"}, "papel"), ({**NOTA, "fuerza": "mucho"}, "fuerza"),
            ({**NOTA, "literal": "sí"}, "literal"), ({**NOTA, "que_dijo": largo}, "que_dijo"),
            ({**NOTA, "que_dijo": " \n#> "}, "que_dijo"), ({**NOTA, "quien": "q" * 81}, "quien"),
            ({**NOTA, "donde": 3}, "donde"), ({k: v for k, v in NOTA.items() if k != "fuerza"}, "fuerza"),
        ]
        base = git(self.bare, "rev-parse", "main")
        for cuerpo, campo in casos:
            codigo, r = self.ag.accion("/v1/anotar", cuerpo)
            self.assertEqual((codigo, r.get("campo")), (400, campo), cuerpo)
            self.assertIn("error", r)
        self.assertEqual(self.ag.accion("/v1/anotar", ["x"])[0], 400)
        self.assertEqual(git(self.bare, "rev-parse", "main"), base)     # nada subido

    def test_saneado(self):
        s = acciones_mod.sanear
        self.assertEqual(s("  # > ## título\r\ncon\u2028salto  y\u202e\x00 control "), "título con salto y control")
        self.assertEqual(s("dato #3 > 2"), "dato #3 > 2")               # solo al principio
        self.assertEqual(acciones_mod.anadir(b"a\r\nb\r\n\r\n", "c\nd\n"), b"a\r\nb\r\n\r\nc\r\nd\r\n")
        self.assertEqual(acciones_mod.anadir("\ufeffa\n".encode("utf-8"), "c\n"), "\ufeffa\n\nc\n".encode("utf-8"))
        self.assertEqual(acciones_mod.anadir("a\n".encode("utf-16"), "c\n").decode("utf-16"), "a\n\nc\n")
        self.assertEqual(acciones_mod.anadir(b"", "c\n"), b"c\n")


class GhFalso:
    def __init__(self, login=A, falla_edit=False):
        self.login, self.falla_edit, self.llamadas = login, falla_edit, []

    def __call__(self, args):
        self.llamadas.append(args)
        if args[:2] == ["api", "user"]:
            return (0, self.login, "") if self.login else (1, "", "error connecting to api.github.com\nmás")
        if args[:2] == ["issue", "edit"]:
            return (1, "", "GraphQL: Could not resolve to an issue\nmás") if self.falla_edit else (0, "https://x/5", "")
        return 1, "", "orden desconocida"


def tarea(tid, valor, dueno=A, issue=None, declarado=None):
    t = {"id": tid, "titulo": f"Tarea {tid}", "dueno": dueno, "depende_de": [],
         "estado": {"valor": valor, "fuente": "derivado", "observado_en": AHORA}, "declarado": declarado}
    if issue:
        t["issue"] = issue
    return t


class Reclamar(Base):
    os_md = "# Hackathon OS\nactiva: sí\nweb_nueva: sí\n"     # github: sí por defecto

    def setUp(self):
        super().setUp()
        self.gh = self.ag.acciones.gh = GhFalso()
        self.ag.estado = {"tareas": [tarea("T01", "lista", issue=5), tarea("T02", "pendiente", dueno=B, issue=6),
                                     tarea("T03", "en_curso", issue=7), tarea("T04", "lista", dueno=""),
                                     tarea("T05", "lista", issue=9), tarea("T06", "pendiente", issue=10)]}
        self.registro = os.path.join(self.ag.dir, "acciones.jsonl")

    def lineas(self):
        if not os.path.exists(self.registro):
            return []
        with open(self.registro, "rb") as f:
            datos = f.read()
        self.assertTrue(datos == b"" or datos.endswith(b"\n"))
        return [json.loads(l) for l in datos.splitlines()]

    def test_con_github(self):
        codigo, r = self.ag.accion("/v1/reclamar", {"tarea": "T01"})
        self.assertEqual((codigo, r), (200, {"ok": True, "issue": 5}))
        self.assertEqual(self.gh.llamadas, [["api", "user", "--jq", ".login"],
                                            ["issue", "edit", "5", "--repo", "equipo/reto", "--add-assignee", "@me"]])
        [e] = self.ag.cola
        self.assertTrue(Esquema("eventos.schema.json").valido(e), e)
        self.assertEqual((e["tipo"], e["fuente"], e["tarea"], e["actor"], e["ts"]),
                         ("reclamo", "web", "T01", {"persona": A, "papel": "humano"}, AHORA))
        self.assertEqual(e["id"], f"web-{A}-reclamo-T01-1800000000000")
        self.assertEqual(self.lineas(), [{"id": e["id"], "tipo": "reclamo", "tarea": "T01", "ts": AHORA}])
        # El motor lo pinta reclamada, con la fuente web y declarada (principio II).
        r = derivar({"id": "T01", "dueno": A, "depende_de": []}, {"creado_en": AHORA, "acciones": []}, [e], {}, {A, B},
                    "2026-11-20T10:06:00Z")
        self.assertEqual((r["estado"]["valor"], r["estado"]["fuente"], r["estado"].get("declarado")),
                         ("reclamada", "web", True))
        # Un segundo clic, antes de que el estado lo refleje: no hay otro reclamo ni otro turno.
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T01"})[0], 409)
        # gh api user, una sola vez.
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T05"}), (200, {"ok": True, "issue": 9}))
        self.assertEqual(sum(1 for c in self.gh.llamadas if c[:2] == ["api", "user"]), 1)
        self.assertEqual(len(self.lineas()), 2)

    def test_rechazos(self):
        casos = [({"tarea": "T02"}, 409, "es de @persona-b según el plan"), ({"tarea": "T03"}, 409, "está en curso"),
                 ({"tarea": "T99"}, 404, None), ({"tarea": "T1"}, 400, None), ({"tarea": "T01", "x": 1}, 400, None),
                 ({"id": "T01"}, 400, None), ({"tarea": 1}, 400, None), ("T01", 400, None)]
        for cuerpo, esperado, error in casos:
            codigo, r = self.ag.accion("/v1/reclamar", cuerpo)
            self.assertEqual(codigo, esperado, (cuerpo, r))
            if error:
                self.assertEqual(r["error"], error)
        self.ag.estado["tareas"][0]["declarado"] = {"valor": "cerrada", "fuente": "github", "observado_en": AHORA}
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T01"})[0], 409)
        self.assertEqual((self.gh.llamadas, self.ag.cola, self.lineas()), ([], [], []))
        self.ag.estado = None
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T04"})[0], 503)

    def test_gh_de_otra_cuenta_o_que_falla(self):
        self.gh.login = "otra-cuenta"
        codigo, r = self.ag.accion("/v1/reclamar", {"tarea": "T01"})
        self.assertEqual((codigo, r["error"]), (409, f"tu gh es @otra-cuenta, no @{A}"))
        self.assertEqual(len(self.gh.llamadas), 1)                       # no asigna
        self.ag.acciones.login, self.gh.login = None, None
        codigo, r = self.ag.accion("/v1/reclamar", {"tarea": "T01"})
        self.assertEqual((codigo, r["error"]), (502, "gh api user: error connecting to api.github.com"))
        self.gh.login, self.gh.falla_edit = A, True
        codigo, r = self.ag.accion("/v1/reclamar", {"tarea": "T01"})
        self.assertEqual((codigo, r["error"]), (502, "gh issue edit: GraphQL: Could not resolve to an issue"))
        self.assertEqual((self.ag.cola, self.lineas()), ([], []))        # si gh falla, no se emite nada

    def test_sin_issue_solo_el_evento(self):
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T04"}), (200, {"ok": True, "issue": None}))
        self.assertEqual(self.gh.llamadas, [])
        self.assertEqual([e["tarea"] for e in self.ag.cola], ["T04"])

    def test_tope_por_hora(self):
        with open(self.registro, "w", encoding="utf-8") as f:
            for i in range(10):
                f.write(json.dumps({"id": f"web-{A}-reclamo-T{20 + i}-1", "tipo": "reclamo", "tarea": f"T{20 + i}",
                                    "ts": f"2026-11-20T09:{10 + i}:00.000000Z"}) + "\n")
            f.write("{rota\n")
        codigo, r = self.ag.accion("/v1/reclamar", {"tarea": "T04"})
        self.assertEqual(codigo, 429, r)
        self.ag.ahora = lambda: "2026-11-20T10:10:30.000000Z"           # la primera ya tiene más de una hora
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T04"})[0], 200)
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T06"})[0], 429)


class ReclamarSinGithub(Reclamar):
    os_md = "# Hackathon OS\nactiva: sí\nweb_nueva: sí\ngithub: no\n"

    def test_con_github(self):
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T01"}), (200, {"ok": True, "issue": None}))
        self.assertEqual(self.gh.llamadas, [])
        self.assertEqual([(e["tipo"], e["fuente"]) for e in self.ag.cola], [("reclamo", "web")])
        self.assertEqual([l["tarea"] for l in self.lineas()], ["T01"])

    def test_gh_de_otra_cuenta_o_que_falla(self):
        self.gh.login, self.gh.falla_edit = None, True
        self.assertEqual(self.ag.accion("/v1/reclamar", {"tarea": "T01"})[0], 200)


class PorHttp(Base):
    """Las dos rutas de verdad, con el manejador del demonio: lo que espera la web (hkos/web-src/src/datos/acciones.js)."""

    def test_respuestas(self):
        srv = Servidor(("127.0.0.1", 0), agente_mod.manejador(self.ag))
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        puerto = srv.server_address[1]
        self.ag.estado = {"tareas": [tarea("T04", "lista", dueno="")]}

        def post(ruta, cuerpo):
            c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=60)
            c.request("POST", ruta, json.dumps(cuerpo).encode(), {"Content-Type": "application/json",
                                                                   "X-HK-Token": self.ag.web_token})
            r = c.getresponse()
            datos = json.loads(r.read())
            c.close()
            self.assertEqual(r.getheader("Cache-Control"), "no-store")
            return r.status, datos
        codigo, r = post("/v1/anotar", NOTA)
        self.assertEqual((codigo, set(r)), (200, {"ok", "sha"}))
        self.assertRegex(r["sha"], r"^[0-9a-f]{40}$")
        self.assertEqual(post("/v1/anotar", {**NOTA, "fuerza": "x"}), (400, {"error": "fuera de la lista", "campo": "fuerza"}))
        self.assertEqual(post("/v1/reclamar", {"tarea": "T04"}), (200, {"ok": True, "issue": None}))
        self.assertEqual(post("/v1/reclamar", {"tarea": "T09"})[0], 404)


if __name__ == "__main__":
    unittest.main()
