"""K-103 (R-36, ADR-0013; api.md §11.4): la ruta crítica de hkos/ruta.py, con su tabla de casos, los tres momentos de G14
y los casos de la cadena de cada persona (decisión 3B). Cada salida se valida contra $defs/vista_ruta de
estado.schema.json (con el validador de M8b y, si está, con jsonschema), y cada entrada, contra estado.schema.json.
Sin red, sin git y con `ahora` como parámetro.

Uso: uv run --no-project --with "jsonschema[format-nongpl]" -m unittest hkos/pruebas/test_ruta.py -v
"""
import copy
import json
import math
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(HKOS)
sys.path.insert(0, HKOS)
from compilar import leer_plan  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha, iso  # noqa: E402
from ruta import calcular, firma  # noqa: E402

try:
    import jsonschema
except ImportError:
    jsonschema = None

CONTRATOS = os.path.join(KIT, "docs", "hackathon-os", "contratos")
CARPETA_G14 = os.path.join(KIT, "evals", "coordinacion", "simulador", "guiones", "g14")
MADRID = timezone(timedelta(hours=2))          # Europe/Madrid en septiembre (CEST), como lo resuelve el relay
T0 = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)    # sáb 19 sep, 10:00 en Madrid
OBS = "2026-09-18T17:00:00Z"                    # el commit de equipo.md y plan.md en origin/main
TIPOS_DE_HECHO = {"plazo_pasado", "parada", "no_cerrada", "sin_senales", "ciclo"}


class _Vista(Esquema):
    def error(self, valor):
        return self._error({"$ref": "#/$defs/vista_ruta"}, valor, "")


VISTA, ESTADO = _Vista("estado.schema.json"), Esquema("estado.schema.json")


def _jsonschema():
    """El validador de jsonschema para $defs/vista_ruta, si hay uno con Draft 2020-12 y formatos (como test_esquemas)."""
    v = getattr(jsonschema, "Draft202012Validator", None)
    if not hasattr(v, "FORMAT_CHECKER"):
        return None
    try:
        if v({"format": "date-time"}, format_checker=v.FORMAT_CHECKER).is_valid("ayer"):
            return None
        with open(os.path.join(CONTRATOS, "estado.schema.json"), encoding="utf-8") as f:
            raiz = json.load(f)
        return v({"$schema": raiz["$schema"], "$defs": raiz["$defs"], "$ref": "#/$defs/vista_ruta"},
                 format_checker=v.FORMAT_CHECKER)
    except Exception:
        return None


JSONSCHEMA = _jsonschema()


def m(n):
    """T0 + n minutos, con el desfase de Madrid (como deja las horas el relay)."""
    return (T0 + timedelta(minutes=n)).astimezone(MADRID).isoformat()


def declarada(valor, texto, donde="equipo.md", motivo=None, **extra):
    return dict({"valor": valor, "texto": texto, "motivo": motivo, "donde": donde, "fuente": "git",
                 "observado_en": OBS, "declarado": True}, **extra)


def dato(valor, fuente="git", obs=OBS):
    return {"valor": valor, "fuente": fuente, "observado_en": obs, "declarado": True}


def descanso(persona, desde, hasta, texto=None, motivo=None):
    return {"persona": persona, "desde": desde, "hasta": hasta, "texto": texto or f"- {persona or 'Todos'}: …",
            "motivo": motivo, "fuente": "git", "observado_en": OBS, "declarado": True}


def ruta_de(entrega=240, **kw):
    """El bloque `ruta` de estado.json: Inicio vie 19:00 y Entrega a T0 + `entrega` minutos."""
    r = {"equipo": dato("ok"), "zona": dato("Europe/Madrid"),
         "inicio": declarada("2026-09-18T19:00:00+02:00", "2026-09-18 19:00 (Europe/Madrid)"),
         "entrega": declarada(m(entrega), "entrega") if entrega is not None else None,
         "otras_entregas": [], "hitos": [], "descansos": []}
    r.update(kw)
    return r


def tarea(tid, dueno, estado, orden, franja=None, primera=None, hecha=None, deps=(), titulo=None, fuente=None,
          motivo=None, declarado=None, motivo_franja="sin_plazo"):
    """Una tarea de estado.json con lo de K-104. franja = (desde, hasta[, compartida]) en minutos desde T0; su Hasta
    es el final de la franja. Sin franja, el Hasta va sin resolver con `motivo`."""
    fuente = fuente or {"publicada": "git", "lista": "derivado", "pendiente": "github", "reclamada": "mcp",
                        "cerrada": "github"}.get(estado, "hook")
    hasta_v = m(franja[1]) if franja else None
    t = {"id": tid, "titulo": titulo or f"Tarea {tid}", "dueno": dueno, "depende_de": list(deps),
         "estado": {"valor": estado, "fuente": fuente, "observado_en": m(hecha if hecha is not None else -1)},
         "declarado": declarado,
         "hasta": {"valor": hasta_v, "texto": "sáb" if hasta_v else "hora por confirmar",
                   "motivo": None if hasta_v else (motivo or "por_confirmar"), "fuente": "git", "observado_en": OBS,
                   "declarado": True},
         "franja": {"valor": None, "motivo": motivo_franja, "fuente": "derivado", "observado_en": OBS, "declarado": True},
         "orden_plan": dato(orden) if orden is not None else None,
         "historia": {"primera_senal": m(primera) if primera is not None else None,
                      "hecha_en": m(hecha) if hecha is not None else None, "trabajo_nuevo_desde": None,
                      "fuente": "derivado", "observado_en": m(-1)}}
    if t["orden_plan"] is None:
        del t["orden_plan"]
    if franja:
        desde, fin = franja[0], franja[1]
        compartida = franja[2] if len(franja) > 2 else 1
        t["franja"]["valor"] = {"desde": m(desde), "hasta": m(fin), "compartida": compartida,
                                "min": math.ceil((fin - desde) / compartida)}
        t["franja"]["motivo"] = None
    return t


