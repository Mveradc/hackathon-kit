"""G12 (M9a, K-97): servicios.md con su historia en un repo de git de verdad y los eventos que tocan cada caso, para
igualdad.py (ADR-0009: la vista, estado-equipo.md y el MCP, con los mismos campos de servicios).

Tres personas (persona-a, persona-b, persona-c). Casos:
  - api (persona-a) de /hack-scaffold, confirmado, con el puerto caído según el demonio de persona-a;
  - motor (persona-b) cambiado por persona-c: sin confirmar, le falta persona-b;
  - una propuesta de conexión de persona-c entre web (persona-a) y motor (persona-b): la esperan las dos;
  - la Prueba de «web → api» fallando (hook) y un contrato que no existe;
  - un fichero fuera de todo servicio (scripts/descarga.py) y otro solo en un `arbol` (notas.txt);
  - T01 reclamada desde la web por persona-a: declarada.
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), "..", "hkos"))
import servicios  # noqa: E402

PERSONAS = [{"persona": "persona-a", "nombre": "A"}, {"persona": "persona-b", "nombre": "B"},
            {"persona": "persona-c", "nombre": "C"}]
AHORA = "2026-11-25T18:20:00.000000Z"
AUTORIDAD = ("# Autoridad\n## Por dueño\n### A (@persona-a) · `api/`, `web/`\n### B (@persona-b) · `motor/`\n"
             "### C (@persona-c) · `datos/`\n")
CONTRATOS = "# Contratos\n## web → api\nVive en: api/esquema.py\n## motor → web\nVive en: motor/salida.py\n"
SERVICIOS = ("# Servicios\nFuera de servicios: docs/\n\n## Servicios\n| Nombre | Carpeta | Puerto | Arranque | Salud | Dueño |\n"
             "|---|---|---|---|---|---|\n| api | api/ | 8000 | `uv run api` | /salud | — |\n| web | web/ | 5173 | — | — | — |\n"
             "| motor | motor/ | {puerto_motor} | — | — | — |\n| datos | datos/ | — | — | — | — |\n\n"
             "## Conexiones\n| De | A | Contrato | Prueba |\n|---|---|---|---|\n| web | api | web → api | `pytest t_web_api.py` |\n"
             "| motor | web | motor → web | — |\n| datos | motor | datos → motor | — |\n{propuestas}")
PROPUESTA = ("\n## Propuestas de conexiones\n| De | A | Contrato | Prueba | Autor | Hora |\n|---|---|---|---|---|---|\n"
             "| web | motor | motor → web | — | @persona-c | 2026-11-25 18:10 |\n")
TAREAS = [{"id": "T01", "titulo": "API de predicción", "dueno": "persona-a", "depende_de": []},
          {"id": "T02", "titulo": "Motor", "dueno": "persona-b", "depende_de": []}]
ISSUES = {t["id"]: {"creado_en": "2026-11-25T18:00:00.000000Z", "numero": 100 + i, "acciones": []}
          for i, t in enumerate(TAREAS)}


def git(repo, *args, cuando=None):
    env = dict(os.environ)
    if cuando:                                   # la hora del commit, la del guion (es la de servicios.md en la vista)
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = cuando
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                          check=True, env=env).stdout.strip()


def escribe(repo, ruta, texto):
    p = os.path.join(repo, ruta)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def montar(base):
    """(repo, eventos): el repo con la historia de servicios.md y los eventos del guion."""
    repo = os.path.join(base, "g12")
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.name", "x"); git(repo, "config", "user.email", "x@example.com")
    escribe(repo, ".hackathon/autoridad.md", AUTORIDAD)
    escribe(repo, "docs/contratos.md", CONTRATOS)
    escribe(repo, ".hackathon/servicios.md", SERVICIOS.format(puerto_motor="—", propuestas=""))
    escribe(repo, "api/main.py", "x\n")
    escribe(repo, "scripts/descarga.py", "x\n")
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "scaffold", cuando="2026-11-25T18:00:00Z")
    escribe(repo, ".hackathon/servicios.md", SERVICIOS.format(puerto_motor="9000", propuestas=PROPUESTA))
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "persona-c cambia motor y propone una conexión", cuando="2026-11-25T18:10:00Z")
    sha_c = git(repo, "rev-parse", "HEAD")
    clave_api = servicios.leer(SERVICIOS.format(puerto_motor="—", propuestas=""))["filas"][0]["clave"]

    def ev(n, persona, tipo, ts, papel="principal", fuente="hook", **extra):
        e = {"v": 1, "id": f"g12-{n}", "ts": ts, "actor": {"persona": persona, "papel": papel, "sesion": f"s-{persona}"},
             "tipo": tipo, "fuente": fuente}
        e.update(extra)
        return e

    eventos = [
        ev(1, "persona-c", "commit", "2026-11-25T18:10:00.000000Z", papel="humano", fuente="git",
           datos={"sha": sha_c, "rama": "main", "alcanzable": True}),
        ev(2, "persona-a", "servicio.estado", "2026-11-25T18:12:00.000000Z", papel="demonio", fuente="demonio",
           datos={"servicio": "api", "clave": clave_api, "puerto": 8000, "escucha": False, "salud": None}),
        ev(3, "persona-b", "prueba", "2026-11-25T18:14:00.000000Z",
           datos={"comando_sha": servicios.huella_prueba("pytest t_web_api.py"), "resultado": "falla", "codigo": 1}),
        ev(4, "persona-b", "arbol", "2026-11-25T18:15:00.000000Z", rutas=["notas.txt", "motor/m.py"]),
        ev(5, "persona-a", "reclamo", "2026-11-25T18:16:00.000000Z", papel="humano", fuente="web", tarea="T01"),
    ]
    return repo, eventos
