"""Prueba de los hooks del orquestador (M7) con entradas simuladas: solo-orquestar.sh, compuerta.sh y sin-confirmo.sh.

Monta un repo de juguete con un worktree de worker en un directorio temporal y lanza los hooks con bash.
Uso: python evals/coordinacion/prueba_hooks.py   (sale con 1 si algún caso falla)
"""
import glob
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile

for flujo in (sys.stdout, sys.stderr):    # en Windows, con la salida redirigida, cp1252 no sabe escribir «≤» (issue #18)
    if hasattr(flujo, "reconfigure"):
        flujo.reconfigure(encoding="utf-8", errors="replace")

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
SOLO = KIT + "/scripts/orquestador/solo-orquestar.sh"
COMP = KIT + "/scripts/orquestador/compuerta.sh"
fallos = 0
ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}   # los hooks, en el cwd de cada caso
# En Windows, «bash» puede ser el de WSL: se usa el de Git for Windows, junto a git.
BASH = shutil.which("bash")
if os.name == "nt":
    raiz = os.path.dirname(os.path.dirname(shutil.which("git")))
    BASH = next((b for b in (os.path.join(raiz, "bin", "bash.exe"), os.path.join(raiz, "usr", "bin", "bash.exe")) if os.path.exists(b)), BASH)


def hook(script, datos, cwd, ascii=True):
    r = subprocess.run([BASH, script], input=json.dumps(datos, ensure_ascii=ascii), capture_output=True, text=True,
                       encoding="utf-8", cwd=cwd, env=ENV)
    return r.returncode, r.stderr.strip()


def caso(nombre, esperado, script, datos, cwd, ascii=True):
    global fallos
    code, err = hook(script, datos, cwd, ascii)
    # «niega» solo si es el hook quien niega (exit 2 con su mensaje), no un error de bash.
    obtenido = "permite" if code == 0 else "niega" if code == 2 and err.split(":")[0].split(" ")[0] in ("Compuerta", "Orquestador", "Revisor", "Coordinación") else f"error {code}"
    ok = obtenido == esperado
    fallos += not ok
    print(f"{'OK   ' if ok else 'FALLO'} {obtenido:7} {nombre}" + (f"\n        {err.splitlines()[-2] if len(err.splitlines()) > 1 else err}" if err and not ok else ""))


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


# --- M8c: Hackathon OS (emite.sh, arbol.sh, línea de la compuerta y hkos/normaliza.py) ---
EMITE, ARBOL = KIT + "/scripts/os/emite.sh", KIT + "/scripts/os/arbol.sh"
ENTRADAS = os.path.join(KIT, "evals", "coordinacion", "entradas")
CAMPOS = {  # lista blanca de api.md §1, por tipo de línea
    "hook": {"v", "ts", "persona", "tipo", "session_id", "cwd", "agent_id", "agent_type", "source", "tool_name", "tool_use_id",
             "ruta", "git", "subagent_type", "id", "base", "transcript_path", "veredicto", "fusion", "truncado"},
    "arbol": {"v", "ts", "persona", "tipo", "session_id", "cwd", "agent_id", "agent_type", "base", "porcelain", "diff", "truncado", "contratos"},
    "compuerta": {"v", "ts", "persona", "tipo", "session_id", "cwd", "agent_id", "agent_type", "resultado", "tope", "motivos", "truncado"},
    "prueba": {"v", "ts", "persona", "tipo", "session_id", "cwd", "agent_id", "agent_type", "comando_sha", "resultado", "codigo", "truncado"},
}


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(f"{'OK   ' if ok else 'FALLO'} {nombre}" + (f"\n        {detalle}" if detalle and not ok else ""))


def ejecutable(ruta):
    """Los gh falsos se lanzan como programa: en macOS y Linux necesitan el permiso de ejecución (en Windows, no)."""
    os.chmod(ruta, 0o755)


def lanza(script, texto, cwd, env=None):
    return subprocess.run([BASH, script], input=texto, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env or ENV)


def lineas(repo_dir):
    """{sesión: [líneas]} de los JSONL del OS en ese repo."""
    d = os.path.join(repo_dir, ".git", "hackathon", "os", "eventos")
    if not os.path.isdir(d):
        return {}
    return {f[:-6]: open(os.path.join(d, f), encoding="utf-8").read().splitlines() for f in os.listdir(d) if f.endswith(".jsonl")}


def valida(nombre, texto):
    """json.loads y lista blanca de una línea cruda; da el dict o None."""
    try:
        d = json.loads(texto)
    except ValueError as e:
        comprueba(nombre, False, f"no es JSON: {e}: {texto[:120]}")
        return None
    clase = d.get("tipo") if d.get("tipo") in ("arbol", "compuerta", "prueba") else "hook"
    sobra = set(d) - CAMPOS[clase]
    if sobra:
        comprueba(nombre, False, f"campos fuera de la lista blanca: {sorted(sobra)}")
        return None
    return d


def repo_os(base, nombre, os_md=None, codificacion="utf-8", remoto=False):
    r = os.path.join(base, nombre)
    os.makedirs(os.path.join(r, ".hackathon"))
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.name", "prueba"); git(r, "config", "user.email", "prueba@example.com")
    if os_md is not None:
        open(os.path.join(r, ".hackathon", "os.md"), "w", encoding=codificacion, newline="").write(os_md)
    if remoto:
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", r + ".git"], check=True)
        open(os.path.join(r, "a.txt"), "w").write("uno\n")
        git(r, "add", "-A"); git(r, "commit", "-qm", "inicio")   # os.md va versionado (api.md §0)
        git(r, "remote", "add", "origin", r + ".git"); git(r, "push", "-q", "-u", "origin", "main")
    return r


def scripts_del_os(d, hooks):
    """Los scripts del OS que Claude Code lanzaría con esta entrada, según los matchers de hooks.json."""
    ev, salida = d["hook_event_name"], []
    for g in hooks.get(ev, []):
        m = g.get("matcher")
        clave = d.get("tool_name") if ev in ("PreToolUse", "PostToolUse", "PostToolUseFailure") else d.get("source")
        if m and not (clave and re.fullmatch(m, clave)):
            continue
        salida += [KIT + "/scripts/os/" + s for h in g["hooks"] for s in re.findall(r"scripts/os/(\w+\.sh)", h["command"])]
    return salida