def ana(ritmos=(30, 60, 90)):
    """Ana: tres hechas medidas (franjas de 60 min: 50 %, 100 % y 150 % con los minutos por defecto) y dos abiertas
    seguidas en su sección del plan, T04 y T05, de 60 min de franja cada una."""
    salida, inicio = [], -400
    for i, dur in enumerate(ritmos):
        salida.append(tarea(f"T0{i + 1}", "ana", "publicada", i + 1, franja=(-180 + 60 * i, -120 + 60 * i),
                            primera=inicio, hecha=inicio + dur))
        inicio += dur + 10
    return salida + [tarea("T04", "ana", "lista", 4, franja=(0, 60)), tarea("T05", "ana", "lista", 5, franja=(60, 120))]


def luis(n=3, abiertas=True):
    """Luis: n hechas al 100 % y, si `abiertas`, T12 (60 min de franja)."""
    salida = [tarea(f"T2{i}", "luis", "publicada", i + 1, franja=(-300 + 60 * i, -240 + 60 * i), primera=-300 + 60 * i,
                    hecha=-240 + 60 * i) for i in range(n)]
    if abiertas:
        salida.append(tarea("T12", "luis", "lista", n + 1, franja=(0, 60)))
    return salida


PERSONAS = [{"persona": "ana", "nombre": "Ana", "ultima_senal": m(-1)},
            {"persona": "luis", "nombre": "Luis", "ultima_senal": m(-1)}]


def por_id(tareas, tid):
    return next(t for t in tareas if t["id"] == tid)


class Base(unittest.TestCase):
    def corre(self, ruta, tareas, ahora=None, personas=PERSONAS, fuentes=None, **kw):
        """calcular(), con la entrada validada contra estado.schema.json y la salida contra $defs/vista_ruta."""
        ahora = ahora or iso(T0)
        estado = {"v": 1, "generado_en": ahora, "fuentes": {}, "personas": [], "tareas": tareas, "colisiones": [],
                  "ruta": ruta}
        self.assertIsNone(ESTADO.error(estado), "la entrada no tiene la forma de estado.schema.json")
        bloque = calcular(ruta, tareas, ahora, personas=personas, fuentes=fuentes, **kw)
        self.assertIsNone(VISTA.error(bloque), "la salida no valida contra $defs/vista_ruta")
        if JSONSCHEMA is not None:
            JSONSCHEMA.validate(bloque)
        return bloque

    def hechos(self, b, tipo):
        return [h for h in b["hechos"] if h["tipo"] == tipo]


