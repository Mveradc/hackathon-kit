# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterio 5 de M8f (R-28, constitución IV): las tres vistas coinciden en estados, dueños, colisiones y antigüedades.

Para cada guion G1–G6 (estado calculado por el relay de verdad a partir de los eventos del guion, con las tareas del
plan del 03; en G5 y G6, con las colisiones que calcula el relay desde M8g, criterio 7 de M8g) y para el estado
sintético de 5 personas y 20 tareas con colisiones puestas a mano (fixture.py, que el relay sirve tal cual):
  - web: lo que el relay sirve en GET /v1/vista por HTTP (lo que pinta hkos/web/index.html);
  - estado-equipo.md: lo escribe el demonio de verdad (hkos/agente.py), que pide GET /v1/estado al relay, una vez por
    persona del equipo;
  - MCP: hkos/mcp.py por stdio sobre lo que deja el demonio (`tarea` de cada ID y `colisiones` sin filtrar).
Desde M10 (K-105, criterio 4; nota de ADR-0009), también G13 (jurado) y G14 (ruta), con el relay de verdad y sus
interruptores (m10.py): los bloques `jurado` y `ruta` enteros son los mismos en la vista del relay, en la del demonio
(/v1/vista) y en el MCP (`jurado`, `ruta`, con la misma hora), y la línea de «Jurado y ruta» de estado-equipo.md es el
`resumen` del bloque, con su hora, su fuente y «viejo». En G1–G6 y G12 (sin los bloques), ni la sección ni las firmas.
Issue #77, A3: en cada bloque `ruta` con estimación, el resumen dice «fin hacia» si y solo si temprano y tarde se
escriben con la misma HH:MM en la zona del equipo (ajuste 5, punto 2 de ADR-0013), la regla con que la web elige
«hacia» o «entre» (Ruta.jsx; m10.test.jsx). Y G15, el caso del issue: dos instantes distintos del mismo minuto.

Uso: uv run --no-project evals/coordinacion/simulador/igualdad.py   (0 OK · 1 falla)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path[:0] = [os.path.join(KIT, "hkos"), AQUI]
import agente as agente_mod  # noqa: E402
import m10  # noqa: E402
import mcp as mcp_mod  # noqa: E402
import proyeccion  # noqa: E402
import relay as relay_mod  # noqa: E402
import ruta as ruta_mod  # noqa: E402
from esquema import Esquema  # noqa: E402
from fixture import estado_5x20  # noqa: E402
import g12  # noqa: E402
from red import Servidor  # noqa: E402
from simula import carga, contratos_de, montar  # noqa: E402

DE_ETIQUETA = {v: k for k, v in proyeccion.ETIQUETAS.items()}
fallos = 0


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(("OK    " if ok else "FALLO ") + nombre + ("" if ok or not detalle else f"\n        {detalle}"))


class SondeoFijo:
    """Hace de sondeo de GitHub del relay con las tareas del guion (lo que daría hkos/github.py tras compilar)."""

    def __init__(self, tareas, issues, visto):
        self.tareas, self.issues, self.ultimo_ok, self.estado = tareas, issues, visto, "ok"

    def resultado(self, ahora):
        return self.tareas, self.issues, [], 0


def hhmm(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%H:%M")


def de_la_web(url, token):
    req = urllib.request.Request(url + "/v1/vista", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())["vista"]


def mcp(repo, ids):
    msgs = [{"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": "tarea", "arguments": {"id": t}}}
            for i, t in enumerate(ids)]
    msgs.append({"jsonrpc": "2.0", "id": "col", "method": "tools/call",
                 "params": {"name": "colisiones", "arguments": {"mias": False}}})
    r = subprocess.run([sys.executable, os.path.join(KIT, "hkos", "mcp.py"), "--repo", repo],
                       input="".join(json.dumps(m) + "\n" for m in msgs).encode(), capture_output=True, timeout=60)
    salida = {x["id"]: json.loads(x["result"]["content"][0]["text"]) for x in map(json.loads, r.stdout.decode().splitlines())}
    tareas = {salida[i]["tarea"]["id"]: salida[i]["tarea"] for i in range(len(ids))}
    return tareas, salida["col"]["colisiones"]


def secciones(md):
    sec, salida = None, {}
    for l in md.splitlines():
        if l.startswith("## "):
            sec = l[3:]
            salida[sec] = []
        elif sec and l.startswith("- "):
            salida[sec].append(l)
    return salida


