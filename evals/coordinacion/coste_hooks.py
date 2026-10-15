"""Coste por llamada de los hooks del Hackathon OS en este portátil (M8c, criterio 6, parte sin modelo).

Lanza cada hook N veces con una entrada real, como lo haría Claude Code (un bash por llamada, la entrada por stdin),
y da la media en ms frente a un bash vacío. Umbral de ADR-0004: ≤ 50 ms por llamada en Windows.
Uso: python evals/coordinacion/coste_hooks.py [N]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENT = os.path.join(KIT, "evals", "coordinacion", "entradas")
BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe"),
                             os.path.join(os.path.dirname(raiz), "usr", "bin", "bash.exe")) if os.path.exists(b)), BASH)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def mide(script, texto, cwd):
    t = time.perf_counter()
    for _ in range(N):
        subprocess.run([BASH, script], input=texto, capture_output=True, text=True, encoding="utf-8", cwd=cwd)
    return (time.perf_counter() - t) / N * 1000


tmp = tempfile.mkdtemp(prefix="hk-coste-")
try:
    def repo(nombre, activo):
        r = os.path.join(tmp, nombre)
        os.makedirs(os.path.join(r, ".hackathon"))
        subprocess.run(["git", "init", "-q", "-b", "main", r], check=True)
        if activo:
            open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write("activa: sí\n")
        open(os.path.join(r, "a.txt"), "w").write("x\n")
        return r
    activo, apagado = repo("activo", True), repo("apagado", False)
    vacio = os.path.join(tmp, "vacio.sh"); open(vacio, "w").write("exit 0\n")
    write = open(os.path.join(ENT, "orquestador-y-worker", "09-worker-PostToolUse-Write.json"), encoding="utf-8").read()
    bash = open(os.path.join(ENT, "orquestador-y-worker", "14-worker-PostToolUse-Bash.json"), encoding="utf-8").read()
    d = json.loads(open(os.path.join(ENT, "sesion-normal", "09-principal-PostToolUse-Edit.json"), encoding="utf-8").read())
    d["tool_response"] = {"originalFile": "línea de código con «texto»\n" * 7000}   # ~200 KB, como un Edit de un fichero grande
    edit_grande = json.dumps(d, ensure_ascii=False)
    arbol = json.dumps({"hook_event_name": "PostToolBatch", "session_id": "s-coste", "cwd": activo})
    filas = [("bash vacío", vacio, write, activo),
             ("emite.sh, OS apagado", f"{KIT}/scripts/os/emite.sh", write, apagado),
             ("emite.sh, Write", f"{KIT}/scripts/os/emite.sh", write, activo),
             ("emite.sh, Bash con git commit", f"{KIT}/scripts/os/emite.sh", bash, activo),
             (f"emite.sh, Edit con {len(edit_grande.encode()) // 1024} KB de entrada", f"{KIT}/scripts/os/emite.sh", edit_grande, activo),
             ("arbol.sh (git status; sin cambios, no escribe)", f"{KIT}/scripts/os/arbol.sh", arbol, activo)]
    # M8g: reserva.sh es síncrono (PreToolUse de cada Edit/Write): con el OS apagado, sin reservas, con 50 reservas que
    # no coinciden y con una que coincide (la primera vez avisa; las demás, ya avisada en la sesión, no).
    def pre_edit(repo, ruta):
        return json.dumps({"session_id": "s-coste", "cwd": repo, "hook_event_name": "PreToolUse", "tool_name": "Edit",
                           "tool_input": {"file_path": os.path.join(repo, ruta), "old_string": "a", "new_string": "b"}})
    con_res = repo("reservas", True)
    d_os = os.path.join(con_res, ".git", "hackathon", "os")
    os.makedirs(d_os, exist_ok=True)
    hasta = int(time.time()) + 3600
    open(os.path.join(d_os, "reservas.tsv"), "w", newline="\n").write(
        "".join(f"reserva-{i}\tcarpeta{i}/fichero.py\tpersona-a\t{hasta}\t18:55\tcompartida\n" for i in range(50)) +
        f"reserva-x\tweb/\tpersona-a\t{hasta}\t18:55\tcompartida\n")
    filas += [("reserva.sh, OS apagado", f"{KIT}/scripts/os/reserva.sh", pre_edit(apagado, "a.txt"), apagado),
              ("reserva.sh, OS encendido sin reservas.tsv", f"{KIT}/scripts/os/reserva.sh", pre_edit(activo, "a.txt"), activo),
              ("reserva.sh, 51 reservas, ninguna coincide", f"{KIT}/scripts/os/reserva.sh", pre_edit(con_res, "a.txt"), con_res),
              ("reserva.sh, coincide (avisada ya en la sesión)", f"{KIT}/scripts/os/reserva.sh", pre_edit(con_res, "web/a.js"), con_res)]
    print(f"{N} llamadas por fila; bash: {BASH}")
    for nombre, script, texto, cwd in filas:
        print(f"  {mide(script, texto, cwd):6.1f} ms  {nombre}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