class Tabla(Base):
    """La tabla de casos de K-103, en el orden de «Hecho cuando»."""

    def test_con_estimacion_rango_margen_base_y_cadena(self):
        b = self.corre(ruta_de(240), ana())
        self.assertEqual(b["veredicto"], {"valor": "a_tiempo", "motivos": [], "gravedad": "ninguna",
                                          "fuente": "derivado", "observado_en": iso(T0)})
        # Rango, nunca una sola hora: T04 y T05 seguidas, al 50 % (60 min) y al 150 % (180 min).
        self.assertEqual(b["estimacion"], {"temprano": iso(T0 + timedelta(minutes=60)),
                                           "tarde": iso(T0 + timedelta(minutes=180)), "margen_min": 60,
                                           "margen_max": 180})
        self.assertEqual(b["base"]["minimo"], 3)
        self.assertEqual(b["base"]["desde"], m(-370))
        self.assertEqual([(p["persona"], p["n"], p["ritmo_min"], p["ritmo_max"]) for p in b["base"]["personas"]],
                         [("ana", 3, 50, 150)])
        self.assertEqual([(e["tarjeta"]["id"], e["por"], e["fin_temprano"], e["fin_tarde"]) for e in b["cadena"]],
                         [("T04", "inicio", iso(T0 + timedelta(minutes=30)), iso(T0 + timedelta(minutes=90))),
                          ("T05", "orden_del_plan", iso(T0 + timedelta(minutes=60)), iso(T0 + timedelta(minutes=180)))])
        self.assertEqual(b["resumen"], "ruta: estimación a tiempo · fin 11:00–13:00 · entrega sáb 14:00")
        self.assertEqual((b["objetivo"]["valor"], b["objetivo"]["donde"]), (m(240), "equipo.md"))
        self.assertEqual((b["hechos"], b["sin_plazo"], b["fuera_de_entrega"], b["otras_entregas"]), ([], [], [], []))

    def test_veredicto_en_sus_fronteras(self):
        # temprano = T0 + 60, tarde = T0 + 180: a tiempo si tarde ≤ entrega; justo si temprano ≤ entrega < tarde; no
        # llega si entrega < temprano. «No llega» es ámbar: el rojo es solo para hechos.
        casos = [(180, "a_tiempo", "ninguna", 0, 120), (179, "justo", "ambar", -1, 119),
                 (60, "justo", "ambar", -120, 0), (59, "no_llega", "ambar", -121, -1)]
        for entrega, valor, gravedad, mmin, mmax in casos:
            with self.subTest(entrega=entrega):
                b = self.corre(ruta_de(entrega), ana())
                self.assertEqual((b["veredicto"]["valor"], b["veredicto"]["gravedad"]), (valor, gravedad))
                self.assertEqual((b["estimacion"]["margen_min"], b["estimacion"]["margen_max"]), (mmin, mmax))
                self.assertEqual(firma(b), valor)
                self.assertTrue(b["resumen"].startswith(
                    "ruta: estimación " + {"a_tiempo": "a tiempo", "justo": "justo", "no_llega": "no llega"}[valor]))

    def test_sin_entrega_ilegible_sin_resolver_y_dos_horas(self):
        casos = {
            "sin Entrega:": (ruta_de(None), "sin_entrega", False),
            "equipo.md sin fichero": (ruta_de(None, equipo=dato("sin fichero")), "sin_entrega", False),
            "equipo.md mal formado": (ruta_de(240, equipo=dato("mal formado")), "sin_entrega", False),
            "sin dato": (ruta_de(entrega=None) | {"entrega": declarada(None, "—", motivo="sin_dato")}, "sin_entrega", True),
            "sin zona": (ruta_de() | {"entrega": declarada(None, "dom 10:00", motivo="sin_zona")}, "sin_entrega", True),
            "formato": (ruta_de() | {"entrega": declarada(None, "el domingo", motivo="formato")}, "sin_entrega", True),
            "dos horas": (ruta_de() | {"entrega": declarada(None, "10:00 (cierre 11:00)", motivo="dos_horas")},
                          "entrega_doble", True),
        }
        for nombre, (ruta, motivo, con_objetivo) in casos.items():
            with self.subTest(nombre):
                b = self.corre(ruta, ana())
                self.assertEqual(b["veredicto"]["valor"], "sin_estimacion")
                self.assertEqual(b["veredicto"]["motivos"], [motivo])
                self.assertEqual(b["veredicto"]["gravedad"], "gris")
                self.assertIsNone(b["estimacion"])
                self.assertEqual(b["objetivo"] is not None, con_objetivo)
                self.assertEqual(b["resumen"], "ruta: sin estimación (" +
                                 ("dos horas de entrega" if motivo == "entrega_doble" else "sin hora de entrega") + ")")
                self.assertTrue(all(e["fin_tarde"] is None for e in b["cadena"]))
        # Con más de un motivo, todos, en el orden del contrato; el resumen dice el primero.
        b = self.corre(ruta_de(None), ana()[:2] + ana()[3:])
        self.assertEqual(b["veredicto"]["motivos"], ["sin_entrega", "pocos_datos"])
        self.assertEqual(b["resumen"], "ruta: sin estimación (sin hora de entrega)")

    def test_otras_entregas_al_lado_con_estimacion(self):
        hito = declarada(m(300), "dom 11:00", donde="plan.md", nombre="Entrega final")
        nota = declarada(m(250), "entregad a las 10:10", donde="criterios.md")
        igual = declarada(iso(T0 + timedelta(minutes=240)), "sáb 14:00", donde="plan.md", nombre="Entrega")
        rota = declarada(None, "hora por confirmar", donde="plan.md", motivo="por_confirmar", nombre="Entrega (pitch)")
        b = self.corre(ruta_de(240, otras_entregas=[hito, nota, igual, rota], hitos=[hito, igual]), ana())
        # La de igual hora (escrita en UTC) coincide y no sale; las demás salen al lado y no quitan la estimación.
        self.assertEqual(b["otras_entregas"], [hito, nota, rota])
        self.assertEqual(b["veredicto"]["valor"], "a_tiempo")
        self.assertIsNotNone(b["estimacion"])
        self.assertEqual(b["resumen"], "ruta: estimación a tiempo · fin 11:00–13:00 · entrega sáb 14:00 · "
                                       "otra entrega: dom 11:00 (plan.md)")
        self.assertEqual([h["hito"]["nombre"] for h in b["hitos"]], ["Entrega final", "Entrega"])
        # Con «(confirmar)», hay estimación, marcada.
        r = ruta_de(240)
        r["entrega"]["confirmar"] = True
        b = self.corre(r, ana())
        self.assertTrue(b["objetivo"]["confirmar"])
        self.assertEqual(b["veredicto"]["valor"], "a_tiempo")
        self.assertIsNotNone(b["estimacion"])
        self.assertEqual(b["resumen"], "ruta: estimación a tiempo · fin 11:00–13:00 · entrega sáb 14:00 (confirmar)")

    def test_ciclo_en_las_dependencias(self):
        tareas = ana()
        por_id(tareas, "T04")["depende_de"] = ["T12"]
        tareas += luis()
        por_id(tareas, "T12")["depende_de"] = ["T04"]
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual(b["veredicto"]["motivos"], ["ciclo"])
        self.assertIsNone(b["estimacion"])
        self.assertEqual(self.hechos(b, "ciclo"), [{"tipo": "ciclo", "gravedad": "gris", "ciclo": ["T04", "T12", "T04"],
                                                    "fuente": "derivado", "observado_en": iso(T0), "viejo": False}])
        self.assertEqual(b["resumen"], "ruta: sin estimación (ciclo T04 → T12 → T04)")

    def test_tarea_abierta_sin_franja_sin_plazo_nunca_a_tiempo(self):
        tareas = ana()
        tareas[-1] = tarea("T05", "ana", "lista", 5, motivo="por_confirmar")
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual(b["sin_plazo"], [{"tarea": "T05", "motivo": "por_confirmar"}])
        self.assertEqual(b["veredicto"]["valor"], "sin_estimacion")
        self.assertEqual(b["veredicto"]["motivos"], ["sin_plazo"])
        self.assertIsNone(b["estimacion"])
        self.assertEqual(b["resumen"], "ruta: sin estimación (sin plazo: T05)")
        self.assertEqual(self.hechos(b, "plazo_pasado"), [])
        # Con Hasta resuelto pero sin franja (no es posterior a la anterior), el motivo es el de la franja.
        tareas[-1] = tarea("T05", "ana", "lista", 5, motivo_franja="orden")
        tareas[-1]["hasta"].update(valor=m(60), texto="sáb 11:00", motivo=None)
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual(b["sin_plazo"], [{"tarea": "T05", "motivo": "orden"}])
        # Sin plazo en las hechas y en las que no cuentan no quita nada.
        tareas = ana()
        tareas[0]["franja"] = {"valor": None, "motivo": "sin_inicio", "fuente": "derivado", "observado_en": OBS,
                               "declarado": True}
        tareas += [tarea("T06", "ana", "lista", 6, titulo="Si sobra tiempo: modo oscuro")]
        b = self.corre(ruta_de(240), tareas + luis())
        self.assertEqual(b["sin_plazo"], [])
        self.assertEqual(b["veredicto"]["motivos"], ["pocos_datos"])   # T01 sin franja: ya no se mide

    def test_plazo_vencido_rojo_y_lo_que_arrastra(self):
        tareas = ana()
        tareas[3] = tarea("T04", "ana", "en_curso", 4, franja=(-70, -10), primera=-60)
        tareas += luis()
        por_id(tareas, "T12")["depende_de"] = ["T05"]
        b = self.corre(ruta_de(600), tareas)
        pasados = self.hechos(b, "plazo_pasado")
        # T05 sigue a T04 por el orden del plan (sin «Quién espera a quién»); T12 espera a T05 por depende_de.
        self.assertEqual(pasados, [{"tipo": "plazo_pasado", "gravedad": "rojo", "tarea": "T04", "persona": "ana",
                                    "plazo": m(-10), "arrastra": ["T05", "T12"], "fuente": "derivado",
                                    "observado_en": iso(T0), "viejo": False}])
        self.assertEqual([h["tipo"] for h in b["hechos"] if h["gravedad"] == "rojo"], ["plazo_pasado"])
        self.assertNotEqual(b["veredicto"]["gravedad"], "rojo")
        self.assertTrue(b["resumen"].endswith(" · T04: plazo pasado 09:50"))
        # Con dos pasados, el primero por plazo y «y N más».
        por_id(tareas, "T12")["franja"]["valor"].update(desde=m(-60), hasta=m(-5), min=55)
        por_id(tareas, "T12")["hasta"]["valor"] = m(-5)
        b = self.corre(ruta_de(600), tareas)
        self.assertEqual([h["tarea"] for h in self.hechos(b, "plazo_pasado")], ["T04", "T12"])
        self.assertTrue(b["resumen"].endswith(" · T04: plazo pasado 09:50 y 1 más"))
        # Una hecha con el plazo pasado no es un hecho.
        b = self.corre(ruta_de(600), ana())
        self.assertEqual(self.hechos(b, "plazo_pasado"), [])

    def test_parada_y_no_cerrada_ambar(self):
        tareas = ana()
        tareas[3] = tarea("T04", "ana", "parada", 4, franja=(0, 60), primera=-30, fuente="derivado")
        tareas[4] = tarea("T05", "ana", "no_cerrada", 5, franja=(60, 120), primera=-20)
        b = self.corre(ruta_de(600), tareas)
        self.assertEqual([(h["tipo"], h["gravedad"], h["tarea"]) for h in b["hechos"]],
                         [("parada", "ambar", "T04"), ("no_cerrada", "ambar", "T05")])

    def test_pocos_datos_sin_hora_prevista_n_de_3(self):
        marta = [tarea("T31", "marta", "publicada", 1, franja=(-300, -240), primera=-300, hecha=-250)]
        b = self.corre(ruta_de(240), ana() + luis(n=2) + marta)
        self.assertEqual(b["veredicto"], {"valor": "sin_estimacion", "motivos": ["pocos_datos"], "gravedad": "gris",
                                          "fuente": "derivado", "observado_en": iso(T0)})
        self.assertIsNone(b["estimacion"])
        self.assertEqual([(p["persona"], p["n"], p["ritmo_min"], p["ritmo_max"]) for p in b["base"]["personas"]],
                         [("ana", 3, 50, 150), ("luis", 2, None, None), ("marta", 1, None, None)])
        # Marta no tiene nada abierto: no cuenta para «pocos datos».
        self.assertEqual(b["resumen"], "ruta: sin estimación (pocos datos: @luis 2 de 3)")
        self.assertTrue(b["cadena"] and all(e["fin_temprano"] is None and e["fin_tarde"] is None for e in b["cadena"]))
        # Con la tercera medida de Luis, hay cifra.
        b = self.corre(ruta_de(240), ana() + luis(n=3) + marta)
        self.assertEqual(b["veredicto"]["valor"], "a_tiempo")
        self.assertEqual(b["base"]["desde"], m(-370))

    def test_cadena_de_cada_persona_y_la_mas_larga(self):
        tareas = ana() + luis()
        tareas.append(tarea("T13", "luis", "lista", 5, franja=(60, 150), deps=["T05"]))
        b = self.corre(ruta_de(600), tareas)
        # T13 espera a T05 (depende_de), que va detrás de T04 (orden del plan, inferido): la más larga. T13 también va
        # detrás de T12 (la cadena de Luis), que acaba antes.
        self.assertEqual([(e["tarjeta"]["id"], e["por"]) for e in b["cadena"]],
                         [("T04", "inicio"), ("T05", "orden_del_plan"), ("T13", "depende_de")])
        self.assertEqual(b["cadena"][-1]["fin_tarde"], b["estimacion"]["tarde"])
        self.assertEqual(b["estimacion"]["tarde"], iso(T0 + timedelta(minutes=270)))
        # Sin estimación, la que lleva al Hasta resuelto más tardío.
        b = self.corre(ruta_de(None), tareas)
        self.assertEqual([(e["tarjeta"]["id"], e["por"], e["fin_tarde"]) for e in b["cadena"]],
                         [("T04", "inicio", None), ("T05", "orden_del_plan", None), ("T13", "depende_de", None)])
        self.assertEqual(b["cadena"][0]["hasta"]["valor"], m(60))
        self.assertEqual(b["cadena"][0]["franja"]["valor"]["min"], 60)

    def test_si_y_si_da_tiempo_fuera_de_la_entrega(self):
        tareas = ana()
        tareas[4:4] = [tarea("T06", "ana", "lista", 5, titulo="Si Embat pide validación: medir la estabilidad"),
                       tarea("T07", "ana", "lista", 6, titulo="[SI DA TIEMPO] Modo oscuro"),
                       tarea("T08", "ana", "lista", 7, titulo="si sobra, [si da tiempo] otra")]
        tareas[-1]["orden_plan"]["valor"] = 8
        tareas.append(tarea("T09", "ana", "publicada", 9, titulo="Sistema de colas", franja=(-30, -20), primera=-30,
                            hecha=-25))
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual(b["fuera_de_entrega"], [{"tarea": "T06", "motivo": "condicional"},
                                                {"tarea": "T07", "motivo": "si_da_tiempo"},
                                                {"tarea": "T08", "motivo": "condicional"}])
        # No son «sin plazo», no retrasan el fin y la cadena de Ana se las salta (T04 → T05).
        self.assertEqual(b["sin_plazo"], [])
        self.assertEqual(b["veredicto"]["valor"], "a_tiempo")
        self.assertEqual(b["estimacion"]["tarde"], iso(T0 + timedelta(minutes=180)))
        self.assertEqual([(e["tarjeta"]["id"], e["por"]) for e in b["cadena"]], [("T04", "inicio"), ("T05", "orden_del_plan")])
        self.assertEqual(b["base"]["personas"][0]["n"], 4)       # «Sistema…» cuenta y se mide

    def test_descansos_ni_en_el_ritmo_ni_en_el_fin_ni_sin_senales(self):
        # Ritmo: T03 (90 min) con 30 min de descanso de Ana dentro: 60 min de 60, 100 %.
        tareas = ana()
        r = ruta_de(600, descansos=[descanso("@ana", m(-260), m(-230))])
        b = self.corre(r, tareas)
        self.assertEqual((b["base"]["personas"][0]["ritmo_min"], b["base"]["personas"][0]["ritmo_max"]), (50, 100))
        self.assertEqual(b["descansos"], r["descansos"])
        # Fin previsto: un descanso de todos de T0+30 a T0+90 se salta (temprano 60 → 120; tarde 180 → 240).
        r = ruta_de(600, descansos=[descanso(None, m(30), m(90), texto="- Todos: sáb 10:30–11:30")])
        b = self.corre(r, tareas)
        self.assertEqual((b["estimacion"]["temprano"], b["estimacion"]["tarde"]),
                         (iso(T0 + timedelta(minutes=120)), iso(T0 + timedelta(minutes=240))))
        # El de otra persona y el que no se entiende no cuentan para Ana (el segundo se enseña igual).
        malo = descanso("Ana", None, None, texto="- Ana: la siesta", motivo="formato")
        r = ruta_de(600, descansos=[descanso("@luis", m(0), m(600)), malo])
        b = self.corre(r, tareas)
        self.assertEqual(b["estimacion"]["tarde"], iso(T0 + timedelta(minutes=180)))
        self.assertIn(malo, b["descansos"])
        # Sin señales desde hace 2 h, pero en su descanso (por su nombre): no sale «sin señales».
        personas = [{"persona": "ana", "nombre": "Ana", "ultima_senal": m(-120)}]
        b = self.corre(ruta_de(600, descansos=[descanso("Ana", m(-100), m(30))]), tareas, personas=personas)
        self.assertEqual(self.hechos(b, "sin_senales"), [])
        b = self.corre(ruta_de(600), tareas, personas=personas)
        self.assertEqual(len(self.hechos(b, "sin_senales")), 1)

    def test_sin_senales_gris_nunca_lenta(self):
        personas = [{"persona": "ana", "nombre": "Ana", "ultima_senal": m(-1)},
                    {"persona": "luis", "nombre": "Luis", "ultima_senal": m(-120)}]
        con = self.corre(ruta_de(240), ana() + luis())
        sin = self.corre(ruta_de(240), ana() + luis(), personas=personas)
        self.assertEqual(self.hechos(sin, "sin_senales"), [{
            "tipo": "sin_senales", "gravedad": "gris", "persona": "luis", "desde": m(-120), "fuente": "derivado",
            "observado_en": iso(T0), "viejo": False}])
        self.assertEqual([h["tipo"] for h in sin["hechos"] if h.get("persona") == "luis"], ["sin_senales"])
        self.assertTrue({h["tipo"] for h in sin["hechos"]} <= TIPOS_DE_HECHO)
        # No cambia ni la estimación ni el veredicto: no es lentitud.
        self.assertEqual((sin["veredicto"], sin["estimacion"]), (con["veredicto"], con["estimacion"]))
        # Sin ninguna señal (no está en personas): sin señales, sin hora.
        b = self.corre(ruta_de(240), ana() + luis(), personas=PERSONAS[:1])
        self.assertEqual([(h["persona"], h["desde"]) for h in self.hechos(b, "sin_senales")], [("luis", None)])
        # Sin tareas abiertas, no: no hay nada que esperar de quien no tiene trabajo.
        b = self.corre(ruta_de(240), ana() + luis(abiertas=False), personas=personas)
        self.assertEqual(self.hechos(b, "sin_senales"), [])

    def test_cerrada_a_mano_hecha_para_la_ruta_no_medida(self):
        tareas = ana()
        tareas[2] = tarea("T03", "ana", "en_curso", 3, franja=(-60, -10), primera=-190,
                          declarado={"valor": "cerrada", "fuente": "github", "observado_en": m(-5), "declarado": True})
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual(self.hechos(b, "plazo_pasado"), [])    # su plazo pasó, pero está hecha para la ruta
        self.assertNotIn("T03", [e["tarjeta"]["id"] for e in b["cadena"]])
        self.assertEqual(b["base"]["personas"][0]["n"], 2)      # no se mide: pocos datos
        self.assertEqual(b["veredicto"]["motivos"], ["pocos_datos"])
        # Una cerrada de verdad (publicada y luego cerrada, sin ⚑) sí se mide.
        tareas[2] = tarea("T03", "ana", "cerrada", 3, franja=(-60, 0), primera=-290, hecha=-200)
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual(b["base"]["personas"][0]["n"], 3)

    def test_dato_viejo(self):
        fuentes = {"relay": {"valor": "ok", "observado_en": m(-1), "viejo": False},
                   "github": {"valor": "ok", "observado_en": m(-30), "viejo": True},
                   "git": {"valor": "ok", "observado_en": m(-2), "viejo": False}}
        tareas = ana()
        tareas[3]["estado"]["fuente"] = "github"
        b = self.corre(ruta_de(240), tareas, fuentes=fuentes)
        self.assertTrue(b["viejo"])
        self.assertEqual(b["dato_mas_viejo"], m(-30))
        self.assertEqual([(e["tarjeta"]["id"], e["tarjeta"]["viejo"]) for e in b["cadena"]], [("T04", True), ("T05", False)])
        fuentes["github"] = {"valor": "no", "observado_en": m(-900), "viejo": False}    # sin GitHub (M8h)
        b = self.corre(ruta_de(240), tareas, fuentes=fuentes)
        self.assertFalse(b["viejo"])
        self.assertEqual(b["dato_mas_viejo"], m(-2))
        b = self.corre(ruta_de(240), tareas)
        self.assertEqual((b["viejo"], b["dato_mas_viejo"]), (False, None))

    def test_la_firma_es_solo_el_veredicto(self):
        antes = self.corre(ruta_de(240), ana())
        # Se mueve la hora estimada (pasan 5 min y T04 ya está en curso), el margen (otra entrega, aún a tiempo) y los
        # hechos (Luis sin señales): el veredicto, y con él la firma, no cambia.
        tareas = ana()
        tareas[3] = tarea("T04", "ana", "en_curso", 4, franja=(0, 60), primera=1)
        movidos = [
            self.corre(ruta_de(240), tareas, ahora=iso(T0 + timedelta(minutes=5))),
            self.corre(ruta_de(300), ana()),
            self.corre(ruta_de(240), ana() + luis(), personas=PERSONAS[:1]),
        ]
        for b in movidos:
            self.assertEqual(firma(b), firma(antes))
        self.assertNotEqual([b["estimacion"] for b in movidos[:2]], [antes["estimacion"]] * 2)
        self.assertNotEqual(movidos[2]["hechos"], antes["hechos"])
        self.assertNotEqual(firma(self.corre(ruta_de(100), ana())), firma(antes))

    def test_tarjetas_de_la_vista_y_trabajo_ya_hecho(self):
        tarjetas = {"T04": {"id": "T04", "titulo": "Cuatro", "dueno": "ana", "estado": "en_curso", "etiqueta": "en curso",
                            "fuente": "hook", "observado_en": m(-1), "depende_de": [], "bloquea_a": [], "espera": []}}
        tareas = ana()
        tareas[3] = tarea("T04", "ana", "en_curso", 4, franja=(0, 60), primera=-20)
        b = self.corre(ruta_de(240), tareas, tarjetas=tarjetas)
        self.assertEqual(b["cadena"][0]["tarjeta"], dict(tarjetas["T04"], viejo=False))
        # T04 lleva 20 min: le quedan 60 × 50 % − 20 = 10 y 60 × 150 % − 20 = 70 min.
        self.assertEqual([(e["fin_temprano"], e["fin_tarde"]) for e in b["cadena"]][0],
                         (iso(T0 + timedelta(minutes=10)), iso(T0 + timedelta(minutes=70))))