def mcp_estado(repo):
    """El texto de la herramienta `estado` del MCP (el estado-equipo.md de la persona del clon)."""
    m = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "estado", "arguments": {}}}
    r = subprocess.run([sys.executable, os.path.join(KIT, "hkos", "mcp.py"), "--repo", repo],
                       input=(json.dumps(m) + "\n").encode(), capture_output=True, timeout=60)
    return json.loads(r.stdout.decode().splitlines()[0])["result"]["content"][0]["text"]


def sin_viejo(s):
    """El bloque `servicios` de la vista sin el `viejo` que le añade proyeccion.vista (decisión 1 del PR #13): lo
    demás va tal cual desde estado.json."""
    s = json.loads(json.dumps(s))
    for x in [x.get("comprobado") for x in s["lista"]] + [x.get("resultado") for x in s["conexiones"]] + s["desajustes"]:
        if x:
            x.pop("viejo", None)
    return s


def servicios_esperados(web, persona):
    """Lo que la sección «Servicios» del md de la persona tiene que decir, sacado de los campos de la web (api.md §6):
    [(grupo, principio del texto, HH:MM, fuente, viejo)], en el orden de la sección."""
    s = web["servicios"]
    no_cuadra, sin, fuera = [], [], []
    for d in s["desajustes"]:
        cuando = (hhmm(d["observado_en"]), d["fuente"], d["viejo"])
        if d["tipo"] == "codigo_fuera":
            fuera.append(("fuera de servicios", d["rutas"][0]) + cuando)
        elif persona in d["personas"] or not d["personas"]:
            no_cuadra.append(("no cuadra", d["detalle"]) + cuando)
    for tipo, x, nombre in [("servicio", x, x["nombre"]) for x in s["lista"]] + \
                           [("conexión", x, f"{x['de']} → {x['a']}") for x in s["conexiones"]]:
        c = x["confirmacion"]
        if c["valor"] == "sin_confirmar" and persona in c["faltan"]:
            sin.append(("sin confirmar", f"{tipo} «{nombre}»", hhmm(c["observado_en"]), c["fuente"], False))
    for p in s["propuestas"]:
        if persona in p.get("duenos", []) and p.get("autor_git") != persona:
            c = p["campos"]
            nombre = f"servicio «{c['nombre']}»" if p["tipo"] == "servicio" else f"conexión «{c['de']} → {c['a']}»"
            sin.append(("sin confirmar", f"propuesta de {nombre}", hhmm(p["observado_en"]), "git", False))
    return no_cuadra + sin + fuera


def lineas_jr(web):
    """Lo que la sección «Jurado y ruta» del md tiene que decir, sacado de los bloques de la web (api.md §6, M10): el
    `resumen` de cada bloque, con su hora, su fuente y «viejo»."""
    return [f"- {b['resumen']} ({hhmm(b['observado_en'])} · {b['fuente']}" + (" · viejo" if b["viejo"] else "") + ")"
            for b in (web.get("jurado"), web.get("ruta")) if b]


def rango_como_en_la_web(nombre, ruta):
    """Issue #77, A3: «fin hacia» en el resumen si y solo si temprano y tarde dan la misma HH:MM en la zona del equipo,
    la que usa la web (zonaRuta: la `zona` del bloque o, sin ella, el desfase de la entrega)."""
    est = ruta.get("estimacion")
    if not est or " · fin " not in ruta["resumen"]:
        return
    tz = ruta_mod._zona({"zona": ruta["zona"], "entrega": ruta["objetivo"]})
    hm = [datetime.fromisoformat(est[k].replace("Z", "+00:00")).astimezone(tz).strftime("%H:%M")
          for k in ("temprano", "tarde")]
    comprueba(f"{nombre}: «fin hacia» en el resumen si y solo si temprano y tarde son la misma HH:MM en la zona del "
              f"equipo, como en la web ({hm[0]}, {hm[1]})", (" · fin hacia " in ruta["resumen"]) == (hm[0] == hm[1]),
              ruta["resumen"])