def prueba_os(tmp, repo, informe, handback):
    global fallos
    sys.path.insert(0, os.path.join(KIT, "hkos"))
    from normaliza import Contexto, Normalizador, normalizar_fichero
    hooks = json.load(open(os.path.join(KIT, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]
    reales = {os.path.relpath(f, ENTRADAS).replace("\\", "/"): open(f, encoding="utf-8").read()
              for f in sorted(glob.glob(os.path.join(ENTRADAS, "*", "*.json")))}
    base = os.path.join(tmp, "os"); os.makedirs(base)

    # gh y curl falsos: si un hook del OS los llama, dejan rastro (criterio 1: sin red).
    falsos, rastro = os.path.join(base, "falsos"), os.path.join(base, "rastro").replace("\\", "/")
    os.makedirs(falsos)
    for p in ("gh", "curl"):
        open(os.path.join(falsos, p), "w", newline="\n").write(f"#!/bin/sh\necho {p} >> '{rastro}'\n")
        ejecutable(os.path.join(falsos, p))
    env_falsos = dict(ENV, PATH=falsos + os.pathsep + ENV.get("PATH", ""))

    print("\n== Hackathon OS: apagado (criterio 1)")
    comprueba("los hooks de antes no han creado nada del OS en el repo de prueba",
              not os.path.exists(os.path.join(repo, ".git", "hackathon", "os")))
    variantes = [("sin os.md", None, "utf-8"), ("«activa: no»", "activa: no\n", "utf-8"),
                 ("«activa: no» en UTF-16", "activa: no\r\n", "utf-16"), ("sin línea activa", "# Hackathon OS\nrelay: x\n", "utf-8")]
    for i, (nombre, contenido, cod) in enumerate(variantes):
        r = repo_os(base, f"apagado{i}", contenido, cod, remoto=True)
        open(os.path.join(r, "nuevo.txt"), "w").write("x\n")
        for texto in reales.values():
            lanza(EMITE, texto, r, env_falsos)
        lanza(ARBOL, json.dumps({"hook_event_name": "PostToolBatch", "session_id": "s-apagado", "cwd": r}), r, env_falsos)
        comprueba(f"{nombre}: ni una escritura en .git/hackathon", not os.path.exists(os.path.join(r, ".git", "hackathon")))
    comprueba("sin red: ningún hook del OS ha llamado a gh ni a curl", not os.path.exists(rastro))
    medida = subprocess.run([BASH, "-c", f"cd '{base}/apagado0' && source '{KIT}/scripts/os/comun.sh' && s=$EPOCHREALTIME; "
                             "for i in {1..100}; do os_activo; done; e=$EPOCHREALTIME; echo $(( (${e/./}-${s/./}) / 100 ))"],
                            capture_output=True, text=True)
    us = int(medida.stdout.strip() or 10**9)
    comprueba(f"os_activo sin os.md: {us / 1000:.2f} ms por llamada (< 20 ms)", us < 20000)

    print("\n== Hackathon OS: activado")
    for i, (nombre, contenido, cod) in enumerate([("«activa: sí» con comentario", "activa: sí   # prueba\n", "utf-8"),
                                                  ("«activa: si» con CRLF", "# OS\r\nactiva: si\r\n", "utf-8"),
                                                  ("con BOM", "activa: yes\n", "utf-8-sig"),
                                                  ("en UTF-16", "activa: sí\r\n", "utf-16")]):
        r = repo_os(base, f"activo{i}", contenido, cod)
        lanza(EMITE, reales["sesion-normal/01-principal-SessionStart.json"], r, env_falsos)
        comprueba(f"{nombre}: escribe la línea", sum(map(len, lineas(r).values())) == 1)
    comprueba("activado tampoco llama a gh ni a curl", not os.path.exists(rastro))

    print("\n== Entradas reales por los hooks del OS y normaliza.py (K-34)")
    r = repo_os(base, "reales", "activa: sí\n")
    for texto in reales.values():
        for s in scripts_del_os(json.loads(texto), hooks):
            lanza(s, texto, r)
    prompts = {}
    for texto in reales.values():
        d = json.loads(texto)
        if d["hook_event_name"] == "PreToolUse" and d.get("tool_name") == "Agent":
            prompts[d["session_id"]] = d["tool_input"]["prompt"]
    def primera(ruta):
        m = re.search(r"/([0-9a-f-]{36})/subagents/agent-[0-9a-f]+\.jsonl$", ruta)
        return json.dumps({"type": "user", "message": {"role": "user", "content": prompts[m.group(1)]}}) if m else None
    def raices(cwd):
        c = cwd.replace("\\", "/"); i = c.lower().find("/repo")
        return c, (c[:i + 5] if i >= 0 else c)
    papeles = {"juguete:orq": "orquestador", "juguete:orqlibre": "orquestador", "juguete:worker": "worker", "juguete:workerlibre": "worker"}
    obtenidos, n_lineas = {}, 0
    for sesion, ls in lineas(r).items():
        for i, l in enumerate(ls, 1):
            n_lineas += valida(f"línea {sesion[:8]}-{i}", l) is not None
        nz = Normalizador(Contexto(persona="persona-a", papeles=papeles, raices=raices, primera_linea=primera))
        for e in normalizar_fichero(os.path.join(r, ".git", "hackathon", "os", "eventos", sesion + ".jsonl"), normalizador=nz):
            obtenidos[e["id"]] = e
    print(f"      {n_lineas} líneas crudas válidas y en la lista blanca; {len(obtenidos)} eventos normalizados")
    esperados = {c["evento"]["id"]: c for c in json.load(open(os.path.join(ENTRADAS, "normalizadas.json"), encoding="utf-8"))["casos"] if c["evento"]}
    comprueba("los mismos eventos que normalizadas.json (ni de más ni de menos)", set(obtenidos) == set(esperados),
              f"de más: {sorted(set(obtenidos) - set(esperados))}; faltan: {sorted(set(esperados) - set(obtenidos))}")
    for i, c in esperados.items():
        o = dict(obtenidos.get(i, {})); e = dict(c["evento"])
        ts_ok = bool(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", o.pop("ts", "")))
        e.pop("ts")
        if o != e or not ts_ok:
            comprueba(f"evento de {c['entrada']}", False, f"obtenido {o}\n        esperado {e}")
    comprueba("cada evento coincide con su entrada (salvo ts, que es el de emite.sh)", True)

    print("\n== Recorte de «git» a 200 caracteres (criterio 7)")
    r = repo_os(base, "recorte", "activa: sí\n")
    plantilla = json.loads(reales["orquestador-y-worker/14-worker-PostToolUse-Bash.json"])
    casos = 0
    for nombre, especial, ascii in (("\\\"", '"', True), ("\\\\", "\\", True), ("\\u00f3", "ó", True), ("ó en UTF-8", "ó", False)):
        for k in range(185, 202):
            cmd = "git commit -m " + "a" * (k - 14) + especial * 3 + "b" * 30
            d = dict(plantilla, session_id=f"s-recorte-{casos}", tool_input={"command": cmd, "description": "x"})
            lanza(EMITE, json.dumps(d, ensure_ascii=ascii), r)
            casos += 1
            ls = lineas(r).get(d["session_id"], [])
            linea = valida(f"recorte {nombre} en {k}", ls[0]) if len(ls) == 1 else None
            ok = linea is not None and cmd.startswith(linea.get("git", "-")) and len(json.dumps(linea["git"], ensure_ascii=ascii)) - 2 <= 200
            if not ok:
                comprueba(f"recorte {nombre} con el especial en {k}", False, f"líneas: {ls}")
    comprueba(f"{casos} recortes alrededor de \\\", \\\\, \\u00f3 y ó: JSON válido y prefijo del comando", True)

    print("\n== Entradas grandes (un Edit con el fichero entero en tool_response, un Write de 200 KB)")
    r = repo_os(base, "grandes", "activa: sí\n")
    d = json.loads(reales["sesion-normal/09-principal-PostToolUse-Edit.json"])
    d["tool_response"] = {"originalFile": "línea de código con «texto» y \"comillas\"\n" * 6000}
    d["session_id"] = "s-grande-edit"
    lanza(EMITE, json.dumps(d, ensure_ascii=False), r)
    w = json.loads(reales["orquestador-y-worker/09-worker-PostToolUse-Write.json"])
    w["tool_input"]["content"] = "x = 1\n" * 35000
    w["session_id"] = "s-grande-write"
    lanza(EMITE, json.dumps(w), r)
    for sesion, entrada in (("s-grande-edit", d), ("s-grande-write", w)):
        ls = lineas(r).get(sesion, [])
        l = valida(f"entrada grande {sesion}", ls[0]) if len(ls) == 1 else None
        comprueba(f"{sesion}: ruta y tool_use_id aunque la entrada pase de 200 KB",
                  l is not None and l.get("ruta") == entrada["tool_input"]["file_path"] and l.get("tool_use_id") == entrada["tool_use_id"], str(ls)[:300])

    print("\n== Escrituras simultáneas en el mismo JSONL (criterio 7, tope de 1.000 bytes)")
    # emite.sh y arbol.sh reales, mezclados, con líneas cerca del tope. En Windows, el printf de bash escribe en
    # trozos de 1 KB (api.md §1): por debajo, las líneas de procesos simultáneos no se han mezclado en las medidas.
    r = repo_os(base, "simultaneas", "activa: sí\n", remoto=True)
    for i in range(60):
        open(os.path.join(r, f"fichero-con-un-nombre-bastante-largo-{i:03}.txt"), "w").write("x")
    largo = "C:\\" + "\\".join(["carpeta-larga"] * 25)
    escritura = dict(json.loads(reales["orquestador-y-worker/09-worker-PostToolUse-Write.json"]), session_id="s-simultaneas",
                     cwd=largo, tool_input={"file_path": largo + "\\fichero.txt", "content": "x"})
    rondas, por_ronda = int(os.environ.get("HK_RONDAS", 50)), 20
    for ronda in range(rondas):
        trabajos = []
        for i in range(por_ronda):
            if i % 2:   # cada arbol con su agent_id, para que «sin cambios, no repite» no lo frene
                trabajos.append((ARBOL, json.dumps({"hook_event_name": "PostToolBatch", "session_id": "s-simultaneas", "cwd": r,
                                                    "agent_id": f"w{ronda}-{i}"})))
            else:
                trabajos.append((EMITE, json.dumps(escritura)))
        procs = [subprocess.Popen([BASH, s], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=r, env=ENV)
                 for s, _ in trabajos]
        for p, (_, texto) in zip(procs, trabajos):   # todos arrancados y esperando la entrada: se la damos casi a la vez
            p.stdin.write(texto.encode()); p.stdin.close()
        for p in procs:
            p.wait()
    ls = lineas(r).get("s-simultaneas", [])
    tams = [len(l.encode()) + 1 for l in ls]
    validas = [valida("línea simultánea", l) for l in ls]
    tipos = [v["tipo"] for v in validas if v]
    comprueba(f"{rondas}×{por_ronda} emite.sh y arbol.sh a la vez: {len(ls)} líneas, {len(tipos)} enteras y válidas "
              f"({tipos.count('PostToolUse')} de emite, {tipos.count('arbol')} de arbol; de {min(tams, default=0)} a {max(tams, default=0)} bytes)",
              len(ls) == len(tipos) == rondas * por_ronda and tipos.count("arbol") == tipos.count("PostToolUse")
              and 900 < max(tams) <= 1000 and all(v.get("truncado") for v in validas if v and v["tipo"] == "arbol"))
    escritura["cwd"] = largo * 3
    lanza(EMITE, json.dumps(escritura), r)
    ultima = lineas(r)["s-simultaneas"][-1]
    comprueba("una línea que no cabe en 1.000 bytes se reduce al sobre mínimo con «truncado»",
              len(ultima.encode()) + 1 <= 1000 and (valida("línea reducida", ultima) or {}).get("truncado") is True
              and "cwd" not in json.loads(ultima))

    print("\n== Líneas rotas en un JSONL (normaliza.py)")
    sesion = "be342bee-6649-43f3-b3b9-1a1f96cd32df"
    buenas = open(os.path.join(base, "reales", ".git", "hackathon", "os", "eventos", sesion + ".jsonl"), "rb").read().splitlines(keepends=True)
    rota = os.path.join(base, "rota.jsonl")
    with open(rota, "wb") as f:   # la línea 2 (PreToolUse de Edit) partida en dos, como si dos escrituras se hubieran mezclado
        f.write(buenas[0] + buenas[1][:60] + b"\n" + buenas[1][60:] + b"".join(buenas[2:]))
    nz = Normalizador(Contexto(persona="persona-a", raices=raices))
    e = normalizar_fichero(rota, normalizador=nz)
    comprueba("salta las dos mitades, sigue leyendo, conserva el número de línea real y las cuenta",
              [(x["tipo"], x["id"].rsplit("-", 1)[1]) for x in e] == [("sesion.inicio", "1"), ("edicion", "4"), ("sesion.fin", "7")]
              and nz.lineas_corruptas == 2, f"{[(x['tipo'], x['id']) for x in e]}, rotas: {nz.lineas_corruptas}")

    print("\n== arbol.sh (criterio 4)")
    r = repo_os(base, "arbol", "activa: sí\n", remoto=True)
    def arbol(agente=None):
        d = {"hook_event_name": "PostToolBatch", "session_id": "s-arbol", "cwd": r}
        if agente:
            d["agent_id"] = agente
        lanza(ARBOL, json.dumps(d), r)
        return lineas(r).get("s-arbol", [])
    subprocess.run([BASH, "-c", "sed -i.bak 's/uno/dos/' a.txt && rm a.txt.bak && echo nuevo > generado.txt"], cwd=r, check=True)
    ls = arbol()
    l1 = valida("arbol", ls[-1]) if ls else None
    comprueba("un fichero cambiado solo por Bash (sed) y uno generado aparecen en el arbol",
              l1 is not None and " M a.txt" in l1["porcelain"] and "?? generado.txt" in l1["porcelain"] and l1.get("base") == git(r, "rev-parse", "origin/main"),
              str(l1))
    comprueba("sin cambios, no repite la línea", len(arbol()) == 1)
    comprueba("otro actor (agent_id) con el mismo árbol sí escribe la suya", len(arbol("w1")) == 2)
    git(r, "add", "a.txt", "generado.txt"); git(r, "commit", "-qm", "T07 · cambio")
    ls = arbol()
    l2 = valida("arbol tras commit", ls[-1])
    comprueba("tras un commit, el cambio está en «diff» y no en «porcelain»",
              len(ls) == 3 and l2 is not None and l2["porcelain"] == [] and sorted(l2["diff"]) == ["a.txt", "generado.txt"], str(l2))
    for i in range(300):
        open(os.path.join(r, f"fichero-con-un-nombre-bastante-largo-{i:03}.txt"), "w").write("x")
    ls = arbol()
    l3 = valida("arbol recortado", ls[-1])
    comprueba("con 300 ficheros nuevos, la lista se recorta: «truncado» y como mucho 1.000 bytes",
              l3 is not None and l3.get("truncado") is True and len(ls[-1].encode()) + 1 <= 1000 and len(l3.get("porcelain", [])) >= 3, str(l3))
    nz = Normalizador(Contexto(persona="persona-a", raices=lambda c: (c, c)))
    e = nz.eventos(l1, 1)
    comprueba("normaliza.py: el arbol da rutas de porcelain y diff", len(e) == 1 and e[0]["rutas"] == ["a.txt", "generado.txt"], str(e))

    print("\n== arbol.sh: bloques de docs/contratos.md tocados (M8g, nivel 3)")
    rc = repo_os(base, "arbol-contratos", "activa: sí\n", remoto=True)
    os.makedirs(os.path.join(rc, "docs"), exist_ok=True)
    texto = ("# Contratos\n\n## motor → web: ficha\n\nVive en: motor/api.py\n\n| a | b |\n\n"
             "```json\n## no es un bloque\n```\n\n## Datos de entrada\n\nVive en: datos/\n\nx\n")
    open(os.path.join(rc, "docs", "contratos.md"), "w", encoding="utf-8", newline="\n").write(texto)
    git(rc, "add", "-A"); git(rc, "commit", "-qm", "contratos"); git(rc, "push", "-q", "origin", "HEAD:main")
    def arbol_c():
        lanza(ARBOL, json.dumps({"hook_event_name": "Stop", "session_id": "s-con", "cwd": rc}), rc)
        ls = lineas(rc).get("s-con", [])
        return valida("arbol con contratos", ls[-1]) if ls else None, len(ls)
    open(os.path.join(rc, "docs", "contratos.md"), "w", encoding="utf-8", newline="\n").write(texto.replace("| a | b |", "| a | b | c |"))
    l, n1 = arbol_c()
    comprueba("cambiar una fila de un bloque: «contratos» con su título", l is not None and l.get("contratos") == ["motor → web: ficha"], str(l))
    open(os.path.join(rc, "docs", "contratos.md"), "w", encoding="utf-8", newline="\n").write(
        texto.replace("| a | b |", "| a | b | c |").replace("\nx\n", "\ny\n"))
    l, n2 = arbol_c()
    comprueba("tocar otro bloque del fichero ya cambiado es un arbol nuevo, con los dos títulos",
              n2 == n1 + 1 and l.get("contratos") == ["motor → web: ficha", "Datos de entrada"], str(l))
    nz = Normalizador(Contexto(persona="persona-a", raices=lambda c: (c, c)))
    e = nz.eventos(l, 1)
    comprueba("normaliza.py: datos.contratos en el arbol", e[0].get("datos", {}).get("contratos") == ["motor → web: ficha", "Datos de entrada"], str(e))
    open(os.path.join(rc, "otro.txt"), "w").write("x")
    git(rc, "checkout", "--", "docs/contratos.md")
    l, _ = arbol_c()
    comprueba("sin cambios en contratos.md, el arbol no lleva «contratos»", l is not None and "contratos" not in l, str(l))

    print("\n== compuerta.sh con el OS activo (K-33)")
    open(os.path.join(repo, ".hackathon", "os.md") if os.path.isdir(os.path.join(repo, ".hackathon")) else
         (os.makedirs(os.path.join(repo, ".hackathon")) or os.path.join(repo, ".hackathon", "os.md")), "w", encoding="utf-8").write("activa: sí\n")
    def entrega(msg, aid):
        return dict(handback(msg, aid), session_id="s-compuerta", cwd=repo)
    caso("OS activo: informe cierto", "permite", COMP, entrega(informe(), "os1"), repo)
    caso("OS activo: sin salida de la comprobación", "niega", COMP, entrega(informe(salida=""), "os2"), repo)
    for n, esperado in ((1, "niega"), (2, "niega"), (3, "permite")):
        caso(f"OS activo: tope, intento {n}", esperado, COMP, entrega(informe(salida=""), "os3"), repo)
    ls = [valida("línea de la compuerta", l) for l in lineas(repo).get("s-compuerta", [])]
    resumen = [(l["agent_id"], l["resultado"], l.get("tope", False), len(l["motivos"])) for l in ls if l]
    comprueba("una línea por decisión: ok, ko con motivos, y el tercer intento ko con «tope»",
              resumen == [("os1", "ok", False, 0), ("os2", "ko", False, 1), ("os3", "ko", False, 1), ("os3", "ko", False, 1), ("os3", "ko", True, 1)],
              str(resumen))
    nz = Normalizador(Contexto(persona="persona-a", raices=lambda c: (c, c)))
    e = [x for l in ls for x in nz.eventos(l, 1)]
    comprueba("normaliza.py: compuerta.ok/ko con motivos y datos.tope",
              [x["tipo"] for x in e] == ["compuerta.ok"] + ["compuerta.ko"] * 4 and e[-1]["datos"].get("tope") is True and e[0]["fuente"] == "compuerta")
    os.remove(os.path.join(repo, ".hackathon", "os.md"))


def cksum(datos):
    """El cksum de POSIX (CRC-32 con el polinomio 0x04C11DB7 y la longitud detrás), para comprobar la fórmula del puerto."""
    tabla = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) if c & 0x80000000 else (c << 1)
        tabla.append(c & 0xFFFFFFFF)
    crc = 0
    for b in datos:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ tabla[((crc >> 24) ^ b) & 0xFF]
    n = len(datos)
    while n:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ tabla[((crc >> 24) ^ (n & 0xFF)) & 0xFF]
        n >>= 8
    return ~crc & 0xFFFFFFFF


def prueba_prueba(tmp):
    """M9a, K-96: prueba.sh (api.md §1) con la forma real de las entradas del Paso 0 (entradas/m9a-bash/)."""
    sys.path.insert(0, os.path.join(KIT, "hkos"))
    from esquema import Esquema
    from normaliza import Contexto, Normalizador, normalizar_fichero
    from servicios import huella_prueba
    print("\n== prueba.sh: el resultado de la Prueba de una conexión (M9a, K-96)")
    PRUEBA = KIT + "/scripts/os/prueba.sh"
    hooks = json.load(open(os.path.join(KIT, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]
    pasa = json.load(open(os.path.join(ENTRADAS, "m9a-bash", "01-principal-PostToolUse-Bash.json"), encoding="utf-8"))
    falla = json.load(open(os.path.join(ENTRADAS, "m9a-bash", "02-principal-PostToolUseFailure-Bash.json"), encoding="utf-8"))
    comprueba("hooks.json lanza prueba.sh en PostToolUse y PostToolUseFailure de Bash",
              PRUEBA in scripts_del_os(pasa, hooks) and PRUEBA in scripts_del_os(falla, hooks))
    pruebas = ["uv run pytest tests/test_web_api.py", 'uv run pytest -k "motor and web"', "pytest -q | tee x.log"]
    servicios_md = ("# Servicios\n\n## Servicios\n| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |\n|---|---|---|---|---|---|\n"
                    "| api | api/ | 8000 | — | /salud | — |\n\n## Conexiones\n| De | A | Contrato | Prueba |\n|---|---|---|---|\n"
                    f"| web | api | web → api | `{pruebas[0]}` |\n| motor | web | motor → web | `{pruebas[1]}` |\n"
                    "| web | motor | x | `pytest -q \\| tee x.log` |\n| web | api | sin prueba | — |\n")
    base = os.path.join(tmp, "prueba-m9a"); os.makedirs(base)

    def montar(nombre, os_md, con_servicios=True):
        r = repo_os(base, nombre, os_md)
        if con_servicios:
            open(os.path.join(r, ".hackathon", "servicios.md"), "w", encoding="utf-8", newline="\n").write(servicios_md)
        return r

    def lanzar(r, entrada, comando, sid, **cambios):
        d = dict(entrada, session_id=sid, cwd=r, tool_input=dict(entrada["tool_input"], command=comando), **cambios)
        lanza(PRUEBA, json.dumps(d), r)
        return [valida(f"línea de prueba.sh ({sid})", l) for l in lineas(r).get(sid, [])]

    r = montar("activa", "activa: sí\nweb_nueva: sí   # M9a\n")
    ls = lanzar(r, pasa, pruebas[0], "p1")
    comprueba("PostToolUse con la Prueba exacta: una línea «pasa» con su huella y sin el comando",
              len(ls) == 1 and ls[0] and ls[0]["resultado"] == "pasa" and ls[0]["comando_sha"] == huella_prueba(pruebas[0])
              and "codigo" not in ls[0] and pruebas[0] not in json.dumps(ls[0]))
    ls = lanzar(r, falla, "  " + pruebas[1] + " ", "p2")
    comprueba("PostToolUseFailure (comillas dentro, espacios a los lados): «falla» con codigo 3",
              len(ls) == 1 and ls[0] and ls[0]["resultado"] == "falla" and ls[0].get("codigo") == 3
              and ls[0]["comando_sha"] == huella_prueba(pruebas[1]))
    ls = lanzar(r, pasa, pruebas[2], "p3")
    comprueba("una Prueba con «\\|» en la tabla coincide con el comando con «|»",
              len(ls) == 1 and ls[0] and ls[0]["comando_sha"] == huella_prueba(pruebas[2]))
    comprueba("otro comando, una Prueba a medias o «—»: nada",
              lanzar(r, pasa, "echo pasa", "p4") == [] and lanzar(r, pasa, "uv run pytest", "p5") == []
              and lanzar(r, pasa, "—", "p6") == [])
    comprueba("PostToolUseFailure con is_interrupt: nada", lanzar(r, falla, pruebas[0], "p7", is_interrupt=True) == [])
    # Fabricada (issue #2, hallazgo 8): en segundo plano, PostToolUse llega al arrancar, no al terminar la Prueba.
    def fondo(entrada, valor, tarea="b1"):
        return dict(entrada, tool_input=dict(entrada["tool_input"], run_in_background=valor),
                    tool_response={"stdout": "", "stderr": "", "interrupted": False,
                                   **({"backgroundTaskId": tarea} if tarea else {})})
    comprueba("Bash con run_in_background: true (PostToolUse y PostToolUseFailure): nada",
              lanzar(r, fondo(pasa, True), pruebas[0], "p10") == [] and lanzar(r, fondo(falla, True), pruebas[0], "p11") == [])
    comprueba("run_in_background: false (sin backgroundTaskId) sigue dando «pasa»",
              [l["resultado"] for l in lanzar(r, fondo(pasa, False, None), pruebas[0], "p12") if l] == ["pasa"])

    # Issue #15 (hallazgos 5 y 13), entradas fabricadas a partir de m9a-bash/01. El texto JSON tal cual, sin dumps.
    def crudo(r, d, sid, cambia=lambda t: t, **dumps):
        d = dict(d, session_id=sid, cwd=r, tool_input=dict(d["tool_input"], command=pruebas[0]))
        lanza(PRUEBA, cambia(json.dumps(d, **dumps)), r)
        return [l and l["resultado"] for l in (valida(f"línea de prueba.sh ({sid})", x) for x in lineas(r).get(sid, []))]
    ctrl_b = dict(pasa, tool_response=dict(pasa["tool_response"], backgroundTaskId="bk3x9"))
    comprueba("Ctrl+B: sin run_in_background y con tool_response.backgroundTaskId: nada",
              crudo(r, ctrl_b, "b1") == [] and crudo(r, ctrl_b, "b2", indent=1) == []
              and crudo(r, dict(falla, tool_response={"backgroundTaskId": "bk4"}), "b3") == [])
    grande = dict(pasa, tool_response={"stdout": "línea larga de salida\n" * 1200, "backgroundTaskId": "bk5"})
    comprueba("Ctrl+B con un stdout de más de 16 KB delante de backgroundTaskId: nada", crudo(r, grande, "b4") == [])
    comprueba("backgroundTaskId vacío o null, o dentro del texto de stdout: sigue dando «pasa»",
              crudo(r, dict(pasa, tool_response=dict(pasa["tool_response"], backgroundTaskId=None)), "b5") == ["pasa"]
              and crudo(r, dict(pasa, tool_response=dict(pasa["tool_response"], backgroundTaskId="")), "b6") == ["pasa"]
              and crudo(r, dict(pasa, tool_response={"stdout": '{"backgroundTaskId": "b1"}'}), "b7") == ["pasa"])
    comprueba("run_in_background como la cadena \"true\": nada",
              crudo(r, fondo(pasa, "true", None), "b8") == [])
    comprueba("la clave con escapes (\"run\\u005fin_background\": true, también \"\\u0072un…\"): nada",
              crudo(r, fondo(pasa, True, None), "b9", lambda t: t.replace('"run_in_background"', '"run\\u005fin_background"')) == []
              and crudo(r, fondo(pasa, True, None), "b10", lambda t: t.replace('"run_in_background"', '"\\u0072un_in_background"')) == []
              and crudo(r, fondo(pasa, "true", None), "b11", lambda t: t.replace('"true"', '"\\u0074rue"')) == [])
    comprueba("run_in_background: true con saltos de línea entre clave y valor: nada",
              crudo(r, fondo(pasa, True, None), "b12", lambda t: t.replace('"run_in_background": true', '"run_in_background"\n :\n true')) == [])
    comprueba("run_in_background: true fuera de tool_input (en otro objeto o en tool_response): sigue dando «pasa»",
              crudo(r, dict(pasa, otro={"run_in_background": True}), "b13") == ["pasa"]
              and crudo(r, dict(pasa, tool_response=dict(pasa["tool_response"], run_in_background=True)), "b14") == ["pasa"]
              and crudo(r, dict(pasa, tool_input=dict(pasa["tool_input"], extra={"run_in_background": True})), "b15") == ["pasa"])
    comprueba("run_in_background dentro del texto de description: sigue dando «pasa»",
              crudo(r, dict(pasa, tool_input=dict(pasa["tool_input"], description='{"run_in_background": true}')), "b16") == ["pasa"])

    # Issue #23 (hallazgo 19): tool_input que no es un objeto, y claves repetidas (vale la última, como JSON.parse).
    def tal_cual(r, d, sid, cambia=lambda t: t):
        lanza(PRUEBA, cambia(json.dumps(dict(d, session_id=sid, cwd=r))), r)
        return [l and l["resultado"] for l in (valida(f"línea de prueba.sh ({sid})", x) for x in lineas(r).get(sid, []))]
    ti = dict(pasa["tool_input"], command=pruebas[0])
    comprueba("tool_input que no es un objeto (una lista con el objeto dentro, en segundo plano o no): nada",
              tal_cual(r, dict(pasa, tool_input=[dict(ti, run_in_background=True)]), "c1") == []
              and tal_cual(r, dict(pasa, tool_input=[ti]), "c2") == []
              and tal_cual(r, dict(falla, tool_input=[ti]), "c3") == [])
    dos = lambda a, b: lambda t: t.replace(f'"run_in_background": {a}', f'"run_in_background": {a}, "run_in_background": {b}')
    comprueba("run_in_background repetida: vale la última (true y después false da «pasa»; false y después true, nada)",
              tal_cual(r, dict(pasa, tool_input=dict(ti, run_in_background=True)), "c4", dos("true", "false")) == ["pasa"]
              and tal_cual(r, dict(pasa, tool_input=dict(ti, run_in_background=False)), "c5", dos("false", "true")) == [])
    comprueba("command repetida: cuenta la última (la Prueba y después otro comando: nada)",
              tal_cual(r, dict(pasa, tool_input=ti), "c6", lambda t: t.replace(
                  json.dumps({"command": pruebas[0]})[1:-1], json.dumps({"command": pruebas[0]})[1:-1] + ', "command": "echo otro"')) == [])
    comprueba("backgroundTaskId repetida: vale la última (\"bk\" y después null da «pasa»)",
              tal_cual(r, dict(pasa, tool_input=ti, tool_response=dict(pasa["tool_response"], backgroundTaskId="bk")), "c7",
                       lambda t: t.replace('"backgroundTaskId": "bk"', '"backgroundTaskId": "bk", "backgroundTaskId": null')) == ["pasa"])
    otro_ti = lambda b: lambda t: t.replace('"tool_response":', '"tool_input": ' + json.dumps(b) + ', "tool_response":', 1)
    comprueba("tool_input repetido entero: vale el último (en segundo plano y después no, «pasa»; al revés, nada)",
              tal_cual(r, dict(pasa, tool_input=dict(ti, run_in_background=True)), "c8", otro_ti(ti)) == ["pasa"]
              and tal_cual(r, dict(pasa, tool_input=ti), "c9", otro_ti(dict(ti, run_in_background=True))) == []
              and tal_cual(r, dict(pasa, tool_input=ti), "c10", otro_ti([ti])) == [])
    comprueba("otra herramienta: nada", lanzar(r, pasa, pruebas[0], "p8", tool_name="PowerShell") == [])
    sin_codigo = lanzar(r, falla, pruebas[0], "p9", error="Command failed")
    comprueba("PostToolUseFailure sin «Exit code N»: «falla» sin codigo",
              len(sin_codigo) == 1 and sin_codigo[0] and "codigo" not in sin_codigo[0])

    nz = Normalizador(Contexto(persona="persona-a", raices=lambda cwd: (cwd, cwd)))
    eventos = [e for sid in ("p1", "p2") for e in normalizar_fichero(
        os.path.join(r, ".git", "hackathon", "os", "eventos", sid + ".jsonl"), normalizador=nz)]
    esquema = Esquema("eventos.schema.json")
    comprueba("normaliza.py: eventos `prueba` (fuente hook) que validan contra eventos.schema.json",
              [(e["tipo"], e["fuente"], e["datos"]["resultado"]) for e in eventos] == [("prueba", "hook", "pasa"), ("prueba", "hook", "falla")]
              and eventos[1]["datos"].get("codigo") == 3 and all(esquema.error(e) is None for e in eventos),
              json.dumps(eventos, ensure_ascii=False)[:300])

    for nombre, os_md, con in (("sin web_nueva", "activa: sí\n", True), ("web_nueva: no", "activa: sí\nweb_nueva: no\n", True),
                               ("OS apagado", "activa: no\nweb_nueva: sí\n", True), ("sin servicios.md", "activa: sí\nweb_nueva: sí\n", False)):
        r2 = montar(nombre.replace(" ", "-").replace(":", ""), os_md, con)
        lanzar(r2, pasa, pruebas[0], "q1"); lanzar(r2, falla, pruebas[1], "q2")
        comprueba(f"{nombre}: ni una escritura en .git/hackathon", not os.path.exists(os.path.join(r2, ".git", "hackathon")))


def prueba_servicios_md(tmp):
    """M9a, K-97: la sección «Servicios» de estado-equipo.md en delta.sh (inicio y delta), con el estado de G12 que
    calcula el relay de verdad. Sin servicios en el estado, ni sección ni firma (lo de M8h)."""
    import time
    from datetime import datetime, timezone
    sys.path.insert(0, KIT + "/hkos")
    sys.path.insert(0, KIT + "/evals/coordinacion/simulador")
    import g12
    import proyeccion
    import relay as relay_mod
    print("\n== «Servicios» en estado-equipo.md y delta.sh (M9a, K-97)")
    base = os.path.join(tmp, "servicios-md"); os.makedirs(base)
    repo_g12, eventos = g12.montar(base)
    nov = relay_mod.Novedades(repo_g12, 300, web_nueva=True)
    nov.sondear()

    class Sondeo:
        tareas, issues, estado = g12.TAREAS, g12.ISSUES, "ok"
        ultimo_ok = datetime.fromisoformat(g12.AHORA.replace("Z", "+00:00")).timestamp()

        def resultado(self, ahora):
            return self.tareas, self.issues, [], 0
    rel = relay_mod.Relay(os.path.join(base, "relay"), g12.PERSONAS, ahora=lambda: g12.AHORA, sondeo=Sondeo(),
                          novedades=nov, web_nueva=True)
    rel.recibir({"eventos": eventos})
    rel.recalcular()
    con = rel.estado
    sin = {k: v for k, v in con.items() if k != "servicios"}

    r = repo_os(base, "clon", "activa: sí\npuerto_agente: 47998\n")
    osdir = os.path.join(r, ".git", "hackathon", "os"); os.makedirs(osdir)
    DELTA = KIT + "/scripts/os/delta.sh"

    def deja(estado):
        v = proyeccion.vista(estado)
        open(os.path.join(osdir, "estado-equipo.md"), "w", encoding="utf-8", newline="\n").write(
            proyeccion.markdown(v, "persona-b", "x", tz=timezone.utc, epoch=int(time.time())))
        open(os.path.join(osdir, "agente.vivo"), "w").write(f"47998\n{int(time.time())}\n")

    def inicio(sid):
        return subprocess.run([BASH, DELTA, "inicio", sid], capture_output=True, text=True, encoding="utf-8", cwd=r).stdout

    def turno(sid):
        return lanza(DELTA, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": sid, "cwd": r,
                                        "prompt": "sigue"}), r).stdout

    deja(sin)
    b = inicio("s1")
    comprueba("sin servicios en el estado: ni sección ni firma servicios:", "## Servicios" not in b and turno("s1") == "")
    deja(con)
    b = inicio("s2")
    titulos = [l for l in b.splitlines() if l.startswith("## ")]
    comprueba("con servicios: «Servicios» entre «Reservas» y «Novedades», con lo que afecta a @persona-b",
              titulos[2:4] == ["## Reservas", "## Servicios"] and titulos[4] == "## Novedades"
              and "sin confirmar · servicio «motor» · cambio de @persona-c" in b, str(titulos))
    comprueba("sin cambios: el delta no imprime nada", turno("s2") == "")
    otro = json.loads(json.dumps(con))
    otro["servicios"]["desajustes"].append({"tipo": "salud_falla", "clave": "0" * 12, "personas": ["persona-b"],
                                           "detalle": "«motor» :9000/salud responde 500", "observado_en": g12.AHORA,
                                           "fuente": "demonio"})
    deja(otro)
    d = turno("s2")
    comprueba("un desajuste nuevo de @persona-b: el delta trae solo «Servicios», con la línea nueva delante",
              "## Servicios" in d and "## Tu trabajo" not in d and "## Novedades" not in d
              and d.index("responde 500") < d.index("cambio de @persona-c"), d)
    otro["servicios"]["desajustes"][-1]["personas"] = ["persona-a"]
    deja(otro)
    comprueba("…cuando ese desajuste pasa a ser solo de @persona-a, a @persona-b le llega un delta y después silencio",
              turno("s2") != "" and turno("s2") == "")


def prueba_arranque(tmp):
    """M8d: sesion.sh lanza el demonio (scripts/os/arranque.sh). Con el OS apagado, la salida es la de antes, byte a byte;
    con el puerto de otro programa o sin uv, avisa una sola vez por sesión, en JSON, y no lanza nada."""
    import http.server
    import socket
    import threading
    print("\n== arranque del demonio (sesion.sh y arranque.sh, M8d)")
    base = os.path.join(tmp, "arranque"); os.makedirs(base)
    r = repo_os(base, "clon")
    open(os.path.join(r, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n")
    gh = os.path.join(base, "gh-falso").replace("\\", "/")
    open(gh, "w", newline="\n").write('#!/usr/bin/env bash\ncase "$*" in *"api user"*) echo Persona-A ;; esac\nexit 0\n')
    registro = os.path.join(base, "lanzado.txt").replace("\\", "/")
    ejecutable(gh)
    env = dict(ENV, HK_GH=gh, HKOS_LANZAR=registro)
    # El sesion.sh del commit anterior, con el resto de scripts tal cual, para comparar la salida.
    viejo = os.path.join(base, "kit-viejo")
    shutil.copytree(os.path.join(KIT, "scripts"), os.path.join(viejo, "scripts"))
    texto_viejo = subprocess.run(["git", "show", "HEAD:scripts/coordinacion/sesion.sh"], cwd=KIT, capture_output=True,
                                 text=True, encoding="utf-8", check=True).stdout
    open(os.path.join(viejo, "scripts", "coordinacion", "sesion.sh"), "w", encoding="utf-8", newline="\n").write(texto_viejo)
    SES, SES_VIEJO = KIT + "/scripts/coordinacion/sesion.sh", (viejo + "/scripts/coordinacion/sesion.sh").replace("\\", "/")

    def sesion(sid="s1", source="startup", script=SES, e=None):
        return lanza(script, json.dumps({"hook_event_name": "SessionStart", "session_id": sid, "source": source, "cwd": r}), r, e or env)

    def lanzados():
        if not os.path.exists(registro):
            return []
        texto = open(registro, encoding="utf-8").read()
        os.remove(registro)
        return texto.splitlines()

    antes = sesion(script=SES_VIEJO).stdout
    comprueba("la coordinación responde en la prueba (Eres el agente de @persona-a)", "@persona-a" in antes, antes[:200])
    for nombre, os_md in (("sin os.md", None), ("activa: no", "activa: no\n")):
        if os_md is None:
            if os.path.exists(os.path.join(r, ".hackathon", "os.md")):
                os.remove(os.path.join(r, ".hackathon", "os.md"))
        else:
            open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write(os_md)
        s = sesion()
        comprueba(f"OS apagado ({nombre}): salida idéntica a la de antes y nada lanzado",
                  s.stdout == antes and s.returncode == 0 and not lanzados() and not os.path.isdir(os.path.join(r, ".git", "hackathon", "os")),
                  repr(s.stdout[:200]))

    # M8e: hk-os compilar con el OS apagado sale sin red (un gh falso en el PATH deja rastro si lo llaman).
    uv = shutil.which("uv")
    if uv:
        rastro_dir = os.path.join(base, "gh-rastro"); os.makedirs(rastro_dir)
        rastro = os.path.join(base, "rastro-gh.txt").replace("\\", "/")
        open(os.path.join(rastro_dir, "gh"), "w", newline="\n").write(f'#!/usr/bin/env bash\necho "$*" >> "{rastro}"\nexit 1\n')
        if os.name == "nt":
            open(os.path.join(rastro_dir, "gh.cmd"), "w").write(f'@echo %* >> "{rastro}"\r\n@exit /b 1\r\n')
        e = dict(ENV, PATH=rastro_dir + os.pathsep + ENV["PATH"], HKOS_GITHUB_API="http://127.0.0.1:9")
        c = subprocess.run([uv, "run", "--no-project", "--quiet", KIT + "/hkos/cli.py", "compilar"], cwd=r, env=e,
                           capture_output=True, text=True, encoding="utf-8")
        comprueba("hk-os compilar con el OS apagado: sale con 1, lo dice y no llama a gh ni a la red",
                  c.returncode == 1 and "no está activo" in c.stdout and not os.path.exists(rastro), c.stdout + c.stderr)
    open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write("activa: sí\n")
    s = sesion()
    comun = git(r, "rev-parse", "--path-format=absolute", "--git-common-dir")
    puerto = 47100 + cksum(comun.encode("utf-8")) % 900
    l = lanzados()
    comprueba("OS activo, puerto libre: misma salida y un lanzamiento con la persona y el puerto 47100 + cksum % 900",
              s.stdout == antes and len(l) == 1 and f"--persona persona-a --puerto {puerto}" in l[0] and "hkos/agente.py" in l[0],
              f"{l} (puerto esperado {puerto})")
    if os.name == "nt":
        # M8h: el repo de esta prueba está en TEMP, que Git Bash ve como /tmp/…; uv y PowerShell necesitan C:/….
        m = re.search(r"--repo (\S+)", l[0] if l else "")
        comprueba("Windows: --repo y el script del demonio, con rutas de Windows (también en TEMP, que bash ve como /tmp)",
                  m is not None and re.match(r"^[A-Za-z]:/", m.group(1)) is not None and " /tmp/" not in l[0], str(l))
        # Con MSYS_NO_PATHCONV=1 heredado (headless desde Git Bash), git.exe no entiende rutas /c/…: falló en vivo (M8d).
        s = sesion(e=dict(env, MSYS_NO_PATHCONV="1"))
        l = lanzados()
        comprueba("…también con MSYS_NO_PATHCONV=1 heredado", s.stdout == antes and len(l) == 1 and f"--puerto {puerto}" in l[0], str(l))

    # Un programa ajeno en el puerto (puerto_agente:), y después un demonio de este clon.
    class Ajeno(http.server.BaseHTTPRequestHandler):
        respuesta = b"<html>otro programa</html>"

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.respuesta)))
            self.end_headers()
            self.wfile.write(self.respuesta)

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Ajeno)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    p = srv.server_address[1]
    open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write(f"activa: sí\npuerto_agente: {p}   # prueba\n")
    try:
        s = sesion("s2")
        try:
            j = json.loads(s.stdout)
        except ValueError:
            j = {}
        contexto = j.get("hookSpecificOutput", {}).get("additionalContext", "")
        comprueba("puerto ocupado por otro programa: JSON con systemMessage y el contexto de siempre más el aviso; nada lanzado",
                  f"puerto {p} está ocupado" in j.get("systemMessage", "") and contexto.startswith(antes) and "puerto_agente:" in contexto
                  and not lanzados(), s.stdout[:300])
        marca = open(os.path.join(r, ".git", "hackathon", "os", "entregado", "s2"), encoding="utf-8").read()
        s = sesion("s2", "compact")
        comprueba("…en la misma sesión (compact) no avisa ni lo reintenta", s.stdout == antes and not lanzados() and marca == "puerto_ocupado\n",
                  s.stdout[:200])
        s = sesion("s3")
        comprueba("…en otra sesión vuelve a avisar", s.stdout.startswith('{"systemMessage"') and not lanzados())
        Ajeno.respuesta = f"hk-os {comun.upper() if os.name == 'nt' else comun}\npendientes: 0\n".encode("utf-8")
        s = sesion("s4")
        comprueba("un demonio de este clon en el puerto (/salud con su git común): no lanza otro ni avisa",
                  s.stdout == antes and not lanzados(), s.stdout[:200])
        vivo = os.path.join(r, ".git", "hackathon", "os", "agente.vivo")
        open(vivo, "w").write(f"{p}\n")
        s = sesion("s4b")
        comprueba("…también con agente.vivo (conexión directa, sin sondeo)", s.stdout == antes and not lanzados(), s.stdout[:200])
        Ajeno.respuesta = b"hk-os C:/otro/clon/.git\n"
        s = sesion("s5")
        comprueba("el demonio de otro clon en el puerto cuenta como otro programa", s.stdout.startswith('{"systemMessage"') and not lanzados())
        os.remove(vivo)
    finally:
        srv.shutdown(); srv.server_close()

    # Sin uv en el PATH.
    uv = shutil.which("uv")
    if uv:
        sep = os.pathsep
        camino = sep.join(d for d in env["PATH"].split(sep) if os.path.normcase(os.path.abspath(d or ".")) != os.path.normcase(os.path.dirname(uv)))
        with socket.socket() as so:
            so.bind(("127.0.0.1", 0)); libre = so.getsockname()[1]
        open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write(f"activa: sí\npuerto_agente: {libre}\n")
        s = sesion("s6", e=dict(env, PATH=camino))
        comprueba("sin uv: avisa una vez (JSON) y no lanza", "uv no está instalado" in s.stdout and not lanzados(), s.stdout[:200])
        s = sesion("s6", "resume", e=dict(env, PATH=camino))
        comprueba("…y en la misma sesión ya no", not s.stdout.startswith("{") and not lanzados())
        open(os.path.join(r, ".git", "hackathon", "os", "agente.vivo"), "w").write(f"{libre}\n")
        s = sesion("s7")
        comprueba("agente.vivo viejo (demonio muerto) y el puerto libre: lo lanza", s.stdout == antes and len(lanzados()) == 1)
    os.remove(os.path.join(r, ".hackathon", "os.md"))


