# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterio 1 de M8f: el relay de verdad (hkos/relay.py) sirviendo la web en la IP de la LAN, con las tareas del reto
03 (sin GitHub: un sondeo fijo con tareas-03.json), los eventos de un guion desplazados a la hora actual y dos
colisiones del estado sintético (fixture.py; calcularlas es de M8g). Imprime la URL de la web con el token.

Después, cada evento que se mande a POST /v1/eventos cambia la vista (por ejemplo, con --evento, desde otra consola).

  uv run --no-project evals/coordinacion/web_demo.py --ip <IP de la LAN> [--puerto 7777] [--guion G2]
  uv run --no-project evals/coordinacion/web_demo.py --evento <url> <token>     # manda una edición de persona-a en T01
"""
import argparse
import json
import os
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(AQUI))
sys.path[:0] = [os.path.join(KIT, "hkos"), os.path.join(AQUI, "simulador")]
import relay as relay_mod  # noqa: E402
from fixture import estado_5x20  # noqa: E402
from red import Servidor  # noqa: E402
from simula import carga, montar  # noqa: E402


class SondeoFijo:
    def __init__(self, tareas, issues):
        self.tareas, self.issues, self.estado = tareas, issues, "ok"
        self.ultimo_ok = datetime.now(timezone.utc).timestamp()

    def resultado(self, ahora):
        self.ultimo_ok = datetime.now(timezone.utc).timestamp()
        return self.tareas, self.issues, [], 0


def evento(url, token):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    e = {"v": 1, "id": f"demo-{ts}", "ts": ts, "tipo": "edicion", "fuente": "hook", "tarea": "T01",
         "rutas": ["motor/ficha.py"], "actor": {"persona": "persona-a", "papel": "principal", "sesion": "demo-a"}}
    req = urllib.request.Request(url.rstrip("/") + "/v1/eventos", data=json.dumps({"eventos": [e]}).encode(),
                                 method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        print(ts, r.read().decode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ip")
    p.add_argument("--puerto", type=int, default=7777)
    p.add_argument("--guion", default="G2")
    p.add_argument("--evento", nargs=2, metavar=("URL", "TOKEN"))
    a = p.parse_args()
    if a.evento:
        return evento(*a.evento)
    guion = carga(os.path.join(AQUI, "simulador", "guiones", f"{a.guion}.json"))
    fin = max(x["t"] for x in guion["pasos"])
    guion["inicio"] = (datetime.now(timezone.utc) - timedelta(seconds=fin + 60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tareas, personas, issues, eventos, _ = montar(guion, os.path.join(AQUI, "simulador"))
    colisiones = [dict(c, observado_en=(datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ"))
                  for c in estado_5x20()["colisiones"][:2]]
    calcular = relay_mod.calcular

    def con_colisiones(*args, **kw):
        e = calcular(*args, **kw)
        e["colisiones"] = colisiones
        return e
    relay_mod.calcular = con_colisiones
    if not relay_mod.ip_permitida(a.ip or ""):
        raise SystemExit(f"{a.ip}: no es 127.0.0.1, LAN privada ni Tailscale (R-32)")
    r = relay_mod.Relay(tempfile.mkdtemp(prefix="hk-web-"), personas, sondeo=SondeoFijo(tareas, issues))
    r.recibir({"eventos": eventos})
    srv = Servidor((a.ip, a.puerto), relay_mod.manejador(r))
    parar = threading.Event()
    threading.Thread(target=r.bucle, args=(parar,), daemon=True).start()
    url = f"http://{a.ip}:{a.puerto}"
    print(f"Web: {url}/#t={r.token}", flush=True)
    print(f"Evento: uv run --no-project evals/coordinacion/web_demo.py --evento {url} {r.token}", flush=True)
    try:
        srv.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        srv.server_close()


if __name__ == "__main__":
    sys.exit(main())