def estado_g15():
    """Issue #77, A3: ana con tres medidas (30 %, 60 % y 90 % de 60 min) y T04 abierta con 1 min de franja, a las 10:00
    de Madrid: temprano 08:00:18Z y tarde 08:00:54Z, distintos pero los dos «10:00»."""
    t0 = datetime(2026, 9, 19, 8, 0, tzinfo=timezone.utc)
    obs = "2026-09-18T17:00:00Z"

    def m(n):
        return (t0 + timedelta(seconds=round(60 * n))).astimezone(timezone(timedelta(hours=2))).isoformat()

    def dato(valor):
        return {"valor": valor, "fuente": "git", "observado_en": obs, "declarado": True}

    def declarada(valor, texto):
        return {"valor": valor, "texto": texto, "motivo": None, "donde": "equipo.md", "fuente": "git",
                "observado_en": obs, "declarado": True}

    def tarea(tid, orden, desde, hasta, primera=None, hecha=None):
        e = "publicada" if hecha is not None else "lista"
        return {"id": tid, "titulo": f"Tarea {tid}", "dueno": "ana", "depende_de": [], "declarado": None,
                "estado": {"valor": e, "fuente": "git" if hecha is not None else "derivado",
                           "observado_en": m(hecha if hecha is not None else -1)},
                "hasta": {"valor": m(hasta), "texto": "sáb", "motivo": None, "fuente": "git", "observado_en": obs,
                          "declarado": True},
                "franja": {"valor": {"desde": m(desde), "hasta": m(hasta), "compartida": 1, "min": hasta - desde},
                           "motivo": None, "fuente": "derivado", "observado_en": obs, "declarado": True},
                "orden_plan": dato(orden),
                "historia": {"primera_senal": m(primera) if primera is not None else None,
                             "hecha_en": m(hecha) if hecha is not None else None, "trabajo_nuevo_desde": None,
                             "ultima_senal": m(-1), "fuente": "derivado", "observado_en": m(-1)}}
    tareas = [tarea(f"T0{i + 1}", i + 1, -180 + 60 * i, -120 + 60 * i, -400 + 40 * i, -400 + 40 * i + 18 * (i + 1))
              for i in range(3)] + [tarea("T04", 4, 0, 1)]
    ahora = iso_utc(t0)
    return {"v": 1, "generado_en": ahora,
            "fuentes": {"relay": {"valor": "ok", "fuente": "derivado", "observado_en": ahora}},
            "personas": [{"persona": "ana", "nombre": "Ana", "actores": []}], "tareas": tareas, "colisiones": [],
            "ruta": {"equipo": dato("ok"), "zona": dato("Europe/Madrid"),
                     "inicio": declarada("2026-09-18T19:00:00+02:00", "2026-09-18 19:00 (Europe/Madrid)"),
                     "entrega": declarada(m(240), "entrega"), "otras_entregas": [], "hitos": [], "descansos": []}}


