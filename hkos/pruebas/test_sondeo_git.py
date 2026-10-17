"""K-52 (M8e): sondeo de git del demonio (api.md §4) sobre un repo con remoto bare, contra un relay en el mismo
proceso. Criterio 4 (rama sin ID → sin_tarea, con la persona sin tareas abiertas) y la parte de git del criterio 2
(commit con ID y push → publicada), sin modelos.

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

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import agente as agente_mod  # noqa: E402
import relay as relay_mod  # noqa: E402
from modelo import calcular  # noqa: E402
from red import Servidor, ahora_iso  # noqa: E402


PERSONAS = [{"persona": "persona-b", "nombre": "B"}]


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, check=True).stdout.strip()


def escribe_fichero(ruta, texto):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)


def lee_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class SondeoGit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        remoto = os.path.join(self.tmp, "remoto.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remoto], check=True)
        self.repo = os.path.join(self.tmp, "clon").replace("\\", "/")
        subprocess.run(["git", "init", "-q", "-b", "main", self.repo], check=True)
        for k, v in (("user.name", "B"), ("user.email", "b@example.com")):
            git(self.repo, "config", k, v)
        self.escribe("a.txt", "uno\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-qm", "inicio")
        git(self.repo, "remote", "add", "origin", remoto)
        git(self.repo, "push", "-q", "-u", "origin", "main")
        os.makedirs(os.path.join(self.repo, ".git", "hackathon", "os", "eventos"))
        self.relay = relay_mod.Relay(os.path.join(self.tmp, "relay"), PERSONAS, ahora=ahora_iso)
        srv = Servidor(("127.0.0.1", 0), relay_mod.manejador(self.relay))
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        d = os.path.join(self.repo, ".git", "hackathon", "os")
        self.url = f"http://127.0.0.1:{srv.server_address[1]}"
        escribe_fichero(os.path.join(d, "relay.url"), self.url + "\n")
        escribe_fichero(os.path.join(d, "token"), self.relay.token + "\n")
        self.reloj = Reloj()

    def escribe(self, ruta, texto):
        with open(os.path.join(self.repo, ruta), "a", encoding="utf-8") as f:
            f.write(texto)

    def commit(self, mensaje, rama=None):
        if rama:
            git(self.repo, "checkout", "-q", "-B", rama)
        self.escribe("a.txt", mensaje + "\n")
        git(self.repo, "commit", "-qam", mensaje)
        return git(self.repo, "rev-parse", "HEAD")

    def agente(self):
        return agente_mod.Agente(self.repo, "persona-b", reloj=self.reloj, ahora=ahora_iso)

    def vuelta(self, a):
        self.reloj.t += 16
        a.ciclo()

    def git_del_relay(self, arbol=False):
        """Los eventos de git del relay; los `arbol` del demonio, solo con arbol=True."""
        return [e for e in self.relay.eventos if e["fuente"] == "git" and (arbol or e["tipo"] != "arbol")]

    def test_primera_vuelta_no_emite_lo_ya_subido(self):
        a = self.agente()
        self.vuelta(a)
        self.assertEqual(self.git_del_relay(), [])
        self.assertEqual(lee_json(os.path.join(a.dir, "git.json"))["punta"], git(self.repo, "rev-parse", "origin/main"))

    def test_rama_sin_id_sale_en_sin_tarea(self):
        """Criterio 4, con la persona sin tareas abiertas (T08 de B, sin reclamar)."""
        a = self.agente()
        self.vuelta(a)
        sha = self.commit("probar otra cosa", rama="experimento")
        self.vuelta(a)
        [e] = self.git_del_relay()
        self.assertEqual((e["tipo"], e.get("tarea"), e["datos"]["rama"], e["datos"]["alcanzable"], e["datos"]["sha"]),
                         ("commit", None, "experimento", False, sha))
        r = calcular([{"id": "T08", "titulo": "Ocho", "dueno": "persona-b", "depende_de": []}],
                     {"T08": {"creado_en": "2020-01-01T09:00:00Z", "acciones": []}}, self.relay.eventos, PERSONAS, ahora_iso())
        self.assertEqual([(s["persona"], s["que"]) for s in r["sin_tarea"]], [("persona-b", "commit: experimento")])
        self.assertEqual(r["tareas"][0]["estado"]["valor"], "lista")

    def test_commit_con_id_y_push_publican(self):
        """La tarea humana del criterio 2: commit «T08 · …» en main, push → en_curso y luego publicada."""
        a = self.agente()
        self.vuelta(a)
        sha = self.commit("T08 · arreglar los 500")
        self.vuelta(a)
        tareas = [{"id": "T08", "titulo": "Ocho", "dueno": "persona-b", "depende_de": []}]
        issues = {"T08": {"creado_en": "2020-01-01T09:00:00Z", "acciones": []}}
        r = calcular(tareas, issues, self.relay.eventos, PERSONAS, ahora_iso())
        self.assertEqual((r["tareas"][0]["estado"]["valor"], r["tareas"][0]["estado"]["fuente"]), ("en_curso", "git"))
        git(self.repo, "push", "-q", "origin", "main")
        self.vuelta(a)
        push = [e for e in self.git_del_relay() if e["tipo"] == "push"]
        self.assertEqual([(p["datos"]["sha"], p["datos"]["incluye"]) for p in push], [(sha, [sha])])
        self.assertEqual(len([e for e in self.git_del_relay() if e["tipo"] == "commit"]), 1)   # no se repite al subir
        r = calcular(tareas, issues, self.relay.eventos, PERSONAS, ahora_iso())
        self.assertEqual((r["tareas"][0]["estado"]["valor"], r["tareas"][0]["estado"]["fuente"]), ("publicada", "git"))

    def test_push_directo_emite_el_commit_alcanzable(self):
        """Commit y push antes de la siguiente vuelta: el commit sale igual, con alcanzable."""
        a = self.agente()
        self.vuelta(a)
        sha = self.commit("T08 · rápido")
        git(self.repo, "push", "-q", "origin", "main")
        self.vuelta(a)
        tipos = [(e["tipo"], e["datos"].get("alcanzable")) for e in self.git_del_relay()]
        self.assertEqual(tipos, [("commit", True), ("push", None)])
        self.assertEqual(self.git_del_relay()[1]["datos"]["incluye"], [sha])

    def test_commit_de_otra_persona_por_origin_no_es_suyo(self):
        """El push de otra persona llega por fetch: su commit entra en el `incluye`, pero no como commit de esta persona
        (en vivo, M8e: el demonio de B emitía como suyo el commit de A y salía `actividad_ajena`). Horas en UTC."""
        a = self.agente()
        self.vuelta(a)
        otro = os.path.join(self.tmp, "otro")
        subprocess.run(["git", "clone", "-q", os.path.join(self.tmp, "remoto.git"), otro], check=True)
        git(otro, "config", "user.name", "A"); git(otro, "config", "user.email", "a@example.com")
        with open(os.path.join(otro, "a.txt"), "a", encoding="utf-8") as f:
            f.write("de A\n")
        git(otro, "commit", "-qam", "T05 · de A"); git(otro, "push", "-q", "origin", "main")
        sha = git(otro, "rev-parse", "HEAD")
        self.reloj.t += 60                                          # que toque fetch
        self.vuelta(a)
        tipos = [(e["tipo"], e["datos"].get("incluye")) for e in self.git_del_relay()]
        self.assertEqual(tipos, [("push", [sha])])
        # Y un commit propio lleva la hora en UTC con «Z».
        self.commit("T08 · propio", rama="t08")
        self.vuelta(a)
        self.assertTrue(self.git_del_relay()[-1]["ts"].endswith("Z"))

    def otro_clon(self, correo="a@example.com"):
        otro = os.path.join(self.tmp, "otro")
        subprocess.run(["git", "clone", "-q", os.path.join(self.tmp, "remoto.git"), otro], check=True)
        git(otro, "config", "user.name", "A"); git(otro, "config", "user.email", correo)
        return otro

    def commit_en(self, clon, mensaje):
        with open(os.path.join(clon, "a.txt"), "a", encoding="utf-8") as f:
            f.write(mensaje + "\n")
        git(clon, "commit", "-qam", mensaje)
        return git(clon, "rev-parse", "HEAD")

    def commits_emitidos(self):
        return [e["datos"]["sha"] for e in self.git_del_relay() if e["tipo"] == "commit"]

    def test_el_correo_de_git_no_hace_suyo_un_commit(self):
        """Issue #2, hallazgo 2 (ADR-0011): otro clon hace un commit con el user.email de esta persona y lo sube. Antes,
        el demonio lo emitía como suyo por el correo del committer. Ahora solo emite lo que se hizo con `git commit` en
        este clon: entra en el `incluye` del push, pero no como commit. Es también el caso del mismo dueño con dos
        clones: lo emite el demonio del clon donde se hizo, no el otro."""
        a = self.agente()
        self.vuelta(a)
        otro = self.otro_clon(correo="b@example.com")
        sha = self.commit_en(otro, "T05 · con el correo de B")
        git(otro, "push", "-q", "origin", "main")
        self.reloj.t += 60                                          # que toque fetch
        self.vuelta(a)
        self.assertEqual([(e["tipo"], e["datos"].get("incluye")) for e in self.git_del_relay()], [("push", [sha])])
        git(self.repo, "pull", "-q", "--ff-only", "origin", "main")    # traerlo a main tampoco lo hace suyo
        self.vuelta(a)
        self.assertEqual(self.commits_emitidos(), [])

    def test_lo_traido_de_fuera_no_se_emite(self):
        """Issue #2, hallazgo 5: los commits de otra persona que este clon solo ha traído (fetch y checkout de su rama,
        merge local, cherry-pick, rebase) no salen como suyos aunque estén en una rama local fuera de origin/main. Lo
        que se hace aquí encima con `git commit` (también --amend), sí."""
        a = self.agente()
        self.vuelta(a)
        otro = self.otro_clon()
        git(otro, "checkout", "-q", "-b", "feature")
        ajenos = [self.commit_en(otro, "T05 · de A"), self.commit_en(otro, "T05 · más de A")]
        git(otro, "push", "-q", "origin", "feature")
        git(self.repo, "fetch", "-q", "origin")
        git(self.repo, "checkout", "-q", "-b", "feature", "origin/feature")            # la rama de A, en local
        git(self.repo, "checkout", "-q", "-b", "mezcla", "main")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "Merge de feature", "origin/feature")
        git(self.repo, "checkout", "-q", "-b", "elegido", "main")
        git(self.repo, "cherry-pick", ajenos[0])
        git(self.repo, "checkout", "-q", "-b", "propia", "main")
        self.escribe("b.txt", "propio\n")
        git(self.repo, "add", "b.txt"); git(self.repo, "commit", "-qm", "T08 · base propia")
        propio = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "-b", "rebasado", "origin/feature")
        git(self.repo, "rebase", "-q", "propia")                                       # A encima de lo propio
        self.vuelta(a)
        self.assertEqual(self.commits_emitidos(), [propio])
        git(self.repo, "checkout", "-q", "feature")
        encima = self.commit("T05 · lo mío encima")
        git(self.repo, "commit", "-q", "--amend", "-m", "T05 · lo mío encima, corregido")
        corregido = git(self.repo, "rev-parse", "HEAD")
        self.vuelta(a)
        self.assertEqual(self.commits_emitidos(), [propio, corregido])
        self.assertNotIn(encima, self.commits_emitidos())               # el de antes del amend ya no está en la rama
        for e in self.git_del_relay():
            self.assertEqual(e["actor"]["persona"], "persona-b")

    def test_solo_el_id_del_principio_y_sin_merges(self):
        """«Ajuste del plan: T14 …» no es de T14; un merge al traer origin no es un commit de tarea (en vivo, M8e)."""
        a = self.agente()
        self.vuelta(a)
        self.commit("Ajuste del plan: T14 contra EJ-0001", rama="plan")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'plan'", "plan")
        self.vuelta(a)
        commits = [e for e in self.git_del_relay() if e["tipo"] == "commit"]
        self.assertEqual([e.get("tarea") for e in commits], [None])          # una vez (está en main y en plan), sin T14
        self.assertNotIn(git(self.repo, "rev-parse", "HEAD"), [e["datos"]["sha"] for e in commits])   # el merge, no

    def test_rama_de_worker_toma_la_tarea_del_encargo(self):
        a = self.agente()
        self.vuelta(a)
        a.ficheros["s1.jsonl"] = agente_mod.Fichero("x", agente_mod.Normalizador(a.ctx))
        a.ficheros["s1.jsonl"].nz.tarea_de_agente["a1b2"] = "T11"
        self.commit("pintar el desglose", rama="worktree-agent-a1b2")
        self.vuelta(a)
        [e] = self.git_del_relay()
        self.assertEqual((e.get("tarea"), e["actor"]["papel"], e["actor"]["agente"]), ("T11", "worker", "a1b2"))

    def test_commit_en_un_worktree_de_worker(self):
        """ADR-0011: el commit de un worker en su worktree sale como de la persona: el reflog de su rama está en el git
        común, así que cuenta como hecho con `git commit` en este clon."""
        a = self.agente()
        self.vuelta(a)
        wt = os.path.join(self.tmp, "wt")
        git(self.repo, "worktree", "add", "-q", "-b", "worktree-agent-c3d4", wt)
        with open(os.path.join(wt, "w.txt"), "w", encoding="utf-8") as f:
            f.write("del worker\n")
        git(wt, "add", "w.txt"); git(wt, "commit", "-qm", "T11 · del worker")
        self.vuelta(a)
        [e] = self.git_del_relay()
        self.assertEqual((e["datos"]["sha"], e["actor"]["papel"], e["actor"]["agente"]),
                         (git(wt, "rev-parse", "HEAD"), "worker", "c3d4"))

    def test_sin_confirmar_se_reemite_con_el_mismo_id(self):
        a = self.agente()
        self.vuelta(a)
        os.remove(os.path.join(a.dir, "relay.url"))                 # el relay no recibe nada
        self.commit("T08 · sin relay", rama="t08")
        self.vuelta(a)
        self.assertEqual(len(a.cola), 1)
        b = self.agente()                                           # el demonio se reinicia antes de confirmar
        escribe_fichero(os.path.join(a.dir, "relay.url"), self.url + "\n")
        self.vuelta(b)
        self.assertEqual(len(self.git_del_relay()), 1)
        self.vuelta(b)
        self.assertEqual(len(self.git_del_relay()), 1)              # confirmado: no se repite
        self.assertEqual(len(lee_json(os.path.join(a.dir, "git.json"))["vistos"]), 1)

    def test_push_desde_la_terminal_rehace_el_arbol(self):
        """Pendiente de M8g: tras un push desde la terminal, el amarillo seguía hasta el siguiente `arbol` de una sesión.
        Al cambiar origin/main, el demonio emite el `arbol` de la copia principal: sin lo subido, con lo que sigue
        cambiado (un renombrado cuenta por el nombre nuevo). No es actividad de ninguna tarea."""
        a = self.agente()
        self.vuelta(a)
        self.commit("T08 · subido desde la terminal")
        git(self.repo, "push", "-q", "origin", "main")
        self.escribe("b.txt", "sin subir\n")
        git(self.repo, "mv", "a.txt", "c.txt")                      # renombrado sin commit: «R  c.txt\0a.txt»
        self.vuelta(a)
        [e] = [e for e in self.git_del_relay(arbol=True) if e["tipo"] == "arbol"]
        self.assertEqual((e["actor"]["papel"], e["actor"]["worktree"], sorted(e["rutas"]), e["datos"]["base"]),
                         ("demonio", "", ["b.txt", "c.txt"], git(self.repo, "rev-parse", "origin/main")))
        self.vuelta(a)                                              # sin cambios en origin/main: nada nuevo
        self.assertEqual(len([e for e in self.git_del_relay(arbol=True) if e["tipo"] == "arbol"]), 1)
        tareas = [{"id": "T09", "titulo": "Nueve", "dueno": "persona-b", "depende_de": []}]
        issues = {"T09": {"creado_en": "2020-01-01T09:00:00Z", "acciones": []}}
        r = calcular(tareas, issues, self.relay.eventos, PERSONAS, ahora_iso())
        self.assertNotIn("arbol", " ".join(s["que"] for s in r["sin_tarea"]))


if __name__ == "__main__":
    unittest.main()
