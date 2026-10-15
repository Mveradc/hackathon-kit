"""K-40 y K-41 (M8d): relay del Hackathon OS (api.md §3). Criterios 2 y 4 de M8d, y lo que fija el contrato.

Uso: uv run --no-project --with "jsonschema[format-nongpl]" -m unittest discover -s hkos/pruebas -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import relay as relay_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from red import Servidor  # noqa: E402

T0 = "2026-11-20T10:00:00.000000Z"


def evento(n, sesion="s1", persona="persona-b", ts=T0, tipo="edicion", **extra):
    e = {"v": 1, "id": f"{sesion}-{n}", "ts": ts, "actor": {"persona": persona, "papel": "principal", "sesion": sesion},
         "tipo": tipo, "fuente": "hook"}
    if tipo == "edicion":
        e["rutas"] = [f"f{n}.txt"]
    e.update(extra)
    return e


class Reloj:
    def __init__(self, ts):
        self.ts = ts

    def __call__(self):
        return self.ts


class Base(unittest.TestCase):
    PERSONAS = [{"persona": "persona-a", "nombre": "A"}, {"persona": "persona-b", "nombre": "B"}]

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.reloj = Reloj("2026-11-20T10:00:30.000000Z")

    def nuevo(self):
        return relay_mod.Relay(self.dir, self.PERSONAS, ahora=self.reloj)


class Modelo(Base):
    def test_idempotente_y_persistente(self):
        r = self.nuevo()
        self.assertEqual(r.recibir({"eventos": [evento(1), evento(2)]}), {"aceptados": 2, "repetidos": 0})
        self.assertEqual(r.recibir({"eventos": [evento(2), evento(3), evento(3)]}), {"aceptados": 1, "repetidos": 2})
        token = r.token
        # Reinicio: relee el registro, reconoce los repetidos y conserva el token (criterio 2).
        r2 = self.nuevo()
        self.assertEqual(r2.token, token)
        self.assertEqual(len(r2.eventos), 3)
        self.assertEqual(r2.recibir({"eventos": [evento(1), evento(2), evento(3), evento(4)]}), {"aceptados": 1, "repetidos": 3})
        with open(os.path.join(self.dir, "eventos.jsonl"), encoding="utf-8") as f:
            self.assertEqual([json.loads(l)["id"] for l in f], ["s1-1", "s1-2", "s1-3", "s1-4"])

    def test_registro_con_linea_rota(self):
        r = self.nuevo()
        r.recibir({"eventos": [evento(1)]})
        with open(os.path.join(self.dir, "eventos.jsonl"), "ab") as f:
            f.write(b'{"v":1,"id":"s1-2", roto\n')
        r2 = self.nuevo()
        self.assertEqual([e["id"] for e in r2.eventos], ["s1-1"])

    def test_lote_invalido_entero_o_nada(self):
        r = self.nuevo()
        malo = evento(2)
        malo["contenido"] = "codigo"
        with self.assertRaises(relay_mod.Invalido) as cm:
            r.recibir({"eventos": [evento(1), malo, evento(3)]})
        self.assertEqual(cm.exception.indice, 1)
        self.assertEqual(cm.exception.campo, "/contenido")
        self.assertEqual(r.eventos, [])
        self.assertFalse(os.path.exists(os.path.join(self.dir, "eventos.jsonl")))
        for cuerpo in ([evento(1)], {"eventos": "x"}, {"eventos": [evento(i) for i in range(201)]}):
            with self.assertRaises(relay_mod.Invalido):
                r.recibir(cuerpo)

    def test_presencia_y_ttl(self):
        r = self.nuevo()
        r.recibir({"eventos": [evento(1, tipo="sesion.inicio")]})
        r.recalcular()
        actor = r.estado["personas"][1]["actores"][0]
        self.assertTrue(actor["activo"])
        self.reloj.ts = "2026-11-20T10:01:31.000000Z"        # 91 s sin señales (R-18)
        r.recalcular()
        self.assertFalse(r.estado["personas"][1]["actores"][0]["activo"])

    def test_sesion_fin_la_retira(self):
        r = self.nuevo()
        r.recibir({"eventos": [evento(1, tipo="sesion.inicio"), evento(2, tipo="sesion.fin", ts="2026-11-20T10:00:10.000000Z")]})
        r.recalcular()
        self.assertFalse(r.estado["personas"][1]["actores"][0]["activo"])

    def test_latido_usa_la_ultima_senal_y_sustituye_al_anterior(self):
        r = self.nuevo()
        r.latido({"persona": "persona-a", "actores": [
            {"papel": "worker", "sesion": "s9", "agente": "w1", "worktree": ".claude/worktrees/agent-w1", "tarea": "T05",
             "ultima_senal": "2026-11-20T10:00:20.000000Z"}], "lineas_corruptas": 2})
        r.recalcular()
        a = r.estado["personas"][0]["actores"][0]
        self.assertEqual((a["papel"], a["agente"], a["ultimo_latido"], a["activo"]),
                         ("worker", "w1", "2026-11-20T10:00:20.000000Z", True))
        self.assertEqual(a["tarea"]["valor"], "T05")
        d = [x for x in r.estado["discrepancias"] if x["tipo"] == "linea_corrupta"]
        self.assertEqual((d[0]["persona"], d[0]["veces"]), ("persona-a", 2))
        # El latido no alarga la presencia: a los 91 s de su última señal, inactivo aunque el latido sea reciente.
        self.reloj.ts = "2026-11-20T10:01:51.000000Z"
        r.recalcular()
        self.assertFalse(r.estado["personas"][0]["actores"][0]["activo"])
        # Un latido sin actores sustituye al anterior.
        r.latido({"persona": "persona-a", "actores": []})
        r.recalcular()
        self.assertEqual(r.estado["personas"][0]["actores"], [])

    def test_latido_invalido(self):
        r = self.nuevo()
        for cuerpo in ({"actores": []}, {"persona": "persona-a", "actores": [{"papel": "jefe", "ultima_senal": T0}]},
                       {"persona": "persona-a", "actores": [{"papel": "principal"}]},
                       {"persona": "persona-a", "actores": [], "lineas_corruptas": -1}):
            with self.subTest(cuerpo):
                with self.assertRaises(relay_mod.Invalido):
                    r.latido(cuerpo)

    def test_version_solo_cambia_con_el_contenido(self):
        r = self.nuevo()
        v = r.version
        self.reloj.ts = "2026-11-20T10:00:31.000000Z"
        r.recalcular()
        self.assertEqual(r.version, v)
        r.recibir({"eventos": [evento(1)]})
        r.recalcular()
        self.assertEqual(r.version, v + 1)

    def test_reloj_adelantado_no_oculta_eventos(self):
        r = self.nuevo()
        r.recibir({"eventos": [evento(1, tipo="sesion.inicio", ts="2026-11-20T10:05:00.000000Z")]})
        r.recalcular()
        self.assertTrue(r.estado["personas"][1]["actores"][0]["activo"])

    def test_estado_valida(self):
        r = self.nuevo()
        r.recibir({"eventos": [evento(1, tipo="sesion.inicio"), evento(2)]})
        r.latido({"persona": "persona-b", "actores": [{"papel": "principal", "sesion": "s1", "ultima_senal": T0}],
                  "lineas_corruptas": 1})
        r.recalcular()
        self.assertIsNone(Esquema("estado.schema.json").error(r.estado))

    def test_ip_permitida(self):
        for ip, ok in (("127.0.0.1", True), ("192.168.1.20", True), ("10.0.0.5", True), ("172.20.1.1", True),
                       ("100.101.2.3", True), ("0.0.0.0", False), ("8.8.8.8", False), ("172.32.0.1", False), ("x", False)):
            with self.subTest(ip):
                self.assertEqual(relay_mod.ip_permitida(ip), ok)


class Http(Base):
    def setUp(self):
        super().setUp()
        self.reloj = relay_mod.ahora_iso
        self.relay = relay_mod.Relay(self.dir, self.PERSONAS)
        self.srv = Servidor(("127.0.0.1", 0), relay_mod.manejador(self.relay))
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def pide(self, ruta, cuerpo=None, token=True, cabeceras=None, crudo=None):
        h = dict(cabeceras or {})
        if token:
            h["Authorization"] = f"Bearer {self.relay.token if token is True else token}"
        datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
        req = urllib.request.Request(self.url + ruta, data=datos, headers=h, method="POST" if datos is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as ex:
            return ex.code, ex.read(), ex.headers

    def test_401_sin_token_o_con_otro(self):
        for token in (False, "otro"):
            for ruta, cuerpo in (("/v1/estado", None), ("/v1/eventos", {"eventos": []}), ("/v1/stream", None)):
                with self.subTest(token=token, ruta=ruta):
                    self.assertEqual(self.pide(ruta, cuerpo, token=token)[0], 401)

    def test_400_y_sigue_vivo(self):
        malo = evento(1)
        malo["tipo"] = "otro"
        codigo, cuerpo, _ = self.pide("/v1/eventos", {"eventos": [malo]})
        self.assertEqual(codigo, 400)
        self.assertEqual(json.loads(cuerpo)["indice"], 0)
        self.assertEqual(self.pide("/v1/eventos", crudo=b"{no es json")[0], 400)
        codigo, cuerpo, _ = self.pide("/v1/eventos", {"eventos": [evento(1)]})
        self.assertEqual((codigo, json.loads(cuerpo)), (200, {"aceptados": 1, "repetidos": 0}))
        self.assertEqual(self.pide("/v1/latido", {"persona": "persona-b", "actores": []})[0], 204)

    def test_etag_304(self):
        codigo, cuerpo, h = self.pide("/v1/estado")
        self.assertEqual(codigo, 200)
        self.assertEqual(json.loads(cuerpo)["v"], 1)
        self.assertEqual(self.pide("/v1/estado", cabeceras={"If-None-Match": h["ETag"]})[0], 304)

    def test_sse_manda_el_actual_y_los_cambios(self):
        req = urllib.request.Request(self.url + "/v1/stream", headers={"Authorization": f"Bearer {self.relay.token}"})
        r = urllib.request.urlopen(req, timeout=5)
        self.addCleanup(r.close)

        def mensaje():
            campos = {}
            while True:
                l = r.readline().decode("utf-8").rstrip("\n")
                if not l:
                    return campos
                k, _, v = l.partition(": ")
                campos[k] = v
        m = mensaje()
        self.assertEqual((m["event"], m["id"]), ("estado", str(self.relay.version)))
        # M8f: tras cada `estado`, la `vista` de la misma versión, con la hora del relay al servirla.
        m = mensaje()
        self.assertEqual((m["event"], m["id"]), ("vista", str(self.relay.version)))
        self.assertEqual(set(json.loads(m["data"])), {"servido_en", "vista"})
        self.pide("/v1/eventos", {"eventos": [evento(1, tipo="sesion.inicio", ts=relay_mod.ahora_iso())]})
        self.relay.recalcular()
        m = mensaje()
        self.assertEqual(m["event"], "estado")
        self.assertEqual(json.loads(m["data"])["personas"][1]["actores"][0]["sesion"], "s1")
        m = mensaje()
        self.assertEqual(m["event"], "vista")
        self.assertEqual(json.loads(m["data"])["vista"]["personas"][1]["activos"], 1)

    def test_web_sin_token_y_datos_con_token(self):
        """M8f: `GET /` es el HTML estático, sin datos y sin token (api.md §3); /v1/vista exige el token y usa ETag."""
        codigo, cuerpo, h = self.pide("/", token=False)
        self.assertEqual(codigo, 200)
        self.assertTrue(h["Content-Type"].startswith("text/html"))
        self.assertIn(b"/v1/stream", cuerpo)
        self.assertNotIn(self.relay.token.encode(), cuerpo)
        self.assertEqual(self.pide("/v1/vista", token=False)[0], 401)
        codigo, cuerpo, h = self.pide("/v1/vista")
        self.assertEqual(codigo, 200)
        self.assertEqual(json.loads(cuerpo)["vista"]["v"], 1)
        self.assertEqual(self.pide("/v1/vista", cabeceras={"If-None-Match": h["ETag"]})[0], 304)
        self.assertEqual(h["ETag"], self.pide("/v1/estado")[2]["ETag"])


class Novedades(unittest.TestCase):
    """M8f: decisiones y criterios de origin/main del clon del relay; el fetch que falla no hace ruido."""
    DECISIONES = ("# Decisiones\n\n- 2026-11-20 11:05 +0100 · [#12](https://github.com/x/y/issues/12) · @persona-a ↔ "
                  "@persona-b · nivel: 2 · La ficha devuelve `moneda` en ISO 4217\n")
    CRITERIOS = ("# Criterios del jurado\n\n<!-- Formato de cada nota:\n## <AAAA-MM-DD HH:MM> · <quién lo dijo> -->\n\n"
                 "## 2026-11-20 10:30 · Lucía (jurado)\n- Dónde: apertura\n- Qué dijo: «El pitch son cinco minutos»\n"
                 "- Fuerza: dato\n- Anotado por: Persona B\n")

    def test_parseo(self):
        from datetime import timezone as tz
        n = relay_mod.novedades_de(self.DECISIONES, self.CRITERIOS, tz.utc)
        self.assertEqual(n, [
            {"tipo": "decision", "resumen": "#12: La ficha devuelve `moneda` en ISO 4217", "autor": "@persona-a ↔ @persona-b",
             "observado_en": "2026-11-20T10:05:00Z"},
            {"tipo": "criterio", "resumen": "Lucía (jurado): «El pitch son cinco minutos»", "autor": "Persona B",
             "observado_en": "2026-11-20T10:30:00Z"}])

    def git(self, cmd, *args):
        return subprocess.run(["git", *args], cwd=cmd, capture_output=True, text=True, check=True).stdout

    def repos(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        remoto, uno, otro = (os.path.join(d, n) for n in ("remoto.git", "relay", "persona"))
        self.git(d, "init", "-q", "--bare", "-b", "main", remoto)
        for r in (uno, otro):
            self.git(d, "clone", "-q", remoto, r)
            self.git(r, "config", "user.email", "x@y")
            self.git(r, "config", "user.name", "x")
        os.makedirs(os.path.join(otro, ".hackathon"))
        with open(os.path.join(otro, ".hackathon", "decisiones.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(self.DECISIONES)
        self.git(otro, "add", ".")
        self.git(otro, "commit", "-qm", "Acuerdo #12")
        self.git(otro, "push", "-q", "origin", "HEAD:main")
        return remoto, uno, otro

    def test_fetch_y_lectura_de_origin(self):
        remoto, repo, _ = self.repos()
        reloj = Reloj(1000.0)
        n = relay_mod.Novedades(repo, 300, reloj=reloj)
        self.assertTrue(n.sondear())
        self.assertEqual([x["tipo"] for x in n.lista], ["decision"])
        self.assertIsNone(n.fuente())
        self.assertFalse(n.sondear())                 # sin cambios: nada nuevo

    def test_fetch_que_falla_es_silencioso_hasta_el_umbral(self):
        remoto, repo, otro = self.repos()
        reloj = Reloj(1000.0)
        n = relay_mod.Novedades(repo, 300, reloj=reloj)
        n.sondear()
        lista = list(n.lista)
        # Un commit nuevo en el remoto y la ref de origin bloqueada (un `git pull` de la persona a la vez): el fetch
        # no puede actualizarla y falla.
        with open(os.path.join(otro, ".hackathon", "decisiones.md"), "a", encoding="utf-8", newline="\n") as f:
            f.write(self.DECISIONES.splitlines()[-1].replace("#12", "#13") + "\n")
        self.git(otro, "commit", "-qam", "Acuerdo #13")
        self.git(otro, "push", "-q", "origin", "HEAD:main")
        bloqueo = os.path.join(repo, ".git", "refs", "remotes", "origin", "main.lock")
        os.makedirs(os.path.dirname(bloqueo), exist_ok=True)
        open(bloqueo, "w").close()
        self.addCleanup(lambda: os.path.exists(bloqueo) and os.remove(bloqueo))
        reloj.ts = 1200.0
        self.assertTrue(n.sondear())                  # cambia el estado del fetch (para recalcular), no la lista
        self.assertTrue(n.fallando)
        self.assertEqual(n.lista, lista)              # se queda con lo último
        self.assertIsNone(n.fuente())                 # 200 s < 300: en silencio
        # Después, sin red (el remoto no está): sigue fallando y, pasado el umbral, se ve en fuentes.git.
        os.remove(bloqueo)
        self.git(repo, "remote", "set-url", "origin", os.path.join(remoto, "no-existe"))
        reloj.ts = 1301.0
        n.sondear()
        self.assertEqual(n.fuente(), {"valor": "sin fetch", "fuente": "git", "observado_en": relay_mod.iso_us(1000.0)})
        self.git(repo, "remote", "set-url", "origin", remoto)
        reloj.ts = 1360.0
        n.sondear()                                   # se reintenta en la vuelta siguiente y se recupera
        self.assertIsNone(n.fuente())
        self.assertEqual(len(n.lista), 2)

    def test_estado_lleva_novedades_y_fuente_git(self):
        remoto, repo, _ = self.repos()
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        n = relay_mod.Novedades(repo, 300, reloj=Reloj(1000.0))
        n.sondear()
        r = relay_mod.Relay(d, Base.PERSONAS, ahora=Reloj("2026-11-20T12:00:00.000000Z"), novedades=n)
        r.recalcular()
        self.assertEqual(r.estado["novedades"][0]["resumen"][:4], "#12:")
        self.assertIsNone(Esquema("estado.schema.json").error(r.estado))
        self.assertEqual(r.vista["novedades"][0]["tipo"], "decision")


if __name__ == "__main__":
    unittest.main()
