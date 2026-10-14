# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""hk-os: arranque del Hackathon OS (M8d, R-02). Se lanza desde cualquier carpeta del clon.

  hk-os relay [--ip IP] [--puerto 7777]   quien coordina: arranca el relay e imprime la línea para los demás
  hk-os unir <url> <token>                cada persona, una vez: guarda el relay y el token y prueba la conexión
  hk-os agente …                          el demonio (lo lanza sesion.sh; ver agente.py)
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agente  # noqa: E402
import relay  # noqa: E402

USO = __doc__.split("\n\n", 1)[1]


def unir(url, token, cwd="."):
    comun = agente.git_comun(cwd)
    url = url.rstrip("/")
    if not url.startswith("http://"):
        print(f"hk-os unir: «{url}» no es una URL http://<ip>:<puerto>", file=sys.stderr)
        return 2
    carpeta = os.path.join(comun, "hackathon", "os")
    os.makedirs(carpeta, exist_ok=True)
    for nombre, valor in (("relay.url", url), ("token", token)):
        with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
            f.write(valor + "\n")
    req = urllib.request.Request(url + "/v1/estado", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            estado = json.loads(r.read())
    except urllib.error.HTTPError as ex:
        motivo = "el token no es el del relay" if ex.code == 401 else f"HTTP {ex.code}"
        print(f"Guardado en {carpeta}, pero el relay responde: {motivo}.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as ex:
        print(f"Guardado en {carpeta}, pero el relay no responde ({ex}). El demonio lo reintentará solo.", file=sys.stderr)
        return 1
    personas = ", ".join("@" + p["persona"] for p in estado.get("personas", []))
    print(f"Unido a {url} (equipo: {personas or 'vacío'}). El demonio envía los eventos desde la próxima sesión.")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(USO)
        return 0
    orden, resto = argv[0], argv[1:]
    if orden == "unir" and len(resto) == 2:
        return unir(*resto)
    if orden == "relay":
        comun = agente.git_comun(".")
        principal = comun[:-len("/.git")] if comun.endswith("/.git") else "."
        relay.main(["--dir", os.path.join(comun, "hackathon", "os", "relay"),
                    "--equipo", os.path.join(principal, ".hackathon", "coordinacion.md"), *resto])
        return 0
    if orden == "agente":
        return agente.main(resto)
    print(USO, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
