"""M8e: rendimiento de modelo.calcular() con el indexado por tarea (Pendiente de M8d). El relay recalcula tras cada lote
con todos los eventos: con tareas reales y miles de eventos tiene que seguir cabiendo en el ritmo del relay.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import os
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
from estados import iso  # noqa: E402
from modelo import calcular  # noqa: E402

T0 = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
PERSONAS = [{"persona": f"p{i}", "nombre": chr(65 + i)} for i in range(5)]


def escenario(n_eventos=20000, n_tareas=30):
    """30 tareas repartidas entre 5 personas; cada persona reclama una y edita sin ID (la regla 9 tiene trabajo);
    el resto, eventos con tarea y algún push."""
    tareas = [{"id": f"T{i + 1:02d}", "titulo": f"Tarea {i + 1}", "dueno": f"p{i % 5}",
               "depende_de": [f"T{i:02d}"] if i % 4 == 3 else []} for i in range(n_tareas)]
    issues = {t["id"]: {"creado_en": iso(T0), "numero": 100 + i, "acciones": []} for i, t in enumerate(tareas)}
    eventos = []
    for p in range(5):
        eventos.append({"v": 1, "id": f"r{p}", "ts": iso(T0), "actor": {"persona": f"p{p}", "papel": "principal"},
                        "tipo": "reclamo", "tarea": f"T{p + 1:02d}", "fuente": "mcp"})
    for n in range(n_eventos):
        p = n % 5
        e = {"v": 1, "id": f"e{n}", "ts": iso(T0 + timedelta(seconds=n)), "actor": {"persona": f"p{p}", "papel": "principal",
             "sesion": f"s{p}"}, "fuente": "hook"}
        if n % 500 == 499:
            e.update(tipo="push", fuente="git", datos={"sha": "abcdef0", "incluye": []})
        elif n % 3:
            e.update(tipo="edicion", rutas=[f"src/f{n % 7}.py"])
        else:
            e.update(tipo="arbol", tarea=f"T{(n % n_tareas) + 1:02d}" if (n % n_tareas) % 5 == p else None, rutas=["a.py"])
            if e["tarea"] is None:
                del e["tarea"]
        eventos.append(e)
    return tareas, issues, eventos


class Rendimiento(unittest.TestCase):
    def test_20000_eventos_y_30_tareas_en_menos_de_1_s(self):
        tareas, issues, eventos = escenario()
        t = time.perf_counter()
        e = calcular(tareas, issues, eventos, PERSONAS, iso(T0 + timedelta(hours=7)))
        dt = time.perf_counter() - t
        self.assertEqual(len(e["tareas"]), 30)
        self.assertEqual({t["estado"]["valor"] for t in e["tareas"] if t["id"] in ("T01", "T02")}, {"parada"})
        self.assertLess(dt, 1.0, f"{dt:.2f} s")


if __name__ == "__main__":
    unittest.main()
