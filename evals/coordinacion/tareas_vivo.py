# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterios 2–4 de M8e en vivo: observa el estado de las tareas en el relay mientras pasan cosas de verdad
(orquestador, commits a mano, issues cerrados en GitHub).

Consulta GET /v1/estado cada 2 s (con el relay y el token que dejó `hk-os unir` en el clon) y apunta cada cambio de
estado de una tarea, con su fuente y su hora de observación, el ⚑ declarado si lo hay, y lo que entra en `sin_tarea`
y en `discrepancias`. Al terminar, la secuencia de cada tarea vista, para compararla con la tabla de diseno.md §5.

Uso: uv run --no-project evals/coordinacion/tareas_vivo.py --clon ../prueba-m8e-B --segundos 1800 [--tareas T08 T11 …]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone


def comun(clon):
    return subprocess.run(["git", "-C", clon, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                          capture_output=True, text=True, check=True).stdout.strip()


def main():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--clon", required=True)
    ap.add_argument("--segundos", type=float, default=1800)
    ap.add_argument("--tareas", nargs="*", help="solo estas (por defecto, todas)")
    a = ap.parse_args()
    d = os.path.join(comun(a.clon), "hackathon", "os")
    url, token = (open(os.path.join(d, n), encoding="utf-8").read().strip() for n in ("relay.url", "token"))
    visto, secuencias, sin_tarea, disc = {}, {}, set(), set()
    fin = time.time() + a.segundos
    while time.time() < fin:
        try:
            req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=5) as r:
                e = json.loads(r.read())
        except OSError as ex:
            print(f"{datetime.now(timezone.utc):%H:%M:%S} relay: {ex}", flush=True)
            time.sleep(2)
            continue
        ahora = f"{datetime.now(timezone.utc):%H:%M:%S}"
        for t in e["tareas"]:
            if a.tareas and t["id"] not in a.tareas:
                continue
            est, dec = t["estado"], t.get("declarado")
            clave = (est["valor"], est["fuente"], dec["valor"] if dec else None)
            if visto.get(t["id"]) != clave:
                visto[t["id"]] = clave
                texto = f"{est['valor']} ({est['fuente']}, {est['observado_en'][11:19]})" + (f" ⚑ {dec['valor']}" if dec else "")
                secuencias.setdefault(t["id"], []).append(texto)
                print(f"{ahora} {t['id']} {texto}", flush=True)
        for s in e.get("sin_tarea", []):
            k = (s["persona"], s["que"])
            if k not in sin_tarea:
                sin_tarea.add(k)
                print(f"{ahora} sin_tarea: @{s['persona']} {s['que']}", flush=True)
        for x in e.get("discrepancias", []):
            k = (x["tipo"], x.get("tarea"), x.get("persona"))
            if k not in disc:
                disc.add(k)
                print(f"{ahora} discrepancia: {x['tipo']} {x.get('tarea', '')} @{x.get('persona', '')}: {x['detalle'][:120]}",
                      flush=True)
        time.sleep(2)
    print("\nSecuencias:")
    for tid in sorted(secuencias):
        if len(secuencias[tid]) > 1 or a.tareas:
            print(f"  {tid}: " + " → ".join(secuencias[tid]))


if __name__ == "__main__":
    main()
