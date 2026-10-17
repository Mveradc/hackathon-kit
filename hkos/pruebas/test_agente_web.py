"""M9a, K-94: el demonio con `web_nueva` (api.md §4, ADR-0010): la web y sus datos, la seguridad común, la suscripción
al SSE del relay, la salud de los servicios propios y `hk-os web`. Sin `web_nueva`, como en M8h.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import http.client
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
import agente as agente_mod  # noqa: E402
import cli  # noqa: E402
import relay as relay_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from red import Servidor  # noqa: E402

PERSONA = "persona-b"


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pide(puerto, metodo, ruta, cabeceras=None, cuerpo=None, host=None):
    """Una petición con el Host que se quiera (http.client pone el suyo si no se le pide lo contrario)."""
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=10)
    c.putrequest(metodo, ruta, skip_host=True, skip_accept_encoding=True)
    c.putheader("Host", host or f"127.0.0.1:{puerto}")
    for k, v in (cabeceras or {}).items():
        c.putheader(k, v)
    if cuerpo is not None:
        c.putheader("Content-Length", str(len(cuerpo)))
    c.endheaders(cuerpo)
    r = c.getresponse()
    datos = r.read()
    c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, datos


def servir(manejador):
    srv = Servidor(("127.0.0.1", 0), manejador)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
    return srv


class Base(unittest.TestCase):
    web_nueva = True

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo").replace("\\", "/")
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        os.makedirs(os.path.join(self.repo, ".hackathon"))
        with open(os.path.join(self.repo, ".hackathon", "os.md"), "w", encoding="utf-8") as f:
            f.write("# Hackathon OS\nactiva: sí\n" + ("web_nueva: sí\n" if self.web_nueva else "web_nueva: no\n"))
        self.dir = os.path.join(self.repo, ".git", "hackathon", "os")
        self.reloj = Reloj()
        self.ahora = relay_mod.ahora_iso()
        self.relay = relay_mod.Relay(os.path.join(self.tmp, "relay"), [{"persona": PERSONA, "nombre": "B"}],
                                     web_nueva=True)
        self.a = agente_mod.Agente(self.repo, PERSONA, reloj=self.reloj, ahora=lambda: self.ahora)
        self.srv = servir(agente_mod.manejador(self.a))
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.puerto = self.srv.server_address[1]

    def token(self):
        return {"X-HK-Token": self.a.web_token}

    def con_estado(self):
        self.relay.recalcular()
        self.a.estado = self.relay.estado

    def levantar_relay(self):
        self.rsrv = servir(relay_mod.manejador(self.relay))
        self.addCleanup(self.rsrv.server_close)
        self.addCleanup(self.rsrv.shutdown)
        for nombre, valor in (("relay.url", f"http://127.0.0.1:{self.rsrv.server_address[1]}"), ("token", self.relay.token)):
            with open(os.path.join(self.dir, nombre), "w", encoding="utf-8") as f:
                f.write(valor + "\n")


class SinWebNueva(Base):
    web_nueva = False

    def test_todo_como_en_m8h(self):
        self.con_estado()
        self.assertIsNone(self.a.web_token)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "web.token")))
        for metodo, ruta in (("GET", "/"), ("GET", "/v1/vista"), ("GET", "/v1/stream"), ("GET", "/assets/a.js")):
            self.assertEqual(pide(self.puerto, metodo, ruta)[0], 404, ruta)
        cuerpo = b'{"tarea":"T01"}'
        self.assertEqual(pide(self.puerto, "POST", "/v1/reclamar", {"Content-Type": "application/json"}, cuerpo)[0], 404)
        codigo, _, datos = pide(self.puerto, "GET", "/salud")
        self.assertEqual(codigo, 200)
        self.assertTrue(datos.decode().startswith("hk-os "))
        self.assertEqual(self.a.salud_servicios.ciclo(), [])          # sin servicios en el estado, nada que mirar


class Token(Base):
    def test_se_crea_y_se_reutiliza(self):
        with open(os.path.join(self.dir, "web.token"), encoding="utf-8") as f:
            self.assertEqual(f.read().strip(), self.a.web_token)
        self.assertRegex(self.a.web_token, r"^[0-9a-f]{64}$")
        otro = agente_mod.Agente(self.repo, PERSONA, reloj=self.reloj, ahora=lambda: self.ahora)
        self.assertEqual(otro.web_token, self.a.web_token)


class Seguridad(Base):
    """Criterio 6 de M9a (ADR-0010), en el proceso; evals/coordinacion/acciones_seguridad.py lo repite en vivo."""

    def sin_cors(self, cabeceras):
        self.assertFalse([k for k in cabeceras if k.startswith("access-control-")])

    def test_datos(self):
        self.assertEqual(pide(self.puerto, "GET", "/v1/vista", self.token())[0], 503)    # aún sin estado.json
        self.con_estado()
        t = self.a.web_token
        casos = [
            ({}, "/v1/vista", None, 401),                                   # sin token
            ({"X-HK-Token": "0" * 64}, "/v1/vista", None, 401),             # otro token
            ({}, f"/v1/vista?t={t}", None, 401),                            # en la query, nunca
            (self.token(), f"/v1/vista?token={t}", None, 401),              # ni con la cabecera buena al lado
            ({}, f"/v1/stream?t={t}", None, 401),
            (self.token(), "/v1/vista", f"evil.example:{self.puerto}", 403),  # DNS rebinding
            (self.token(), "/v1/vista", "127.0.0.1:1", 403),
            (dict(self.token(), Origin="http://evil.example"), "/v1/vista", None, 403),
            (dict(self.token(), Origin=f"http://localhost:{self.puerto + 1}"), "/v1/vista", None, 403),
            (self.token(), "/v1/vista", f"localhost:{self.puerto}", 200),
            (dict(self.token(), Origin=f"http://127.0.0.1:{self.puerto}"), "/v1/vista", None, 200),
        ]
        for cabeceras, ruta, host, esperado in casos:
            codigo, resp, datos = pide(self.puerto, "GET", ruta, cabeceras, host=host)
            self.assertEqual(codigo, esperado, (cabeceras, ruta, host))
            self.sin_cors(resp)
        codigo, resp, datos = pide(self.puerto, "GET", "/v1/vista", self.token())
        self.assertEqual(resp["cache-control"], "no-store")
        cuerpo = json.loads(datos)
        self.assertEqual(set(cuerpo), {"servido_en", "persona", "relay", "vista"})
        self.assertEqual((cuerpo["persona"], cuerpo["servido_en"]), (PERSONA, self.ahora))
        self.assertEqual(cuerpo["vista"]["umbrales"]["fuente_s"], 300)
        self.assertTrue(cuerpo["relay"]["conectado"])

    def test_acciones(self):
        json_ = {"Content-Type": "application/json"}
        bien = b'{"tarea":"T01"}'
        casos = [
            ({"Content-Type": "text/plain"}, bien, None, 415),                 # un formulario de otra página
            ({"Content-Type": "application/x-www-form-urlencoded"}, bien, None, 415),
            (json_, bien, None, 401),                                          # sin token
            (dict(json_, **{"X-HK-Token": "x"}), bien, None, 401),
            (dict(self.token(), **json_), bien, f"evil.example:{self.puerto}", 403),
            (dict(self.token(), **json_, Origin="http://evil.example"), bien, None, 403),
            (dict(self.token(), **json_), b"x" * 5000, None, 413),
            (dict(self.token(), **json_), b"{no", None, 400),
            (dict(self.token(), **json_), bien, None, 503),                    # las comprobaciones pasan; sin estado aún (K-95)
        ]
        for cabeceras, cuerpo, host, esperado in casos:
            codigo, resp, _ = pide(self.puerto, "POST", "/v1/reclamar", cabeceras, cuerpo, host=host)
            self.assertEqual(codigo, esperado, (cabeceras, cuerpo[:20], host))
            self.sin_cors(resp)
        t = self.a.web_token
        self.assertEqual(pide(self.puerto, "POST", f"/v1/anotar?t={t}", json_, bien)[0], 401)
        self.assertEqual(pide(self.puerto, "POST", "/v1/otra", dict(self.token(), **json_), bien)[0], 404)

    def test_options_sin_cors(self):
        for ruta in ("/v1/anotar", "/v1/vista", "/"):
            codigo, resp, _ = pide(self.puerto, "OPTIONS", ruta, {
                "Origin": "http://evil.example", "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-hk-token, content-type"})
            self.assertEqual(codigo, 405)
            self.sin_cors(resp)


class Estaticos(Base):
    def test_lista_blanca(self):
        web = os.path.join(self.tmp, "web")
        os.makedirs(os.path.join(web, "assets", "sub"))
        for ruta, texto in (("index.html", "<!doctype html><title>hk</title>"), ("assets/app-1a.js", "x"),
                            ("assets/f.woff2", "w"), ("assets/x.exe", "no"), ("assets/sub/a.js", "no"),
                            ("secreto.txt", "no")):
            with open(os.path.join(web, ruta), "w", encoding="utf-8") as f:
                f.write(texto)
        viejo, agente_mod.WEB_NUEVA = agente_mod.WEB_NUEVA, web
        self.addCleanup(setattr, agente_mod, "WEB_NUEVA", viejo)
        codigo, resp, datos = pide(self.puerto, "GET", "/")
        self.assertEqual((codigo, resp["content-type"]), (200, "text/html; charset=utf-8"))
        self.assertIn("script-src 'self'", resp["content-security-policy"])
        self.assertNotIn(self.a.web_token.encode(), datos)
        self.assertEqual(pide(self.puerto, "GET", "/assets/app-1a.js")[1]["content-type"], "text/javascript; charset=utf-8")
        self.assertEqual(pide(self.puerto, "GET", "/assets/f.woff2")[1]["content-type"], "font/woff2")
        for ruta in ("/assets/x.exe", "/assets/sub/a.js", "/assets/../secreto.txt", "/assets/%2e%2e%2fsecreto.txt",
                     "/secreto.txt", "/index.html", "/assets/"):
            self.assertEqual(pide(self.puerto, "GET", ruta)[0], 404, ruta)
        self.assertEqual(pide(self.puerto, "GET", "/", host=f"evil.example:{self.puerto}")[0], 403)
        agente_mod.WEB_NUEVA = os.path.join(self.tmp, "no-existe")
        self.assertEqual(pide(self.puerto, "GET", "/")[0], 404)


def lector_sse(r):
    def mensaje():
        campos = {}
        while True:
            l = r.readline().decode("utf-8").rstrip("\n")
            if not l:
                return campos
            k, _, v = l.partition(": ")
            campos[k] = v
    return mensaje


class Suscripcion(Base):
    def stream_del_demonio(self):
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        c.request("GET", "/v1/stream", headers=self.token())
        r = c.getresponse()
        self.addCleanup(c.close)
        self.assertEqual(r.status, 200)
        return lector_sse(r)

    def esperar(self, condicion, s=10):
        fin = time.time() + s
        while time.time() < fin:
            if condicion():
                return True
            time.sleep(0.05)
        return False

    def test_estado_y_eventos_por_el_stream_del_relay(self):
        self.levantar_relay()
        self.relay.recalcular()
        parar = threading.Event()
        self.addCleanup(parar.set)
        threading.Thread(target=self.a.suscripcion.correr, args=(parar,), daemon=True).start()
        self.assertTrue(self.esperar(lambda: self.a.en_stream and self.a.estado is not None))
        with open(os.path.join(self.dir, "estado.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), self.a.estado)
        self.assertEqual(self.a.etag, f'"{self.relay.version}"')
        self.reloj.t += 10
        self.assertFalse(self.a.recibir_estado())           # con el stream vivo, no sondea
        self.assertEqual(self.a.ultimo_estado, -1e18)
        self.a.ciclo()                                       # y el md sale de lo que trajo el stream
        self.assertTrue(os.path.exists(os.path.join(self.dir, "estado-equipo.md")))
        lee = self.stream_del_demonio()
        primero = lee()
        self.assertEqual(primero["event"], "vista")
        self.assertEqual(json.loads(primero["data"])["persona"], PERSONA)
        ts = relay_mod.ahora_iso()
        eventos = [{"v": 1, "id": f"s1-{i}", "ts": ts, "actor": {"persona": PERSONA, "papel": "principal", "sesion": "s1"},
                    "tipo": "sesion.inicio", "fuente": "hook"} for i in (1, 2, 3)]
        url, token = self.a._relay()
        self.a._post(url, token, "/v1/eventos", {"eventos": eventos})
        vistos = []
        while len(vistos) < 3:
            m = lee()
            if m.get("event") == "eventos":
                cuerpo = json.loads(m["data"])
                vistos += [e["id"] for e in cuerpo["eventos"]]
                self.assertTrue(all(set(e) == {"id", "tipo", "persona", "papel", "ts"} for e in cuerpo["eventos"]))
        self.assertEqual(vistos, ["s1-1", "s1-2", "s1-3"])

    def test_corte_y_vuelta(self):
        """Lo que hace Suscripcion con cada mensaje y al cortarse, sin hilos: mensajes_sse y las dos llamadas."""
        self.con_estado()
        estado = json.dumps(self.a.estado)
        flujo = io.BytesIO(f"id: 7\nevent: estado\ndata: {estado}\n\n: comentario\nevent: ping\ndata: \n\n"
                           'event: eventos\ndata: {"eventos":[{"id":"x"}]}\n\n'.encode())
        mensajes = list(agente_mod.mensajes_sse(flujo))
        self.assertEqual([(m[0], m[2]) for m in mensajes], [("estado", "7"), ("ping", None), ("eventos", None)])
        self.a.estado = None
        visto, _ = self.a.web_esperar(-1, 0)
        for m in mensajes:
            self.a.mensaje_relay(*m)
        self.assertEqual((self.a.etag, self.a.en_stream, self.a.relay_caido_desde), ('"7"', True, None))
        visto, nuevos = self.a.web_esperar(visto, 0)
        self.assertEqual(nuevos, [("vista", None), ("eventos", b'{"eventos":[{"id":"x"}]}')])
        self.assertTrue(self.a.md_pendiente)
        self.a.ciclo()
        self.assertFalse(self.a.md_pendiente)
        self.a.corte_relay()
        self.assertFalse(self.a.en_stream)
        self.assertEqual(self.a.relay_caido_desde, self.ahora)
        self.assertFalse(self.a.vista_web()["relay"]["conectado"])
        visto, nuevos = self.a.web_esperar(visto, 0)
        self.assertEqual(nuevos, [("vista", None)])
        self.a.corte_relay()                                 # otro intento fallido: nada nuevo
        self.assertEqual(self.a.web_esperar(visto, 0)[1], [])
        self.a.mensaje_relay("ping", "", None)               # el primer mensaje nuevo lo devuelve
        self.assertTrue(self.a.vista_web()["relay"]["conectado"])
        self.assertEqual(self.a.vista_web()["relay"]["desde"], self.ahora)


class SaludServicios(Base):
    def setUp(self):
        super().setUp()
        pedidas = self.pedidas = []

        class Salud(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                pedidas.append(self.path)
                self.send_response(200 if self.path == "/salud" else 500)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")
        self.servicio = servir(Salud)
        self.p = self.servicio.server_address[1]

    def fila(self, nombre, clave, puerto, salud=None, dueno=PERSONA, valor="confirmada"):
        return {"clave": clave, "nombre": nombre, "carpeta": f"{nombre}/", "puerto": puerto, "arranque": None,
                "salud": salud, "dueno": None, "dueno_autoridad": dueno, "confirmacion": {"valor": valor}}

    def test_solo_los_suyos_confirmados_y_al_cambiar(self):
        cerrado = puerto_libre()
        self.a.estado = {"servicios": {"lista": [
            self.fila("api", "a" * 12, self.p, "/salud"),
            self.fila("cerrado", "b" * 12, cerrado),
            self.fila("ajeno", "c" * 12, self.p, "/otro", dueno="otra"),
            self.fila("nuevo", "d" * 12, self.p, "/otro", valor="sin_confirmar"),
            self.fila("fuera", "e" * 12, self.p, "http://evil.example/"),
            self.fila("roto", "f" * 12, self.p, "/otro"),
            self.fila("sinpuerto", "1" * 12, None, "/otro"),
        ], "desajustes": [{"tipo": "formato_invalido", "clave": "f" * 12}]}}
        esquema = Esquema("eventos.schema.json")
        primeros = self.a.salud_servicios.ciclo()
        self.assertEqual([(e["datos"]["servicio"], e["datos"]["escucha"], e["datos"]["salud"]) for e in primeros],
                         [("api", True, 200), ("cerrado", False, None)])
        self.assertEqual(self.pedidas, ["/salud"])                   # nunca la Salud de otra fila
        for e in primeros:
            self.assertTrue(esquema.valido(e), e)
            self.assertEqual((e["fuente"], e["actor"]), ("demonio", {"persona": PERSONA, "papel": "demonio"}))
        self.assertTrue(primeros[0]["id"].startswith(f"demonio-{PERSONA}-servicio-{'a' * 12}-"))
        self.assertEqual(self.a.salud_servicios.ciclo(), [])          # antes de 15 s, nada
        self.reloj.t += 15
        self.assertEqual(self.a.salud_servicios.ciclo(), [])          # sin cambios, nada
        self.servicio.shutdown()
        self.servicio.server_close()
        self.reloj.t += 15
        caido = self.a.salud_servicios.ciclo()
        self.assertEqual([(e["datos"]["servicio"], e["datos"]["escucha"], e["datos"]["salud"]) for e in caido],
                         [("api", False, None)])
        with open(os.path.join(self.dir, "servicios.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"a" * 12: {"escucha": False, "salud": None},
                                            "b" * 12: {"escucha": False, "salud": None}})
        self.a.ciclo_servicios()                                      # a la cola, validado
        self.assertEqual(self.a.cola, [])
        self.reloj.t += 15
        self.a.salud_servicios.emitidos.clear()                       # como al arrancar otra vez: una vez cada uno
        self.a.ciclo_servicios()
        self.assertEqual([e["tipo"] for e in self.a.cola], ["servicio.estado", "servicio.estado"])


class HkOsWeb(Base):
    def test_abre_con_el_token_en_el_fragmento_y_no_lo_imprime(self):
        abiertas, salida = [], []
        self.assertEqual(cli.web(self.repo, abiertas.append, salida.append), 1)   # sin agente.vivo: no abre nada
        self.assertEqual(abiertas, [])
        self.a.puerto = self.puerto
        self.a.latir_vivo()
        self.assertEqual(cli.web(self.repo, abiertas.append, salida.append), 0)   # sin estado todavía (503): abre
        self.assertEqual(abiertas, [f"http://127.0.0.1:{self.puerto}/#t={self.a.web_token}"])
        self.assertFalse(any(self.a.web_token in s for s in salida))
        self.assertIn(f"http://127.0.0.1:{self.puerto}/ ", salida[-1])
        self.a.web_nueva = False                                                  # un demonio de antes de web_nueva
        self.assertEqual(cli.web(self.repo, abiertas.append, salida.append), 1)
        self.assertEqual(len(abiertas), 1)

    def test_apagada_en_os_md(self):
        with open(os.path.join(self.repo, ".hackathon", "os.md"), "w", encoding="utf-8") as f:
            f.write("activa: sí\n")
        salida = []
        self.assertEqual(cli.web(self.repo, lambda u: self.fail(u), salida.append), 1)
        self.assertIn("web_nueva: sí", salida[0])

    def test_recoger_sin_secretos(self):
        with open(os.path.join(self.dir, "nota.index"), "w") as f:
            f.write("x")
        destino = os.path.join(self.tmp, "r.zip")
        cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, cwd)
        self.assertEqual(cli.recoger(destino=destino, salida=lambda *_: None), 0)
        with zipfile.ZipFile(destino) as z:
            nombres = z.namelist()
        self.assertFalse([n for n in nombres if n.endswith(("web.token", "nota.index"))])


if __name__ == "__main__":
    unittest.main()
