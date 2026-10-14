# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""G11 (criterio 5 de M8d): 5 personas con 3 actores cada una mandan 50 eventos/s en total al relay durante 2 min,
con 5 clientes SSE conectados. Sin modelos.

Lanza un relay de verdad (hkos/relay.py, en otro proceso) en una carpeta temporal. «Sin perder ninguno»:
- el relay acepta todos los eventos, sin repetidos, y su registro tiene todos, en el orden en que los mandó cada persona;
- cada cliente SSE recibe, para cada evento, una instantánea de estado.json en la que el `ultimo_latido` de su actor ya
  es ≥ el `ts` del evento, y ese `ultimo_latido` nunca retrocede;
- la latencia desde que el relay confirma el POST hasta esa instantánea, p50/p99/máx (objetivo de R-26: ≤ 5 s).

Uso: uv run --no-project evals/coordinacion/simulador/carga.py [--segundos 120] [--ritmo 50] [--clientes 5]
Sale con 1 si se pierde algún evento o la latencia máxima pasa de 5 s.
"""
import argparse
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
PERSONAS = [f"persona-{c}" for c in "abcde"]


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def percentil(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))] if xs else float("nan")


class Cliente(threading.Thread):
    """Un navegador o un demonio escuchando /v1/stream. Guarda (hora de llegada, {actor: ultimo_latido})."""

    def __init__(self, puerto, token):
        super().__init__(daemon=True)
        self.puerto, self.token = puerto, token
        self.mensajes, self.errores, self.retrocesos = [], [], 0
        self.parar = threading.Event()

    def run(self):
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=30)
        c.request("GET", "/v1/stream", headers={"Authorization": f"Bearer {self.token}"})
        r = c.getresponse()
        visto, evento, datos = {}, None, None
        try:
            while not self.parar.is_set():
                l = r.fp.readline()
                if not l:
                    self.errores.append("el relay cerró el stream")
                    return
                l = l.decode("utf-8").rstrip("\n")
                if l.startswith("event: "):
                    evento = l[7:]
                elif l.startswith("data: "):
                    datos = l[6:]
                elif l == "":
                    if evento == "estado" and datos:
                        t = time.monotonic()
                        e = json.loads(datos)
                        ult = {}
                        for p in e["personas"]:
                            for a in p["actores"]:
                                k = (p["persona"], a.get("sesion"), a.get("agente"))
                                ult[k] = a["ultimo_latido"]
                                if visto.get(k, "") > a["ultimo_latido"]:
                                    self.retrocesos += 1
                                visto[k] = a["ultimo_latido"]
                        self.mensajes.append((t, ult))
                    evento, datos = None, None
        except OSError as ex:
            if not self.parar.is_set():
                self.errores.append(repr(ex))
        finally:
            c.close()


class Emisor(threading.Thread):
    """El demonio de una persona: 3 actores (sesión principal, orquestador y un worker), lotes cada 200 ms."""

    def __init__(self, persona, puerto, token, por_segundo, hasta):
        super().__init__(daemon=True)
        self.persona, self.puerto, self.token, self.hasta = persona, puerto, token, hasta
        self.por_lote = max(1, round(por_segundo / 5))
        self.enviados = []          # (id, actor, ts, hora de la confirmación)
        self.aceptados = self.repetidos = 0
        self.errores = []
        p = persona[-1]
        self.actores = [({"persona": persona, "papel": "principal", "sesion": f"s{p}1"}, f"s{p}1"),
                        ({"persona": persona, "papel": "orquestador", "sesion": f"s{p}2"}, f"s{p}2"),
                        ({"persona": persona, "papel": "worker", "sesion": f"s{p}2", "agente": f"w{p}"}, f"s{p}2")]

    def run(self):
        n, siguiente = 0, time.monotonic()
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        while time.monotonic() < self.hasta:
            lote = []
            for _ in range(self.por_lote):
                actor, sesion = self.actores[n % 3]
                n += 1
                lote.append({"v": 1, "id": f"{sesion}-{n}", "ts": ahora_iso(), "actor": actor,
                             "tipo": "arbol" if n % 2 else "edicion", "rutas": [f"src/{self.persona}/f{n % 17}.py"],
                             "fuente": "hook"})
            try:
                c.request("POST", "/v1/eventos", body=json.dumps({"eventos": lote}),
                          headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
                r = c.getresponse()
                cuerpo = json.loads(r.read())
                t = time.monotonic()
                if r.status != 200:
                    self.errores.append(f"HTTP {r.status}: {cuerpo}")
                else:
                    self.aceptados += cuerpo["aceptados"]
                    self.repetidos += cuerpo["repetidos"]
                    for e in lote:
                        a = e["actor"]
                        self.enviados.append((e["id"], (a["persona"], a["sesion"], a.get("agente")), e["ts"], t))
            except (OSError, ValueError, http.client.HTTPException) as ex:
                self.errores.append(repr(ex))
                c.close()
                c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
            siguiente += 0.2
            time.sleep(max(0, siguiente - time.monotonic()))
        c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segundos", type=float, default=120)
    ap.add_argument("--ritmo", type=int, default=50, help="eventos por segundo entre todas las personas")
    ap.add_argument("--clientes", type=int, default=5)
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="hk-carga-")
    equipo = os.path.join(tmp, "coordinacion.md")
    with open(equipo, "w", encoding="utf-8") as f:
        f.write("| Persona | GitHub |\n|---|---|\n" + "".join(f"| {p[-1].upper()} | @{p} |\n" for p in PERSONAS))
    carpeta, puerto = os.path.join(tmp, "relay"), puerto_libre()
    relay = subprocess.Popen([sys.executable, os.path.join(KIT, "hkos", "relay.py"), "--dir", carpeta, "--equipo", equipo,
                              "--ip", "127.0.0.1", "--puerto", str(puerto)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", puerto), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        with open(os.path.join(carpeta, "token"), encoding="utf-8") as f:
            token = f.read().strip()

        clientes = [Cliente(puerto, token) for _ in range(a.clientes)]
        for c in clientes:
            c.start()
        time.sleep(1)
        inicio = time.monotonic()
        emisores = [Emisor(p, puerto, token, a.ritmo / len(PERSONAS), inicio + a.segundos) for p in PERSONAS]
        for e in emisores:
            e.start()
        for e in emisores:
            e.join()
        duracion = time.monotonic() - inicio
        time.sleep(6)                       # margen para el último recálculo
        for c in clientes:
            c.parar.set()

        enviados = [x for e in emisores for x in e.enviados]
        aceptados, repetidos = sum(e.aceptados for e in emisores), sum(e.repetidos for e in emisores)
        errores_post = [x for e in emisores for x in e.errores]
        with open(os.path.join(carpeta, "eventos.jsonl"), encoding="utf-8") as f:
            registro = [json.loads(l)["id"] for l in f]
        orden_ok = all([i for i in registro if i in {x[0] for x in e.enviados}] == [x[0] for x in e.enviados] for e in emisores)

        print(f"Relay en 127.0.0.1:{puerto}; {len(PERSONAS)} personas × 3 actores; {a.clientes} clientes SSE; {a.segundos:g} s")
        print(f"Enviados y confirmados: {len(enviados)} en {duracion:.1f} s ({len(enviados) / duracion:.1f}/s); "
              f"aceptados {aceptados}, repetidos {repetidos}, errores de POST {len(errores_post)}")
        print(f"Registro del relay: {len(registro)} líneas, {len(set(registro))} distintas; orden de cada persona: {'sí' if orden_ok else 'NO'}")
        fallo = not (aceptados == len(enviados) and repetidos == 0 and not errores_post and len(registro) == len(enviados)
                     and len(set(registro)) == len(registro) and orden_ok)
        for i, c in enumerate(clientes, 1):
            perdidos, lat = 0, []
            j = 0
            msgs = c.mensajes
            # Para cada evento, la primera instantánea (llegada después de su confirmación) que ya lo refleja.
            for ident, actor, ts, t_ok in sorted(enviados, key=lambda x: x[3]):
                k = next((m for m in msgs if m[0] >= t_ok - 1 and m[1].get(actor, "") >= ts), None)
                if k is None:
                    perdidos += 1
                else:
                    lat.append(max(0.0, k[0] - t_ok))
            print(f"Cliente {i}: {len(msgs)} instantáneas; eventos reflejados {len(enviados) - perdidos}/{len(enviados)}; "
                  f"retrocesos {c.retrocesos}; errores {len(c.errores)}; latencia p50 {percentil(lat, 50) * 1000:.0f} ms, "
                  f"p99 {percentil(lat, 99) * 1000:.0f} ms, máx {max(lat, default=float('nan')) * 1000:.0f} ms")
            fallo |= bool(perdidos or c.retrocesos or c.errores or not lat or max(lat) > 5)
        print("OK" if not fallo else "FALLO")
        return 1 if fallo else 0
    finally:
        relay.terminate()
        try:
            relay.wait(5)
        except subprocess.TimeoutExpired:
            relay.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
