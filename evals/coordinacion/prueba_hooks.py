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
    "arbol": {"v", "ts", "persona", "tipo", "session_id", "cwd", "agent_id", "agent_type", "base", "porcelain", "diff", "truncado"},
    "compuerta": {"v", "ts", "persona", "tipo", "session_id", "cwd", "agent_id", "agent_type", "resultado", "tope", "motivos", "truncado"},
}


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(f"{'OK   ' if ok else 'FALLO'} {nombre}" + (f"\n        {detalle}" if detalle and not ok else ""))


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
    clase = d.get("tipo") if d.get("tipo") in ("arbol", "compuerta") else "hook"
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
        clave = d.get("tool_name") if ev in ("PreToolUse", "PostToolUse") else d.get("source")
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
    subprocess.run([BASH, "-c", "sed -i 's/uno/dos/' a.txt && echo nuevo > generado.txt"], cwd=r, check=True)
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
    orden = ["## Tu trabajo", "## Colisiones que te afectan", "## Novedades", "## Equipo", "## Detalle"]
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
                  herramientas(ENV) == ("2025-06-18", ["estado", "tarea", "colisiones"], True))
    os.remove(os.path.join(r, ".hackathon", "os.md"))
    comprueba("MCP con el OS apagado: responde en bash (initialize, ping), sin herramientas",
              herramientas(ENV) == ("2025-06-18", [], True))
    open(os.path.join(r, ".hackathon", "os.md"), "w", encoding="utf-8").write("activa: sí\npuerto_agente: 47999\n")

    # Coste con el OS apagado: delta.sh corre en cada turno de toda sesión con el kit.
    os.remove(os.path.join(r, ".hackathon", "os.md"))
    t = time.perf_counter()
    for _ in range(10):
        turno("s0")
    ms = (time.perf_counter() - t) * 100
    comprueba(f"delta.sh con el OS apagado: {ms:.0f} ms por turno (proceso bash incluido; ≤ 50 ms como los hooks del OS, M8c)",
              ms <= 50, f"{ms:.0f} ms")


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
    prueba_arranque(tmp)
    prueba_proyeccion(tmp)
finally:
    subprocess.run(["git", "worktree", "prune"], cwd=os.path.join(tmp, "repo"), capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{fallos} fallos")
sys.exit(1 if fallos else 0)