class CadenaDeCadaPersona(Base):
    """R3B (decisión 3B): la cadena de cada persona (sus filas, en orden) es una dependencia, aunque «Quién espera a
    quién» no diga nada. G14 no la ejercita (sus hechos usan solo depende_de), así que aquí se ve que cambia el
    veredicto, lo que arrastra un plazo pasado y el ciclo."""

    def al_100(self, dueno_t05="ana", con_orden=True):
        tareas = ana(ritmos=(60, 60, 60)) + luis(abiertas=False)
        por_id(tareas, "T05")["dueno"] = dueno_t05
        if not con_orden:
            for t in tareas:
                t.pop("orden_plan", None)
        return tareas

    def test_la_cadena_de_una_persona_cambia_el_veredicto(self):
        # T04 y T05, 60 min de franja cada una, ritmo 100 %, entrega a T0 + 90, sin depende_de.
        misma = self.corre(ruta_de(90), self.al_100())
        self.assertEqual(misma["veredicto"]["valor"], "no_llega")       # una detrás de otra: acaba a T0 + 120
        self.assertEqual(misma["estimacion"]["temprano"], iso(T0 + timedelta(minutes=120)))
        self.assertEqual([(e["tarjeta"]["id"], e["por"]) for e in misma["cadena"]], [("T04", "inicio"), ("T05", "orden_del_plan")])
        dos = self.corre(ruta_de(90), self.al_100(dueno_t05="luis"))
        self.assertEqual(dos["veredicto"]["valor"], "a_tiempo")         # en paralelo, cada una en su cadena
        sin_orden = self.corre(ruta_de(90), self.al_100(con_orden=False))
        self.assertEqual(sin_orden["veredicto"]["valor"], "a_tiempo")   # sin orden del plan, solo depende_de
        self.assertNotEqual(firma(misma), firma(dos))

    def test_un_plazo_pasado_arrastra_por_el_orden_del_plan(self):
        tareas = self.al_100()
        tareas[3] = tarea("T04", "ana", "en_curso", 4, franja=(-60, -1), primera=-50)
        b = self.corre(ruta_de(600), tareas)
        self.assertEqual(self.hechos(b, "plazo_pasado")[0]["arrastra"], ["T05"])
        for t in tareas:
            t.pop("orden_plan", None)
        b = self.corre(ruta_de(600), tareas)
        self.assertEqual(self.hechos(b, "plazo_pasado")[0]["arrastra"], [])

    def test_una_espera_hacia_atras_en_la_misma_persona_es_un_ciclo(self):
        # T04 «espera a» T05, pero T05 va después en su sección: con la cadena de la persona, un ciclo.
        tareas = self.al_100()
        por_id(tareas, "T04")["depende_de"] = ["T05"]
        b = self.corre(ruta_de(600), tareas)
        self.assertEqual(b["veredicto"]["motivos"], ["ciclo"])
        self.assertEqual(self.hechos(b, "ciclo")[0]["ciclo"], ["T04", "T05", "T04"])
        for t in tareas:
            t.pop("orden_plan", None)
        self.assertEqual(self.corre(ruta_de(600), tareas)["veredicto"]["motivos"], [])


