"""Tabla de casos del motor de estados (diseno.md §5.2). Un método test_Exx por fila; E45–E49 y E55–E58, sobre la
atribución de modelo.py; E59 y E60, sobre el paso de issues a tareas de github.py. Una prueba más comprueba que la
tabla y estas pruebas tienen los mismos IDs.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import itertools
import os
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
from estados import derivar, iso  # noqa: E402
from github import tareas_de_issues  # noqa: E402
from modelo import atribuir, calcular  # noqa: E402

DISENO = os.path.join(os.path.dirname(HKOS), "docs", "hackathon-os", "diseno.md")
T0 = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
A, B, FUERA = "persona-a", "persona-b", "fuera"
EQUIPO = {A, B}
X, Y, Z, W, C1, C2 = "aaaaaaa", "bbbbbbb", "ccccccc", "ddddddd", "c1c1c1c", "c2c2c2c"
_n = itertools.count()


def ts(m):
    return iso(T0 + timedelta(minutes=m))


def ev(t, tipo, persona=B, tarea="T10", fuente="hook", papel="principal", id=None, rutas=None, **datos):
    e = {"v": 1, "id": id or f"e{next(_n)}", "ts": ts(t), "actor": {"persona": persona, "papel": papel},
         "tipo": tipo, "fuente": fuente}
    if tarea:
        e["tarea"] = tarea
    if rutas:
        e["rutas"] = rutas
    if datos:
        e["datos"] = datos
    return e


# Atajos de la secuencia del orquestador de B.
def enc(t): return ev(t, "encargo.lanzado", papel="orquestador", base="0123abc")
def cre(t, sha): return ev(t, "fusion.creada", papel="orquestador", sha=sha)
def ver(t, v, sha, id=None): return ev(t, "revision.veredicto", papel="revisor", id=id, veredicto=v, sha=sha)
def apr(t, sha): return ev(t, "fusion.aprobada", papel="orquestador", fuente="git", sha=sha)
def des(t, sha): return ev(t, "fusion.descartada", papel="orquestador", sha=sha)
def push(t, *incluye, fuente="git"): return ev(t, "push", tarea=None, fuente=fuente, papel="demonio", incluye=list(incluye))
def commit(t, sha, **mas): return ev(t, "commit", fuente="git", papel="humano", sha=sha, **mas)
def acc(t, accion, por=B, a=None): return dict({"accion": accion, "por": por, "ts": ts(t)}, **({"a": a} if a else {}))
def dep(valor, declarado=None):
    return {"estado": {"valor": valor, "fuente": "git", "observado_en": ts(-5)},
            "declarado": {"valor": declarado, "fuente": "github", "observado_en": ts(-4), "declarado": True} if declarado else None}


def corre(eventos=(), acciones=(), depende_de=(), deps=None, ahora=None, dueno=B):
    marcas = [e["ts"] for e in eventos] + [a["ts"] for a in acciones]
    if ahora is None:
        ahora = (max(marcas) if marcas else ts(0))
        ahora = iso(datetime.fromisoformat(ahora.replace("Z", "+00:00")) + timedelta(minutes=1))
    else:
        ahora = ts(ahora)
    tarea = {"id": "T10", "dueno": dueno, "depende_de": list(depende_de)}
    return derivar(tarea, {"creado_en": ts(-10), "acciones": list(acciones)}, list(eventos), deps or {}, EQUIPO, ahora)


# Secuencias reutilizadas por varias filas.
E22 = lambda: [enc(0), cre(5, X), ver(10, "APROBADO", X), apr(11, X)]
E30 = lambda: [enc(0), cre(5, X), ver(10, "CAMBIOS", X), enc(11), cre(15, Y), ver(20, "CAMBIOS", Y), des(21, Y)]
E39 = lambda: [ev(0, "reclamo", fuente="mcp"), commit(5, C1), push(6, C1)]


class Motor(unittest.TestCase):
    def estado(self, r, valor, fuente=None, t=None):
        self.assertEqual(r["estado"]["valor"], valor, r)
        if fuente:
            self.assertEqual(r["estado"]["fuente"], fuente, r)
        if t is not None:
            self.assertEqual(r["estado"]["observado_en"], ts(t), r)

    def disc(self, r, *tipos):
        self.assertEqual(sorted(d["tipo"] for d in r["discrepancias"]), sorted(tipos), r["discrepancias"])

    # GitHub y dependencias
    def test_E01(self):
        r = corre(depende_de=["T02"], deps={"T02": dep("en_curso")}); self.estado(r, "pendiente", "github"); self.disc(r)
    def test_E02(self): self.estado(corre(), "lista", "derivado")
    def test_E03(self): self.estado(corre(depende_de=["T02"], deps={"T02": dep("publicada")}), "lista", "derivado")
    def test_E04(self):
        r = corre(depende_de=["T02"], deps={"T02": dep("cerrada")}); self.estado(r, "lista", "derivado")
        self.assertEqual(r["cumplidas_por_cierre"], [])
    def test_E05(self): self.estado(corre(depende_de=["T02"], deps={"T02": dep("integrada")}), "pendiente", "github")
    def test_E06(self):
        r = corre(depende_de=["T02"], deps={"T02": dep("en_curso", "cerrada")})
        self.estado(r, "lista", "derivado"); self.assertEqual(r["cumplidas_por_cierre"], ["T02"])
    def test_E07(self):
        r = corre(depende_de=["T99"]); self.estado(r, "pendiente", "github"); self.disc(r, "dependencia_inexistente")
    def test_E08(self): self.estado(corre(acciones=[acc(0, "asignar", B, a=B)]), "reclamada", "github", 0)
    def test_E09(self): self.estado(corre([ev(0, "reclamo", fuente="mcp")]), "reclamada", "mcp", 0)
    def test_E10(self):
        r = corre(acciones=[acc(0, "asignar", FUERA, a=B)]); self.estado(r, "lista", "derivado"); self.disc(r, "fuera_del_equipo")

    # Actividad y parada
    def test_E11(self): self.estado(corre([ev(0, "reclamo", fuente="mcp"), ev(2, "edicion")]), "en_curso", "hook", 2)
    def test_E12(self): self.estado(corre([enc(0)]), "en_curso", "hook", 0)
    def test_E13(self):
        r = corre([ev(0, "edicion", persona=A)]); self.estado(r, "lista", "derivado"); self.disc(r, "actividad_ajena")
    def test_E14(self): self.estado(corre([ev(0, "edicion")], ahora=21), "parada", "derivado", 20)
    def test_E15(self): self.estado(corre([ev(0, "edicion")], ahora=19), "en_curso", "hook", 0)
    def test_E16(self): self.estado(corre([ev(0, "edicion"), ev(30, "edicion")], ahora=31), "en_curso", "hook", 30)
    def test_E17(self): self.estado(corre([ev(0, "edicion"), ev(20, "latido", papel="worker")], ahora=30), "en_curso", "hook", 20)
    def test_E18(self): self.estado(corre([ev(0, "reclamo", fuente="mcp")], ahora=30), "reclamada", "mcp")
    def test_E19(self): self.estado(corre([enc(0), cre(5, X)], ahora=40), "en_revision", "hook")

    # Revisión y fusión
    def test_E20(self): self.estado(corre([enc(0), cre(5, X)]), "en_revision", "hook", 5)
    def test_E21(self): self.estado(corre([enc(0), cre(5, X), ver(10, "APROBADO", X)]), "en_revision", "hook", 5)
    def test_E22(self):
        r = corre(E22()); self.estado(r, "integrada", "git", 11); self.assertEqual(r["fusion"], X); self.disc(r)
    def test_E23(self):
        r = corre([enc(0), cre(5, X), apr(11, X)]); self.estado(r, "integrada", "git"); self.disc(r, "hook_frente_a_git")
    def test_E24(self):
        r = corre([cre(5, X), ver(10, "APROBADO", Y)]); self.estado(r, "en_revision", "hook"); self.disc(r, "veredicto_sha")
    def test_E25(self): self.estado(corre([cre(5, X), des(6, X)]), "en_curso", "hook", 6)
    def test_E26(self): self.estado(corre(E22() + [enc(20)]), "en_curso", "hook", 20)

    # CAMBIOS y no_cerrada
    def test_E27(self): self.estado(corre([enc(0), cre(5, X), ver(10, "CAMBIOS", X)]), "en_curso", "hook", 10)
    def test_E28(self): self.estado(corre([enc(0), cre(5, X), ver(10, "CAMBIOS", X), enc(11), cre(15, Y)]), "en_revision", "hook")
    def test_E29(self):
        r = corre([enc(0), cre(5, X), ver(10, "CAMBIOS", X), enc(11), cre(15, Y), ver(20, "CAMBIOS", Y)])
        self.estado(r, "no_cerrada", "hook", 20)
    def test_E30(self): self.estado(corre(E30()), "no_cerrada", "hook", 20)
    def test_E31(self): self.estado(corre(E30() + [enc(30), cre(35, Z)]), "en_revision", "hook", 35)
    def test_E32(self): self.estado(corre(E30() + [enc(30), cre(35, Z), ver(40, "CAMBIOS", Z)]), "en_curso", "hook", 40)
    def test_E33(self):
        r = corre([cre(5, X), ver(10, "CAMBIOS", X), cre(15, Y), ver(20, "APROBADO", Y), apr(21, Y),
                   enc(30), cre(35, Z), ver(40, "CAMBIOS", Z)])
        self.estado(r, "en_curso", "hook", 40)
    def test_E34(self):
        v = ver(10, "CAMBIOS", X, id="repetido")
        self.estado(corre([cre(5, X), v, dict(v)]), "en_curso", "hook")

    # Publicación y cierre
    def test_E35(self): self.estado(corre(E22() + [push(20, X)]), "publicada", "git", 20)
    def test_E36(self): self.estado(corre(E22() + [push(20, X, fuente="hook")]), "integrada", "git")
    def test_E37(self): self.estado(corre(E22() + [push(20, W)]), "integrada", "git")
    def test_E38(self):
        r = corre([cre(5, X), push(20, X)]); self.estado(r, "publicada", "git"); self.disc(r, "hook_frente_a_git")
    def test_E39(self): self.estado(corre(E39()), "publicada", "git", 6)
    def test_E40(self): self.estado(corre(E39() + [commit(10, C2)]), "en_curso", "git", 10)
    def test_E41(self): self.estado(corre(E22() + [push(20, X)], [acc(25, "cerrar")]), "cerrada", "github", 25)
    def test_E42(self):
        r = corre([ev(0, "reclamo", fuente="mcp"), ev(2, "edicion")], [acc(5, "cerrar")])
        self.estado(r, "en_curso", "hook"); self.assertEqual(r["declarado"]["valor"], "cerrada"); self.assertTrue(r["declarado"]["declarado"])
    def test_E43(self):
        r = corre([ev(0, "reclamo", fuente="mcp"), ev(2, "edicion")], [acc(5, "cerrar"), acc(6, "reabrir")])
        self.estado(r, "en_curso", "hook"); self.assertIsNone(r["declarado"])
    def test_E44(self):
        r = corre(E22() + [push(20, X)], [acc(25, "cerrar", FUERA)]); self.estado(r, "publicada", "git"); self.disc(r, "fuera_del_equipo")
    def test_E50(self):
        r = corre(depende_de=["T02"], deps={"T02": dep("lista", "cerrada")})
        self.estado(r, "lista", "derivado"); self.assertEqual(r["cumplidas_por_cierre"], ["T02"])
    def test_E51(self): self.estado(corre(E22() + [push(20, X), commit(25, X)]), "publicada", "git", 20)
    def test_E52(self): self.estado(corre(E39() + [commit(10, C2, alcanzable=True)]), "publicada", "git", 6)
    # Dueño sin GitHub («C», que no está en EQUIPO): el ID manda sobre quién lo escribe (M8e, regla 1).
    def test_E53(self):
        r = corre([commit(0, C1, persona=A)], dueno="C"); self.estado(r, "en_curso", "git", 0); self.assertEqual(r["discrepancias"], [])
    def test_E54(self): self.estado(corre([commit(0, C1, persona=A), push(1, C1)], dueno="C"), "publicada", "git", 1)
    def test_E13_sigue_igual_con_dueno_de_github(self):
        self.disc(corre([ev(0, "edicion", persona=A)]), "actividad_ajena")


class Atribucion(unittest.TestCase):
    """E45–E49: el paso previo de modelo.py, con dos tareas de B (T10, T11)."""
    TAREAS = [{"id": "T10", "titulo": "Diez", "dueno": B, "depende_de": []},
              {"id": "T11", "titulo": "Once", "dueno": B, "depende_de": []}]
    PERSONAS = [{"persona": A, "nombre": "A"}, {"persona": B, "nombre": "B"}]

    def issues(self, **acciones):
        return {t["id"]: {"creado_en": ts(-10), "acciones": acciones.get(t["id"], [])} for t in self.TAREAS}

    def calcula(self, eventos, ahora, **acciones):
        e = calcular(self.TAREAS, self.issues(**acciones), eventos, self.PERSONAS, ts(ahora))
        return {t["id"]: t["estado"] for t in e["tareas"]}, e

    def test_E45(self):
        estados, _ = self.calcula([ev(0, "reclamo", fuente="mcp"), ev(2, "edicion", tarea=None, rutas=["a.py"])], 3)
        self.assertEqual(estados["T10"]["valor"], "en_curso"); self.assertEqual(estados["T10"]["fuente"], "hook")

    def test_E46(self):
        estados, e = self.calcula([ev(0, "reclamo", fuente="mcp"), ev(0, "reclamo", tarea="T11", fuente="mcp"),
                                   ev(2, "edicion", tarea=None, rutas=["a.py"])], 3)
        self.assertEqual((estados["T10"]["valor"], estados["T11"]["valor"]), ("reclamada", "reclamada"))
        self.assertEqual([d["tipo"] for d in e["discrepancias"]], ["atribucion_ambigua"])

    def test_E47(self):
        estados, e = self.calcula([ev(2, "edicion", tarea=None, rutas=["a.py"])], 3)
        self.assertEqual(estados["T10"]["valor"], "lista")
        self.assertEqual([(s["persona"], s["que"]) for s in e["sin_tarea"]], [(B, "edicion: a.py")])

    def test_E48(self):
        estados, _ = self.calcula([ev(0, "edicion"), ev(15, "arbol", tarea=None, rutas=["a.py"])], 30)
        self.assertEqual(estados["T10"], {"valor": "en_curso", "fuente": "hook", "observado_en": ts(15)})

    def test_E49(self):
        eventos = [ev(0, "reclamo", fuente="mcp"), ev(0, "commit", tarea="T11", fuente="git", papel="humano", sha=C1),
                   push(1, C1), ev(2, "edicion", tarea=None, rutas=["a.py"])]
        estados, _ = self.calcula(eventos, 3)
        self.assertEqual((estados["T10"]["valor"], estados["T11"]["valor"]), ("en_curso", "publicada"))

    # M8e: un commit sin ID pasa por la regla 9 como una edición.
    def test_E55(self):
        estados, _ = self.calcula([ev(0, "reclamo", fuente="mcp"), commit(2, C1, tarea=None, rama="ficha")], 3)
        self.assertEqual((estados["T10"]["valor"], estados["T10"]["fuente"]), ("en_curso", "git"))

    def test_E56(self):
        estados, e = self.calcula([ev(0, "reclamo", fuente="mcp"), ev(0, "reclamo", tarea="T11", fuente="mcp"),
                                   commit(2, C1, tarea=None, rama="ficha")], 3)
        self.assertEqual((estados["T10"]["valor"], estados["T11"]["valor"]), ("reclamada", "reclamada"))
        self.assertEqual([d["tipo"] for d in e["discrepancias"]], ["atribucion_ambigua"])

    def test_E57(self):
        estados, e = self.calcula([commit(2, C1, tarea=None, rama="experimento")], 3)
        self.assertEqual(estados["T10"]["valor"], "lista")
        self.assertEqual([(s["persona"], s["que"]) for s in e["sin_tarea"]], [(B, "commit: experimento")])

    def test_E58(self):
        estados, e = self.calcula([commit(2, C1, rama="worktree-agent-x")], 3)
        self.assertEqual((estados["T10"]["valor"], estados["T10"]["fuente"]), ("en_curso", "git"))
        self.assertEqual(e["sin_tarea"], [])

    def test_atribuir_no_toca_eventos_con_tarea(self):
        e = [ev(0, "edicion", tarea="T11")]
        salida, sin_tarea, disc = atribuir(self.TAREAS, self.issues(), e, EQUIPO)
        self.assertEqual(salida[0]["tarea"], "T11"); self.assertEqual((sin_tarea, disc), ([], []))


def issue(numero, tid, autor=B, estado="open", razon=None, depende=(), dueno=B, creado=-10):
    cuerpo = (f"<!-- hk-tarea id={tid} hash=0123456789ab plan=abcdef0 -->\n**Dueño:** @{dueno} (B)\n"
              f"**Bloque:** Ficha · **Hasta:** Vie 23:00\n**Cómo se comprueba:** algo\n")
    if depende:
        cuerpo += f"Depende de: {', '.join(depende)}\n"
    return {"number": numero, "title": f"{tid} · Tarea {tid}", "body": cuerpo, "user": {"login": autor}, "state": estado,
            "state_reason": razon, "labels": [{"name": "hk-tarea"}, {"name": f"hk-tarea:{dueno}"}], "created_at": ts(creado)}


class Issues(unittest.TestCase):
    """E59 y E60: de issues hk-tarea a tareas (github.tareas_de_issues) y después el modelo."""
    PERSONAS = [{"persona": A, "nombre": "A"}, {"persona": B, "nombre": "B"}]

    def calcula(self, issues):
        tareas, motor, _, disc = tareas_de_issues(issues, EQUIPO)
        return calcular(tareas, motor, [], self.PERSONAS, ts(1), discrepancias=disc)

    def test_E59(self):
        e = self.calcula([issue(30, "T10", autor=FUERA)])
        self.assertEqual(e["tareas"], [])
        self.assertEqual([(d["tipo"], d.get("persona")) for d in e["discrepancias"]], [("fuera_del_equipo", FUERA)])

    def test_E60(self):
        e = self.calcula([issue(30, "T02", estado="closed", razon="not_planned"), issue(31, "T10", depende=["T02"])])
        self.assertEqual([t["id"] for t in e["tareas"]], ["T10"])
        self.assertEqual((e["tareas"][0]["estado"]["valor"], e["tareas"][0]["estado"]["fuente"]), ("pendiente", "github"))
        self.assertEqual([d["tipo"] for d in e["discrepancias"]], ["dependencia_inexistente"])

    def test_issue_del_equipo_y_duplicado(self):
        tareas, motor, numeros, disc = tareas_de_issues([issue(31, "T10"), issue(30, "T10", autor=A)], EQUIPO)
        self.assertEqual((len(tareas), motor["T10"]["numero"], tareas[0]["dueno"], tareas[0]["bloque"]), (1, 30, B, "Ficha"))
        self.assertEqual([d["tipo"] for d in disc], ["issue_duplicado"])

    def test_dueno_sin_github(self):
        i = issue(30, "T21")
        i["labels"] = [{"name": "hk-tarea"}]
        i["body"] = i["body"].replace("**Dueño:** @persona-b (B)", "**Dueño:** C (sin GitHub)")
        tareas, *_ = tareas_de_issues([i], EQUIPO)
        self.assertEqual(tareas[0]["dueno"], "C")


class Tabla(unittest.TestCase):
    def test_mismos_ids_en_la_tabla_y_en_las_pruebas(self):
        with open(DISENO, encoding="utf-8") as f:
            tabla = set(re.findall(r"^\| (E\d\d) \|", f.read(), re.M))
        pruebas = {n[5:] for c in (Motor, Atribucion, Issues) for n in dir(c) if re.fullmatch(r"test_E\d\d", n)}
        self.assertEqual(tabla, pruebas)


if __name__ == "__main__":
    unittest.main()
