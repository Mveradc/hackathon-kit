"""K-42 (M8d): demonio local del Hackathon OS (api.md §4), contra un relay de verdad en el mismo proceso.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HKOS, os.path.dirname(os.path.abspath(__file__))]
import agente as agente_mod  # noqa: E402
import permisos  # noqa: E402
import relay as relay_mod  # noqa: E402
from red import Servidor  # noqa: E402


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def crudo(n_seg, tipo, sesion="s1", persona="persona-b", cwd=None, **extra):
    e = {"v": 1, "ts": f"2026-11-20T10:00:{n_seg:02d}.000000Z", "persona": persona, "tipo": tipo, "session_id": sesion}
    if cwd:
        e["cwd"] = cwd
    e.update(extra)
    return json.dumps(e) + "\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo").replace("\\", "/")
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.eventos = os.path.join(self.repo, ".git", "hackathon", "os", "eventos")
        os.makedirs(self.eventos)
        self.ahora = "2026-11-20T10:01:00.000000Z"
        self.reloj = Reloj()
        # Relay de verdad en un puerto libre.
        self.rdir = os.path.join(self.tmp, "relay")
        self.relay = relay_mod.Relay(self.rdir, [{"persona": "persona-b", "nombre": "B"}], ahora=lambda: self.ahora)
        self.srv = None

    def levantar_relay(self):
        self.srv = Servidor(("127.0.0.1", 0), relay_mod.manejador(self.relay))
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        os_dir = os.path.join(self.repo, ".git", "hackathon", "os")
        with open(os.path.join(os_dir, "relay.url"), "w") as f:
            f.write(f"http://127.0.0.1:{self.srv.server_address[1]}\n")
        with open(os.path.join(os_dir, "token"), "w") as f:
            f.write(self.relay.token + "\n")

    def tirar_relay(self):
        self.srv.shutdown()
        self.srv.server_close()

    def escribe(self, texto, fichero="s1.jsonl"):
        with open(os.path.join(self.eventos, fichero), "a", encoding="utf-8", newline="") as f:
            f.write(texto)

    def agente(self, apagado_min=30):
        return agente_mod.Agente(self.repo, "persona-b", apagado_min, reloj=self.reloj, ahora=lambda: self.ahora)

    def ids_relay(self):
        return [e["id"] for e in self.relay.eventos]


class Lectura(Base):
    def test_linea_sin_salto_espera(self):
        a = self.agente()
        self.escribe(crudo(1, "SessionStart", cwd=self.repo, source="startup"))
        self.escribe(crudo(2, "PostToolUse", cwd=self.repo, tool_name="Edit", ruta=self.repo + "/a.txt").rstrip("\n"))
        a.leer()
        self.assertEqual([e["tipo"] for e in a.cola], ["sesion.inicio"])
        self.escribe("\n")
        a.leer()
        self.assertEqual([e["id"] for e in a.cola], ["s1-1", "s1-2"])
        self.assertEqual(a.cola[1]["rutas"], ["a.txt"])

    def test_lineas_rotas_y_persona_vacia(self):
        a = self.agente()
        self.escribe(crudo(1, "SessionStart", persona="", cwd=self.repo) + "{roto\n" + '"no es objeto"\n'
                     + crudo(2, "SessionEnd", cwd=self.repo))
        a.leer()
        self.assertEqual([e["id"] for e in a.cola], ["s1-1", "s1-4"])
        self.assertEqual(a.cola[0]["actor"]["persona"], "persona-b")
        self.assertEqual(a.corruptas, 2)
        self.assertIn("lineas_corruptas: 2", a.salud())

    def test_orden_entre_ficheros(self):
        a = self.agente()
        self.escribe(crudo(5, "SessionStart", sesion="s2", cwd=self.repo), "s2.jsonl")
        self.escribe(crudo(3, "SessionStart", sesion="s1", cwd=self.repo), "s1.jsonl")
        a.leer()
        self.assertEqual([e["id"] for e in a.cola], ["s1-1", "s2-1"])

    def test_latido_y_apagado(self):
        a = self.agente(apagado_min=1)
        self.ahora = "2026-11-20T10:00:30.000000Z"
        self.escribe(crudo(1, "SessionStart", cwd=self.repo))
        a.leer()
        lat = a.latido()
        self.assertEqual([(x["sesion"], x["papel"], x["ultima_senal"]) for x in lat["actores"]],
                         [("s1", "principal", "2026-11-20T10:00:01.000000Z")])
        self.reloj.t += 61
        self.assertFalse(a.debe_apagarse())           # la sesión sigue activa (señal hace 29 s)
        self.ahora = "2026-11-20T10:01:32.000000Z"     # 91 s sin señales
        self.assertEqual(a.latido()["actores"], [])
        self.assertTrue(a.debe_apagarse())
        self.ahora = "2026-11-20T10:00:30.000000Z"
        self.escribe(crudo(9, "SessionEnd", cwd=self.repo))
        a.leer()                                       # un evento nuevo reinicia la cuenta
        self.assertFalse(a.debe_apagarse())
        self.reloj.t += 61
        self.assertTrue(a.debe_apagarse())             # y el SessionEnd la cierra

    def test_puerto_es_el_bloqueo(self):
        uno = Servidor(("127.0.0.1", 0), agente_mod.manejador(self.agente()))
        self.addCleanup(uno.server_close)
        with self.assertRaises(OSError):
            Servidor(("127.0.0.1", uno.server_address[1]), agente_mod.manejador(self.agente()))


class Envio(Base):
    def test_envia_confirma_y_no_reenvia_tras_reiniciar(self):
        self.levantar_relay()
        a = self.agente()
        self.escribe(crudo(1, "SessionStart", cwd=self.repo) + crudo(2, "PreToolUse", cwd=self.repo, tool_name="Edit"))
        a.ciclo()
        self.assertEqual(self.ids_relay(), ["s1-1"])
        self.assertEqual(a.posiciones["s1.jsonl"]["linea"], 2)
        self.assertEqual(len(self.relay.latidos["persona-b"]), 1)
        b = self.agente()
        b.ciclo()
        self.assertEqual(b.cola, [])
        self.assertEqual(self.ids_relay(), ["s1-1"])

    def test_sin_posiciones_reenvia_y_el_relay_descarta(self):
        self.levantar_relay()
        self.escribe(crudo(1, "SessionStart", cwd=self.repo))
        self.agente().ciclo()
        os.remove(os.path.join(self.repo, ".git", "hackathon", "os", "posiciones.json"))
        b = self.agente()
        b.leer()
        url, token = b._relay()
        self.assertEqual(b._post(url, token, "/v1/eventos", {"eventos": b.cola}), {"aceptados": 0, "repetidos": 1})

    def test_relay_caido_no_pierde_nada_y_llega_en_orden(self):
        self.levantar_relay()
        a = self.agente()
        self.escribe(crudo(1, "SessionStart", cwd=self.repo))
        a.ciclo()
        self.tirar_relay()
        for i in range(2, 8):
            self.escribe(crudo(i, "PostToolUse", cwd=self.repo, tool_name="Write", ruta=f"{self.repo}/f{i}.txt"))
        a.ciclo()
        self.assertTrue(a.relay_estado.startswith("caído desde"))
        self.assertEqual(len(a.cola), 6)
        self.assertEqual(a.posiciones["s1.jsonl"]["linea"], 1)
        # Reinicio del demonio con el relay caído: lo pendiente sale del disco, no de la memoria.
        b = self.agente()
        self.relay2 = relay_mod.Relay(self.rdir, self.relay.personas, ahora=lambda: self.ahora)
        self.relay = self.relay2
        self.levantar_relay()
        b.ciclo()
        self.assertEqual(self.ids_relay(), [f"s1-{i}" for i in range(1, 8)])
        self.assertEqual(b.posiciones["s1.jsonl"]["linea"], 7)

    def test_tarea_del_worker_tras_reiniciar(self):
        """El normalizador recupera la tarea del worker (de su SubagentStart) releyendo hasta la posición."""
        self.levantar_relay()
        transcript = os.path.join(self.tmp, "proy", "s1.jsonl").replace("\\", "/")
        os.makedirs(os.path.join(self.tmp, "proy", "s1", "subagents"))
        with open(os.path.join(self.tmp, "proy", "s1", "subagents", "agent-w1.jsonl"), "w") as f:
            f.write(json.dumps({"message": {"content": "ID: T05\nBase: abc1234\nHaz esto"}}) + "\n")
        self.escribe(crudo(1, "SubagentStart", cwd=self.repo, agent_id="w1", agent_type="hackathon-kit:worker",
                           transcript_path=transcript))
        self.agente().ciclo()
        self.escribe(crudo(2, "PostToolUse", cwd=self.repo, agent_id="w1", agent_type="hackathon-kit:worker",
                           tool_name="Edit", ruta=self.repo + "/x.py"))
        b = self.agente()
        b.ciclo()
        ed = [e for e in self.relay.eventos if e["tipo"] == "edicion"][0]
        self.assertEqual((ed["tarea"], ed["actor"]["papel"], ed["actor"]["agente"]), ("T05", "worker", "w1"))
        self.assertEqual(b.latido()["actores"][0]["tarea"], "T05")


class Proyeccion(Base):
    """M8f: el demonio recibe estado.json (ETag) y escribe estado-equipo.md; agente.vivo lleva la hora."""

    def md(self):
        with open(os.path.join(self.repo, ".git", "hackathon", "os", "estado-equipo.md"), encoding="utf-8") as f:
            return f.read()

    def test_estado_md_y_etag(self):
        self.levantar_relay()
        a = self.agente()
        self.escribe(crudo(1, "SessionStart", cwd=self.repo))
        a.ciclo()                                      # envía; el relay aún no ha recalculado con el evento
        self.relay.recalcular()
        self.reloj.t += 3
        a.ciclo()
        self.assertEqual(a.estado["personas"][0]["actores"][0]["sesion"], "s1")
        md = self.md()
        self.assertTrue(md.startswith("<!-- hk-os v1 persona=persona-b "))
        self.assertIn(" relay=ok ", md)
        self.assertIn("## Tu trabajo\n", md)
        with open(os.path.join(self.repo, ".git", "hackathon", "os", "estado.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), a.estado)
        # Sin cambios en el relay: 304 y el md no se reescribe hasta MD_S.
        os.remove(os.path.join(self.repo, ".git", "hackathon", "os", "estado-equipo.md"))
        self.reloj.t += 3
        a.ciclo()
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".git", "hackathon", "os", "estado-equipo.md")))
        self.reloj.t += agente_mod.MD_S
        a.ciclo()
        self.assertIn("persona=persona-b", self.md())

    def test_relay_caido_lo_dice_el_md(self):
        self.levantar_relay()
        a = self.agente()
        a.ciclo()
        self.assertIn(" relay=ok ", self.md())
        self.tirar_relay()
        self.reloj.t += 3
        a.ciclo()
        md = self.md()
        self.assertIn(" relay=viejo ", md)
        self.assertIn("> Relay sin respuesta desde ", md)

    def test_agente_vivo_lleva_la_hora(self):
        a = self.agente()
        a.puerto = 4711
        a.ciclo()
        with open(a.vivo, encoding="utf-8") as f:
            self.assertEqual(f.read(), "4711\n1000\n")
        self.reloj.t += agente_mod.LATIDO_S
        a.ciclo()
        with open(a.vivo, encoding="utf-8") as f:
            self.assertEqual(f.read(), f"4711\n{int(self.reloj.t)}\n")

    def test_el_apagado_borra_agente_vivo(self):
        """Ajuste del usuario (M8f): al apagarse por apagado_min, el demonio borra agente.vivo."""
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        vivo = os.path.join(self.repo, ".git", "hackathon", "os", "agente.vivo")
        hecho = []
        hilo = threading.Thread(target=lambda: hecho.append(agente_mod.main(
            ["--repo", self.repo, "--persona", "persona-b", "--puerto", str(puerto), "--apagado-min", "0.02"])))
        hilo.start()
        hilo.join(30)
        self.assertEqual(hecho, [0])
        self.assertFalse(os.path.exists(vivo))
        with open(os.path.join(self.repo, ".git", "hackathon", "os", "agente.log"), encoding="utf-8") as f:
            log = f.read()
        self.assertIn("arranca en 127.0.0.1", log)
        self.assertIn("se apaga", log)


class ReemplazoFalso:
    """os.replace que da PermissionError (el WinError 5 de Windows con el destino abierto por un lector: sesion.sh,
    delta.sh o el MCP) las `veces` primeras que el destino se llama `nombre`; con veces=None, siempre."""

    def __init__(self, nombre, veces=None):
        self.nombre, self.veces, self.fallos, self.real = nombre, veces, 0, os.replace

    def __call__(self, origen, destino, *a, **kw):
        if os.path.basename(destino) == self.nombre and (self.veces is None or self.fallos < self.veces):
            self.fallos += 1
            raise PermissionError(13, "Acceso denegado (simulado)", destino)
        return self.real(origen, destino, *a, **kw)


class Windows(Base):
    """Issue #77, parte B (#27 · os.replace en Windows): Agente._escribe y `hk-os unir` (estado_inicial) reintentan como
    permisos.reemplaza, y en recibir_estado el ETag y el estado en memoria solo cambian con estado.json ya escrito."""

    def os_dir(self, *nombre):
        return os.path.join(self.repo, ".git", "hackathon", "os", *nombre)

    def test_escribe_reintenta_con_el_destino_abierto_un_momento(self):
        a = self.agente()
        falso = ReemplazoFalso("estado-equipo.md", veces=3)
        with mock.patch.object(permisos, "WINDOWS", True), mock.patch.object(os, "replace", falso):
            a._escribe("estado-equipo.md", "nuevo\n")
        self.assertEqual(falso.fallos, 3)
        with open(self.os_dir("estado-equipo.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "nuevo\n")
        self.assertFalse([n for n in os.listdir(self.os_dir()) if n.endswith(".tmp")])

    def test_escribe_se_rinde_sin_dejar_temporal(self):
        a = self.agente()
        a._escribe("reservas.tsv", "viejo\n")
        with mock.patch.object(permisos, "WINDOWS", True), mock.patch.object(permisos, "REEMPLAZO_S", 0.2), \
                mock.patch.object(os, "replace", ReemplazoFalso("reservas.tsv")):
            with self.assertRaises(PermissionError):
                a._escribe("reservas.tsv", "nuevo\n")
        with open(self.os_dir("reservas.tsv"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "viejo\n")
        self.assertFalse([n for n in os.listdir(self.os_dir()) if n.endswith(".tmp")])

    def test_un_fallo_al_escribir_estado_json_no_deja_el_disco_atrasado_tras_un_304(self):
        """Por el código del issue: antes, self.etag y self.estado cambiaban antes de escribir estado.json; si ese
        os.replace fallaba, la siguiente petición recibía un 304 y el disco se quedaba en la versión anterior."""
        self.levantar_relay()
        a = self.agente()
        a.ciclo()
        with open(self.os_dir("estado.json"), encoding="utf-8") as f:
            primero = json.load(f)
        etag, estado = a.etag, a.estado
        self.escribe(crudo(1, "SessionStart", cwd=self.repo))
        a.ciclo()                                      # envía el evento
        self.relay.recalcular()
        self.reloj.t += agente_mod.ESTADO_S
        with mock.patch.object(os, "replace", ReemplazoFalso("estado.json")):
            with self.assertRaises(PermissionError):
                a.recibir_estado()
        self.assertEqual((a.etag, a.estado), (etag, estado))       # la memoria, como el disco
        with open(self.os_dir("estado.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), primero)
        self.reloj.t += agente_mod.ESTADO_S
        self.assertTrue(a.recibir_estado())                         # 200, no 304: se vuelve a escribir
        with open(self.os_dir("estado.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), a.estado)
        self.assertNotEqual(a.estado, primero)
        self.assertEqual(a.estado["personas"][0]["actores"][0]["sesion"], "s1")

    def test_estado_inicial_de_unir_reintenta(self):
        import cli  # noqa: PLC0415
        from test_proyeccion import estado_base  # noqa: PLC0415
        falso = ReemplazoFalso("estado.json", veces=2)
        with mock.patch.object(permisos, "WINDOWS", True), mock.patch.object(os, "replace", falso):
            cli.estado_inicial(os.path.join(self.repo, ".git"), self.repo, estado_base(), "persona-b")
        self.assertEqual(falso.fallos, 2)
        with open(self.os_dir("estado.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), estado_base())
        self.assertEqual(sorted(n for n in os.listdir(self.os_dir()) if n != "eventos"),
                         ["estado-equipo.md", "estado.json", "reservas.tsv"])


if __name__ == "__main__":
    unittest.main()