# =================================================================================================================== G14
def _carga(nombre):
    with open(os.path.join(CARPETA_G14, nombre), encoding="utf-8") as f:
        return f.read()


HECHOS = json.loads(_carga("hechos.json"))
TABLA = json.loads(_carga("tareas.json"))
# La primera señal de las abiertas en curso (no está en hechos.json): la del guion, con t = 0 a las 17:00Z.
PRIMERAS = {"mitad bien": {"T08": "2026-09-19T08:55:30Z", "T17": "2026-09-19T08:00:30Z", "T25": "2026-09-19T09:35:30Z"},
            "mitad con riesgo": {"T04": "2026-09-19T09:10:30Z", "T17": "2026-09-19T08:00:30Z"}}
FUENTE = {"publicada": "git", "en_curso": "hook", "lista": "derivado", "pendiente": "github", "reclamada": "mcp"}
MOTIVO_HASTA = {"sin Inicio": "relativo_sin_inicio", "plazo sin resolver": "por_confirmar"}
MOTIVO_FUERA = {"empieza por «Si …»": "condicional", "lleva [SI DA TIEMPO]": "si_da_tiempo"}
POR_PERSONA = {"persona-a": "Persona A", "persona-b": "Persona B", "persona-c": "Persona C"}


def madrid(z):
    return fecha(z).astimezone(MADRID).isoformat() if z else None


