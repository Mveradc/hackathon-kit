# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""M8h, antes del ensayo (5 minutos, lo hace una persona): lo que solo se ve en una sesión interactiva de Claude Code.

  1. El bloque «Estado del equipo» al empezar la sesión (R-24) y si `hk-os` está en el PATH de la sesión (`! command -v hk-os`).
  2. Una colisión roja nueva (nivel 3: otra persona toca un contrato tuyo) abre un turno sola, por el monitor
     (criterio 5 de M8g), una vez.
  3. En tu siguiente mensaje, el delta (R-25) con la colisión, si el turno del monitor no la había contado ya.

Monta `../prueba-m8h-interactivo` (fuera del repo del kit): un remoto `bare`, tu clon con el OS activo, contratos y
autoridad de juguete (eres la dueña o el dueño del contrato «motor → web»), un relay y una segunda persona falsa
(@hk-persona-b) cuyos eventos manda este script. Tú eres la persona A, declarada con `hk-os unir --persona` (por defecto,
mveradc). El monitor del buzón lee los issues del sandbox (solo lectura). No gasta en modelos por sí mismo: lo que
gaste tu sesión (unos 0,10–0,30 USD).

Uso: uv run --no-project evals/coordinacion/interactivo.py [--yo mveradc] [--repo Mveradc/hk-sandbox]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(AQUI))
sys.path[:0] = [AQUI]
import colisiones_vivo as cv  # noqa: E402

CARPETA = os.path.join(os.path.dirname(KIT), "prueba-m8h-interactivo")


def ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def post(url, token, ruta, cuerpo):
    req = urllib.request.Request(url + ruta, data=json.dumps(cuerpo).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def pausa(texto):
    print("\n" + texto)
    input("   → Pulsa Enter cuando lo hayas hecho. ")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--yo", default="mveradc")
    p.add_argument("--repo", default="Mveradc/hk-sandbox")
    a = p.parse_args(argv)
    yo, otra = a.yo.lower(), "hk-persona-b"
    if os.path.exists(CARPETA):
        raise SystemExit(f"{CARPETA} ya existe: bórrala antes (es de una pasada anterior).")
    remoto, clon = CARPETA + "-remoto.git", CARPETA
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remoto], check=True)
    subprocess.run(["git", "clone", "-q", remoto, clon], check=True, capture_output=True)
    for k, v in (("user.email", f"{yo}@example.com"), ("user.name", yo)):
        cv.git(clon, "config", k, v)
    puerto = cv.libre()
    contratos = open(os.path.join(AQUI, "simulador", "contratos-g6.md"), encoding="utf-8").read()
    autoridad = (open(os.path.join(AQUI, "simulador", "autoridad-g6.md"), encoding="utf-8").read()
                 .replace("@persona-a", f"@{yo}").replace("@persona-b", f"@{otra}"))
    cv.escribe(clon, "docs/contratos.md", contratos)
    cv.escribe(clon, ".hackathon/autoridad.md", autoridad)
    cv.escribe(clon, ".hackathon/coordinacion.md", f"# Coordinación\nactiva: sí\nrepo: {a.repo}\n\n| Persona | GitHub |\n"
               f"|---|---|\n| Persona A | @{yo} |\n| Persona B | @{otra} |\n")
    cv.escribe(clon, ".hackathon/os.md", f"# Hackathon OS\nactiva: sí\nrelay: http://127.0.0.1:{puerto}\n")
    cv.escribe(clon, "motor/api.py", "def ficha(empresa):\n    return {}\n")
    cv.escribe(clon, ".gitignore", ".claude/worktrees/\n")
    cv.git(clon, "add", "-A")
    cv.git(clon, "commit", "-qm", "Juguete para la prueba interactiva de M8h")
    cv.git(clon, "push", "-q", "origin", "HEAD:main")
    log = os.path.join(CARPETA + "-relay.log")
    relay = subprocess.Popen(["uv", "run", "--no-project", "--quiet", os.path.join(KIT, "hkos", "cli.py"), "relay", "--ip",
                              "127.0.0.1", "--puerto", str(puerto), "--sin-github"], cwd=clon, stdout=open(log, "w"),
                             stderr=subprocess.STDOUT)
    try:
        if not cv.espera(lambda: "Token: " in open(log, encoding="utf-8", errors="replace").read(), 60):
            raise SystemExit("el relay no arranca: " + open(log, encoding="utf-8", errors="replace").read())
        token = next(l.split("Token: ", 1)[1].strip() for l in open(log, encoding="utf-8").read().splitlines() if "Token: " in l)
        url = f"http://127.0.0.1:{puerto}"
        r = subprocess.run(["uv", "run", "--no-project", "--quiet", os.path.join(KIT, "hkos", "cli.py"), "unir", url, token,
                            "--persona", yo], cwd=clon, capture_output=True, text=True, encoding="utf-8")
        print(r.stdout + r.stderr)
        print(f"Web (para mirarla mientras): {url}/#t={token}")
        pausa(f"PASO 1. En otra terminal:\n     cd \"{clon}\"\n     claude --plugin-dir \"{KIT.replace(os.sep, '/')}\"\n"
              "   Escribe: «Dime en una línea qué te dice el estado del equipo que recibiste al empezar».\n"
              "   Después: ! command -v hk-os\n"
              "   Apunta: ¿cita el bloque «Estado del equipo»? ¿Qué devuelve command -v (una ruta o nada)?")
        print("\nPASO 2. Mando eventos de la otra persona: toca motor/api.py, del contrato «motor → web», que es tuyo.")
        post(url, token, "/v1/eventos", {"eventos": [
            {"v": 1, "id": "interactivo-b-1", "ts": ahora(), "actor": {"persona": otra, "papel": "principal", "sesion": "sb"},
             "tipo": "sesion.inicio", "fuente": "hook"},
            {"v": 1, "id": "interactivo-b-2", "ts": ahora(), "actor": {"persona": otra, "papel": "principal", "sesion": "sb"},
             "tipo": "arbol", "fuente": "hook", "rutas": ["motor/api.py"]}]})
        roja = cv.espera(lambda: any(c["gravedad"] == "rojo" for c in cv.estado(url, token)["colisiones"]), 30)
        print("   El relay ya la tiene: " + ("ROJO, nivel 3." if roja else "NO (algo va mal: mira " + log + ")."))
        pausa("   Sin escribir nada, espera hasta 1 minuto. Apunta: ¿aparece sola una línea «ROJA nueva…» del monitor y "
              "Claude responde sin que escribas (se abre un turno)? ¿Solo una vez?")
        pausa("PASO 3. Escribe en la sesión: «¿Algo nuevo del equipo?».\n"
              "   Apunta: ¿lo sabe por el turno del monitor o por un delta («Cambios en el equipo…»)? ¿Lo trata como dato?")
        print("\nListo. Pega en el chat de Claude Code lo que has apuntado en los tres pasos. Cierra la sesión (/exit).")
    finally:
        relay.terminate() if os.name != "nt" else subprocess.run(["taskkill", "/T", "/F", "/PID", str(relay.pid)],
                                                                   capture_output=True)
        print(f"\nRelay parado. El demonio de tu clon se apaga solo a los 30 min sin sesiones. Para borrar la prueba: "
              f"rm -rf \"{CARPETA}\" \"{remoto}\" \"{log}\"")


if __name__ == "__main__":
    sys.exit(main())
