"""M8g: colisiones de nivel 1 y 3 y reservas (colisiones.py, contratos.py), con el reloj inyectado.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import colisiones  # noqa: E402
import contratos  # noqa: E402
from estados import iso  # noqa: E402
from modelo import calcular  # noqa: E402

T0 = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
PERSONAS = [{"persona": "ana", "nombre": "A"}, {"persona": "bea", "nombre": "B"}, {"persona": "carla", "nombre": "C"}]
EQUIPO = {"ana", "bea", "carla"}


def ts(s):
    return iso(T0 + timedelta(seconds=s))


class Eventos:
    def __init__(self):
        self.lista, self.n = [], 0

    def __call__(self, s, persona, tipo, papel="principal", agente=None, worktree="", **extra):
        self.n += 1
        actor = {"persona": persona, "papel": papel, "sesion": f"s-{persona}", "worktree": worktree}
        if agente:
            actor["agente"] = agente
        e = {"v": 1, "id": f"e{self.n}", "ts": ts(s), "actor": actor, "tipo": tipo, "fuente": "hook", **extra}
        self.lista.append(e)
        return e


def col(eventos, ahora=600, **kw):
    return colisiones.calcular(eventos, PERSONAS, ts(ahora), **kw)


class Nivel1(unittest.TestCase):
    def test_dos_personas_mismo_fichero_amarillo_en_ambas(self):
        ev = Eventos()
        ev(0, "ana", "arbol", rutas=["web/App.jsx", "motor/a.py"])
        ev(10, "bea", "edicion", rutas=["web/App.jsx"])
        c, _ = col(ev.lista)
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["id"], "1:ana+bea")
        self.assertEqual((c[0]["nivel"], c[0]["gravedad"], c[0]["personas"], c[0]["rutas"]),
                         ("1", "amarillo", ["ana", "bea"], ["web/App.jsx"]))
        self.assertEqual(c[0]["observado_en"], ts(10))          # cuando la tuvieron las dos

    def test_mayusculas_y_barras_son_el_mismo_fichero(self):
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=["Web\\App.jsx"])
        ev(5, "bea", "arbol", rutas=["web/app.jsx"])
        c, _ = col(ev.lista)
        self.assertEqual(len(c), 1)
        self.assertEqual(len(c[0]["rutas"]), 1)

    def test_misma_persona_nunca_colisiona(self):
        """Criterio 6: dos workers de la misma persona, en ficheros distintos y en el mismo."""
        ev = Eventos()
        ev(0, "ana", "edicion", papel="worker", agente="w1", worktree=".claude/worktrees/agent-w1", rutas=["web/a.js"])
        ev(1, "ana", "edicion", papel="worker", agente="w2", worktree=".claude/worktrees/agent-w2", rutas=["web/b.js"])
        ev(2, "ana", "edicion", papel="worker", agente="w2", worktree=".claude/worktrees/agent-w2", rutas=["web/a.js"])
        ev(3, "ana", "arbol", rutas=["web/a.js"])
        self.assertEqual(col(ev.lista)[0], [])

    def test_el_amarillo_acaba_con_el_siguiente_arbol_limpio(self):
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=["x.py"])
        ev(5, "bea", "edicion", rutas=["x.py"])
        self.assertEqual(len(col(ev.lista, 10)[0]), 1)
        ev(20, "bea", "arbol", rutas=[])                       # subió o deshizo: su árbol ya no lo tiene
        self.assertEqual(col(ev.lista, 30)[0], [])

    def test_worker_cuenta_hasta_su_fin(self):
        ev = Eventos()
        ev(0, "ana", "edicion", papel="worker", agente="w1", worktree=".claude/worktrees/agent-w1", rutas=["x.py"])
        ev(5, "bea", "edicion", rutas=["x.py"])
        self.assertEqual(len(col(ev.lista, 10)[0]), 1)
        ev(20, "ana", "worker.fin", papel="worker", agente="w1", worktree=".claude/worktrees/agent-w1")
        self.assertEqual(col(ev.lista, 30)[0], [])

    def test_ruido_y_carpetas_no_cuentan(self):
        ev = Eventos()
        ev(0, "ana", "arbol", rutas=[".claude/worktrees/agent-1/x.py", "nuevo/"])
        ev(5, "bea", "arbol", rutas=[".claude/worktrees/agent-1/x.py", "nuevo/"])
        self.assertEqual(col(ev.lista)[0], [])

    def test_hackathon_si_cuenta(self):
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=[".hackathon/plan.md"])
        ev(5, "bea", "edicion", rutas=[".hackathon/plan.md"])
        self.assertEqual(len(col(ev.lista)[0]), 1)

    def test_agrupado_por_conjunto_de_personas(self):
        ev = Eventos()
        ev(0, "ana", "arbol", rutas=["a.py", "b.py", "c.py"])
        ev(1, "bea", "arbol", rutas=["a.py", "b.py"])
        ev(2, "carla", "arbol", rutas=["c.py"])
        c = {x["id"]: x["rutas"] for x in col(ev.lista)[0]}
        self.assertEqual(c, {"1:ana+bea": ["a.py", "b.py"], "1:ana+carla": ["c.py"]})

    def test_fuera_del_equipo_no_cuenta(self):
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=["x.py"])
        ev(5, "fuera", "edicion", rutas=["x.py"])
        self.assertEqual(col(ev.lista)[0], [])

    def test_el_nivel_2_tapa_al_1(self):
        ev = Eventos()
        ev(0, "ana", "arbol", rutas=["a.py", "b.py"])
        ev(1, "bea", "arbol", rutas=["a.py", "b.py"])
        c, _ = col(ev.lista, conflictos=[{"personas": ["bea", "ana"], "rutas": ["a.py"], "desde": ts(50)}])
        por_id = {x["id"]: x for x in c}
        self.assertEqual(por_id["2:ana+bea"]["gravedad"], "rojo")
        self.assertEqual(por_id["2:ana+bea"]["rutas"], ["a.py"])
        self.assertEqual(por_id["1:ana+bea"]["rutas"], ["b.py"])


AUTORIDAD = """# Autoridad
## Por dueño