def franjas_g14(filas, inicio):
    """Lo que hace K-104 (api.md §11.2, decisión 4A): del Hasta de la fila anterior de la persona con otro Hasta (o
    del inicio) al suyo, repartido entre las filas que lo heredan."""
    salida, i = {}, 0
    while i < len(filas):
        tid, persona, efectivo, valor = filas[i]
        if i == 0 or filas[i - 1][1] != persona:
            desde = inicio
        j = i + 1
        while j < len(filas) and filas[j][1] == persona and filas[j][2] == efectivo:
            j += 1
        bloque = filas[i:j]
        for b in bloque:
            if valor is None:
                salida[b[0]] = (None, "sin_plazo")
            elif desde is None:
                salida[b[0]] = (None, "sin_inicio")
            elif fecha(valor) <= fecha(desde):
                salida[b[0]] = (None, "orden")
            else:
                minutos = (fecha(valor) - fecha(desde)).total_seconds() / 60
                salida[b[0]] = ({"desde": madrid(desde), "hasta": madrid(valor), "compartida": len(bloque),
                                 "min": math.ceil(minutos / len(bloque))}, None)
        desde = valor if valor is not None else desde
        i = j
    return salida


def momento_g14(mo, t28=None):
    """(ruta, tareas, personas) de un momento de G14, con lo que dicen hechos.json, el plan y equipo.md de ese momento.
    t28: None (como está), «fuera» (con «Si …» delante) o «hasta» (con Hasta sáb 23:00)."""
    plan = leer_plan(_carga(os.path.basename(mo["plan.md"])), TABLA["personas"])
    obs_plan = mo["entrega"]["fichero_desde"]
    inicio = mo["inicio"]["valor"]
    plazos = copy.deepcopy(mo["plazos"])
    if t28 == "hasta":
        plazos["T28"].update(valor="2026-09-19T21:00:00Z", motivo=None, efectivo="sáb 23:00", hasta="sáb 23:00")
    filas = [(t["id"], t["dueno"], plazos[t["id"]]["efectivo"], plazos[t["id"]]["valor"]) for t in plan]
    franjas = franjas_g14(filas, inicio)
    hechas = {x["tarea"]: x for p in mo["base"].values() for x in p["hechas"]}
    orden, tareas = {}, []
    for t in plan:
        tid, estado = t["id"], mo["tareas"][t["id"]]
        orden[t["dueno"]] = orden.get(t["dueno"], 0) + 1
        pl, (fr, fr_motivo) = plazos[tid], franjas[tid]
        h = hechas.get(tid)
        titulo = ("Si no da tiempo: " + t["titulo"]) if tid == "T28" and t28 == "fuera" else t["titulo"]
        tareas.append({
            "id": tid, "titulo": titulo, "bloque": t["bloque"], "dueno": t["dueno"], "depende_de": t["depende_de"],
            "estado": {"valor": estado, "fuente": FUENTE[estado],
                       "observado_en": h["publicada_en"] if h else mo["ahora"]},
            "declarado": None,
            "hasta": {"valor": madrid(pl["valor"]), "texto": pl["efectivo"],
                      "motivo": None if pl["valor"] else MOTIVO_HASTA[pl["motivo"]], "fuente": "git",
                      "observado_en": obs_plan, "declarado": True},
            "franja": {"valor": fr, "motivo": fr_motivo, "fuente": "derivado", "observado_en": obs_plan,
                       "declarado": True},
            "orden_plan": dato(orden[t["dueno"]], obs=obs_plan),
            "historia": {"primera_senal": h["primera_senal"] if h else PRIMERAS.get(mo["nombre"], {}).get(tid),
                         "hecha_en": h["publicada_en"] if h else None, "trabajo_nuevo_desde": None,
                         "fuente": "derivado", "observado_en": mo["ahora"]}})
    ent = mo["entrega"]
    otras = [declarada(madrid(d["valor"]), d["texto"], donde="plan.md", nombre="Entrega final (pitch: hora por confirmar)")
             for d in ent["discrepancias"]]
    for o in otras:
        o["observado_en"] = obs_plan
    descansos = [descanso(p, madrid(f["desde"]), madrid(f["hasta"]), texto=f"- {POR_PERSONA[p]}: {f['texto']}",
                          motivo=None if f["desde"] else "sin_inicio")
                 for f in mo["descansos"]["filas"] for p in f["personas"]]
    ruta = {"equipo": dato("ok", obs=ent["fichero_desde"]), "zona": dato("Europe/Madrid", obs=ent["fichero_desde"]),
            "inicio": declarada(madrid(inicio), mo["inicio"]["texto"], motivo=None if inicio else "por_confirmar"),
            "entrega": declarada(madrid(ent["valor"]), ent["texto"]),
            "otras_entregas": otras,
            "hitos": otras + [declarada("2026-09-19T22:00:00+02:00", "sáb 22:00", donde="plan.md", nombre="Congelación")],
            "descansos": descansos}
    ahora = fecha(mo["ahora"])
    personas = [{"persona": p, "nombre": n,
                 "ultima_senal": mo["sin_senales"][p]["desde"] if p in mo["sin_senales"]
                 else iso(ahora - timedelta(minutes=1))} for p, n in POR_PERSONA.items()]
    return ruta, tareas, personas


