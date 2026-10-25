"""K-114 (M11, criterio 4; hallazgo de K-112 en el PR #84): escucha.sh recordaba para siempre las rojas vistas, así que
una roja que bajaba a 2b y volvía a rojo con el mismo texto no abría turno. Lo demás, igual: la misma roja con otra
hora no es nueva, las amarillas no abren turno y las que había al arrancar tampoco.

Issue #88 (decisiones del usuario del 2026-10-25), dos reglas:
1. Una roja solo se olvida cuando su par pasa a 2b (sale una línea `nivel 2b` de las mismas personas). Si se va por
   otra cosa (el relay que se reinicia y publica un md sin ella, un ref WIP borrado un momento), al volver no abre
   turno, como en la 0.5.0. Por eso `test_roja_que_se_va_y_vuelve_...` ha cambiado de sentido: antes daba 1 línea.
2. Una roja de nivel 2 con un subconjunto de los ficheros de una roja ya vista del mismo par no abre turno, si ese par
   sale en una línea `nivel 2b`. Sin 2b (`x.py` se resuelve y no hay 2b) abre turno, como en la 0.5.0: con el 2b
   apagado, el monitor es el de la 0.5.0 (constitución I).

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
DOS = dict(ROJA, rutas=["src/x.py", "src/y.py"])
SOLO_Y = dict(ROJA, rutas=["src/y.py"], observado_en="2026-11-20T10:26:00Z")
X_EN_2B = dict(m11.BAJA, rutas=["src/x.py"])


@unittest.skipUnless(m11.BASH and os.name != "nt", "sin bash, o en Windows (allí, escucha.sh lo prueba prueba_hooks.py)")
class Escucha(m11._Md):
    escucha = m11.Monitor.escucha

    def test_roja_que_baja_a_2b_y_vuelve_una_linea(self):
        self.deja([ROJA])                                  # ya estaba al arrancar: va en el bloque de inicio
        salida = self.escucha([lambda: self.deja([BAJA]), lambda: self.deja([ROJA]),
                               lambda: self.deja([ROJA], ahora="2026-11-20T10:59:00Z")])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn(LINEA, salida[0])

    def test_roja_que_se_va_y_vuelve_ninguna_linea(self):
        """Regla 1: irse sin pasar a 2b no la olvida (antes de #88 daba 1 línea)."""
        self.deja([ROJA, OTRA])
        salida = self.escucha([lambda: self.deja([OTRA]), lambda: self.deja([ROJA, OTRA])])
        self.assertEqual(salida, [])

    def test_md_que_pierde_la_roja_un_momento_ninguna_linea(self):
        """Regla 1: el relay que se reinicia publica un md sin colisiones antes del primer sondeo; como en la 0.5.0."""
        self.deja([ROJA])
        salida = self.escucha([lambda: self.deja([]), lambda: self.deja([ROJA])])
        self.assertEqual(salida, [])

    def test_2b_de_otro_par_no_la_olvida(self):
        """Regla 1: un 2b de otras personas no cuenta."""
        otro = dict(BAJA, id="2b:persona-b+persona-c", personas=["persona-b", "persona-c"])
        self.deja([ROJA])
        salida = self.escucha([lambda: self.deja([otro]), lambda: self.deja([ROJA, otro])])
        self.assertEqual(salida, [])

    def test_roja_con_menos_ficheros_ninguna_linea(self):
        """Regla 2: un fichero baja a 2b y el otro sigue rojo; es una buena noticia, no una roja nueva."""
        self.deja([DOS])
        salida = self.escucha([lambda: self.deja([SOLO_Y, X_EN_2B])])
        self.assertEqual(salida, [])

    def test_roja_con_menos_ficheros_y_vuelta_una_linea(self):
        """Reglas 1 y 2 juntas: x.py baja a 2b (ninguna línea) y vuelve a rojo (una)."""
        self.deja([DOS])
        salida = self.escucha([lambda: self.deja([SOLO_Y, X_EN_2B]), lambda: self.deja([DOS])])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn("colisión ROJA nueva · nivel 2 · src/x.py, src/y.py · @persona-a, @persona-b", salida[0])

    def test_roja_con_menos_ficheros_sin_2b_una_linea(self):
        """Regla 2: sin una línea 2b del par (x.py se resuelve, o el 2b está apagado), como en la 0.5.0."""
        self.deja([DOS])
        salida = self.escucha([lambda: self.deja([SOLO_Y])])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn("colisión ROJA nueva · nivel 2 · src/y.py · @persona-a, @persona-b", salida[0])

    def test_roja_con_otros_ficheros_una_linea(self):
        """Regla 2: solo vale un subconjunto; con un fichero que no estaba es una roja nueva, aunque haya 2b."""
        self.deja([DOS])
        salida = self.escucha([lambda: self.deja([dict(ROJA, rutas=["src/y.py", "src/z.py"]), X_EN_2B])])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn("nivel 2 · src/y.py, src/z.py", salida[0])

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
