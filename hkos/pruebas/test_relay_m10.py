"""M10, K-104: los datos de entrada de la vista de jurado y de la ruta crítica en el relay (api.md §3 y §11.1–§11.2).

- hkos/lecturas.py: criterios.md (notas con su clave), equipo.md (Inicio, Entrega y zona), plan.md (etiquetas, Hasta,
  franjas, orden, Hitos y Descansos) y pitch.md, con las entradas de G13 y G14 y los planes de ejemplo 02 y 03;
- hkos/modelo.py: la historia de transiciones de cada tarea (y su evidencia), comparada con el motor recalculado en
  cada evento;
- hkos/relay.py y hkos/red.py: los interruptores, la lectura de origin/main de un clon (con un remoto bare temporal,
  nunca GitHub), el último bueno, el arranque desde eventos.jsonl y estado.json contra el esquema.

Uso: uv run --no-project --with "jsonschema[format-nongpl]" -m unittest discover -s hkos/pruebas -v
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(HKOS)
SIM = os.path.join(KIT, "evals", "coordinacion", "simulador")
GUIONES = os.path.join(SIM, "guiones")
EJEMPLOS = os.path.join(KIT, "skills", "hack-plan", "examples")
sys.path[:0] = [HKOS, SIM]
import lecturas  # noqa: E402
import modelo  # noqa: E402
import red  # noqa: E402
import relay as relay_mod  # noqa: E402
import ruta as ruta_mod  # noqa: E402
import servicios  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha  # noqa: E402
from simula import carga, montar  # noqa: E402

try:
    import jsonschema
except ImportError:
    jsonschema = None

PERSONAS = [{"persona": "persona-a", "nombre": "Persona A"}, {"persona": "persona-b", "nombre": "Persona B"},
            {"persona": "persona-c", "nombre": "Persona C"}]
CT = "2026-09-19T07:31:00Z"
CTS = {k: CT for k in ("punta", "criterios", "plan", "pitch", "equipo", "servicios")}
EQUIPO_03 = "# Equipo\n\n## Hackathon\n- Inicio: 2026-09-18 19:00 (Europe/Madrid)\n- Entrega: 2026-09-20 10:00 (Europe/Madrid)\n"
HECHAS = ("publicada", "cerrada")
# Los motivos de g14/hechos.json (en palabras) y los del contrato (api.md §11.2)
MOTIVO = {None: None, "sin Inicio": "relativo_sin_inicio", "plazo sin resolver": "por_confirmar"}


def leer(rel, base=GUIONES):
    with open(os.path.join(base, rel), encoding="utf-8") as f:
        return f.read()


def mismo(a, b):
    """La misma hora (o las dos None), aunque una venga en UTC y otra con su desfase."""
    return (a is None and b is None) or (a is not None and b is not None and fecha(a) == fecha(b))


def esquema_estado():
    return Esquema("estado.schema.json")


def con_jsonschema(test, estado):
    """Con jsonschema (Draft 2020-12 y formatos), también con él; sin él, solo el validador del kit."""
    test.assertIsNone(esquema_estado().error(estado))
    v = getattr(jsonschema, "Draft202012Validator", None) if jsonschema else None
    if v is None or not hasattr(v, "FORMAT_CHECKER"):
        return
    with open(os.path.join(KIT, "docs", "hackathon-os", "contratos", "estado.schema.json"), encoding="utf-8") as f:
        errores = list(v(json.load(f), format_checker=v.FORMAT_CHECKER).iter_errors(estado))
    test.assertEqual([e.message for e in errores], [])


def estado_minimo(**extra):
    return dict({"v": 1, "generado_en": CT, "fuentes": {}, "personas": [], "tareas": [], "sin_tarea": [],
                 "discrepancias": [], "colisiones": []}, **extra)


def calcula(equipo=None, plan=None, criterios=None, pitch=None, servicios_md=None, jurado=True, ruta=True, cts=CTS,
            personas=PERSONAS):
    return lecturas.calcular({"equipo": equipo, "plan": plan, "criterios": criterios, "pitch": pitch,
                              "servicios": servicios_md}, cts, personas, jurado, ruta)


class SinZoneinfo(unittest.TestCase):
    """Cada prueba corre con el respaldo de la UE (como en Windows sin tzdata), también en Linux."""

    def setUp(self):
        antes = lecturas.ZONEINFO
        lecturas.ZONEINFO = False
        self.addCleanup(setattr, lecturas, "ZONEINFO", antes)


# =============================================================================================== criterios.md
class Criterios(SinZoneinfo):
    def setUp(self):
        super().setUp()
        self.hechos = carga(os.path.join(GUIONES, "g13", "hechos.json"))
        r = calcula(equipo=leer("g14/equipo-2.md"), plan=leer("g13/plan.md"), criterios=leer("g13/criterios.md"),
                    pitch=leer("g13/pitch.md"))
        self.r, self.notas = r, r["jurado"]["notas"]

    def test_las_8_notas_de_g13_con_todos_sus_campos(self):
        hn = self.hechos["notas"]
        self.assertEqual(len(self.notas), len(hn))
        for n, h in zip(self.notas, hn):
            self.assertEqual((n["cita"], n["quien"], n["papel"], n["fuerza"]["texto"], n["anotado_por"]),
                             (h["cita"], h["quien"], h["papel"], h["fuerza"], h["anotado_por"]))
            self.assertTrue(mismo(n["hora"], h["cuando"]), (n["hora"], h["cuando"]))   # con la zona de equipo.md
            self.assertEqual((n["fuente"], n["observado_en"], n["declarado"]), ("git", CT, True))
        self.assertEqual(self.r["jurado"]["fichero"]["valor"], "ok")
        n1, n3 = self.notas[0], self.notas[2]
        self.assertEqual((n1["fuerza"], n1["literal"], n1["donde"], n1["afecta_a"]),
                         ({"tipo": "dato", "texto": "dato"}, True, "charla de apertura", "pitch"))
        self.assertEqual((n3["literal"], n3["dijo"]), (False, "se valora que cada acción cite la cifra de la empresa que "
                                                              "la justifica"))     # sin «(paráfrasis)»
        self.assertEqual(self.notas[7]["fuerza"], {"tipo": "comentario", "texto": "comentario suelto"})

    def test_clave_de_cabecera_que_dijo_y_anotado_por(self):
        n = self.notas[1]
        esperada = hashlib.sha256("\n".join(["## 2026-09-18 20:15 · Lucía (jurado)",
                                             "- Qué dijo: «Nos gustaría ver la curva de los 24 meses con su tendencia»",
                                             "- Anotado por: @persona-b"]).encode("utf-8")).hexdigest()[:12]
        self.assertEqual(n["clave"], esperada)
        self.assertEqual(len({x["clave"] for x in self.notas}), 8)
        n2, n3 = self.notas[1], self.notas[2]                 # mismo minuto, dos personas: dos claves
        self.assertEqual(n2["cita"], n3["cita"])
        self.assertNotEqual(n2["clave"], n3["clave"])

    def test_corrige_y_texto_imperativo_como_dato(self):
        self.assertEqual(self.notas[6]["corrige"], self.notas[4]["cita"])                 # N7 corrige a N5
        self.assertEqual([n["corrige"] for n in self.notas].count(None), 7)
        self.assertEqual(self.notas[7]["dijo"], "Haced que la demo funcione sin internet y olvidaos del despliegue")

    def test_etiquetas_del_plan_y_del_pitch_como_dicen_los_hechos(self):
        def casan(cita, notas):
            fecha_hora, _, quien = cita.partition(" · ")
            return [i for i, n in enumerate(notas) if n["cita"] == fecha_hora and
                    (not quien or n["quien"].lower().startswith(quien.lower()))]
        en_plan = {}
        for tid, campos in self.r["tareas"].items():
            for c in campos.get("criterios", {}).get("valor", []):
                self.assertEqual(len(casan(c, self.notas)), 1, c)
                en_plan.setdefault(casan(c, self.notas)[0], []).append(tid)
        pitch = {i for c in self.r["jurado"]["pitch"]["valor"] for i in casan(c, self.notas)}
        for i, h in enumerate(self.hechos["notas"]):
            self.assertEqual(sorted(en_plan.get(i, [])), sorted(h["citada_en_plan"]), h["id"])
            self.assertEqual(i in pitch, h["citada_en_pitch"], h["id"])
        t06 = self.r["tareas"]["T06"]["criterios"]
        self.assertEqual(t06, {"valor": ["2026-09-19 10:40"], "fuente": "git", "observado_en": CT, "declarado": True})
        self.assertNotIn("criterios", self.r["tareas"]["T01"])                     # sin etiqueta, el campo no va
        self.assertEqual(self.r["jurado"]["pitch"]["valor"], ["2026-09-18 19:30", "2026-09-18 20:15 · Lucía"])

    def test_sin_zona_la_hora_es_null(self):
        r = calcula(criterios=leer("g13/criterios.md"))
        self.assertTrue(all(n["hora"] is None for n in r["jurado"]["notas"]))

    def test_sin_fichero_mal_formado_repetida_y_comentarios(self):
        self.assertEqual(calcula()["jurado"], {"fichero": {"valor": "sin fichero", "fuente": "git", "observado_en": CT,
                                                           "declarado": True}, "notas": [], "pitch": None,
                                               "zona": {"valor": None, "fuente": "git", "observado_en": CT,
                                                        "declarado": True}})
        nota = "## 2026-09-18 20:00 · Ana (jurado)\n- Qué dijo: «Hola»\n- Anotado por: @ana\n"
        md = ("# Criterios\n<!-- ## 2026-01-01 00:00 · Plantilla (x)\n- Qué dijo: «no es una nota» -->\n" + nota + nota +
              "## 2026-09-18 21:00 · Luis (mentor)\n- Dónde: mesa\n\n## Otra sección\n- Qué dijo: «fuera de una nota»\n"
              "## 2026-09-18 22:00 · Marta (Embat) (jurado)\n- Qué dijo: (paráfrasis) algo; corrige la nota del "
              "2026-09-18 20:00 · Ana: mejor así\n")
        j = calcula(criterios=md)["jurado"]
        self.assertEqual(j["fichero"]["valor"], "mal formado")                     # la de las 21:00 no tiene «Qué dijo»
        self.assertEqual([n["cita"] for n in j["notas"]], ["2026-09-18 20:00", "2026-09-18 22:00"])
        ultima = j["notas"][1]
        self.assertEqual((ultima["quien"], ultima["papel"], ultima["corrige"], ultima["fuerza"]),
                         ("Marta (Embat)", "jurado", "2026-09-18 20:00 · Ana", {"tipo": "sin_precisar", "texto": "sin precisar"}))
        self.assertIsNone(j["notas"][0]["donde"])

    def test_56_corrige_con_parentesis_en_el_quien(self):
        """#56 (sin decisión, fila 13): «corrige la nota del … · Marta (Embat)» no se corta en el primer «)». Antes,
        corrige salía «… · Marta (Embat» (que no es una cita) y la corrección se perdía en silencio."""
        import jurado
        md = ("## 2026-09-19 10:40 · Marta (Embat) (jurado)\n- Qué dijo: «Un mes malo no hunde el score»\n"
              "- Fuerza: obligatorio\n- Anotado por: @persona-a\n"
              "## 2026-09-19 12:05 · Marta (Embat) (jurado)\n- Qué dijo: (paráfrasis) no es obligatorio, se valora "
              "(corrige la nota del 2026-09-19 10:40 · Marta (Embat))\n- Fuerza: se valora\n- Anotado por: @persona-a\n")
        notas = calcula(criterios=md)["jurado"]["notas"]
        self.assertEqual([n["corrige"] for n in notas], [None, "2026-09-19 10:40 · Marta (Embat)"])
        b = jurado.bloque({"fichero": {"valor": "ok", "fuente": "git", "observado_en": CT, "declarado": True},
                           "zona": {"valor": None, "fuente": "git", "observado_en": CT, "declarado": True},
                           "notas": notas, "pitch": None}, [], CT)
        self.assertEqual(b["cuenta"]["corregidas"], 1)
        self.assertEqual(lecturas.CORRIGE.search("corrige la nota del 2026-09-19 10:40 · Ana: mejor").group(2), "Ana")

    def test_utf16_y_crlf(self):
        md = leer("g13/criterios.md").replace("\n", "\r\n")
        texto = servicios.decodificar(b"\xff\xfe" + md.encode("utf-16-le"))
        j = calcula(criterios=texto)["jurado"]
        self.assertEqual([n["clave"] for n in j["notas"]], [n["clave"] for n in self.notas])

    def test_etiqueta_solo_al_final_y_con_parentesis_en_el_quien(self):
        self.assertEqual(lecturas.etiqueta_plan("Algo (criterios: 2026-09-18 20:15 · Marta (Embat))"),
                         ["2026-09-18 20:15 · Marta (Embat)"])
        self.assertIsNone(lecturas.etiqueta_plan("(criterios: 2026-09-18 20:15) y después más texto"))
        self.assertEqual(lecturas.etiqueta_plan("x (criterios: 2026-09-18 20:15, 2026-09-19 10:40 · Jorge, mal)"),
                         ["2026-09-18 20:15", "2026-09-19 10:40 · Jorge"])

    def test_conexiones_por_su_prueba(self):
        sm = ("# Servicios\n## Servicios\n| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |\n|---|---|---|---|---|---|\n"
              "| api | api/ | 8000 | — | /salud | — |\n| web | web/ | — | — | — | — |\n\n## Conexiones\n| De | A | Contrato | "
              "Prueba |\n|---|---|---|---|\n| web | api | web → api | `curl` |\n")
        r = calcula(plan=leer("g13/plan.md"), servicios_md=sm)
        clave = next(f["clave"] for f in servicios.leer(sm)["filas"] if f["tabla"] == servicios.CONEXIONES)
        self.assertEqual(r["tareas"]["T02"]["conexiones"]["valor"], [clave])
        self.assertNotIn("conexiones", r["tareas"]["T01"])


# =============================================================================================== equipo.md
class Equipo(SinZoneinfo):
    def linea(self, texto, anio=2026):
        dt, motivo, confirmar, zona, _, aviso, _ = lecturas.hora_equipo(texto, anio)
        return (dt.isoformat() if dt else None), motivo, confirmar, zona, aviso

    def test_g14(self):
        r1 = calcula(equipo=leer("g14/equipo-1.md"))["ruta"]
        self.assertEqual((r1["inicio"]["valor"], r1["inicio"]["motivo"], r1["inicio"]["texto"]),
                         (None, "por_confirmar", "por confirmar"))
        self.assertTrue(mismo(r1["entrega"]["valor"], "2026-09-20T08:00:00Z"))
        self.assertEqual((r1["entrega"]["texto"], r1["zona"]["valor"], r1["equipo"]["valor"]),
                         ("2026-09-20 10:00 (Europe/Madrid)", "Europe/Madrid", "ok"))   # la zona, de Entrega
        r2 = calcula(equipo=leer("g14/equipo-2.md"))["ruta"]
        self.assertEqual(r2["inicio"]["valor"], "2026-09-18T19:00:00+02:00")
        self.assertEqual((r2["entrega"]["donde"], r2["entrega"]["declarado"], r2["entrega"]["confirmar"]),
                         ("equipo.md", True, False))

    def test_formas_de_la_linea(self):
        self.assertEqual(self.linea("<fecha y hora, zona horaria>")[1], "sin_dato")
        self.assertEqual(self.linea("—")[1], "sin_dato")
        self.assertEqual(self.linea("2026-09-20 10:00 (cierre 11:00), Europe/Madrid")[1], "dos_horas")
        self.assertEqual(self.linea("2026-09-20 10:00 CEST")[1:4], ("sin_zona", False, None))   # abreviatura: ambigua
        self.assertEqual(self.linea("el domingo por la mañana, Europe/Madrid")[1], "formato")
        self.assertEqual(self.linea("2026-09-20 10:00 (Europe/Madrid) (confirmar)")[:3],
                         ("2026-09-20T10:00:00+02:00", None, True))
        self.assertEqual(self.linea("20/9/2026 10:00 +02:00")[0], "2026-09-20T10:00:00+02:00")
        self.assertEqual(self.linea("domingo 20 de septiembre 10:00, UTC+2", 2026)[0], "2026-09-20T10:00:00+02:00")
        self.assertEqual(self.linea("20 de septiembre de 2027 10:00 UTC−3")[0:4:3], ("2027-09-20T10:00:00-03:00", "-03:00"))
        self.assertEqual(self.linea("2026-09-20 10:00 UTC")[0], "2026-09-20T10:00:00+00:00")

    def test_zona_iana_sin_tzdata(self):
        dt, motivo, _, zona, aviso = self.linea("2026-09-20 10:00 (America/Bogota)")
        self.assertEqual((dt, motivo, zona), (None, "sin_zona", None))
        self.assertEqual(aviso, "la zona America/Bogota no se puede resolver sin tzdata en este portátil; usa +HH:MM")
        r = calcula(equipo="## Hackathon\n- Inicio: 2026-09-18 19:00 (America/Bogota)\n")
        self.assertIn(aviso.replace("2026", ""), r["avisos"][0])
        self.assertEqual(r["ruta"]["zona"]["valor"], None)

    def test_sin_fichero_mal_formado_sin_linea(self):
        r = calcula()["ruta"]
        self.assertEqual((r["equipo"]["valor"], r["inicio"], r["entrega"], r["zona"]["valor"]), ("sin fichero", None, None, None))
        r = calcula(equipo="# Equipo\n- Inicio: 2026-09-18 19:00 (Europe/Madrid)\n")["ruta"]
        self.assertEqual((r["equipo"]["valor"], r["inicio"]), ("mal formado", None))
        r = calcula(equipo="## Hackathon\n- Inicio: 2026-09-18 19:00 (Europe/Madrid)\n")["ruta"]
        self.assertEqual((r["entrega"]["valor"], r["entrega"]["motivo"], r["entrega"]["texto"]), (None, "sin_dato", None))


# =============================================================================================== zonas
class Zonas(unittest.TestCase):
    """El respaldo de la UE en los dos cambios de hora de 2026 (29 mar y 25 oct, a las 01:00 UTC), como zoneinfo con
    fold=0: la hora que no existe (02:30 del 29 mar) se lee con el desfase de antes (+01:00, son las 03:30 de verano);
    la que se repite (02:30 del 25 oct), como la primera (+02:00)."""
    UE = lecturas._ZonaUE("Europe/Madrid", 1)

    def test_cambios_de_hora(self):
        z = self.UE
        casos = [((2026, 3, 29, 1, 59), "+01:00"), ((2026, 3, 29, 2, 30), "+01:00"), ((2026, 3, 29, 3, 0), "+02:00"),
                 ((2026, 10, 25, 1, 59), "+02:00"), ((2026, 10, 25, 2, 30), "+02:00"), ((2026, 10, 25, 3, 0), "+01:00"),
                 ((2026, 9, 19, 12, 0), "+02:00"), ((2026, 1, 10, 12, 0), "+01:00")]
        for partes, desfase in casos:
            self.assertEqual(datetime(*partes, tzinfo=z).isoformat()[-6:], desfase, partes)
        self.assertEqual(datetime(2026, 10, 25, 2, 30, fold=1, tzinfo=z).isoformat()[-6:], "+01:00")
        hueco = datetime(2026, 3, 29, 2, 30, tzinfo=z).astimezone(timezone.utc)
        self.assertEqual((hueco.hour, hueco.minute), (1, 30))
        self.assertEqual(hueco.astimezone(z).isoformat(), "2026-03-29T03:30:00+02:00")
        for h in (0, 1, 2):                                  # de UTC a local en la hora repetida, y vuelta
            u = datetime(2026, 10, 25, h, 30, tzinfo=timezone.utc)
            self.assertEqual(u.astimezone(z).astimezone(timezone.utc), u)
        self.assertEqual(datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc).astimezone(z).isoformat(),
                         "2026-10-25T02:30:00+01:00")

    def test_h_mas_n_cruzando_el_cambio(self):
        inicio = datetime(2026, 3, 28, 19, 0, tzinfo=self.UE)
        dt, _ = lecturas.resolver("H+12", inicio, self.UE)
        self.assertEqual(dt.isoformat(), "2026-03-29T08:00:00+02:00")      # 12 h de reloj real, no de pared

    def test_igual_que_zoneinfo(self):
        try:
            import zoneinfo
            zi = zoneinfo.ZoneInfo("Europe/Madrid")
        except Exception:
            self.skipTest("sin tzdata en este portátil (Windows): solo el respaldo")
        for anio in (2025, 2026, 2027):
            for mes, dia in ((3, 25), (3, 26), (3, 27), (3, 28), (3, 29), (3, 30), (3, 31), (10, 24), (10, 25), (10, 26),
                             (10, 27), (10, 31), (7, 1), (12, 1)):
                for h in range(24):
                    for fold in (0, 1):
                        a = datetime(anio, mes, dia, h, 30, fold=fold, tzinfo=self.UE)
                        b = datetime(anio, mes, dia, h, 30, fold=fold, tzinfo=zi)
                        self.assertEqual(a.utcoffset(), b.utcoffset(), (anio, mes, dia, h, fold))
                    u = datetime(anio, mes, dia, h, 30, tzinfo=timezone.utc)
                    self.assertEqual(u.astimezone(self.UE).isoformat(), u.astimezone(zi).isoformat())

    def test_g13_y_g14_igual_con_y_sin_zoneinfo(self):
        antes = lecturas.ZONEINFO
        self.addCleanup(setattr, lecturas, "ZONEINFO", antes)
        salidas = []
        for zi in (True, False):
            lecturas.ZONEINFO = zi
            salidas.append([calcula(equipo=leer(e), plan=leer(p), criterios=leer("g13/criterios.md"), pitch=leer("g13/pitch.md"))
                            for e, p in (("g14/equipo-1.md", "g14/plan-1.md"), ("g14/equipo-2.md", "g14/plan-2.md"),
                                         ("g14/equipo-2.md", "g13/plan.md"))])
        self.assertEqual(json.dumps(salidas[0], sort_keys=True), json.dumps(salidas[1], sort_keys=True))


# =============================================================================================== plan.md
class Plan(SinZoneinfo):
    def setUp(self):
        super().setUp()
        self.hechos = carga(os.path.join(GUIONES, "g14", "hechos.json"))

    def momento(self, mo):
        return calcula(equipo=leer(mo["equipo.md"].replace("guiones/", "")), plan=leer(mo["plan.md"].replace("guiones/", "")),
                       jurado=False)

    def test_cada_hasta_de_g14_como_dicen_los_hechos(self):
        for mo in self.hechos["momentos"]:
            r = self.momento(mo)
            for tid, h in mo["plazos"].items():
                hasta = r["tareas"][tid]["hasta"]
                self.assertTrue(mismo(hasta["valor"], h["valor"]), (mo["nombre"], tid, hasta, h))
                self.assertEqual((hasta["texto"], hasta["motivo"]), (h["efectivo"] or None, MOTIVO[h["motivo"]]),
                                 (mo["nombre"], tid))
                self.assertEqual((hasta["fuente"], hasta["observado_en"], hasta["declarado"]), ("git", CT, True))
            sin_plazo = {t: x["hasta"]["motivo"] for t, x in r["tareas"].items()
                         if x["hasta"]["valor"] is None and mo["tareas"][t] not in HECHAS and t not in mo["no_cuentan"]}
            self.assertEqual(sin_plazo, {t: MOTIVO[m] for t, m in mo["sin_plazo"].items()}, mo["nombre"])

    def test_hasta_del_plan_de_g13_con_el_equipo_del_reto(self):
        r = calcula(equipo=EQUIPO_03, plan=leer("g13/plan.md"), jurado=False)
        valores = {t: x["hasta"]["valor"] for t, x in r["tareas"].items()}
        self.assertEqual((valores["T01"], valores["T05"], valores["T06"], valores["T07"], valores["T27"]),
                         ("2026-09-18T19:45:00+02:00", "2026-09-19T02:30:00+02:00", "2026-09-19T11:00:00+02:00",
                          "2026-09-19T11:00:00+02:00", "2026-09-19T21:00:00+02:00"))
        self.assertTrue(all(valores.values()))

    def test_planes_de_ejemplo_02_y_03(self):
        for nombre, n, muestras in (
                ("02-facturas-real-plan.md", 42, {"T01": "2026-09-18T20:00:00+02:00", "T05": "2026-09-19T10:00:00+02:00",
                                                  "T10": "2026-09-20T07:30:00+02:00", "T13": "2026-09-19T00:00:00+02:00"}),
                ("03-xray-embat-real-plan.md", 28, {"T04": "2026-09-18T23:00:00+02:00", "T14": "2026-09-19T01:00:00+02:00",
                                                    "T28": "2026-09-19T21:00:00+02:00"})):
            texto = leer(nombre, EJEMPLOS)
            personas = [{"persona": x.lower(), "nombre": x} for x in "ABCDE"] if nombre.startswith("02") else PERSONAS
            r = calcula(equipo=EQUIPO_03, plan=texto, jurado=False, personas=personas)
            hastas = {t: x["hasta"] for t, x in r["tareas"].items()}
            self.assertEqual(len(hastas), n)
            self.assertEqual([t for t, h in hastas.items() if h["valor"] is None], [], nombre)   # todos se resuelven
            for t, v in muestras.items():
                self.assertEqual(hastas[t]["valor"], v, (nombre, t))
            con_jsonschema(self, estado_minimo(ruta=r["ruta"]))
            sin = calcula(equipo="## Hackathon\n- Entrega: 2026-09-20 10:00 (Europe/Madrid)\n", plan=texto, jurado=False,
                          personas=personas)
            self.assertEqual({x["hasta"]["motivo"] for x in sin["tareas"].values()}, {"sin_inicio"}, nombre)

    def test_formas_de_hasta(self):
        tz = lecturas.zona("Europe/Madrid")
        inicio = datetime(2026, 9, 18, 19, 0, tzinfo=tz)
        res = lambda t, **k: (lambda dt, m: ((dt.isoformat() if dt else None), m))(*lecturas.resolver(t, k.get("i", inicio),
                                                                                                     k.get("tz", tz),
                                                                                                     k.get("ant"), 2026))
        self.assertEqual(res("SÁB 02:30"), ("2026-09-19T02:30:00+02:00", None))
        self.assertEqual(res("sábado 02:30"), ("2026-09-19T02:30:00+02:00", None))
        self.assertEqual(res("Sab. 02:30"), ("2026-09-19T02:30:00+02:00", None))
        self.assertEqual(res("vie 19:45"), ("2026-09-18T19:45:00+02:00", None))
        self.assertEqual(res("jue 10:00"), ("2026-09-24T10:00:00+02:00", None))            # el primer jueves desde el inicio
        self.assertEqual(res("H+1:30"), ("2026-09-18T20:30:00+02:00", None))
        ant = datetime(2026, 9, 18, 23, 0, tzinfo=tz)
        self.assertEqual(res("01:00", ant=ant), ("2026-09-19T01:00:00+02:00", None))       # antes que la anterior: día siguiente
        self.assertEqual(res("23:30", ant=ant), ("2026-09-18T23:30:00+02:00", None))
        self.assertEqual(res("21:00"), ("2026-09-18T21:00:00+02:00", None))                # sin anterior, el día del inicio
        self.assertEqual(res(""), (None, "vacio"))
        self.assertEqual(res("—"), (None, "vacio"))
        self.assertEqual(res("hora por confirmar"), (None, "por_confirmar"))
        self.assertEqual(res("sáb ?"), (None, "por_confirmar"))
        self.assertEqual(res("sesión formativa"), (None, "formato"))
        self.assertEqual(res("sáb 25:00"), (None, "formato"))
        self.assertEqual(res("H+2", i=None), (None, "relativo_sin_inicio"))
        self.assertEqual(res("sáb 02:30", i=None), (None, "sin_inicio"))
        self.assertEqual(res("02:30", i=None), (None, "sin_inicio"))
        self.assertEqual(res("sáb 02:30", i=None, tz=None), (None, "sin_zona"))

    def test_fecha_explicita(self):
        tz = lecturas.zona("Europe/Madrid")
        inicio = datetime(2026, 9, 18, 19, 0, tzinfo=tz)
        for i in (inicio, None):                                                            # con y sin Inicio
            self.assertEqual(lecturas.resolver("dom 20 sep 09:30", i, tz, None, 2026)[0].isoformat(), "2026-09-20T09:30:00+02:00")
            self.assertEqual(lecturas.resolver("20 de septiembre 09:30", i, tz, None, 2026)[0].isoformat(),
                             "2026-09-20T09:30:00+02:00")
            self.assertEqual(lecturas.resolver("domingo 20 de sep. a las 09:30", i, tz, None, 2026)[0].isoformat(),
                             "2026-09-20T09:30:00+02:00")
        self.assertEqual(lecturas.resolver("sáb 20 sep 09:30", inicio, tz, None, 2026), (None, "formato"))  # no cuadra
        self.assertEqual(lecturas.resolver("dom 20 sep 09:30", None, None, None, 2026), (None, "sin_zona"))
        # el año: del Inicio, si no de la Entrega, si no del commit del plan
        plan = "## Hitos del equipo\n| Cuándo | Qué |\n|---|---|\n| 20 sep 09:30 | Entrega final |\n"
        r = calcula(equipo="## Hackathon\n- Entrega: 2027-09-20 10:00 (Europe/Madrid)\n", plan=plan, jurado=False)
        self.assertEqual(r["ruta"]["otras_entregas"][0]["valor"], "2027-09-20T09:30:00+02:00")
        cts = dict(CTS, plan="2028-01-02T00:00:00Z")
        r = calcula(equipo="## Hackathon\n- Inicio: por confirmar\n- Entrega: el domingo, +02:00\n", plan=plan, jurado=False,
                    cts=cts)
        self.assertEqual(r["ruta"]["otras_entregas"][0]["valor"], "2028-09-20T09:30:00+02:00")

    def test_franjas_y_orden_del_plan(self):
        r = calcula(equipo=leer("g14/equipo-2.md"), plan=leer("g14/plan-2.md"), jurado=False)["tareas"]
        self.assertEqual(r["T03"]["franja"]["valor"], {"desde": "2026-09-18T21:00:00+02:00", "hasta": "2026-09-18T23:00:00+02:00",
                                                        "min": 60, "compartida": 2})
        self.assertEqual(r["T04"]["franja"]["valor"], r["T03"]["franja"]["valor"])          # heredan: se reparten el bloque
        self.assertEqual(r["T01"]["franja"]["valor"]["desde"], "2026-09-18T19:00:00+02:00")  # la primera, desde el inicio
        self.assertEqual(r["T28"]["franja"], {"valor": None, "motivo": "sin_plazo", "fuente": "derivado", "observado_en": CT,
                                              "declarado": True})
        self.assertEqual([r[t]["orden_plan"]["valor"] for t in ("T01", "T10", "T11", "T19", "T20", "T28")], [1, 10, 1, 9, 1, 9])
        self.assertEqual(r["T11"]["orden_plan"], {"valor": 1, "fuente": "git", "observado_en": CT, "declarado": True})
        r = calcula(equipo=leer("g14/equipo-1.md"), plan=leer("g14/plan-1.md"), jurado=False)["tareas"]
        self.assertEqual(r["T01"]["franja"]["motivo"], "sin_plazo")
        plan = ("## Por persona\n### Persona A · x\n| ID | Hasta | Bloque | Tarea | Cómo se comprueba |\n|---|---|---|---|---|\n"
                "| T01 | sáb 10:00 | B | a | b |\n| T02 | sáb 10:00 | | c | d |\n| T03 | sáb 09:00 | | e | f |\n"
                "| T04 | hora por confirmar | | g | h |\n| T05 | 11:30 | | i | j |\n")
        r = calcula(equipo=EQUIPO_03, plan=plan, jurado=False)["tareas"]
        self.assertEqual(r["T01"]["franja"]["valor"]["min"], 450)                           # 15 h / 2, hacia arriba
        self.assertEqual(r["T03"]["franja"]["motivo"], "orden")                             # no es posterior al desde
        # T05: desde el Hasta resuelto anterior (T03, sáb 09:00), saltando el de T04, que no se resuelve
        self.assertEqual(r["T05"]["franja"]["valor"], {"desde": "2026-09-19T09:00:00+02:00", "hasta": "2026-09-19T11:30:00+02:00",
                                                        "min": 150, "compartida": 1})
        r = calcula(equipo="## Hackathon\n- Entrega: 2026-09-20 10:00 (Europe/Madrid)\n", plan=plan.replace("sáb 10:00",
                    "20 sep 10:00"), jurado=False)["tareas"]
        self.assertEqual(r["T01"]["franja"]["motivo"], "sin_inicio")

    def test_hitos_y_otras_entregas(self):
        for mo in self.hechos["momentos"]:
            r = self.momento(mo)["ruta"]
            otras = [(o["nombre"], o["valor"], o["texto"], o["donde"]) for o in r["otras_entregas"]]
            self.assertEqual(len(otras), len(mo["entrega"]["discrepancias"]), otras)        # no «entregables»
            for o, d in zip(r["otras_entregas"], mo["entrega"]["discrepancias"]):
                self.assertTrue(mismo(o["valor"], d["valor"]))
                self.assertEqual((o["texto"], o["donde"], o["nombre"]), (d["texto"], "plan.md", "Entrega final (pitch: hora "
                                                                                                "por confirmar)"))
            self.assertTrue(mismo(r["entrega"]["valor"], mo["entrega"]["valor"]))
        r = calcula(equipo=leer("g14/equipo-1.md"), plan=leer("g14/plan-1.md"), jurado=False)["ruta"]
        self.assertEqual([(h["texto"], h["valor"], h["motivo"]) for h in r["hitos"]][:3],
                         [("H+1", None, "sin_dato"), ("H+17", None, "sin_dato"), ("H+27", None, "sin_dato")])
        r = calcula(equipo=EQUIPO_03, plan=leer("g13/plan.md"), jurado=False)["ruta"]
        self.assertEqual([(h["texto"], h["motivo"]) for h in r["hitos"]][1], ("sáb mañana (hora por confirmar)", "por_confirmar"))
        self.assertEqual([o["nombre"][:16] for o in r["otras_entregas"]], ["Entrega final (p"])   # la temprana es un hito
        self.assertIn("Entrega temprana", [h["nombre"][:16] for h in r["hitos"]])
        crit = ("## 2026-09-19 11:20 · Marta (organización)\n- Qué dijo: «Se entrega antes del domingo a las 09:00»\n"
                "- Fuerza: dato\n- Afecta a: entrega\n- Anotado por: @persona-c\n"
                "## 2026-09-19 11:25 · Marta (organización)\n- Qué dijo: «El pitch, a las 10:00»\n- Fuerza: dato\n"
                "- Afecta a: entrega\n- Anotado por: @persona-c\n")
        r = calcula(equipo=EQUIPO_03, criterios=crit, jurado=False)["ruta"]
        self.assertEqual([(o["valor"], o["texto"], o["cita"], o["donde"]) for o in r["otras_entregas"]],
                         [("2026-09-20T09:00:00+02:00", None, "2026-09-19 11:20", "criterios.md")])   # una hora suelta, no

    def test_descansos_de_g14_como_dicen_los_hechos(self):
        for mo in self.hechos["momentos"]:
            r = self.momento(mo)["ruta"]
            self.assertEqual(len(r["descansos"]), len(mo["descansos"]["filas"]))         # una entrada por turno
            for d, h in zip(r["descansos"], mo["descansos"]["filas"]):
                self.assertIn(h["texto"], d["texto"])
                self.assertEqual(d["personas"], h["personas"])
                self.assertTrue(mismo(d["desde"], h["desde"]) and mismo(d["hasta"], h["hasta"]), (d, h))
                self.assertEqual(d["motivo"], None if mo["descansos"]["resueltos"] else "sin_inicio")
            con_jsonschema(self, estado_minimo(ruta=r))

    def test_descansos_en_lista_y_los_que_no_se_leen(self):
        plan = ("## Descansos\n- Todos: sáb 03:00–07:00\n- @persona-a: sáb 23:30-dom 07:00\n- Persona C: sáb 08:00—09:00\n"
                "- Persona B: cuando pueda\n")
        r = calcula(equipo=EQUIPO_03, plan=plan, jurado=False)["ruta"]["descansos"]
        self.assertEqual([(d["personas"], d["desde"], d["hasta"], d["motivo"]) for d in r], [
            (["persona-a", "persona-b", "persona-c"], "2026-09-19T03:00:00+02:00", "2026-09-19T07:00:00+02:00", None),
            (["persona-a"], "2026-09-19T23:30:00+02:00", "2026-09-20T07:00:00+02:00", None),
            (["persona-c"], "2026-09-19T08:00:00+02:00", "2026-09-19T09:00:00+02:00", None),
            (["persona-b"], None, None, "formato")])
        self.assertEqual(r[0]["texto"], "- Todos: sáb 03:00–07:00")
        sin_equipo = calcula(equipo=EQUIPO_03, plan=plan, jurado=False, personas=[])["ruta"]["descansos"]
        self.assertEqual(sin_equipo[0]["personas"], None)                                   # «Todos» sin equipo: null
        r = calcula(plan=plan, jurado=False)["ruta"]["descansos"]
        self.assertEqual({d["motivo"] for d in r}, {"sin_zona", "formato"})
        personas = [{"persona": x.lower(), "nombre": x} for x in "ABCDE"]
        dos = calcula(equipo=EQUIPO_03, plan=leer("02-facturas-real-plan.md", EJEMPLOS), jurado=False,
                      personas=personas)["ruta"]["descansos"]
        self.assertEqual([(d["personas"], d["desde"], d["hasta"], d["motivo"]) for d in dos][:2], [
            (["e"], "2026-09-19T00:30:00+02:00", "2026-09-19T07:00:00+02:00", None),
            (["a"], "2026-09-19T01:00:00+02:00", "2026-09-19T06:00:00+02:00", None)])
        self.assertEqual((len(dos), {d["motivo"] for d in dos}), (9, {None}))

    def test_plan_mal_formado_no_da_campos(self):
        r = calcula(equipo=EQUIPO_03, plan="## Por persona\n| T01 | x | y |\n")
        self.assertEqual(r["tareas"], {})
        self.assertEqual(r["ruta"]["hitos"], [])

    def test_g14_contra_el_esquema(self):
        for mo in self.hechos["momentos"]:
            r = calcula(equipo=leer(mo["equipo.md"].replace("guiones/", "")), plan=leer(mo["plan.md"].replace("guiones/", "")),
                        criterios=leer("g13/criterios.md"), pitch=leer("g13/pitch.md"))
            tareas = [dict({"id": t, "titulo": "x", "dueno": "persona-a", "estado": {"valor": "lista", "fuente": "derivado",
                                                                                    "observado_en": CT}}, **c)
                      for t, c in sorted(r["tareas"].items())]
            con_jsonschema(self, estado_minimo(tareas=tareas, jurado=r["jurado"], ruta=r["ruta"]))


# =============================================================================================== historia
def transiciones_a_fuerza(tareas, issues, eventos, personas):
    """La historia con el motor de verdad: modelo.calcular a la hora de cada evento y de cada acción de GitHub."""
    horas = sorted({e["ts"] for e in eventos} | {a["ts"] for i in issues.values() for a in i["acciones"]}, key=fecha)
    salida = {t["id"]: {"primera_senal": None, "hecha_en": None, "nuevo": None, "hecha": False} for t in tareas}
    for ts in horas:
        for x in modelo.calcular(tareas, issues, eventos, personas, ts)["tareas"]:
            s, v = salida[x["id"]], x["estado"]["valor"]
            if v == "en_curso":
                s["primera_senal"] = s["primera_senal"] or ts
                if s["hecha_en"] and s["nuevo"] is None:
                    s["nuevo"] = ts
            if v in HECHAS and not s["hecha"]:
                s["hecha_en"], s["nuevo"] = s["hecha_en"] or ts, None
            s["hecha"] = v in HECHAS
    return {t: (s["primera_senal"], s["hecha_en"], None if s["hecha"] else s["nuevo"]) for t, s in salida.items()}


class Historia(unittest.TestCase):
    def guion(self, nombre):
        g = carga(os.path.join(GUIONES, nombre))
        return g, montar(g, SIM)

    def test_igual_que_el_motor_en_cada_evento(self):
        for nombre in ("G2.json", "G3.json", "G4.json", "G13.json", "G14.json", "G14r.json"):
            _, (tareas, personas, issues, eventos, ts) = self.guion(nombre)
            fin = max(e["ts"] for e in eventos)
            hs = modelo.historias(tareas, issues, eventos, personas, fin)
            esperado = transiciones_a_fuerza(tareas, issues, eventos, personas)
            real = {t: (h["primera_senal"], h["hecha_en"], h["trabajo_nuevo_desde"]) for t, (h, _) in hs.items()}
            self.assertEqual(real, esperado, nombre)
            for h, _ in hs.values():
                self.assertEqual(h["fuente"], "derivado")
                self.assertIsNotNone(fecha(h["observado_en"]))

    def test_g13_evidencia_y_trabajo_nuevo_como_dicen_los_hechos(self):
        g, (tareas, personas, issues, eventos, _) = self.guion("G13.json")
        hechos = carga(os.path.join(GUIONES, "g13", "hechos.json"))
        for mo in hechos["momentos"]:
            hs = modelo.historias(tareas, issues, eventos, personas, mo["ahora"])
            for nid, n in mo["notas"].items():
                for ev in n["evidencia"]:
                    historia, evidencia = hs[ev["tarea"]]
                    self.assertEqual((evidencia["valor"], evidencia["tipo"], evidencia["observado_en"]),
                                     (ev["sha"], "commit", ev["observado_en"]), (mo["nombre"], nid))
                    publicada = modelo.calcular(tareas, issues, eventos, personas, ev["observado_en"])
                    self.assertEqual(next(t for t in publicada["tareas"] if t["id"] == ev["tarea"])["estado"]["valor"],
                                     "publicada")
                    self.assertLessEqual(fecha(historia["hecha_en"]), fecha(ev["observado_en"]))
                for t in n["tareas"]:
                    nuevo = hs[t][0]["trabajo_nuevo_desde"]
                    self.assertEqual(nuevo if t == "T11" else None, n["trabajo_nuevo_desde"] if t == "T11" else None)
                for t in n["cerradas_a_mano"]:                     # cerrada a mano: ni hecha ni evidencia
                    self.assertEqual((hs[t][0]["hecha_en"], hs[t][1]), (None, None))
        m2 = modelo.historias(tareas, issues, eventos, personas, hechos["momentos"][1]["ahora"])["T11"]
        self.assertEqual((m2[0]["hecha_en"], m2[0]["trabajo_nuevo_desde"], m2[1]["valor"]),
                         ("2026-09-18T21:20:00Z", "2026-09-19T12:15:00Z", "111c0de"))
        m3 = modelo.historias(tareas, issues, eventos, personas, hechos["momentos"][2]["ahora"])["T11"]
        self.assertEqual((m3[0]["hecha_en"], m3[0]["trabajo_nuevo_desde"], m3[1]["valor"]),
                         ("2026-09-18T21:20:00Z", None, "112c0de"))

    def test_g14_hechas_como_dicen_los_hechos(self):
        hechos = carga(os.path.join(GUIONES, "g14", "hechos.json"))
        for mo in hechos["momentos"]:
            _, (tareas, personas, issues, eventos, _) = self.guion(mo["guion"])
            hs = modelo.historias(tareas, issues, eventos, personas, mo["ahora"])
            for p, b in mo["base"].items():
                for x in b["hechas"]:
                    h = hs[x["tarea"]][0]
                    self.assertEqual(h["hecha_en"], x["publicada_en"], (mo["nombre"], x["tarea"]))
                    # primera_senal es el primer paso a en_curso (la primera actividad); en los hechos de G14 es la
                    # primera señal, el reclamo, 30 s antes
                    self.assertEqual(fecha(h["primera_senal"]) - fecha(x["primera_senal"]), timedelta(seconds=30))
            abiertas = [t for t, v in mo["tareas"].items() if v not in HECHAS]
            self.assertTrue(all(hs[t][0]["hecha_en"] is None and hs[t][1] is None for t in abiertas))

    def test_cache_por_tarea_y_sin_latidos(self):
        _, (tareas, personas, issues, eventos, _) = self.guion("G14.json")
        fin = max(e["ts"] for e in eventos)
        cache = {}
        uno = modelo.historias(tareas, issues, eventos, personas, fin, cache=cache)
        latido = {"v": 1, "id": "latido-persona-a-0", "ts": fin, "actor": {"persona": "persona-a", "papel": "principal"},
                  "tipo": "latido", "fuente": "hook", "tarea": "T27"}
        dos = modelo.historias(tareas, issues, eventos + [latido], personas, fin, cache=cache)
        self.assertTrue(all(uno[t] is dos[t] for t in uno))                           # el latido no cuenta
        nuevo = {"v": 1, "id": "x-1", "ts": fin, "actor": {"persona": "persona-c", "papel": "principal", "sesion": "s-c"},
                 "tipo": "edicion", "fuente": "hook", "tarea": "T28"}
        tres = modelo.historias(tareas, issues, eventos + [nuevo], personas, fin, cache=cache)
        self.assertEqual([t for t in uno if uno[t] is not tres[t]], ["T28"])
        self.assertEqual(tres["T28"][0]["primera_senal"], fin)
        self.assertEqual(tres["T28"][0]["ultima_senal"], fin)          # #56, 2: el evento nuevo invalida la caché

    def test_56_2_ultima_senal_solo_de_lo_atribuido_a_la_tarea(self):
        """#56, punto 2: historia.ultima_senal es la hora del último commit con su ID o de la última edición atribuida
        a ella sin ambigüedad. No cuentan los latidos, los push, las acciones del issue, los commits sin ID (aunque la
        regla 9 los atribuya) ni las ediciones con atribucion_ambigua; null si no hay ninguno."""
        a = {"persona": "persona-a", "papel": "principal", "sesion": "s-a"}
        humano = {"persona": "persona-a", "papel": "humano"}

        def ev(i, minuto, tipo, actor=a, **extra):
            return dict({"v": 1, "id": f"e{i}", "ts": f"2026-09-19T10:{minuto:02d}:00Z", "actor": actor, "tipo": tipo,
                         "fuente": "git" if tipo in ("commit", "push") else "mcp" if tipo == "reclamo" else "hook"}, **extra)
        tareas = [{"id": t, "titulo": t, "dueno": "persona-a", "depende_de": []} for t in ("T01", "T02", "T03")]
        issues = {t: {"creado_en": "2026-09-19T09:00:00Z", "acciones": []} for t in ("T01", "T02", "T03")}
        issues["T01"]["acciones"] = [{"accion": "etiqueta", "ts": "2026-09-19T10:50:00Z", "por": "persona-a"}]
        eventos = [ev(1, 0, "reclamo", tarea="T01"),
                   ev(2, 5, "edicion", rutas=["a.py"]),                                   # atribuida a T01: cuenta
                   ev(3, 10, "commit", humano, tarea="T01", datos={"sha": "aaa0001", "rama": "main"}),   # con ID
                   ev(4, 15, "commit", humano, datos={"sha": "aaa0002", "rama": "main"}),              # sin ID: no
                   ev(6, 25, "latido", tarea="T01"),
                   ev(7, 30, "reclamo", tarea="T02"),
                   ev(8, 35, "edicion", rutas=["b.py"]),                                  # T01 y T02: ambigua
                   ev(5, 45, "push", humano, datos={"sha": "aaa0002", "incluye": ["aaa0001", "aaa0002"]})]   # la publica
        hs = modelo.historias(tareas, issues, eventos, PERSONAS, "2026-09-19T11:00:00Z")
        self.assertEqual({t: h["ultima_senal"] for t, (h, _) in hs.items()},
                         {"T01": "2026-09-19T10:10:00Z", "T02": None, "T03": None})
        # La edición de T02 con su ID sí cuenta, aunque haya dos abiertas.
        eventos.append(ev(9, 40, "edicion", tarea="T02", rutas=["b.py"]))
        hs = modelo.historias(tareas, issues, eventos, PERSONAS, "2026-09-19T11:00:00Z")
        self.assertEqual(hs["T02"][0]["ultima_senal"], "2026-09-19T10:40:00Z")


# =============================================================================================== relay
def git(repo, *args, env=None):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", check=True,
                          env=env).stdout.strip()


class SondeoFijo:
    """Las tareas e issues de un guion, como las daría el sondeo de GitHub."""
    estado, fuente, ultimo_ok = "ok", "github", None

    def __init__(self, tareas, issues):
        self.tareas, self.issues = tareas, issues

    def resultado(self, ahora=None):
        return self.tareas, self.issues, [], 0


class Relay(SinZoneinfo):
    """Un remoto bare temporal, el clon de una persona que sube y el clon del relay, que lee su origin/main."""
    AHORA = "2026-09-19T18:30:00Z"            # G13, M3

    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.bare, self.persona, self.clon = (os.path.join(self.dir, n) for n in ("equipo.git", "persona", "relay-clon"))
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.bare], check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", self.bare, self.persona], check=True, capture_output=True)
        for k, v in (("user.name", "x"), ("user.email", "x@example.com"), ("core.autocrlf", "false")):
            git(self.persona, "config", k, v)
        self.escribe(".hackathon/criterios.md", leer("g13/criterios.md"))
        self.sube("criterios", "2026-09-19T11:31:00Z")
        self.escribe(".hackathon/equipo.md", leer("g14/equipo-2.md"))
        self.escribe(".hackathon/pitch.md", leer("g13/pitch.md"))
        self.sube("equipo y pitch", "2026-09-19T07:31:00Z")
        self.escribe(".hackathon/plan.md", leer("g13/plan.md"))
        self.escribe(".hackathon/servicios.md", "# Servicios\n## Servicios\n| Nombre | Carpeta | Puerto | Arranque | Salud | "
                     "Dueño |\n|---|---|---|---|---|---|\n| api | api/ | 8000 | — | /salud | — |\n| web | web/ | — | — | — "
                     "| — |\n\n## Conexiones\n| De | A | Contrato | Prueba |\n|---|---|---|---|\n| web | api | web → api | "
                     "`curl` |\n")
        self.sube("plan", "2026-09-19T09:41:00Z")
        subprocess.run(["git", "clone", "-q", self.bare, self.clon], check=True, capture_output=True)
        self.g13 = carga(os.path.join(GUIONES, "G13.json"))
        self.tareas, _, self.issues, self.eventos, _ = montar(self.g13, SIM)

    def escribe(self, ruta, texto, base=None):
        p = os.path.join(base or self.persona, ruta)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)

    def sube(self, mensaje, cuando):
        env = dict(os.environ, GIT_AUTHOR_DATE=cuando, GIT_COMMITTER_DATE=cuando)
        git(self.persona, "add", "-A")
        git(self.persona, "commit", "-qm", mensaje, env=env)
        git(self.persona, "push", "-q", "origin", "main")

    def relay(self, jurado=True, ruta=True, carpeta="relay", git_=relay_mod._git, eventos=True, novedades=True):
        n = relay_mod.Novedades(self.clon, 300, git=git_, vista_jurado=jurado, ruta_critica=ruta) if novedades else None
        if n:
            n.sondear()
        r = relay_mod.Relay(os.path.join(self.dir, carpeta), PERSONAS, ahora=lambda: self.AHORA,
                            sondeo=SondeoFijo(self.tareas, self.issues), novedades=n, vista_jurado=jurado, ruta_critica=ruta)
        if eventos:
            for i in range(0, len(self.eventos), 200):
                r.recibir({"eventos": self.eventos[i:i + 200]})
        r.recalcular()
        return r

    def test_con_los_dos_interruptores_y_contra_el_esquema(self):
        r = self.relay()
        e = r.estado
        con_jsonschema(self, e)
        self.assertEqual((e["jurado"]["fichero"]["valor"], len(e["jurado"]["notas"])), ("ok", 8))
        self.assertEqual(e["jurado"]["notas"][0]["observado_en"], "2026-09-19T11:31:00Z")    # la hora del commit
        self.assertEqual(e["jurado"]["pitch"]["observado_en"], "2026-09-19T07:31:00Z")
        self.assertTrue(mismo(e["jurado"]["notas"][0]["hora"], "2026-09-18T17:30:00Z"))
        t = {x["id"]: x for x in e["tareas"]}
        self.assertEqual(t["T06"]["criterios"]["valor"], ["2026-09-19 10:40"])
        self.assertEqual(t["T06"]["criterios"]["observado_en"], "2026-09-19T09:41:00Z")
        self.assertEqual(len(t["T02"]["conexiones"]["valor"]), 1)
        self.assertEqual((t["T11"]["evidencia"]["valor"], t["T11"]["evidencia"]["observado_en"],
                          t["T11"]["historia"]["hecha_en"]), ("112c0de", "2026-09-19T13:00:00Z", "2026-09-18T21:20:00Z"))
        self.assertNotIn("evidencia", t["T20"])                                              # cerrada a mano
        self.assertEqual(t["T05"]["hasta"]["valor"], "2026-09-19T02:30:00+02:00")
        self.assertEqual((t["T05"]["orden_plan"]["valor"], t["T13"]["franja"]["valor"]["compartida"]), (5, 3))
        ruta = e["ruta"]
        self.assertEqual((ruta["equipo"]["valor"], ruta["zona"]["valor"], ruta["inicio"]["valor"]),
                         ("ok", "Europe/Madrid", "2026-09-18T19:00:00+02:00"))
        self.assertEqual(len(ruta["descansos"]), 5)                     # 5 turnos; uno es de dos personas
        self.assertEqual(e["jurado"]["zona"], ruta["zona"])
        self.assertEqual(ruta["hitos"][0]["observado_en"], "2026-09-19T09:41:00Z")

    def test_cuatro_combinaciones(self):
        JURADO, RUTA = {"criterios", "conexiones"}, {"hasta", "franja", "orden_plan"}
        base = self.relay(False, False, "r0")
        claves_base = {k for x in base.estado["tareas"] for k in x}
        for jurado, ruta in ((False, False), (True, False), (False, True), (True, True)):
            r = self.relay(jurado, ruta, f"r-{jurado}-{ruta}")
            e = r.estado
            con_jsonschema(self, e)
            claves = {k for x in e["tareas"] for k in x}
            self.assertEqual("jurado" in e, jurado)
            self.assertEqual("ruta" in e, ruta)
            self.assertEqual(bool(claves & JURADO), jurado)
            self.assertEqual(bool(claves & RUTA), ruta)
            self.assertEqual({"historia", "evidencia"} <= claves, jurado or ruta)
            if not (jurado or ruta):
                self.assertEqual(r.texto, base.texto)
                self.assertEqual(claves, claves_base)

    def test_apagado_sin_lecturas_ni_campos(self):
        llamadas = []

        def espia(repo, *args, **k):
            llamadas.append(args)
            return relay_mod._git(repo, *args, **k)
        r = self.relay(False, False, git_=espia)
        m10 = ("plan.md", "equipo.md", "pitch.md", "servicios.md")
        self.assertFalse([a for a in llamadas if any(f in x for x in a for f in m10)])
        self.assertFalse([a for a in llamadas if a[0] == "ls-tree"])
        self.assertIsNone(r.novedades.m10)
        self.assertEqual(r.novedades.m10_rutas, {})
        self.assertNotIn(b'"historia"', r.texto)
        sin = relay_mod.Relay(os.path.join(self.dir, "sin"), PERSONAS, ahora=lambda: self.AHORA,
                              sondeo=SondeoFijo(self.tareas, self.issues), novedades=r.novedades)
        sin.recibir({"eventos": self.eventos[:200]})
        sin.recibir({"eventos": self.eventos[200:]})
        sin.recalcular()
        self.assertEqual(sin.texto, r.texto)                                                # el Relay de antes de M10

    def test_lee_origin_main_y_no_la_copia_del_clon(self):
        r = self.relay(eventos=False)
        self.escribe(".hackathon/equipo.md", "# Equipo\n## Hackathon\n- Inicio: 2026-09-18 20:00 (Europe/Madrid)\n", self.clon)
        n = r.novedades
        n.sondear()
        r.recalcular()
        self.assertEqual(r.estado["ruta"]["inicio"]["valor"], "2026-09-18T19:00:00+02:00")    # lo del clon no cuenta
        self.escribe(".hackathon/equipo.md", leer("g14/equipo-1.md"))
        self.sube("equipo sin inicio", "2026-09-19T12:00:00Z")
        n.sondear()
        r.recalcular()
        self.assertEqual((r.estado["ruta"]["inicio"]["motivo"], r.estado["ruta"]["equipo"]["observado_en"]),
                         ("por_confirmar", "2026-09-19T12:00:00Z"))
        t = {x["id"]: x for x in r.estado["tareas"]}
        self.assertEqual(t["T05"]["hasta"]["motivo"], "sin_inicio")
        git(self.persona, "rm", "-q", ".hackathon/criterios.md")
        self.sube("sin criterios", "2026-09-19T13:00:00Z")
        n.sondear()
        r.recalcular()
        self.assertEqual(r.estado["jurado"]["fichero"], {"valor": "sin fichero", "fuente": "git",
                                                         "observado_en": "2026-09-19T13:00:00Z", "declarado": True})

    def test_sin_cambios_no_vuelve_a_leer_los_ficheros(self):
        llamadas = []

        def espia(repo, *args, **k):
            llamadas.append(args)
            return relay_mod._git(repo, *args, **k)
        r = self.relay(git_=espia, eventos=False)
        del llamadas[:]
        r.novedades.sondear()
        lecturas_m10 = [a for a in llamadas if a[0] == "log" and "--" in a]
        self.assertEqual(lecturas_m10, [])                                                  # ni log del fichero ni show

    def test_una_lectura_que_falla_conserva_el_ultimo_bueno(self):
        reloj = [1000.0]
        falla = [False]

        def git_(repo, *args, **k):
            if falla[0] and args[0] == "ls-tree" and ".hackathon/plan.md" in args:
                return None
            return relay_mod._git(repo, *args, **k)
        n = relay_mod.Novedades(self.clon, 300, git=git_, reloj=lambda: reloj[0], vista_jurado=True, ruta_critica=True)
        n.sondear()
        bueno = n.m10
        falla[0] = True
        reloj[0] += 100
        n.sondear()
        self.assertIs(n.m10, bueno)
        self.assertIsNone(n.fuente())
        reloj[0] += 301
        n.sondear()
        self.assertEqual(n.fuente(), {"valor": "sin leer jurado y ruta", "fuente": "git",
                                      "observado_en": relay_mod.iso_us(1000.0)})
        falla[0] = False
        n.sondear()
        self.assertIsNone(n.fuente())

    def test_utf16_y_crlf_en_main(self):
        md = leer("g13/criterios.md").replace("\n", "\r\n")
        with open(os.path.join(self.persona, ".hackathon", "criterios.md"), "wb") as f:
            f.write(b"\xff\xfe" + md.encode("utf-16-le"))
        self.sube("criterios en utf-16", "2026-09-19T14:00:00Z")
        r = self.relay(eventos=False)
        self.assertEqual(len(r.estado["jurado"]["notas"]), 8)

    def test_historia_desde_eventos_jsonl_al_arrancar(self):
        uno = self.relay()
        dos = relay_mod.Relay(os.path.join(self.dir, "relay"), PERSONAS, ahora=lambda: self.AHORA,
                              sondeo=SondeoFijo(self.tareas, self.issues), novedades=uno.novedades, vista_jurado=True,
                              ruta_critica=True)
        self.assertEqual(len(dos.eventos), len(self.eventos))
        historia = lambda r: {x["id"]: (x.get("historia"), x.get("evidencia")) for x in r.estado["tareas"]}
        self.assertEqual(historia(dos), historia(uno))
        dos.latido({"persona": "persona-c", "actores": [{"papel": "principal", "sesion": "s-c", "tarea": "T28",
                                                          "ultima_senal": self.AHORA}]})
        dos.recalcular()
        self.assertEqual(historia(dos), historia(uno))                                      # un latido no es historia
        with open(os.path.join(self.dir, "relay", "eventos.jsonl"), encoding="utf-8") as f:
            self.assertEqual(sum(1 for _ in f), len(self.eventos))

    def test_push_de_un_demonio_adelanta_la_lectura(self):
        push = {"v": 1, "id": "git-persona-a-push-1", "ts": self.AHORA, "actor": {"persona": "persona-a", "papel": "demonio"},
                "tipo": "push", "fuente": "git", "datos": {"sha": "abc1234", "incluye": []}}
        for jurado, ruta, esperado in ((False, False, False), (True, False, True), (False, True, True)):
            r = self.relay(jurado, ruta, f"p-{jurado}-{ruta}", eventos=False)
            r.push_visto.clear()
            r.recibir({"eventos": [dict(push, id=f"{push['id']}-{jurado}-{ruta}")]})
            self.assertEqual(r.push_visto.is_set(), esperado)

    def test_sin_novedades_solo_la_historia(self):
        r = self.relay(novedades=False)
        self.assertNotIn("jurado", r.estado)
        self.assertNotIn("ruta", r.estado)
        self.assertTrue(all("historia" in x for x in r.estado["tareas"]))
        con_jsonschema(self, r.estado)


class Interruptores(unittest.TestCase):
    def test_lectura_de_os_md(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        ruta = os.path.join(d, "os.md")
        for texto, j, r in (("activa: sí\n", False, False),
                            ("vista_jurado: sí   # R-35\nruta_critica: no\n", True, False),
                            ("vista_jurado: no\nruta_critica: yes\n", False, True),
                            ("\ufeffvista_jurado: si\r\nruta_critica: sí\r\n", True, True)):
            with open(ruta, "w", encoding="utf-8", newline="") as f:
                f.write(texto)
            self.assertEqual((red.vista_jurado(ruta), red.ruta_critica(ruta)), (j, r), texto)
        with open(ruta, "wb") as f:
            f.write("\ufeffvista_jurado: sí\n".encode("utf-16-le"))
        self.assertTrue(red.vista_jurado(ruta))
        self.assertFalse(red.vista_jurado(None) or red.ruta_critica(os.path.join(d, "no-existe.md")))


# =============================================================================================== issue #46
class Issue46(SinZoneinfo):
    """Las decisiones 4, 5 y 6 del issue #46 y B4, B6 y B9: cada caso fallaba con lo de K-104."""

    def equipo(self, inicio="2026-09-18 19:00 (Europe/Madrid)", entrega="2026-09-20 10:00 (Europe/Madrid)"):
        return f"# Equipo\n\n## Hackathon\n- Inicio: {inicio}\n- Entrega: {entrega}\n"

    def test_4_un_descanso_por_turno_con_sus_personas(self):
        for e, p in (("g14/equipo-2.md", "g14/plan-2.md"), ("g14/equipo-2.md", "g13/plan.md")):
            d = calcula(equipo=leer(e), plan=leer(p), jurado=False)["ruta"]["descansos"]
            self.assertEqual([x["personas"] for x in d], [["persona-c"], ["persona-b"], ["persona-a"],
                                                         ["persona-b", "persona-c"], ["persona-a"]], p)
            self.assertEqual((d[3]["desde"], d[3]["hasta"]), ("2026-09-19T23:00:00+02:00", "2026-09-20T07:30:00+02:00"))
            self.assertNotIn("persona", d[3])
        d = calcula(equipo=EQUIPO_03, plan=leer("03-xray-embat-real-plan.md", EJEMPLOS), jurado=False)["ruta"]["descansos"]
        self.assertEqual((len(d), d[3]["personas"]), (5, ["persona-b", "persona-c"]))
        plan = "## Descansos\n- Persona B y @persona-c: sáb 23:00–dom 07:30\n- Todos: dom 08:00–08:30\n"
        d = calcula(equipo=EQUIPO_03, plan=plan, jurado=False)["ruta"]["descansos"]
        self.assertEqual([(x["personas"], x["desde"], x["hasta"]) for x in d], [
            (["persona-b", "persona-c"], "2026-09-19T23:00:00+02:00", "2026-09-20T07:30:00+02:00"),
            (["persona-a", "persona-b", "persona-c"], "2026-09-20T08:00:00+02:00", "2026-09-20T08:30:00+02:00")])

    def test_5_dos_horas_la_primera_manda_y_la_otra_es_otra_entrega(self):
        personas = [{"persona": x.lower(), "nombre": x} for x in "ABCDE"]
        for entrega in ("2026-09-20 10:00 (cierre 11:00) (Europe/Madrid)", "dom 20 sep 10:00 (cierre 11:00), Europe/Madrid"):
            r = calcula(equipo=self.equipo(entrega=entrega), plan=leer("02-facturas-real-plan.md", EJEMPLOS), jurado=False,
                        personas=personas)["ruta"]
            self.assertEqual((r["entrega"]["valor"], r["entrega"]["motivo"]), ("2026-09-20T10:00:00+02:00", None), entrega)
            self.assertEqual([(o["valor"], o["donde"]) for o in r["otras_entregas"]],
                             [("2026-09-20T11:00:00+02:00", "equipo.md"), ("2026-09-20T10:00:00+02:00", "plan.md")])
            self.assertEqual((r["otras_entregas"][0]["texto"], r["otras_entregas"][0]["observado_en"]), (entrega, CT))
            self.assertEqual(r["otras_entregas"][1]["nombre"], "Entrega final (guía `/entrega`)")
            nombres = [h["nombre"] for h in r["hitos"]]                         # las tempranas son hitos (y no entregas)
            self.assertEqual([n[:16] for n in nombres if n.startswith("Entrega")], ["Entrega temprana"] * 2)
            con_jsonschema(self, estado_minimo(ruta=r))
        # la misma hora dos veces, o una zona con forma de hora, no son dos horas
        for entrega in ("2026-09-20 10:00 (10:00) +02:00", "2026-09-20 10:00 UTC+02:00"):
            r = calcula(equipo=self.equipo(entrega=entrega), jurado=False)["ruta"]
            self.assertEqual((r["entrega"]["valor"], r["otras_entregas"]), ("2026-09-20T10:00:00+02:00", []), entrega)
        r = calcula(equipo=self.equipo(inicio="2026-09-18 19:00 (cierre 20:00) (Europe/Madrid)"), jurado=False)["ruta"]
        self.assertEqual((r["inicio"]["valor"], r["inicio"]["motivo"]), (None, "dos_horas"))   # en Inicio: no
        # En el esquema, dos_horas solo vale en Inicio: ($defs/hora_inicio); en Entrega: ($defs/hora_declarada), no.
        con_jsonschema(self, estado_minimo(ruta=r))
        mala = dict(r, entrega=dict(r["entrega"], valor=None, motivo="dos_horas"))
        self.assertIsNotNone(esquema_estado().error(estado_minimo(ruta=mala)))

    def test_5_fechas_con_dia_y_mes_y_sin_zona(self):
        casos = (("dom 20 sep 09:30 (Europe/Madrid)", "2026-09-20T09:30:00+02:00", None),
                 ("dom 20 sep 2026 10:00", "2026-09-20T10:00:00+02:00", None),        # el equipo.md real del reto 03
                 ("domingo, 20 sep. 2026 10:00", "2026-09-20T10:00:00+02:00", None),
                 ("sáb 20 sep 2026 10:00", None, "formato"))                          # el día no cuadra
        for entrega, valor, motivo in casos:
            r = calcula(equipo=self.equipo(entrega=entrega), jurado=False)["ruta"]
            self.assertEqual((r["entrega"]["valor"], r["entrega"]["motivo"]), (valor, motivo), entrega)
            self.assertEqual(r["zona"]["valor"], "Europe/Madrid")                     # la de Inicio:
        r = calcula(equipo=self.equipo(inicio="2026-09-18 19:00", entrega="dom 20 sep 2026 10:00"), jurado=False)["ruta"]
        self.assertEqual((r["entrega"]["valor"], r["entrega"]["motivo"]), (None, "sin_zona"))
        r = calcula(equipo=self.equipo(entrega="dom 20 sep 2026 10:00 (America/Bogota)"), jurado=False)["ruta"]
        self.assertEqual(r["entrega"]["motivo"], "sin_zona")             # una zona que no se resuelve no hereda la otra

    def test_5_b9_la_fila_entrega_solo_en_otras_entregas(self):
        hechos = carga(os.path.join(GUIONES, "g14", "hechos.json"))
        for mo in hechos["momentos"]:
            r = calcula(equipo=leer(mo["equipo.md"].replace("guiones/", "")), plan=leer(mo["plan.md"].replace("guiones/", "")),
                        jurado=False)["ruta"]
            self.assertFalse([h for h in r["hitos"] if h["nombre"].startswith("Entrega final")], mo["nombre"])
            self.assertEqual([o["texto"] for o in r["otras_entregas"]], ["dom 20 sep 09:30"])
        self.assertTrue(lecturas.es_entrega("Entrega") and lecturas.es_entrega("entrega final (guía)"))
        self.assertFalse(lecturas.es_entrega("Entrega temprana") or lecturas.es_entrega("Entregables listos"))

    def test_5_nota_dato_sin_su_texto(self):
        crit = ("## 2026-09-19 11:20 · Marta (organización)\n- Qué dijo: «Se entrega el domingo a las 09:00, sin prórroga»\n"
                "- Fuerza: dato\n- Afecta a: entrega\n- Anotado por: @persona-c\n")
        r = calcula(equipo=EQUIPO_03, criterios=crit, cts=dict(CTS, criterios="2026-09-19T09:25:00Z"))
        o = r["ruta"]["otras_entregas"]
        # §11.4: la cita de la nota (su hora), como pide $defs/hora_declarada con donde criterios.md; el texto, null.
        self.assertEqual(o, [{"valor": "2026-09-20T09:00:00+02:00", "texto": None, "motivo": None, "donde": "criterios.md",
                              "cita": "2026-09-19 11:20", "fuente": "git", "observado_en": "2026-09-19T09:25:00Z",
                              "declarado": True}])
        self.assertNotIn("prórroga", json.dumps(r["ruta"], ensure_ascii=False))
        con_jsonschema(self, estado_minimo(ruta=r["ruta"]))
        # ruta.py ya saca de la cita la hora de la nota: no le hace falta el texto.
        resumen = ruta_mod.calcular(r["ruta"], [], CT, personas=[])["resumen"]
        self.assertTrue(resumen.endswith(" · otra entrega: dom 09:00 (criterios.md, nota de 11:20)"), resumen)

    def test_6_evidencia_ultima_publicacion_con_su_hora_y_tipo(self):
        g = carga(os.path.join(GUIONES, "G13.json"))
        tareas, personas, issues, eventos, _ = montar(g, SIM)
        m3 = modelo.historias(tareas, issues, eventos, personas, "2026-09-19T18:30:00Z")["T11"][1]
        self.assertEqual(m3, {"valor": "112c0de", "tipo": "commit", "fuente": "git", "observado_en": "2026-09-19T13:00:00Z"})
        # parada tras hecha_en: sigue hecha, con su trabajo nuevo y la evidencia de la publicación anterior
        ahora = "2026-09-19T12:40:00Z"
        t11 = next(t for t in modelo.calcular(tareas, issues, eventos, personas, ahora)["tareas"] if t["id"] == "T11")
        h, ev = modelo.historias(tareas, issues, eventos, personas, ahora)["T11"]
        self.assertEqual((t11["estado"]["valor"], h["hecha_en"], h["trabajo_nuevo_desde"]),
                         ("parada", "2026-09-18T21:20:00Z", "2026-09-19T12:15:00Z"))
        self.assertEqual((ev["valor"], ev["observado_en"]), ("111c0de", "2026-09-18T21:20:00Z"))
        g = carga(os.path.join(GUIONES, "G2.json"))
        tareas, personas, issues, eventos, _ = montar(g, SIM)
        ev = modelo.historias(tareas, issues, eventos, personas, max(e["ts"] for e in eventos))["T15"][1]
        self.assertEqual((ev["valor"], ev["tipo"]), ("a15a15a", "fusion"))

    def test_56_4_titulo_plan_de_la_fila_del_plan_vigente(self):
        """#56, punto 4: lecturas da por tarea el título de su fila del plan.md vigente (tareas[].titulo_plan, solo con
        ruta_critica), y ruta.py decide con él «fuera de la entrega»: en G14, T18 pasa a [SI DA TIEMPO] en plan-2 y su
        issue sigue con el título de antes."""
        r = calcula(equipo=leer("g14/equipo-2.md"), plan=leer("g14/plan-2.md"), jurado=False)
        self.assertEqual(r["tareas"]["T18"]["titulo_plan"], {"valor": "[SI DA TIEMPO] Cada cifra lleva su moneda o «puntos»",
                                                             "fuente": "git", "observado_en": CT, "declarado": True})
        self.assertNotIn("titulo_plan", calcula(equipo=leer("g14/equipo-2.md"), plan=leer("g14/plan-2.md"),
                                                ruta=False)["tareas"]["T18"])
        issue = next(t for t in carga(os.path.join(GUIONES, "g14", "tareas.json"))["tareas"] if t["id"] == "T18")
        self.assertNotIn("SI DA TIEMPO", issue["titulo"])
        t18 = dict({"id": "T18", "titulo": issue["titulo"], "dueno": "persona-b", "depende_de": [],
                    "estado": {"valor": "lista", "fuente": "derivado", "observado_en": CT}, "declarado": None},
                   **r["tareas"]["T18"])
        b = ruta_mod.calcular(r["ruta"], [t18], CT, personas=PERSONAS)
        self.assertEqual([(x["tarea"], x["motivo"]) for x in b["fuera_de_entrega"]], [("T18", "si_da_tiempo")])

    def test_56_6_zona_iana_si_equipo_md_la_da_y_el_cambio_de_hora(self):
        """#56, punto 6, sin tzdata: ruta.zona (y jurado.zona) es la IANA si alguna línea de equipo.md la da y, si no, el
        desfase; con ella, un reto que cruza el cambio de hora del 25 oct 2026 resuelve y escribe bien las horas de
        antes (+02:00) y de después (+01:00)."""
        r = calcula(equipo=self.equipo(inicio="2026-10-24 10:00 +02:00", entrega="2026-10-25 12:00 (Europe/Madrid)"))
        self.assertEqual((r["ruta"]["zona"]["valor"], r["jurado"]["zona"]["valor"]), ("Europe/Madrid", "Europe/Madrid"))
        r = calcula(equipo=self.equipo(inicio="2026-10-24 10:00 +02:00", entrega="2026-10-25 12:00"))
        self.assertEqual(r["ruta"]["zona"]["valor"], "+02:00")
        plan = ("# Plan\n\n## Por persona\n\n### Persona A · todo\n| ID | Hasta | Bloque | Tarea | Cómo se comprueba |\n"
                "|---|---|---|---|---|\n| T01 | sáb 23:00 | x | Antes del cambio | Se ve |\n"
                "| T02 | dom 09:30 | x | Después del cambio | Se ve |\n")
        r = calcula(equipo=self.equipo(inicio="2026-10-24 10:00 (Europe/Madrid)", entrega="2026-10-25 12:00 (Europe/Madrid)"),
                    plan=plan, jurado=False)
        self.assertEqual([r["tareas"][t]["hasta"]["valor"] for t in ("T01", "T02")],
                         ["2026-10-24T23:00:00+02:00", "2026-10-25T09:30:00+01:00"])
        self.assertEqual(r["ruta"]["entrega"]["valor"], "2026-10-25T12:00:00+01:00")
        tareas = [dict({"id": t, "titulo": t, "dueno": "persona-a", "depende_de": [], "declarado": None,
                        "estado": {"valor": "lista", "fuente": "derivado", "observado_en": CT}}, **r["tareas"][t])
                  for t in ("T01", "T02")]
        b = ruta_mod.calcular(r["ruta"], tareas, "2026-10-25T08:00:00Z", personas=PERSONAS)
        self.assertIn("T01: plazo pasado 23:00", b["resumen"])                  # con el desfase fijo, «22:00»
        self.assertEqual(b["zona"], r["ruta"]["zona"])

    def test_56_desfase_iso_pegado_a_la_hora_es_zona(self):
        """#56 (sin decisión, fila 7): un desfase ISO 8601 pegado a la hora («10:00+02:00», «2026-09-20T10:00+02:00»)
        es la zona, no una segunda hora. Antes, su «02:00» daba una entrega fantasma a las 02:00 del día siguiente, y con
        todo en ISO, Inicio salía dos_horas y Entrega sin_zona."""
        r = calcula(equipo=self.equipo(entrega="2026-09-20 10:00+02:00"), jurado=False)["ruta"]
        self.assertEqual((r["entrega"]["valor"], r["entrega"]["motivo"], r["otras_entregas"]),
                         ("2026-09-20T10:00:00+02:00", None, []))
        r = calcula(equipo=self.equipo(inicio="2026-09-18T19:00+02:00", entrega="2026-09-20T10:00:00+02:00"), jurado=False)["ruta"]
        self.assertEqual([(r[k]["valor"], r[k]["motivo"]) for k in ("inicio", "entrega")],
                         [("2026-09-18T19:00:00+02:00", None), ("2026-09-20T10:00:00+02:00", None)])
        self.assertEqual((r["zona"]["valor"], r["otras_entregas"]), ("+02:00", []))
        self.assertEqual(lecturas.hora_equipo("2026-09-20T10:00-03:00", 2026)[0].isoformat(), "2026-09-20T10:00:00-03:00")
        # Un tramo «10:00-11:00» sigue siendo dos horas (con «-», solo detrás de una hora ISO con «T» es zona), y la zona
        # IANA de la línea manda sobre el desfase pegado.
        r = calcula(equipo=self.equipo(entrega="dom 20 sep 10:00-11:00, Europe/Madrid"), jurado=False)["ruta"]
        self.assertEqual((r["entrega"]["valor"], [o["valor"] for o in r["otras_entregas"]]),
                         ("2026-09-20T10:00:00+02:00", ["2026-09-20T11:00:00+02:00"]))
        self.assertEqual(lecturas.hora_equipo("2026-10-25T12:00+02:00 (Europe/Madrid)", 2026)[3], "Europe/Madrid")

    def test_b4_zona_en_el_bloque_jurado_y_b6_por_confirmar(self):
        r = calcula(equipo=leer("g14/equipo-2.md"), criterios=leer("g13/criterios.md"), ruta=False)
        self.assertIsNone(r["ruta"])
        self.assertEqual(r["jurado"]["zona"], {"valor": "Europe/Madrid", "fuente": "git", "observado_en": CT,
                                               "declarado": True})
        r = calcula(equipo=self.equipo(inicio="por confirmar", entrega="domingo, hora por confirmar (Europe/Madrid)"))["ruta"]
        self.assertEqual((r["inicio"]["motivo"], r["entrega"]["motivo"]), ("por_confirmar", "por_confirmar"))


# =============================================================================================== arranque
def registro_sintetico(horas=39, personas=PERSONAS, por_tarea_min=80, cada_s=30):
    """Un relay/eventos.jsonl de un reto de `horas` h: cada persona hace sus tareas una detrás de otra (reclamo,
    una edición cada `cada_s` s, commit con su ID y push) y su sesión latea cada minuto con un `arbol`."""
    t0 = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    iso = lambda s: (t0 + timedelta(seconds=s)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tareas, eventos, n = [], [], 0
    for i, p in enumerate(personas):
        actor = {"persona": p["persona"], "papel": "principal", "sesion": f"s-{i}"}
        s, k = 0, 0
        while s < horas * 3600:
            k += 1
            tid = f"T{len(tareas) + 1:02d}"
            tareas.append({"id": tid, "titulo": tid, "dueno": p["persona"], "depende_de": []})
            fin = s + por_tarea_min * 60
            eventos.append({"v": 1, "id": f"s-{i}-{n}", "ts": iso(s), "actor": actor, "tipo": "reclamo", "fuente": "mcp",
                            "tarea": tid})
            n += 1
            for x in range(s + 30, fin, cada_s):
                eventos.append({"v": 1, "id": f"s-{i}-{n}", "ts": iso(x), "actor": actor, "tipo": "edicion", "fuente": "hook",
                                "rutas": [f"src/{tid}.py"]})
                n += 1
            sha = hashlib.sha1(tid.encode()).hexdigest()[:7]
            eventos.append({"v": 1, "id": f"git-{n}", "ts": iso(fin), "actor": {"persona": p["persona"], "papel": "humano"},
                            "tipo": "commit", "fuente": "git", "tarea": tid, "datos": {"sha": sha, "alcanzable": False}})
            eventos.append({"v": 1, "id": f"git-{n}-p", "ts": iso(fin + 60), "actor": {"persona": p["persona"],
                                                                                       "papel": "demonio"},
                            "tipo": "push", "fuente": "git", "datos": {"sha": sha, "incluye": [sha]}})
            n += 1
            s = fin + 120
    issues = {t["id"]: {"creado_en": iso(0), "acciones": []} for t in tareas}
    return tareas, issues, eventos, iso(horas * 3600)


class Arranque(unittest.TestCase):
    """El arranque con un registro de 39 h (≈14.000 eventos): la historia sale entera y cuesta como mucho lo que ya
    cuesta el arranque sin M10 (modelo.calcular) más un margen, medido aquí en el mismo portátil."""

    def test_registro_grande(self):
        tareas, issues, eventos, ahora = registro_sintetico()
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "eventos.jsonl"), "w", encoding="utf-8") as f:
            for e in eventos:
                f.write(json.dumps(e) + "\n")
        tiempos = {}
        for m10 in (False, True):
            t = time.perf_counter()
            r = relay_mod.Relay(d, PERSONAS, ahora=lambda: ahora, sondeo=SondeoFijo(tareas, issues), vista_jurado=m10,
                                ruta_critica=m10)
            tiempos[m10] = time.perf_counter() - t
        print(f"\n  arranque con {len(eventos)} eventos y {len(tareas)} tareas: sin M10 {tiempos[False]:.2f} s, "
              f"con M10 {tiempos[True]:.2f} s", file=sys.stderr)
        h = {x["id"]: x["historia"] for x in r.estado["tareas"]}
        self.assertTrue(all(x["hecha_en"] and x["primera_senal"] for x in h.values()))
        self.assertEqual(len(r.estado["tareas"]), len(tareas))
        self.assertLess(tiempos[True], 2 * tiempos[False] + 5)
        t = time.perf_counter()
        r.recalcular()                                     # sin eventos nuevos: la historia, de la caché
        self.assertLess(time.perf_counter() - t, tiempos[False] + 2)


if __name__ == "__main__":
    unittest.main()
