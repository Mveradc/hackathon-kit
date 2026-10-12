"""Comprobaciones automáticas A1–A7 de evals/rubrica.md sobre una carpeta generada por el kit.

Nunca modifica la carpeta: el arranque (A2), git (A3) y el relanzado (A6) se hacen sobre copias temporales.

Uso:
    python evals/comprobar.py <carpeta> --enunciado evals/retos/02-facturas-real.md
        [--ref <repo de referencia> ...] [--sin-arranque]
        [--relanzar --stack "python con uv"]
"""

import argparse
import hashlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
IGNORADAS = {".venv", "node_modules", "__pycache__", ".git", "dist", "build", ".pytest_cache", ".pio", ".next", ".m4"}
TEXTO = {".md", ".txt", ".toml", ".json", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
         ".html", ".css", ".yml", ".yaml", ".cfg", ".ini", ".example", ".gitignore", ".env"}
ORIGENES = ("enunciado", "análisis", "analisis", "riesgo típico", "decisión", "supuesto", "conocimiento externo",
            "convención del kit", "criterios")

PASA, FALLA, NA = "Pasa", "Falla", "N/A"


# ---------- utilidades ----------

def leer(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def sin_comentarios(texto):
    return re.sub(r"<!--.*?-->", "", texto, flags=re.S)


def seccion(texto, titulo, nivel):
    """Contenido de la sección cuyo encabezado de `nivel` empieza por `titulo`."""
    marca = "#" * nivel + " "
    dentro, out = False, []
    for linea in texto.splitlines():
        if re.match(rf"^#{{1,{nivel}}} ", linea):
            if dentro:
                break
            dentro = linea.startswith(marca) and linea[len(marca):].strip().startswith(titulo)
            continue
        if dentro:
            out.append(linea)
    return "\n".join(out) if dentro or out else None


def encabezados(texto, nivel):
    return [l[nivel + 1:].strip() for l in sin_comentarios(texto).splitlines() if l.startswith("#" * nivel + " ")]


def palabras(texto):
    return [t for t in sin_comentarios(texto).split() if re.search(r"\w", t)]


def filas(tabla_texto):
    """Filas de la primera tabla markdown del texto, sin cabecera ni separador."""
    lineas = [l for l in tabla_texto.splitlines() if l.strip().startswith("|")]
    celdas = [[c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))] for l in lineas]
    if len(celdas) < 2:
        return [], []
    return celdas[0], [c for c in celdas[2:]]


def es_texto(p):
    return p.suffix.lower() in TEXTO or p.name in {".gitignore", ".env.example", "README", "LICENSE"}


def ficheros(carpeta):
    for raiz, dirs, nombres in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in IGNORADAS]
        for n in nombres:
            yield Path(raiz) / n


def copia(carpeta):
    destino = Path(tempfile.mkdtemp(prefix="hk-eval-")) / Path(carpeta).name
    shutil.copytree(carpeta, destino, ignore=shutil.ignore_patterns(*IGNORADAS))
    return destino


def norm(s):
    return re.sub(r"\s+", " ", s.replace("`", "").replace("*", "")).strip().lower()


# ---------- A1 forma ----------