def prueba_persona_fija(tmp):
    """M8h (K-80): sin GitHub, `hk-os unir --persona` deja yo-fijo, que manda sobre gh en hk_yo y en la persona de los
    eventos. sesion.sh avisa una vez por clon si gh, cuando responde, dice otro usuario. Sin yo-fijo, nada cambia (lo
    comprueba prueba_proyeccion contra la 0.3.2)."""
    print("\n== persona declarada sin GitHub (yo-fijo, M8h)")
    base = os.path.join(tmp, "persona"); os.makedirs(base)
    r = repo_os(base, "clon", os_md="activa: sí\npuerto_agente: 47998\n")
    open(os.path.join(r, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n| B | @persona-b |\n")
    gh = os.path.join(base, "gh-falso").replace("\\", "/")
    respuesta = os.path.join(base, "gh-dice").replace("\\", "/")
    open(gh, "w", newline="\n").write('#!/usr/bin/env bash\ncase "$*" in *"api user"*) [ -s "%s" ] || exit 1; cat "%s" ;; esac\n'
                                     'exit 0\n' % (respuesta, respuesta))
    ejecutable(gh)
    env = dict(ENV, HK_GH=gh, HKOS_LANZAR=os.path.join(base, "lanzado.txt").replace("\\", "/"))
    estado = os.path.join(r, ".git", "hackathon")
    os.makedirs(estado, exist_ok=True)
    SES = KIT + "/scripts/coordinacion/sesion.sh"

    def sesion(sid):
        return lanza(SES, json.dumps({"hook_event_name": "SessionStart", "session_id": sid, "source": "startup", "cwd": r}), r, env)

    def gh_dice(login):
        open(respuesta, "w", newline="\n").write(login + "\n" if login else "")

    open(os.path.join(estado, "yo-fijo"), "w", newline="\n").write("Persona-A\r\n")
    gh_dice("")                                                     # sin red: gh no responde
    s = sesion("p1")
    comprueba("yo-fijo sin red: la sesión es de @persona-a, sin aviso ni comprobación hecha",
              "agente de @persona-a" in s.stdout and "gh dice" not in s.stdout
              and not os.path.exists(os.path.join(estado, "yo-fijo.comprobado")), s.stdout[:200])
    gh_dice("persona-b")                                            # vuelve la red y gh es otra persona
    s = sesion("p2")
    try:
        d = json.loads(s.stdout)
    except ValueError:
        d = {}
    comprueba("gh responde con otro usuario: aviso en systemMessage y en el contexto",
              "gh dice que eres @persona-b" in d.get("systemMessage", "")
              and "agente de @persona-a" in d.get("hookSpecificOutput", {}).get("additionalContext", ""), s.stdout[:300])
    s = sesion("p3")
    comprueba("…una sola vez por clon", "gh dice" not in s.stdout and "agente de @persona-a" in s.stdout, s.stdout[:200])
    os.remove(os.path.join(estado, "yo-fijo.comprobado"))
    gh_dice("persona-a")
    s = sesion("p4")
    comprueba("gh coincide: sin aviso, y queda comprobado",
              "gh dice" not in s.stdout and os.path.exists(os.path.join(estado, "yo-fijo.comprobado")), s.stdout[:200])
    # La persona de los eventos: yo-fijo manda aunque haya una caché de gh con otra.
    open(os.path.join(estado, "yo-12345"), "w", newline="\n").write("persona-b\n")
    e = lanza(KIT + "/scripts/os/emite.sh", json.dumps({"hook_event_name": "SessionStart", "session_id": "p5",
                                                         "source": "startup", "cwd": r}), r)
    ls = lineas(r).get("p5", [])
    comprueba("emite.sh: la persona del evento es la de yo-fijo",
              e.returncode == 0 and len(ls) == 1 and json.loads(ls[0])["persona"] == "persona-a", repr(ls))


def prueba_avisar(tmp):
    """Pendiente de M6b-2: `buzon.sh avisar` con la misma nota dos veces (un reintento) abría dos issues (#11 y #12 del
    sandbox). La segunda vez dice el issue de la primera y no llama a gh; una nota distinta sí abre otro."""
    print("\n== buzon.sh avisar no repite la misma nota (M6b-2)")
    base = os.path.join(tmp, "avisar"); os.makedirs(base)
    r = repo_os(base, "clon")
    open(os.path.join(r, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n| B | @persona-b |\n")
    gh = os.path.join(base, "gh-falso").replace("\\", "/")
    llamadas = os.path.join(base, "llamadas.txt").replace("\\", "/")
    open(gh, "w", newline="\n").write(
        '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" >> "%s"\n'
        'case "$*" in *"api user"*) echo persona-a ;; *"issue create"*) n=$(grep -c "issue create" "%s"); '
        'echo "https://github.com/equipo/reto/issues/$n" ;; esac\nexit 0\n' % (llamadas, llamadas))
    ejecutable(gh)
    env = dict(ENV, HK_GH=gh)
    BUZ = KIT + "/scripts/coordinacion/buzon.sh"

    def avisar(texto):
        f = os.path.join(base, "nota.md")
        open(f, "w", encoding="utf-8", newline="\n").write(texto)
        return subprocess.run([BASH, BUZ, "avisar", "nota de prueba", f.replace("\\", "/")], capture_output=True,
                              text=True, encoding="utf-8", cwd=r, env=env)

    def creados():
        return open(llamadas, encoding="utf-8").read().count("issue create") if os.path.exists(llamadas) else 0

    nota = "- 2026-11-20 10:00 · Jurado · «Queremos ver la demo» · Anotado por A\n"
    s1 = avisar(nota)
    comprueba("la primera vez abre el issue", s1.returncode == 0 and creados() == 1 and "issues/1" in s1.stdout,
              s1.stdout + s1.stderr)
    s2 = avisar(nota)
    comprueba("la misma nota otra vez: dice el issue de antes y no abre otro",
              s2.returncode == 0 and creados() == 1 and "ya se avisó" in s2.stdout and "issues/1" in s2.stdout,
              s2.stdout + s2.stderr)
    s3 = avisar(nota.replace("10:00", "10:05"))
    comprueba("una nota distinta sí abre otro", s3.returncode == 0 and creados() == 2, s3.stdout + s3.stderr)


def prueba_reservas(tmp):
    """M8g (K-73, criterio 4): reserva.sh avisa de un fichero reservado por otra persona, sin bloquear nunca, una vez
    por sesión y reserva; la sección «Reservas» llega en el bloque de inicio y en el delta. Con el OS apagado, nada."""
    import time
    from datetime import datetime, timedelta, timezone
    sys.path.insert(0, KIT + "/hkos")
    import proyeccion
    print("\n== reserva.sh y la sección «Reservas» (M8g, criterio 4)")
    RES, DELTA = KIT + "/scripts/os/reserva.sh", KIT + "/scripts/os/delta.sh"
    base = os.path.join(tmp, "reservas"); os.makedirs(base)
    r = repo_os(base, "clon")
    osdir = os.path.join(r, ".git", "hackathon", "os")

    def edit(ruta, sid="s1", agente=None, cwd=None):
        d = {"session_id": sid, "cwd": cwd or r, "hook_event_name": "PreToolUse", "tool_name": "Edit",
             "tool_input": {"file_path": ruta, "old_string": "a", "new_string": "b"}, "tool_use_id": "toolu_1"}
        if agente:
            d.update(agent_id=agente, agent_type="hackathon-kit:worker")
        return lanza(RES, json.dumps(d), r)

    def estado_con(reservas):
        ahora = datetime.now(timezone.utc)
        return {"v": 1, "generado_en": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"), "fuentes": {},
                "personas": [{"persona": "persona-a", "nombre": "A", "actores": []},
                             {"persona": "persona-b", "nombre": "B", "actores": []}],
                "tareas": [], "sin_tarea": [], "discrepancias": [], "colisiones": [], "reservas": reservas}

    def deja(reservas, persona="persona-b"):
        v = proyeccion.vista(estado_con(reservas))
        os.makedirs(osdir, exist_ok=True)
        open(os.path.join(osdir, "estado-equipo.md"), "w", encoding="utf-8", newline="\n").write(
            proyeccion.markdown(v, persona, "/x/estado.json", tz=timezone.utc, epoch=int(time.time())))
        open(os.path.join(osdir, "reservas.tsv"), "w", encoding="utf-8", newline="\n").write(
            proyeccion.reservas_tsv(v, persona, timezone.utc))

    hasta = (datetime.now(timezone.utc) + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = [{"id": "reserva-1", "rutas": ["web/src/"], "persona": "persona-a", "hasta": hasta, "modo": "compartida"},
           {"id": "reserva-2", "rutas": ["motor/api.py"], "persona": "persona-a", "hasta": hasta, "modo": "exclusiva"},
           {"id": "reserva-3", "rutas": ["pitch/guion.md"], "persona": "persona-b", "hasta": hasta, "modo": "compartida"}]
    deja(res)
    abs_win = (r.replace("/", "\\") + "\\web\\src\\App.jsx")
    for nombre, os_md in (("sin os.md", None), ("activa: no", "activa: no\n")):
        if os_md:
            open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write(os_md)
        s = edit(abs_win)
        comprueba(f"OS apagado ({nombre}): reserva.sh no imprime nada y sale con 0, aunque haya reservas.tsv",
                  s.returncode == 0 and s.stdout == "" and s.stderr == "", s.stdout + s.stderr)
    open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write("activa: sí\n")
    s = edit(abs_win)
    try:
        d = json.loads(s.stdout)
        o = d["hookSpecificOutput"]
    except (ValueError, KeyError):
        d, o = {}, {}
    comprueba("fichero bajo una carpeta reservada por otra (ruta de Windows): additionalContext con quién y hasta cuándo",
              s.returncode == 0 and o.get("hookEventName") == "PreToolUse" and "«web/src/»" in o.get("additionalContext", "")
              and "@persona-a" in o.get("additionalContext", "") and "no se bloquea" in o.get("additionalContext", ""), s.stdout)
    comprueba("nunca lleva permissionDecision ni decision (no bloquea)",
              "permissionDecision" not in o and "decision" not in d and "continue" not in d, s.stdout)
    comprueba("la misma reserva, otra vez en la sesión: sin aviso", edit(abs_win).stdout == "")
    comprueba("otra sesión sí recibe el aviso", "@persona-a" in edit(abs_win, sid="s2").stdout)
    comprueba("un worker de la sesión, aparte (su contexto es otro)", "@persona-a" in edit(abs_win, agente="w1").stdout)
    s = edit(r + "/Motor/API.py", sid="s3")
    comprueba("fichero reservado (ruta de Git Bash, otras mayúsculas): aviso de la reserva exclusiva",
              "«motor/api.py»" in s.stdout and "exclusiva" in s.stdout, s.stdout)
    comprueba("una reserva propia no avisa", edit(r + "/pitch/guion.md", sid="s4").stdout == "")
    comprueba("un fichero sin reservar no avisa", edit(r + "/web/otro.js", sid="s5").stdout == "")
    vencida = [dict(res[0], hasta=(datetime.now(timezone.utc) - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))]
    deja(vencida)
    comprueba("una reserva vencida (aunque siga en reservas.tsv) no avisa", edit(abs_win, sid="s6").stdout == "")
    deja(res)
    w = lanza(RES, json.dumps({"session_id": "s7", "cwd": r, "hook_event_name": "SubagentStart", "agent_id": "w9",
                               "agent_type": "hackathon-kit:worker"}), r)
    comprueba("SubagentStart de un worker: las reservas de otras personas, sin las propias",
              "«web/src/»" in w.stdout and "«motor/api.py»" in w.stdout and "pitch" not in w.stdout
              and '"hookEventName":"SubagentStart"' in w.stdout, w.stdout)
    for tipo in ("hackathon-kit:revisor", "Explore", "general-purpose", "otro-plugin:worker"):
        w = lanza(RES, json.dumps({"session_id": "s7", "cwd": r, "hook_event_name": "SubagentStart", "agent_id": "r1",
                                   "agent_type": tipo}), r)
        comprueba(f"SubagentStart de otro subagente ({tipo}): nada", w.stdout == "", w.stdout)
    w = lanza(RES, json.dumps({"session_id": "s7", "cwd": r, "hook_event_name": "SubagentStart", "agent_id": "w8",
                               "agent_type": "worker"}), r)
    comprueba("SubagentStart de un «worker» sin prefijo (como en los hooks de M7): sí", "«web/src/»" in w.stdout, w.stdout)
    # La sección «Reservas» en el bloque de inicio y en el delta (el agente la tiene delante antes de editar).
    deja([])
    subprocess.run([BASH, DELTA, "inicio", "s8"], capture_output=True, text=True, encoding="utf-8", cwd=r, env=ENV)
    deja(res)
    t = lanza(DELTA, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "s8", "cwd": r, "prompt": "x"}), r).stdout
    comprueba("una reserva nueva de otra persona llega en el siguiente delta, en «Reservas»",
              "## Reservas" in t and "«web/src/»" in t and "pitch" not in t, t)
    t = lanza(DELTA, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "s8", "cwd": r, "prompt": "x"}), r).stdout
    comprueba("…y en el turno siguiente, nada", t == "", t)
    b = subprocess.run([BASH, DELTA, "inicio", "s9"], capture_output=True, text=True, encoding="utf-8", cwd=r, env=ENV).stdout
    comprueba("el bloque de inicio lleva «Reservas» detrás de las colisiones",
              b.index("## Colisiones que te afectan") < b.index("## Reservas") < b.index("## Novedades") and "«motor/api.py»" in b, b)
    os.remove(os.path.join(r, ".hackathon", "os.md"))

    print("\n== escucha.sh: colisión roja nueva por el monitor (M8g, criterio 5, parte sin modelo)")
    ESC = KIT + "/scripts/coordinacion/escucha.sh"
    gh = os.path.join(base, "gh-falso").replace("\\", "/")
    llamadas = os.path.join(base, "gh-llamadas.txt").replace("\\", "/")
    open(gh, "w", newline="\n").write('#!/usr/bin/env bash\necho "$*" >> "' + llamadas + '"\n'
                                      'case "$*" in *"api user"*) echo persona-b ;; esac\nexit 0\n')
    ejecutable(gh)
    coord = os.path.join(r, ".hackathon", "coordinacion.md")
    md_ruta = os.path.join(osdir, "estado-equipo.md")

    def md_con(colisiones):
        e = estado_con([])
        e["colisiones"] = colisiones
        open(md_ruta, "w", encoding="utf-8", newline="\n").write(
            proyeccion.markdown(proyeccion.vista(e), "persona-b", "/x/estado.json", tz=timezone.utc, epoch=int(time.time())))

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    roja1 = {"id": "2:persona-a+persona-b", "nivel": "2", "gravedad": "rojo", "personas": ["persona-a", "persona-b"],
             "rutas": ["app.py"], "observado_en": ahora}
    roja2 = {"id": "3:api:persona-a", "nivel": "3", "gravedad": "rojo", "personas": ["persona-a", "persona-b"],
             "rutas": ["motor/api.py"], "contrato": "motor → web", "observado_en": ahora}
    amarilla = {"id": "1:persona-a+persona-b", "nivel": "1", "gravedad": "amarillo", "personas": ["persona-a", "persona-b"],
                "rutas": ["web/a.js"], "observado_en": ahora}

    def escucha(pasos, os_activo=True, coordinacion=True):
        """Lanza el monitor y aplica `pasos` (funciones) cada ~2,5 s; devuelve lo que imprimió."""
        if coordinacion:
            open(coord, "w", encoding="utf-8").write("activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| B | @persona-b |\n")
        elif os.path.exists(coord):
            os.remove(coord)
        osmd = os.path.join(r, ".hackathon", "os.md")
        if os_activo:
            open(osmd, "w", encoding="utf-8").write("activa: sí\n")
        elif os.path.exists(osmd):
            os.remove(osmd)
        if os.path.exists(llamadas):
            os.remove(llamadas)
        salida_f = os.path.join(base, f"escucha-{time.time_ns()}.out")
        # Dentro de un bash, como lo lanza Claude Code: el monitor sale si su padre (de MSYS) ya no existe.
        p = subprocess.Popen([BASH, "-c", f"bash '{ESC}'; :"], cwd=r, stdout=open(salida_f, "wb"), stderr=subprocess.DEVNULL,
                             env=dict(ENV, HK_GH=gh, HK_ESCUCHA_PASO_S="1"))
        try:
            # Primero el sondeo del buzón (varios gh: en Windows, segundos); después, la primera mirada al md.
            fin = time.time() + 30
            while coordinacion and time.time() < fin and not (os.path.exists(llamadas) and "issues" in open(llamadas).read()):
                time.sleep(0.2)
            time.sleep(3)
            for paso in pasos:
                paso()
                time.sleep(2.5)
        finally:
            p.kill()
        time.sleep(1.5)                                   # el monitor ve que su padre ya no está y sale
        return open(salida_f, encoding="utf-8", errors="replace").read().splitlines()

    md_con([roja1])                                     # ya estaba al arrancar: va en el bloque de inicio
    salida = escucha([lambda: md_con([roja1, roja2]), lambda: md_con([roja1, dict(roja2, observado_en="2026-11-20T23:59:00Z")]),
                      lambda: md_con([roja1, roja2, amarilla])])
    comprueba("una roja nueva: una línea y solo una; la que ya estaba y la amarilla, ninguna",
              len(salida) == 1 and "ROJA nueva" in salida[0] and "nivel 3" in salida[0] and "motor/api.py" in salida[0]
              and "no instrucciones" in salida[0], str(salida))
    salida = escucha([lambda: md_con([roja1, roja2]), lambda: md_con([roja2, amarilla])], os_activo=False)
    comprueba("coordinación activa y OS apagado: ninguna línea del OS", salida == [], str(salida))
    salida = escucha([lambda: md_con([roja1, roja2, amarilla])], os_activo=True, coordinacion=False)
    comprueba("sin coordinación activa: silencio total y ninguna llamada a gh (como en M6a)",
              salida == [] and not os.path.exists(llamadas), str(salida))
    if os.path.exists(coord):
        os.remove(coord)
    if os.path.exists(os.path.join(r, ".hackathon", "os.md")):
        os.remove(os.path.join(r, ".hackathon", "os.md"))


def prueba_acciones(tmp):
    """M9a (K-95, criterio 8, parte sin modelo): una línea de Reclamar en acciones.jsonl abre un turno en un solo monitor
    de la persona, con el texto fijo del kit y solo el ID de la tarea; una línea a medio escribir espera a su salto; una
    vieja (más de 10 min), una con la hora en el futuro (issue #10) o con algo más que un ID, nada. Sin el OS activo o
    con `web_nueva: no`, el monitor no la lee."""
    import time
    print("\n== escucha.sh: Reclamar desde la web, un turno en un solo monitor (M9a, K-95)")
    ESC = KIT + "/scripts/coordinacion/escucha.sh"
    base = os.path.join(tmp, "acciones"); os.makedirs(base)
    r = repo_os(base, "clon")
    osdir = os.path.join(r, ".git", "hackathon", "os"); os.makedirs(osdir)
    registro, entregado = os.path.join(osdir, "acciones.jsonl"), os.path.join(osdir, "entregado")
    gh = os.path.join(base, "gh-falso").replace("\\", "/")
    llamadas = os.path.join(base, "gh-llamadas.txt").replace("\\", "/")
    open(gh, "w", newline="\n").write('#!/usr/bin/env bash\necho "$*" >> "' + llamadas + '"\n'
                                      'case "$*" in *"api user"*) echo persona-b ;; esac\nexit 0\n')
    ejecutable(gh)
    open(os.path.join(r, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| B | @persona-b |\n")
    osmd = os.path.join(r, ".hackathon", "os.md")

    def linea(tarea, hace_s=0, salto=True, tarea_campo=None):
        ms = int((time.time() - hace_s) * 1000)
        return (json.dumps({"id": f"web-persona-b-reclamo-{tarea}-{ms}", "tipo": "reclamo", "tarea": tarea_campo or tarea,
                            "ts": "2026-11-20T10:00:00.000000Z"}, separators=(",", ":")) + ("\n" if salto else "")).encode()

    def anade(datos):
        with open(registro, "ab") as f:           # como el demonio: una sola escritura en modo append
            f.write(datos)

    def monitores(n, os_md, pasos):
        """Lanza n monitores a la vez (n sesiones de la misma persona) y aplica `pasos` cada ~3 s; lo que imprimió
        cada uno."""
        if os_md is None:
            if os.path.exists(osmd):
                os.remove(osmd)
        else:
            open(osmd, "w", encoding="utf-8").write(os_md)
        if os.path.exists(llamadas):
            os.remove(llamadas)
        salidas, procesos = [os.path.join(base, f"escucha-{time.time_ns()}-{i}.out") for i in range(n)], []
        for s in salidas:
            procesos.append(subprocess.Popen([BASH, "-c", f"bash '{ESC}'; :"], cwd=r, stdout=open(s, "wb"),
                                             stderr=subprocess.DEVNULL, env=dict(ENV, HK_GH=gh, HK_ESCUCHA_PASO_S="1")))
        try:
            fin = time.time() + 40                  # primero el sondeo del buzón de cada uno; después, el paso del OS
            while time.time() < fin and not (os.path.exists(llamadas) and open(llamadas).read().count("issues") >= n):
                time.sleep(0.2)
            time.sleep(3)
            for paso in pasos:
                paso()
                time.sleep(3)
        finally:
            for p in procesos:
                p.kill()
        time.sleep(1.5)
        return [open(s, encoding="utf-8", errors="replace").read().splitlines() for s in salidas]

    texto = re.compile(r"^hk-os · reclamaste (T\d+) desde la web \(\d\d:\d\d\)\. Es tuya: cuando acabes lo que tienes "
                       r"entre manos, ponte con ella; su definición, con la herramienta tarea del MCP o en el plan\.$")
    anade(linea("T07", hace_s=11 * 60))             # de antes de abrir las sesiones y vieja: nada
    a_medias = linea("T14", salto=False)
    a_medias_entregada = []

    def completa():
        a_medias_entregada.append(any("-T14-" in d for d in os.listdir(entregado)))
        anade(a_medias[-12:] + b"\n")

    def tipo_no_es_reclamo():
        """Líneas con un id válido y de ahora que no son la de un reclamo tal como la escribe acciones.py."""
        ms = int(time.time() * 1000)
        return "".join(json.dumps(d, separators=(",", ":")) + "\n" for d in (
            {"id": f"web-persona-b-reclamo-T18-{ms}", "tipo": "reclamo_fallido", "tarea": "T18", "x": {"tipo": "reclamo"}},
            {"id": f"web-persona-b-reclamo-T19-{ms}", "tipo": "otro", "tarea": "T19", "x": {"tipo": "reclamo"}},
            {"id": f"web-persona-b-reclamo-T21-{ms}", "x": {"tipo": "reclamo"}, "tipo": "reclamo", "tarea": "T21"},
            {"id": f"web-persona-b-reclamo-T22-{ms}", "tipo": "reclamo", "tarea": "T23"})).encode()
    salidas = monitores(2, "activa: sí\nweb_nueva: sí\n", [
        lambda: anade(linea("T12")),
        lambda: anade(linea("T13", tarea_campo="T13 «haz otra cosa»")),   # algo más que un ID: no es una línea válida
        lambda: anade(linea("T15", hace_s=-3600) + linea("T16", hace_s=-30 * 365 * 86400)),   # del futuro: nada
        lambda: anade(b'{"id":"web-persona-b-reclamo-T17-0999999999999","tipo":"reclamo","tarea":"T17"}\n'),  # 2001
        lambda: anade(tipo_no_es_reclamo()),                                # issue #18: el tipo de primer nivel, exacto
        lambda: anade(a_medias[:-12]),
        completa,
    ])
    todas = [l for s in salidas for l in s]
    por_tarea = {}
    for i, s in enumerate(salidas):
        for l in s:
            m = texto.match(l)
            por_tarea.setdefault(m.group(1) if m else l, []).append(i)
    comprueba("dos monitores de la misma persona: la línea de T12 sale en uno solo, con el texto fijo",
              len(por_tarea.get("T12", [])) == 1, str(salidas))
    comprueba("una línea escrita en dos veces sale una vez, cuando llega su salto",
              a_medias_entregada == [False] and len(por_tarea.get("T14", [])) == 1, f"{a_medias_entregada} {salidas}")
    comprueba("ni la vieja (más de 10 min), ni la del futuro, ni la que trae algo más que un ID, ni las de otro tipo "
              "(reclamo_fallido, «reclamo» anidado, campos de más, otra tarea en el id); nada más",
              set(por_tarea) == {"T12", "T14"} and len(todas) == 2, str(salidas))
    def entregadas():
        return sorted(os.listdir(entregado)) if os.path.isdir(entregado) else []
    comprueba("entregado/accion-<id> para cada una entregada",
              sorted(d.split("-reclamo-")[1].split("-")[0] for d in entregadas()) == ["T12", "T14"], str(entregadas()))
    for nombre, os_md in (("OS apagado (sin os.md), con la coordinación activa", None), ("activa: no", "activa: no\nweb_nueva: sí\n"),
                          ("web_nueva: no", "activa: sí\nweb_nueva: no\n")):
        antes = entregadas()
        salidas = monitores(1, os_md, [lambda: anade(linea("T20"))])
        comprueba(f"{nombre}: el monitor no lee acciones.jsonl (ni turno ni entregado/)",
                  salidas == [[]] and entregadas() == antes, str(salidas))
    for f in (osmd, os.path.join(r, ".hackathon", "coordinacion.md")):
        if os.path.exists(f):
            os.remove(f)


def prueba_proyeccion(tmp):
    """M8f (K-62): el bloque «Equipo» de sesion.sh (criterio 2) y delta.sh (criterio 3), con el reloj inyectado en el
    estado y el md generado por hkos/proyeccion.py. Con el OS apagado, todo sale como en la 0.3.2."""
    import time
    from datetime import datetime, timedelta, timezone
    sys.path.insert(0, KIT + "/hkos")
    sys.path.insert(0, KIT + "/evals/coordinacion/simulador")
    import proyeccion
    from fixture import estado_5x20
    from modelo import calcular
    from simula import AQUI, carga, ejecutar
    print("\n== proyección en las sesiones (sesion.sh y delta.sh, M8f)")
    base = os.path.join(tmp, "proyeccion"); os.makedirs(base)
    r = repo_os(base, "clon")
    open(os.path.join(r, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| B | @persona-b |\n")
    gh = os.path.join(base, "gh-falso").replace("\\", "/")
    open(gh, "w", newline="\n").write('#!/usr/bin/env bash\ncase "$*" in *"api user"*) echo persona-b ;; esac\nexit 0\n')
    registro = os.path.join(base, "lanzado.txt").replace("\\", "/")
    ejecutable(gh)
    env = dict(ENV, HK_GH=gh, HKOS_LANZAR=registro)
    DELTA, SES = KIT + "/scripts/os/delta.sh", KIT + "/scripts/coordinacion/sesion.sh"
    osdir = os.path.join(r, ".git", "hackathon", "os")
    md_ruta = os.path.join(osdir, "estado-equipo.md")

    def sesion(sid, source="startup", script=SES):
        return lanza(script, json.dumps({"hook_event_name": "SessionStart", "session_id": sid, "source": source, "cwd": r}), r, env)

    def turno(sid="s1"):
        s = lanza(DELTA, json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": sid, "cwd": r,
                                     "prompt": "sigue"}), r, env)
        return s.stdout

    def inicio(sid):
        return subprocess.run([BASH, DELTA, "inicio", sid], capture_output=True, text=True, encoding="utf-8", cwd=r, env=env).stdout

    def deja_md(estado, ahora=None, persona="persona-b"):
        v = proyeccion.vista(estado, ahora=ahora)
        os.makedirs(osdir, exist_ok=True)
        open(md_ruta, "w", encoding="utf-8", newline="\n").write(
            proyeccion.markdown(v, persona, osdir.replace("\\", "/") + "/estado.json", tz=timezone.utc, epoch=int(time.time())))

    def vivo_fresco():
        os.makedirs(osdir, exist_ok=True)
        open(os.path.join(osdir, "agente.vivo"), "w").write(f"47999\n{int(time.time())}\n")

    def lanzados():
        if not os.path.exists(registro):
            return []
        texto = open(registro, encoding="utf-8").read()
        os.remove(registro)
        return texto.splitlines()

    # --- OS apagado: sesion.sh igual que en la 0.3.2 (startup y compact), delta.sh sin salida ni ficheros ---
    v032 = os.path.join(base, "kit-0.3.2")
    tar = subprocess.run(["git", "archive", "--format=tar", "v0.3.2", "scripts"], cwd=KIT, capture_output=True, check=True).stdout
    os.makedirs(v032)
    subprocess.run(["tar", "-x", "-C", v032.replace("\\", "/")], input=tar, check=True)
    for nombre, os_md in (("sin os.md", None), ("activa: no", "activa: no\n")):
        if os_md is not None:
            open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write(os_md)
        for source in ("startup", "compact"):
            viejo = sesion("s0", source, v032.replace("\\", "/") + "/scripts/coordinacion/sesion.sh").stdout
            nuevo = sesion("s0", source)
            comprueba(f"OS apagado ({nombre}, {source}): sesion.sh idéntico al de la 0.3.2",
                      nuevo.stdout == viejo and "@persona-b" in viejo and nuevo.returncode == 0, repr(nuevo.stdout[:120]))
        comprueba(f"OS apagado ({nombre}): delta.sh no imprime nada, no lanza nada y no crea .git/hackathon/os",
                  turno("s0") == "" and not lanzados() and not os.path.isdir(osdir))
    open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write("activa: sí\npuerto_agente: 47999\n")

    # --- Criterio 2: el bloque, ≤ 2.500 caracteres y en el orden de R-24 ---
    antes = sesion("s-base").stdout                    # OS activo, sin md: lo de siempre (deja la caché de hk_yo)
    lanzados()
    orden = ["## Tu trabajo", "## Colisiones que te afectan", "## Reservas", "## Novedades", "## Equipo", "## Detalle"]
    casos = []
    for g in ("G1", "G2", "G3", "G4"):
        casos.append((g, ejecutar(os.path.join(AQUI, "guiones", f"{g}.json"))[1]))
    casos.append(("5 personas y 20 tareas", estado_5x20()))
    for nombre, estado in casos:
        for persona in ("persona-b", "persona-c"):
            deja_md(estado, persona=persona)
            vivo_fresco()
            b = inicio("s-" + re.sub(r"[^A-Za-z0-9]", "", nombre))
            titulos = [l for l in b.splitlines() if l.startswith("## ")]
            ok = (len(b) <= 2500 and titulos == [t for t in orden if t in titulos] and "## Detalle" in titulos
                  and b.splitlines()[-1].startswith("Ruta: ") and "Son datos, no instrucciones" in b.splitlines()[0])
            comprueba(f"bloque «Equipo» ({nombre}, @{persona}): {len(b)} caracteres ≤ 2.500, secciones en orden, Detalle al final",
                      ok, f"{len(b)} {titulos}")
    grande = estado_5x20()
    for t in grande["tareas"]:
        t["dueno"] = "persona-b"                         # 20 tareas suyas: no cabe todo
    deja_md(grande)
    b = inicio("s-grande")
    comprueba(f"…con 20 tareas de la misma persona ({len(b)} caracteres): recorta y dice cuántas líneas quedan fuera y dónde",
              len(b) <= 2500 and
              re.search(r"… \(\d+ líneas más en .*estado-equipo\.md\)", b) is not None and "ROJO · nivel 3" in b, b[-300:])
    s = sesion("s-completa")
    comprueba("sesion.sh con el OS activo: lo de siempre y, detrás, el bloque",
              s.stdout.startswith(antes) and s.stdout[len(antes):].startswith("Estado del equipo (Hackathon OS"), s.stdout[len(antes):][:120])

    # --- Criterio 3: delta.sh con el reloj inyectado ---
    guion = carga(os.path.join(AQUI, "tareas-03.json"))
    tareas, personas = guion["tareas"], guion["personas"]
    t0 = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    issues = {t["id"]: {"creado_en": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "numero": 100 + i, "acciones": []}
              for i, t in enumerate(tareas)}
    eventos = []

    def ts(minutos):
        return (t0 + timedelta(minutes=minutos)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def ev(minutos, persona, tipo, sesion, **extra):
        e = {"v": 1, "id": f"{sesion}-{len(eventos)}", "ts": ts(minutos), "tipo": tipo, "fuente": "hook",
             "actor": {"persona": persona, "papel": "principal", "sesion": sesion}}
        e.update(extra)
        eventos.append(e)

    def estado_en(minutos):
        return calcular(tareas, issues, eventos, personas, ts(minutos))
    t10 = next(t for t in tareas if t["id"] == "T10")
    comprueba("el guion usa T10 de B, que espera a T01 de A", t10["dueno"] == "persona-b" and t10["depende_de"] == ["T01"], str(t10))
    # Minuto 0: A empieza T01; B tiene su sesión. La sesión de B arranca con el bloque entero.
    ev(0, "persona-a", "sesion.inicio", "sa")
    ev(0, "persona-a", "edicion", "sa", tarea="T01", rutas=["motor/ficha.py"])
    ev(0, "persona-b", "sesion.inicio", "sb")
    deja_md(estado_en(0), ts(0))
    vivo_fresco()
    inicio("sb")
    silencio, salidas = 0, []
    for m in range(1, 31):
        # 30 minutos de actividad ajena: A edita T01 y otros ficheros, C entra y sale, A cambia de presencia.
        ev(m, "persona-a", "edicion", "sa", tarea="T01", rutas=[f"motor/f{m % 4}.py"])
        if m % 7 == 0:
            ev(m, "persona-c", "sesion.inicio", f"sc{m}")
        if m % 7 == 3:
            ev(m, "persona-c", "sesion.fin", f"sc{m - 3}")
        if m % 10 == 5:
            ev(m, "persona-a", "arbol", "sa", rutas=["motor/ficha.py", ".claude/worktrees/"])
        deja_md(estado_en(m), ts(m))
        vivo_fresco()
        salida = turno("sb")
        silencio += salida == ""
        if salida:
            salidas.append((m, salida))
    comprueba("30 turnos en 30 minutos de actividad ajena: delta.sh no imprime nada en ninguno", silencio == 30, str(salidas[:2]))
    # A deja T01 a medias: a los 20 minutos sin actividad, parada. A B le afecta (T10 espera a T01).
    deja_md(estado_en(51), ts(51))
    vivo_fresco()
    d = turno("sb")
    comprueba("la dependencia pasa a parada: B recibe solo «Tu trabajo», ≤ 600 caracteres, con «espera a T01 (@persona-a, parada)»",
              0 < len(d) <= 600 and "## Tu trabajo" in d and "espera a T01 (@persona-a, parada)" in d
              and "## Equipo" not in d and "## Colisiones" not in d, d)
    comprueba("…y en el turno siguiente, nada", turno("sb") == "")
    # Compactación: sesion.sh (delta.sh inicio) reinyecta el bloque entero y pone a cero lo entregado.
    b = inicio("sb")
    firmas = open(os.path.join(osdir, "entregado", "sb.firmas"), encoding="utf-8").read()
    comprueba("compactación: vuelve a dar el bloque entero y pone la cuenta a cero",
              "## Tu trabajo" in b and "## Equipo" in b and "chars=0" in firmas and turno("sb") == "", firmas)
    # Sesión sin nada entregado (el md llegó después del SessionStart): el primer turno da lo que no está vacío.
    d = turno("sb-nueva")
    comprueba("sesión sin bloque inicial: el primer turno trae «Tu trabajo» (≤ 600) y no las secciones vacías",
              "## Tu trabajo" in d and "## Colisiones" not in d and "## Novedades" not in d and len(d) <= 600, d)
    # R-25b: pasados 6.000 caracteres, solo colisiones rojas nuevas.
    estado = estado_5x20()
    deja_md(estado)
    vivo_fresco()
    inicio("s-tope")
    f = os.path.join(osdir, "entregado", "s-tope.firmas")
    texto = open(f, encoding="utf-8", newline="").read()
    open(f, "w", encoding="utf-8", newline="").write(texto.replace("chars=0", "chars=6001"))
    estado["tareas"][1]["estado"]["valor"] = "en_revision"          # cambia «Tu trabajo» de B
    deja_md(estado)
    d = turno("s-tope")
    comprueba("tope de 6.000 (R-25b): un cambio de «Tu trabajo» ya no se inyecta", d == "", d)
    estado["colisiones"].append({"id": "n3-otro", "nivel": "3", "gravedad": "rojo", "personas": ["persona-b", "persona-d"],
                                 "rutas": ["motor/api.py"], "contrato": "API", "observado_en": estado["generado_en"]})
    estado["colisiones"].append({"id": "n1-otro", "nivel": "1", "gravedad": "amarillo", "personas": ["persona-b", "persona-e"],
                                 "rutas": ["web/b.js"], "observado_en": estado["generado_en"]})
    deja_md(estado)
    d = turno("s-tope")
    comprueba("…pero una colisión roja nueva sí: solo la roja nueva", "contrato «API»" in d and "Ficha de empresa" not in d
              and "AMARILLO" not in d and "## Tu trabajo" not in d, d)

    # --- Relanzar el demonio (Pendiente de M8d) ---
    vivo = os.path.join(osdir, "agente.vivo")
    os.remove(vivo)
    lanzados()
    turno("sb")
    comprueba("sin agente.vivo: delta.sh lanza el arranque (una vez)", len(lanzados()) == 1)
    open(vivo, "w").write(f"47999\n{int(time.time()) - 600}\n")
    turno("sb")
    comprueba("agente.vivo de hace 10 min (murió sin borrarlo): lo borra y relanza", len(lanzados()) == 1 and not os.path.exists(vivo))
    open(vivo, "w").write(f"47999\n{int(time.time()) + 3600}\n")
    turno("sb")
    comprueba("agente.vivo con la hora 1 h en el futuro (issue #23): lo borra y relanza", len(lanzados()) == 1 and not os.path.exists(vivo))
    open(vivo, "w").write(f"47999\n{int(time.time()) + 2}\n")
    turno("sb")
    comprueba("…pero 2 s en el futuro (dentro del margen de 5 s) sigue siendo un latido: no lanza nada",
              lanzados() == [] and os.path.exists(vivo))
    vivo_fresco()
    turno("sb")
    comprueba("agente.vivo fresco: no lanza nada", lanzados() == [])
    # --- MCP (K-63), lanzado como lo declara .mcp.json (con el alias de git) ---
    servidor = json.load(open(KIT + "/.mcp.json", encoding="utf-8"))["mcpServers"]["os"]
    orden_mcp = [servidor["command"]] + [a.replace("${CLAUDE_PLUGIN_ROOT}", KIT) for a in servidor["args"]]
    hola = "".join(json.dumps(m) + "\n" for m in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": "x", "method": "ping"}))

    def herramientas(e):
        s = subprocess.run(orden_mcp, input=hola, capture_output=True, text=True, encoding="utf-8", cwd=base,
                           env=dict(e, CLAUDE_PROJECT_DIR=r), timeout=120)
        resp = {m["id"]: m for m in map(json.loads, s.stdout.splitlines())}
        return resp[1]["result"]["protocolVersion"], [t["name"] for t in resp[2]["result"]["tools"]], "x" in resp
    deja_md(estado_5x20())
    open(os.path.join(osdir, "estado.json"), "w", encoding="utf-8").write(json.dumps(estado_5x20()))
    uv = shutil.which("uv")
    if uv:
        sep = os.pathsep
        sin_uv = sep.join(d for d in ENV["PATH"].split(sep) if os.path.normcase(os.path.abspath(d or ".")) != os.path.normcase(os.path.dirname(uv)))
        comprueba("MCP con el OS activo y sin uv: responde en bash, sin herramientas",
                  herramientas(dict(ENV, PATH=sin_uv)) == ("2025-06-18", [], True))
        comprueba("MCP con el OS activo y uv: estado, tarea y colisiones",
                  herramientas(ENV) == ("2025-06-18", ["estado", "tarea", "colisiones", "reservar", "liberar"], True))
    os.remove(os.path.join(r, ".hackathon", "os.md"))
    comprueba("MCP con el OS apagado: responde en bash (initialize, ping), sin herramientas",
              herramientas(ENV) == ("2025-06-18", [], True))
    open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write("activa: sí\npuerto_agente: 47999\n")

    # Coste con el OS apagado: delta.sh corre en cada turno de toda sesión con el kit.
    # Con la máquina cargada, una tanda puede salir lenta sin que delta.sh lo sea: hasta 3 tandas y cuenta la mejor. Una
    # regresión de verdad (algo que se ejecuta con el OS apagado) sale lenta en las tres.
    os.remove(os.path.join(r, ".hackathon", "os.md"))
    medidas = []
    while len(medidas) < 3 and (not medidas or min(medidas) > 50):
        t = time.perf_counter()
        for _ in range(10):
            turno("s0")
        medidas.append((time.perf_counter() - t) * 100)
    ms = min(medidas)
    comprueba(f"delta.sh con el OS apagado: {ms:.0f} ms por turno (proceso bash incluido; ≤ 50 ms como los hooks del OS, M8c)",
              ms <= 50, "tandas: " + ", ".join(f"{m:.0f} ms" for m in medidas))


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
    # v0.3.1: informe en un fichero de <git común>/hackathon/informes/ y una línea en el contexto.
    informes = os.path.join(repo, ".git", "hackathon", "informes").replace("\\", "/")
    os.makedirs(informes, exist_ok=True)
    def fichero(nombre, texto, carpeta=informes):
        ruta = f"{carpeta}/{nombre}"
        open(ruta, "w", encoding="utf-8").write(texto)
        return ruta
    def linea(ruta, aid):
        return handback(f"Estado: hecho · Rama: worktree-agent-x · Informe: {ruta}", aid)
    caso("informe en fichero, completo y cierto", "permite", COMP, linea(fichero("x.md", informe()), "i1"), repo)
    caso("informe en fichero, ruta con barras de Windows", "permite", COMP,
         linea(fichero("x2.md", informe()).replace("/", "\\"), "i2"), repo)
    caso("informe en fichero, sin salida de la comprobación", "niega", COMP, linea(fichero("y.md", informe(salida="")), "i3"), repo)
    caso("informe en fichero, ruta inexistente", "niega", COMP, linea(informes + "/no.md", "i4"), repo)
    caso("informe en fichero, fuera de hackathon/informes", "niega", COMP, linea(fichero("fuera.md", informe(), tmp.replace("\\", "/")), "i5"), repo)
    caso("informe en fichero, «..» para salir de la carpeta", "niega", COMP,
         linea(informes + "/../../../../" + os.path.basename(tmp) + "/fuera.md", "i6"), repo)
    caso("formato antiguo, informe completo en el mensaje", "permite", COMP, handback(informe(), "i7"), repo)
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
    # M7c: fusión fuera de main, referencias de fusión y borrado de ramas de workers.
    caso("orquestador, worktree de fusión", "permite", SOLO, bash("git worktree add --detach .claude/worktrees/fusion-abc12345 HEAD", O), repo)
    caso("orquestador, merge en el worktree de fusión", "permite", SOLO,
         bash("git -C .claude/worktrees/fusion-abc12345 merge --no-ff worktree-agent-x -m \"tarea (worker)\"", O), repo)
    caso("orquestador, merge --ff-only a la fusión", "permite", SOLO, bash("git merge --ff-only abc1234", O), repo)
    caso("orquestador, worktree remove fusion-textos-ficha («-f» en el nombre)", "permite", SOLO,
         bash("git -C \"C:/p\" worktree remove .claude/worktrees/fusion-textos-ficha", O), repo)
    caso("orquestador, worktree remove -f", "niega", SOLO, bash("git worktree remove -f .claude/worktrees/fusion-x", O), repo)
    caso("orquestador, worktree remove ruta --force", "niega", SOLO, bash("git worktree remove .claude/worktrees/fusion-x --force", O), repo)
    caso("orquestador, update-ref refs/hackathon", "permite", SOLO, bash("git update-ref refs/hackathon/fusion/nav abc1234", O), repo)
    caso("orquestador, update-ref -d refs/hackathon", "permite", SOLO, bash("git update-ref -d refs/hackathon/fusion/nav", O), repo)
    caso("orquestador, update-ref refs/heads/main", "niega", SOLO, bash("git update-ref refs/heads/main abc1234", O), repo)
    caso("orquestador, update-ref HEAD", "niega", SOLO, bash("git update-ref HEAD abc1234", O), repo)
    caso("orquestador, update-ref encadenado", "niega", SOLO, bash("git update-ref refs/hackathon/x a; git update-ref refs/heads/main b", O), repo)
    caso("revisor, update-ref", "niega", SOLO, bash("git update-ref refs/hackathon/fusion/nav abc1234", R), repo)
    caso("orquestador, branch -D de worker", "permite", SOLO, bash("git branch -D worktree-agent-x worktree-agent-y", O), repo)
    caso("orquestador, branch -D main", "niega", SOLO, bash("git branch -D main", O), repo)
    caso("orquestador, branch -D de worker y main", "niega", SOLO, bash("git branch -D worktree-agent-x main", O), repo)
    caso("orquestador, branch -D encadenado", "niega", SOLO, bash("git branch -D worktree-agent-x && git branch -D main", O), repo)
    caso("revisor, branch -D de worker", "niega", SOLO, bash("git branch -D worktree-agent-x", R), repo)

    print("== sin-confirmo.sh")
    CONF = KIT + "/scripts/coordinacion/sin-confirmo.sh"
    coord = os.path.join(tmp, "coord")
    os.makedirs(os.path.join(coord, ".hackathon"))
    git(coord, "init", "-q", "-b", "main")
    open(os.path.join(coord, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: sí\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n")
    open(os.path.join(coord, "cuerpo.md"), "w", encoding="utf-8").write("Hk Confirmo\n")
    open(os.path.join(coord, "cuerpo16.md"), "w", encoding="utf-16").write("hk confirmo\r\n")
    open(os.path.join(coord, "otro.md"), "w", encoding="utf-8").write("Propuesta: cambiar el contrato\n")
    def cmd(c, herramienta="Bash", tipo=None):
        d = {"hook_event_name": "PreToolUse", "tool_name": herramienta, "tool_input": {"command": c}, "cwd": coord}
        if tipo:
            d["agent_type"] = tipo
        return d
    caso("gh issue comment --body «hk confirmo»", "niega", CONF, cmd('gh issue comment 7 --body "hk confirmo"'), coord)
    caso("gh issue comment --body «HK  Confirmo»", "niega", CONF, cmd("gh issue comment 7 --body 'HK  Confirmo'"), coord)
    caso("gh issue comment -b en un subagente", "niega", CONF, cmd('cd x && gh issue comment 7 -b "hk confirmo"', tipo="hackathon-kit:worker"), coord)
    caso("--body-file con la marca (UTF-8)", "niega", CONF, cmd("gh issue comment 7 --body-file cuerpo.md"), coord)
    caso("-F con la marca (UTF-16)", "niega", CONF, cmd("gh issue comment 7 -F cuerpo16.md"), coord)
    caso("--body-file= con ruta absoluta", "niega", CONF, cmd(f"gh issue comment 7 --body-file={coord}/cuerpo.md".replace("\\", "/")), coord)
    caso("gh api -f body=", "niega", CONF, cmd('gh api repos/equipo/reto/issues/7/comments -f body="hk confirmo"'), coord)
    caso("gh api -F body=@fichero", "niega", CONF, cmd("gh api repos/equipo/reto/issues/7/comments -F body=@cuerpo.md"), coord)
    caso("PowerShell, gh.exe", "niega", CONF, cmd('gh.exe issue comment 7 --body "hk confirmo"', "PowerShell"), coord)
    caso("gh sin la marca", "permite", CONF, cmd("gh issue comment 7 --body-file otro.md"), coord)
    caso("gh issue list", "permite", CONF, cmd("gh issue list --label hk"), coord)
    caso("echo con la marca, sin gh", "permite", CONF, cmd("echo 'escribe hk confirmo en el issue'"), coord)
    caso("buzon.sh (no llama a gh en el comando)", "permite", CONF, cmd('bash "C:/kit/scripts/coordinacion/buzon.sh" leer'), coord)
    caso("otra herramienta", "permite", CONF, {"hook_event_name": "PreToolUse", "tool_name": "Write",
                                               "tool_input": {"file_path": "x", "content": "hk confirmo"}, "cwd": coord}, coord)
    caso("sin coordinación (otra carpeta)", "permite", CONF, cmd('gh issue comment 7 --body "hk confirmo"'), repo)
    open(os.path.join(coord, ".hackathon", "coordinacion.md"), "w", encoding="utf-8").write(
        "activa: no\nrepo: equipo/reto\n\n| Persona | GitHub |\n|---|---|\n| A | @persona-a |\n")
    caso("coordinación con «activa: no»", "permite", CONF, cmd('gh issue comment 7 --body "hk confirmo"'), coord)

    # --- M8a (K-13): los issues de tarea (`hk-tarea`) no entran en el buzón ---
    # GitHub filtra `labels=` por etiqueta exacta (P7 de M8.0, comprobado en el sandbox): basta con que toda
    # consulta de issues del buzón y del monitor pida la etiqueta `hk` tal cual, sin comodines ni prefijos.
    print("\n-- hk-tarea fuera del buzón --")
    for script in ("buzon.sh", "escucha.sh"):
        texto = open(f"{KIT}/scripts/coordinacion/{script}", encoding="utf-8").read()
        consultas = re.findall(r"issues\?labels=([^&\"]*)", texto)
        ok = bool(consultas) and all(c.split(",")[0] == "hk" for c in consultas)
        fallos += not ok
        print(f"{'OK   ' if ok else 'FALLO'} {script}: consultas con labels={', labels='.join(consultas) or '(ninguna)'}")

    prueba_os(tmp, repo, informe, handback)
    prueba_prueba(tmp)
    prueba_servicios_md(tmp)
    prueba_arranque(tmp)
    prueba_proyeccion(tmp)
    prueba_reservas(tmp)
    prueba_acciones(tmp)
    prueba_persona_fija(tmp)
    prueba_avisar(tmp)
finally:
    subprocess.run(["git", "worktree", "prune"], cwd=os.path.join(tmp, "repo"), capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{fallos} fallos")
sys.exit(1 if fallos else 0)
