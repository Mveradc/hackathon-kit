# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterios 2 y 3 de M8d, sin modelos: hooks reales (scripts/os/emite.sh) en dos clones, cada uno con su demonio
(lanzado por scripts/os/arranque.sh, como en SessionStart), y un relay que se tumba y se reinicia.

1. Relay arriba: hooks a ritmo constante en los dos clones; se mide el coste de cada hook.
2. Criterio 3: relay parado `--caida` segundos (300 por defecto) mientras siguen los hooks: ninguno falla ni se
   ralentiza; al volver, todos los eventos llegan y, por sesión, en orden.
3. Criterio 2: reinicio brusco del relay con hooks en marcha: no se pierde nada. Después, un demonio sin
   posiciones.json lo reenvía todo y el relay lo descarta (el registro no crece).

Uso (desde la raíz del kit, con los clones unidos al relay y `os.md` activo):
  uv run --no-project evals/coordinacion/caidas_relay.py --relay-clon ../prueba-m8d-B --clones ../prueba-m8d-B ../prueba-m8d-A \
      --personas mveradc hk-persona-b [--caida 300] [--puerto 7777]
"""
import argparse
import glob
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "hkos"))
from normaliza import normalizar_fichero  # noqa: E402
from red import ahora_iso  # noqa: E402

BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe"))
                 if os.path.exists(b)), BASH)
EMITE, ARRANQUE = os.path.join(KIT, "scripts", "os", "emite.sh"), os.path.join(KIT, "scripts", "os", "arranque.sh")


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, check=True).stdout.strip()


def log(texto):
    print(f"{time.strftime('%H:%M:%S')} {texto}", flush=True)


class Clon:
    def __init__(self, ruta, persona, etiqueta):
        self.ruta, self.persona = os.path.abspath(ruta).replace("\\", "/"), persona
        self.comun = git(self.ruta, "rev-parse", "--path-format=absolute", "--git-common-dir")
        self.sesion = f"m8d-{etiqueta}-{int(time.time())}"
        self.n = 0
        self.tiempos = {}       # fase → [ms]
        self.fallos = 0

    def hook(self, fase, entrada):
        t = time.perf_counter()
        r = subprocess.run([BASH, EMITE], input=json.dumps(entrada), capture_output=True, text=True, cwd=self.ruta)
        self.tiempos.setdefault(fase, []).append((time.perf_counter() - t) * 1000)
        self.fallos += r.returncode != 0 or bool(r.stdout.strip())

    def paso(self, fase):
        self.n += 1
        if self.n == 1:
            self.hook(fase, {"hook_event_name": "SessionStart", "session_id": self.sesion, "cwd": self.ruta, "source": "startup"})
        else:
            self.hook(fase, {"hook_event_name": "PostToolUse", "session_id": self.sesion, "cwd": self.ruta, "tool_name": "Edit",
                             "tool_input": {"file_path": f"{self.ruta}/src/f{self.n % 7}.py"}, "tool_use_id": f"toolu_{self.n}"})

    def arrancar_demonio(self):
        subprocess.run([BASH, ARRANQUE, self.sesion, self.persona], cwd=self.ruta, capture_output=True, text=True)

    def salud(self):
        try:
            puerto = int(open(os.path.join(self.comun, "hackathon", "os", "agente.vivo")).read())
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/salud", timeout=2) as r:
                return dict(l.split(": ", 1) for l in r.read().decode().splitlines()[1:])
        except (OSError, ValueError):
            return None

    def esperados(self):
        """IDs de los eventos que el demonio debería haber enviado de la sesión de esta prueba."""
        f = os.path.join(self.comun, "hackathon", "os", "eventos", f"{self.sesion}.jsonl")
        return [e["id"] for e in normalizar_fichero(f)] if os.path.exists(f) else []


class Relay:
    def __init__(self, clon, puerto):
        self.clon, self.puerto = clon, puerto
        self.dir = os.path.join(git(clon, "rev-parse", "--path-format=absolute", "--git-common-dir"), "hackathon", "os", "relay")
        self.p = None

    def arrancar(self):
        # Python directo (no uv run) para poder matar el proceso de verdad, como una caída.
        self.p = subprocess.Popen([sys.executable, os.path.join(KIT, "hkos", "relay.py"), "--dir", self.dir,
                                   "--equipo", os.path.join(self.clon, ".hackathon", "coordinacion.md"),
                                   "--ip", "127.0.0.1", "--puerto", str(self.puerto)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}/v1/estado", timeout=0.5)
            except urllib.error.HTTPError:
                return                                  # 401: escucha
            except OSError:
                time.sleep(0.2)
        raise SystemExit("el relay no arranca")

    def matar(self):
        self.p.kill()
        self.p.wait()

    def registro(self):
        try:
            with open(os.path.join(self.dir, "eventos.jsonl"), encoding="utf-8") as f:
                return [json.loads(l)["id"] for l in f if l.strip()]
        except OSError:
            return []


def espera_entrega(clones, relay, tope=90):
    t0 = time.time()
    while time.time() - t0 < tope:
        reg = set(relay.registro())
        if all(set(c.esperados()) <= reg for c in clones):
            return time.time() - t0
        time.sleep(1)
    return None


def en_orden(relay, clon):
    ids = [i for i in relay.registro() if i.startswith(clon.sesion + "-")]
    lineas = [int(i[len(clon.sesion) + 1:].split(".")[0]) for i in ids]
    return lineas == sorted(lineas), len(ids)


def fase(clones, nombre, segundos, cada=2.0):
    fin = time.time() + segundos
    while time.time() < fin:
        for c in clones:
            c.paso(nombre)
        time.sleep(cada)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay-clon", required=True)
    ap.add_argument("--clones", nargs="+", required=True)
    ap.add_argument("--personas", nargs="+", required=True)
    ap.add_argument("--caida", type=float, default=300)
    ap.add_argument("--puerto", type=int, default=7777)
    a = ap.parse_args()
    clones = [Clon(r, p, chr(ord("a") + i)) for i, (r, p) in enumerate(zip(a.clones, a.personas))]
    relay = Relay(a.relay_clon, a.puerto)
    ok = True

    relay.arrancar()
    log(f"relay arriba en :{a.puerto}; registro con {len(relay.registro())} eventos")
    for c in clones:
        c.paso("arriba")
        c.arrancar_demonio()
    time.sleep(5)
    for c in clones:
        log(f"demonio de {c.persona}: {c.salud()}")
    fase(clones, "arriba", 30)
    t = espera_entrega(clones, relay)
    log(f"fase 1 (relay arriba): todo entregado en {t:.0f} s" if t is not None else "fase 1: NO se entregó todo")
    ok &= t is not None

    log(f"criterio 3: relay parado {a.caida:g} s con los hooks en marcha")
    relay.matar()
    t_caida = ahora_iso()
    fase(clones, "caido", a.caida)
    for c in clones:
        log(f"  demonio de {c.persona} con el relay caído: {c.salud()}")
    antes = len(relay.registro())
    relay.arrancar()
    log(f"relay de vuelta (caído desde {t_caida}); registro con {antes} eventos")
    t = espera_entrega(clones, relay)
    log(f"  todo entregado {t:.0f} s después de volver" if t is not None else "  NO se entregó todo")
    ok &= t is not None
    for c in clones:
        orden, n = en_orden(relay, c)
        log(f"  {c.persona}: {n} eventos de la sesión en el registro; en orden: {'sí' if orden else 'NO'}")
        ok &= orden

    log("criterio 2: reinicio brusco del relay con hooks en marcha")
    for i in range(3):
        fase(clones, "reinicio", 6, cada=1.0)
        relay.matar()
        fase(clones, "reinicio", 2, cada=1.0)
        relay.arrancar()
    fase(clones, "reinicio", 6, cada=1.0)
    t = espera_entrega(clones, relay)
    reg = relay.registro()
    log(f"  tras 3 reinicios: todo entregado ({t:.0f} s); registro {len(reg)} líneas, {len(set(reg))} distintas"
        if t is not None else "  NO se entregó todo")
    ok &= t is not None and len(reg) == len(set(reg))

    c = clones[-1]
    os_dir = os.path.join(c.comun, "hackathon", "os")
    puerto = int(open(os.path.join(os_dir, "agente.vivo")).read())
    log(f"  demonio de {c.persona} sin posiciones.json: se para, se borra y se relanza")
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    f"Get-NetTCPConnection -LocalPort {puerto} -State Listen | % {{ Stop-Process -Id $_.OwningProcess -Force }}"]
                   if os.name == "nt" else ["fuser", "-k", f"{puerto}/tcp"], capture_output=True)
    time.sleep(2)
    os.remove(os.path.join(os_dir, "posiciones.json"))
    try:
        os.remove(os.path.join(os_dir, "agente.vivo"))
    except OSError:
        pass
    antes = len(relay.registro())
    total = sum(len(normalizar_fichero(f)) for f in glob.glob(os.path.join(os_dir, "eventos", "*.jsonl")))
    c.arrancar_demonio()
    for _ in range(60):
        s = c.salud()
        if s and s.get("pendientes") == "0" and s.get("relay") == "ok":
            break
        time.sleep(1)
    despues = len(relay.registro())
    log(f"  reenviados {total} eventos de sus JSONL; el registro pasa de {antes} a {despues} (repetidos descartados); salud {s}")
    ok &= despues == antes

    for c in clones:
        for nombre, ts in c.tiempos.items():
            log(f"hooks de {c.persona}, fase «{nombre}»: {len(ts)} llamadas, mediana {statistics.median(ts):.0f} ms, "
                f"p95 {sorted(ts)[int(0.95 * len(ts))]:.0f} ms, máx {max(ts):.0f} ms")
        log(f"hooks de {c.persona} con fallo o con salida: {c.fallos}")
        ok &= c.fallos == 0
    relay.matar()
    log("OK" if ok else "FALLO")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
