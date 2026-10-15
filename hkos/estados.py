"""Motor de estados del Hackathon OS: función pura, sin E/S (diseno.md §5.1, casos en §5.2).

derivar(tarea, issue, eventos, dependencias, equipo, ahora) da el estado de una tarea a partir de sus señales.
Los eventos llegan ya atribuidos (la atribución, regla 9, va en modelo.py) y son los de la tarea más los `push`.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache

# Tipos que cuentan como actividad del dueño (regla 1). `reclamo` no: una tarea reclamada no tiene actividad aún.
ACTIVIDAD = {"edicion", "arbol", "latido", "encargo.lanzado", "worker.inicio", "worker.fin", "compuerta.ok",
             "compuerta.ko", "fusion.creada", "revision.veredicto", "fusion.aprobada", "fusion.descartada", "commit"}
CUMPLEN = {"publicada", "cerrada"}          # estados derivados que cumplen una dependencia (regla 10)
ATRIBUIBLES = {"reclamada", "en_curso", "parada"}   # regla 9


@lru_cache(maxsize=1 << 16)
def fecha(s):
    """ISO 8601 → datetime con zona. `fromisoformat` de 3.10 no acepta «Z». En caché: el recálculo convierte las mismas
    horas una y otra vez (M8e)."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(d):
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ordenar(eventos):
    """En orden de ts, sin repetidos por id; a igual ts, en el orden en que llegaron."""
    vistos, salida = set(), []
    for e in eventos:
        if e["id"] not in vistos:
            vistos.add(e["id"])
            salida.append(e)
    return sorted(salida, key=lambda e: fecha(e["ts"]))


def dato(valor, fuente, ts):
    return {"valor": valor, "fuente": fuente, "observado_en": ts}


def estado_issue(issue, dueno, equipo, ahora):
    """Asignación y cierre del issue con las acciones de GitHub hasta `ahora`. Lo de fuera del equipo se ignora."""
    asignado, cerrado, disc = None, None, []
    for a in sorted(issue.get("acciones", []), key=lambda a: fecha(a["ts"])):
        if fecha(a["ts"]) > ahora:
            continue
        if a["por"] not in equipo:
            disc.append(("fuera_del_equipo", a["por"], f"{a['accion']} del issue por una cuenta de fuera del equipo", a["ts"]))
        elif a["accion"] == "asignar":
            if a["a"] == dueno:
                asignado = asignado or a["ts"]
            else:
                disc.append(("actividad_ajena", a["por"], f"issue asignado a {a['a']}, que no es su dueño", a["ts"]))
        elif a["accion"] == "cerrar":
            cerrado = a["ts"]
        elif a["accion"] == "reabrir":
            cerrado = None
    return asignado, cerrado, disc


