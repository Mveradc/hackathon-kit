# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Criterios 4 y 6 de M8e sin red ni modelos, con reloj inyectado: el relay de verdad (hkos/relay.py) con su sondeo de
GitHub (hkos/github.py) contra el GitHub falso de hkos/pruebas, y el compilador de verdad con el plan del 03.

Criterio 4: una tarea `en_curso` sin actividad pasa a `parada` a los 20 min; una `reclamada` sin actividad sigue
`reclamada`; un commit en una rama sin ID, con la persona sin tareas abiertas, sale en `sin_tarea`.
Criterio 6: 2 h simuladas (un sondeo cada 30 s): el GitHub falso cuenta todas las escrituras de todas las cuentas;
ninguna hora deslizante pasa de 60 (con la compilación inicial exenta, R-30); los sondeos sin cambios reciben 304; la
cuenta del equipo que hace el relay desde lo que muestra GitHub coincide con la del falso.

Uso: uv run --no-project evals/coordinacion/simulador/duradero.py   (0 OK · 1 falla)
"""
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path[:0] = [os.path.join(KIT, "hkos"), os.path.join(KIT, "hkos", "pruebas")]
import compilar  # noqa: E402
import github  # noqa: E402
import relay as relay_mod  # noqa: E402
from github_falso import GitHubFalso  # noqa: E402
from red import leer_texto  # noqa: E402

PLAN = os.path.join(KIT, "skills", "hack-plan", "examples", "03-xray-embat-real-plan.md")
TABLA = [{"persona": "persona-a", "nombre": "Persona A"}, {"persona": "persona-b", "nombre": "Persona B"}]
T0 = 1_800_000_000.0
fallos = 0


class Reloj:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def iso(self):
        return datetime.fromtimestamp(self.t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def comprueba(nombre, ok, detalle=""):
    global fallos
    fallos += not ok
    print(f"{'OK   ' if ok else 'FALLO'} {nombre}" + (f"  [{detalle}]" if detalle else ""))


def montar(reloj, tmp):
    gh = GitHubFalso(reloj=reloj)
    tareas = compilar.leer_plan(leer_texto(PLAN), TABLA)
    c = compilar.Compilador(github.Cliente(gh.repo, "tok-persona-a", base=gh.base, reloj=reloj), TABLA, "abc1234",
                            reloj=reloj, dormir=lambda s: setattr(reloj, "t", reloj.t + s), salida=lambda s: None)
    c.compilar(tareas)
    sondeo = github.Sondeo(github.Cliente(gh.repo, "tok-persona-b", base=gh.base, reloj=reloj),
                           {p["persona"] for p in TABLA}, reloj=reloj)
    r = relay_mod.Relay(os.path.join(tmp, "relay"), TABLA, ahora=reloj.iso, sondeo=sondeo)
    return gh, sondeo, r, tareas


def ev(reloj, n, tipo, persona, tarea=None, **datos):
    e = {"v": 1, "id": f"sim-{n}", "ts": reloj.iso(), "actor": {"persona": persona, "papel": "principal", "sesion": "s"},
         "tipo": tipo, "fuente": "git" if tipo == "commit" else "hook"}
    if tarea:
        e["tarea"] = tarea
    if tipo == "edicion":
        e["rutas"] = ["web/src/App.jsx"]
    if datos:
        e["datos"] = datos
    return e


def numero(gh, tid):
    return next(n for n, i in gh.issues.items() if i["title"].startswith(tid + " "))


def tarea(r, tid):
    return next(t for t in r.estado["tareas"] if t["id"] == tid)


def criterio_4(tmp):
    print("== Criterio 4: parada, reclamada y rama sin ID (reloj inyectado)")
    reloj = Reloj()
    gh, sondeo, r, tareas = montar(reloj, tmp)
    try:
        # Dos tareas de B sin dependencias: una se reclama (se asigna), la otra pasa a en curso por una edición.
        libres = [t["id"] for t in tareas if t["dueno"] == "persona-b" and not t["depende_de"]]
        t_curso, t_recl = libres[0], libres[1]
        print(f"     tareas de B: {t_curso} (en curso) y {t_recl} (reclamada)")
        b = github.Cliente(gh.repo, "tok-persona-b", base=gh.base, reloj=reloj)
        b.pedir("POST", f"/repos/{gh.repo}/issues/{numero(gh, t_recl)}/assignees", {"assignees": ["persona-b"]})
        sondeo.sondear()
        r.recibir({"eventos": [ev(reloj, 1, "edicion", "persona-b", t_curso)]})
        r.recalcular()
        comprueba("t=0: una en_curso y otra reclamada",
                  (tarea(r, t_curso)["estado"]["valor"], tarea(r, t_recl)["estado"]["valor"]) == ("en_curso", "reclamada"))
        reloj.t += 19 * 60
        r.recalcular()
        comprueba("t=19 min: sigue en_curso", tarea(r, t_curso)["estado"]["valor"] == "en_curso")
        reloj.t += 2 * 60
        r.recalcular()
        t10, t11 = tarea(r, t_curso)["estado"], tarea(r, t_recl)["estado"]
        comprueba("t=21 min: la de en curso, parada (derivado, en el minuto 20); la reclamada sigue reclamada",
                  (t10["valor"], t10["fuente"], t11["valor"]) == ("parada", "derivado", "reclamada"),
                  f"{t10['valor']} {t10['fuente']} {t10['observado_en']}; {t11['valor']}")
        r.recibir({"eventos": [ev(reloj, 2, "edicion", "persona-b", t_curso)]})
        r.recalcular()
        comprueba("una edición la saca de parada", tarea(r, t_curso)["estado"]["valor"] == "en_curso")
        # Rama sin ID, con la persona sin tareas abiertas (A no tiene ninguna reclamada ni en curso).
        r.recibir({"eventos": [ev(reloj, 3, "commit", "persona-a", sha="abc1234", rama="experimento", alcanzable=False)]})
        r.recalcular()
        comprueba("commit de A en la rama «experimento» sin ID → sin_tarea",
                  [(s["persona"], s["que"]) for s in r.estado["sin_tarea"]] == [("persona-a", "commit: experimento")],
                  str(r.estado["sin_tarea"]))
        comprueba("y ninguna tarea de A cambia", all(t["estado"]["valor"] in ("lista", "pendiente")
                                                    for t in r.estado["tareas"] if t["dueno"] == "persona-a"))
    finally:
        gh.cerrar()


def criterio_6(tmp):
    print("== Criterio 6: 2 h simuladas, escrituras a GitHub y 304")
    reloj = Reloj()
    gh, sondeo, r, tareas = montar(reloj, tmp)
    try:
        iniciales = len(gh.escrituras)
        fin_inicial = reloj.t
        a = github.Cliente(gh.repo, "tok-persona-a", base=gh.base, reloj=reloj)
        b = github.Cliente(gh.repo, "tok-persona-b", base=gh.base, reloj=reloj)
        ids_a = [t["id"] for t in tareas if t["dueno"] == "persona-a"]
        ids_b = [t["id"] for t in tareas if t["dueno"] == "persona-b"]
        sin_cambios = cambios = 0
        recompilado = False
        cuentas = []
        for vuelta in range(240):                               # 2 h, un sondeo cada 30 s
            if vuelta % 20 == 5:                                # cada 10 min, alguien reclama o cierra
                k = vuelta // 20
                quien, ids = (a, ids_a) if k % 2 else (b, ids_b)
                tid = ids[k // 2 % len(ids)]
                yo = "persona-a" if quien is a else "persona-b"
                quien.pedir("POST", f"/repos/{gh.repo}/issues/{numero(gh, tid)}/assignees", {"assignees": [yo]})
                if k % 3 == 2:
                    quien.pedir("PATCH", f"/repos/{gh.repo}/issues/{numero(gh, tid)}", {"state": "closed"})
            if vuelta == 120 and not recompilado:               # a la hora, un ajuste del plan
                texto = leer_texto(PLAN)
                for tid in ("T02", "T03"):
                    fila = next(l for l in texto.splitlines() if l.startswith(f"| {tid} |"))
                    texto = texto.replace(fila, fila[:-2] + " (v2) |")
                compilar.Compilador(a, TABLA, "def5678", reloj=reloj, dormir=lambda s: setattr(reloj, "t", reloj.t + s),
                                    salida=lambda s: None).compilar(compilar.leer_plan(texto, TABLA))
                recompilado = True
            antes = dict(gh.lecturas)
            if sondeo.sondear():
                cambios += 1
                r.recalcular()
            elif gh.lecturas["200"] == antes["200"]:
                sin_cambios += 1
            if vuelta % 10 == 9:
                cuentas.append((reloj.t, sondeo.resultado()[3]))
            reloj.t += 30
        # Ventanas deslizantes de 1 h sobre las escrituras del falso (todas las cuentas).
        todas = [t for t, *_ in gh.escrituras]
        sin_inicial = [t for t in todas[iniciales:]]
        def maximo(ts):
            return max((sum(1 for x in ts if s <= x < s + 3600) for s in ts), default=0)
        comprueba(f"compilación inicial: {iniciales} escrituras, exenta del tope (R-30), a ≤ 1/s",
                  fin_inicial - T0 >= iniciales - 1, f"{fin_inicial - T0:.0f} s")
        m = maximo(sin_inicial)
        comprueba(f"después: máximo de escrituras en una hora deslizante, entre todas las cuentas = {m} (< 60)", m < 60)
        comprueba(f"sondeos sin ningún cambio: {sin_cambios} de 240, todos con 304 en las tres consultas",
                  sin_cambios > 200, f"200: {gh.lecturas['200']}, 304: {gh.lecturas['304']}")
        # La cuenta del relay (desde GitHub) frente a la del falso, en la última hora.
        reales = sum(1 for t in todas if reloj.t - 3600 < t <= reloj.t)
        cuenta = sondeo.resultado()[3]
        comprueba(f"la cuenta del equipo que hace el relay desde GitHub ({cuenta}) = la del GitHub falso ({reales})",
                  cuenta == reales)
        print(f"     escrituras del equipo vistas por el relay, cada 5 min: {[c for _, c in cuentas]}")
    finally:
        gh.cerrar()


def main():
    tmp = tempfile.mkdtemp(prefix="hk-duradero-")
    try:
        criterio_4(os.path.join(tmp, "c4"))
        criterio_6(os.path.join(tmp, "c6"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{fallos} fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