### Persona A (@Ana) · `motor/`, `docs/`, `arranca.py`
| Tema | Nivel | Ejemplos |
|---|---|---|
| Implementación interna de `motor/` | Agente solo | … |
| `docs/contratos.md`: motor → web (ficha de empresa) | Agentes + confirmación | añadir un campo |

### Persona B (@bea) · `web/`
| Tema | Nivel | Ejemplos |
|---|---|---|
| Implementación interna de `web/` | Agente solo | … |

### Persona C (sin usuario de GitHub) · `pitch/`
| Tema | Nivel | Ejemplos |
|---|---|---|
| `docs/contratos.md`: guion del pitch | Agentes + confirmación | … |

## Siempre solo humano
- Enfoque.
"""

CONTRATOS = """# Contratos

## motor → web: ficha de empresa

La produce el motor en `GET /api/ficha` y la consume la web. (decisión)

Vive en: `motor/api.py`, `web/src/api.js`

```json
## esto no es un bloque
```

## Datos de entrada

Vive en: `datos/`

## Guion del pitch

Vive en: pitch/guion.md

## Entrega del reto

Vive en: fuera del repo
"""


class Contratos(unittest.TestCase):
    def test_bloques_y_vive_en(self):
        b = {x["nombre"]: x["rutas"] for x in contratos.bloques(CONTRATOS)}
        self.assertEqual(b, {"motor → web: ficha de empresa": ["motor/api.py", "web/src/api.js"],
                             "Datos de entrada": ["datos/"], "Guion del pitch": ["pitch/guion.md"],
                             "Entrega del reto": []})

    def test_duenos_por_fila_por_carpeta_y_sin_dueno(self):
        con, avisos = contratos.duenos(CONTRATOS, AUTORIDAD)
        d = {x["nombre"]: (x["dueno"], x["con_github"]) for x in con}
        self.assertEqual(d["motor → web: ficha de empresa"], ("ana", True))     # por su fila
        self.assertEqual(d["Guion del pitch"], ("Persona C", False))             # por su fila, sin GitHub
        self.assertNotIn("Datos de entrada", d)                                  # datos/ no es de nadie
        self.assertNotIn("Entrega del reto", d)
        self.assertEqual(len(avisos), 2)

    def test_por_carpeta_cuando_no_hay_fila(self):
        aut = AUTORIDAD.replace("| `docs/contratos.md`: motor → web (ficha de empresa) | Agentes + confirmación | añadir un campo |\n", "")
        con, _ = contratos.duenos("## Ficha\nVive en: motor/api.py\n", aut)
        self.assertEqual(con[0]["dueno"], "ana")

    def test_dos_candidatas_sin_dueno(self):
        aut = AUTORIDAD.replace("| Implementación interna de `web/` | Agente solo | … |",
                                "| `docs/contratos.md`: motor → web | Agentes + confirmación | … |")
        con, avisos = contratos.duenos(CONTRATOS, aut)
        self.assertNotIn("motor → web: ficha de empresa", [x["nombre"] for x in con])
        self.assertTrue(any("más de una persona" in a for a in avisos))

    def test_nivel3_por_ruta_y_por_bloque(self):
        con, _ = contratos.duenos(CONTRATOS, AUTORIDAD)
        ev = Eventos()
        ev(0, "bea", "edicion", rutas=["motor/api.py"])
        c = [x for x in col(ev.lista, contratos=con)[0] if x["nivel"] == "3"]
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["personas"], ["bea", "ana", "carla"])            # quien toca, dueño, resto
        self.assertEqual((c[0]["gravedad"], c[0]["contrato"], c[0]["rutas"]),
                         ("rojo", "motor → web: ficha de empresa", ["motor/api.py"]))
        ev2 = Eventos()
        ev2(0, "carla", "arbol", rutas=["docs/contratos.md"], datos={"contratos": ["motor → web: ficha de empresa"]})
        c = [x for x in col(ev2.lista, contratos=con)[0] if x["nivel"] == "3"]
        self.assertEqual([(x["id"], x["rutas"]) for x in c],
                         [("3:motor web ficha de empresa:carla", ["docs/contratos.md"])])

    def test_el_dueno_no_se_avisa_a_si_mismo(self):
        con, _ = contratos.duenos(CONTRATOS, AUTORIDAD)
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=["motor/api.py"])
        ev(1, "ana", "arbol", rutas=["docs/contratos.md"], datos={"contratos": ["motor → web: ficha de empresa"]})
        self.assertEqual([x for x in col(ev.lista, contratos=con)[0] if x["nivel"] == "3"], [])

    def test_dueno_sin_github(self):
        con, _ = contratos.duenos(CONTRATOS, AUTORIDAD)
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=["pitch/guion.md"])
        c = [x for x in col(ev.lista, contratos=con)[0] if x["nivel"] == "3"]
        self.assertEqual(c[0]["personas"], ["ana", "bea", "carla"])             # sin «Persona C»: no está en el equipo


class Reservas(unittest.TestCase):
    def test_vigente_vencida_y_liberada(self):
        ev = Eventos()
        r = ev(0, "ana", "reserva", rutas=["web/"], datos={"ttl_s": 60, "modo": "compartida"})
        r["fuente"] = "mcp"
        _, res = col(ev.lista, 30)
        self.assertEqual([(x["id"], x["rutas"], x["persona"], x["hasta"]) for x in res], [(r["id"], ["web/"], "ana", ts(60))])
        self.assertEqual(col(ev.lista, 61)[1], [])                               # vencida
        ev(10, "bea", "liberacion", datos={"reserva": r["id"]})                 # otra persona no la libera
        self.assertEqual(len(col(ev.lista, 30)[1]), 1)
        ev(20, "ana", "liberacion", datos={"reserva": r["id"]})
        self.assertEqual(col(ev.lista, 30)[1], [])

    def test_en_estado_json_solo_con_reservas(self):
        ev = Eventos()
        ev(0, "ana", "edicion", rutas=["x.py"])
        e = calcular([], {}, ev.lista, PERSONAS, ts(10))
        self.assertNotIn("reservas", e)
        ev(5, "ana", "reserva", rutas=["x.py"], datos={"ttl_s": 900})
        e = calcular([], {}, ev.lista, PERSONAS, ts(10))
        self.assertEqual(len(e["reservas"]), 1)


if __name__ == "__main__":
    unittest.main()
