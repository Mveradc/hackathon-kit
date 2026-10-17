"""M9a, K-92: servicios.md → `servicios` de estado.json (servicios.py, ADR-0011, api.md §10). Tabla de casos.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import os
import sys
import unittest

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import servicios  # noqa: E402
from esquema import Esquema  # noqa: E402

T = "2026-11-25T18:00:00.000000Z"
T2 = "2026-11-25T18:05:00.000000Z"
AUTORIDAD = """# Autoridad
## Por dueño
### Ana (@ana) · `api/`, `web/`
| Tema | Nivel | Ejemplos |
|---|---|---|
### Luis (@luis) · `motor/`
| Tema | Nivel | Ejemplos |
|---|---|---|
"""
CONTRATOS = """# Contratos
## web → api
Vive en: api/esquema.py
## motor → web
Vive en: motor/salida.py
"""
SHA = {"s1": None, "a1": "ana", "a2": "ana", "l1": "luis", "l2": "luis", "w1": "ana"}   # s1: sin evento


def md(servicios=(), conexiones=(), prop_s=(), prop_c=(), fuera="docs/, README.md"):
    partes = ["# Servicios", f"Fuera de servicios: {fuera}", "", "## Servicios",
              "| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |", "|---|---|---|---|---|---|"]
    partes += [f"| {' | '.join(f)} |" for f in servicios]
    partes += ["", "## Conexiones", "| De | A | Contrato | Prueba |", "|---|---|---|---|"]
    partes += [f"| {' | '.join(f)} |" for f in conexiones]
    if prop_s:
        partes += ["", "## Propuestas de servicios",
                   "| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño | Autor | Hora |", "|---|---|---|---|---|---|---|---|"]
        partes += [f"| {' | '.join(f)} |" for f in prop_s]
    if prop_c:
        partes += ["", "## Propuestas de conexiones", "| De | A | Contrato | Prueba | Autor | Hora |",
                   "|---|---|---|---|---|---|"]
        partes += [f"| {' | '.join(f)} |" for f in prop_c]
    return "\n".join(partes) + "\n"


API = ("api", "api/", "8000", "`uv run uvicorn api.main:app`", "/salud", "@ana")
WEB = ("web", "web/", "5173", "`npm run dev`", "—", "@ana")
MOTOR = ("motor", "motor/", "—", "—", "—", "@luis")
WEB_API = ("web", "api", "web → api", "`uv run pytest tests/test_web_api.py`")
MOTOR_WEB = ("motor", "web", "motor → web", "`uv run pytest tests/test_motor_web.py`")
BASE = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB])


def historia(*pasos):
    """[(sha, texto)] → versiones en orden, cada una con el texto de su padre (la anterior)."""
    versiones, anterior = [], None
    for sha, texto in pasos:
        versiones.append({"sha": sha, "textos_padres": [anterior], "texto": texto})
        anterior = texto
    return versiones


def calc(texto, versiones, rutas=(), comprobados=None, pruebas=None):
    return servicios.calcular(texto, versiones, SHA, AUTORIDAD, CONTRATOS, rutas, comprobados or {}, pruebas or {},
                              T, T)


def de(s, nombre):
    return next(x for x in s["lista"] if x["nombre"] == nombre)


def con(s, de_):
    return next(x for x in s["conexiones"] if x["de"] == de_)


def tipos(s):
    return sorted(d["tipo"] for d in s["desajustes"])


class Leer(unittest.TestCase):
    def test_tablas_fuera_y_claves(self):
        t = md([API], [WEB_API], prop_s=[MOTOR + ("@luis", "2026-11-25 18:10")],
               prop_c=[MOTOR_WEB + ("@luis", "2026-11-25 18:12")])
        l = servicios.leer(t)
        self.assertEqual(l["errores"], [])
        self.assertEqual(l["fuera"], ["docs/", "README.md"])
        self.assertEqual([f["tabla"] for f in l["filas"]], [servicios.SERVICIOS, servicios.CONEXIONES,
                                                            servicios.PROP_SERVICIOS, servicios.PROP_CONEXIONES])
        api, prop = l["filas"][0], l["filas"][2]
        self.assertEqual(api["campos"]["arranque"], "uv run uvicorn api.main:app")   # sin comillas invertidas
        self.assertEqual(api["campos"]["dueno"], "@ana")
        # una propuesta tiene la clave de la fila que propone (sin Autor ni Hora)
        self.assertEqual(prop["clave"], servicios.clave("servicio", servicios.leer(md([MOTOR]))["filas"][0]["campos"]))
        self.assertEqual((prop["autor"], prop["hora"]), ("@luis", "2026-11-25 18:10"))

    def test_mal_formado(self):
        t = md([API, ("api", "otra/", "1", "—", "—", "@ana"), ("roto", "x/")])
        errores = [d for _, d in servicios.leer(t)["errores"]]
        self.assertTrue(any("2 celdas en vez de 6" in d for d in errores))
        self.assertTrue(any("«api» repetido" in d for d in errores))
        t2 = BASE.replace("| Nombre | Carpeta |", "| Nom | Carpeta |")
        self.assertTrue(any("cabecera" in d for _, d in servicios.leer(t2)["errores"]))
        s = calc(t, historia(("s1", t)))
        self.assertEqual(s["fichero"]["valor"], "mal formado")
        self.assertIn("formato_invalido", tipos(s))

    def test_barra_escapada_y_bom(self):
        t = md([API], [("web", "api", "web → api", r"`pytest -q \| tee x`")])
        self.assertEqual(servicios.leer(t)["filas"][1]["campos"]["prueba"], "pytest -q | tee x")
        self.assertEqual(servicios.decodificar("\ufeff# S".encode("utf-8")), "# S")
        self.assertEqual(servicios.decodificar("# S".encode("utf-16")), "# S")


class Confirmacion(unittest.TestCase):
    def test_filas_iniciales_de_scaffold(self):
        s = calc(BASE, historia(("s1", BASE)))
        self.assertEqual(de(s, "api")["confirmacion"]["valor"], "confirmada")
        self.assertTrue(de(s, "api")["confirmacion"]["de_scaffold"])
        self.assertEqual(con(s, "motor")["confirmacion"]["valor"], "confirmada")
        self.assertEqual(s["desajustes"], [])

    def test_fila_nueva_del_dueno(self):
        t = md([API, WEB, MOTOR, ("cache", "api/cache/", "6379", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        s = calc(t, historia(("s1", BASE), ("a1", t)))
        c = de(s, "cache")["confirmacion"]
        self.assertEqual((c["valor"], c["por"], c["de_scaffold"]), ("confirmada", ["ana"], False))

    def test_cambiada_por_otra_persona(self):
        t = md([API[:2] + ("9000",) + API[3:], WEB, MOTOR], [WEB_API, MOTOR_WEB])
        s = calc(t, historia(("s1", BASE), ("l1", t)))
        c = de(s, "api")["confirmacion"]
        self.assertEqual((c["valor"], c["por"], c["faltan"]), ("sin_confirmar", ["luis"], ["ana"]))

    def test_comando_de_prueba_cambiado(self):
        nueva = MOTOR_WEB[:3] + ("`uv run pytest -x`",)
        t = md([API, WEB, MOTOR], [WEB_API, nueva])
        s = calc(t, historia(("s1", BASE), ("a1", t)))        # ana es un extremo; falta luis
        c = con(s, "motor")["confirmacion"]
        self.assertEqual((c["valor"], c["faltan"]), ("sin_confirmar", ["luis"]))
        t3 = md([API, WEB, MOTOR], [WEB_API, nueva]) + "\n"   # luis la vuelve a añadir tal cual: no es un añadido
        s3 = calc(t3, historia(("s1", BASE), ("a1", t), ("l1", t3)))
        self.assertEqual(con(s3, "motor")["confirmacion"]["valor"], "sin_confirmar")

    def test_sha_desconocido_nunca_confirma(self):
        t = md([API, WEB, MOTOR, ("cache", "api/cache/", "—", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        s = calc(t, historia(("s1", BASE), ("rebase-1", t)))   # mismo contenido que un commit de ana, sha reescrito
        c = de(s, "cache")["confirmacion"]
        self.assertEqual((c["valor"], c["por"], c["faltan"]), ("sin_confirmar", [], ["ana"]))

    def test_dueno_distinto_de_autoridad(self):
        t = md([API[:5] + ("@luis",), WEB, MOTOR], [WEB_API, MOTOR_WEB])
        s = calc(t, historia(("s1", BASE), ("l1", t)))        # luis se pone de dueño de api/: no vale
        self.assertEqual(de(s, "api")["confirmacion"]["valor"], "sin_confirmar")
        self.assertEqual(de(s, "api")["dueno_autoridad"], "ana")
        self.assertIn("dueno_distinto", tipos(s))
        sin = md([("suelto", "otro/", "—", "—", "—", "@ana")], [])
        s2 = calc(sin, historia(("s1", sin)))
        self.assertEqual(de(s2, "suelto")["confirmacion"]["valor"], "sin_confirmar")
        self.assertIn("dueno_distinto", tipos(s2))

    def test_dueno_sin_valor_manda_autoridad(self):
        t = md([API[:5] + ("—",), WEB, MOTOR], [WEB_API, MOTOR_WEB])   # /hack-scaffold antes del reparto
        s = calc(t, historia(("s1", t)))
        self.assertEqual((de(s, "api")["dueno"], de(s, "api")["dueno_autoridad"]), (None, "ana"))
        self.assertEqual(de(s, "api")["confirmacion"]["valor"], "confirmada")
        self.assertEqual(s["desajustes"], [])

    def test_sin_dueno_antes_del_reparto(self):
        t = md([("suelto", "otro/", "—", "—", "—", "—")], [])
        for versiones, valor in ((historia(("s1", t)), "confirmada"),                       # de /hack-scaffold
                                 (historia(("s1", md([], [])), ("a1", t)), "sin_confirmar")):  # añadida después
            s = servicios.calcular(t, versiones, SHA, "", CONTRATOS, (), {}, {}, T)        # sin autoridad.md
            self.assertEqual((de(s, "suelto")["dueno_autoridad"], de(s, "suelto")["confirmacion"]["valor"]),
                             (None, valor))
            self.assertEqual(s["desajustes"], [])

    def test_sin_dueno_con_el_reparto_hecho(self):
        t = md([("suelto", "otro/", "—", "—", "—", "—")], [])
        for versiones in (historia(("s1", t)), historia(("s1", md([], [])), ("a1", t))):
            s = calc(t, versiones)                                                          # AUTORIDAD sin otro/
            self.assertEqual(de(s, "suelto")["confirmacion"]["valor"], "sin_confirmar")
            self.assertEqual(tipos(s), ["dueno_distinto"])

    def test_propuesta_que_su_dueno_pasa_a_su_tabla(self):
        cache = ("cache", "api/cache/", "6379", "—", "—", "@ana")
        v2 = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB], prop_s=[cache + ("@luis", "2026-11-25 18:10")])
        s2 = calc(v2, historia(("s1", BASE), ("l1", v2)))
        self.assertNotIn("cache", [x["nombre"] for x in s2["lista"]])
        p = s2["propuestas"][0]
        self.assertEqual((p["tipo"], p["autor_git"], p["autor_declarado"]), ("servicio", "luis", "@luis"))
        v3 = md([API, WEB, MOTOR, cache], [WEB_API, MOTOR_WEB])
        s3 = calc(v3, historia(("s1", BASE), ("l1", v2), ("a1", v3)))
        c = de(s3, "cache")["confirmacion"]
        self.assertEqual((c["valor"], c["por"]), ("confirmada", ["ana", "luis"]))

    def test_conexion_necesita_a_los_dos_duenos(self):
        motor_api = ("motor", "api", "web → api", "`uv run pytest tests/test_motor_api.py`")
        v2 = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB], prop_c=[motor_api + ("@luis", "2026-11-25 18:12")])
        v3 = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB, motor_api])
        s = calc(v3, historia(("s1", BASE), ("l1", v2), ("a1", v3)))
        self.assertEqual(s["conexiones"][2]["confirmacion"]["valor"], "confirmada")
        solo_ana = calc(v3, historia(("s1", BASE), ("a1", v3)))
        c = solo_ana["conexiones"][2]["confirmacion"]
        self.assertEqual((c["valor"], c["faltan"]), ("sin_confirmar", ["luis"]))

    def test_fila_anadida_por_un_worker_de_su_dueno(self):
        eventos = [{"tipo": "commit", "actor": {"persona": "ana", "papel": "worker", "agente": "a1b2"},
                    "datos": {"sha": "w1sha", "rama": "worktree-agent-a1b2", "alcanzable": False}},
                   {"tipo": "edicion", "actor": {"persona": "luis", "papel": "principal"}, "datos": {"sha": "x"}}]
        mapa = servicios.personas_de_commits(eventos)
        self.assertEqual(mapa, {"w1sha": "ana"})
        t = md([API, WEB, MOTOR, ("cache", "api/cache/", "—", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        s = servicios.calcular(t, historia(("s1", BASE), ("w1sha", t)), mapa, AUTORIDAD, CONTRATOS, (), {}, {}, T)
        self.assertEqual(de(s, "cache")["confirmacion"]["valor"], "confirmada")

    def test_fila_de_una_resolucion_de_merge_no_confirma(self):
        a = md([API, WEB, MOTOR, ("cache", "api/cache/", "1", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        b = md([API, WEB, MOTOR, ("cache", "api/cache/", "2", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        m = md([API, WEB, MOTOR, ("cache", "api/cache/", "3", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        versiones = historia(("s1", BASE), ("a1", a)) + [{"sha": "a2", "textos_padres": [BASE], "texto": b},
                                                       {"sha": "merge", "textos_padres": [a, b], "texto": m}]
        self.assertEqual(de(calc(m, versiones), "cache")["confirmacion"]["valor"], "sin_confirmar")


class Desajustes(unittest.TestCase):
    def test_salud_que_no_es_una_ruta(self):
        for salud in ("http://x/salud", "//host/salud", "/../salud", "salud"):
            t = md([API[:4] + (salud,) + API[5:], WEB, MOTOR], [WEB_API, MOTOR_WEB])
            comprobado = {"valor": {"escucha": True, "salud": None}, "fuente": "demonio", "observado_en": T2}
            s = calc(t, historia(("s1", t)), comprobados={servicios.leer(t)["filas"][0]["clave"]: {"ana": comprobado}})
            self.assertEqual(tipos(s), ["formato_invalido"], salud)   # ni salud_falla: no se consulta

    def test_puerto_salud_prueba_y_contrato(self):
        t = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB, ("web", "motor", "web → motor", "—")])
        filas = servicios.leer(t)["filas"]
        k_api, k_web = filas[0]["clave"], filas[1]["clave"]
        comprobados = {k_api: {"ana": {"valor": {"escucha": True, "salud": 500}, "fuente": "demonio", "observado_en": T2}},
                       k_web: {"ana": {"valor": {"escucha": False, "salud": None}, "fuente": "demonio", "observado_en": T2}}}
        pruebas = {servicios.huella_prueba("uv run pytest tests/test_motor_web.py"):
                   {"valor": "falla", "fuente": "hook", "observado_en": T2}}
        s = calc(t, historia(("s1", BASE), ("a1", t)), comprobados=comprobados, pruebas=pruebas)
        self.assertEqual(tipos(s), ["contrato_inexistente", "prueba_falla", "puerto_sin_respuesta", "salud_falla"])
        d = {x["tipo"]: x for x in s["desajustes"]}
        self.assertEqual((d["puerto_sin_respuesta"]["fuente"], d["puerto_sin_respuesta"]["observado_en"]),
                         ("demonio", T2))
        self.assertEqual(d["prueba_falla"]["personas"], ["ana", "luis"])
        self.assertEqual(con(s, "motor")["resultado"]["valor"], "falla")

    def test_sin_confirmar_no_da_desajuste_de_puerto(self):
        t = md([API[:2] + ("9000",) + API[3:], WEB, MOTOR], [WEB_API, MOTOR_WEB])
        k = servicios.leer(t)["filas"][0]["clave"]
        s = calc(t, historia(("s1", BASE), ("l1", t)),
                 comprobados={k: {"ana": {"valor": {"escucha": False}, "fuente": "demonio", "observado_en": T2}}})
        self.assertNotIn("puerto_sin_respuesta", tipos(s))

    def test_solo_cuenta_el_demonio_del_dueno(self):
        k = servicios.leer(BASE)["filas"][0]["clave"]
        caido = {"valor": {"escucha": False, "salud": None}, "fuente": "demonio", "observado_en": T2}
        s = calc(BASE, historia(("s1", BASE)), comprobados={k: {"luis": caido}})   # api es de ana
        self.assertIsNone(de(s, "api")["comprobado"])
        self.assertNotIn("puerto_sin_respuesta", tipos(s))

    def test_codigo_fuera_de_todo_servicio(self):
        rutas = ["api/main.py", "web/src/App.tsx", "motor/m.py", "docs/x.md", "README.md", ".gitignore",
                 ".hackathon/plan.md", "scripts/descarga.py", "notas.txt"]
        s = calc(BASE, historia(("s1", BASE)), rutas=rutas)
        d = [x for x in s["desajustes"] if x["tipo"] == "codigo_fuera"]
        self.assertEqual(d[0]["rutas"], ["notas.txt", "scripts/descarga.py"])
        self.assertEqual(s["fuera"][:3], [".hackathon/", ".claude/", ".github/"])

    def test_cumple_el_esquema(self):
        t = md([API, WEB, MOTOR, ("mal", "x", "0", "—", "http://x", "ana")], [WEB_API, MOTOR_WEB],
               prop_c=[("motor", "api", "web → api", "—", "@luis", "ayer")])
        s = calc(t, historia(("s1", BASE), ("l1", t)), rutas=["scripts/a.py"])
        estado = {"v": 1, "generado_en": T, "fuentes": {}, "personas": [], "tareas": [], "colisiones": [],
                  "servicios": s}
        self.assertIsNone(Esquema("estado.schema.json").error(estado))


if __name__ == "__main__":
    unittest.main()