def a1(c):
    fallos, notas = [], []
    h = c / ".hackathon"

    an = h / "analisis.md"
    if an.exists():
        t = leer(an)
        if "**Reto:**" not in t:
            fallos.append("analisis.md sin línea **Reto:**")
        esperadas = ["Reto en una frase", "Qué hay que entregar", "Cómo se evalúa", "Restricciones",
                     "Recursos disponibles", "Ambigüedades", "Riesgos y trampas", "Qué distinguiría"]
        hs = encabezados(t, 3)
        faltan = [e for e in esperadas if not any(x.startswith(e) for x in hs)]
        if faltan:
            fallos.append(f"analisis.md sin secciones: {', '.join(faltan)}")
    else:
        fallos.append("falta .hackathon/analisis.md")

    for nombre, plantilla, maximo, opcionales in [
        ("plan.md", KIT / "skills/hack-plan/templates/plan.md", None, {"Descansos"}),
        ("pitch.md", KIT / "skills/hack-pitch/templates/pitch.md", 900, set()),
    ]:
        f = h / nombre
        if not f.exists():
            fallos.append(f"falta .hackathon/{nombre}")
            continue
        t = leer(f)
        hs = encabezados(t, 2)
        for e in encabezados(leer(plantilla), 2):
            if e not in hs:
                (notas if e in opcionales else fallos).append(f"{nombre} sin sección «{e}»")
        n = len(palabras(t))
        if nombre == "plan.md":
            # El plan se mide por persona: la sección de cada una cabe en una pantalla (unas 10 filas).
            # El total crece con el número de personas y solo se anota.
            bloques = re.split(r"\n(?=### )", seccion(t, "Por persona", 2) or "")[1:]
            filas_pp = []
            for b in bloques:
                quien = re.split(r"[(·]", b.splitlines()[0][4:])[0].strip()
                cab, fs = filas(b)
                filas_pp.append(f"{quien} {len(fs)}")
                if len(fs) > 10:
                    fallos.append(f"plan.md: {quien} con {len(fs)} filas (máx. 10 por persona)")
                i = next((k for k, x in enumerate(cab) if x.startswith("Tarea")), None)
                for fila in fs:
                    if i is not None and i < len(fila) and fila[i].count(";") >= 3:
                        notas.append(f"plan.md: bloque «{fila[1] if len(fila) > 1 else '?'}» con {fila[i].count(';') + 1} tareas separadas por «;» (C4)")
            notas.append(f"plan.md: {n} palabras, {len(bloques)} personas; filas por persona: {', '.join(filas_pp)}")
            continue
        (fallos if n > maximo else notas).append(f"{nombre}: {n} palabras (máx. {maximo})")

    cm = c / "CLAUDE.md"
    if cm.exists():
        n = len(leer(cm).splitlines())
        (fallos if n >= 100 else notas).append(f"CLAUDE.md: {n} líneas (máx. 99)")
    else:
        fallos.append("falta CLAUDE.md")

    reglas = sorted((c / ".claude/rules").glob("*.md"))
    if not 2 <= len(reglas) <= 4:
        fallos.append(f"{len(reglas)} reglas en .claude/rules (2–4)")
    for r in reglas:
        cuerpo = re.sub(r"^---.*?---", "", leer(r), count=1, flags=re.S)
        n = len(re.findall(r"^- ", cuerpo, flags=re.M))
        if not 2 <= n <= 10:
            fallos.append(f"regla {r.name}: {n} viñetas (2–10)")
    skills = list((c / ".claude/skills").glob("*/SKILL.md"))
    if not 1 <= len(skills) <= 3:
        fallos.append(f"{len(skills)} skills en .claude/skills (1–3)")
    ct = c / "docs/contratos.md"
    if ct.exists():
        bloques = re.split(r"\n(?=## )", leer(ct))[1:]
        for b in bloques:
            nombre = b.splitlines()[0][3:].strip()
            if "| Campo" not in b:
                fallos.append(f"contratos.md: «{nombre}» sin tabla de campos")
            if "```" not in b:
                fallos.append(f"contratos.md: «{nombre}» sin ejemplo")
        if not bloques:
            fallos.append("contratos.md sin contratos")
        notas.append(f"{len(bloques)} contratos")
    else:
        fallos.append("falta docs/contratos.md")
    notas.append(f"{len(reglas)} reglas, {len(skills)} skills")
    return (FALLA if fallos else PASA), fallos + notas


# ---------- A2 arranque ----------

def comando_arranque(c):
    readme = c / "README.md"
    if not readme.exists():
        return None
    s = seccion(leer(readme), "Arrancar", 2) or ""
    m = re.search(r"```[^\n]*\n(.+?)\n```", s, flags=re.S)
    return m.group(1).strip() if m else None


