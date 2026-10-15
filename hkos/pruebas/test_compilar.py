"""K-50 (M8e): hk-os compilar contra el GitHub falso. Criterio 1 de M8e sin red: compilar el plan del 03 crea un
issue por tarea con dueño y dependencias; compilar otra vez no escribe nada; tras un ajuste, solo cambian las filas
cambiadas y la tarea quitada se cierra con comentario. Además, el tope de R-30 en una recompilación.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import os
import sys
import unittest

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(HKOS)
sys.path.insert(0, HKOS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compilar  # noqa: E402
import github  # noqa: E402
from github_falso import GitHubFalso  # noqa: E402
from red import leer_texto  # noqa: E402

PLAN = os.path.join(KIT, "skills", "hack-plan", "examples", "03-xray-embat-real-plan.md")
TABLA = [{"persona": "persona-a", "nombre": "Persona A"}, {"persona": "persona-b", "nombre": "Persona B"}]


class Reloj:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


class Base(unittest.TestCase):
    def setUp(self):
        self.reloj = Reloj()
        self.gh = GitHubFalso(reloj=self.reloj)
        self.addCleanup(self.gh.cerrar)
        self.texto = leer_texto(PLAN)

    def cliente(self, usuario="persona-a"):
        return github.Cliente(self.gh.repo, f"tok-{usuario}", base=self.gh.base, reloj=self.reloj)

    def compila(self, texto=None, usuario="persona-a", plan_sha="abc1234"):
        tareas = compilar.leer_plan(texto or self.texto, TABLA)
        salida = []
        c = compilar.Compilador(self.cliente(usuario), TABLA, plan_sha, reloj=self.reloj, dormir=self.reloj.dormir,
                                salida=salida.append)
        return c.compilar(tareas), salida

    def escrituras(self):
        return len(self.gh.escrituras)


class Compilar(Base):
    def test_inicial_crea_un_issue_por_tarea_con_dueno_y_dependencias(self):
        t0 = self.reloj.t
        r, salida = self.compila()
        self.assertEqual((len(r["creadas"]), r["dependencias"], r["pendientes"]), (28, 9, 0))
        self.assertIn("exenta", salida[0])
        self.assertEqual(self.escrituras(), 3 + 28 + 9)                 # 3 etiquetas
        self.assertGreaterEqual(self.reloj.t - t0, self.escrituras() - 1)  # ≤ 1 escritura/s
        por_id = {github.MARCADOR.search(i["body"]).group(1): i for i in self.gh.issues.values()}
        t05, t20 = por_id["T05"], por_id["T20"]
        self.assertEqual([l["name"] for l in t05["labels"]], ["hk-tarea", "hk-tarea:persona-a"])
        self.assertIn("Depende de: T03, T04", t05["body"])
        self.assertEqual(sorted(self.gh.issues[n]["title"][:3] for n in t05["_bloqueado_por"]), ["T03", "T04"])
        self.assertEqual([l["name"] for l in t20["labels"]], ["hk-tarea"])  # Persona C, sin GitHub
        self.assertIn("**Dueño:** Persona C (sin GitHub)", t20["body"])
        self.assertTrue(t05["title"].startswith("T05 · "))

    def test_recompilar_sin_cambios_no_escribe(self):
        self.compila()
        n = self.escrituras()
        r, salida = self.compila()
        self.assertEqual((self.escrituras(), len(r["sin_cambios"]), r["escrituras"]), (n, 28, 0))
        self.assertIn("Escrituras del equipo en la última hora", salida[0])

    def test_ajuste_solo_toca_lo_cambiado(self):
        self.compila()
        n = self.escrituras()
        texto = self.texto.replace("| T28 |", "| T29 |", 1)              # T28 sale del plan y entra T29
        texto = texto.replace("- T28 espera a T10", "- T29 espera a T03")
        fila = next(l for l in texto.splitlines() if l.startswith("| T03 |"))
        texto = texto.replace(fila, fila[:-2] + " (revisado) |")
        self.reloj.t += 7200                                           # fuera de la hora de la compilación inicial
        r, _ = self.compila(texto)
        self.assertEqual((r["creadas"], r["editadas"], r["cerradas"], r["dependencias"]), (["T29"], ["T03"], ["T28"], 1))
        self.assertEqual(self.escrituras() - n, 5)                      # crear, editar, dependencia, comentar y cerrar
        t28 = next(i for i in self.gh.issues.values() if i["title"].startswith("T28"))
        self.assertEqual((t28["state"], t28["state_reason"]), ("closed", "not_planned"))
        self.assertIn("Quitada del plan", self.gh.comentarios[-1]["body"])
        # Si vuelve al plan, se reabre.
        r, _ = self.compila()
        self.assertIn("T28", r["reabiertas"])

    def test_tope_del_equipo_en_una_recompilacion(self):
        self.compila()
        self.reloj.t += 7200
        cli = self.cliente("persona-b")
        numeros = sorted(self.gh.issues)
        for k in range(58):                                             # 58 escrituras del equipo en esta hora
            cli.pedir("POST", f"/repos/{self.gh.repo}/issues/{numeros[k % len(numeros)]}/assignees",
                      {"assignees": ["persona-b"]})
            self.reloj.t += 1
        texto = self.texto
        for tid in ("T01", "T02", "T03"):
            fila = next(l for l in texto.splitlines() if l.startswith(f"| {tid} |"))
            texto = texto.replace(fila, fila[:-2] + " (v2) |")
        r, salida = self.compila(texto)
        self.assertIn("58 de 60", salida[0])
        self.assertEqual((r["escrituras"], r["pendientes"], len(r["editadas"])), (2, 1, 2))
        self.reloj.t += 3700                                            # pasa la hora: la siguiente sigue donde se quedó
        r, _ = self.compila(texto)
        self.assertEqual((r["editadas"], r["pendientes"]), (["T03"], 0))

    def test_issue_de_fuera_con_marcador_no_cuenta(self):
        self.gh.crear("fuera", "T01 · falso", "<!-- hk-tarea id=T01 hash=000000000000 plan=abcdef0 -->", ["hk-tarea"])
        r, _ = self.compila()
        self.assertIn("T01", r["creadas"])

    def test_plan_mal_formado_no_escribe(self):
        with self.assertRaises(compilar.PlanMalo):
            compilar.leer_plan(self.texto.replace("| T02 |", "| T01 |", 1), TABLA)
        with self.assertRaises(compilar.PlanMalo):
            compilar.leer_plan("# Plan\n## Por persona\n", TABLA)

    def test_huella_estable_y_sensible(self):
        t = compilar.leer_plan(self.texto, TABLA)[0]
        h = compilar.huella(t)
        self.assertEqual(h, compilar.huella(dict(t)))
        self.assertNotEqual(h, compilar.huella(dict(t, depende_de=["T09"])))
        self.assertEqual(len(h), 12)


class Lector(unittest.TestCase):
    def test_formatos_de_dependencias(self):
        texto = ("## Por persona\n### A · x\n| ID | Hasta | Bloque | Tarea | Cómo |\n|---|---|---|---|---|\n"
                 "| T01 | Vie | B1 | Uno | ok |\n| T02 | | | Dos | ok |\n| T03 | | | Tres | ok |\n| T04 | Sáb | B2 | Cuatro | ok |\n"
                 "## Quién espera a quién\n- T04 espera a T01–T03: algo\n- **T03 espera a T01**: algo\n- T02 espera a T01 y T03.\n")
        t = {x["id"]: x for x in compilar.leer_plan(texto, [{"persona": "pa", "nombre": "A"}])}
        self.assertEqual(t["T04"]["depende_de"], ["T01", "T02", "T03"])
        self.assertEqual(t["T03"]["depende_de"], ["T01"])
        self.assertEqual(t["T02"]["depende_de"], ["T01", "T03"])
        self.assertEqual((t["T03"]["hasta"], t["T03"]["bloque"], t["T03"]["dueno"]), ("Vie", "B1", "pa"))


if __name__ == "__main__":
    unittest.main()
