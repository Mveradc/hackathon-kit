"""Criterio 1 de M8b y K-20: los esquemas de contratos/ validan con un validador JSON Schema 2020-12.

jsonschema solo lo usan las pruebas, nunca el OS. Sin él, o con uno sin Draft 2020-12 y su comprobador de formatos
(la 3.2 de algunos sistemas, la 4.0), estas pruebas se saltan.
Uso: uv run --no-project --with "jsonschema[format-nongpl]" -m unittest discover -s hkos/pruebas -v
"""
import copy
import json
import os
import sys
import unittest

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(HKOS)
sys.path.insert(0, HKOS)
from modelo import calcular  # noqa: E402

try:
    import jsonschema
except ImportError:
    jsonschema = None
CONTRATOS = os.path.join(KIT, "docs", "hackathon-os", "contratos")
NORMALIZADAS = os.path.join(KIT, "evals", "coordinacion", "entradas", "normalizadas.json")


def carga(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _usable():
    """Draft202012Validator llega en la 4.0 y su FORMAT_CHECKER después; sin el extra «format», no comprueba date-time,
    y la 4.10 del sistema de Ubuntu no resuelve los $ref con el $id de estado.schema.json (M8d, WSL). Se prueba que
    funciona de verdad, no solo que existe."""
    v = getattr(jsonschema, "Draft202012Validator", None)
    if not hasattr(v, "FORMAT_CHECKER"):
        return False
    try:
        if v({"format": "date-time"}, format_checker=v.FORMAT_CHECKER).is_valid("ayer"):
            return False
        v(carga(os.path.join(CONTRATOS, "estado.schema.json"))).is_valid({"tareas": [{"estado": {}}]})
    except Exception:
        return False
    return True


USABLE = _usable()


def validador(nombre):
    esquema = carga(os.path.join(CONTRATOS, nombre))
    jsonschema.Draft202012Validator.check_schema(esquema)
    return jsonschema.Draft202012Validator(esquema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER)


EVENTO = {"v": 1, "id": "s1-1", "ts": "2026-11-20T10:00:00Z", "actor": {"persona": "persona-b", "papel": "worker", "agente": "a1"},
          "tipo": "edicion", "tarea": "T14", "rutas": ["web/src/App.jsx"], "fuente": "hook", "datos": {"lo_que_sea": 1}}


@unittest.skipIf(not USABLE, "sin jsonschema con Draft 2020-12: lanzar con uv run --with \"jsonschema[format-nongpl]\"")
class Esquemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ev = validador("eventos.schema.json")
        cls.es = validador("estado.schema.json")

    def test_el_formato_de_fecha_se_comprueba(self):
        # Sin el extra «format», jsonschema acepta cualquier date-time sin avisar.
        self.assertFalse(self.ev.is_valid(dict(EVENTO, ts="ayer")))

    def test_evento_valido_con_datos_abiertos(self):
        self.ev.validate(EVENTO)

    def test_eventos_invalidos(self):
        malos = {
            "sin fuente": {k: v for k, v in EVENTO.items() if k != "fuente"},
            "campo de más": dict(EVENTO, contenido="x"),
            "tarea mal": dict(EVENTO, tarea="T7"),
            "papel desconocido": dict(EVENTO, actor={"persona": "persona-b", "papel": "jefe"}),
            "persona con mayúsculas": dict(EVENTO, actor={"persona": "Mveradc", "papel": "principal"}),
            "sha mal": dict(EVENTO, tipo="push", datos={"incluye": ["xyz"]}),
            "veredicto raro": dict(EVENTO, tipo="revision.veredicto", datos={"veredicto": "OK"}),
        }
        for nombre, e in malos.items():
            with self.subTest(nombre):
                self.assertFalse(self.ev.is_valid(e))

    def test_entradas_reales_normalizadas(self):
        doc = carga(NORMALIZADAS)
        con_evento = [c for c in doc["casos"] if c["evento"]]
        self.assertGreaterEqual(len(con_evento), 15)
        ids = [c["evento"]["id"] for c in con_evento]
        self.assertEqual(len(ids), len(set(ids)))
        for c in con_evento:
            with self.subTest(c["entrada"]):
                self.ev.validate(c["evento"])
                self.assertTrue(os.path.exists(os.path.join(os.path.dirname(NORMALIZADAS), c["entrada"])))

    def estado(self):
        tareas = [{"id": "T10", "titulo": "Diez", "dueno": "persona-b", "depende_de": ["T11", "T99"]},
                  {"id": "T11", "titulo": "Once", "dueno": "persona-b", "depende_de": []}]
        issues = {"T10": {"creado_en": "2026-11-20T09:00:00Z", "numero": 30, "acciones": [
                      {"accion": "cerrar", "por": "fuera", "ts": "2026-11-20T09:30:00Z"}]},
                  "T11": {"creado_en": "2026-11-20T09:00:00Z", "acciones": [
                      {"accion": "cerrar", "por": "persona-b", "ts": "2026-11-20T09:10:00Z"}]}}
        eventos = [dict(EVENTO, tarea=None, tipo="arbol", actor={"persona": "persona-a", "papel": "principal", "sesion": "s2"})]
        eventos[0].pop("tarea")
        return calcular(tareas, issues, eventos, [{"persona": "persona-a", "nombre": "A"}, {"persona": "persona-b", "nombre": "B"}],
                        "2026-11-20T10:01:00Z")

    def test_estado_del_modelo_valida(self):
        e = self.estado()
        self.es.validate(e)
        tipos = {d["tipo"] for d in e["discrepancias"]}
        self.assertEqual(tipos, {"dependencia_inexistente", "fuera_del_equipo"})
        self.assertEqual(e["tareas"][0]["cumplidas_por_cierre"], ["T11"])
        self.assertEqual(len(e["sin_tarea"]), 1)

    def test_estados_invalidos(self):
        bueno = self.estado()
        malos = {}
        e = copy.deepcopy(bueno); e["tareas"][0]["estado"]["valor"] = "en curso"; malos["estado con espacio"] = e
        e = copy.deepcopy(bueno); e["tareas"][0]["extra"] = 1; malos["campo de más en tarea"] = e
        e = copy.deepcopy(bueno); e["extra"] = 1; malos["campo de más arriba"] = e
        e = copy.deepcopy(bueno); del e["discrepancias"][0]["veces"]; malos["discrepancia sin contador"] = e
        e = copy.deepcopy(bueno); e["personas"][0]["actores"][0]["papel"] = "demonio"; malos["actor demonio"] = e
        for nombre, e in malos.items():
            with self.subTest(nombre):
                self.assertFalse(self.es.is_valid(e))


if __name__ == "__main__":
    unittest.main()
