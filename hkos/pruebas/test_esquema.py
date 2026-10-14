"""M8d: el validador mínimo de hkos/esquema.py (el que usan el relay y el demonio) da el mismo veredicto que
jsonschema con los esquemas de contratos/. Sin jsonschema, la comparación se salta y quedan las comprobaciones propias.

Uso: uv run --no-project --with "jsonschema[format-nongpl]" -m unittest discover -s hkos/pruebas -v
"""
import copy
import json
import os
import sys
import unittest

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
from esquema import Esquema  # noqa: E402
from modelo import calcular  # noqa: E402
from test_esquemas import EVENTO, NORMALIZADAS, USABLE, carga, validador  # noqa: E402


def eventos_de_prueba():
    buenos = [EVENTO, dict(EVENTO, ts="2026-11-20T10:00:00.123456Z"), dict(EVENTO, ts="2026-11-20T10:00:00+01:00"),
              dict(EVENTO, tipo="push", datos={"incluye": ["abc1234"], "sha": "abcdef0"}),
              dict(EVENTO, tipo="reserva", datos={"ttl_s": 900, "modo": "compartida"})]
    buenos += [c["evento"] for c in carga(NORMALIZADAS)["casos"] if c["evento"]]
    malos = [{k: v for k, v in EVENTO.items() if k != "fuente"}, dict(EVENTO, contenido="x"), dict(EVENTO, tarea="T7"),
             dict(EVENTO, actor={"persona": "persona-b", "papel": "jefe"}),
             dict(EVENTO, actor={"persona": "Mveradc", "papel": "principal"}),
             dict(EVENTO, actor={"persona": "persona-b", "papel": "principal", "otro": 1}),
             dict(EVENTO, tipo="push", datos={"incluye": ["xyz"]}), dict(EVENTO, datos={"veredicto": "OK"}),
             dict(EVENTO, ts="ayer"), dict(EVENTO, ts="2026-11-20 10:00:00"), dict(EVENTO, ts="2026-11-20T10:00:00"),
             dict(EVENTO, v=2), dict(EVENTO, v=True), dict(EVENTO, rutas="a.txt"), dict(EVENTO, rutas=[1]),
             dict(EVENTO, datos={"ttl_s": 10}), dict(EVENTO, datos={"ttl_s": 900.5}), dict(EVENTO, datos={"ttl_s": True}),
             dict(EVENTO, datos={"motivos": ["x" * 301]}), dict(EVENTO, datos={"alcanzable": "sí"}), dict(EVENTO, datos=[]),
             "no es un objeto", None, []]
    return buenos, malos


def estados_de_prueba():
    tareas = [{"id": "T10", "titulo": "Diez", "dueno": "persona-b", "depende_de": ["T11", "T99"]},
              {"id": "T11", "titulo": "Once", "dueno": "persona-b", "depende_de": []}]
    issues = {"T10": {"creado_en": "2026-11-20T09:00:00Z", "numero": 30,
                      "acciones": [{"accion": "cerrar", "por": "fuera", "ts": "2026-11-20T09:30:00Z"}]},
              "T11": {"creado_en": "2026-11-20T09:00:00Z",
                      "acciones": [{"accion": "cerrar", "por": "persona-b", "ts": "2026-11-20T09:10:00Z"}]}}
    ev = dict(EVENTO, tipo="arbol", actor={"persona": "persona-a", "papel": "principal", "sesion": "s2"})
    ev.pop("tarea")
    bueno = calcular(tareas, issues, [ev], [{"persona": "persona-a", "nombre": "A"}, {"persona": "persona-b", "nombre": "B"}],
                     "2026-11-20T10:01:00Z")
    con_corrupta = copy.deepcopy(bueno)
    con_corrupta["discrepancias"].append({"tipo": "linea_corrupta", "persona": "persona-a", "detalle": "2 líneas rotas",
                                          "veces": 2, "primera_vez": "2026-11-20T10:00:00Z", "ultima_vez": "2026-11-20T10:00:00Z"})
    malos = []
    for cambio in (lambda e: e["tareas"][0]["estado"].update(valor="en curso"), lambda e: e["tareas"][0].update(extra=1),
                   lambda e: e.update(extra=1), lambda e: e["discrepancias"][0].pop("veces"),
                   lambda e: e["discrepancias"][0].update(veces=0), lambda e: e["discrepancias"][0].update(tipo="otro"),
                   lambda e: e["personas"][0]["actores"][0].update(papel="demonio"),
                   lambda e: e["tareas"][0].update(declarado={"valor": "cerrada"}),
                   lambda e: e["tareas"][0].update(issue="30"), lambda e: e.pop("colisiones")):
        e = copy.deepcopy(bueno)
        cambio(e)
        malos.append(e)
    return [bueno, con_corrupta, dict(copy.deepcopy(bueno), tareas=[dict(bueno["tareas"][0], declarado=None)])], malos


class Propio(unittest.TestCase):
    def test_veredictos(self):
        for nombre, (buenos, malos) in (("eventos.schema.json", eventos_de_prueba()), ("estado.schema.json", estados_de_prueba())):
            e = Esquema(nombre)
            for i, x in enumerate(buenos):
                with self.subTest(nombre, bueno=i):
                    self.assertIsNone(e.error(x))
            for i, x in enumerate(malos):
                with self.subTest(nombre, malo=i):
                    self.assertIsNotNone(e.error(x))

    def test_campo_del_error(self):
        self.assertEqual(Esquema("eventos.schema.json").error(dict(EVENTO, contenido="x")), ("/contenido", "campo no permitido"))

    def test_palabra_clave_desconocida_falla(self):
        e = Esquema("eventos.schema.json")
        with self.assertRaises(ValueError):
            e._revisar({"type": "object", "oneOf": []})


@unittest.skipIf(not USABLE, "sin jsonschema con Draft 2020-12: lanzar con uv run --with \"jsonschema[format-nongpl]\"")
class IgualQueJsonschema(unittest.TestCase):
    def test_mismo_veredicto(self):
        for nombre, (buenos, malos) in (("eventos.schema.json", eventos_de_prueba()), ("estado.schema.json", estados_de_prueba())):
            propio, ref = Esquema(nombre), validador(nombre)
            for i, x in enumerate(buenos + malos):
                with self.subTest(nombre, caso=i, valor=json.dumps(x, ensure_ascii=False)[:80]):
                    self.assertEqual(propio.valido(x), ref.is_valid(x))


if __name__ == "__main__":
    unittest.main()
