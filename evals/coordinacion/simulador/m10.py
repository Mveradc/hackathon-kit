"""G13 y G14 (M10, K-105) con el código de verdad: los ficheros de cada guion en un repo de git con su historia (un
remoto bare temporal y el clon del relay), hkos/relay.py con sus interruptores (lee origin/main con hkos/lecturas.py y
reconstruye la historia de cada tarea desde los eventos) y proyeccion.vista, que añade los bloques `jurado` y `ruta`
(hkos/jurado.py y hkos/ruta.py). Lo usan g13_g14.py (criterios 2 y 3 de M10: cada bloque, con la forma de los hechos) e
igualdad.py (criterio 4: la vista, estado-equipo.md y el MCP).

Sin red, sin GitHub y sin modelo: el sondeo de GitHub es el de las tareas del guion y los commits llevan la hora de los
hechos (`en_main_desde`).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path[:0] = [os.path.join(KIT, "hkos"), AQUI]
import proyeccion  # noqa: E402
import relay as relay_mod  # noqa: E402
from compilar import leer_plan  # noqa: E402
from estados import fecha  # noqa: E402
from simula import carga, montar  # noqa: E402

RUTAS = {"criterios.md": ".hackathon/criterios.md", "plan.md": ".hackathon/plan.md", "pitch.md": ".hackathon/pitch.md",
         "equipo.md": ".hackathon/equipo.md", "servicios.md": ".hackathon/servicios.md"}
NOTA = re.compile(r"^## \d{4}-\d\d-\d\d \d\d:\d\d · ", re.M)
# G13 no trae equipo.md propio: la zona de las notas (api.md §11.2, B4) es la del equipo del reto 03, la de G14.
EQUIPO_G13 = "guiones/g14/equipo-2.md"
# Las palabras de los hechos de G14 (g13_g14.TEXTO_MOTIVO y FUERA) para los motivos del contrato.
TEXTO_MOTIVO = {"relativo_sin_inicio": "sin Inicio", "sin_inicio": "sin Inicio", "por_confirmar": "plazo sin resolver",
                "vacio": "vacío", "sin_zona": "sin zona", "formato": "formato", "orden": "franja al revés"}
FUERA = {"condicional": "empieza por «Si …»", "si_da_tiempo": "lleva [SI DA TIEMPO]"}


def texto(rel):
    with open(os.path.join(AQUI, rel), encoding="utf-8") as f:
        return f.read()


def z(x):
    return fecha(x).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if x else None


def epoca(iso):
    return fecha(iso).timestamp()


class Sondeo:
    """El sondeo de GitHub del relay con las tareas del guion (como igualdad.SondeoFijo)."""

    def __init__(self, tareas, issues, visto):
        self.tareas, self.issues, self.ultimo_ok, self.estado = tareas, issues, visto, "ok"

    def resultado(self, ahora):
        return self.tareas, self.issues, [], 0


def _git(cwd, *args, cuando=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="guion", GIT_AUTHOR_EMAIL="guion@example.com", GIT_COMMITTER_NAME="guion",
               GIT_COMMITTER_EMAIL="guion@example.com")
    if cuando:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = cuando
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, encoding="utf-8", check=True,
                          env=env).stdout.strip()


def repo(base, versiones):
    """El clon del relay, con origin/main = la historia de `versiones` ([(hora, {nombre: texto})], en orden: cada una, un
    commit con esos ficheros a esa hora). Un remoto bare temporal y su clon, como el relay de verdad."""
    trabajo, bare, clon = (os.path.join(base, n) for n in ("trabajo", "remoto.git", "clon"))
    os.makedirs(os.path.join(trabajo, ".hackathon"))
    _git(trabajo, "init", "-q", "-b", "main")
    for cuando, ficheros in versiones:
        for nombre, contenido in ficheros.items():
            with open(os.path.join(trabajo, RUTAS[nombre]), "w", encoding="utf-8", newline="\n") as f:
                f.write(contenido)
        _git(trabajo, "add", "-A")
        _git(trabajo, "commit", "-q", "--allow-empty", "-m", f"guion {cuando}", cuando=cuando)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True, capture_output=True)
    _git(trabajo, "push", "-q", bare, "main")
    subprocess.run(["git", "clone", "-q", bare, clon], check=True, capture_output=True)
    return clon


def criterios_hasta(md, notas, ahora):
    """criterios.md con las notas que ya estaban en main a `ahora` (cada una llega en su en_main_desde), en su orden. Las
    que no están en los hechos (las que añade un caso) ya están."""
    partes = NOTA.split(md)
    salida = partes[0]
    for i, (cab, cuerpo) in enumerate(zip(NOTA.findall(md), partes[1:])):
        if i >= len(notas) or fecha(notas[i]["en_main_desde"]) <= fecha(ahora):
            salida += cab + cuerpo
    return salida


def versiones_g13(guion, hechos, ahora, cambia=None):
    """Las versiones de G13 hasta `ahora`: el equipo y el pitch, cada nota en su en_main_desde y el plan con etiquetas.
    cambia(nombre, texto) -> texto: los reemplazos de un caso."""
    cambia = cambia or (lambda n, t: t)
    ent, hn = guion["entradas"], hechos["notas"]
    crit = cambia("criterios.md", texto(ent["criterios.md"]))
    horas = {h["en_main_desde"] for h in hn} | {hechos["entradas"]["pitch.md"]["en_main_desde"],
                                                hechos["entradas"]["plan.md"]["en_main_desde"]}
    versiones = [("2026-09-18T17:00:00Z", {"equipo.md": texto(EQUIPO_G13)})]
    for h in sorted(horas, key=fecha):
        if fecha(h) > fecha(ahora):
            continue
        ficheros = {"criterios.md": criterios_hasta(crit, hn, h)}
        if fecha(hechos["entradas"]["pitch.md"]["en_main_desde"]) <= fecha(h):
            ficheros["pitch.md"] = texto(ent["pitch.md"])
        if fecha(hechos["entradas"]["plan.md"]["en_main_desde"]) <= fecha(h):
            ficheros["plan.md"] = cambia("plan.md", texto(ent["plan.md"]))
        versiones.append((h, ficheros))
    return versiones


def versiones_g14(hechos, ahora, cambia=None):
    """Las versiones de equipo.md y plan.md de G14 que estaban en main a `ahora` (la del ajuste del sábado, después)."""
    cambia = cambia or (lambda n, t: t)
    salida = {}
    for nombre in ("equipo.md", "plan.md"):
        for v in hechos["entradas"][nombre]:
            if fecha(v["en_main_desde"]) <= fecha(ahora):
                salida.setdefault(v["en_main_desde"], {})[nombre] = cambia(nombre, texto(v["fichero"]))
    return sorted(salida.items(), key=lambda x: fecha(x[0]))


def relay(base, guion, versiones, ahora, jurado=True, ruta=True, tareas=None, extra=()):
    """El relay de verdad a `ahora`, con origin/main = `versiones` y los eventos del guion hasta esa hora (más `extra`).
    tareas: las del plan, si cambian (un caso que vuelve a leer el plan); si no, las del guion."""
    base = tempfile.mkdtemp(prefix="m10-", dir=base)
    t_guion, personas, issues, eventos, _ = montar(guion, AQUI)
    clon = repo(base, versiones)
    reloj = lambda: epoca(ahora)                   # noqa: E731
    nov = relay_mod.Novedades(clon, 300, reloj=reloj, vista_jurado=jurado, ruta_critica=ruta,
                              web_nueva=any("servicios.md" in f for _, f in versiones))
    nov.sondear()
    r = relay_mod.Relay(os.path.join(base, "relay"), personas, ahora=lambda: ahora,
                        sondeo=Sondeo(tareas or t_guion, issues, epoca(ahora)),
                        umbral_parada_s=guion.get("umbral_parada_s", 1200), novedades=nov, vista_jurado=jurado,
                        ruta_critica=ruta, web_nueva=nov.web_nueva)
    vistos = sorted([e for e in eventos if fecha(e["ts"]) <= fecha(ahora)] + list(extra), key=lambda e: fecha(e["ts"]))
    for i in range(0, len(vistos), 200):
        r.recibir({"eventos": vistos[i:i + 200]})
    r.recalcular()
    return r


def tareas_del_plan(guion, plan_md):
    """Las tareas de plan.md con las personas del guion (las de su tareas.json, o las de un caso que añade alguna)."""
    return leer_plan(plan_md, guion.get("personas") or json.loads(texto(guion["tareas"]))["personas"])


# ------------------------------------------------------------------------------- la vista, con la forma de los hechos
def ids_g13(crit_md, hechos):
    """{(cita, quien): N1…} de las notas de criterios.md, en su orden: las de los hechos con su ID y las que añade un caso
    con el siguiente (como g13_g14.py)."""
    suyos = {(h["cita"], h["quien"]): h["id"] for h in hechos["notas"]}
    salida = {}
    for k, m in enumerate(re.finditer(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+) \((.+)\)$", crit_md, re.M)):
        salida[(m.group(1), m.group(2))] = suyos.get((m.group(1), m.group(2)), f"N{k + 1}")
    return salida


def conexiones_de(v):
    """{clave: «de → a»} de las conexiones de la vista, para leer la Prueba como en los hechos."""
    return {c["clave"]: f"{c['de']} → {c['a']}" for c in (v.get("servicios") or {}).get("conexiones", [])}


def jurado_hechos(b, ids, conexiones=None):
    """El bloque `jurado` con la forma de g13/hechos.json. ids: {(cita, quien): N1…}; conexiones: {clave: «de → a»}."""
    conexiones = conexiones or {}

    def nid(nota):
        return ids.get((nota["cita"], nota["quien"]), nota["clave"])
    clave_a_id = {x["nota"]["clave"]: nid(x["nota"]) for x in b["notas"]}
    notas = {}
    for x in b["notas"]:
        filas = x["tareas"]
        n = {"estado": "corregida" if x["corregida_por"] else x["cobertura"]["valor"],
             "tareas": {f["tarjeta"]["id"]: f["tarjeta"]["estado"] for f in filas},
             "evidencia": [{"tarea": e["tarea"], "sha": e["valor"], "observado_en": z(e["observado_en"])}
                           for e in x["evidencias"] if e["tipo"] in ("commit", "fusion")],
             "trabajo_nuevo_desde": z(x["trabajo_nuevo_desde"]),
             "cerradas_a_mano": [f["tarjeta"]["id"] for f in filas if f["tarjeta"].get("declarado") == "cerrada"],
             "corregida_por": clave_a_id.get((x["corregida_por"] or {}).get("valor")),
             "tambien_en_pitch": x["pitch"] is not None}
        if any(f["enlace"]["ambiguo"] for f in filas):
            n["ambiguas"] = [f["tarjeta"]["id"] for f in filas if f["enlace"]["ambiguo"]]
        pruebas = [{"conexion": conexiones.get(e["conexion"], e["conexion"]), "resultado": e["valor"],
                    "observado_en": z(e["observado_en"]), "tarea": e["tarea"]}
                   for e in x["evidencias"] if e["tipo"] == "prueba"]
        if pruebas:
            n["pruebas"] = pruebas
        notas[nid(x["nota"])] = n
    return {"notas": notas, "orden": [nid(x["nota"]) for x in b["notas"]], "cuenta": b["cuenta"],
            "sin_nota": [{"tarea": s["tarea"], "cita": s["cita"]} for s in b["sin_nota"]], "resumen": b["resumen"]}


def jurado_esperado(esperado):
    """Lo que se compara de los hechos de G13 (todo menos el «motivo», que es texto para quien lee)."""
    salida = {k: v for k, v in esperado.items() if k in ("orden", "cuenta", "sin_nota", "resumen")}
    if "notas" in esperado:
        salida["notas"] = {k: {c: v for c, v in n.items() if c != "motivo"} for k, n in esperado["notas"].items()}
    return salida


def ruta_hechos(b, v, personas):
    """El bloque `ruta` con la forma de g14/hechos.json (horas en UTC; motivos, en las palabras de los hechos)."""
    e, o = b["estimacion"], b["objetivo"]
    hechos = b["hechos"]
    ciclo = next((h["ciclo"] for h in hechos if h["tipo"] == "ciclo"), None)
    zona = b.get("zona")
    return {
        "tareas": {t["id"]: t["estado"] for c in v["columnas"].values() for t in c},
        "zona": zona and {k: z(x) if k == "observado_en" else x for k, x in zona.items()},
        "entrega": {"texto": o["texto"], "valor": z(o["valor"]), "motivo": o["motivo"], "confirmar": o["confirmar"],
                    "discrepancias": [{"texto": x["texto"], "valor": z(x["valor"]), "donde": x["donde"]}
                                      for x in b["otras_entregas"]]},
        "veredicto": b["veredicto"]["valor"],
        "cifra": {"hay": e is not None, "motivos": b["veredicto"]["motivos"],
                  "rango": e and {"temprano": z(e["temprano"]), "tarde": z(e["tarde"]), "margen_min": e["margen_min"],
                                  "margen_max": e["margen_max"]}},
        "base": {p["persona"]: {"n": p["n"], "ritmo": None if p["ritmo_min"] is None else
                                {"min": p["ritmo_min"], "max": p["ritmo_max"]}} for p in b["base"]["personas"]},
        "sin_plazo": {x["tarea"]: TEXTO_MOTIVO.get(x["motivo"], x["motivo"]) for x in b["sin_plazo"]},
        "no_cuentan": {x["tarea"]: FUERA.get(x["motivo"], x["motivo"]) for x in b["fuera_de_entrega"]},
        "plazos_vencidos": {h["tarea"]: {"plazo": z(h["plazo"]), "arrastra": h["arrastra"]}
                            for h in hechos if h["tipo"] == "plazo_pasado"},
        "sin_senales": {h["persona"]: {"desde": z(h["desde"])} for h in hechos if h["tipo"] == "sin_senales"},
        "riesgos": [dict(r, fin_tarde=z(r["fin_tarde"])) for r in b["riesgos"]],
        "cadena": [{"tarea": x["tarjeta"]["id"], "por": x["por"], "fin_temprano": z(x["fin_temprano"]),
                    "fin_tarde": z(x["fin_tarde"])} for x in b["cadena"]],
        "ciclo": ciclo,
        "descansos": {"resueltos": all(d["desde"] for d in b["descansos"]),
                      "filas": [{"personas": d["personas"] or list(personas), "desde": z(d["desde"]),
                                 "hasta": z(d["hasta"])} for d in b["descansos"]]},
        "resumen": b["resumen"], "viejo": b["viejo"], "dato_mas_viejo": z(b["dato_mas_viejo"])}


RUTA_CLAVES = ("tareas", "zona", "veredicto", "cifra", "base", "sin_plazo", "no_cuentan", "plazos_vencidos",
               "sin_senales", "riesgos", "cadena", "ciclo", "descansos", "resumen", "viejo", "dato_mas_viejo")


def ruta_esperada(esperado):
    """Lo que se compara de los hechos (o de la espera de un caso) de G14: lo que la vista dice con sus campos."""
    salida = {k: esperado[k] for k in RUTA_CLAVES if k in esperado}
    if "entrega" in esperado:
        ent = esperado["entrega"]
        salida["entrega"] = {k: ent[k] for k in ("valor", "motivo", "confirmar") if k in ent}
        if "discrepancias" in ent:
            salida["entrega"]["discrepancias"] = [{k: d[k] for k in ("texto", "valor", "donde") if k in d}
                                                  for d in ent["discrepancias"]]
    if "cifra" in salida:
        salida["cifra"] = {k: v for k, v in salida["cifra"].items() if k in ("hay", "motivos", "rango")}
    if "base" in salida:
        salida["base"] = {p: {k: x[k] for k in ("n", "ritmo") if k in x} for p, x in salida["base"].items()}
    if "plazos_vencidos" in salida:
        salida["plazos_vencidos"] = {t: {k: x[k] for k in ("plazo", "arrastra")} for t, x in salida["plazos_vencidos"].items()}
    if "sin_senales" in salida:
        salida["sin_senales"] = {p: {"desde": x["desde"]} for p, x in salida["sin_senales"].items()}
    if "descansos" in salida:
        d = salida["descansos"]
        salida["descansos"] = {k: d[k] for k in ("resueltos",) if k in d}
        salida["descansos"]["filas"] = [{k: f[k] for k in ("personas", "desde", "hasta")} for f in d.get("filas", [])]
    return salida


def vista(r, ahora=None):
    """La vista que calcularía el demonio (o el MCP) con el estado del relay, a `ahora` (por defecto, la del relay)."""
    return proyeccion.vista(r.estado, ahora=ahora or r.estado["generado_en"])
