"""Prueba de los hooks del orquestador (M7) con entradas simuladas: solo-orquestar.sh y compuerta.sh.

Monta un repo de juguete con un worktree de worker en un directorio temporal y lanza los hooks con bash.
Uso: python evals/coordinacion/prueba_hooks.py   (sale con 1 si algún caso falla)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
SOLO = KIT + "/scripts/orquestador/solo-orquestar.sh"
COMP = KIT + "/scripts/orquestador/compuerta.sh"
fallos = 0
# En Windows, «bash» puede ser el de WSL: se usa el de Git for Windows, junto a git.
BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe")) if os.path.exists(b)), BASH)


def hook(script, datos, cwd, ascii=True):
    r = subprocess.run([BASH, script], input=json.dumps(datos, ensure_ascii=ascii), capture_output=True, text=True,
                       encoding="utf-8", cwd=cwd)
    return r.returncode, r.stderr.strip()


def caso(nombre, esperado, script, datos, cwd, ascii=True):
    global fallos
    code, err = hook(script, datos, cwd, ascii)
    # «niega» solo si es el hook quien niega (exit 2 con su mensaje), no un error de bash.
    obtenido = "permite" if code == 0 else "niega" if code == 2 and err.split(":")[0].split(" ")[0] in ("Compuerta", "Orquestador", "Revisor") else f"error {code}"
    ok = obtenido == esperado
    fallos += not ok
    print(f"{'OK   ' if ok else 'FALLO'} {obtenido:7} {nombre}" + (f"\n        {err.splitlines()[-2] if len(err.splitlines()) > 1 else err}" if err and not ok else ""))


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


tmp = tempfile.mkdtemp(prefix="hk-hooks-")
try:
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, "web"))
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "prueba"); git(repo, "config", "user.email", "prueba@example.com")
    open(os.path.join(repo, "web", "a.js"), "w").write("a\n")
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "inicio")
    base = git(repo, "rev-parse", "HEAD")
    wt = os.path.join(tmp, "wt").replace("\\", "/")
    git(repo, "worktree", "add", "-q", "-b", "worktree-agent-x", wt)
    open(os.path.join(wt, "web", "a.js"), "w").write("b\n")
    open(os.path.join(wt, "web", "b.js"), "w").write("b\n")
    git(wt, "add", "-A"); git(wt, "commit", "-qm", "trabajo")
    wt_vacio = os.path.join(tmp, "wt2").replace("\\", "/")
    git(repo, "worktree", "add", "-q", "-b", "worktree-agent-vacia", wt_vacio)

    def informe(rama="worktree-agent-x", w=wt, ficheros="web/a.js, web/b.js (nuevo)", salida="OK 24\n404", estado="hecho"):
        return (f"Rama: {rama}\nBase: {base} · ok\nWorktree: {w.replace('/', chr(92))}\nEstado: {estado}\n"
                f"Ficheros tocados: {ficheros}\nPreparación: npm ci · 6 s · ok\nComprobación: npm test\n{salida}\n"
                "Pendiente o dudas: nada")

    def handback(msg, aid="a1", tipo="hackathon-kit:worker"):
        return {"hook_event_name": "PreToolUse", "agent_type": tipo, "agent_id": aid,
                "tool_name": "SubagentHandback", "tool_input": {"message": msg}}

    print("== compuerta.sh")
    caso("otro agent_type (revisor)", "permite", COMP, handback("nada", tipo="hackathon-kit:revisor"), repo)
    caso("sesión sin agent_type", "permite", COMP, {"hook_event_name": "SubagentStop", "last_assistant_message": "x"}, repo)
    caso("worker, otra herramienta", "permite", COMP, {"hook_event_name": "PreToolUse", "agent_type": "hackathon-kit:worker",
                                                        "agent_id": "a0", "tool_name": "Bash", "tool_input": {"command": "ls"}}, repo)
    caso("informe completo y cierto (JSON con \u00f3)", "permite", COMP, handback(informe(), "ok1"), repo)
    caso("informe completo y cierto (JSON en UTF-8)", "permite", COMP, handback(informe(), "ok2"), repo, ascii=False)
    caso("SubagentStop tras entregar", "permite", COMP, {"hook_event_name": "SubagentStop", "agent_type": "hackathon-kit:worker",
                                                          "agent_id": "ok1", "stop_hook_active": False, "last_assistant_message": "listo"}, repo)
    caso("falta «Comprobación:»", "niega", COMP, handback(informe().replace("Comprobación: npm test\n", ""), "f1"), repo)
    caso("sin salida de la comprobación", "niega", COMP, handback(informe(salida=""), "f2"), repo)
    caso("rama sin commits", "niega", COMP, handback(informe(rama="worktree-agent-vacia", w=wt_vacio, ficheros="—"), "f3"), repo)
    caso("fichero del diff sin declarar", "niega", COMP, handback(informe(ficheros="web/a.js"), "f4"), repo)
    open(os.path.join(wt, "sucio.txt"), "w").write("x\n")
    caso("worktree sucio", "niega", COMP, handback(informe(), "f5"), repo)
    os.remove(os.path.join(wt, "sucio.txt"))
    caso("bloqueado, sin comprobación", "permite", COMP, handback(informe(estado="bloqueado: falta X", salida=""), "b1"), repo)
    caso("tope: 1.º rechazo", "niega", COMP, handback(informe(salida=""), "t1"), repo)
    caso("tope: 2.º rechazo", "niega", COMP, handback(informe(salida=""), "t1"), repo)
    caso("tope: 3.º deja pasar", "permite", COMP, handback(informe(salida=""), "t1"), repo)
    tr = os.path.join(tmp, "agent-s1.jsonl").replace("\\", "/")
    open(tr, "w").write("{}\n")
    open(tr.replace(".jsonl", ".meta.json"), "w").write('{"agentType":"hackathon-kit:worker"}')
    def parada(aid, activo=False, transcript=tr):
        d = {"hook_event_name": "SubagentStop", "agent_type": "hackathon-kit:worker", "agent_id": aid,
             "stop_hook_active": activo, "last_assistant_message": "He terminado."}
        if transcript:
            d["agent_transcript_path"] = transcript
        return d
    caso("SubagentStop de worker sin handback ni informe", "niega", COMP, parada("s1"), repo)
    caso("SubagentStop con stop_hook_active", "permite", COMP, parada("s1", activo=True), repo)
    caso("SubagentStop de agente interno (sin transcript)", "permite", COMP, parada("i1", transcript=None), repo)
    caso("SubagentStop con transcript inexistente", "permite", COMP, parada("i2", transcript=tmp.replace("\\", "/") + "/no.jsonl"), repo)

    print("== solo-orquestar.sh")
    def bash(cmd, tipo):
        return {"hook_event_name": "PreToolUse", "agent_type": tipo, "tool_name": "Bash", "tool_input": {"command": cmd}}
    def edit(ruta, tipo):
        return {"hook_event_name": "PreToolUse", "agent_type": tipo, "tool_name": "Edit", "tool_input": {"file_path": ruta}}
    R, O = "hackathon-kit:revisor", "hackathon-kit:orquestador"
    caso("sesión normal, Edit", "permite", SOLO, {"tool_name": "Edit", "tool_input": {"file_path": "C:\\p\\a.py"}}, repo)
    caso("worker, Edit", "permite", SOLO, edit("C:\\p\\a.py", "hackathon-kit:worker"), repo)
    caso("orquestador, Edit en .hackathon", "permite", SOLO, edit("C:\\p\\.hackathon\\estado\\B.md", O), repo)
    caso("orquestador, Edit en código", "niega", SOLO, edit("C:\\p\\web\\a.js", O), repo)
    caso("orquestador, git merge", "permite", SOLO, bash("git merge --no-ff worktree-agent-x -m \"add (worker)\"", O), repo)
    caso("orquestador, git push", "permite", SOLO, bash("git pull --ff-only && git push", O), repo)
    caso("orquestador, git push -u origin main", "permite", SOLO, bash("git push -u origin main", O), repo)
    for c in ("git push --force", "git push -f origin main", "git push --force-with-lease", "git push origin +main",
              "git push origin :main", "git push --delete origin x", "git push --mirror"):
        caso(f"orquestador, {c}", "niega", SOLO, bash(c, O), repo)
    caso("revisor, git push", "niega", SOLO, bash("git push", R), repo)
    caso("revisor, Edit en .hackathon", "niega", SOLO, edit("C:\\p\\.hackathon\\estado\\B.md", R), repo)
    caso("revisor, echo >", "niega", SOLO, bash("echo x > web/a.js", R), repo)
    caso("revisor, git worktree add --detach", "permite", SOLO, bash("git worktree add --detach .claude/worktrees/revision-abc12345 abc1234", R), repo)
    caso("revisor, npm ci en su worktree", "permite", SOLO, bash("cd .claude/worktrees/revision-abc12345 && npm ci --prefix web 2>&1 | tail -3", R), repo)
    caso("revisor, git worktree remove", "permite", SOLO, bash("git worktree remove .claude/worktrees/revision-abc12345", R), repo)
    caso("revisor, git worktree remove --force", "niega", SOLO, bash("git worktree remove --force .claude/worktrees/revision-abc12345", R), repo)
    caso("revisor, git diff de la fusión", "permite", SOLO, bash("git diff abc^1 abc --stat", R), repo)
    caso("revisor, git merge", "niega", SOLO, bash("git merge x", R), repo)
    caso("revisor, git checkout", "niega", SOLO, bash("git checkout main", R), repo)
    caso("revisor, git commit", "niega", SOLO, bash("git commit -am x", R), repo)
finally:
    subprocess.run(["git", "worktree", "prune"], cwd=os.path.join(tmp, "repo"), capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{fallos} fallos")
sys.exit(1 if fallos else 0)
