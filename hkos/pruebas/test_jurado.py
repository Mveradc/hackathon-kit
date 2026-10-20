"""M10, K-102: la cobertura del jurado (hkos/jurado.py, ADR-0012, api.md §11.3), con la tabla de casos de K-102 y los
tres momentos de G13 (evals/coordinacion/simulador/guiones/g13/hechos.json), sin relay, sin red y sin git.

Cada entrada valida contra estado.schema.json (la nota de $defs/nota, tareas[] y jurado: la forma que produce K-104) y
cada salida contra $defs/vista_jurado, ya sin lo transitorio del issue #46, con el validador del OS (esquema.py) y, si
está, con jsonschema.
Uso: uv run --no-project --with "jsonschema[format-nongpl]" -m unittest discover -s hkos/pruebas -v
"""
import copy
import hashlib
import json
import os
import re
import sys
import unittest

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(HKOS)
sys.path.insert(0, HKOS)
import jurado  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha  # noqa: E402

try:
    import jsonschema
except ImportError:
    jsonschema = None


ESQ = Esquema("estado.schema.json")
G13 = os.path.join(KIT, "evals", "coordinacion", "simulador", "guiones", "g13")
AHORA = "2026-09-19T10:00:00Z"
PLAN = "2026-09-19T07:30:00Z"            # hora del commit de plan.md
CRITERIOS = "2026-09-19T08:52:10Z"       # hora del commit de criterios.md
PITCH = "2026-09-19T08:00:00Z"
FUENTES = {k: {"valor": "ok", "fuente": "derivado", "observado_en": AHORA} for k in ("relay", "github", "git")}


def _jsonschema(esq, sub):
    """Un validador de jsonschema para un trozo del esquema, o None si no hay uno con Draft 2020-12 y formatos."""
    v = getattr(jsonschema, "Draft202012Validator", None)
    if not hasattr(v, "FORMAT_CHECKER"):
        return None
    try:
        if v({"format": "date-time"}, format_checker=v.FORMAT_CHECKER).is_valid("ayer"):
            return None
        return v({"$defs": esq.raiz["$defs"], **sub}, format_checker=v.FORMAT_CHECKER)
    except Exception:
        return None


def validador(sub, esq=ESQ):
    js = _jsonschema(esq, sub)

    def errores(valor):
        e = esq._error(sub, valor, "")          # los $ref son locales: esquema.py los resuelve contra la raíz
        if e is None and js is not None:
            e = next(((list(x.absolute_path), x.message) for x in js.iter_errors(valor)), None)
        return e
    return errores


# La salida, contra el esquema ya sin lo transitorio del issue #46 (cierre del contrato de M10): sin «declarada», sin
# «declaradas», sin corregida_por suelta, sin el tope de 160, con planificadas, en_curso, pitch.donde y zona.
VISTA = validador({"$ref": "#/$defs/vista_jurado"})
NOTA = validador({"$ref": "#/$defs/nota"})
TAREAS = validador(ESQ.raiz["properties"]["tareas"])       # tareas[].evidencia, solo como objeto
JURADO = validador(ESQ.raiz["properties"]["jurado"])


def nota(cita, quien="Marta", papel="jurado", dijo="Queremos ver la validación con datos reales", fuerza="obligatorio",
         anotado="@ana", literal=True, corrige=None, obs=CRITERIOS, zona="+02:00"):
    """Una nota como la deja el relay (api.md §11.2), con su clave de 12 hex."""
    cabecera = f"## {cita} · {quien} ({papel})"
    linea = f"- Qué dijo: «{dijo}»" if literal else f"- Qué dijo: (paráfrasis) {dijo}"
    clave = hashlib.sha256("\n".join([cabecera, linea, f"- Anotado por: {anotado}"]).encode("utf-8")).hexdigest()[:12]
    tipo = {"dato": "dato", "comentario suelto": "comentario", "sin precisar": "sin_precisar"}.get(fuerza, "palabra")
    return {"clave": clave, "cita": cita, "hora": cita.replace(" ", "T") + ":00" + zona if zona else None,
            "quien": quien, "papel": papel, "donde": "mesa 4", "dijo": dijo, "literal": literal,
            "fuerza": {"tipo": tipo, "texto": fuerza}, "afecta_a": "plan", "anotado_por": anotado, "corrige": corrige,
            "fuente": "git", "observado_en": obs, "declarado": True}


def tarea(tid, valor, citas=None, fuente="hook", obs=AHORA, evidencia=None, hecha_en=None, nuevo=None, declarado=None,
          estado_declarado=False, conexiones=None, tipo="commit", ev_fuente="git", ev_en=None, primera=None):
    """evidencia: el sha de la última publicación; tareas[].evidencia lleva además su tipo, fuente y hora (ev_en; por
    defecto, la del estado)."""
    t = {"id": tid, "titulo": f"Tarea {tid}", "dueno": "ana", "estado": {"valor": valor, "fuente": fuente, "observado_en": obs},
         "declarado": None}
    if estado_declarado:
        t["estado"]["declarado"] = True
    if declarado:
        t["declarado"] = {"valor": declarado, "fuente": "github", "observado_en": obs, "declarado": True}
    if citas is not None:
        t["criterios"] = {"valor": citas, "fuente": "git", "observado_en": PLAN, "declarado": True}
    if evidencia:
        t["evidencia"] = {"valor": evidencia, "tipo": tipo, "fuente": ev_fuente, "observado_en": ev_en or obs}
    if conexiones:
        t["conexiones"] = {"valor": conexiones, "fuente": "git", "observado_en": PLAN, "declarado": True}
    if hecha_en or nuevo or primera:
        t["historia"] = {"primera_senal": primera, "hecha_en": hecha_en, "trabajo_nuevo_desde": nuevo,
                         "ultima_senal": primera, "fuente": "derivado", "observado_en": obs}
    return t


def estado_jurado(notas, pitch=None, fichero="ok", zona="+02:00"):
    """El bloque jurado de estado.json; zona, la de equipo.md (B4: el relay siempre la pone, aunque sea null)."""
    return {"fichero": {"valor": fichero, "fuente": "git", "observado_en": CRITERIOS, "declarado": True},
            "zona": {"valor": zona, "fuente": "git", "observado_en": PLAN, "declarado": True},
            "notas": notas,
            "pitch": None if pitch is None else {"valor": pitch, "fuente": "git", "observado_en": PITCH, "declarado": True}}