def parar(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def puerto_abierto(url):
    m = re.match(r"https?://([^:/]+):(\d+)", url)
    if not m:
        return False
    try:
        with socket.create_connection((m.group(1), int(m.group(2))), timeout=1):
            return True
    except OSError:
        return False


def urls_anunciadas(texto):
    urls = set(re.findall(r"https?://(?:localhost|127\.0\.0\.1):\d+[^\s'\"`»)]*", texto))
    # El servidor (uvicorn, vite…) imprime su raíz aunque el arranque anuncie otra ruta del mismo puerto:
    # si hay una URL más concreta con el mismo origen, la raíz sobra.
    return sorted(u for u in urls
                  if not any(o != u and o.startswith(u.rstrip("/") + "/") for o in urls))


def a2(c, espera=300):
    cmd = comando_arranque(c)
    if not cmd:
        return FALLA, ["README.md sin comando en «## Arrancar»"]
    tmp = copia(c)
    salida = []
    kw = {"start_new_session": True} if os.name != "nt" else {}
    proc = subprocess.Popen(cmd, shell=True, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    threading.Thread(target=lambda: [salida.append(l.decode("utf-8", "replace")) for l in proc.stdout],
                     daemon=True).start()
    detalle = [f"comando: `{cmd}` en una copia limpia ({tmp})"]
    inicio = time.time()
    urls = []
    while time.time() - inicio < espera and proc.poll() is None:
        urls = urls_anunciadas("".join(salida))
        if urls and all(puerto_abierto(u) for u in urls):
            break
        time.sleep(1)
    texto = "".join(salida)

    if proc.poll() is not None:  # una pieza sin servidor: termina sola
        ok = proc.returncode == 0 and "hola mundo" in texto.lower()
        detalle.append(f"terminó con código {proc.returncode} en {time.time() - inicio:.0f} s")
        if not ok:
            detalle.append("salida: " + texto.strip()[-400:])
        return (PASA if ok else FALLA), detalle

    if not urls:
        parar(proc)
        return FALLA, detalle + [f"tras {espera} s ni terminó ni mostró URLs", "salida: " + texto.strip()[-400:]]

    fallos, cuerpos = [], ""
    for u in urls:
        try:
            # Un servidor de desarrollo compila la página en la primera petición: margen amplio.
            with urllib.request.urlopen(u, timeout=120) as r:
                cuerpo = r.read().decode("utf-8", "replace")
                cuerpos += cuerpo
                detalle.append(f"{u} → HTTP {r.status}")
        except Exception as e:  # noqa: BLE001
            fallos.append(f"{u} no responde: {e}")
    if "hola mundo" not in cuerpos.lower():
        fallos.append("ninguna URL devuelve «hola mundo» en el HTML (una web que lo pinta con JS se revisa a mano)")
    parar(proc)
    time.sleep(3)
    vivos = [u for u in urls if puerto_abierto(u)]
    if vivos:
        fallos.append(f"tras pararlo siguen escuchando: {', '.join(vivos)}")
    detalle.append("no comprobado: que la web muestre lo que devuelve el motor (requiere navegador)")
    return (FALLA if fallos else PASA), fallos + detalle


# ---------- A3 codificación ----------

def a3(c):
    fallos, notas = [], []
    for f in ficheros(c):
        if not es_texto(f):
            continue
        datos = f.read_bytes()
        rel = f.relative_to(c).as_posix()
        if datos[:2] in (b"\xff\xfe", b"\xfe\xff"):
            fallos.append(f"{rel}: UTF-16")
            continue
        try:
            datos.decode("utf-8")
        except UnicodeDecodeError:
            fallos.append(f"{rel}: no es UTF-8")
            continue
        if datos.startswith(b"\xef\xbb\xbf"):
            notas.append(f"{rel}: UTF-8 con BOM")

    tmp = copia(c)
    (tmp / ".env").write_text("CLAVE=secreta\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp, capture_output=True)
    r = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=tmp, capture_output=True)
    if r.returncode == 0:
        notas.append("git ignora .env")
    else:
        fallos.append("git NO ignora .env (bloquea M5: puede exponer secretos)")
    return (FALLA if fallos else PASA), fallos + notas


# ---------- A4 trazas y cifras ----------

def etiqueta_mala(texto):
    """Fallo de la etiqueta de origen de una regla o viñeta, o None si es válida.

    Una ambigüedad es una pregunta: solo puede citarse como supuesto que hay que confirmar.
    El conocimiento externo del modelo tiene que pedir verificación."""
    for p in re.findall(r"\(([^()]*)\)", texto):
        p = p.lower()
        if "ambigüedad" in p and not ("supuesto" in p and "confirmar" in p):
            return f"cita una ambigüedad como fuente, no como supuesto: «({p})»"
        if "conocimiento externo" in p and "verificar" not in p:
            return f"conocimiento externo sin «verificar»: «({p})»"
    m = re.search(r"\(([^()]*)\)\W*$", texto)
    if not m or not any(o in m.group(1).lower() for o in ORIGENES):
        return "sin origen"
    return None


def a4(c):
    fallos, notas = [], []
    cm = c / "CLAUDE.md"
    reglas = seccion(leer(cm), "Reglas de equipo", 2) if cm.exists() else None
    if reglas is None:
        fallos.append("CLAUDE.md sin «## Reglas de equipo»")
    else:
        items = re.findall(r"^\d+\.\s+(.*)$", reglas, flags=re.M)
        for i, r in enumerate(items, 1):
            mal = etiqueta_mala(r)
            if mal:
                fallos.append(f"regla de equipo {i} {mal}: «{r[:80]}…»")
        notas.append(f"{len(items)} reglas de equipo")
    total = 0
    for r in sorted((c / ".claude/rules").glob("*.md")):
        for v in re.findall(r"^- (.*)$", re.sub(r"^---.*?---", "", leer(r), count=1, flags=re.S), flags=re.M):
            total += 1
            mal = etiqueta_mala(v)
            if mal:
                fallos.append(f"{r.name}: viñeta {mal}: «{v[:80]}…»")
    notas.append(f"{total} viñetas en .claude/rules")

    pitch, an = c / ".hackathon/pitch.md", c / ".hackathon/analisis.md"
    if not (pitch.exists() and an.exists()):
        return FALLA, fallos + ["faltan pitch.md o analisis.md"] + notas
    t = leer(pitch)
    tabla = seccion(t, "Cifras que hay que medir", 2) or ""
    _, fs = filas(tabla)
    # Una fila puede agrupar varias cifras («consumo en reposo / activo (mA)»): basta con que
    # todas las palabras de la cifra estén en el mismo hueco.
    huecos = [set(re.findall(r"\w+", norm(f[0]))) for f in fs if f]
    resto = t.replace(tabla, "")
    for cifra in re.findall(r"\[CIFRA:\s*([^\]]+)\]", resto):
        palabras_cifra = set(re.findall(r"\w+", norm(cifra)))
        if not any(palabras_cifra <= h for h in huecos):
            fallos.append(f"[CIFRA: {cifra}] sin fila en «Cifras que hay que medir»")

    evaluacion = norm(seccion(leer(an), "Cómo se evalúa", 3) or "")
    criterios = [l for l in evaluacion.splitlines() if l.strip()]
    peso_re = r"\d+(?:[.,]\d+)?\s*(?:%|puntos\b|pts\b|/\s*\d+\b)"
    if not re.search(peso_re, evaluacion):
        # Sin rúbrica publicada: los pesos no se comprueban (N/A), pero el pitch no puede inventarlos.
        guion = (seccion(t, "Guion", 2) or "")
        for p in re.findall(peso_re, guion):
            fallos.append(f"el análisis no publica pesos, pero el guion del pitch tiene «{p}» (peso de relleno)")
        notas.insert(0, "pesos: N/A, el análisis no publica rúbrica")
        return (FALLA if fallos else PASA), fallos + notas
    numero = r"(?<![\d.]){}(?!\d|[.,]\d)"
    cab, fs = filas(seccion(t, "Guion", 2) or "")
    i = next((k for k, x in enumerate(cab) if x.startswith("Criterio")), None)
    vistos = 0
    for fila in fs:
        if i is None or i >= len(fila):
            continue
        # «Nombre (peso)», separados por «;» o «·»; el peso puede ser libre («15 % del 60 %», «sin peso»).
        for m in re.finditer(r"([^;·()]+?)\s*\(([^)]*)\)", fila[i]):
            nombre, peso = norm(m.group(1)), m.group(2)
            vistos += 1
            lineas = [l for l in criterios if nombre in l]
            if not lineas:
                fallos.append(f"criterio del pitch «{m.group(1).strip()}» no aparece en «Cómo se evalúa»")
                continue
            cifras = re.findall(r"\+?\d+(?:[.,]\d+)?", peso)
            if not cifras:
                continue
            patron = numero.format(re.escape(cifras[0]))
            if any(re.search(patron, l) for l in lineas):
                continue
            if re.search(patron, evaluacion):
                notas.append(f"peso de «{m.group(1).strip()}» ({peso}): {cifras[0]} está en el análisis, "
                             f"pero no en la línea del criterio (revisar en C5)")
            else:
                fallos.append(f"peso de «{m.group(1).strip()}»: el pitch dice {peso}, el análisis no")
    notas.append(f"{vistos} menciones de criterio con peso en el guion")
    return (FALLA if fallos else PASA), fallos + notas


# ---------- A5 sin copia ----------

N = 8          # palabras seguidas iguales
CONTENIDO = 3  # palabras propias de un reto que debe tener el tramo copiado


def lineas_tokens(texto):
    """Tokens por línea: un tramo copiado no cruza saltos de línea (evita casar encabezados contiguos)."""
    return [re.findall(r"\w+", l.lower()) for l in sin_comentarios(texto).splitlines()]


def ngramas(texto):
    return {tuple(t[i:i + N]) for t in lineas_tokens(texto) for i in range(len(t) - N + 1)}


def a5(c, enunciado, refs):
    reto_id = re.match(r"(\d+)-", Path(enunciado).name)
    reto_id = reto_id.group(1) if reto_id else None
    corpus = {}
    for f in (KIT / "skills").glob("*/examples/*"):
        if not (reto_id and f.name.startswith(reto_id + "-")):
            corpus[f] = ngramas(leer(f))
    for ref in refs:
        for f in ficheros(Path(ref)):
            if es_texto(f):
                corpus[f] = ngramas(leer(f))
    # Las plantillas y los prompts se copian a propósito, y el enunciado es la fuente: se pueden repetir.
    kit = [*(KIT / "skills").glob("*/SKILL.md"), *(KIT / "skills").glob("*/templates/*")]
    permitidos = ngramas(leer(enunciado))
    vocabulario = set()
    for f in kit:
        permitidos |= ngramas(leer(f))
        vocabulario |= {t for l in lineas_tokens(leer(f)) for t in l}

    def propias(toks):
        # Palabras que no vienen del kit ni son cifras ni muy cortas: lo que hace concreto un tramo.
        return {t for t in toks if len(t) >= 4 and not any(ch.isdigit() for ch in t) and t not in vocabulario}

    salidas = [c / "CLAUDE.md", c / "README.md", *(c / ".claude").rglob("*.md"), *(c / ".hackathon").glob("*.md")]
    fallos = []
    for s in salidas:
        if not s.exists():
            continue
        for toks in lineas_tokens(leer(s)):
            i = 0
            while i <= len(toks) - N:
                g = tuple(toks[i:i + N])
                fuentes = [f for f, gs in corpus.items() if g in gs] if g not in permitidos else []
                if not fuentes:
                    i += 1
                    continue
                j = i + 1
                while (j <= len(toks) - N and tuple(toks[j:j + N]) in corpus[fuentes[0]]
                       and tuple(toks[j:j + N]) not in permitidos):
                    j += 1
                tramo = toks[i:j + N - 1]
                if len(propias(tramo)) >= CONTENIDO:
                    f = fuentes[0]
                    origen = f.relative_to(KIT).as_posix() if f.is_relative_to(KIT) else f
                    fallos.append(f"{s.relative_to(c).as_posix()} ← {origen}: «{' '.join(tramo)[:120]}»")
                i = j + N - 1
    notas = [f"comparado con {len(corpus)} ficheros" + ("" if refs else "; sin repositorio de referencia (--ref)")]
    if reto_id:
        notas.append(f"excluidos los ejemplos del propio reto ({reto_id}-*)")
    return (FALLA if fallos else PASA), fallos + notas


# ---------- A6 no sobrescribe ----------

def huellas(c):
    return {f.relative_to(c).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in ficheros(c)}


def a6(c, enunciado, stack):
    claude = shutil.which("claude")
    if not claude:
        return NA, ["no se encuentra el CLI de claude"]
    tmp = copia(c)
    pasos = [
        ("hack-scaffold", stack or "", set()),
        ("hack-plan", "", set()),
        ("hack-pitch", "", set()),
        ("hack-approaches", "", {".hackathon/enfoques.md"}),
        ("hack-analyze", str(Path(enunciado).resolve()), {".hackathon/analisis.md"}),
        # Sin «aplicar» y sin poder preguntar, /hack-check solo escribe su informe.
        ("hack-check", "", {".hackathon/verificacion.md"}),
    ]
    fallos, notas = [], [f"copia: {tmp}"]
    for cmd, arg, permitidos in pasos:
        antes = huellas(tmp)
        r = subprocess.run([claude, "-p", f"/{cmd} {arg}".strip(), "--plugin-dir", str(KIT),
                            "--permission-mode", "bypassPermissions", "--output-format", "json"],
                           cwd=tmp, capture_output=True, timeout=1200)
        despues = huellas(tmp)
        cambiados = sorted(k for k in antes if k in despues and antes[k] != despues[k] and k not in permitidos)
        borrados = sorted(k for k in antes if k not in despues)
        nuevos = sorted(k for k in despues if k not in antes)
        coste = re.search(rb'"total_cost_usd"\s*:\s*([\d.]+)', r.stdout)
        notas.append(f"/{cmd}: código {r.returncode}" + (f", {float(coste.group(1)):.2f} USD" if coste else ""))
        if cambiados or borrados:
            fallos.append(f"/{cmd} cambió {', '.join(cambiados + borrados)}")
        if nuevos:
            notas.append(f"/{cmd} creó {', '.join(nuevos)}")
    if not stack:
        notas.append("sin --stack, /hack-scaffold se para antes de mirar los ficheros")
    return (FALLA if fallos else PASA), fallos + notas


# ---------- A7 citas literales ----------

COMILLAS = "«»“”\"'‘’„"


def sin_comillas(s):
    return norm("".join(ch for ch in s if ch not in COMILLAS)).strip(" .,;:")


def a7(c, enunciado):
    """Cada cita de .hackathon/verificacion.md aparece literalmente en la fuente que nombra."""
    v = c / ".hackathon/verificacion.md"
    if not v.exists():
        return NA, ["sin .hackathon/verificacion.md (no se ha lanzado /hack-check)"]
    t = leer(v)
    fuentes = {"enunciado": leer(enunciado),
               "analisis.md": leer(c / ".hackathon/analisis.md") if (c / ".hackathon/analisis.md").exists() else "",
               "decision.md": leer(c / ".hackathon/decision.md") if (c / ".hackathon/decision.md").exists() else "",
               "criterios.md": leer(c / ".hackathon/criterios.md") if (c / ".hackathon/criterios.md").exists() else ""}
    textos = {k: sin_comillas(x) for k, x in fuentes.items()}
    fallos, notas, vistas = [], [], 0

    def comprobar(cita, fuente, donde):
        nonlocal vistas
        cita = cita.strip()
        if not cita or cita in {"—", "-"} or re.fullmatch(r"\([^()]*\)", cita):  # «(la misma)»: anotación
            return
        vistas += 1
        claves = [k for k in textos if k.split(".")[0] in fuente.lower()]
        clave = claves[0] if claves else None
        if clave is None:
            fallos.append(f"{donde}: fuente desconocida «{fuente}» para «{cita[:60]}»")
            return
        # Si la celda trae citas entrecomilladas, solo cuenta lo de dentro (fuera puede haber anotaciones);
        # si no, la celda entera. Varias citas se separan con « / ». «…» separa tramos literales.
        partes = re.findall(r"«+([^«»]+)»+|“([^”]+)”", cita)
        citas = [a or b for a, b in partes] or re.split(r"\s+/\s+", cita)
        for x in citas:
            tramos = [sin_comillas(y) for y in re.split(r"…|\.\.\.|\[…\]", x)]
            if not any(all(y in textos[k] for y in tramos if y) for k in claves):
                fallos.append(f"{donde}: cita no literal en {clave}: «{x[:100]}»")

    cab, fs = filas(seccion(t, "Afirmaciones", 2) or "")
    i = next((k for k, x in enumerate(cab) if x.lower().startswith("cita")), None)
    j = next((k for k, x in enumerate(cab) if x.lower().startswith("fuente")), None)
    veredictos = {}
    for fila in fs:
        if i is not None and j is not None and max(i, j) < len(fila):
            comprobar(fila[i], fila[j], "Afirmaciones")
        if len(fila) > 2:
            ver = re.sub(r"\W+$", "", norm(fila[2]).split()[0]) if fila[2].strip() else "?"
            veredictos[ver] = veredictos.get(ver, 0) + 1
    for titulo in ("Bloqueantes", "Cobertura de la rúbrica"):
        cab, fs = filas(seccion(t, titulo, 2) or "")
        k = next((n for n, x in enumerate(cab) if "cita" in x.lower()), None)
        for fila in fs:
            if k is not None and k < len(fila):
                # Una condición puede venir del enunciado o de una nota del jurado (criterios.md, M6b).
                comprobar(fila[k], "enunciado criterios", titulo)
    notas.append(f"{vistas} citas comprobadas; veredictos: "
                 + ", ".join(f"{k} {n}" for k, n in sorted(veredictos.items())))
    return (FALLA if fallos else PASA), fallos + notas


# ---------- main ----------

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("carpeta")
    p.add_argument("--enunciado", required=True, help="fichero del reto en evals/retos/")
    p.add_argument("--ref", action="append", default=[], help="repositorio de referencia (A5)")
    p.add_argument("--sin-arranque", action="store_true", help="no ejecuta A2")
    p.add_argument("--relanzar", action="store_true", help="ejecuta A6 (cinco llamadas a claude -p)")
    p.add_argument("--stack", help="stack para relanzar /hack-scaffold, p. ej. «python con uv»")
    a = p.parse_args()
    c = Path(a.carpeta).resolve()

    comprobaciones = [
        ("A1", "Forma: secciones y tamaños", lambda: a1(c)),
        ("A2", "Arranque desde cero", (lambda: (NA, ["--sin-arranque"])) if a.sin_arranque else (lambda: a2(c))),
        ("A3", "Codificación", lambda: a3(c)),
        ("A4", "Trazas y cifras", lambda: a4(c)),
        ("A5", "Sin copia", lambda: a5(c, a.enunciado, a.ref)),
        ("A6", "No sobrescribe sin preguntar",
         (lambda: a6(c, a.enunciado, a.stack)) if a.relanzar else (lambda: (NA, ["sin --relanzar"]))),
        ("A7", "Citas literales de /hack-check", lambda: a7(c, a.enunciado)),
    ]
    print(f"# Comprobaciones automáticas · {c.name}\n")
    print("| # | Comprobación | Resultado | Evidencia |\n|---|---|---|---|")
    detalles, falla = [], False
    for clave, nombre, fn in comprobaciones:
        try:
            res, det = fn()
        except Exception as e:  # noqa: BLE001
            res, det = FALLA, [f"error del script: {e!r}"]
        falla |= res == FALLA
        print(f"| {clave} | {nombre} | {res} | {det[0] if det else ''} |")
        detalles.append((clave, det))
    print()
    for clave, det in detalles:
        print(f"## {clave}")
        for d in det:
            print(f"- {d}")
        print()
    sys.exit(1 if falla else 0)


if __name__ == "__main__":
    main()