class G14(Base):
    """Los tres momentos de G14 (evals/coordinacion/simulador/guiones/g14/hechos.json), con las entradas que dejaría el
    relay. Dos diferencias con hechos.json, por el contrato (api.md §11.4), que K-105 tiene que corregir allí:
      - en las dos mitades, T28 («hora por confirmar») es una abierta que cuenta sin franja: `sin_estimacion` con
        `sin_plazo`, no `a_tiempo` ni `no_llega`. Con T28 fuera de la entrega o con su Hasta, salen los de hechos.json;
      - en «inicio», sin Inicio no hay franjas y sin franja no hay medida: la base es 0 de 3 para las tres personas,
        no 2, 1 y 0 (el veredicto y sus motivos son los mismos)."""

    def momento(self, nombre, t28=None):
        mo = next(x for x in HECHOS["momentos"] if x["nombre"] == nombre)
        ruta, tareas, personas = momento_g14(mo, t28)
        return mo, self.corre(ruta, tareas, ahora=mo["ahora"], personas=personas)

    def comunes(self, mo, b):
        """Lo que hechos.json dice igual que el contrato, en cualquier momento."""
        self.assertEqual(b["objetivo"]["valor"], madrid(mo["entrega"]["valor"]))
        self.assertEqual([fecha(o["valor"]) for o in b["otras_entregas"]],
                         [fecha(d["valor"]) for d in mo["entrega"]["discrepancias"]])
        self.assertNotIn("sin_entrega", b["veredicto"]["motivos"])     # la discrepancia no bloquea
        self.assertEqual({x["tarea"]: x["motivo"] for x in b["sin_plazo"]},
                         {k: MOTIVO_HASTA[v] for k, v in mo["sin_plazo"].items()})
        self.assertEqual({x["tarea"]: x["motivo"] for x in b["fuera_de_entrega"]},
                         {k: MOTIVO_FUERA[v] for k, v in mo["no_cuentan"].items()})
        pasados = self.hechos(b, "plazo_pasado")
        self.assertEqual({h["tarea"]: fecha(h["plazo"]) for h in pasados},
                         {k: fecha(v["plazo"]) for k, v in mo["plazos_vencidos"].items()})
        en_riesgo = {h["tarea"] for h in pasados} | {t for h in pasados for t in h["arrastra"]}
        self.assertTrue(set(mo["en_riesgo"]) <= en_riesgo, set(mo["en_riesgo"]) - en_riesgo)
        self.assertEqual({h["persona"]: h["desde"] for h in self.hechos(b, "sin_senales")},
                         {p: x["desde"] for p, x in mo["sin_senales"].items()})
        for p in mo["sin_senales"]:                                     # nunca «va lenta»
            self.assertEqual([h["tipo"] for h in b["hechos"] if h.get("persona") == p], ["sin_senales"])
        self.assertTrue({h["tipo"] for h in b["hechos"]} <= TIPOS_DE_HECHO)
        self.assertEqual(len(b["descansos"]), 6)
        self.assertEqual(all(d["desde"] for d in b["descansos"]), mo["descansos"]["resueltos"])
        self.assertEqual(b["veredicto"]["valor"] == "a_tiempo" and bool(b["sin_plazo"]), False)

    def test_inicio(self):
        mo, b = self.momento("inicio")
        self.comunes(mo, b)
        self.assertEqual(b["veredicto"]["valor"], mo["veredicto"])
        self.assertEqual(b["veredicto"]["motivos"], ["sin_plazo", "pocos_datos"])
        self.assertEqual({p["persona"]: p["n"] for p in b["base"]["personas"]},
                         {"persona-a": 0, "persona-b": 0, "persona-c": 0})     # hechos.json: 2, 1 y 0 (ver arriba)
        self.assertIn("T20", [x["tarea"] for x in b["sin_plazo"]])     # lleva más de H+2 en curso, pero sin plazo
        self.assertEqual(b["cadena"], [])                               # ningún Hasta resuelto
        # 24 sin plazo: el resumen se corta a 160 (api.md §11.4), y lo de detrás no cabe.
        self.assertTrue(b["resumen"].startswith("ruta: sin estimación (sin plazo: T03, T04, "))
        self.assertEqual((len(b["resumen"]), b["resumen"][-1]), (160, "…"))

    def test_mitad_bien(self):
        mo, b = self.momento("mitad bien")
        self.comunes(mo, b)
        self.assertEqual(b["veredicto"]["valor"], "sin_estimacion")     # hechos.json: a_tiempo (ver arriba)
        self.assertEqual(b["veredicto"]["motivos"], ["sin_plazo"])
        self.assertEqual(b["sin_plazo"], [{"tarea": "T28", "motivo": "por_confirmar"}])
        self.assertEqual({p["persona"]: p["n"] for p in b["base"]["personas"]},
                         {p: x["n"] for p, x in mo["base"].items()})
        self.assertEqual(b["resumen"], "ruta: sin estimación (sin plazo: T28) · otra entrega: dom 20 sep 09:30 (plan.md)")
        self.assertEqual(self.hechos(b, "plazo_pasado"), [])           # T19 espera a T08, en plazo: nada en riesgo
        for t28 in ("fuera", "hasta"):
            with self.subTest(t28=t28):
                _, c = self.momento("mitad bien", t28)
                self.assertEqual(c["veredicto"]["valor"], mo["veredicto"])
                self.assertGreater(c["estimacion"]["margen_min"], 120)  # el extremo lento, horas antes de la entrega
                self.assertEqual(firma(c), "a_tiempo")

    def test_mitad_con_riesgo(self):
        mo, b = self.momento("mitad con riesgo")
        self.comunes(mo, b)
        self.assertEqual(b["veredicto"]["valor"], "sin_estimacion")     # hechos.json: no_llega (ver arriba)
        self.assertEqual(b["veredicto"]["motivos"], ["sin_plazo"])
        self.assertEqual({p["persona"]: p["n"] for p in b["base"]["personas"]},
                         {p: x["n"] for p, x in mo["base"].items()})
        pasados = self.hechos(b, "plazo_pasado")
        self.assertEqual([(h["tarea"], h["gravedad"]) for h in pasados],
                         [("T04", "rojo"), ("T05", "rojo"), ("T06", "rojo"), ("T07", "rojo")])
        # Con la cadena de cada persona (3B), T04 arrastra también lo que va detrás en la sección de A (T08, T09) y lo
        # que espera a eso; T17 y T24–T26 no están en riesgo.
        self.assertEqual(pasados[0]["arrastra"], ["T05", "T06", "T07", "T08", "T09", "T19", "T27", "T28"])
        arrastradas = {t for h in pasados for t in h["arrastra"]}
        self.assertFalse({"T17", "T24", "T25", "T26"} & arrastradas)
        self.assertTrue(b["resumen"].endswith(" · T04: plazo pasado 23:00 y 3 más"))
        for t28 in ("fuera", "hasta"):
            with self.subTest(t28=t28):
                _, c = self.momento("mitad con riesgo", t28)
                self.assertEqual(c["veredicto"]["valor"], mo["veredicto"])
                self.assertEqual(c["veredicto"]["gravedad"], "ambar")
                self.assertLess(c["estimacion"]["margen_max"], 0)        # los dos extremos, después de la entrega
                # La cadena más larga es la de A, por su orden del plan; T08 y T09 acaban tarde con cualquier ritmo.
                self.assertEqual([(e["tarjeta"]["id"], e["por"]) for e in c["cadena"]],
                                 [("T04", "inicio"), ("T05", "depende_de"), ("T06", "orden_del_plan"),
                                  ("T07", "orden_del_plan"), ("T08", "orden_del_plan"), ("T09", "orden_del_plan")])
                entrega = fecha(mo["entrega"]["valor"])
                self.assertTrue(all(fecha(e["fin_temprano"]) > entrega for e in c["cadena"][-2:]))


if __name__ == "__main__":
    unittest.main()