class Base(unittest.TestCase):
    maxDiff = None

    def calcula(self, notas, tareas=(), pitch=None, fichero="ok", ahora=AHORA, fuentes=None, j=None, **kw):
        """bloque() con las entradas validadas contra estado.schema.json y la salida contra $defs/vista_jurado. Sin
        `fuentes`, todas al día en `ahora`."""
        j, tareas = j or estado_jurado(notas, pitch, fichero), list(tareas)
        fuentes = fuentes or {k: dict(d, observado_en=ahora) for k, d in FUENTES.items()}
        notas = j["notas"]
        for n in notas:
            self.assertIsNone(NOTA(n), n["cita"])
        self.assertIsNone(TAREAS(tareas))
        self.assertIsNone(JURADO(j))
        antes = copy.deepcopy((j, tareas, fuentes, kw))
        b = jurado.bloque(j, tareas, ahora, fuentes=fuentes, **kw)
        self.assertIsNone(VISTA(b))
        c = b["cuenta"]
        self.assertEqual(c["sin_cubrir"], c["sin_tarea"] + c["ambiguas"] + c["planificadas"] + c["en_curso"] + c["en_pitch"])
        self.assertEqual(c["notas"], c["sin_cubrir"] + c["cubiertas"] + c["corregidas"])
        self.assertEqual(sum(f["n"] for f in c["sin_cubrir_por_fuerza"]), c["sin_cubrir"])
        vivas = [x["cobertura"]["valor"] for x in b["notas"] if not x["corregida_por"]]
        for clave, valor in (("sin_tarea", "sin_tarea"), ("ambiguas", "ambigua"), ("planificadas", "planificada"),
                             ("en_curso", "en_curso"), ("en_pitch", "en_pitch"), ("cubiertas", "cubierta")):
            self.assertEqual(c[clave], vivas.count(valor), clave)
        self.assertLessEqual(len(b["resumen"]), 120)
        self.assertEqual(antes, (j, tareas, fuentes, kw), "bloque() no cambia sus entradas")
        self.assertEqual(b, jurado.bloque(*copy.deepcopy((j, tareas, ahora)), fuentes=fuentes, **kw), "puro")
        self.assertEqual((b["observado_en"], b["fuente"]), (ahora, "derivado"))
        return b

    def de(self, b, n):
        return next(x for x in b["notas"] if x["nota"]["clave"] == n["clave"])

    def cobertura(self, b, n):
        return self.de(b, n)["cobertura"]["valor"]


