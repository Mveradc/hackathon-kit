"""Estado sintético de M8f: 5 personas y 20 tareas con títulos largos, colisiones de nivel 1 y 3 puestas a mano (su
cálculo es de M8g), 7 novedades y actividad sin tarea. Para el presupuesto del bloque «Equipo» (criterio 2 de M8f) y
para ejercitar el camino de colisiones de la prueba de igualdad (criterio 5). Determinista; valida contra
estado.schema.json (lo comprueba igualdad.py).
"""
from datetime import datetime, timedelta, timezone

T0 = datetime(2026, 9, 19, 9, 0, tzinfo=timezone.utc)
PERSONAS = [("persona-a", "A"), ("persona-b", "B"), ("persona-c", "C"), ("persona-d", "D"), ("persona-e", "E")]
ESTADOS = ["en_curso", "parada", "en_revision", "lista", "pendiente", "reclamada", "integrada", "publicada",
           "no_cerrada", "cerrada"]
FUENTE = {"en_curso": "hook", "parada": "derivado", "en_revision": "hook", "lista": "derivado", "pendiente": "github",
          "reclamada": "github", "integrada": "git", "publicada": "git", "no_cerrada": "hook", "cerrada": "github"}


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def estado_5x20(ahora_min=90):
    ahora = T0 + timedelta(minutes=ahora_min)
    tareas = []
    for i in range(20):
        persona = PERSONAS[i % 5][0]
        e = ESTADOS[(i * 3) % len(ESTADOS)]
        t = {"id": f"T{i + 1:02d}", "dueno": persona, "bloque": f"Bloque {i // 5 + 1}",
             "titulo": f"Tarea {i + 1}: implementar el módulo {i + 1} con su comprobación, sus casos límite y la "
                       f"integración con lo que entrega la persona {PERSONAS[(i + 1) % 5][1]}",
             "depende_de": [f"T{i:02d}"] if i % 4 == 3 else [],
             "estado": {"valor": e, "fuente": FUENTE[e], "observado_en": iso(T0 + timedelta(minutes=3 * i))},
             "declarado": None}
        if i == 6:
            t["declarado"] = {"valor": "cerrada", "fuente": "github", "observado_en": iso(T0 + timedelta(minutes=40)),
                              "declarado": True}
        if e == "pendiente":
            t["depende_de"] = [f"T{i:02d}"]
        tareas.append(t)
    personas = []
    for n, (p, nombre) in enumerate(PERSONAS):
        actores = []
        if n < 4:
            actores.append({"papel": "orquestador" if n % 2 else "principal", "sesion": f"s-{p}", "activo": n != 3,
                            "ultimo_latido": iso(ahora - timedelta(seconds=30 + 200 * (n == 3)))})
        if n == 1:
            for w in range(2):
                actores.append({"papel": "worker", "sesion": f"s-{p}", "agente": f"w{w}", "activo": True,
                                "ultimo_latido": iso(ahora - timedelta(seconds=20)),
                                "tarea": {"valor": "T02", "fuente": "hook", "observado_en": iso(ahora - timedelta(minutes=5))}})
        personas.append({"persona": p, "nombre": nombre, "actores": actores})
    colisiones = [
        {"id": "n1-web-app", "nivel": "1", "gravedad": "amarillo", "personas": ["persona-a", "persona-b"],
         "rutas": ["web/src/App.jsx", "web/src/api.js"], "observado_en": iso(ahora - timedelta(minutes=2))},
        {"id": "n3-contrato-ficha", "nivel": "3", "gravedad": "rojo", "personas": ["persona-b", "persona-c"],
         "rutas": ["motor/ficha.py"], "contrato": "Ficha de empresa (GET /api/ficha)",
         "observado_en": iso(ahora - timedelta(minutes=1))},
        {"id": "n1-datos", "nivel": "1", "gravedad": "amarillo", "personas": ["persona-d", "persona-e"],
         "rutas": ["datos/carga.py"], "observado_en": iso(ahora - timedelta(minutes=7))}]
    novedades = [{"tipo": "decision" if k % 2 else "criterio",
                  "resumen": f"#{20 + k}: acuerdo o nota número {k} con un texto largo que sigue y sigue para ocupar sitio "
                             f"en el presupuesto del bloque",
                  "autor": "@persona-a ↔ @persona-b" if k % 2 else "Persona C",
                  "observado_en": iso(T0 + timedelta(minutes=10 * k))} for k in range(7)]
    return {"v": 1, "generado_en": iso(ahora),
            "fuentes": {"relay": {"valor": "ok", "fuente": "derivado", "observado_en": iso(ahora)},
                        "github": {"valor": "ok", "fuente": "github", "observado_en": iso(ahora - timedelta(seconds=20))},
                        "git": {"valor": "ok", "fuente": "git", "observado_en": iso(ahora - timedelta(minutes=4))}},
            "personas": personas, "tareas": tareas,
            "sin_tarea": [{"persona": "persona-d", "que": "commit: experimento", "observado_en": iso(ahora - timedelta(minutes=9))}],
            "discrepancias": [], "colisiones": colisiones, "novedades": novedades}
