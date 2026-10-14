# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterio 1 de M8d: observa la presencia en el relay mientras corren sesiones reales.

Consulta GET /v1/estado cada 0,5 s (con el relay y el token que dejó `hk-os unir` en el clon) y anota, por actor, cuándo
aparece activo, cuándo deja de estarlo y su `ultimo_latido`. Con el JSONL de cada sesión (en los clones), da:
- aparición: desde el `ts` de su SessionStart hasta que el relay la muestra activa (criterio: ≤ 5 s);
- retirada: desde la última línea de la sesión (su SessionEnd, si llegó) hasta que deja de estar activa (≤ 90 s).

Uso: uv run --no-project evals/coordinacion/presencia.py --clon ../prueba-m8d-B --segundos 300 [--clones ../prueba-m8d-A …]
"""
import argparse
import glob
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone


def fecha(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def ahora():
    return datetime.now(timezone.utc)


def comun(clon):
    return subprocess.run(["git", "-C", clon, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                          capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clon", required=True, help="clon unido al relay (de él salen la URL y el token)")
    ap.add_argument("--clones", nargs="*", default=[], help="clones cuyas sesiones se miden (JSONL de eventos)")
    ap.add_argument("--segundos", type=float, default=300)
    a = ap.parse_args()
    d = os.path.join(comun(a.clon), "hackathon", "os")
    url = open(os.path.join(d, "relay.url")).read().strip()
    token = open(os.path.join(d, "token")).read().strip()
    vistos = {}         # actor → {aparece, desaparece, ultimo}
    fin = time.time() + a.segundos
    while time.time() < fin:
        try:
            req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=2) as r:
                e = json.loads(r.read())
        except OSError as ex:
            print(f"{ahora():%H:%M:%S} relay: {ex}", flush=True)
            time.sleep(1)
            continue
        t = ahora()
        for p in e["personas"]:
            for x in p["actores"]:
                k = (p["persona"], x.get("sesion"), x.get("agente") or "", x["papel"])
                v = vistos.setdefault(k, {})
                v["ultimo"] = x["ultimo_latido"]
                if x["activo"] and "aparece" not in v:
                    v["aparece"] = t
                    print(f"{t:%H:%M:%S.%f} activo   {k}", flush=True)
                if not x["activo"] and "aparece" in v and "desaparece" not in v:
                    v["desaparece"] = t
                    print(f"{t:%H:%M:%S.%f} inactivo {k} (último latido {x['ultimo_latido']})", flush=True)
        time.sleep(0.5)

    print("\nSesión | persona | aparición (s) | retirada desde su última línea (s) | SessionEnd")
    for clon in a.clones:
        for f in glob.glob(os.path.join(comun(clon), "hackathon", "os", "eventos", "*.jsonl")):
            sesion = os.path.basename(f)[:-6]
            lineas = []
            for l in open(f, encoding="utf-8"):
                try:
                    lineas.append(json.loads(l))
                except ValueError:
                    pass
            inicio = next((x for x in lineas if x.get("tipo") == "SessionStart" and not x.get("agent_id")), None)
            if not inicio:
                continue
            fin_ = next((x for x in lineas if x.get("tipo") == "SessionEnd"), None)
            ultima = max(fecha(x["ts"]) for x in lineas)
            v = next((v for k, v in vistos.items() if k[1] == sesion and not k[2]), {})
            ap_ = (v["aparece"] - fecha(inicio["ts"])).total_seconds() if "aparece" in v else None
            re_ = (v["desaparece"] - ultima).total_seconds() if "desaparece" in v else None
            print(f"{sesion} | {inicio.get('persona') or '(vacía)'} | {ap_ if ap_ is None else f'{ap_:.1f}'} | "
                  f"{re_ if re_ is None else f'{re_:.1f}'} | {'sí' if fin_ else 'no'}")


if __name__ == "__main__":
    main()