class TablaK102(Base):
    def test_validador_rechaza_una_salida_mala(self):
        """El validador de las pruebas no deja pasar cualquier cosa."""
        b = jurado.bloque(estado_jurado([nota("2026-09-19 10:40")]), [], AHORA)
        self.assertIsNone(VISTA(b))
        # Tampoco lo que era transitorio en el esquema (#53), que el código ya no produce.
        x = b["notas"][0]
        malos = {"cobertura inventada": ("cobertura", "recogida"), "declarada": ("cobertura", "declarada"),
                 "corregida_por suelta": ("corregida_por", "0123456789ab"),
                 "pitch sin donde": ("pitch", {"fuente": "git", "observado_en": PITCH, "declarado": True})}
        for nombre, (campo, valor) in malos.items():
            with self.subTest(nombre):
                malo = copy.deepcopy(b)
                malo["notas"][0][campo] = dict(x["cobertura"], valor=valor) if campo == "cobertura" else valor
                self.assertIsNotNone(VISTA(malo))
        for nombre, cambia in {"declaradas": lambda c: c.update(declaradas=0), "sin planificadas": lambda c: c.pop("planificadas"),
                               "sin en_curso": lambda c: c.pop("en_curso"), "sin ambiguas": lambda c: c.pop("ambiguas")}.items():
            with self.subTest(nombre):
                malo = copy.deepcopy(b)
                cambia(malo["cuenta"])
                self.assertIsNotNone(VISTA(malo))
        self.assertIsNotNone(VISTA(dict(b, resumen="j" * 121)))              # el tope de 160 era transitorio

    def test_la_salida_valida_contra_el_esquema_nuevo(self):
        n, vieja = nota("2026-09-19 10:40"), nota("2026-09-19 09:00", dijo="antes")
        n["corrige"] = "2026-09-19 09:00"
        t = tarea("T05", "publicada", ["2026-09-19 10:40"], fuente="git", evidencia="055c0de", tipo="fusion")
        zona = {"valor": "Europe/Madrid", "fuente": "git", "observado_en": PLAN, "declarado": True}
        j = dict(estado_jurado([n, vieja], pitch=["2026-09-19 10:40"]), zona=zona)
        b = self.calcula(None, [t], j=j)
        self.assertIsNone(VISTA(b))
        self.assertEqual(b["zona"], zona)                                    # B4: la de equipo.md, tal cual
        # Ya no es opcional: sin ella, ni la entrada (jurado de estado.json) ni la vista validan.
        self.assertIsNotNone(JURADO({k: v for k, v in j.items() if k != "zona"}))
        self.assertIsNotNone(VISTA({k: v for k, v in b.items() if k != "zona"}))

    def test_sin_tarea(self):
        n = nota("2026-09-19 10:40")
        b = self.calcula([n])
        x = b["notas"][0]
        self.assertEqual(x["cobertura"], {"valor": "sin_tarea", "fuente": "derivado", "observado_en": CRITERIOS, "viejo": False})
        self.assertEqual((x["tareas"], x["evidencias"], x["pitch"], x["corregida_por"], x["trabajo_nuevo_desde"]),
                         ([], [], None, None, None))
        self.assertEqual(b["cuenta"], {"notas": 1, "corregidas": 0, "cubiertas": 0, "sin_cubrir": 1, "sin_tarea": 1,
                                       "ambiguas": 0, "planificadas": 0, "en_curso": 0, "en_pitch": 0,
                                       "sin_cubrir_por_fuerza": [{"texto": "obligatorio", "n": 1}]})
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir · 1 «obligatorio» (criterios.md) · 0 cubiertas de 1")
        self.assertEqual((b["fichero"], b["sin_nota"], b["viejo"]), ("ok", [], False))

    def test_en_curso_con_su_tarea_empezada(self):
        n = nota("2026-09-18 21:15")
        b = self.calcula([n], [tarea("T12", "en_curso", ["2026-09-18 21:15"], obs="2026-09-19T08:40:00Z",
                                     primera="2026-09-19T08:40:00Z")])
        x = b["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "en_curso")
        self.assertEqual(x["cobertura"]["observado_en"], "2026-09-19T08:40:00Z")
        self.assertEqual(x["tareas"][0]["enlace"], {"cita": "2026-09-18 21:15", "ambiguo": False, "donde": "plan.md",
                                                    "fuente": "git", "observado_en": PLAN, "declarado": True})
        t = x["tareas"][0]["tarjeta"]
        self.assertEqual((t["id"], t["estado"], t["etiqueta"], t["fuente"], t["viejo"]), ("T12", "en_curso", "en curso", "hook", False))
        self.assertEqual(x["evidencias"], [])
        self.assertEqual((b["cuenta"]["en_curso"], b["cuenta"]["planificadas"]), (1, 0))

    def test_k108_4_planificada_o_en_curso_con_la_hora_mas_reciente_del_plan_o_del_estado(self):
        """K-108, punto 4: el observado_en de una nota planificada o en curso es la más reciente entre la hora del
        commit del plan que trae su etiqueta y la del estado de sus tareas. En el sandbox salía la de los eventos
        viejos de sus issues (2026-10-14), no la de cuando se enlazó."""
        n = nota("2026-09-18 21:15")
        viejo = "2026-09-14T09:00:00Z"
        b = self.calcula([n], [tarea("T12", "lista", ["2026-09-18 21:15"], fuente="github", obs=viejo)])
        self.assertEqual((self.de(b, n)["cobertura"]["valor"], self.de(b, n)["cobertura"]["observado_en"]),
                         ("planificada", PLAN))
        b = self.calcula([n], [tarea("T12", "en_curso", ["2026-09-18 21:15"], obs=viejo, primera=viejo)])
        self.assertEqual((self.de(b, n)["cobertura"]["valor"], self.de(b, n)["cobertura"]["observado_en"]),
                         ("en_curso", PLAN))
        # Con el estado más reciente que el plan, la del estado (como antes).
        b = self.calcula([n], [tarea("T12", "en_curso", ["2026-09-18 21:15"], obs="2026-09-19T08:40:00Z",
                                     primera="2026-09-19T08:40:00Z")])
        self.assertEqual(self.de(b, n)["cobertura"]["observado_en"], "2026-09-19T08:40:00Z")
        # Una cubierta, la de sus tareas, sin cambios.
        b = self.calcula([n], [tarea("T12", "publicada", ["2026-09-18 21:15"], fuente="git", obs="2026-09-19T07:00:00Z",
                                     evidencia="abc1234", hecha_en="2026-09-19T07:00:00Z")])
        self.assertEqual(self.de(b, n)["cobertura"]["observado_en"], "2026-09-19T07:00:00Z")

    def test_cubierta_con_todas_publicadas_o_cerradas_y_su_evidencia(self):
        n = nota("2026-09-18 20:30", fuerza="dato")
        tareas = [tarea("T03", "publicada", ["2026-09-18 20:30"], fuente="git", obs="2026-09-19T01:10:00Z",
                        evidencia="9e1f2a3b4c5d", hecha_en="2026-09-19T01:10:00Z"),
                  tarea("T04", "cerrada", ["2026-09-18 20:30"], fuente="github", obs="2026-09-19T03:00:00Z",
                        evidencia="aa11bb22cc33", tipo="fusion", ev_en="2026-09-19T02:00:00Z",
                        hecha_en="2026-09-19T02:00:00Z")]
        b = self.calcula([n], tareas)
        x = b["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "cubierta")
        self.assertEqual(x["cobertura"]["observado_en"], "2026-09-19T03:00:00Z")
        self.assertEqual(x["evidencias"], [
            {"tipo": "commit", "tarea": "T03", "valor": "9e1f2a3b4c5d", "fuente": "git", "observado_en": "2026-09-19T01:10:00Z", "viejo": False},
            {"tipo": "fusion", "tarea": "T04", "valor": "aa11bb22cc33", "fuente": "git", "observado_en": "2026-09-19T02:00:00Z", "viejo": False}])
        self.assertEqual(b["resumen"], "jurado: 0 sin cubrir · 1 cubierta de 1")
        # Con una de las dos sin hacer: sin cubrir, y la evidencia de la hecha se enseña igual.
        tareas[1] = tarea("T04", "lista", ["2026-09-18 20:30"], fuente="github")
        x = self.calcula([n], tareas)["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "en_curso")          # #56, 3: T03 ya no está lista ni pendiente
        self.assertEqual([e["tarea"] for e in x["evidencias"]], ["T03"])

    def test_dos_notas_en_el_mismo_minuto(self):
        lucia = nota("2026-09-18 20:15", quien="Lucía", dijo="la curva de 24 meses", fuerza="nos gustaría ver")
        jorge = nota("2026-09-18 20:15", quien="Jorge", papel="mentor de Embat", dijo="cada acción con su cifra", fuerza="se valora")
        # Sin quién: casa con las dos, enlace ambiguo a cada una; no se elige.
        b = self.calcula([lucia, jorge], [tarea("T11", "publicada", ["2026-09-18 20:15"], fuente="git", evidencia="111c0de")])
        for n in (lucia, jorge):
            x = self.de(b, n)
            self.assertEqual(x["cobertura"]["valor"], "ambigua")
            self.assertEqual([(f["tarjeta"]["id"], f["enlace"]["ambiguo"]) for f in x["tareas"]], [("T11", True)])
            self.assertEqual([e["valor"] for e in x["evidencias"]], ["111c0de"])
        # Ambiguas y sin cubrir: cuentan en «ambiguas», no en sin_tarea ni en curso (#46, 2), y el resumen lo dice.
        self.assertEqual({k: b["cuenta"][k] for k in ("sin_cubrir", "ambiguas", "sin_tarea", "en_curso", "cubiertas")},
                         {"sin_cubrir": 2, "ambiguas": 2, "sin_tarea": 0, "en_curso": 0, "cubiertas": 0})
        self.assertEqual(b["resumen"], "jurado: 2 sin cubrir · 1 «se valora» (criterios.md) · 2 ambiguas · 0 cubiertas de 2")
        # Con «· quién» (sin mayúsculas ni espacios de más): casa con una.
        b = self.calcula([lucia, jorge], [tarea("T11", "publicada", ["2026-09-18 20:15 ·  lucía"], fuente="git", evidencia="111c0de")])
        self.assertEqual((self.cobertura(b, lucia), self.cobertura(b, jorge)), ("cubierta", "sin_tarea"))
        self.assertFalse(self.de(b, lucia)["tareas"][0]["enlace"]["ambiguo"])
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir · 1 «se valora» (criterios.md) · 1 cubierta de 2")

    def test_cita_sin_nota(self):
        n = nota("2026-09-19 10:40")
        b = self.calcula([n], [tarea("T07", "en_curso", ["2026-09-19 10:41", "2026-09-19 10:40 · Pedro"])])
        self.assertEqual(b["sin_nota"], [
            {"tarea": "T07", "cita": "2026-09-19 10:41", "fuente": "git", "observado_en": PLAN, "declarado": True},
            {"tarea": "T07", "cita": "2026-09-19 10:40 · Pedro", "fuente": "git", "observado_en": PLAN, "declarado": True}])
        self.assertEqual(self.cobertura(b, n), "sin_tarea")

    def test_en_pitch_y_con_tarea_y_pitch(self):
        solo = nota("2026-09-18 19:30", quien="Marta Ruiz", papel="organización", fuerza="dato")
        con = nota("2026-09-18 20:15", quien="Lucía", fuerza="nos gustaría ver")
        b = self.calcula([solo, con], [tarea("T11", "en_curso", ["2026-09-18 20:15 · Lucía"], primera="2026-09-19T09:00:00Z")],
                         pitch=["2026-09-18 19:30", "2026-09-18 20:15 · Lucía"])
        x = self.de(b, solo)
        self.assertEqual(x["cobertura"]["valor"], "en_pitch")
        self.assertEqual(x["cobertura"]["observado_en"], PITCH)
        # B3: dónde, fuente y hora; sin autor.
        self.assertEqual(x["pitch"], {"donde": "pitch.md", "fuente": "git", "observado_en": PITCH, "declarado": True})
        y = self.de(b, con)
        self.assertEqual(y["cobertura"]["valor"], "en_curso")           # la cobertura, de la tarea
        self.assertEqual(y["pitch"], {"donde": "pitch.md", "fuente": "git", "observado_en": PITCH, "declarado": True})
        self.assertEqual(y["tareas"][0]["enlace"], {"cita": "2026-09-18 20:15 · Lucía", "ambiguo": False, "donde": "plan.md",
                                                    "fuente": "git", "observado_en": PLAN, "declarado": True})
        self.assertEqual({k: b["cuenta"][k] for k in ("sin_cubrir", "en_pitch", "en_curso")},
                         {"sin_cubrir": 2, "en_pitch": 1, "en_curso": 1})
        self.assertEqual(b["resumen"], "jurado: 2 sin cubrir · 1 «dato» (criterios.md) · 1 en el pitch · 0 cubiertas de 2")
        # El pitch nunca cubre: ni con la tarea publicada cambia de lo que diga la tarea.
        b = self.calcula([con], [tarea("T11", "publicada", ["2026-09-18 20:15 · Lucía"], fuente="git")], pitch=["2026-09-18 20:15"])
        self.assertEqual(self.cobertura(b, con), "cubierta")
        self.assertIsNotNone(self.de(b, con)["pitch"])

    def test_corregida_por_y_correccion_ambigua(self):
        vieja = nota("2026-09-19 10:40", quien="Jorge", dijo="un mes malo no puede hundir el score")
        nueva = nota("2026-09-19 12:05", quien="Jorge", dijo="no es obligatorio, se valora", fuerza="se valora",
                     literal=False, corrige="2026-09-19 10:40")
        b = self.calcula([vieja, nueva], [tarea("T06", "publicada", ["2026-09-19 10:40"], fuente="git", evidencia="061c0de")])
        x = self.de(b, vieja)
        # M20: la relación es declarada, con la hora del commit de criterios.md de la que corrige.
        self.assertEqual(x["corregida_por"], {"valor": nueva["clave"], "fuente": "declarado", "observado_en": CRITERIOS})
        self.assertEqual(x["cobertura"]["valor"], "cubierta")           # enseña aún sus tareas y su evidencia
        self.assertEqual([e["valor"] for e in x["evidencias"]], ["061c0de"])
        self.assertIsNone(self.de(b, nueva)["corregida_por"])
        self.assertEqual([y["nota"]["clave"] for y in b["notas"]], [nueva["clave"], vieja["clave"]])  # corregidas al final
        self.assertEqual({k: b["cuenta"][k] for k in ("notas", "sin_cubrir", "cubiertas", "corregidas")},
                         {"notas": 2, "sin_cubrir": 1, "cubiertas": 0, "corregidas": 1})
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir · 1 «se valora» (criterios.md) · 0 cubiertas de 2")
        # Con «· quién» casa con una aunque haya dos en el minuto.
        otra = nota("2026-09-19 10:40", quien="Lucía", dijo="la demo sin red", fuerza="se valora")
        quien = dict(nueva, corrige="2026-09-19 10:40 · Jorge")
        b = self.calcula([vieja, otra, quien])
        self.assertEqual((self.de(b, vieja)["corregida_por"]["valor"], self.de(b, otra)["corregida_por"]), (quien["clave"], None))
        # Si la cita de la corrección casa con más de una nota, no se marca ninguna.
        b = self.calcula([vieja, otra, nueva])
        self.assertEqual([x["corregida_por"] for x in b["notas"]], [None, None, None])
        self.assertEqual(b["cuenta"]["corregidas"], 0)

    def test_cerrada_a_mano_no_cubre(self):
        n = nota("2026-09-18 20:40")
        b = self.calcula([n], [tarea("T20", "lista", ["2026-09-18 20:40"], fuente="github", declarado="cerrada")])
        x = b["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "planificada")
        self.assertEqual(x["tareas"][0]["tarjeta"]["declarado"], "cerrada")   # con su ⚑, nunca como evidencia
        self.assertEqual(x["evidencias"], [])
        # Un estado declarado (cerrada o reclamada desde la web) tampoco cubre.
        b = self.calcula([n], [tarea("T20", "cerrada", ["2026-09-18 20:40"], fuente="web", estado_declarado=True)])
        self.assertEqual(self.cobertura(b, n), "planificada")
        self.assertTrue(b["notas"][0]["tareas"][0]["tarjeta"]["estado_declarado"])

    def test_publicada_que_vuelve_a_en_curso(self):
        n = nota("2026-09-18 20:15")
        t = tarea("T11", "en_curso", ["2026-09-18 20:15"], obs="2026-09-19T12:20:00Z", evidencia="111c0de",
                  ev_en="2026-09-18T21:20:00Z", hecha_en="2026-09-18T21:20:00Z", nuevo="2026-09-19T12:15:00Z")
        x = self.calcula([n], [t], ahora="2026-09-19T12:30:00Z")["notas"][0]
        self.assertEqual((x["cobertura"]["valor"], x["trabajo_nuevo_desde"]), ("cubierta", "2026-09-19T12:15:00Z"))
        self.assertEqual(x["evidencias"], [{"tipo": "commit", "tarea": "T11", "valor": "111c0de", "fuente": "git",
                                            "observado_en": "2026-09-18T21:20:00Z", "viejo": False}])
        # Con dos tareas que vuelven a tener trabajo, la más antigua; una que sigue publicada no pone hora.
        dos = [t, tarea("T13", "en_revision", ["2026-09-18 20:15"], hecha_en="2026-09-19T09:00:00Z", nuevo="2026-09-19T11:00:00Z"),
               tarea("T14", "publicada", ["2026-09-18 20:15"], fuente="git")]
        x = self.calcula([n], dos, ahora="2026-09-19T12:30:00Z")["notas"][0]
        self.assertEqual((x["cobertura"]["valor"], x["trabajo_nuevo_desde"]), ("cubierta", "2026-09-19T11:00:00Z"))
        # Publicada otra vez: sin «trabajo nuevo desde» y con la hora de la última publicación.
        t2 = tarea("T11", "publicada", ["2026-09-18 20:15"], fuente="git", obs="2026-09-19T13:00:00Z", evidencia="112c0de",
                   hecha_en="2026-09-18T21:20:00Z")
        x = self.calcula([n], [t2], ahora="2026-09-19T13:05:00Z")["notas"][0]
        self.assertIsNone(x["trabajo_nuevo_desde"])
        self.assertEqual((x["evidencias"][0]["valor"], x["evidencias"][0]["observado_en"]), ("112c0de", "2026-09-19T13:00:00Z"))

    def test_evidencia_de_la_ultima_publicacion_con_su_tipo(self):
        """#46, 6: tareas[].evidencia es el último sha publicado, con su tipo, fuente y hora; evidencias[] sale de ahí."""
        n = nota("2026-09-18 20:15")
        # Publicada dos veces (21:20 y 13:00), y otra vez en curso: el sha y la hora de la última, no hecha_en.
        t = tarea("T11", "en_curso", ["2026-09-18 20:15"], obs="2026-09-19T14:20:00Z", evidencia="112c0de",
                  ev_en="2026-09-19T13:00:00Z", hecha_en="2026-09-18T21:20:00Z", nuevo="2026-09-19T14:15:00Z")
        x = self.calcula([n], [t], ahora="2026-09-19T14:30:00Z")["notas"][0]
        self.assertEqual(x["evidencias"], [{"tipo": "commit", "tarea": "T11", "valor": "112c0de", "fuente": "git",
                                            "observado_en": "2026-09-19T13:00:00Z", "viejo": False}])
        # Una fusión aprobada vista por GitHub: tipo fusion y lo viejo, el de GitHub.
        t = tarea("T12", "publicada", ["2026-09-18 20:15"], fuente="github", evidencia="f00dfeed", tipo="fusion",
                  ev_fuente="github", ev_en="2026-09-19T09:00:00Z")
        fuentes = dict(FUENTES, github={"valor": "ok", "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z"})
        x = self.calcula([n], [t], fuentes=fuentes)["notas"][0]
        self.assertEqual(x["evidencias"], [{"tipo": "fusion", "tarea": "T12", "valor": "f00dfeed", "fuente": "github",
                                            "observado_en": "2026-09-19T09:00:00Z", "viejo": True}])
        self.assertEqual((x["cobertura"]["valor"], x["cobertura"]["viejo"]), ("cubierta", True))

    def test_parada_o_no_cerrada_tras_hecha_en_sigue_cubierta(self):
        """#46, 6 (M7): publicada antes y ahora parada o no cerrada sigue contando como hecha, sin parpadeo."""
        n = nota("2026-09-18 20:15")
        for valor in ("parada", "no_cerrada"):
            with self.subTest(valor):
                t = tarea("T11", valor, ["2026-09-18 20:15"], fuente="derivado", obs="2026-09-19T12:40:00Z",
                          evidencia="111c0de", ev_en="2026-09-18T21:20:00Z", hecha_en="2026-09-18T21:20:00Z",
                          nuevo="2026-09-19T12:15:00Z")
                b = self.calcula([n], [t], ahora="2026-09-19T12:45:00Z")
                x = b["notas"][0]
                self.assertEqual((x["cobertura"]["valor"], x["trabajo_nuevo_desde"]), ("cubierta", "2026-09-19T12:15:00Z"))
                self.assertEqual(b["cuenta"]["cubiertas"], 1)
                # Sin haber estado publicada antes, no: sin cubrir, en curso (con su primera señal).
                t["historia"].update(hecha_en=None, primera_senal="2026-09-19T12:15:00Z")
                self.assertEqual(self.cobertura(self.calcula([n], [t], ahora="2026-09-19T12:45:00Z"), n), "en_curso")

    def test_cuenta_planificadas_en_curso_y_sin_cubrir(self):
        """#46, 2 (api.md §11.3): sin_cubrir = sin_tarea + ambiguas + planificadas + en_curso + en_pitch (todo lo no
        cubierto menos las corregidas); planificada si ninguna de sus tareas tiene primera señal, en curso si alguna la
        tiene. Una ambigua cuenta en «ambiguas», aunque alguna de sus tareas haya empezado: no se reparte."""
        sola = nota("2026-09-18 19:00", dijo="sola")
        pitch = nota("2026-09-18 19:30", dijo="pitch", fuerza="dato")
        plan = nota("2026-09-18 20:00", dijo="plan")
        curso = nota("2026-09-18 20:30", dijo="curso")
        senal = nota("2026-09-18 21:00", dijo="señal")
        amb1 = nota("2026-09-18 21:30", quien="Lucía", dijo="amb1")
        amb2 = nota("2026-09-18 21:30", quien="Jorge", dijo="amb2")
        cubierta = nota("2026-09-18 22:00", dijo="cubierta")
        vieja = nota("2026-09-18 18:00", dijo="vieja")
        corrige = nota("2026-09-19 09:00", dijo="corrige", corrige="2026-09-18 18:00")
        tareas = [
            tarea("T01", "lista", ["2026-09-18 20:00", "2026-09-18 21:30"], declarado="cerrada"),   # ⚑: sin señales
            tarea("T02", "reclamada", ["2026-09-18 20:00"], fuente="mcp"),
            tarea("T03", "lista", ["2026-09-18 20:30"]),
            tarea("T04", "publicada", ["2026-09-18 20:30", "2026-09-18 22:00"], fuente="git",       # empezó y acabó
                  primera="2026-09-18T23:00:00Z", hecha_en="2026-09-19T01:00:00Z"),
            tarea("T05", "pendiente", ["2026-09-18 21:00", "2026-09-18 21:30"], fuente="github",
                  primera="2026-09-19T08:00:00Z"),
            tarea("T06", "en_curso", ["2026-09-18 18:00"], primera="2026-09-19T08:30:00Z"),
        ]
        b = self.calcula([sola, pitch, plan, curso, senal, amb1, amb2, cubierta, vieja, corrige], tareas,
                         pitch=["2026-09-18 19:30"])
        self.assertEqual([self.cobertura(b, x) for x in (sola, pitch, plan, curso, senal, amb1, amb2, cubierta, vieja)],
                         ["sin_tarea", "en_pitch", "planificada", "en_curso", "en_curso", "ambigua", "ambigua",
                          "cubierta", "en_curso"])
        # sin_tarea: sola y corrige; ambiguas: las dos, aunque T05 haya empezado (antes iban a en curso); planificadas:
        # plan (T01 con ⚑ y T02 reclamada, sin primera señal); en curso: curso (T04) y señal (T05); la corregida (con
        # T06 en curso) no cuenta en ninguna.
        self.assertEqual(b["cuenta"], {"notas": 10, "corregidas": 1, "cubiertas": 1, "sin_cubrir": 8, "sin_tarea": 2,
                                       "ambiguas": 2, "planificadas": 1, "en_curso": 2, "en_pitch": 1,
                                       "sin_cubrir_por_fuerza": [{"texto": "dato", "n": 1}, {"texto": "obligatorio", "n": 7}]})
        self.assertEqual(b["resumen"], "jurado: 8 sin cubrir · 1 «dato» (criterios.md) · 2 ambiguas · 1 en el pitch · 1 cubierta de 10")
        # Una sola ambigua, en singular.
        b = self.calcula([amb1, amb2], [tarea("T01", "lista", ["2026-09-18 21:30 · Lucía", "2026-09-18 21:30"])])
        self.assertEqual((self.cobertura(b, amb1), self.cobertura(b, amb2)), ("planificada", "ambigua"))
        self.assertEqual(b["resumen"], "jurado: 2 sin cubrir · 2 «obligatorio» (criterios.md) · 1 ambigua · 0 cubiertas de 2")

    def test_56_3_en_curso_por_el_estado_aunque_no_haya_primera_senal(self):
        """#56, punto 3 (fila 6): «en curso» si alguna de sus tareas tiene un estado distinto de lista, pendiente y
        reclamada, o historia.primera_senal; si no, «planificada». La historia se hace sin latidos y solo con los pasos a
        en_curso, así que una tarea en curso por un latido (J1) o publicada sin pasar por en_curso con otra lista (J1b)
        se quedaba en «planificada»."""
        n = nota("2026-09-19 10:40")
        sin_historia = {"primera_senal": None, "hecha_en": None, "trabajo_nuevo_desde": None, "ultima_senal": None,
                        "fuente": "derivado", "observado_en": AHORA}
        j1 = [dict(tarea("T01", "en_curso", ["2026-09-19 10:40"]), historia=dict(sin_historia)),
              tarea("T02", "reclamada", ["2026-09-19 10:40"], fuente="mcp")]
        self.assertEqual(self.cobertura(self.calcula([n], j1), n), "en_curso")
        j1b = [tarea("T01", "publicada", ["2026-09-19 10:40"], fuente="git", hecha_en="2026-09-19T09:00:00Z"),
               tarea("T02", "lista", ["2026-09-19 10:40"])]
        self.assertEqual(self.cobertura(self.calcula([n], j1b), n), "en_curso")
        for valor in ("parada", "no_cerrada", "en_revision", "integrada"):
            with self.subTest(valor):
                self.assertEqual(self.cobertura(self.calcula([n], [tarea("T01", valor, ["2026-09-19 10:40"])]), n), "en_curso")
        # Lista, pendiente o reclamada, sin primera señal: planificada (aunque una ⚑ la dé por cerrada).
        for valor in ("lista", "pendiente", "reclamada"):
            with self.subTest(valor):
                t = tarea("T01", valor, ["2026-09-19 10:40"], declarado="cerrada" if valor == "lista" else None)
                self.assertEqual(self.cobertura(self.calcula([n], [t]), n), "planificada")
        # Con primera señal (empezó y volvió a pendiente por una dependencia), en curso.
        t = tarea("T01", "pendiente", ["2026-09-19 10:40"], fuente="github", primera="2026-09-19T08:00:00Z")
        self.assertEqual(self.cobertura(self.calcula([n], [t]), n), "en_curso")

    def test_prueba_que_falla_y_prueba_vieja_no_cambian_la_cobertura(self):
        a, b_ = nota("2026-09-19 10:40"), nota("2026-09-19 11:20", dijo="la entrega por formulario")
        k1, k2 = "c0ffee000001", "c0ffee000002"
        servicios = {"conexiones": [
            {"clave": k1, "resultado": {"valor": "falla", "fuente": "hook", "observado_en": "2026-09-19T09:58:00Z"}},
            {"clave": k2, "resultado": {"valor": "pasa", "fuente": "hook", "observado_en": "2026-09-19T08:00:00Z"}},
            {"clave": "c0ffee000003", "resultado": None}]}
        tareas = [tarea("T05", "publicada", ["2026-09-19 10:40"], fuente="git", evidencia="055c0de", conexiones=[k1]),
                  tarea("T06", "en_curso", ["2026-09-19 11:20"], conexiones=[k2, "c0ffee000003"])]
        b = self.calcula([a, b_], tareas, servicios=servicios)
        x, y = self.de(b, a), self.de(b, b_)
        self.assertEqual((x["cobertura"]["valor"], x["cobertura"]["viejo"]), ("cubierta", False))
        self.assertEqual(x["evidencias"][1], {"tipo": "prueba", "tarea": "T05", "valor": "falla", "conexion": k1,
                                              "fuente": "hook", "observado_en": "2026-09-19T09:58:00Z", "viejo": False})
        self.assertEqual((y["cobertura"]["valor"], y["cobertura"]["viejo"]), ("en_curso", False))     # #56, 3: por su estado
        self.assertEqual(y["evidencias"], [{"tipo": "prueba", "tarea": "T06", "valor": "pasa", "conexion": k2,
                                            "fuente": "hook", "observado_en": "2026-09-19T08:00:00Z", "viejo": True}])
        # Sin las Pruebas, la misma cobertura.
        sin = self.calcula([a, b_], tareas)
        self.assertEqual([z["cobertura"] for z in sin["notas"]], [z["cobertura"] for z in b["notas"]])

    def test_evidencia_vieja_da_cobertura_vieja(self):
        n = nota("2026-09-19 10:40")
        fuentes = dict(FUENTES, git={"valor": "ok", "fuente": "derivado", "observado_en": "2026-09-19T09:00:00Z"})
        t = tarea("T05", "publicada", ["2026-09-19 10:40"], fuente="git", obs="2026-09-19T08:50:00Z", evidencia="055c0de")
        b = self.calcula([n], [t], fuentes=fuentes)
        x = b["notas"][0]
        self.assertEqual((x["cobertura"]["valor"], x["cobertura"]["viejo"]), ("cubierta", True))
        self.assertTrue(x["evidencias"][0]["viejo"] and x["tareas"][0]["tarjeta"]["viejo"] and b["viejo"])
        # Con la tarea de vuelta en curso (su tarjeta viene del relay, al día), la evidencia vieja sigue haciéndola vieja.
        t = tarea("T05", "en_curso", ["2026-09-19 10:40"], evidencia="055c0de", hecha_en="2026-09-19T08:50:00Z",
                  nuevo="2026-09-19T09:30:00Z")
        x = self.calcula([n], [t], fuentes=fuentes)["notas"][0]
        self.assertFalse(x["tareas"][0]["tarjeta"]["viejo"])
        self.assertTrue(x["cobertura"]["viejo"])
        # Las fuentes de la vista (con su viejo ya calculado) valen igual.
        vista_fuentes = {k: {"valor": "ok", "observado_en": AHORA, "viejo": k == "git"} for k in FUENTES}
        self.assertTrue(self.calcula([n], [t], fuentes=vista_fuentes)["notas"][0]["cobertura"]["viejo"])

    def test_orden_por_fuerza_y_hora_cubiertas_y_corregidas(self):
        def n(cita, fuerza, dijo):
            return nota(cita, dijo=dijo, fuerza=fuerza)
        comentario = n("2026-09-18 19:00", "comentario suelto", "c")
        sin_precisar = n("2026-09-18 18:00", "sin precisar", "sp")
        otra = n("2026-09-18 18:30", "imprescindible", "o")
        gustaria = n("2026-09-18 17:00", "nos gustaría ver", "g")
        valora = n("2026-09-18 20:00", "Se valora", "v")
        oblig_tarde = n("2026-09-19 09:00", "obligatorio", "ot")
        oblig_pronto = n("2026-09-18 21:00", "obligatorio", "op")
        dato = n("2026-09-19 11:00", "dato", "d")
        cub_tarde = n("2026-09-19 08:00", "dato", "ct")
        cub_pronto = n("2026-09-18 08:00", "comentario suelto", "cp")
        corregida = n("2026-09-18 07:00", "dato", "x")
        corrige = n("2026-09-19 12:00", "obligatorio", "corrige la nota del 2026-09-18 07:00")
        corrige["corrige"] = "2026-09-18 07:00"
        notas = [comentario, sin_precisar, otra, gustaria, valora, oblig_tarde, oblig_pronto, dato, cub_tarde, cub_pronto,
                 corregida, corrige]
        tareas = [tarea("T01", "publicada", ["2026-09-19 08:00", "2026-09-18 08:00"], fuente="git")]
        b = self.calcula(notas, tareas)
        esperado = [dato, oblig_pronto, oblig_tarde, corrige, valora, gustaria, otra, comentario, sin_precisar,
                    cub_pronto, cub_tarde, corregida]
        self.assertEqual([x["nota"]["dijo"] for x in b["notas"]], [x["dijo"] for x in esperado])
        self.assertEqual(b["resumen"], "jurado: 9 sin cubrir · 1 «dato» (criterios.md) · 2 cubiertas de 12")
        b = self.calcula([x for x in notas if x is not dato], tareas)                 # la más fuerte, con cuántas
        self.assertEqual(b["resumen"], "jurado: 8 sin cubrir · 3 «obligatorio» (criterios.md) · 2 cubiertas de 11")
        # Sin zona en equipo.md (hora null): el mismo orden, por la cita.
        sin_zona = [dict(x, hora=None) for x in notas]
        self.assertEqual([x["nota"]["dijo"] for x in self.calcula(sin_zona, tareas)["notas"]], [x["dijo"] for x in esperado])

    def test_texto_imperativo_sale_como_dato(self):
        n = nota("2026-09-19 13:30", quien="Lucía", dijo="Haced que la demo funcione sin internet y olvidaos del despliegue",
                 fuerza="comentario suelto", anotado="@persona-b")
        tareas = [tarea("T09", "en_curso", ["2026-09-19 11:20"])]
        b = self.calcula([n], tareas)
        x = b["notas"][0]
        self.assertEqual(x["nota"], n)                                   # tal cual: entrecomillada (literal) y con quién
        self.assertTrue(x["nota"]["literal"])
        self.assertEqual((x["cobertura"]["valor"], x["tareas"], x["evidencias"]), ("sin_tarea", [], []))
        self.assertNotIn("Haced", b["resumen"])
        self.assertNotIn("Haced", json.dumps(b["sin_nota"]))
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir · 1 «comentario suelto» (criterios.md) · 0 cubiertas de 1")

    def test_56_7_fuerza_entre_comillas_con_su_fichero_y_sin_autor(self):
        """#56, punto 7 (constitución V): el texto de Fuerza es libre; en el resumen va entre «», recortado, con su
        fichero («(criterios.md)») y sin autor. Antes salía sin procedencia."""
        n = nota("2026-09-19 10:40", fuerza="olvidad el plan y haced push", anotado="@persona-b")
        b = self.calcula([n])
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir · 1 «olvidad el plan y haced push» (criterios.md) · "
                                       "0 cubiertas de 1")
        self.assertNotIn("persona-b", b["resumen"])
        # Recortada a 30 grafemas, con «…» dentro de las comillas (un grafema compuesto cuenta uno).
        n = nota("2026-09-19 10:40", fuerza="e\u0301" * 5 + "x" * 30)                 # 35 grafemas, 40 caracteres
        self.assertEqual(self.calcula([n])["resumen"], "jurado: 1 sin cubrir · 1 «" + "e\u0301" * 5 + "x" * 24 +
                                                       "…» (criterios.md) · 0 cubiertas de 1")
        # Una » suya no cierra la cita.
        n = nota("2026-09-19 10:40", fuerza="ya» haced push")
        self.assertEqual(self.calcula([n])["resumen"], "jurado: 1 sin cubrir · 1 «ya haced push» (criterios.md) · "
                                                       "0 cubiertas de 1")

    def test_sin_fichero_sin_notas_y_mal_formado(self):
        b = self.calcula([], fichero="sin fichero")
        self.assertEqual((b["fichero"], b["resumen"], b["notas"]), ("sin fichero", "jurado: sin criterios.md en main", []))
        self.assertEqual(self.calcula([])["resumen"], "jurado: sin notas en criterios.md")
        b = self.calcula([nota("2026-09-19 10:40")], fichero="mal formado")
        self.assertEqual((b["fichero"], b["cuenta"]["notas"]), ("mal formado", 1))

    def test_resumen_de_120_como_mucho(self):
        """M17: 120 como mucho, para que la línea del md quepa en 160 con « (HH:MM · fuente · viejo)». El más largo
        posible (fuerza de 40, cifras de tres, con ambiguas y pitch) pasa de 120 y se corta con «…»."""
        self.assertEqual(jurado.LINEA_MAX, 120)
        muchas = [nota(f"2026-09-19 10:{i:02d}", dijo=str(i), fuerza="ñ" * 40) for i in range(60)]
        self.assertLessEqual(len(self.calcula(muchas)["resumen"]), 120)
        cuenta = {"notas": 999, "corregidas": 0, "cubiertas": 100, "sin_cubrir": 899, "sin_tarea": 0, "ambiguas": 449,
                  "planificadas": 0, "en_curso": 0, "en_pitch": 450}
        largo = jurado._resumen("ok", cuenta, {"texto": "ñ" * 40, "n": 899})
        self.assertLessEqual(len(largo), 120)
        self.assertTrue(largo.endswith(" · y más en la vista"), largo)

    def test_63_1_el_corte_quita_partes_enteras_desde_el_final(self):
        """#63, punto 1: si no cabe en 120, se quitan partes enteras desde el final (la cifra sin cubrir, nunca) y se
        añade « · y más en la vista»; nunca se corta dentro de una parte, así que la Fuerza no queda con la «» abierta
        ni sin su fichero. Antes, el corte a 120 dejaba «… 450 en el pitch · 100 cubierta…»."""
        cuenta = {"notas": 999, "corregidas": 0, "cubiertas": 100, "sin_cubrir": 899, "sin_tarea": 0, "ambiguas": 449,
                  "planificadas": 0, "en_curso": 0, "en_pitch": 450}
        largo = jurado._resumen("ok", cuenta, {"texto": "ñ" * 40, "n": 899})
        self.assertEqual(largo, "jurado: 899 sin cubrir · 899 «" + "ñ" * 29 + "…» (criterios.md) · 449 ambiguas · "
                                "y más en la vista")
        self.assertEqual(largo.count("«"), largo.count("»"))
        # Aunque solo quepa la cifra sin cubrir, se queda.
        from ruta import recorta
        self.assertEqual(recorta(["jurado: 899 sin cubrir", "x" * 200], 1), "jurado: 899 sin cubrir · y más en la vista")

    def test_tarjetas_de_la_vista(self):
        """Con las tarjetas de proyeccion.vista, la de la nota es la misma (más viejo)."""
        n = nota("2026-09-19 10:40")
        t = tarea("T05", "en_curso", ["2026-09-19 10:40"])
        suya = {"id": "T05", "titulo": "Motor", "dueno": "ana", "estado": "en_curso", "etiqueta": "en curso", "fuente": "hook",
                "observado_en": AHORA, "depende_de": [], "bloquea_a": [], "espera": []}
        b = self.calcula([n], [t], tarjetas={"T05": suya})
        self.assertEqual(b["notas"][0]["tareas"][0]["tarjeta"], dict(suya, viejo=False))


# --- G13 (guiones/g13): los hechos de la nota, sin relay ---

CABECERA = re.compile(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+) \((.+)\)$")
ETIQUETA = re.compile(r"\(criterios: ([^)]+)\)")
CORRIGE = re.compile(r"corrige la nota del (\d{4}-\d\d-\d\d \d\d:\d\d)")
EMPEZADA = ("lista", "pendiente", "reclamada")


def _lee(nombre):
    with open(os.path.join(G13, nombre), encoding="utf-8") as f:
        return f.read()


def _citas(linea):
    return [c.strip() for m in ETIQUETA.finditer(linea) for c in m.group(1).split(",")]


def notas_g13():
    """Las notas de g13/criterios.md como las deja el relay (api.md §11.2), por cabecera."""
    notas, actual = {}, None
    for linea in _lee("criterios.md").splitlines():
        m = CABECERA.match(linea)
        if m:
            actual = {"cabecera": linea, "cita": m.group(1), "quien": m.group(2), "papel": m.group(3), "lineas": {}}
            notas[linea] = actual
        elif actual and linea.startswith("- ") and ":" in linea:
            k, v = linea[2:].split(":", 1)
            actual["lineas"][k] = (linea, v.strip())
    salida = {}
    for cab, x in notas.items():
        l = x["lineas"]
        dijo = l["Qué dijo"][1]
        literal = dijo.startswith("«")
        texto = dijo.strip("«»") if literal else dijo.replace("(paráfrasis)", "", 1).strip()
        fuerza = l["Fuerza"][1]
        m = CORRIGE.search(dijo)
        clave = hashlib.sha256("\n".join([cab, l["Qué dijo"][0], l["Anotado por"][0]]).encode("utf-8")).hexdigest()[:12]
        salida[cab] = {"clave": clave, "cita": x["cita"], "hora": x["cita"].replace(" ", "T") + ":00+02:00",
                       "quien": x["quien"], "papel": x["papel"], "donde": l["Dónde"][1], "dijo": texto, "literal": literal,
                       "fuerza": {"tipo": {"dato": "dato", "comentario suelto": "comentario"}.get(fuerza, "palabra"),
                                  "texto": fuerza},
                       "afecta_a": l["Afecta a"][1], "anotado_por": l["Anotado por"][1],
                       "corrige": m.group(1) if m else None, "fuente": "git", "observado_en": None, "declarado": True}
    return salida


ANTES_DE_52 = {"sin_cubrir": "sin_tarea", "recogida_en_pitch": "en_pitch"}


def momentos_g13(ruta=os.path.join(G13, "hechos.json")):
    """(momento, jurado, tareas, {id de nota: clave}) de cada momento de hechos.json (o de `ruta`)."""
    with open(ruta, encoding="utf-8") as f:
        hechos = json.load(f)
    # Los hechos de main aún usan los nombres de antes del contrato; el PR #52 los cambia a los de §11.3. Hasta que
    # llegue a main, se montan aquí con los del contrato (con los de #52, no cambia nada).
    for mo in hechos["momentos"]:
        for esperado in mo["notas"].values():
            esperado["estado"] = ANTES_DE_52.get(esperado["estado"], esperado["estado"])
    with open(os.path.join(G13, "tareas.json"), encoding="utf-8") as f:
        info = {t["id"]: t for t in json.load(f)["tareas"]}
    base = notas_g13()
    plan = {m.group(1): _citas(linea) for linea in _lee("plan.md").splitlines()
            if (m := re.match(r"^\| (T\d\d) \|", linea)) and ETIQUETA.search(linea)}
    pitch = {"valor": [c for linea in _lee("pitch.md").splitlines() for c in _citas(linea)], "fuente": "git",
             "observado_en": hechos["entradas"]["pitch.md"]["en_main_desde"], "declarado": True}
    plan_en = hechos["entradas"]["plan.md"]["en_main_desde"]
    ids = {h["id"]: base[h["cabecera"]]["clave"] for h in hechos["notas"]}
    # La hora del estado de las que no han empezado (K-108, decisión 5): lista o pendiente desde el plan; reclamada,
    # desde su última señal (sin_senales: «reclama T23 y no da más señales»), o ahora si los hechos no la dan.
    reclama = {p: x["desde"] for p, x in hechos.get("sin_senales", {}).items()}
    publicada_en = {}
    salida = []
    for mo in hechos["momentos"]:
        ahora = mo["ahora"]
        presentes = [h for h in hechos["notas"] if fecha(h["en_main_desde"]) <= fecha(ahora)]
        obs = max((h["en_main_desde"] for h in presentes), key=fecha)
        notas = [dict(base[h["cabecera"]], observado_en=obs) for h in presentes]
        evid, nuevo, a_mano = {}, {}, set()
        for esperado in mo["notas"].values():
            for e in esperado["evidencia"]:
                evid[e["tarea"]] = e
                publicada_en.setdefault(e["tarea"], e["observado_en"])
            a_mano.update(esperado["cerradas_a_mano"])
            if esperado["trabajo_nuevo_desde"]:
                for tid, valor in esperado["tareas"].items():
                    if valor not in ("publicada", "cerrada") and tid in evid:
                        nuevo[tid] = esperado["trabajo_nuevo_desde"]
        tareas = []
        for tid, valor in mo["tareas"].items():
            publicada = valor == "publicada"
            estado_en = evid[tid]["observado_en"] if publicada and tid in evid else nuevo.get(tid, ahora)
            if valor in ("lista", "pendiente"):
                estado_en = plan_en
            elif valor == "reclamada":
                estado_en = reclama.get(info[tid]["dueno"], ahora)
            # La primera señal la pone el relay en el primer paso a en_curso: la tienen las que ya no están sin empezar.
            primera = None if valor in EMPEZADA else estado_en
            hecha_en = publicada_en.get(tid)       # de otro momento, solo si ya había pasado (M2b va detrás de M3)
            hecha_en = hecha_en if hecha_en and fecha(hecha_en) <= fecha(ahora) else None
            t = {"id": tid, "titulo": info[tid]["titulo"], "dueno": info[tid]["dueno"],
                 "estado": {"valor": valor, "fuente": "git" if publicada else "hook", "observado_en": estado_en},
                 "declarado": {"valor": "cerrada", "fuente": "github", "observado_en": "2026-09-18T19:00:00Z",
                               "declarado": True} if tid in a_mano else None,
                 "historia": {"primera_senal": primera, "hecha_en": hecha_en,   # el primer paso a publicada
                              "trabajo_nuevo_desde": nuevo.get(tid), "ultima_senal": primera, "fuente": "derivado",
                             "observado_en": ahora}}
            if tid in evid:            # el último sha publicado, con su hora (#46, 6)
                t["evidencia"] = {"valor": evid[tid]["sha"], "tipo": "commit", "fuente": "git",
                                  "observado_en": evid[tid]["observado_en"]}
            if tid in plan:
                t["criterios"] = {"valor": plan[tid], "fuente": "git", "observado_en": plan_en, "declarado": True}
            tareas.append(t)
        j = {"fichero": {"valor": "ok", "fuente": "git", "observado_en": obs, "declarado": True},
             "zona": {"valor": "+02:00", "fuente": "git", "observado_en": plan_en, "declarado": True},    # la de las horas
             "notas": notas, "pitch": pitch}
        salida.append((mo, j, tareas, ids))
    return salida


class GuionG13(Base):
    RESUMENES = {"M1": "jurado: 4 sin cubrir · 1 «dato» (criterios.md) · 1 en el pitch · 2 cubiertas de 6",
                 "M2": "jurado: 6 sin cubrir · 1 «dato» (criterios.md) · 1 en el pitch · 1 cubierta de 8",
                 "M3": "jurado: 5 sin cubrir · 1 «dato» (criterios.md) · 1 en el pitch · 2 cubiertas de 8"}

    def test_momentos(self):
        for mo, j, tareas, ids in momentos_g13():
            with self.subTest(momento=mo["nombre"]):
                de_clave = {v: k for k, v in ids.items()}
                b = self.calcula(None, tareas, j=j, ahora=mo["ahora"])
                self.assertEqual(sorted(de_clave[x["nota"]["clave"]] for x in b["notas"]), sorted(mo["notas"]))
                for x in b["notas"]:
                    nid, esperado = de_clave[x["nota"]["clave"]], mo["notas"][de_clave[x["nota"]["clave"]]]
                    estados = {f["tarjeta"]["id"]: f["tarjeta"]["estado"] for f in x["tareas"]}
                    real = {"estado": "corregida" if x["corregida_por"] else x["cobertura"]["valor"], "tareas": estados,
                            "evidencia": [{"tarea": e["tarea"], "sha": e["valor"], "observado_en": e["observado_en"]}
                                          for e in x["evidencias"] if e["tipo"] in ("commit", "fusion")],
                            "trabajo_nuevo_desde": x["trabajo_nuevo_desde"],
                            "cerradas_a_mano": [f["tarjeta"]["id"] for f in x["tareas"] if f["tarjeta"].get("declarado") == "cerrada"],
                            "corregida_por": de_clave.get((x["corregida_por"] or {}).get("valor")), "tambien_en_pitch": x["pitch"] is not None}
                    if "observado_en" in esperado:        # K-108, decisión 5 (PR #74): la hora de la nota, del bloque
                        real["observado_en"] = x["cobertura"]["observado_en"]
                    self.assertEqual(real, {k: v for k, v in esperado.items() if k != "motivo"}, f"{mo['nombre']} {nid}")
                    self.assertFalse(x["cobertura"]["viejo"])
                resumen = self.RESUMENES.get(mo["nombre"].split(" · ")[0])
                if resumen:
                    self.assertEqual(b["resumen"], resumen)
                # #46, 2: la cuenta separa lo mismo que los hechos; con los de #52, que traen la suya, entera.
                estados = [v["estado"] for v in mo["notas"].values()]
                self.assertEqual({k: b["cuenta"][k] for k in ("sin_tarea", "ambiguas", "planificadas", "en_curso",
                                                              "en_pitch", "cubiertas", "corregidas")},
                                 {"sin_tarea": estados.count("sin_tarea"), "ambiguas": estados.count("ambigua"),
                                  "planificadas": estados.count("planificada"), "en_curso": estados.count("en_curso"),
                                  "en_pitch": estados.count("en_pitch"), "cubiertas": estados.count("cubierta"),
                                  "corregidas": estados.count("corregida")})
                if "cuenta" in mo:
                    self.assertEqual(b["cuenta"], mo["cuenta"])
                self.assertEqual(b["sin_nota"], [])
                orden = [de_clave[x["nota"]["clave"]] for x in b["notas"]]
                cubre = ("cubierta", "corregida")
                sin_cubrir = [i for i in orden if mo["notas"][i]["estado"] not in cubre]
                self.assertEqual(sin_cubrir, [i for i in ("N1", "N4", "N6", "N3", "N7", "N8")      # fuerza y luego hora
                                              if i in mo["notas"] and mo["notas"][i]["estado"] not in cubre])
                self.assertEqual(orden[:len(sin_cubrir)], sin_cubrir)               # después, las cubiertas
                if mo["notas"]["N5"]["estado"] == "corregida":
                    self.assertEqual(orden[-1], "N5")                                  # y al final, la corregida


if __name__ == "__main__":
    unittest.main()