def derivar(tarea, issue, eventos, dependencias, equipo, ahora, umbral_parada_s=1200):
    """Estado de una tarea (diseno.md §5.1).

    tarea: {id, dueno, depende_de}; issue: {creado_en, acciones: [{accion, por, a?, ts}]};
    eventos: normalizados, ya atribuidos (los de la tarea y los push); dependencias: {ID: {estado, declarado}} de las
    que existen; equipo: personas de coordinacion.md; ahora: ISO 8601.
    Devuelve {estado, declarado, fusion, cumplidas_por_cierre, discrepancias}; cada discrepancia es
    {tipo, tarea, persona, detalle, ts}, sin agrupar (lo agrupa modelo.py).
    """
    tid, dueno = tarea["id"], tarea["dueno"]
    t_ahora = fecha(ahora)
    disc = []

    def anota(tipo, persona, detalle, ts):
        d = {"tipo": tipo, "tarea": tid, "detalle": detalle, "ts": ts}
        if persona:
            d["persona"] = persona
        disc.append(d)

    fase = None           # None, en_curso, en_revision, integrada, no_cerrada, publicada
    fase_dato = None      # (fuente, ts) del evento que fijó la fase
    ultima = None         # (fuente, ts) de la última actividad del dueño
    reclamo = None        # ts del primer reclamo del dueño
    cambios = 0
    fusion_actual, veredicto_actual, fusion = None, None, None
    por_publicar = None   # sha cuya llegada a origin/main publica la tarea (última fusión aprobada o último commit)
    incluidos = set()

    for e in ordenar(eventos):
        if fecha(e["ts"]) > t_ahora:
            continue
        tipo, fuente, ts, d = e["tipo"], e["fuente"], e["ts"], e.get("datos", {})
        persona = e["actor"]["persona"]

        if tipo == "push":                         # regla 8: observación de origin/main, sea quien sea quien la ve
            if fuente != "git":
                if persona == dueno and e.get("tarea") == tid:
                    ultima = (fuente, ts)
                continue
            incluye = set(d.get("incluye", []))
            incluidos |= incluye
            if fase != "publicada" and por_publicar and por_publicar in incluye:
                fase, fase_dato, por_publicar = "publicada", (fuente, ts), None
            elif fase == "en_revision" and fusion_actual in incluye:
                anota("hook_frente_a_git", persona, f"la fusión {fusion_actual} llegó a origin/main sin veredicto ni ff-only", ts)
                fase, fase_dato, por_publicar, fusion = "publicada", (fuente, ts), None, fusion_actual
            continue

        # Regla 1. Excepción (M8e): si el dueño no tiene GitHub (no está en el equipo), cuenta cualquiera del equipo que
        # traiga el ID; lo atribuido por la regla 9 nunca llega aquí, porque solo atribuye a tareas de la propia persona.
        if persona != dueno and not (dueno not in equipo and persona in equipo):
            anota("actividad_ajena", persona, f"{tipo} en {tid}, que es de {dueno}", ts)
            continue

        if tipo == "reclamo":
            reclamo = reclamo or ts
            continue
        if tipo not in ACTIVIDAD:
            continue
        ultima = (fuente, ts)

        if tipo == "encargo.lanzado":              # regla 2
            if fase == "no_cerrada":
                cambios = 0
            if fase in (None, "integrada", "publicada", "no_cerrada"):
                fase, fase_dato = "en_curso", (fuente, ts)
            if fase != "en_revision":
                por_publicar = None
        elif tipo == "fusion.creada":              # regla 3
            fase, fase_dato = "en_revision", (fuente, ts)
            fusion_actual, veredicto_actual = d.get("sha"), None
        elif tipo == "revision.veredicto":         # regla 4
            if d.get("sha") != fusion_actual:
                anota("veredicto_sha", persona, f"veredicto {d.get('veredicto')} sobre {d.get('sha')}; la fusión actual es {fusion_actual}", ts)
                continue
            veredicto_actual = d.get("veredicto")
            if veredicto_actual == "APROBADO":
                cambios = 0
            else:
                cambios += 1
                fase, fase_dato = ("no_cerrada" if cambios >= 2 else "en_curso"), (fuente, ts)
        elif tipo == "fusion.descartada":          # regla 5
            if fase == "en_revision" and veredicto_actual is None:
                fase, fase_dato, fusion_actual = "en_curso", (fuente, ts), None
        elif tipo == "fusion.aprobada":            # regla 6
            sha = d.get("sha")
            if not (sha == fusion_actual and veredicto_actual == "APROBADO"):
                anota("hook_frente_a_git", persona, f"main contiene la fusión {sha} sin un APROBADO registrado", ts)
            fase, fase_dato = "integrada", (fuente, ts)
            fusion = por_publicar = sha
            fusion_actual, veredicto_actual = None, None
        elif tipo == "commit":                     # regla 7
            sha = d.get("sha")
            if sha in incluidos or d.get("alcanzable"):
                if fase != "publicada":
                    fase, fase_dato, por_publicar = "publicada", (fuente, ts), None
            elif fase in (None, "en_curso", "publicada"):
                fase, fase_dato, por_publicar = "en_curso", (fuente, ts), sha
        elif fase is None:                         # regla 1: cualquier otra actividad
            fase, fase_dato = "en_curso", (fuente, ts)

    asignado, cerrado, disc_issue = estado_issue(issue, dueno, equipo, t_ahora)
    for tipo, persona, detalle, ts in disc_issue:
        anota(tipo, persona, detalle, ts)

    # Dependencias (regla 10), también para la marca de cumplidas por cierre.
    cumplidas, por_cierre, pendientes = [], [], False
    for dep in tarea.get("depende_de", []):
        info = dependencias.get(dep)
        if info is None:
            anota("dependencia_inexistente", None, f"depende de {dep}, que no existe", issue["creado_en"])
            pendientes = True
        elif info["estado"]["valor"] in CUMPLEN:
            cumplidas.append(info["estado"]["observado_en"])
        elif info.get("declarado") and info["declarado"]["valor"] == "cerrada":
            cumplidas.append(info["declarado"]["observado_en"])
            por_cierre.append(dep)
        else:
            pendientes = True

    if fase is None:                               # regla 10
        if asignado or reclamo:
            primero = min((x for x in ((asignado, "github"), (reclamo, "mcp")) if x[0]), key=lambda x: fecha(x[0]))
            estado = dato("reclamada", primero[1], primero[0])
        elif pendientes:
            estado = dato("pendiente", "github", issue["creado_en"])
        else:
            ts = max([issue["creado_en"]] + cumplidas, key=fecha)
            estado = dato("lista", "derivado", ts)
    elif fase == "en_curso":                       # regla 11
        limite = fecha(ultima[1]) + timedelta(seconds=umbral_parada_s)
        if t_ahora > limite:
            estado = dato("parada", "derivado", iso(limite))
        else:
            estado = dato("en_curso", ultima[0], ultima[1])
    else:
        estado = dato(fase, fase_dato[0], fase_dato[1])

    declarado = None                               # regla 12
    if cerrado:
        if estado["valor"] == "publicada":
            estado = dato("cerrada", "github", cerrado)
        else:
            declarado = dict(dato("cerrada", "github", cerrado), declarado=True)

    return {"estado": estado, "declarado": declarado, "fusion": fusion,
            "cumplidas_por_cierre": por_cierre, "discrepancias": disc}
