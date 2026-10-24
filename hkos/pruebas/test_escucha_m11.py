"""K-114 (M11, criterio 4; hallazgo de K-112 en el PR #84): escucha.sh recordaba para siempre las rojas vistas, así que
una roja que bajaba a 2b (o se iba) y volvía a rojo con el mismo texto no abría turno. Ahora solo recuerda las que
siguen en estado-equipo.md: la que se va o baja se olvida, y al volver da una línea del monitor. Lo demás, igual: la
misma roja con otra hora no es nueva, las amarillas no abren turno y las que había al arrancar tampoco.

Con el escucha.sh de verdad y el md que escribe proyeccion.markdown, como `Monitor` en test_proyeccion_m11.py.

Uso: uv run --no-project -m unittest hkos.pruebas.test_escucha_m11 -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_proyeccion_m11 as m11  # noqa: E402

ROJA, BAJA = m11.ROJA, m11.BAJA
OTRA = m11.colision("3:api:persona-a", "3", "rojo", ["motor/api.py"], "2026-11-20T10:21:00Z")
LINEA = "colisión ROJA nueva · nivel 2 · src/app.py · @persona-a, @persona-b"


@unittest.skipUnless(m11.BASH and os.name != "nt", "sin bash, o en Windows (allí, escucha.sh lo prueba prueba_hooks.py)")
class Escucha(m11._Md):
    escucha = m11.Monitor.escucha

    def test_roja_que_baja_a_2b_y_vuelve_una_linea(self):
        self.deja([ROJA])                                  # ya estaba al arrancar: va en el bloque de inicio
        salida = self.escucha([lambda: self.deja([BAJA]), lambda: self.deja([ROJA]),
                               lambda: self.deja([ROJA], ahora="2026-11-20T10:59:00Z")])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn(LINEA, salida[0])

    def test_roja_que_se_va_y_vuelve_una_linea(self):
        self.deja([ROJA, OTRA])
        salida = self.escucha([lambda: self.deja([OTRA]), lambda: self.deja([ROJA, OTRA])])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn(LINEA, salida[0])

    def test_dos_vueltas_dos_lineas(self):
        self.deja([])
        salida = self.escucha([lambda: self.deja([ROJA]), lambda: self.deja([BAJA]), lambda: self.deja([ROJA])])
        self.assertEqual(len(salida), 2, salida)
        self.assertTrue(all(LINEA in l for l in salida), salida)

    def test_lo_demas_igual(self):
        """La misma roja con otra hora, una amarilla al lado y la que ya estaba al arrancar: ninguna línea."""
        self.deja([ROJA])
        salida = self.escucha([lambda: self.deja([dict(ROJA, observado_en="2026-11-20T10:40:00Z")]),
                               lambda: self.deja([ROJA, BAJA | {"id": "1:persona-a+persona-b", "nivel": "1"}])])
        self.assertEqual(salida, [])


if __name__ == "__main__":
    unittest.main()
