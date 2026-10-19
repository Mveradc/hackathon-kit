"""M10, K-102: la cobertura del jurado (hkos/jurado.py, ADR-0012, api.md §11.3), con la tabla de casos de K-102 y los
tres momentos de G13 (evals/coordinacion/simulador/guiones/g13/hechos.json), sin relay, sin red y sin git.

Cada entrada valida contra estado.schema.json (la nota de $defs/nota, tareas[] y jurado: la forma que produce K-104) y
cada salida contra $defs/vista_jurado, con el validador del OS (esquema.py) y, si está, con jsonschema.
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
DEFS = ESQ.raiz["$defs"]
G13 = os.path.join(KIT, "evals", "coordinacion", "simulador", "guiones", "g13")
AHORA = "2026-09-19T10:00:00Z"
PLAN = "2026-09-19T07:30:00Z"            # hora del commit de plan.md
CRITERIOS = "2026-09-19T08:52:10Z"       # hora del commit de criterios.md
PITCH = "2026-09-19T08:00:00Z"
FUENTES = {k: {"valor": "ok", "fuente": "derivado", "observado_en": AHORA} for k in ("relay", "github", "git")}


def _jsonschema(sub):
    """Un validador de jsonschema para un trozo del esquema, o None si no hay uno con Draft 2020-12 y formatos."""
    v = getattr(jsonschema, "Draft202012Validator", None)
    if not hasattr(v, "FORMAT_CHECKER"):
        return None
    try:
        if v({"format": "date-time"}, format_checker=v.FORMAT_CHECKER).is_valid("ayer"):
            return None
        return v({"$defs": DEFS, **sub}, format_checker=v.FORMAT_CHECKER)
    except Exception:
        return None


def validador(sub):
    js = _jsonschema(sub)

    def errores(valor):
        e = ESQ._error(sub, valor, "")          # los $ref son locales: esquema.py los resuelve contra la raíz
        if e is None and js is not None:
            e = next(((list(x.absolute_path), x.message) for x in js.iter_errors(valor)), None)
        return e
    return errores


VISTA = validador({"$ref": "#/$defs/vista_jurado"})
NOTA = validador({"$ref": "#/$defs/nota"})
TAREAS = validador(ESQ.raiz["properties"]["tareas"])
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
          estado_declarado=False, conexiones=None, fusion=None):
    t = {"id": tid, "titulo": f"Tarea {tid}", "dueno": "ana", "estado": {"valor": valor, "fuente": fuente, "observado_en": obs},
         "declarado": None}
    if estado_declarado:
        t["estado"]["declarado"] = True
    if declarado:
        t["declarado"] = {"valor": declarado, "fuente": "github", "observado_en": obs, "declarado": True}
    if citas is not None:
        t["criterios"] = {"valor": citas, "fuente": "git", "observado_en": PLAN, "declarado": True}
    if evidencia:
        t["evidencia"] = evidencia
    if fusion:
        t["fusion"] = fusion
    if conexiones:
        t["conexiones"] = {"valor": conexiones, "fuente": "git", "observado_en": PLAN, "declarado": True}
    if hecha_en or nuevo:
        t["historia"] = {"primera_senal": None, "hecha_en": hecha_en, "trabajo_nuevo_desde": nuevo,
                         "fuente": "derivado", "observado_en": obs}
    return t


def estado_jurado(notas, pitch=None, fichero="ok"):
    return {"fichero": {"valor": fichero, "fuente": "git", "observado_en": CRITERIOS, "declarado": True},
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
        malo = copy.deepcopy(b)
        malo["notas"][0]["cobertura"]["valor"] = "recogida"
        self.assertIsNotNone(VISTA(malo))

    def test_sin_tarea(self):
        n = nota("2026-09-19 10:40")
        b = self.calcula([n])
        x = b["notas"][0]
        self.assertEqual(x["cobertura"], {"valor": "sin_tarea", "fuente": "derivado", "observado_en": CRITERIOS, "viejo": False})
        self.assertEqual((x["tareas"], x["evidencias"], x["pitch"], x["corregida_por"], x["trabajo_nuevo_desde"]),
                         ([], [], None, None, None))
        self.assertEqual(b["cuenta"], {"notas": 1, "sin_cubrir": 1, "sin_tarea": 1, "ambiguas": 0, "declaradas": 0,
                                       "en_pitch": 0, "cubiertas": 0, "corregidas": 0,
                                       "sin_cubrir_por_fuerza": [{"texto": "obligatorio", "n": 1}]})
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir (1 «obligatorio») · 0 cubiertas de 1")
        self.assertEqual((b["fichero"], b["sin_nota"], b["viejo"]), ("ok", [], False))

    def test_declarada_con_su_tarea_en_curso(self):
        n = nota("2026-09-18 21:15")
        b = self.calcula([n], [tarea("T12", "en_curso", ["2026-09-18 21:15"], obs="2026-09-19T08:40:00Z")])
        x = b["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "declarada")
        self.assertEqual(x["cobertura"]["observado_en"], "2026-09-19T08:40:00Z")
        self.assertEqual(x["tareas"][0]["enlace"], {"cita": "2026-09-18 21:15", "ambiguo": False, "donde": "plan.md",
                                                    "fuente": "git", "observado_en": PLAN, "declarado": True})
        t = x["tareas"][0]["tarjeta"]
        self.assertEqual((t["id"], t["estado"], t["etiqueta"], t["fuente"], t["viejo"]), ("T12", "en_curso", "en curso", "hook", False))
        self.assertEqual(x["evidencias"], [])
        self.assertEqual(b["cuenta"]["declaradas"], 1)

    def test_cubierta_con_todas_publicadas_o_cerradas_y_su_evidencia(self):
        n = nota("2026-09-18 20:30", fuerza="dato")
        tareas = [tarea("T03", "publicada", ["2026-09-18 20:30"], fuente="git", obs="2026-09-19T01:10:00Z",
                        evidencia="9e1f2a3b4c5d", hecha_en="2026-09-19T01:10:00Z"),
                  tarea("T04", "cerrada", ["2026-09-18 20:30"], fuente="github", obs="2026-09-19T03:00:00Z",
                        evidencia="aa11bb22cc33", fusion="aa11bb22cc33", hecha_en="2026-09-19T02:00:00Z")]
        b = self.calcula([n], tareas)
        x = b["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "cubierta")
        self.assertEqual(x["cobertura"]["observado_en"], "2026-09-19T03:00:00Z")
        self.assertEqual(x["evidencias"], [
            {"tipo": "commit", "tarea": "T03", "valor": "9e1f2a3b4c5d", "fuente": "git", "observado_en": "2026-09-19T01:10:00Z", "viejo": False},
            {"tipo": "fusion", "tarea": "T04", "valor": "aa11bb22cc33", "fuente": "git", "observado_en": "2026-09-19T02:00:00Z", "viejo": False}])
        self.assertEqual(b["resumen"], "jurado: 0 sin cubrir · 1 cubierta de 1")
        self.assertEqual(b["cuenta"]["sin_cubrir_por_fuerza"], [])
        # Con una de las dos sin hacer: declarada, y la evidencia de la hecha se enseña igual.
        tareas[1] = tarea("T04", "lista", ["2026-09-18 20:30"], fuente="github")
        x = self.calcula([n], tareas)["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "declarada")
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
        self.assertEqual((b["cuenta"]["ambiguas"], b["cuenta"]["cubiertas"]), (2, 0))
        self.assertEqual(b["resumen"], "jurado: 2 sin cubrir (1 «se valora») · 2 ambiguas · 0 cubiertas de 2")
        # Con «· quién» (sin mayúsculas ni espacios de más): casa con una.
        b = self.calcula([lucia, jorge], [tarea("T11", "publicada", ["2026-09-18 20:15 ·  lucía"], fuente="git", evidencia="111c0de")])
        self.assertEqual((self.cobertura(b, lucia), self.cobertura(b, jorge)), ("cubierta", "sin_tarea"))
        self.assertFalse(self.de(b, lucia)["tareas"][0]["enlace"]["ambiguo"])
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir (1 «se valora») · 1 cubierta de 2")

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
        b = self.calcula([solo, con], [tarea("T11", "en_curso", ["2026-09-18 20:15 · Lucía"])],
                         pitch=["2026-09-18 19:30", "2026-09-18 20:15 · Lucía"])
        x = self.de(b, solo)
        self.assertEqual(x["cobertura"]["valor"], "en_pitch")
        self.assertEqual(x["cobertura"]["observado_en"], PITCH)
        self.assertEqual(x["pitch"], {"fuente": "git", "observado_en": PITCH, "declarado": True})
        y = self.de(b, con)
        self.assertEqual(y["cobertura"]["valor"], "declarada")          # la cobertura, de la tarea
        self.assertEqual(y["pitch"], {"fuente": "git", "observado_en": PITCH, "declarado": True})
        self.assertEqual(b["resumen"], "jurado: 2 sin cubrir (1 «dato») · 1 en el pitch · 0 cubiertas de 2")
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
        self.assertEqual(x["corregida_por"], nueva["clave"])
        self.assertEqual(x["cobertura"]["valor"], "cubierta")           # enseña aún sus tareas y su evidencia
        self.assertEqual([e["valor"] for e in x["evidencias"]], ["061c0de"])
        self.assertIsNone(self.de(b, nueva)["corregida_por"])
        self.assertEqual([y["nota"]["clave"] for y in b["notas"]], [nueva["clave"], vieja["clave"]])  # corregidas al final
        self.assertEqual({k: b["cuenta"][k] for k in ("notas", "sin_cubrir", "cubiertas", "corregidas")},
                         {"notas": 2, "sin_cubrir": 1, "cubiertas": 0, "corregidas": 1})
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir (1 «se valora») · 0 cubiertas de 2")
        # Con «· quién» casa con una aunque haya dos en el minuto.
        otra = nota("2026-09-19 10:40", quien="Lucía", dijo="la demo sin red", fuerza="se valora")
        quien = dict(nueva, corrige="2026-09-19 10:40 · Jorge")
        b = self.calcula([vieja, otra, quien])
        self.assertEqual((self.de(b, vieja)["corregida_por"], self.de(b, otra)["corregida_por"]), (quien["clave"], None))
        # Si la cita de la corrección casa con más de una nota, no se marca ninguna.
        b = self.calcula([vieja, otra, nueva])
        self.assertEqual([x["corregida_por"] for x in b["notas"]], [None, None, None])
        self.assertEqual(b["cuenta"]["corregidas"], 0)

    def test_cerrada_a_mano_es_declarada(self):
        n = nota("2026-09-18 20:40")
        b = self.calcula([n], [tarea("T20", "lista", ["2026-09-18 20:40"], fuente="github", declarado="cerrada")])
        x = b["notas"][0]
        self.assertEqual(x["cobertura"]["valor"], "declarada")
        self.assertEqual(x["tareas"][0]["tarjeta"]["declarado"], "cerrada")   # con su ⚑, nunca como evidencia
        self.assertEqual(x["evidencias"], [])
        # Un estado declarado (cerrada o reclamada desde la web) tampoco cubre.
        b = self.calcula([n], [tarea("T20", "cerrada", ["2026-09-18 20:40"], fuente="web", estado_declarado=True)])
        self.assertEqual(self.cobertura(b, n), "declarada")
        self.assertTrue(b["notas"][0]["tareas"][0]["tarjeta"]["estado_declarado"])

    def test_publicada_que_vuelve_a_en_curso(self):
        n = nota("2026-09-18 20:15")
        t = tarea("T11", "en_curso", ["2026-09-18 20:15"], obs="2026-09-19T12:20:00Z", evidencia="111c0de",
                  hecha_en="2026-09-18T21:20:00Z", nuevo="2026-09-19T12:15:00Z")
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
        self.assertEqual((y["cobertura"]["valor"], y["cobertura"]["viejo"]), ("declarada", False))
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
        self.assertEqual(b["cuenta"]["sin_cubrir_por_fuerza"], [
            {"texto": "dato", "n": 1}, {"texto": "obligatorio", "n": 3}, {"texto": "Se valora", "n": 1},
            {"texto": "nos gustaría ver", "n": 1}, {"texto": "imprescindible", "n": 1},
            {"texto": "comentario suelto", "n": 1}, {"texto": "sin precisar", "n": 1}])
        self.assertEqual(b["resumen"], "jurado: 9 sin cubrir (1 «dato») · 2 cubiertas de 12")
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
        self.assertEqual(b["resumen"], "jurado: 1 sin cubrir (1 «comentario suelto») · 0 cubiertas de 1")

    def test_sin_fichero_sin_notas_y_mal_formado(self):
        b = self.calcula([], fichero="sin fichero")
        self.assertEqual((b["fichero"], b["resumen"], b["notas"]), ("sin fichero", "jurado: sin criterios.md en main", []))
        self.assertEqual(self.calcula([])["resumen"], "jurado: sin notas en criterios.md")
        b = self.calcula([nota("2026-09-19 10:40")], fichero="mal formado")
        self.assertEqual((b["fichero"], b["cuenta"]["notas"]), ("mal formado", 1))

    def test_resumen_cortado_a_160(self):
        muchas = [nota(f"2026-09-19 10:{i:02d}", dijo=str(i), fuerza="ñ" * 40) for i in range(60)]
        self.assertLessEqual(len(self.calcula(muchas)["resumen"]), 160)

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


def momentos_g13():
    """(momento, jurado, tareas, {id de nota: clave}) de cada momento de hechos.json."""
    with open(os.path.join(G13, "hechos.json"), encoding="utf-8") as f:
        hechos = json.load(f)
    with open(os.path.join(G13, "tareas.json"), encoding="utf-8") as f:
        info = {t["id"]: t for t in json.load(f)["tareas"]}
    base = notas_g13()
    plan = {m.group(1): _citas(linea) for linea in _lee("plan.md").splitlines()
            if (m := re.match(r"^\| (T\d\d) \|", linea)) and ETIQUETA.search(linea)}
    pitch = {"valor": [c for linea in _lee("pitch.md").splitlines() for c in _citas(linea)], "fuente": "git",
             "observado_en": hechos["entradas"]["pitch.md"]["en_main_desde"], "declarado": True}
    plan_en = hechos["entradas"]["plan.md"]["en_main_desde"]
    ids = {h["id"]: base[h["cabecera"]]["clave"] for h in hechos["notas"]}
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
            t = {"id": tid, "titulo": info[tid]["titulo"], "dueno": info[tid]["dueno"],
                 "estado": {"valor": valor, "fuente": "git" if publicada else "hook",
                            "observado_en": evid[tid]["observado_en"] if publicada and tid in evid else nuevo.get(tid, ahora)},
                 "declarado": {"valor": "cerrada", "fuente": "github", "observado_en": "2026-09-18T19:00:00Z",
                               "declarado": True} if tid in a_mano else None,
                 "historia": {"primera_senal": None, "hecha_en": publicada_en.get(tid),   # el primer paso a publicada
                              "trabajo_nuevo_desde": nuevo.get(tid), "fuente": "derivado", "observado_en": ahora}}
            if tid in evid:
                t["evidencia"] = evid[tid]["sha"]
            if tid in plan:
                t["criterios"] = {"valor": plan[tid], "fuente": "git", "observado_en": plan_en, "declarado": True}
            tareas.append(t)
        j = {"fichero": {"valor": "ok", "fuente": "git", "observado_en": obs, "declarado": True}, "notas": notas, "pitch": pitch}
        salida.append((mo, j, tareas, ids))
    return salida


class GuionG13(Base):
    RESUMENES = ["jurado: 4 sin cubrir (1 «dato») · 1 en el pitch · 2 cubiertas de 6",
                 "jurado: 6 sin cubrir (1 «dato») · 1 en el pitch · 1 cubierta de 8",
                 "jurado: 5 sin cubrir (1 «dato») · 1 en el pitch · 2 cubiertas de 8"]

    def test_momentos(self):
        for (mo, j, tareas, ids), resumen in zip(momentos_g13(), self.RESUMENES):
            with self.subTest(momento=mo["nombre"]):
                de_clave = {v: k for k, v in ids.items()}
                b = self.calcula(None, tareas, j=j, ahora=mo["ahora"])
                self.assertEqual(sorted(de_clave[x["nota"]["clave"]] for x in b["notas"]), sorted(mo["notas"]))
                for x in b["notas"]:
                    nid, esperado = de_clave[x["nota"]["clave"]], mo["notas"][de_clave[x["nota"]["clave"]]]
                    c = x["cobertura"]["valor"]
                    estados = {f["tarjeta"]["id"]: f["tarjeta"]["estado"] for f in x["tareas"]}
                    if x["corregida_por"]:
                        valor = "corregida"
                    elif c == "declarada":
                        valor = "planificada" if all(e in EMPEZADA for e in estados.values()) else "en_curso"
                    else:
                        valor = {"sin_tarea": "sin_cubrir", "en_pitch": "recogida_en_pitch"}.get(c, c)
                    real = {"estado": valor, "tareas": estados,
                            "evidencia": [{"tarea": e["tarea"], "sha": e["valor"], "observado_en": e["observado_en"]}
                                          for e in x["evidencias"] if e["tipo"] in ("commit", "fusion")],
                            "trabajo_nuevo_desde": x["trabajo_nuevo_desde"],
                            "cerradas_a_mano": [f["tarjeta"]["id"] for f in x["tareas"] if f["tarjeta"].get("declarado") == "cerrada"],
                            "corregida_por": de_clave.get(x["corregida_por"]), "tambien_en_pitch": x["pitch"] is not None}
                    self.assertEqual(real, {k: v for k, v in esperado.items() if k != "motivo"}, f"{mo['nombre']} {nid}")
                    self.assertFalse(x["cobertura"]["viejo"])
                self.assertEqual(b["resumen"], resumen)
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
