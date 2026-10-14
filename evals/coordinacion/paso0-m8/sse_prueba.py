# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Paso 0 de M8 (K-05, P14 y criterio 2 de ADR-0005). No es el relay: solo mide si el runtime aguanta.

Arranca un servidor HTTP + SSE con la biblioteca estándar (ThreadingHTTPServer), conecta N clientes SSE,
publica eventos a un ritmo fijo con POST y comprueba que cada cliente los recibe todos y en orden.

    python sse_prueba.py                 # 5 clientes, 50 eventos/s, 120 s
    uv run sse_prueba.py --segundos 30
    python sse_prueba.py --solo-servidor --host 0.0.0.0 --puerto 7777   # para P15 (dos portátiles)
    python sse_prueba.py --solo-clientes --url http://<ip>:7777 ...
Sale con 0 si no se pierde nada.
"""
import argparse, json, queue, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = "prueba-m8"
suscriptores: list[queue.Queue] = []
cerrojo = threading.Lock()


class Relay(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _ok_token(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401); self.send_header("Content-Length", "0"); self.end_headers()
            return False
        return True

    def do_POST(self):
        if not self._ok_token():
            return
        cuerpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            eventos = json.loads(cuerpo)
        except ValueError:
            self.send_response(400); self.send_header("Content-Length", "0"); self.end_headers(); return
        with cerrojo:
            for q in suscriptores:
                for e in eventos:
                    q.put(e)
        self.send_response(204); self.send_header("Content-Length", "0"); self.end_headers()

    def do_GET(self):
        if not self._ok_token():
            return
        q: queue.Queue = queue.Queue()
        with cerrojo:
            suscriptores.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(b": hola\n\n"); self.wfile.flush()
            while True:
                try:
                    e = q.get(timeout=20)
                    self.wfile.write(f"id: {e['n']}\nevent: estado\ndata: {json.dumps(e)}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b"event: ping\ndata: {}\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            with cerrojo:
                suscriptores.remove(q)


def cliente(url, nombre, recibidos, parar):
    req = urllib.request.Request(url + "/v1/stream", headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        for linea in r:
            if parar.is_set():
                return
            if linea.startswith(b"data: ") and b'"n"' in linea:
                e = json.loads(linea[6:])
                recibidos[nombre].append((e["n"], time.time() - e["t"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--clientes", type=int, default=5)
    p.add_argument("--ritmo", type=int, default=50, help="eventos por segundo")
    p.add_argument("--segundos", type=int, default=120)
    p.add_argument("--lote", type=int, default=5, help="eventos por POST")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--puerto", type=int, default=0)
    p.add_argument("--solo-servidor", action="store_true")
    p.add_argument("--solo-clientes", action="store_true")
    p.add_argument("--url")
    a = p.parse_args()
    print(f"Python {sys.version.split()[0]} · {sys.executable}")

    if not a.solo_clientes:
        srv = ThreadingHTTPServer((a.host, a.puerto), Relay)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://{a.host if a.host != '0.0.0.0' else '127.0.0.1'}:{srv.server_address[1]}"
        print(f"Servidor en {a.host}:{srv.server_address[1]}")
        if a.solo_servidor:
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                return 0
    else:
        url = a.url.rstrip("/")

    recibidos = {f"c{i}": [] for i in range(a.clientes)}
    parar = threading.Event()
    hilos = [threading.Thread(target=cliente, args=(url, k, recibidos, parar), daemon=True) for k in recibidos]
    for h in hilos:
        h.start()
    time.sleep(1)

    total = a.ritmo * a.segundos
    inicio = time.time(); n = 0
    while n < total:
        lote = [{"n": n + i, "t": time.time()} for i in range(min(a.lote, total - n))]
        req = urllib.request.Request(url + "/v1/eventos", data=json.dumps(lote).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        n += len(lote)
        espera = inicio + n / a.ritmo - time.time()
        if espera > 0:
            time.sleep(espera)
    time.sleep(3)
    parar.set()

    malos = 0
    for k, v in recibidos.items():
        ns = [x for x, _ in v]
        lat = sorted(l for _, l in v) or [0]
        bien = ns == list(range(total))
        malos += not bien
        print(f"{k}: {len(ns)}/{total} {'en orden' if bien else 'PERDIDOS O DESORDENADOS'} · "
              f"latencia p50 {lat[len(lat)//2]*1000:.1f} ms · p99 {lat[int(len(lat)*.99)]*1000:.1f} ms · máx {lat[-1]*1000:.1f} ms")
    print(f"{total} eventos en {time.time()-inicio:.1f} s a {a.clientes} clientes · {'OK' if not malos else 'FALLO'}")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
