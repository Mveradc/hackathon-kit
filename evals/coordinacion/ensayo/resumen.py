# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Resumen del ensayo de M8h (K-83) a partir de lo que el Hackathon OS guarda solo: los zips de `hk-os recoger` de cada
persona (el de quien coordina trae el registro del relay y, en `contexto/`, el plan, la coordinación, la autoridad y
los contratos de origin/main).

Rehace el estado minuto a minuto con hkos/modelo.py (el mismo cálculo que el relay) y saca:
  - la línea de tiempo de cada tarea (estado y fuente de cada cambio);
  - las colisiones (nivel, desde y hasta, personas avisadas y ficheros o contrato);
  - las discrepancias por tipo (atribucion_ambigua, actividad_ajena, sin_tarea…);
  - las sesiones sin `sesion.fin` (el SessionEnd perdido);
  - lo inyectado en cada sesión (caracteres de los deltas desde el último inicio, de entregado/*.firmas);
  - el desfase del reloj de cada portátil frente al relay y los eventos con hora por delante de la del relay;
  - lo que tardó el arranque del demonio en cada sesión (arranque.log);
  - las acciones de la web nueva (M9a, si aparecen): los eventos con fuente `web` del registro del relay (`reclamo`, y
    `anotacion` si algún día la emite), las líneas de `acciones.jsonl` de cada clon (y si el relay tiene su evento y si
    un monitor la entregó, `entregado/accion-<id>`) y las notas de Anotar (commits «Criterio: <papel> · …» de
    git-log.tsv y, si el zip trae `contexto/.hackathon/criterios.md`, las entradas «anotada desde la web»).
Lo que no sale de aquí (las preguntas en voz alta y si un estado era incorrecto) está en la hoja.

**Anonimizado por defecto** (Persona A, B…, también dentro de rutas y textos): la salida va a prueba.md, que es público.
Con --sin-anonimizar solo escribe fuera del repo del kit.

Uso: uv run --no-project evals/coordinacion/ensayo/resumen.py --zips <zips…> [--informe f.md] [--paso 60] [--sin-anonimizar]
"""
import argparse
import json
import os
import re
import string
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(KIT, "hkos"))
import compilar  # noqa: E402
import contratos as contratos_mod  # noqa: E402
import github  # noqa: E402
from estados import fecha, iso  # noqa: E402
from modelo import calcular  # noqa: E402
from red import conf  # noqa: E402


def leer_zip(ruta):
    """{nombre interno: texto} de un zip de hk-os recoger. Las carpetas (`entregado/accion-<id>/`) quedan con texto vacío."""
    with zipfile.ZipFile(ruta) as z:
        return {n: "" if n.endswith("/") else z.read(n).decode("utf-8", "replace") for n in z.namelist()}


# Anotar (api.md §4): «Criterio: <papel> · <primeros 50 caracteres>». /hack-note sube «Criterio: <resumen>», sin papel.
NOTA_WEB = re.compile(r"^Criterio: (jurado|mentor|organizaci[oó]n) · ")
ACCION_ENTREGADA = re.compile(r"^os/entregado/accion-([^/]+)(/|$)")


def acciones_web(eventos, zips, por_zip, personas, nombres, tz):
    """Lo que dejan Anotar y Reclamar (M9a): eventos con fuente web del relay, acciones.jsonl de cada clon, entregas del
    monitor y notas de Anotar. Devuelve las líneas del informe; main anonimiza el texto entero al final."""
    web = [e for e in eventos if e.get("fuente") == "web"]
    ids_relay = {e["id"] for e in eventos}
    # La persona de cada commit, solo de los eventos `commit` de los demonios (nunca del autor de git, ADR-0011).
    sha_persona = {e["datos"]["sha"][:12]: e["actor"]["persona"] for e in eventos
                   if e["tipo"] == "commit" and isinstance(e.get("datos"), dict) and e["datos"].get("sha")}
    notas = {}                                           # sha → hora (dedup: cada clon trae el log de todo main)
    for z in zips.values():
        for l in z.get("git-log.tsv", "").splitlines():
            c = l.split("\t")
            if len(c) >= 5 and NOTA_WEB.match(c[4]):
                notas.setdefault(c[0][:12], c[1])
    criterios = next((z["contexto/.hackathon/criterios.md"] for z in zips.values()
                      if z.get("contexto/.hackathon/criterios.md")), "")
    # «Afecta a» va antes que «Anotado por» (plantilla de api.md §4): se cuenta cada entrada al cerrarla.
    por_md, entrada = Counter(), None
    for l in criterios.splitlines() + ["## fin"]:
        l = l.strip()
        if l.startswith("## "):
            if entrada and entrada["web"]:
                por_md[entrada["autor"] or "—"] += 1
            entrada = {"web": False, "autor": None}
        elif entrada is not None and l.startswith("- Afecta a:") and "anotada desde la web" in l:
            entrada["web"] = True
        elif entrada is not None and l.startswith("- Anotado por:"):
            entrada["autor"] = l[len("- Anotado por:"):].strip().lstrip("@").lower() or None

    if not (web or notas or por_md or any("os/acciones.jsonl" in z for z in zips.values())):
        return ["Ninguna en los zips (con `web_nueva: no`, o nadie usó Anotar ni Reclamar).", ""]

    L = ["| Persona | Eventos web en el relay (por tipo) | Horas de los reclamos web | `acciones.jsonl` (por tipo) | "
         "Sin evento en el relay | Entregadas por un monitor | Notas de Anotar (git) |", "|---|---|---|---|---|---|---|"]
    # entregado/accion-<id> es una carpeta vacía: un zip sin ninguna no dice que no se entregaran, sino que no las trae.
    con_entregas = any(ACCION_ENTREGADA.match(n) for z in zips.values() for n in z)
    for p in personas:
        yo = p["persona"]
        mios = [e for e in web if e["actor"]["persona"] == yo]
        tipos = Counter(e["tipo"] for e in mios)
        horas = ", ".join(hhmm(e["ts"], tz) for e in mios if e["tipo"] == "reclamo") or "—"
        z = por_zip.get(yo, {})
        acc = jsonl(z.get("os/acciones.jsonl", ""))
        acc_tipos = Counter(str(x.get("tipo", "?")) for x in acc)
        sin_evento = sum(1 for x in acc if x.get("id") and x["id"] not in ids_relay)
        entregadas = {m.group(1) for n in z for m in [ACCION_ENTREGADA.match(n)] if m}
        n_notas = sum(1 for sha in notas if sha_persona.get(sha) == yo)
        L.append(f"| {nombres[yo]} | {', '.join(f'{k} {v}' for k, v in tipos.most_common()) or '0'} | {horas} | "
                 f"{', '.join(f'{k} {v}' for k, v in acc_tipos.most_common()) or ('0' if z else '— (sin zip)')} | "
                 f"{sin_evento} | {len(entregadas) if con_entregas else '—'} | {n_notas} |")
    sin_atribuir = sum(1 for sha in notas if sha not in sha_persona)
    otros_reclamos = Counter(e["fuente"] for e in eventos if e["tipo"] == "reclamo" and e.get("fuente") != "web")
    L += ["", f"- Notas de Anotar en el log de main: {len(notas)}"
          + (f" ({sin_atribuir} sin evento `commit` de ningún demonio: no se sabe de quién)" if sin_atribuir else "") + "."]
    if por_md:
        L.append("- En `criterios.md` de main, entradas «anotada desde la web» (por «Anotado por»): "
                 + ", ".join(f"{nombres.get(k, k)} {v}" for k, v in por_md.most_common()) + ".")
    if not con_entregas:
        L.append("- «Entregadas por un monitor»: ningún zip trae `entregado/accion-<id>`. O ningún monitor entregó una "
                 "acción, o los zips son de antes de que `hk-os recoger` guardara las carpetas vacías (PR #11). "
                 "Si la sesión recibió el turno, lo dice la hoja.")
    if otros_reclamos:
        L.append("- Reclamos por otra vía (para comparar): " + ", ".join(f"{k} {v}" for k, v in otros_reclamos.items()) + ".")
    L += ["- Lo que no sale de aquí: los reclamos y notas que la web rechazó (409, 429, 502…), que no dejan ni evento ni "
          "línea, y lo que se siguió haciendo en la terminal. Eso, en la sección 7 de la hoja.", ""]
    return L


def jsonl(texto):
    salida = []
    for l in texto.splitlines():
        try:
            e = json.loads(l)
        except ValueError:
            continue
        if isinstance(e, dict):
            salida.append(e)
    return salida


def equipo_de(texto):
    salida = []
    for l in texto.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*@([A-Za-z0-9-]+)\s*\|", l)
        if m:
            salida.append({"persona": m.group(2).lower(), "nombre": m.group(1)})
    return salida


class Anonimo:
    """Usuarios y nombres → «Persona A», «Persona B»… en cualquier texto (también dentro de rutas)."""

    def __init__(self, personas, activo=True):
        self.activo, self.cambios = activo, []
        for i, p in enumerate(personas):
            letra = f"Persona {string.ascii_uppercase[i]}"
            self.cambios += [(p["persona"], letra), (p["nombre"], letra)]
        self.cambios.sort(key=lambda x: -len(x[0]))

    def __call__(self, texto):
        texto = str(texto)
        if not self.activo:
            return texto
        for viejo, nuevo in self.cambios:
            if len(viejo) >= 3 and viejo != nuevo:     # «C» o «A» a secas romperían rutas y textos
                texto = re.sub(rf"(?<![A-Za-z0-9-])@?{re.escape(viejo)}(?![A-Za-z0-9-])", nuevo, texto, flags=re.I)
        return texto


def hhmm(ts, tz):
    return fecha(ts).astimezone(tz).strftime("%H:%M")


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Resumen del ensayo de M8h")
    p.add_argument("--zips", nargs="+", required=True)
    p.add_argument("--informe")
    p.add_argument("--paso", type=int, default=60, help="segundos entre dos cálculos del estado (60)")
    p.add_argument("--sin-anonimizar", action="store_true")
    a = p.parse_args(argv)
    if a.sin_anonimizar:
        destino = os.path.abspath(a.informe or "")
        if not a.informe or os.path.normcase(destino).startswith(os.path.normcase(KIT + os.sep)):
            raise SystemExit("resumen.py: --sin-anonimizar solo con --informe fuera del repo del kit.")
    tz = datetime.now().astimezone().tzinfo

    zips = {os.path.basename(z): leer_zip(z) for z in a.zips}
    coord = next((z for z in zips.values() if "os/relay/eventos.jsonl" in z), None)
    if coord is None:
        raise SystemExit("resumen.py: ningún zip trae os/relay/eventos.jsonl (el de quien coordina).")
    eventos = sorted(jsonl(coord["os/relay/eventos.jsonl"]), key=lambda e: (fecha(e["ts"]), e["id"]))
    if not eventos:
        raise SystemExit("resumen.py: el registro del relay está vacío.")
    personas = equipo_de(coord.get("contexto/.hackathon/coordinacion.md", ""))
    if not personas:
        vistas = sorted({e["actor"]["persona"] for e in eventos if e["actor"].get("persona")})
        personas = [{"persona": x, "nombre": x} for x in vistas]
    inicio, fin = fecha(eventos[0]["ts"]), fecha(eventos[-1]["ts"])

    # Tareas: de la foto de GitHub del relay o, sin GitHub, del plan de origin/main.
    tareas, motor, origen = [], {}, "ninguno"
    foto = json.loads(coord["os/relay/github.json"]) if coord.get("os/relay/github.json") else None
    if foto and foto.get("issues"):
        s = github.Sondeo(type("Cliente", (), {"repo": "-"})(), {p["persona"] for p in personas})
        s.de_disco(foto)
        tareas, motor, _, _ = s.resultado(fin)
        origen = "issues hk-tarea (github.json del relay)"
    elif coord.get("contexto/.hackathon/plan.md"):
        tareas, motor, _, _ = compilar.tareas_de_plan(coord["contexto/.hackathon/plan.md"], personas, iso(inicio))
        origen = "plan.md de origin/main (sin GitHub)"
    # Los dueños sin GitHub (filas con «—» en la tabla) también se anonimizan.
    sueltos = sorted({t["dueno"] for t in tareas} - {p["persona"] for p in personas})
    anon = Anonimo(personas + [{"persona": d, "nombre": d} for d in sueltos], not a.sin_anonimizar)
    nombres = {p["persona"]: anon(p["persona"]) for p in personas}
    contratos, _ = contratos_mod.duenos(coord.get("contexto/docs/contratos.md", ""), coord.get("contexto/.hackathon/autoridad.md", ""))

    # Estado minuto a minuto.
    historia, colisiones, t = defaultdict(list), {}, inicio
    ultimo_estado = None
    while True:
        ahora = iso(t)
        e = calcular(tareas, motor, eventos, personas, ahora, contratos=contratos)
        ultimo_estado = e
        for x in e["tareas"]:
            v = (x["estado"]["valor"], x["estado"]["fuente"])
            if not historia[x["id"]] or historia[x["id"]][-1][1:] != v:
                historia[x["id"]].append((x["estado"]["observado_en"], *v))
        for c in e["colisiones"]:
            k = c["id"]
            if k not in colisiones:
                colisiones[k] = dict(c, desde=ahora, hasta=ahora, rutas=set(c["rutas"]))
            colisiones[k]["hasta"] = ahora
            colisiones[k]["rutas"] |= set(c["rutas"])
        if t >= fin:
            break
        t = min(fin, t + timedelta(seconds=a.paso))

    L = [f"# Resumen del ensayo (Hackathon OS, M8h)", "",
         f"- Del {inicio.astimezone(tz):%Y-%m-%d %H:%M} al {fin.astimezone(tz):%H:%M} ({(fin - inicio).total_seconds() / 3600:.1f} h), "
         f"{len(eventos)} eventos en el relay, {len(personas)} personas, {len(tareas)} tareas ({origen}).",
         f"- Estado rehecho cada {a.paso} s con hkos/modelo.py. Anonimizado: {'sí' if anon.activo else '**no**'}.", ""]

    L += ["## Tareas: cambios de estado", "", "| Tarea | Dueño | Cambios (hora · estado · fuente) | Final |", "|---|---|---|---|"]
    for x in ultimo_estado["tareas"]:
        h = historia[x["id"]]
        cambios = " → ".join(f"{hhmm(ts, tz)} {v} ({f})" for ts, v, f in h)
        L.append(f"| {x['id']} | {nombres.get(x['dueno'], anon(x['dueno']))} | {anon(cambios)} | {x['estado']['valor']} |")
    finales = Counter(x["estado"]["valor"] for x in ultimo_estado["tareas"])
    L += ["", "Al final: " + ", ".join(f"{k} {v}" for k, v in finales.most_common()) + ".", ""]

    L += ["## Colisiones", ""]
    if colisiones:
        L += ["| Nivel | Gravedad | Desde | Hasta | Personas avisadas | Ficheros o contrato |", "|---|---|---|---|---|---|"]
        for c in sorted(colisiones.values(), key=lambda c: c["desde"]):
            que = c.get("contrato") or ", ".join(sorted(c["rutas"]))[:200]
            L.append(f"| {c['nivel']} | {c['gravedad']} | {hhmm(c['desde'], tz)} | {hhmm(c['hasta'], tz)} | "
                     f"{', '.join(nombres.get(x, anon(x)) for x in c['personas'])} | {anon(que)} |")
        por_nivel = Counter(c["nivel"] for c in colisiones.values())
        avisos3 = sum(len(c["personas"]) for c in colisiones.values() if c["nivel"] == "3")
        L += ["", "Por nivel: " + ", ".join(f"nivel {k}: {v}" for k, v in sorted(por_nivel.items()))
              + (f". Avisos de nivel 3 enviados (personas × colisiones): {avisos3}." if avisos3 else "."),
              "El nivel 2 no se rehace (sale de merge-tree en el relay, no del registro): mira el estado final y la hoja.", ""]
    else:
        L += ["Ninguna en el registro (niveles 1 y 3).", ""]

    L += ["## Discrepancias y actividad sin tarea", ""]
    d = Counter(x["tipo"] for x in ultimo_estado["discrepancias"])
    L.append("- Discrepancias (estado final): " + (", ".join(f"{k} {v}" for k, v in d.most_common()) or "ninguna") + ".")
    sin = ultimo_estado.get("sin_tarea", [])
    L.append(f"- Sin tarea: {len(sin)}" + (" — " + anon("; ".join(f"{s['persona']}: {s['que']}" for s in sin[:10])) if sin else "") + ".")
    L.append("")

    L += ["## Sesiones", "", "| Persona | Sesiones | Sin `sesion.fin` | Arranques del demonio (mediana ms) | Desfase del reloj |",
          "|---|---|---|---|---|"]
    sesiones = defaultdict(lambda: {"ini": set(), "fin": set()})
    for e in eventos:
        s = e["actor"].get("sesion")
        if not s or e["actor"]["papel"] not in ("principal", "orquestador"):
            continue
        if e["tipo"] == "sesion.inicio":
            sesiones[e["actor"]["persona"]]["ini"].add(s)
        elif e["tipo"] == "sesion.fin":
            sesiones[e["actor"]["persona"]]["fin"].add(s)
    por_zip = {}
    for nombre_zip, z in zips.items():
        persona = None
        for n, texto in z.items():
            if n.startswith("os/eventos/") and n.endswith(".jsonl"):
                ps = {x.get("persona") for x in jsonl(texto) if x.get("persona")}
                if ps:
                    persona = sorted(ps)[0]
                    break
        if persona:
            por_zip[persona] = z
    for p in personas:
        s = sesiones[p["persona"]]
        z = por_zip.get(p["persona"], {})
        ms = sorted(int(m.group(1)) for m in re.finditer(r" (\d+) ms$", z.get("os/arranque.log", ""), re.M))
        desfase = z.get("desfase.txt", "").strip() or "—"
        L.append(f"| {nombres[p['persona']]} | {len(s['ini'])} | {len(s['ini'] - s['fin'])} | "
                 f"{ms[len(ms) // 2] if ms else '—'} ({len(ms)}) | {desfase} s |")
    L.append("")

    L += ["## Lo inyectado en las sesiones (deltas, desde el último inicio o compactación)", "",
          "| Persona | Sesiones con deltas | Caracteres (máx.) | Líneas de colisión entregadas |", "|---|---|---|---|"]
    for p in personas:
        z = por_zip.get(p["persona"], {})
        chars, sesiones_d, colis = [], 0, 0
        for n, texto in z.items():
            if n.startswith("os/entregado/") and n.endswith(".firmas"):
                m = re.search(r"^chars=(\d+)$", texto, re.M)
                if m:
                    chars.append(int(m.group(1)))
                    sesiones_d += int(m.group(1)) > 0
                colis += len(re.findall(r"^linea=.*nivel", texto, re.M))
        L.append(f"| {nombres[p['persona']]} | {sesiones_d} de {len(chars)} | {max(chars) if chars else 0} | {colis} |")
    L.append("")

    L += ["El desfase es el del reloj de cada portátil frente al del relay al recoger (`hk-os recoger`; positivo = "
          "adelantado). El relay toma como «ahora» el máximo entre su hora y la del último evento (M8d): un portátil "
          "adelantado no se oculta, pero puede adelantar los umbrales de presencia y de «parada» de los demás.", ""]

    L += ["## Acciones de la web nueva (M9a: Anotar y Reclamar)", ""]
    L += acciones_web(eventos, zips, por_zip, personas, nombres, tz)

    texto = anon("\n".join(L)) + "\n"
    if a.informe:
        with open(a.informe, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