def iso_utc(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def herramientas(repo):
    """Los nombres de tools/list del MCP de verdad, por stdio."""
    m = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    r = subprocess.run([sys.executable, os.path.join(KIT, "hkos", "mcp.py"), "--repo", repo],
                       input=(json.dumps(m) + "\n").encode(), capture_output=True, timeout=60)
    return [t["name"] for t in json.loads(r.stdout.decode().splitlines()[0])["result"]["tools"]]


def comparar_m10(nombre, web, repo, persona):
    """M10 (criterio 4): los bloques enteros en la vista del relay (la web), la del demonio (/v1/vista) y el MCP, con la
    misma hora (la de la web)."""
    a = agente_mod.Agente(repo, persona, 30, ahora=lambda: web["ahora"])
    a.recibir_estado()
    demonio = json.loads(json.dumps(a.vista_web()["vista"]))
    fuente = mcp_mod.Fuente(repo, ahora=lambda: web["ahora"])
    for k in ("jurado", "ruta"):
        if k not in web:
            continue
        r = mcp_mod.responder(fuente, {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                       "params": {"name": k, "arguments": {}}})["result"]
        del_mcp = json.loads(r["content"][0]["text"]) if not r["isError"] else {}
        comprueba(f"{nombre}: el bloque «{k}» entero, igual en la vista del relay, en la del demonio y en el MCP",
                  web[k] == demonio.get(k) == del_mcp.get(k) and del_mcp.get("generado_en") == web["generado_en"],
                  r["content"][0]["text"][:200])


def comparar(nombre, url, token, repo, personas, estado=None):
    web = de_la_web(url, token)
    if estado is not None and estado.get("servicios"):
        comprueba(f"{nombre}: la web trae los servicios de estado.json, campo a campo (más su «viejo»)",
                  sin_viejo(web["servicios"]) == estado["servicios"])
        viejos = [d["viejo"] for d in web["servicios"]["desajustes"]]
        comprueba(f"{nombre}: hay desajustes viejos y otros que no ({viejos})", True in viejos and False in viejos)
        declaradas = {t["id"] for t in estado["tareas"] if t["estado"].get("declarado")}
        en_web = {t["id"] for c in web["columnas"].values() for t in c if t.get("estado_declarado")}
        comprueba(f"{nombre}: las tareas declaradas (reclamadas desde la web) lo son también en la web ({sorted(declaradas)})",
                  declaradas == en_web and bool(declaradas), f"{sorted(en_web)}")
    tarjetas = {t["id"]: t for c in web["columnas"].values() for t in c}
    # Web frente a MCP: estado, dueño y antigüedad (observado_en) de cada tarea; colisiones enteras.
    a = agente_mod.Agente(repo, personas[0], 30)
    a.tz = timezone.utc
    a.recibir_estado()
    tareas_mcp, col_mcp = mcp(repo, sorted(tarjetas))
    dif = [tid for tid, t in tarjetas.items()
           if (t["estado"], t["dueno"], t["observado_en"]) != (tareas_mcp[tid]["estado"]["valor"], tareas_mcp[tid]["dueno"],
                                                               tareas_mcp[tid]["estado"]["observado_en"])]
    comprueba(f"{nombre}: web y MCP, mismos estados, dueños y antigüedades en las {len(tarjetas)} tareas", not dif, str(dif))
    comprueba(f"{nombre}: web y MCP, mismas colisiones ({len(web['colisiones'])})", col_mcp == web["colisiones"],
              f"{col_mcp} / {web['colisiones']}")
    # Web frente al md de cada persona (lo escribe su demonio): «Tu trabajo», «Colisiones que te afectan» y la línea
    # de cada persona en «Equipo».
    for persona in personas:
        a = agente_mod.Agente(repo, persona, 30, ahora=lambda: web["ahora"])   # el «viejo» con la hora de la web
        a.tz = timezone.utc
        a.recibir_estado()
        a.escribir_md(True)
        with open(os.path.join(a.dir, "estado-equipo.md"), encoding="utf-8") as f:
            md = f.read()
        sec = secciones(md)
        jr, cabecera = lineas_jr(web), md.splitlines()[0]
        if jr:                                         # M10 (K-105): una línea por bloque, el `resumen`
            firmas = proyeccion.firmas(web, persona)
            comprueba(f"{nombre}, md de @{persona}: «Jurado y ruta» = el resumen de cada bloque de la web ({len(jr)}), "
                      "y sus firmas en la cabecera", sec.get("Jurado y ruta") == jr and all(
                          f",{k}:{firmas[k]}" in cabecera for k in ("jurado", "ruta") if k in web),
                      f"{sec.get('Jurado y ruta')} / {jr}")
        else:
            comprueba(f"{nombre}, md de @{persona}: sin bloques en la vista, ni «Jurado y ruta» ni las firmas jurado: y "
                      "ruta:", "Jurado y ruta" not in sec and not re.search(r",(jurado|ruta):", cabecera))
        mias = sorted((t for t in tarjetas.values() if t["dueno"] == persona and t["estado"] in proyeccion.TRABAJO),
                      key=lambda t: (proyeccion.TRABAJO.index(t["estado"]), t["id"]))
        esperado = [(t["id"], t["estado"], hhmm(t["observado_en"]), t["fuente"], bool(t.get("estado_declarado")))
                    for t in mias]
        real = []
        for l in sec.get("Tu trabajo", []):
            m = re.match(r"^- (T\d{2,3}) «.*?» · (.+?) \((\d\d:\d\d) · ([a-z]+)(?: · viejo)?( · declarado)?\)", l)
            if m:
                real.append((m.group(1), DE_ETIQUETA.get(m.group(2), m.group(2)), m.group(3), m.group(4),
                             bool(m.group(5))))
        comprueba(f"{nombre}, md de @{persona}: «Tu trabajo» = sus tareas abiertas de la web ({len(esperado)})",
                  real == esperado, f"{real} / {esperado}")
        col_web = [(c["gravedad"].upper(), c["nivel"], sorted(c["personas"]), hhmm(c["observado_en"]))
                   for c in web["colisiones"] if persona in c["personas"]]
        col_md = []
        for l in sec.get("Colisiones que te afectan", []):
            m = re.match(r"^- (ROJO|AMARILLO) · nivel (\S+) · .* · ((?:@[\w-]+(?:, )?)+) \((\d\d:\d\d)\)$", l)
            if m:
                col_md.append((m.group(1), m.group(2), sorted(p.strip()[1:] for p in m.group(3).split(",")), m.group(4)))
        comprueba(f"{nombre}, md de @{persona}: sus colisiones como en la web ({len(col_web)})", col_md == col_web,
                  f"{col_md} / {col_web}")
        equipo_md = {}
        for l in sec.get("Equipo", []):
            m = re.match(r"^- @([\w-]+) \(", l)
            if m:
                equipo_md[m.group(1)] = sorted(re.findall(r"(T\d{2,3}) ", l))
        equipo_web = {p["persona"]: sorted(p["haciendo"][:4]) for p in web["personas"] if p["persona"] != persona}
        comprueba(f"{nombre}, md de @{persona}: «Equipo», lo que hace cada una como en la web", equipo_md == equipo_web,
                  f"{equipo_md} / {equipo_web}")
        if web.get("servicios"):                       # M9a (K-97): «Servicios», con los campos de la web
            esperado = servicios_esperados(web, persona)
            real = []
            for l in sec.get("Servicios", []):
                m = re.match(r"^- (no cuadra|sin confirmar|fuera de servicios) · (.*) \((\d\d:\d\d) · ([a-z]+)( · viejo)?\)$", l)
                if m:
                    real.append(m.groups()[:4] + (bool(m.group(5)),))
            ok = len(real) == len(esperado) and all(r[0] == e[0] and r[1].startswith(e[1]) and r[2:] == e[2:]
                                                   for r, e in zip(real, esperado))
            comprueba(f"{nombre}, md de @{persona}: «Servicios» como en la web ({len(esperado)} líneas)", ok,
                      f"{real} / {esperado}")
            texto = mcp_estado(repo)
            comprueba(f"{nombre}, MCP de @{persona}: `estado` trae la misma sección «Servicios»",
                      secciones(texto).get("Servicios") == sec.get("Servicios"))
        elif "Servicios" in sec:
            comprueba(f"{nombre}, md de @{persona}: sin servicios en el estado, sin sección «Servicios»", False)
        if jr:
            comprueba(f"{nombre}, MCP de @{persona}: `estado` trae la misma sección «Jurado y ruta»",
                      secciones(mcp_estado(repo)).get("Jurado y ruta") == sec.get("Jurado y ruta"))
    if web.get("ruta"):
        rango_como_en_la_web(nombre, web["ruta"])
    if web.get("jurado") or web.get("ruta"):
        comparar_m10(nombre, web, repo, personas[0])


def main():
    tmp = tempfile.mkdtemp(prefix="hk-igualdad-")
    try:
        repo = os.path.join(tmp, "clon").replace("\\", "/")
        subprocess.run(["git", "init", "-q", repo], check=True)
        os.makedirs(os.path.join(repo, ".git", "hackathon", "os"), exist_ok=True)
        for g in ("G1", "G2", "G3", "G4", "G5", "G6"):
            guion = carga(os.path.join(AQUI, "guiones", f"{g}.json"))
            tareas, personas, issues, eventos, ts = montar(guion, AQUI)
            contratos = contratos_de(guion, AQUI)
            for punto in guion["esperado"]:
                ahora = ts(punto["tras"])
                r = relay_mod.Relay(os.path.join(tmp, f"relay-{g}-{punto['tras']}"), personas, ahora=lambda a=ahora: a,
                                    sondeo=SondeoFijo(tareas, issues, datetime.fromisoformat(ahora.replace("Z", "+00:00")).timestamp()),
                                    umbral_parada_s=guion.get("umbral_parada_s", 1200), contratos=contratos)
                vistos = [e for e in eventos if e["ts"] <= ahora]
                for i in range(0, len(vistos), 200):
                    r.recibir({"eventos": vistos[i:i + 200]})
                r.recalcular()
                servir_y_comparar(f"{g} (t={punto['tras']} s)", r, repo, [p["persona"] for p in personas])
        e = estado_5x20()
        err = Esquema("estado.schema.json").error(e)
        comprueba("fixture de 5 personas y 20 tareas: valida contra estado.schema.json", err is None, str(err))
        r = relay_mod.Relay(os.path.join(tmp, "relay-fixture"), [], ahora=lambda: e["generado_en"])
        with r.lock:
            r.estado, r.vista, r.version = e, proyeccion.vista(e), r.version + 1
            r.texto = json.dumps(e, ensure_ascii=False).encode("utf-8")
        servir_y_comparar("5 personas y 20 tareas", r, repo, [p["persona"] for p in e["personas"]])
        # G12 (M9a, K-97): servicios calculados por el relay de verdad (web_nueva) desde un repo con su historia.
        repo_g12, eventos = g12.montar(tmp)
        nov = relay_mod.Novedades(repo_g12, 300, web_nueva=True)
        nov.sondear()
        visto = datetime.fromisoformat(g12.AHORA.replace("Z", "+00:00")).timestamp()
        r = relay_mod.Relay(os.path.join(tmp, "relay-g12"), g12.PERSONAS, ahora=lambda: g12.AHORA,
                            sondeo=SondeoFijo(g12.TAREAS, g12.ISSUES, visto), novedades=nov, web_nueva=True)
        r.recibir({"eventos": eventos})
        r.recalcular()
        comprueba("G12: estado.json con servicios, que valida contra estado.schema.json",
                  "servicios" in r.estado and Esquema("estado.schema.json").error(r.estado) is None,
                  str(Esquema("estado.schema.json").error(r.estado)))
        servir_y_comparar("G12 (servicios)", r, repo, [p["persona"] for p in g12.PERSONAS], estado=r.estado)
        # M10 (K-105): G13 y G14 con los dos interruptores, por el relay de verdad (m10.py). El MCP solo lista jurado y
        # ruta con su interruptor en el os.md de la copia principal (issue #46, ajuste 7).
        base = ["estado", "tarea", "colisiones", "reservar", "liberar"]
        comprueba("MCP sin vista_jurado ni ruta_critica: tools/list, el de la 0.4.0", herramientas(repo) == base)
        os.makedirs(os.path.join(repo, ".hackathon"), exist_ok=True)
        with open(os.path.join(repo, ".hackathon", "os.md"), "w", encoding="utf-8") as f:
            f.write("activa: sí\nvista_jurado: sí\nruta_critica: sí\n")
        comprueba("MCP con vista_jurado: sí y ruta_critica: sí: tools/list, más jurado y ruta",
                  herramientas(repo) == base + ["jurado", "ruta"])
        g13 = carga(os.path.join(AQUI, "guiones", "G13.json"))
        h13 = carga(os.path.join(AQUI, g13["hechos"]))
        for mo in h13["momentos"]:
            r = m10.relay(tmp, g13, m10.versiones_g13(g13, h13, mo["ahora"]), mo["ahora"])
            servir_y_comparar(f"G13 ({mo['nombre']})", r, repo, [p["persona"] for p in r.personas])
        h14 = carga(os.path.join(AQUI, "guiones", "g14", "hechos.json"))
        for mo in h14["momentos"]:
            g14 = carga(os.path.join(AQUI, "guiones", mo["guion"]))
            versiones = m10.versiones_g14(h14, mo["ahora"])
            plan = [f["plan.md"] for _, f in versiones if "plan.md" in f][-1]
            r = m10.relay(tmp, g14, versiones, mo["ahora"], tareas=m10.tareas_del_plan(g14, plan))
            servir_y_comparar(f"G14 ({mo['nombre']})", r, repo, [p["persona"] for p in r.personas])
        # G15 (issue #77, A3): el rango sin anchura, con dos instantes distintos del mismo minuto.
        e = estado_g15()
        err = Esquema("estado.schema.json").error(e)
        comprueba("G15 (#77, A3): valida contra estado.schema.json", err is None, str(err))
        r = relay_mod.Relay(os.path.join(tmp, "relay-g15"), [], ahora=lambda: e["generado_en"])
        with r.lock:
            r.estado, r.vista, r.version = e, proyeccion.vista(e), r.version + 1
            r.texto = json.dumps(e, ensure_ascii=False).encode("utf-8")
        est = r.vista["ruta"]["estimacion"]
        comprueba("G15 (#77, A3): temprano y tarde distintos, del mismo minuto",
                  [iso_utc(datetime.fromisoformat(est[k].replace("Z", "+00:00"))) for k in ("temprano", "tarde")]
                  == ["2026-09-19T08:00:18Z", "2026-09-19T08:00:54Z"], str(est))
        servir_y_comparar("G15 (#77, A3: rango sin anchura)", r, repo, ["ana"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{fallos} fallos")
    return 1 if fallos else 0


def servir_y_comparar(nombre, r, repo, personas, estado=None):
    srv = Servidor(("127.0.0.1", 0), relay_mod.manejador(r))
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        d = os.path.join(repo, ".git", "hackathon", "os")
        for n, v in (("relay.url", url), ("token", r.token)):
            with open(os.path.join(d, n), "w") as f:
                f.write(v + "\n")
        comparar(nombre, url, r.token, repo, personas, estado)
    finally:
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    sys.exit(main())
