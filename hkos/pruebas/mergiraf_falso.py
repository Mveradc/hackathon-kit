"""Un `mergiraf` falso para las pruebas del nivel 2b (M11, K-111): anota cada llamada y devuelve el código que se le
pida. Lo que hace sale de un JSON cuya ruta está en la variable HK_MERGIRAF_FALSO:

  {"log": "<fichero donde anota una línea JSON por llamada>",
   "version": "mergiraf 0.20.0",          # lo que imprime --version; null: no responde (rc 2)
   "rc": {"<ruta>": 0},                   # código por ruta (la de --path-name=, o -p); si no está, "por_defecto"
   "por_defecto": 0,
   "espera": {"<ruta>": 3.0},             # segundos que tarda antes de salir
   "real": "<ruta del mergiraf real>"}    # opcional: anota y pasa la llamada al de verdad, con su código

Como el de verdad (P12), con rc 0 deja una copia en $XDG_DATA_HOME/mergiraf/merges/ y en %APPDATA% (Windows), y
escribe -o. Cada llamada anota sus argumentos, su cwd y su pid. `instalar(directorio, config)` deja un `mergiraf`
ejecutable en `directorio`, para ponerlo en el PATH; en Windows, un `mergiraf.exe` como el de verdad (el relay solo
acepta un .exe, #88): el lanzador de distlib que trae el pip de `ensurepip`, como los de pip.
"""
import glob
import io
import json
import os
import stat
import subprocess
import sys
import time
import zipfile


def instalar(directorio, config):
    """Crea el lanzador en `directorio` y devuelve el entorno que lo pone primero en el PATH."""
    os.makedirs(directorio, exist_ok=True)
    script = os.path.abspath(__file__)
    if os.name == "nt":
        exe(os.path.join(directorio, "mergiraf.exe"), script)
    else:
        ruta = os.path.join(directorio, "mergiraf")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\nexec '{sys.executable}' '{script}' \"$@\"\n")
        os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"PATH": directorio + os.pathsep + os.environ.get("PATH", ""), "HK_MERGIRAF_FALSO": config}


def exe(destino, script):
    """Un .exe que lanza `python script` con sus argumentos: el lanzador t64/t32 de distlib (del pip de `ensurepip`),
    con el `#!` del Python de las pruebas y un zip con __main__.py detrás, como los de los `console_scripts` de pip. El
    lanzador mete al hijo en un job: si se mata el .exe, muere con él, como el Mergiraf de verdad."""
    import ensurepip
    import platform
    nombre = "t64-arm.exe" if platform.machine().lower() in ("arm64", "aarch64") else \
        "t64.exe" if sys.maxsize > 2 ** 32 else "t32.exe"
    ruedas = glob.glob(os.path.join(os.path.dirname(ensurepip.__file__), "_bundled", "pip-*.whl"))
    if not ruedas:
        raise RuntimeError("sin la rueda de pip de ensurepip: no hay con qué hacer el mergiraf.exe falso")
    with zipfile.ZipFile(ruedas[0]) as z:
        lanzador = z.read(f"pip/_vendor/distlib/{nombre}")
    principal = io.BytesIO()
    with zipfile.ZipFile(principal, "w") as z:
        z.writestr("__main__.py", f"import runpy\nrunpy.run_path({script!r}, run_name='__main__')\n")
    with open(destino, "wb") as f:
        f.write(lanzador + f'#!"{sys.executable}"\n'.encode("utf-8") + principal.getvalue())


def ruta_de(args):
    """La ruta de `--path-name=<ruta>` (la forma que usa el relay desde #88), o la de `-p <ruta>`."""
    for a in args:
        if a.startswith("--path-name="):
            return a[len("--path-name="):]
    return opcion(args, "-p")


def opcion(args, nombre):
    return args[args.index(nombre) + 1] if nombre in args and args.index(nombre) + 1 < len(args) else None


def main(args):
    with open(os.environ["HK_MERGIRAF_FALSO"], encoding="utf-8") as f:
        conf = json.load(f)
    if conf.get("real") and args[:1] == ["--version"]:
        return subprocess.run([conf["real"], *args]).returncode
    if args[:1] == ["--version"]:
        if conf.get("version") is None:
            return 2
        print(conf.get("version", "mergiraf 0.20.0"))
        return 0
    ruta = ruta_de(args)
    entradas = [a for a in args[1:4]]
    llamada = {"args": args, "ruta": ruta, "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME"),
               "APPDATA": os.environ.get("APPDATA"), "cwd": os.getcwd(), "pid": os.getpid(),
               "entradas": [os.path.isfile(e) for e in entradas]}
    with open(conf["log"], "a", encoding="utf-8") as f:
        f.write(json.dumps(llamada) + "\n")
    if conf.get("real"):
        return subprocess.run([conf["real"], *args]).returncode
    time.sleep(conf.get("espera", {}).get(ruta, 0))
    if not all(os.path.isfile(e) for e in entradas):
        # Lo mataron por el plazo y ya se borró su directorio, pero este proceso sigue (un lanzador que no se lleva al
        # hijo, como un .cmd en Windows; el real es un solo .exe): no escribe nada, como si hubiera muerto.
        return 1
    rc = conf.get("rc", {}).get(ruta, conf.get("por_defecto", 0))
    if rc == 0:
        for var, sub in (("XDG_DATA_HOME", ("mergiraf", "merges")), ("APPDATA", ("Mergiraf", "merges"))):
            if os.environ.get(var):
                d = os.path.join(os.environ[var], *sub)
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "copia"), "w", encoding="utf-8") as f:
                    f.write("copia\n")
        if opcion(args, "-o"):
            with open(opcion(args, "-o"), "w", encoding="utf-8") as f:
                f.write("fusionado\n")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
