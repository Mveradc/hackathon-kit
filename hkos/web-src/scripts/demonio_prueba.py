# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Un demonio de verdad (hkos/agente.py, con `web_nueva: sí`) para probar la web en un navegador, en un repo temporal y
sin relay, GitHub ni modelo. Lo usa scripts/pestanas_chrome.mjs (issue #15).

- Sirve el compilado (hkos/web/nueva/, o el de --web) y las rutas de datos con el manejador real del demonio.
- El estado es el de un relay de verdad recién creado con dos personas; el demonio lo sirve como persona-a.
- `PING_S` baja a --ping segundos: el demonio solo nota que un cliente de /v1/stream se ha ido al escribirle.
- Un puerto de control (solo 127.0.0.1): GET /clientes → cuántos /v1/stream tiene abiertos el demonio;
  POST /marca?texto=… → una novedad nueva en el estado y una `vista` a la web (para ver que sigue llegando).

Escribe en la salida una línea JSON {"puerto", "token", "control"} y sirve hasta que se cierra su entrada.
Uso: uv run --no-project scripts/demonio_prueba.py [--web DIR] [--ping S]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KIT)
import agente as agente_mod  # noqa: E402
import relay as relay_mod  # noqa: E402
from red import Servidor  # noqa: E402

PERSONAS = [{"persona": "persona-a", "nombre": "A"}, {"persona": "persona-b", "nombre": "B"}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", help="carpeta del compilado (por defecto, hkos/web/nueva)")
    ap.add_argument("--ping", type=float, default=2.0)
    args = ap.parse_args()
    if args.web:
        agente_mod.WEB_NUEVA = os.path.abspath(args.web)
    agente_mod.PING_S = args.ping

    tmp = tempfile.mkdtemp(prefix="hk-pestanas-")
    try:
        repo = os.path.join(tmp, "repo").replace("\\", "/")
        subprocess.run(["git", "init", "-q", repo], check=True)
        os.makedirs(os.path.join(repo, ".hackathon"))
        with open(os.path.join(repo, ".hackathon", "os.md"), "w", encoding="utf-8") as f:
            f.write("# Hackathon OS\nactiva: sí\nweb_nueva: sí\n")
        relay = relay_mod.Relay(os.path.join(tmp, "relay"), PERSONAS, web_nueva=True)
        relay.recalcular()
        ag = agente_mod.Agente(repo, "persona-a", ahora=relay_mod.ahora_iso)
        ag.estado = relay.estado
        srv = Servidor(("127.0.0.1", 0), agente_mod.manejador(ag))
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()

        class Control(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _texto(self, texto):
                cuerpo = str(texto).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def do_GET(self):
                with ag.web_cambio:
                    self._texto(ag.web_clientes)

            def do_POST(self):
                texto = parse_qs(urlsplit(self.path).query).get("texto", ["marca"])[0]
                with ag.lock:
                    ag.estado = dict(ag.estado, novedades=[{"tipo": "criterio", "resumen": texto, "autor": "@persona-b",
                                                            "observado_en": relay_mod.ahora_iso()}])
                ag.a_la_web("vista")
                self._texto("ok")

        control = ThreadingHTTPServer(("127.0.0.1", 0), Control)
        threading.Thread(target=control.serve_forever, daemon=True).start()
        print(json.dumps({"puerto": srv.server_address[1], "token": ag.web_token,
                          "control": control.server_address[1]}), flush=True)
        sys.stdin.read()                                  # hasta que quien lo lanzó cierre la entrada
        srv.shutdown()
        control.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
