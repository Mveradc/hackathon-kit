"""Un `mergiraf` falso para las pruebas del nivel 2b (M11, K-111): anota cada llamada y devuelve el código que se le
pida. Lo que hace sale de un JSON cuya ruta está en la variable HK_MERGIRAF_FALSO:

  {"log": "<fichero donde anota una línea JSON por llamada>",
   "version": "mergiraf 0.20.0",          # lo que imprime --version; null: no responde (rc 2)
   "rc": {"<ruta de -p>": 0},             # código por ruta; si no está, "por_defecto"
   "por_defecto": 0,
   "espera": {"<ruta de -p>": 3.0},       # segundos que tarda antes de salir
   "real": "<ruta del mergiraf real>"}    # opcional: anota y pasa la llamada al de verdad, con su código

Como el de verdad (P12), con rc 0 deja una copia en $XDG_DATA_HOME/mergiraf/merges/ y en %APPDATA% (Windows), y
escribe -o. `instalar(directorio, config)` deja un `mergiraf` ejecutable (`mergiraf.cmd` en Windows) en `directorio`,
para ponerlo en el PATH.
"""
import json
import os
import stat
import subprocess
import sys
import time


def instalar(directorio, config):
    """Crea el lanzador en `directorio` y devuelve el entorno que lo pone primero en el PATH."""
    os.makedirs(directorio, exist_ok=True)
    script = os.path.abspath(__file__)
    if os.name == "nt":
        with open(os.path.join(directorio, "mergiraf.cmd"), "w", encoding="utf-8") as f:
            f.write(f'@"{sys.executable}" "{script}" %*\r\n')
    else:
        ruta = os.path.join(directorio, "mergiraf")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\nexec '{sys.executable}' '{script}' \"$@\"\n")
        os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"PATH": directorio + os.pathsep + os.environ.get("PATH", ""), "HK_MERGIRAF_FALSO": config}


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
    ruta = opcion(args, "-p")
    entradas = [a for a in args[1:4]]
    llamada = {"args": args, "ruta": ruta, "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME"),
               "APPDATA": os.environ.get("APPDATA"), "cwd": os.getcwd(),
               "entradas": [os.path.isfile(e) for e in entradas]}
    with open(conf["log"], "a", encoding="utf-8") as f:
        f.write(json.dumps(llamada) + "\n")
    if conf.get("real"):
        return subprocess.run([conf["real"], *args]).returncode
    time.sleep(conf.get("espera", {}).get(ruta, 0))
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
