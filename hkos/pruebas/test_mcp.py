"""K-63 (M8f): servidor MCP del Hackathon OS (api.md §5) por stdio de verdad, sin modelo.

Uso: uv run --no-project -m unittest discover -s hkos/pruebas -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import timezone

HKOS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HKOS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proyeccion  # noqa: E402
from test_proyeccion import estado_base  # noqa: E402


def conversa(repo, mensajes):
    """Lanza hkos/mcp.py, le manda los mensajes y devuelve las respuestas por id."""
    entrada = "".join(json.dumps(m) + "\n" for m in mensajes)
    r = subprocess.run([sys.executable, os.path.join(HKOS, "mcp.py"), "--repo", repo], input=entrada.encode("utf-8"),
                       capture_output=True, timeout=60)
    return {x["id"]: x for x in map(json.loads, r.stdout.decode("utf-8").splitlines())}


def llama(n, nombre, args=None):
    return {"jsonrpc": "2.0", "id": n, "method": "tools/call", "params": {"name": nombre, "arguments": args or {}}}


class Mcp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = os.path.join(self.tmp, "repo")
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        self.dir = os.path.join(self.repo, ".git", "hackathon", "os")
        os.makedirs(self.dir)

    def deja_estado(self, estado):
        with open(os.path.join(self.dir, "estado.json"), "w", encoding="utf-8") as f:
            json.dump(estado, f)
        md = proyeccion.markdown(proyeccion.vista(estado), "persona-b", "x", tz=timezone.utc)
        with open(os.path.join(self.dir, "estado-equipo.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        return md

    def test_protocolo_y_herramientas(self):
        e = estado_base()
        e["colisiones"] = [
            {"id": "c1", "nivel": "1", "gravedad": "amarillo", "personas": ["persona-a", "persona-b"], "rutas": ["a.py"],
             "observado_en": "2026-11-20T10:00:00Z"},
            {"id": "c2", "nivel": "3", "gravedad": "rojo", "personas": ["persona-a", "persona-c"], "rutas": ["b.py"],
             "contrato": "API", "observado_en": "2026-11-20T10:00:00Z"}]
        md = self.deja_estado(e)
        r = conversa(self.repo, [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            llama(3, "estado"), llama(4, "tarea", {"id": "t10"}), llama(5, "colisiones"),
            llama(6, "colisiones", {"mias": False}), llama(7, "tarea", {"id": "T99"}),
            {"jsonrpc": "2.0", "id": 8, "method": "otro"}])
        self.assertEqual(r[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual([t["name"] for t in r[2]["result"]["tools"]], ["estado", "tarea", "colisiones", "reservar", "liberar"])
        texto = r[3]["result"]["content"][0]["text"]
        self.assertTrue(texto.startswith(md))
        self.assertIn("(generado_en: 2026-11-20T10:30:00Z)", texto)
        t = json.loads(r[4]["result"]["content"][0]["text"])
        self.assertEqual((t["tarea"]["id"], t["columna"]), ("T10", "haciendo"))
        self.assertEqual([c["id"] for c in json.loads(r[5]["result"]["content"][0]["text"])["colisiones"]], ["c1"])
        self.assertEqual([c["id"] for c in json.loads(r[6]["result"]["content"][0]["text"])["colisiones"]], ["c2", "c1"])
        self.assertTrue(r[7]["result"]["isError"])
        self.assertEqual(r[8]["error"]["code"], -32601)

    def test_reservar_y_liberar_con_el_relay(self):
        """M8g (K-73): reservar y liberar hablan con el relay de verdad (relay.url y token del demonio)."""
        import threading
        import relay as relay_mod
        from red import Servidor
        self.deja_estado(estado_base())
        r = relay_mod.Relay(os.path.join(self.tmp, "relay"), [{"persona": "persona-a", "nombre": "A"},
                                                             {"persona": "persona-b", "nombre": "B"}])
        srv = Servidor(("127.0.0.1", 0), relay_mod.manejador(r))
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        for n, v in (("relay.url", f"http://127.0.0.1:{srv.server_address[1]}"), ("token", r.token)):
            with open(os.path.join(self.dir, n), "w") as f:
                f.write(v + chr(10))
        absoluta = os.path.join(self.repo, "motor", "api.py")
        res = conversa(self.repo, [llama(1, "reservar", {"rutas": ["web/src/", absoluta], "ttl_s": 600}),
                                   llama(2, "reservar", {"rutas": ["../fuera.txt"]}),
                                   llama(3, "reservar", {"rutas": ["C:/otro/x.py"]})])
        x = json.loads(res[1]["result"]["content"][0]["text"])
        self.assertEqual(x["rutas"], ["web/src/", "motor/api.py"])
        self.assertTrue(res[2]["result"]["isError"] and res[3]["result"]["isError"])
        r.recalcular()
        self.assertEqual([(y["persona"], y["rutas"]) for y in r.estado["reservas"]], [("persona-b", ["web/src/", "motor/api.py"])])
        res = conversa(self.repo, [llama(1, "liberar", {"id": x["id"]}), llama(2, "liberar", {"id": x["id"] + "x"})])
        self.assertFalse(res[1]["result"]["isError"])
        self.assertTrue(res[2]["result"]["isError"])
        r.recalcular()
        self.assertEqual(r.estado["reservas"], [])

    def test_reservar_sin_relay_lo_dice(self):
        self.deja_estado(estado_base())
        res = conversa(self.repo, [llama(1, "reservar", {"rutas": ["a.py"]})])
        self.assertTrue(res[1]["result"]["isError"])
        self.assertIn("relay", res[1]["result"]["content"][0]["text"])

    def test_sin_estado_lo_dice(self):
        r = conversa(self.repo, [llama(1, "estado"), llama(2, "tarea", {"id": "T01"})])
        for i in (1, 2):
            self.assertIn("aún no ha recibido el estado", r[i]["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
