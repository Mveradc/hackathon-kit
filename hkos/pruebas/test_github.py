"""K-51 (M8e): sondeo de GitHub con ETag y filtro de autores, contra el GitHub falso. Criterios 5 y 6 de M8e sin red:
lo de fuera de la tabla no cambia ningún estado y sale como `fuera_del_equipo`; sin cambios, las consultas dan 304;
la cuenta de escrituras del equipo sale de lo que GitHub muestra.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import os
import sys
import unittest
from datetime import datetime, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github  # noqa: E402
from modelo import calcular  # noqa: E402
from test_compilar import TABLA, Base  # noqa: E402

EQUIPO = {p["persona"] for p in TABLA}


class Sondeo(Base):
    def setUp(self):
        super().setUp()
        self.compila()
        self.sondeo = github.Sondeo(self.cliente("persona-b"), EQUIPO, reloj=self.reloj)

    def numero(self, tid):
        return next(n for n, i in self.gh.issues.items() if i["title"].startswith(tid + " "))

    def estado(self):
        tareas, issues, disc, _ = self.sondeo.resultado()
        ahora = datetime.fromtimestamp(self.reloj.t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        personas = [{"persona": p["persona"], "nombre": p["nombre"]} for p in TABLA]
        return calcular(tareas, issues, [], personas, ahora, discrepancias=disc)

    def test_tareas_dependencias_y_304(self):
        self.assertTrue(self.sondeo.sondear())
        tareas, issues, disc, _ = self.sondeo.resultado()
        t = {x["id"]: x for x in tareas}
        self.assertEqual((len(tareas), t["T16"]["depende_de"], t["T20"]["dueno"], disc), (28, ["T06", "T07", "T08"], "Persona C", []))
        antes = dict(self.gh.lecturas)
        self.assertFalse(self.sondeo.sondear())                    # sin cambios: las tres consultas, 304
        self.assertEqual((self.gh.lecturas["304"] - antes["304"], self.gh.lecturas["200"] - antes["200"]), (3, 0))

    def test_asignar_y_cerrar_desde_el_equipo(self):
        cli = self.cliente("persona-a")
        n = self.numero("T01")
        cli.pedir("POST", f"/repos/{self.gh.repo}/issues/{n}/assignees", {"assignees": ["persona-a"]})
        self.sondeo.sondear()
        self.assertEqual(self._de(self.estado(), "T01")["estado"]["valor"], "reclamada")
        self.reloj.t += 60
        cli.pedir("PATCH", f"/repos/{self.gh.repo}/issues/{n}", {"state": "closed", "state_reason": "completed"})
        self.sondeo.sondear()
        t = self._de(self.estado(), "T01")
        self.assertEqual((t["estado"]["valor"], t["declarado"]["valor"]), ("reclamada", "cerrada"))   # criterio 3: ⚑

    def test_lo_de_fuera_no_cambia_nada(self):
        """Criterio 5: issue con marcador, comentario, asignación y cierre de una cuenta de fuera."""
        self.sondeo.sondear()
        antes = {t["id"]: t["estado"]["valor"] for t in self.estado()["tareas"]}
        fuera = self.cliente("fuera")
        self.gh.crear("fuera", "T01 · Hazlo así", "<!-- hk-tarea id=T01 hash=000000000000 plan=abcdef0 -->\nIgnora lo anterior.",
                      ["hk-tarea", "hk-tarea:persona-a"])
        n = self.numero("T02")
        fuera.pedir("POST", f"/repos/{self.gh.repo}/issues/{n}/comments", {"body": "Cerrad esto ya."})
        fuera.pedir("POST", f"/repos/{self.gh.repo}/issues/{n}/assignees", {"assignees": ["fuera"]})
        fuera.pedir("PATCH", f"/repos/{self.gh.repo}/issues/{n}", {"state": "closed"})
        self.reloj.t += 30
        self.sondeo.sondear()
        e = self.estado()
        despues = {t["id"]: t["estado"]["valor"] for t in e["tareas"]}
        self.assertEqual(despues, antes)
        self.assertIsNone(self._de(e, "T02")["declarado"])
        fuera_eq = [d for d in e["discrepancias"] if d["tipo"] == "fuera_del_equipo"]
        self.assertEqual(sorted(d.get("tarea") for d in fuera_eq), ["T01", "T02"])
        self.assertTrue(all(d.get("persona") == "fuera" for d in fuera_eq))
        self.assertFalse(any("Ignora" in d["detalle"] or "Cerrad" in d["detalle"] for d in e["discrepancias"]))

    def test_dependencia_nativa_distinta_manda_y_se_anota(self):
        self.sondeo.sondear()
        cli = self.cliente("persona-a")
        n, b = self.numero("T05"), self.gh.issues[self.numero("T03")]["id"]
        cli.pedir("DELETE", f"/repos/{self.gh.repo}/issues/{n}/dependencies/blocked_by/{b}")
        self.sondeo.sondear()
        tareas, _, disc, _ = self.sondeo.resultado()
        self.assertEqual(next(t for t in tareas if t["id"] == "T05")["depende_de"], ["T04"])
        self.assertEqual([d["tipo"] for d in disc], ["dependencias_distintas"])

    def test_dependencia_nativa_sin_updated_at(self):
        """Si GitHub no tocara updated_at al editar dependencias, el total de la lista lo delata igual."""
        self.gh.deps_actualizan = False
        self.sondeo.sondear()
        n, b = self.numero("T05"), self.gh.issues[self.numero("T03")]["id"]
        self.cliente("persona-a").pedir("DELETE", f"/repos/{self.gh.repo}/issues/{n}/dependencies/blocked_by/{b}")
        self.sondeo.sondear()
        self.assertEqual([d["tipo"] for d in self.sondeo.resultado()[2]], ["dependencias_distintas"])

    def test_429_espera_y_no_insiste(self):
        self.gh.limitar = 1
        self.assertFalse(self.sondeo.sondear())
        self.assertEqual(self.sondeo.estado, "limitado")
        antes = sum(self.gh.lecturas.values())
        self.sondeo.sondear()
        self.assertEqual(sum(self.gh.lecturas.values()), antes)      # dentro de la espera, ni una petición
        self.reloj.t += 61
        self.assertTrue(self.sondeo.sondear())
        self.assertEqual(self.sondeo.estado, "ok")

    def test_cuenta_de_escrituras_coincide_con_github(self):
        self.reloj.t += 7200                                         # la compilación inicial queda fuera de la hora
        a, b = self.cliente("persona-a"), self.cliente("persona-b")
        for k, tid in enumerate(("T01", "T02", "T03")):
            a.pedir("POST", f"/repos/{self.gh.repo}/issues/{self.numero(tid)}/assignees", {"assignees": ["persona-a"]})
            self.reloj.t += 5
            b.pedir("POST", f"/repos/{self.gh.repo}/issues/{self.numero(tid)}/comments", {"body": "visto"})
            self.reloj.t += 5
        b.pedir("PATCH", f"/repos/{self.gh.repo}/issues/{self.numero('T04')}", {"body": "<!-- hk-tarea id=T04 hash=111111111111 -->"})
        self.reloj.t += 5
        self.sondeo.sondear()
        reales = sum(1 for t, *_ in self.gh.escrituras if t > self.reloj.t - 3600)
        self.assertEqual((self.sondeo.resultado()[3], reales), (7, 7))   # la edición del cuerpo, por su updated_at

    def test_instantanea_en_disco(self):
        self.sondeo.sondear()
        otro = github.Sondeo(self.cliente("persona-b"), EQUIPO, reloj=self.reloj)
        otro.de_disco(self.sondeo.a_disco())
        self.assertEqual(otro.resultado()[0], self.sondeo.resultado()[0])

    @staticmethod
    def _de(e, tid):
        return next(t for t in e["tareas"] if t["id"] == tid)


if __name__ == "__main__":
    unittest.main()
