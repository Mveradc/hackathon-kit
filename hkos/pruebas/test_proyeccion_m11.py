"""K-112 (M11): el nivel 2b en el modelo, el relay, la proyección y el MCP (api.md §0, §3, §5 y §6; ADR-0009, ADR-0014).

1. colisiones.calcular: por par, `2:<a>+<b>` rojo con `rutas` y `2b:<a>+<b>` amarillo con `rutas_2b` (cada una solo si
   tiene rutas; observado_en = desde y desde_2b), y las dos tapan el nivel 1 entre esas personas. Sin `rutas_2b`, la
   salida de la 0.5.0.
2. El relay lee `fusion_estructural:` de su os.md y se lo pasa al Calculo del nivel 2 (solo encendido: apagado, la
   llamada de la 0.5.0). Criterio 1 de M11, la parte sin relay vivo: con el interruptor apagado, estado.json, la vista y
   estado-equipo.md salen byte a byte como en la 0.5.0 con los mismos datos.
3. estado-equipo.md: «- AMARILLO · nivel 2b · fusión estructural sin conflictos · …» (decisión 7) y la firma de
   colisiones cambia al bajar o subir de nivel. El MCP: la frase de ADR-0014 en la descripción de `colisiones`.
4. Criterio 4 de M11 (R-24, R-25, R-25b, X) con delta.sh y escucha.sh tal como están: bajar de rojo a 2b da un delta de
   ≤ 600 caracteres y ninguna línea del monitor; volver a rojo, una línea del monitor; 30 minutos con un 2b estable no
   inyectan nada; pasados 6.000 caracteres, un 2b no se inyecta (una roja nueva, sí).

El Calculo de verdad (colisiones_merge.py, K-111) no hace falta: los `conflictos` se construyen a mano con la forma de
ADR-0014, `[{personas, rutas, rutas_2b, desde, desde_2b}]`.

Uso: uv run --no-project -m unittest hkos.pruebas.test_proyeccion_m11 -v
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from datetime import datetime, timedelta, timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.dirname(HKOS)
SIM = os.path.join(KIT, "evals", "coordinacion", "simulador")
sys.path[:0] = [HKOS, os.path.dirname(os.path.abspath(__file__)), SIM]
import colisiones  # noqa: E402
import colisiones_merge  # noqa: E402
import mcp  # noqa: E402
import modelo  # noqa: E402
import proyeccion as p  # noqa: E402
import red  # noqa: E402
import relay as relay_mod  # noqa: E402
import simula  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha, iso  # noqa: E402
from fixture import estado_5x20  # noqa: E402
from test_proyeccion import estado_base  # noqa: E402

ESTADO = Esquema("estado.schema.json")
MADRID = timezone(timedelta(hours=2))
BASH = shutil.which("bash")
if os.name == "nt" and shutil.which("git"):          # el bash de Git for Windows, no el de WSL (como prueba_hooks.py)
    _raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(_raiz, "bin", "bash.exe"), os.path.join(_raiz, "usr", "bin", "bash.exe"))
                 if os.path.exists(b)), BASH)
DELTA = os.path.join(KIT, "scripts", "os", "delta.sh").replace("\\", "/")
ESCUCHA = os.path.join(KIT, "scripts", "coordinacion", "escucha.sh").replace("\\", "/")
TEXTO_2B = "- AMARILLO · nivel 2b · fusión estructural sin conflictos · "
FRASE_2B = "conflicto de git que la fusión estructural (Mergiraf) resuelve; amarillo, revisad la fusión igualmente"
AB = ["persona-a", "persona-b"]


def de_050(nombre):
    """hkos/<nombre>.py de la etiqueta v0.5.0, como módulo (None sin la etiqueta: un clon superficial)."""
    r = subprocess.run(["git", "-C", KIT, "show", f"v0.5.0:hkos/{nombre}.py"], capture_output=True)
    if r.returncode != 0:
        return None
    m = types.ModuleType(f"{nombre}_050")
    m.__dict__["__file__"] = os.path.join(HKOS, f"{nombre}.py")
    exec(compile(r.stdout.decode("utf-8"), f"{nombre}_050.py", "exec"), m.__dict__)
    return m


def ev(n, ts, persona, rutas, tipo="edicion"):
    return {"v": 1, "id": f"e{n}", "ts": ts, "actor": {"persona": persona, "papel": "principal", "sesion": f"s-{persona}"},
            "tipo": tipo, "fuente": "hook", "rutas": rutas}


PERSONAS = [{"persona": x, "nombre": x[-1].upper()} for x in ("persona-a", "persona-b", "persona-c")]
EVENTOS = [ev(1, "2026-11-20T10:00:00Z", "persona-a", ["src/app.py", "src/datos.json", "web/App.jsx", "README.md"]),
           ev(2, "2026-11-20T10:01:00Z", "persona-b", ["src/app.py", "src/datos.json", "web/App.jsx", "README.md"]),
           ev(3, "2026-11-20T10:02:00Z", "persona-c", ["README.md"])]
AHORA = "2026-11-20T10:30:00Z"


def leer(ruta):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        return f.read()


def colision(cid, nivel, gravedad, rutas, cuando, personas=AB):
    return {"id": cid, "nivel": nivel, "gravedad": gravedad, "personas": personas, "rutas": rutas, "observado_en": cuando}


def con_colisiones(e, cols):
    e = json.loads(json.dumps(e))
    e["colisiones"] = cols
    return e


# ============================================================================================ 1. colisiones.calcular
class Calcular(unittest.TestCase):
    def calc(self, conflictos):
        return colisiones.calcular(EVENTOS, PERSONAS, AHORA, conflictos=conflictos)[0]

    def test_un_par_con_las_dos_y_ninguna_de_sus_rutas_en_el_nivel_1(self):
        cols = self.calc([{"personas": ["persona-b", "persona-a"], "rutas": ["web/App.jsx"],
                           "rutas_2b": ["src/datos.json", "src/app.py"], "desde": "2026-11-20T10:05:00Z",
                           "desde_2b": "2026-11-20T10:06:00Z"}])
        # README.md, sin conflicto, en el nivel 1 de los tres; lo del 2 y el 2b, en ningún nivel 1 de A y B.
        self.assertEqual(cols, [
            colision("1:persona-a+persona-b+persona-c", "1", "amarillo", ["README.md"], "2026-11-20T10:02:00Z",
                     ["persona-a", "persona-b", "persona-c"]),
            colision("2:persona-a+persona-b", "2", "rojo", ["web/App.jsx"], "2026-11-20T10:05:00Z"),
            colision("2b:persona-a+persona-b", "2b", "amarillo", ["src/app.py", "src/datos.json"],
                     "2026-11-20T10:06:00Z")])
        for c in cols:
            self.assertIsNone(ESTADO.error(con_colisiones(estado_base(), [c])), c)

    def test_solo_2b_sin_rojo_y_solo_rojo_sin_2b(self):
        solo_2b = self.calc([{"personas": AB, "rutas": [], "rutas_2b": ["src/app.py", "src/datos.json", "web/App.jsx"],
                              "desde": "2026-11-20T10:05:00Z", "desde_2b": "2026-11-20T10:05:00Z"}])
        self.assertEqual([c["id"] for c in solo_2b], ["1:persona-a+persona-b+persona-c", "2b:persona-a+persona-b"])
        solo_2 = self.calc([{"personas": AB, "rutas": ["src/app.py"], "rutas_2b": [], "desde": "2026-11-20T10:05:00Z",
                             "desde_2b": None}])
        self.assertEqual([c["id"] for c in solo_2], ["1:persona-a+persona-b", "1:persona-a+persona-b+persona-c",
                                                     "2:persona-a+persona-b"])
        self.assertEqual(solo_2[0]["rutas"], ["src/datos.json", "web/App.jsx"])

    def test_sin_rutas_2b_la_salida_de_la_050(self):
        viejo = de_050("colisiones")
        if viejo is None:
            self.skipTest("sin la etiqueta v0.5.0 (clon superficial)")
        for conflictos in (None, [], [{"personas": AB, "rutas": ["src/app.py", "web/App.jsx"],
                                       "desde": "2026-11-20T10:05:00Z"}],
                           [{"personas": ["persona-c", "persona-a"], "rutas": ["README.md"], "desde": AHORA}]):
            with self.subTest(conflictos=conflictos):
                self.assertEqual(json.dumps(self.calc(conflictos)),
                                 json.dumps(viejo.calcular(EVENTOS, PERSONAS, AHORA, conflictos=conflictos)[0]))


# ================================================ 2. relay: el interruptor y, apagado, todo byte a byte como la 0.5.0
class CalculoFalso:
    """Anota cómo lo construye el relay. Sin `fusion_estructural` en la firma, como el Calculo de la 0.5.0."""
    llamadas = []

    def __init__(self, repo, equipo, aviso=print, **extra):
        CalculoFalso.llamadas.append(extra)
        self.activo, self.conflictos = True, []


class Interruptor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.os_md = os.path.join(self.tmp, "os.md")
        original = colisiones_merge.Calculo
        colisiones_merge.Calculo = CalculoFalso
        self.addCleanup(setattr, colisiones_merge, "Calculo", original)
        CalculoFalso.llamadas = []

    def nivel2(self, texto):
        with open(self.os_md, "w", encoding="utf-8") as f:
            f.write(texto)
        return relay_mod.nivel2(self.tmp, self.os_md, PERSONAS, aviso=lambda s: None)

    def test_lectura_de_fusion_estructural(self):
        for texto, valor in (("activa: sí\n", False), ("fusion_estructural: no\n", False),
                             ("fusion_estructural: sí   # con Mergiraf\n", True), ("fusion_estructural: si\n", True),
                             ("fusion_estructural: yes\n", True), ("fusion_estructural:\n", False)):
            with self.subTest(texto=texto):
                with open(self.os_md, "w", encoding="utf-8") as f:
                    f.write(texto)
                self.assertIs(red.fusion_estructural(self.os_md), valor)
        self.assertFalse(red.fusion_estructural(None))

    def test_el_relay_pasa_el_interruptor_al_calculo_solo_encendido(self):
        self.assertIsInstance(self.nivel2("publicar_wip: sí\nfusion_estructural: sí\n"), CalculoFalso)
        self.assertIsInstance(self.nivel2("publicar_wip: sí\nfusion_estructural: no\n"), CalculoFalso)
        self.assertIsInstance(self.nivel2("publicar_wip: sí\n"), CalculoFalso)
        # Sin publicar_wip no hay nivel 2, y el interruptor no hace nada.
        self.assertIsNone(self.nivel2("publicar_wip: no\nfusion_estructural: sí\n"))
        self.assertIsNone(self.nivel2("fusion_estructural: sí\n"))
        self.assertEqual(CalculoFalso.llamadas, [{"fusion_estructural": True}, {}, {}])

    def test_calculo_inactivo_no_es_nivel_2(self):
        class Inactivo(CalculoFalso):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.activo = False
        colisiones_merge.Calculo = Inactivo
        self.assertIsNone(self.nivel2("publicar_wip: sí\nfusion_estructural: sí\n"))


class Wip:
    def __init__(self, conflictos):
        self.conflictos = conflictos


class Apagado(unittest.TestCase):
    """Criterio 1 de M11, la parte sin relay vivo: sin `rutas_2b` (el interruptor apagado), estado.json del relay, la
    vista y estado-equipo.md, byte a byte como en la 0.5.0 con los mismos datos (G5, G6 y G15 sin el 2b)."""

    def setUp(self):
        self.col050, self.pro050 = de_050("colisiones"), de_050("proyeccion")
        if self.col050 is None or self.pro050 is None:
            self.skipTest("sin la etiqueta v0.5.0 (clon superficial)")
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def casos(self):
        """(nombre, personas, eventos, ahora, contratos, conflictos sin rutas_2b) de los guiones con colisiones."""
        for g in ("G5", "G6", "G15"):
            guion = simula.carga(os.path.join(SIM, "guiones", f"{g}.json"))
            _, personas, _, eventos, ts = simula.montar(guion, SIM)
            contratos = simula.contratos_de(guion, SIM)
            for punto in guion["esperado"]:
                conf = simula.conflictos_de(guion, ts, punto["tras"])
                if conf is not None:      # G15 con el interruptor apagado: lo de 2b, en rojo y sin rutas_2b
                    conf = [{"personas": c["personas"], "rutas": sorted(c["rutas"] + c.get("rutas_2b", [])),
                             "desde": c["desde"]} for c in conf]
                yield f"{g} t={punto['tras']}", personas, eventos, ts(punto["tras"]), contratos, conf

    def relay(self, nombre, personas, eventos, ahora, contratos, conf):
        r = relay_mod.Relay(os.path.join(self.tmp, nombre + str(time.time_ns())), personas, ahora=lambda: ahora,
                            contratos=contratos, wip=Wip(conf) if conf is not None else None)
        r.recibir({"eventos": [e for e in eventos if e["ts"] <= ahora]})
        r.recalcular()
        return r

    def test_estado_json_del_relay_byte_a_byte(self):
        vistos = 0
        for caso in self.casos():
            with self.subTest(caso=caso[0]):
                nuevo = self.relay(*caso).texto
                actual = modelo.colisiones
                modelo.colisiones = self.col050
                try:
                    viejo = self.relay(*caso).texto
                finally:
                    modelo.colisiones = actual
                self.assertEqual(nuevo, viejo)
                vistos += b'"nivel":"2"' in nuevo
        self.assertGreater(vistos, 0)          # y hay nivel 2 en alguno

    def test_la_vista_y_el_md_byte_a_byte(self):
        estados = [self.relay(*caso).estado for caso in self.casos()] + [estado_base(), estado_5x20()]
        estados.append(con_colisiones(estado_base(), [colision("2:persona-a+persona-b", "2", "rojo", ["src/app.py"],
                                                               "2026-11-20T10:20:00Z")]))
        for e in estados:
            for ahora in (None, iso(fecha(e["generado_en"]) + timedelta(minutes=9))):
                v, v0 = p.vista(e, ahora), self.pro050.vista(e, ahora)
                self.assertEqual(json.dumps(v, ensure_ascii=False), json.dumps(v0, ensure_ascii=False))
                for persona in [x["persona"] for x in e["personas"]]:
                    for tz in (timezone.utc, MADRID):
                        self.assertEqual(p.markdown(v, persona, "x", tz=tz, epoch=1),
                                         self.pro050.markdown(v0, persona, "x", tz=tz, epoch=1))


# ===================================================================================== 3. estado-equipo.md y el MCP
class Proyeccion(unittest.TestCase):
    def test_la_linea_2b_decision_7(self):
        c = colision("2b:persona-a+persona-b", "2b", "amarillo", ["src/app.py"], "2026-11-20T16:41:00Z")
        self.assertEqual(p.linea_colision(c, MADRID),
                         "- AMARILLO · nivel 2b · fusión estructural sin conflictos · src/app.py · @persona-a, "
                         "@persona-b (18:41)")
        muchas = dict(c, rutas=[f"src/modulo_{i}.py" for i in range(6)])
        linea = p.linea_colision(muchas, MADRID)
        self.assertEqual(linea, TEXTO_2B + "src/modulo_0.py, src/modulo_1.py, src/modulo_2.py (+3) · @persona-a, "
                         "@persona-b (18:41)")
        self.assertLessEqual(len(linea), p.LINEA_MAX)
        # La roja del mismo par, como en la 0.5.0.
        self.assertEqual(p.linea_colision(dict(c, id="2:persona-a+persona-b", nivel="2", gravedad="rojo"), MADRID),
                         "- ROJO · nivel 2 · src/app.py · @persona-a, @persona-b (18:41)")

    def test_md_vista_y_firma_al_bajar_y_al_subir(self):
        roja = colision("2:persona-a+persona-b", "2", "rojo", ["src/app.py"], "2026-11-20T10:20:00Z")
        baja = dict(roja, id="2b:persona-a+persona-b", nivel="2b", gravedad="amarillo", observado_en="2026-11-20T10:25:00Z")
        firmas = []
        for cols in ([roja], [baja], [roja]):
            e = con_colisiones(estado_base(), cols)
            self.assertIsNone(ESTADO.error(e))
            v = p.vista(e)
            md = p.markdown(v, "persona-b", "x", tz=timezone.utc)
            firmas.append(p.firmas(v, "persona-b")["colisiones"])
            if cols == [baja]:
                self.assertEqual(v["colisiones"], [baja])
                self.assertIn("## Colisiones que te afectan\n" + TEXTO_2B + "src/app.py · @persona-a, @persona-b (10:25)\n", md)
        self.assertNotEqual(firmas[0], firmas[1])
        self.assertEqual(firmas[0], firmas[2])
        # La hora sola no cambia la firma.
        v = p.vista(con_colisiones(estado_base(), [dict(baja, observado_en="2026-11-20T10:29:00Z")]))
        self.assertEqual(p.firmas(v, "persona-b")["colisiones"], firmas[1])

    def test_en_la_vista_las_rojas_primero(self):
        roja = colision("2:persona-a+persona-b", "2", "rojo", ["web/App.jsx"], "2026-11-20T10:20:00Z")
        b = colision("2b:persona-a+persona-b", "2b", "amarillo", ["src/app.py"], "2026-11-20T10:21:00Z")
        n1 = colision("1:persona-a+persona-b", "1", "amarillo", ["README.md"], "2026-11-20T10:01:00Z")
        v = p.vista(con_colisiones(estado_base(), [n1, roja, b]))
        self.assertEqual([c["id"] for c in v["colisiones"]], [roja["id"], n1["id"], b["id"]])


class Mcp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(self.repo, ".hackathon"))
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.dir = os.path.join(self.repo, ".git", "hackathon", "os")
        os.makedirs(self.dir)
        b = colision("2b:persona-a+persona-b", "2b", "amarillo", ["src/app.py"], "2026-11-20T10:21:00Z")
        self.estado = con_colisiones(estado_base(), [b])
        with open(os.path.join(self.dir, "estado.json"), "w", encoding="utf-8") as f:
            json.dump(self.estado, f)

    def pide(self, os_md, metodo, nombre=None, args=None):
        ruta = os.path.join(self.repo, ".hackathon", "os.md")
        if os_md is None:
            if os.path.exists(ruta):
                os.remove(ruta)
        else:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(os_md)
        m = {"jsonrpc": "2.0", "id": 1, "method": metodo}
        if nombre:
            m["params"] = {"name": nombre, "arguments": args or {}}
        return mcp.responder(mcp.Fuente(self.repo, ahora=lambda: self.estado["generado_en"]), m)["result"]

    def test_la_frase_de_adr_0014_con_el_interruptor(self):
        d = {t["name"]: t["description"] for t in self.pide("activa: sí\nfusion_estructural: sí\n", "tools/list")["tools"]}
        self.assertIn(FRASE_2B, d["colisiones"])
        self.assertTrue(d["colisiones"].startswith(mcp.HERRAMIENTAS[2]["description"]))
        self.assertEqual(list(d), ["estado", "tarea", "colisiones", "reservar", "liberar"])
        con_m10 = self.pide("activa: sí\nfusion_estructural: sí\nvista_jurado: sí\n", "tools/list")["tools"]
        self.assertEqual([t["name"] for t in con_m10], ["estado", "tarea", "colisiones", "reservar", "liberar", "jurado"])
        self.assertIn(FRASE_2B, con_m10[2]["description"])

    def test_apagado_tools_list_e_instrucciones_de_la_050(self):
        viejo = de_050("mcp")
        if viejo is None:
            self.skipTest("sin la etiqueta v0.5.0 (clon superficial)")
        for os_md in (None, "activa: sí\n", "activa: sí\nfusion_estructural: no\n"):
            with self.subTest(os_md=os_md):
                self.assertEqual(self.pide(os_md, "tools/list")["tools"], viejo.HERRAMIENTAS)
                ini = self.pide(os_md, "initialize")
                self.assertEqual(ini["instructions"], viejo.INSTRUCCIONES)

    def test_colisiones_devuelve_los_mismos_objetos(self):
        for os_md in (None, "activa: sí\nfusion_estructural: sí\n"):
            r = json.loads(self.pide(os_md, "tools/call", "colisiones", {"mias": False})["content"][0]["text"])
            self.assertEqual(r["colisiones"], self.estado["colisiones"])


# ========================================================================= 4. delta.sh y escucha.sh, tal como están
class _Md(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "clon").replace("\\", "/")
        os.makedirs(os.path.join(self.repo, ".hackathon"))
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        with open(os.path.join(self.repo, ".hackathon", "os.md"), "w", encoding="utf-8") as f:
            f.write("activa: sí\npuerto_agente: 47998\n")
        self.dir = os.path.join(self.repo, ".git", "hackathon", "os")
        os.makedirs(self.dir)
        self.env = {k: x for k, x in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}

    def deja(self, cols, ahora=None, persona="persona-b"):
        """estado-equipo.md con estas colisiones, como lo escribe el demonio."""
        e = con_colisiones(estado_base(), cols)
        if ahora:
            e["generado_en"] = ahora
        with open(os.path.join(self.dir, "estado-equipo.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(p.markdown(p.vista(e, ahora), persona, "x", tz=timezone.utc, epoch=int(time.time())))
        with open(os.path.join(self.dir, "agente.vivo"), "w") as f:         # delta.sh no relanza un demonio vivo
            f.write(f"47998\n{int(time.time())}\n")


ROJA = colision("2:persona-a+persona-b", "2", "rojo", ["src/app.py"], "2026-11-20T10:20:00Z")
BAJA = dict(ROJA, id="2b:persona-a+persona-b", nivel="2b", gravedad="amarillo", observado_en="2026-11-20T10:25:00Z")


@unittest.skipUnless(BASH, "sin bash")
class Delta(_Md):
    def inicio(self, sid):
        return subprocess.run([BASH, DELTA, "inicio", sid], capture_output=True, text=True, encoding="utf-8",
                              cwd=self.repo, env=self.env).stdout

    def turno(self, sid):
        entrada = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": sid, "cwd": self.repo,
                              "prompt": "sigue"})
        return subprocess.run([BASH, DELTA], input=entrada, capture_output=True, text=True, encoding="utf-8",
                              cwd=self.repo, env=self.env).stdout

    def test_bajar_de_rojo_a_2b_da_un_delta_corto_y_volver_a_rojo_otro(self):
        self.deja([ROJA])
        self.assertIn("- ROJO · nivel 2 · src/app.py", self.inicio("s1"))
        self.deja([BAJA])
        d = self.turno("s1")
        self.assertLessEqual(len(d), 600)
        self.assertIn(TEXTO_2B + "src/app.py · @persona-a, @persona-b (10:25)", d)
        self.assertEqual([x for x in d.splitlines() if x.startswith("## ")], ["## Colisiones que te afectan"])
        self.assertEqual(self.turno("s1"), "")
        self.deja([ROJA])                                       # alguien cambia el fichero y Mergiraf ya no lo resuelve
        d = self.turno("s1")
        self.assertLessEqual(len(d), 600)
        self.assertIn("- ROJO · nivel 2 · src/app.py · @persona-a, @persona-b", d)

    def test_30_minutos_con_un_2b_estable_no_inyectan_nada(self):
        self.deja([BAJA], ahora="2026-11-20T10:30:00Z")
        self.assertIn(TEXTO_2B, self.inicio("s2"))
        salidas = []
        for minuto in range(1, 31):
            self.deja([BAJA], ahora=iso(fecha("2026-11-20T10:30:00Z") + timedelta(minutes=minuto)))
            salidas.append(self.turno("s2"))
        self.assertEqual(salidas, [""] * 30)

    def test_pasados_6000_caracteres_un_2b_no_se_inyecta_y_una_roja_si(self):
        self.deja([])
        self.inicio("s3")
        entregado = os.path.join(self.dir, "entregado", "s3.firmas")
        with open(entregado, encoding="utf-8") as f:
            texto = f.read()
        with open(entregado, "w", encoding="utf-8", newline="\n") as f:
            f.write(re.sub(r"(?m)^chars=\d+$", "chars=6001", texto))
        self.deja([BAJA])
        self.assertEqual(self.turno("s3"), "")
        self.deja([BAJA, colision("3:x:persona-a", "3", "rojo", ["motor/api.py"], "2026-11-20T10:29:00Z")
                   | {"contrato": "API del motor"}])
        d = self.turno("s3")
        self.assertIn("- ROJO · nivel 3", d)
        self.assertNotIn("nivel 2b", d)


@unittest.skipUnless(BASH and os.name != "nt", "sin bash, o en Windows (allí, escucha.sh tal cual lo prueba prueba_hooks.py)")
class Monitor(_Md):
    """escucha.sh de verdad (el monitor), como en prueba_hooks.py: abre turno solo por una línea `- ROJO` nueva."""

    def escucha(self, pasos):
        gh = os.path.join(self.tmp, "gh-falso").replace("\\", "/")
        llamadas = os.path.join(self.tmp, "gh-llamadas.txt").replace("\\", "/")
        with open(gh, "w", newline="\n") as f:
            f.write('#!/usr/bin/env bash\necho "$*" >> "' + llamadas + '"\n'
                    'case "$*" in *"api user"*) echo persona-b ;; esac\nexit 0\n')
        os.chmod(gh, 0o755)
        with open(os.path.join(self.repo, ".hackathon", "coordinacion.md"), "w", encoding="utf-8") as f:
            f.write("activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| B | @persona-b |\n")
        salida = os.path.join(self.tmp, f"escucha-{time.time_ns()}.out")
        with open(salida, "wb") as out:
            proc = subprocess.Popen([BASH, "-c", f"bash '{ESCUCHA}'; :"], cwd=self.repo, stdout=out,
                                    stderr=subprocess.DEVNULL, env=dict(self.env, HK_GH=gh, HK_ESCUCHA_PASO_S="1"))
        try:
            fin = time.time() + 30
            while time.time() < fin and not (os.path.exists(llamadas) and "issues" in leer(llamadas)):
                time.sleep(0.2)
            time.sleep(2.5)
            for paso in pasos:
                paso()
                time.sleep(2.5)
        finally:
            proc.kill()
            proc.wait()
        time.sleep(1.5)
        with open(salida, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()

    def test_bajar_a_2b_y_un_2b_estable_ninguna_linea(self):
        self.deja([ROJA])                                  # ya estaba al arrancar: va en el bloque de inicio
        salida = self.escucha([lambda: self.deja([BAJA]), lambda: self.deja([BAJA], ahora="2026-11-20T10:59:00Z")])
        self.assertEqual(salida, [])

    def test_volver_de_2b_a_rojo_una_linea(self):
        self.deja([])
        salida = self.escucha([lambda: self.deja([BAJA]), lambda: self.deja([ROJA]),
                               lambda: self.deja([ROJA], ahora="2026-11-20T10:59:00Z")])
        self.assertEqual(len(salida), 1, salida)
        self.assertIn("colisión ROJA nueva · nivel 2 · src/app.py · @persona-a, @persona-b", salida[0])

if __name__ == "__main__":
    unittest.main()
