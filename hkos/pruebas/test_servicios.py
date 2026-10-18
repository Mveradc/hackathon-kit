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
    """[(sha, texto)] → versiones en orden, cada una con el texto de su padre (la anterior). La primera es la que crea el
    fichero (`crea`, como lo marca relay.Novedades cuando lo sabe con certeza)."""
    versiones, anterior = [], None
    for sha, texto in pasos:
        versiones.append({"sha": sha, "textos_padres": [anterior], "texto": texto, "crea": not versiones})
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

    def test_borrada_y_vuelta_a_anadir_olvida_quien_la_confirmo(self):
        """Decisión 2B (PR #13, hallazgo 10 del issue #2): al borrarse una clave de servicios.md se olvida su `por`;
        solo cuentan las adiciones posteriores al último borrado (ADR-0011: ante la duda, sin confirmar)."""
        cache = ("cache", "api/cache/", "6379", "—", "—", "@ana")
        con_cache = md([API, WEB, MOTOR, cache], [WEB_API, MOTOR_WEB])
        # ana la añade, ella misma la quita y luis la resucita tal cual: no sale confirmada por ana.
        s = calc(con_cache, historia(("s1", BASE), ("a1", con_cache), ("a2", BASE), ("l1", con_cache)))
        c = de(s, "cache")["confirmacion"]
        self.assertEqual((c["valor"], c["por"], c["faltan"]), ("sin_confirmar", ["luis"], ["ana"]))
        # Un sha desconocido que la vuelve a añadir (un revert reescrito) tampoco la confirma.
        s = calc(con_cache, historia(("s1", BASE), ("a1", con_cache), ("l2", BASE), ("rebase-1", con_cache)))
        self.assertEqual(de(s, "cache")["confirmacion"]["por"], [])
        # Si ana la vuelve a añadir después del borrado, sí.
        s = calc(con_cache, historia(("s1", BASE), ("a1", con_cache), ("l1", BASE), ("a2", con_cache)))
        self.assertEqual(de(s, "cache")["confirmacion"]["valor"], "confirmada")
        # Moverla de Propuestas a su tabla no es borrarla: la clave sigue en el fichero.
        prop = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB], prop_s=[cache + ("@luis", "2026-11-25 18:10")])
        s = calc(con_cache, historia(("s1", BASE), ("l1", prop), ("a1", con_cache)))
        self.assertEqual(de(s, "cache")["confirmacion"]["por"], ["ana", "luis"])
        # Una fila de /hack-scaffold que se borra y otra persona vuelve a añadir ya no es de scaffold.
        sin_api = md([WEB, MOTOR], [WEB_API, MOTOR_WEB])
        s = calc(BASE, historia(("s1", BASE), ("a1", sin_api), ("l1", BASE)))
        c = de(s, "api")["confirmacion"]
        self.assertEqual((c["valor"], c["de_scaffold"], c["por"]), ("sin_confirmar", False, ["luis"]))

    def test_fila_de_una_resolucion_de_merge_no_confirma(self):
        a = md([API, WEB, MOTOR, ("cache", "api/cache/", "1", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        b = md([API, WEB, MOTOR, ("cache", "api/cache/", "2", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        m = md([API, WEB, MOTOR, ("cache", "api/cache/", "3", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
        versiones = historia(("s1", BASE), ("a1", a)) + [{"sha": "a2", "textos_padres": [BASE], "texto": b},
                                                       {"sha": "merge", "textos_padres": [a, b], "texto": m}]
        self.assertEqual(de(calc(m, versiones), "cache")["confirmacion"]["valor"], "sin_confirmar")


class RevisionM9a(unittest.TestCase):
    """Issue #2 (revisión independiente de M9a), hallazgos 1, 4, 5, 6, 9 y 13, y sus casos de la sección 6."""

    def test_h1_sin_saber_que_commit_creo_el_fichero_nada_es_de_scaffold(self):
        otra = md([API, ("intruso", "api/intruso/", "9999", "—", "/x", "@luis")], [])
        sin_crea = [dict(v, crea=False) for v in historia(("s1", BASE))]
        dos_raices = historia(("s1", BASE)) + [{"sha": "l1", "textos_padres": [], "texto": otra, "crea": False}]
        dos_marcadas = historia(("s1", BASE)) + [{"sha": "l1", "textos_padres": [None], "texto": otra, "crea": True}]
        merge_que_crea = [{"sha": "s1", "textos_padres": [None, None], "texto": BASE, "crea": True}]   # sección 6, caso 7
        for nombre, versiones in (("sin crea", sin_crea), ("dos raíces", dos_raices), ("dos marcadas", dos_marcadas),
                                  ("merge que crea", merge_que_crea)):
            s = calc(BASE, versiones)
            c = de(s, "api")["confirmacion"]
            self.assertEqual((c["valor"], c["de_scaffold"]), ("sin_confirmar", False), nombre)
            self.assertEqual(con(s, "motor")["confirmacion"]["valor"], "sin_confirmar", nombre)
            self.assertEqual(servicios.confirmaciones(versiones, SHA)[2], set(), nombre)

    def test_h4_nombre_repetido_no_confirma_nada_que_lo_use(self):
        # [reproducido] @luis añade en un commit un segundo «api» en motor/api/ y la conexión motor → api
        motor_api = ("motor", "api", "web → api", "`uv run pytest tests/test_motor_api.py`")
        t = md([API, WEB, MOTOR, ("api", "motor/api/", "—", "—", "—", "@luis")], [WEB_API, MOTOR_WEB, motor_api])
        s = calc(t, historia(("s1", BASE), ("l1", t)))
        self.assertEqual(s["fichero"]["valor"], "mal formado")
        c = next(x for x in s["conexiones"] if (x["de"], x["a"]) == ("motor", "api"))
        self.assertEqual((c["confirmacion"]["valor"], c["duenos"]), ("sin_confirmar", ["ana", "luis"]))
        apis = [x for x in s["lista"] if x["nombre"] == "api"]
        self.assertEqual([(x["dueno_autoridad"], x["confirmacion"]["valor"]) for x in apis],
                         [("ana", "sin_confirmar"), ("luis", "sin_confirmar")])
        self.assertEqual(con(s, "web")["confirmacion"]["valor"], "sin_confirmar")    # web → api, de scaffold
        self.assertEqual(con(s, "motor")["confirmacion"]["valor"], "confirmada")      # motor → web no usa «api»
        self.assertEqual(de(s, "motor")["confirmacion"]["valor"], "confirmada")

    def test_h5_mismo_sha_de_dos_personas_no_es_de_nadie(self):
        def commit(persona, sha="c1"):
            return {"tipo": "commit", "actor": {"persona": persona, "papel": "humano"}, "datos": {"sha": sha}}
        for orden in ((commit("ana"), commit("luis")), (commit("luis"), commit("ana")),
                      (commit("ana"), commit("luis"), commit("ana"))):
            mapa = servicios.personas_de_commits(list(orden) + [commit("ana", "c2"), commit("ana", "c2")])
            self.assertEqual(mapa, {"c1": None, "c2": "ana"})
            t = md([API, WEB, MOTOR, ("cache", "api/cache/", "—", "—", "—", "@ana")], [WEB_API, MOTOR_WEB])
            s = servicios.calcular(t, historia(("s1", BASE), ("c1", t)), mapa, AUTORIDAD, CONTRATOS, (), {}, {}, T)
            c = de(s, "cache")["confirmacion"]
            self.assertEqual((c["valor"], c["por"]), ("sin_confirmar", []))

    def test_h6_fila_con_un_campo_que_no_vale_no_sale_confirmada(self):
        # [reproducido] | api | api/ | 8000 | — | http://evil/ | @ana |, de /hack-scaffold
        mala = ("api", "api/", "8000", "—", "http://evil/", "@ana")
        t = md([mala, WEB, MOTOR], [WEB_API, MOTOR_WEB])
        k = servicios.leer(t)["filas"][0]["clave"]
        caido = {"valor": {"escucha": False, "salud": None}, "fuente": "demonio", "observado_en": T2}
        s = calc(t, historia(("s1", t)), comprobados={k: {"ana": caido}})
        api = de(s, "api")
        self.assertEqual((api["confirmacion"]["valor"], api["salud"]), ("sin_confirmar", None))
        self.assertTrue(api["confirmacion"]["de_scaffold"])
        self.assertEqual(tipos(s), ["formato_invalido"])                 # ni puerto_sin_respuesta: no se consulta
        self.assertEqual(s["desajustes"][0]["clave"], k)
        # Carpeta o Puerto que no valen; una conexión con un campo que no vale
        for fila in (("api", "api", "8000", "—", "/salud", "@ana"), ("api", "api/", "0", "—", "/salud", "@ana"),
                     ("api", "api/", "x", "—", "/salud", "@ana")):
            t = md([fila, WEB, MOTOR], [WEB_API, MOTOR_WEB])
            self.assertEqual(de(calc(t, historia(("s1", t))), "api")["confirmacion"]["valor"], "sin_confirmar", fila)
        larga = WEB_API[:3] + ("x" * 301,)
        t = md([API, WEB, MOTOR], [larga, MOTOR_WEB])
        self.assertEqual(con(calc(t, historia(("s1", t))), "web")["confirmacion"]["valor"], "sin_confirmar")

    def test_h9_propuesta_del_commit_inicial_no_es_de_scaffold(self):
        # [reproducido] el fichero inicial trae «cache» en Propuestas; @luis la pasa después a Servicios
        cache = ("cache", "api/cache/", "6379", "—", "—", "@ana")
        v1 = md([API, WEB, MOTOR], [WEB_API, MOTOR_WEB], prop_s=[cache + ("@ana", "2026-11-25 18:00")])
        v2 = md([API, WEB, MOTOR, cache], [WEB_API, MOTOR_WEB])
        s = calc(v2, historia(("s1", v1), ("l1", v2)))
        c = de(s, "cache")["confirmacion"]
        self.assertEqual((c["valor"], c["de_scaffold"], c["por"], c["faltan"]),
                         ("sin_confirmar", False, ["luis"], ["ana"]))
        self.assertTrue(de(s, "api")["confirmacion"]["de_scaffold"])
        # lo mismo con una propuesta de conexión
        motor_api = ("motor", "api", "web → api", "—")
        v1 = md([API, WEB, MOTOR], [WEB_API], prop_c=[motor_api + ("@luis", "2026-11-25 18:00")])
        v2 = md([API, WEB, MOTOR], [WEB_API, motor_api])
        c = con(calc(v2, historia(("s1", v1), ("l1", v2))), "motor")["confirmacion"]
        self.assertEqual((c["valor"], c["de_scaffold"], c["faltan"]), ("sin_confirmar", False, ["ana"]))

    def test_h13_salud_con_puntos_codificados_no_vale(self):
        # sección 6, caso 12: %2e%2e (mayúsculas, minúsculas, mezclado, dos veces), ? y # y @
        for salud, vale in (("/salud/%2e%2e/%2e%2e/admin", False), ("/salud/%2E%2E/admin", False),
                            ("/salud/.%2e/admin", False), ("/%2e%2E", False), ("/salud/%252e%252e/admin", False),
                            ("/%2f%2fhost/salud", False), ("/salud?x=1", True), ("/api/health?x=1", True),
                            ("/salud#x", False), ("/@host", True), ("/salud/%20x", True), ("/salud", True)):
            self.assertEqual(servicios.salud_valida(salud), vale, salud)
            t = md([API[:4] + (salud,) + API[5:], WEB, MOTOR], [WEB_API, MOTOR_WEB])
            s = calc(t, historia(("s1", t)))
            self.assertEqual(de(s, "api")["confirmacion"]["valor"], "confirmada" if vale else "sin_confirmar", salud)
            self.assertEqual(de(s, "api")["salud"], salud if vale else None, salud)
            self.assertEqual(tipos(s), [] if vale else ["formato_invalido"], salud)


class Desajustes(unittest.TestCase):
    def test_salud_que_no_es_una_ruta(self):
        for salud in ("http://x/salud", "//host/salud", "/../salud", "salud"):
            t = md([API[:4] + (salud,) + API[5:], WEB, MOTOR], [WEB_API, MOTOR_WEB])
            comprobado = {"valor": {"escucha": True, "salud": None}, "fuente": "demonio", "observado_en": T2}
            s = calc(t, historia(("s1", t)), comprobados={servicios.leer(t)["filas"][0]["clave"]: {"ana": comprobado}})
            self.assertEqual(tipos(s), ["formato_invalido"], salud)   # ni salud_falla: no se consulta
            self.assertEqual((de(s, "api")["confirmacion"]["valor"], de(s, "api")["salud"]), ("sin_confirmar", None))

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
