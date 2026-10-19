"""Lectores puros de M10 (K-104; api.md §11.2): lo que el relay lee de origin/main de su clon para la vista de jurado
(ADR-0012) y la ruta crítica (ADR-0013). Sin red, sin git y sin reloj: reciben el texto de cada fichero y la hora de
su último commit, y devuelven lo que va a estado.json (`jurado`, `ruta` y los campos nuevos de las tareas).

Todo lo que sale de un fichero es declarado (constitución II): `fuente: git`, `declarado: true` y, como
`observado_en`, la hora del commit de ese fichero (constitución III). Lo que no se entiende sale con `null` y su
motivo, nunca con una hora inventada.

Zonas horarias: un desfase fijo («+02:00», «UTC+2», «UTC−3») o un nombre IANA. El relay es solo biblioteca estándar
(ADR-0005) y en Windows Python no trae tzdata: si zoneinfo no resuelve el nombre, las zonas de la UE (Europe/* y
Atlantic/Canary) se calculan con la regla de horario de verano de la UE (`_ZonaUE`); cualquier otra sale `sin_zona`.
En los cambios de hora, como zoneinfo con fold=0: una hora que no existe (la de marzo) se lee con el desfase de antes
del cambio (02:30 → 03:30 de verano) y una que se repite (la de octubre), como la primera (la de verano).
"""
import hashlib
import math
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone, tzinfo

import compilar
import proyeccion
import servicios as servicios_mod

ZONEINFO = True                 # las pruebas lo apagan para forzar el respaldo de la UE también en Linux
DIJO_MAX, FUERZA_MAX, TEXTO_MAX = 500, 40, 300
CRITERIO = re.compile(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+)$")       # la de relay.py
CITA = re.compile(r"^\d{4}-\d\d-\d\d \d\d:\d\d( · .{1,80})?$")         # $defs/cita
# El «· quién» puede llevar sus paréntesis («Marta (Embat)», #56): uno sin abrir lo acaba (el de una cita entre ()).
CORRIGE = re.compile(r"corrige la nota del (\d{4}-\d\d-\d\d \d\d:\d\d)(?: · ((?:[^:;,.()»\n]|\([^()\n]*\)){1,80}))?", re.I)
CAMPO = re.compile(r"^- ([^:]+):\s*(.*)$")
UNA_HORA = timedelta(hours=1)
ENTREGA = re.compile(r"\bentregas?\b", re.I)      # la palabra, no «entregables»

DIAS = {"lun": 0, "lunes": 0, "mar": 1, "martes": 1, "mie": 2, "miercoles": 2, "jue": 3, "jueves": 3, "vie": 4,
        "viernes": 4, "sab": 5, "sabado": 5, "dom": 6, "domingo": 6}
MESES = {"ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3, "abr": 4, "abril": 4, "may": 5, "mayo": 5,
         "jun": 6, "junio": 6, "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "sept": 9, "septiembre": 9,
         "setiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12}
H_REL = re.compile(r"^h\s*\+\s*(\d{1,3})(?::([0-5]\d))?$")
SOLO_HORA = re.compile(r"^(\d{1,2}):(\d\d)$")
DIA_HORA = re.compile(r"^([a-z]+)\.?\s+(\d{1,2}):(\d\d)$")
FECHA_HORA = re.compile(r"^(?:([a-z]+)\.?,?\s+)?(\d{1,2})\s+(?:de\s+)?([a-z]+)\.?(?:\s+(?:de\s+)?(\d{4}))?,?\s+"
                        r"(?:a\s+las\s+)?(\d{1,2}):(\d\d)$")
TURNO = re.compile(r"^([a-z]+)\.?\s+(\d{1,2}):(\d\d)\s*[-–—]\s*(?:([a-z]+)\.?\s+)?(\d{1,2}):(\d\d)$")
# Una hora dentro del texto de una nota (otras_entregas): con día de la semana o fecha, nunca una hora suelta.
_D = r"(?:lun(?:es)?|mar(?:tes)?|mi[eé](?:rcoles)?|jue(?:ves)?|vie(?:rnes)?|s[aá]b(?:ado)?|dom(?:ingo)?)"
_M = r"(?:ene(?:ro)?|feb(?:rero)?|mar(?:zo)?|abr(?:il)?|may(?:o)?|jun(?:io)?|jul(?:io)?|ago(?:sto)?|sep(?:t(?:iembre)?)?|" \
     r"setiembre|oct(?:ubre)?|nov(?:iembre)?|dic(?:iembre)?)"
EN_TEXTO = re.compile(rf"\b(?:{_D}\.?,?\s+)?(?:\d{{1,2}}\s+(?:de\s+)?{_M}\.?(?:\s+(?:de\s+)?\d{{4}})?,?\s+)?"
                      rf"(?:a\s+las\s+)?\d{{1,2}}:\d\d\b", re.I)
IANA = re.compile(r"\b([A-Z][A-Za-z_]+(?:/[A-Z][A-Za-z_+-]+){1,2})\b")
DESFASE = re.compile(r"(?:\b(?:UTC|GMT)\s*([+\-−])\s*(\d{1,2})(?::?([0-5]\d))?)|(?:(?<![\w:])([+\-−])(\d\d):([0-5]\d)\b)")
# Un desfase ISO 8601 pegado a la hora (con o sin segundos): «10:00+02:00», «T10:00:00-03:00». La hora se queda.
PEGADO = re.compile(r"(?<![\d:])(\d{1,2}:[0-5]\d)(:[0-5]\d)?([+\-−])(\d\d):?([0-5]\d)(?![\d:])")
SOLO_UTC = re.compile(r"\b(?:UTC|GMT)\b(?!\s*[+\-−]\s*\d)")
FECHA_ISO = re.compile(r"(?<!\d)(\d{4})-(\d\d)-(\d\d)(?!\d)")
FECHA_BARRAS = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")
# «20 de septiembre de 2026», «dom 20 sep 2026», «20 sep»: con o sin «de», con o sin día de la semana y año.
FECHA_TEXTO = re.compile(r"(?:\b([a-z]+)\.?,?\s+)?(?<![\d:])(\d{1,2})\s+(?:de\s+)?([a-z]+)\.?(?:,?\s+(?:de\s+)?(\d{4}))?(?!\d)")
HORA_EN = re.compile(r"(?<![\d:])(\d{1,2}):(\d\d)(?![\d:])")

# Zonas de la UE con su desfase de invierno (horas), para cuando zoneinfo no las tiene (Windows sin tzdata).
UE = {**{f"Europe/{c}": 1 for c in (
    "Madrid Paris Berlin Rome Amsterdam Brussels Vienna Zurich Stockholm Oslo Copenhagen Prague Warsaw Budapest Belgrade "
    "Ljubljana Zagreb Bratislava Luxembourg Monaco Andorra Malta Gibraltar Sarajevo Skopje Tirane Podgorica San_Marino "
    "Vatican Vaduz Busingen").split()},
      **{f"Europe/{c}": 0 for c in "Lisbon London Dublin Guernsey Isle_of_Man Jersey".split()},
      **{f"Europe/{c}": 2 for c in "Athens Helsinki Bucharest Sofia Riga Tallinn Vilnius Kyiv Kiev Mariehamn".split()},
      "Atlantic/Canary": 0}


def _ultimo_domingo(anio, mes):
    d = date(anio, mes, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


class _ZonaUE(tzinfo):
    """Una zona de la UE sin tzdata: verano del último domingo de marzo al último de octubre, a las 01:00 UTC.
    Con la semántica de zoneinfo (PEP 495): en el hueco de marzo y en la hora repetida de octubre, fold=0 es el
    desfase de antes del cambio."""

    def __init__(self, nombre, horas):
        self.nombre, self.std = nombre, timedelta(hours=horas)

    def _cambios(self, anio):
        return (datetime.combine(_ultimo_domingo(anio, 3), datetime.min.time()) + UNA_HORA,
                datetime.combine(_ultimo_domingo(anio, 10), datetime.min.time()) + UNA_HORA)

    def utcoffset(self, dt):
        if dt is None:
            return self.std
        ini, fin = self._cambios(dt.year)
        local, a, b = dt.replace(tzinfo=None), ini + self.std, fin + self.std
        if local < a or local >= b + UNA_HORA:
            return self.std
        if local < a + UNA_HORA:                         # 02:00–03:00 de marzo: no existe
            return self.std + UNA_HORA if dt.fold else self.std
        if local >= b:                                   # 02:00–03:00 de octubre: se repite
            return self.std if dt.fold else self.std + UNA_HORA
        return self.std + UNA_HORA

    def dst(self, dt):
        return self.utcoffset(dt) - self.std

    def tzname(self, dt):
        return self.nombre

    def fromutc(self, dt):
        u = dt.replace(tzinfo=None)
        ini, fin = self._cambios(u.year)
        if ini <= u < fin:
            return (u + self.std + UNA_HORA).replace(tzinfo=self)
        return (u + self.std).replace(tzinfo=self, fold=int(fin <= u < fin + UNA_HORA))

    def __repr__(self):
        return f"_ZonaUE({self.nombre!r})"


def zona(nombre):
    """tzinfo de un nombre IANA, o None si no se puede resolver en este portátil."""
    if ZONEINFO:
        try:
            import zoneinfo
            return zoneinfo.ZoneInfo(nombre)
        except Exception:                                # sin tzdata (Windows) o nombre desconocido
            pass
    return _ZonaUE(nombre, UE[nombre]) if nombre in UE else None


def aviso_zona(nombre):
    return f"la zona {nombre} no se puede resolver sin tzdata en este portátil; usa +HH:MM"


def _llano(s):
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def _iso(d):
    return d.isoformat(timespec="seconds") if d else None


def _txt(v, n=TEXTO_MAX):
    v = (v or "").strip()
    return None if v in ("", "—", "-") else proyeccion.corta(v, n)


def _local(dia, h, mi, tz):
    if int(h) > 23 or int(mi) > 59:
        raise ValueError("hora")
    return datetime(dia.year, dia.month, dia.day, int(h), int(mi), tzinfo=tz)


def _de(dt, tz):
    """dt en la zona tz (para sacar su fecha y su desfase)."""
    return dt.astimezone(tz)


# ------------------------------------------------------------------------------------------------ equipo.md
def _zona_de(texto):
    """(zona normalizada, tzinfo, texto sin la zona, aviso) de una línea de equipo.md. Un desfase ISO 8601 pegado a la
    hora («10:00+02:00», «2026-09-20T10:00:00+02:00») es zona, no una segunda hora (#56); con «-», solo detrás de una
    hora ISO con «T» (si no, «10:00-11:00» es un tramo con dos horas)."""
    pegado = None
    for m in PEGADO.finditer(texto):
        if m.group(3) == "+" or texto[max(0, m.start() - 1):m.start()] in ("T", "t"):
            pegado = _desfase(m.group(3), m.group(4), m.group(5))
            if pegado:
                texto = texto[:m.end(1)] + texto[m.end():]
                break
    zona_n, tz, resto, aviso = _zona_suelta(texto)
    if zona_n is None and aviso is None and pegado:
        return pegado[0], pegado[1], resto, None
    return zona_n, tz, resto, aviso


def _desfase(signo, h, mi):
    """(«±HH:MM», tzinfo) de un desfase, o None si pasa de ±14:00."""
    minutos = (int(h) * 60 + int(mi or 0)) * (-1 if signo in "-−" else 1)
    if abs(minutos) > 14 * 60:
        return None
    tz = timezone(timedelta(minutes=minutos))
    return _iso(datetime(2000, 1, 1, tzinfo=tz))[-6:], tz


def _zona_suelta(texto):
    m = DESFASE.search(texto)
    if m:
        d = _desfase(*((m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(4), m.group(5), m.group(6))))
        if d:
            return d[0], d[1], texto[:m.start()] + texto[m.end():], None
    m = IANA.search(texto)
    if m:
        tz = zona(m.group(1))
        return (m.group(1) if tz else None), tz, texto[:m.start()] + texto[m.end():], (None if tz else aviso_zona(m.group(1)))
    m = SOLO_UTC.search(texto)
    if m:
        return "+00:00", timezone.utc, texto[:m.start()] + texto[m.end():], None
    return None, None, texto, None


def _fecha_equipo(texto, anio):
    l = _llano(texto)
    m = FECHA_ISO.search(l)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = FECHA_BARRAS.search(l)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    for m in FECHA_TEXTO.finditer(l):
        if m.group(3) in MESES:
            dia = date(int(m.group(4) or anio), MESES[m.group(3)], int(m.group(2)))
            if m.group(1) in DIAS and DIAS[m.group(1)] != dia.weekday():
                raise ValueError("el día de la semana no cuadra con la fecha")
            return dia
    return None


def hora_equipo(texto, anio, tz_defecto=None, varias=False):
    """`- Inicio:` o `- Entrega:` → (datetime|None, motivo, confirmar, zona normalizada|None, tzinfo|None, aviso,
    [otras horas]). Sin zona en la línea, la de `tz_defecto` (la de Inicio:, para Entrega:). Dos horas distintas (sin
    contar la zona): con `varias` (Entrega:), la primera manda y las demás salen en la lista, el mismo día o el
    siguiente; sin él, `dos_horas`."""
    t = (texto or "").strip()
    confirmar = "(confirmar)" in t.lower()
    t = re.sub(r"\(confirmar\)", "", t, flags=re.I).strip()
    zona_n, tz, resto, aviso = _zona_de(t)
    if not t or t in ("—", "-") or "<" in t:
        return None, "sin_dato", confirmar, zona_n, tz, aviso, []
    if "por confirmar" in _llano(t) or "?" in t:
        return None, "por_confirmar", confirmar, zona_n, tz, aviso, []
    horas = list(dict.fromkeys((int(h), int(mi)) for h, mi in HORA_EN.findall(resto)))
    if len(horas) > 1 and not varias:
        return None, "dos_horas", confirmar, zona_n, tz, aviso, []
    try:
        dia = _fecha_equipo(resto, anio)
        if dia is None or not horas:
            return None, "formato", confirmar, zona_n, tz, aviso, []
        usada = tz or (tz_defecto if zona_n is None and aviso is None else None)
        if usada is None:
            return None, "sin_zona", confirmar, zona_n, tz, aviso, []
        dt = _local(dia, *horas[0], usada)
        otras = [_local(dia, *h, usada) for h in horas[1:]]
        otras = [o if o > dt else _local(dia + timedelta(days=1), *h, usada) for o, h in zip(otras, horas[1:])]
        return dt, None, confirmar, zona_n, usada, aviso, otras
    except ValueError:
        return None, "formato", confirmar, zona_n, tz, aviso, []


def _seccion(texto, titulo):
    """Las líneas de la sección `## <titulo>` (sin distinguir mayúsculas), o None si no está."""
    lineas, dentro, vista = [], False, False
    for linea in (texto or "").splitlines():
        if linea.startswith("## ") or linea.startswith("# "):
            dentro = linea[3:].strip().lower() == titulo.lower() if linea.startswith("## ") else False
            vista = vista or dentro
            continue
        if dentro:
            lineas.append(linea)
    return lineas if vista else None


def _dato(valor, fuente, observado_en, declarado=True):
    return {"valor": valor, "fuente": fuente, "observado_en": observado_en, "declarado": declarado}


def leer_equipo(texto, ct, anio):
    """equipo.md → {equipo, zona, inicio, entrega, tz, avisos, otras} (api.md §11.2, ADR-0013 decisión 1A). Entrega:
    sin zona usa la de Inicio:; con dos horas, la primera manda y las demás van a `otras` (para otras_entregas)."""
    sec = None if texto is None else _seccion(texto, "Hackathon")
    estado = "sin fichero" if texto is None else ("mal formado" if sec is None else "ok")
    salida = {"equipo": _dato(estado, "git", ct), "inicio": None, "entrega": None, "tz": None, "avisos": [], "otras": []}
    zonas, tz_inicio = [], None
    for clave in ("Inicio", "Entrega"):
        if sec is None:
            continue
        linea = next((l.strip()[len(f"- {clave}:"):] for l in sec if l.strip().startswith(f"- {clave}:")), None)
        dt, motivo, confirmar, zona_n, tz, aviso, otras = \
            hora_equipo(linea, anio, tz_inicio, clave == "Entrega") if linea is not None else \
            (None, "sin_dato", False, None, None, None, [])
        zonas.append((zona_n, tz))
        tz_inicio = tz if zona_n else tz_inicio
        if aviso:
            salida["avisos"].append(aviso)
        salida[clave.lower()] = {"valor": _iso(dt), "texto": _txt(linea) if linea is not None else None,
                                 "confirmar": confirmar, "motivo": motivo, "donde": "equipo.md", "fuente": "git",
                                 "observado_en": ct, "declarado": True, "_dt": dt}
        salida["otras"] += [{"valor": _iso(o), "texto": _txt(linea), "motivo": None, "donde": "equipo.md",
                             "fuente": "git", "observado_en": ct, "declarado": True} for o in otras]
    # #56, 6: la zona IANA si alguna de las dos líneas la da (con ella las horas cambian bien en el cambio de hora);
    # si no, el desfase de Inicio: (o el de Entrega:).
    zona_n, salida["tz"] = next(((z, tz) for z, tz in zonas if z and "/" in z), None) or \
        next(((z, tz) for z, tz in zonas if z), (None, None))
    salida["zona"] = _dato(zona_n, "git", ct)
    return salida


def _publica(x):
    return None if x is None else {k: v for k, v in x.items() if not k.startswith("_")}


# ------------------------------------------------------------------------------------------------ Hasta
def resolver(texto, inicio, tz, anterior=None, anio=None, inicio_motivo=None):
    """Un Hasta (o un Cuándo de Hitos, o el principio de un turno) → (datetime|None, motivo) (api.md §11.2, ADR-0013
    decisión 2A). `anterior`: el Hasta resuelto de la fila anterior de la persona, para «HH:MM» sin día."""
    l = _llano(texto)
    if l in ("", "—", "-", "–"):
        return None, "vacio"
    if "por confirmar" in l or "?" in l:
        return None, "por_confirmar"
    try:
        m = H_REL.match(l)
        if m:
            if inicio is None:
                return None, "sin_zona" if inicio_motivo == "sin_zona" else "relativo_sin_inicio"
            suma = timedelta(hours=int(m.group(1)), minutes=int(m.group(2) or 0))
            return _de(inicio.astimezone(timezone.utc) + suma, tz), None
        m = FECHA_HORA.match(l)
        if m and m.group(3) in MESES and (m.group(1) is None or m.group(1) in DIAS):
            if tz is None:
                return None, "sin_zona"
            dia = date(int(m.group(4) or anio), MESES[m.group(3)], int(m.group(2)))
            if m.group(1) is not None and DIAS[m.group(1)] != dia.weekday():
                return None, "formato"                   # el día de la semana no cuadra con la fecha
            return _local(dia, m.group(5), m.group(6), tz), None
        m = DIA_HORA.match(l)
        if m and m.group(1) in DIAS:
            if tz is None:
                return None, "sin_zona"
            if inicio is None:
                return None, "sin_inicio"
            base = _de(inicio, tz).date()
            return _local(base + timedelta(days=(DIAS[m.group(1)] - base.weekday()) % 7), m.group(2), m.group(3), tz), None
        m = SOLO_HORA.match(l)
        if m:
            if tz is None:
                return None, "sin_zona"
            base = anterior or inicio
            if base is None:
                return None, "sin_inicio"
            dia = _de(base, tz).date()
            dt = _local(dia, m.group(1), m.group(2), tz)
            return (dt if dt >= base else _local(dia + timedelta(days=1), m.group(1), m.group(2), tz)), None
    except (ValueError, TypeError):
        pass
    return None, "formato"


# ------------------------------------------------------------------------------------------------ criterios.md
def _sin_comentarios(texto):
    return re.sub(r"<!--.*?-->", "", texto or "", flags=re.S)


def leer_criterios(texto, ct, tz):
    """criterios.md → {fichero, notas} (api.md §11.2, ADR-0012 decisiones 1A y 2A)."""
    if texto is None:
        return {"fichero": _dato("sin fichero", "git", ct), "notas": []}
    bloques, actual = [], None
    for linea in _sin_comentarios(texto).splitlines():
        s = linea.strip()
        if s.startswith("## ") or s.startswith("# "):
            m = CRITERIO.match(s)
            actual = {"cabecera": s, "cita": m.group(1), "resto": m.group(2), "campos": {}, "lineas": []} if m else None
            if actual:
                bloques.append(actual)
        elif actual is not None:
            actual["lineas"].append(s)
            m = CAMPO.match(s)
            if m and m.group(1).strip() not in actual["campos"]:
                actual["campos"][m.group(1).strip()] = (m.group(2).strip(), s)
    notas, claves, mal = [], set(), False
    for b in bloques:
        if "Qué dijo" not in b["campos"]:
            mal = True
            continue
        que, que_linea = b["campos"]["Qué dijo"]
        anotado, anotado_linea = b["campos"].get("Anotado por", (None, ""))
        clave = hashlib.sha256("\n".join((b["cabecera"], que_linea, anotado_linea)).encode("utf-8")).hexdigest()[:12]
        if clave in claves:                              # la repetición de merge=union: es la misma nota
            continue
        claves.add(clave)
        m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", b["resto"])
        quien, papel = (m.group(1), m.group(2)) if m else (b["resto"], None)
        literal = que.startswith("«")
        dijo = que
        if literal:
            dijo = dijo[1:-1] if dijo.endswith("»") else dijo[1:]
        elif _llano(dijo).startswith("(parafrasis)"):
            dijo = dijo[dijo.index(")") + 1:]
        fuerza = (b["campos"].get("Fuerza") or ("", ""))[0].strip().strip("«»\"“”").strip()
        tipo = {"dato": "dato", "comentario suelto": "comentario", "sin precisar": "sin_precisar", "": "sin_precisar"}
        tipo = tipo.get(fuerza.lower(), "palabra")
        c = CORRIGE.search("\n".join(b["lineas"]))
        corrige = (f"{c.group(1)} · {c.group(2).strip()}" if c.group(2) and c.group(2).strip() else c.group(1)) if c else None
        try:
            hora = _iso(_local(datetime.strptime(b["cita"], "%Y-%m-%d %H:%M"), *b["cita"][11:].split(":"), tz)) if tz else None
        except ValueError:
            hora = None
        notas.append({"clave": clave, "cita": b["cita"], "hora": hora, "quien": _txt(quien), "papel": _txt(papel),
                      "donde": _txt((b["campos"].get("Dónde") or ("", ""))[0]),
                      "dijo": proyeccion.equilibra(dijo, DIJO_MAX), "literal": literal,
                      "fuerza": {"tipo": tipo, "texto": proyeccion.corta(fuerza or "sin precisar", FUERZA_MAX)},
                      "afecta_a": _txt((b["campos"].get("Afecta a") or ("", ""))[0]), "anotado_por": _txt(anotado),
                      "corrige": corrige if corrige and CITA.match(corrige) else None,
                      "fuente": "git", "observado_en": ct, "declarado": True})
    return {"fichero": _dato("mal formado" if mal else "ok", "git", ct), "notas": notas}


def etiquetas(texto):
    """[(inicio, fin, [citas])] de cada `(criterios: …)` del texto, con los paréntesis equilibrados (un «quién» puede
    llevar los suyos). Las citas que no tienen la forma de $defs/cita no salen."""
    salida, l = [], (texto or "").lower()
    i = l.find("(criterios:")
    while i >= 0:
        prof, j = 0, i
        while j < len(texto):
            prof += {"(": 1, ")": -1}.get(texto[j], 0)
            if prof == 0:
                break
            j += 1
        if prof:
            break
        citas = [c.strip() for c in texto[i + len("(criterios:"):j].split(",")]
        salida.append((i, j + 1, [c for c in citas if CITA.match(c)]))
        i = l.find("(criterios:", j + 1)
    return salida


def etiqueta_plan(comprobacion):
    """Las citas de la etiqueta al final de «Cómo se comprueba», o None sin etiqueta (ADR-0012, decisión 3A)."""
    t = (comprobacion or "").rstrip()
    ets = etiquetas(t)
    return ets[-1][2] if ets and ets[-1][1] == len(t) else None


def leer_pitch(texto, ct):
    """pitch.md → `jurado.pitch`: las citas de todas sus etiquetas; None sin fichero (ADR-0012, decisión 5B)."""
    if texto is None:
        return None
    return _dato([c for _, _, cs in etiquetas(texto) for c in cs], "git", ct)


# ------------------------------------------------------------------------------------------------ plan.md
def _filas(lineas):
    """Las filas de una tabla markdown, sin la cabecera ni la de guiones: [(línea, celdas)]."""
    salida, cabecera = [], False
    for linea in lineas:
        s = linea.strip()
        if not s.startswith("|"):
            continue
        celdas = servicios_mod._celdas(s)
        if not cabecera:
            cabecera = True
            continue
        if celdas and all(servicios_mod.SEPARADOR.match(c) for c in celdas if c):
            continue
        salida.append((s, celdas))
    return salida


def _quienes(texto, personas):
    """Las personas de una celda o de un «- <quién>:» de Descansos: @usuario, el nombre de coordinacion.md o «Todos»
    (todas las del equipo). None = todo el equipo: «Todos» sin equipo, o la celda vacía."""
    nombres = {p["nombre"].lower(): p["persona"] for p in personas}
    usuarios = {p["persona"].lower() for p in personas}
    salida, todos = [], False
    for x in re.split(r"\s*(?:,|/|&|\+|\by\b)\s*", (texto or "").strip()):
        x = x.strip()
        if not x:
            continue
        if _llano(x) in ("todos", "todo el equipo", "el equipo", "equipo", "todas"):
            todos = True
            salida += [p["persona"] for p in personas]
        elif x.startswith("@"):
            salida.append(x[1:].lower() if x[1:].lower() in usuarios else x[1:])
        else:
            salida.append(nombres.get(x.lower(), x))
    if todos and not personas:
        return None
    return [proyeccion.corta(p, TEXTO_MAX) for p in dict.fromkeys(salida)] or None


def _turno(texto, inicio, tz):
    """«<día> HH:MM–[<día>] HH:MM» → (desde, hasta, motivo)."""
    m = TURNO.match(_llano(texto))
    if not m or m.group(1) not in DIAS or (m.group(4) and m.group(4) not in DIAS):
        return None, None, "formato"
    if tz is None:
        return None, None, "sin_zona"
    if inicio is None:
        return None, None, "sin_inicio"
    try:
        desde, _ = resolver(f"{m.group(1)} {m.group(2)}:{m.group(3)}", inicio, tz)
        base = desde.date()
        if m.group(4):
            dia = base + timedelta(days=(DIAS[m.group(4)] - base.weekday()) % 7)
        else:
            dia = base
        hasta = _local(dia, m.group(5), m.group(6), tz)
        if hasta <= desde:
            hasta = _local(dia + timedelta(days=1), m.group(5), m.group(6), tz)
        return desde, hasta, None
    except (ValueError, TypeError, AttributeError):
        return None, None, "formato"


def leer_descansos(texto, personas, inicio, tz, ct):
    """«## Descansos» del plan (ADR-0013, decisión 9A): la tabla «| <turno> | <quién> |» (la de /hack-plan, los
    ejemplos 02 y 03 y G13/G14) y la lista «- <quién>: <turno>» de api.md §11.2. Una entrada por turno, con todas sus
    personas (null = todo el equipo). Lo que no se entiende sale con desde y hasta en null y su motivo: se enseña y no
    se usa."""
    lineas = _seccion(texto, "Descansos") or []
    filas = []
    for linea, celdas in _filas(lineas):
        turno, quien = (celdas + ["", ""])[:2]
        if TURNO.match(_llano(quien)) and not TURNO.match(_llano(turno)):
            turno, quien = quien, turno
        filas.append((linea, turno, quien))
    for linea in lineas:
        m = re.match(r"^\s*[-*]\s+(.+?):\s*(.+)$", linea)
        if m:
            filas.append((linea.strip(), m.group(2).strip(), m.group(1).strip()))
    salida = []
    for linea, turno, quien in filas:
        desde, hasta, motivo = _turno(turno, inicio, tz)
        salida.append({"personas": _quienes(quien, personas), "desde": _iso(desde),
                       "hasta": _iso(hasta), "texto": proyeccion.corta(linea, TEXTO_MAX), "motivo": motivo,
                       "fuente": "git", "observado_en": ct, "declarado": True})
    return salida


HITO_MOTIVO = {"vacio": "sin_dato", "relativo_sin_inicio": "sin_dato", "sin_inicio": "sin_dato"}


def leer_hitos(texto, inicio, tz, anio, ct, inicio_motivo):
    """«## Hitos del equipo» → [hora_declarada] con `nombre` = Qué y Cuándo resuelto como un Hasta. Los motivos de un
    Hasta que no están en $defs/hora_declarada (vacio, sin_inicio, relativo_sin_inicio) salen como sin_dato."""
    salida, anterior = [], None
    for _, celdas in _filas(_seccion(texto, "Hitos del equipo") or []):
        cuando, que = (celdas + ["", ""])[:2]
        dt, motivo = resolver(cuando, inicio, tz, anterior, anio, inicio_motivo)
        anterior = dt or anterior
        salida.append({"nombre": _txt(que), "valor": _iso(dt), "texto": _txt(cuando),
                       "motivo": HITO_MOTIVO.get(motivo, motivo), "donde": "plan.md", "fuente": "git",
                       "observado_en": ct, "declarado": True})
    return salida


def leer_plan(texto, personas, ct, inicio, tz, anio, inicio_motivo=None):
    """plan.md (con compilar.leer_plan, las mismas 5 columnas) → {ID: {orden_plan, titulo_plan, hasta, franja, citas,
    comprobacion}}. titulo_plan: el título de la fila del plan vigente, para «fuera de la entrega» (#56, 4). Lanza
    compilar.PlanMalo si el plan está mal formado."""
    filas = compilar.leer_plan(texto, personas)
    salida, por_persona = {}, {}
    for t in filas:
        por_persona.setdefault(t["nombre"], []).append(t)
    for fs in por_persona.values():
        anterior, resueltos = None, []
        for n, t in enumerate(fs, 1):
            dt, motivo = resolver(t["hasta"], inicio, tz, anterior, anio, inicio_motivo)
            anterior = dt or anterior
            resueltos.append(dt)
            salida[t["id"]] = {"orden_plan": _dato(n, "git", ct), "titulo_plan": _dato(t["titulo"], "git", ct),
                               "hasta": {"valor": _iso(dt), "texto": _txt(t["hasta"]), "motivo": motivo, "fuente": "git",
                                         "observado_en": ct, "declarado": True},
                               "citas": etiqueta_plan(t["comprobacion"]), "comprobacion": t["comprobacion"]}
        i, desde = 0, inicio                              # franjas: un bloque = las filas seguidas con el mismo Hasta
        while i < len(fs):
            j = i + 1
            while j < len(fs) and fs[j]["hasta"] == fs[i]["hasta"]:
                j += 1
            fin, compartida = resueltos[i], j - i
            if fin is None:
                valor, motivo = None, "sin_plazo"
            elif desde is None:
                valor, motivo = None, "sin_inicio"
            elif fin <= desde:
                valor, motivo = None, "orden"
            else:
                minutos = math.ceil((fin - desde).total_seconds() / 60 / compartida)
                valor, motivo = {"desde": _iso(_de(desde, tz)), "hasta": _iso(fin), "min": minutos,
                                 "compartida": compartida}, None
            for t in fs[i:j]:
                salida[t["id"]]["franja"] = {"valor": valor, "motivo": motivo, "fuente": "derivado", "observado_en": ct,
                                             "declarado": True}
            desde = fin or desde
            i = j
    return salida


def es_entrega(que):
    """La fila de Hitos que es la entrega: Qué es «Entrega» o empieza por «Entrega final» («Entrega temprana» es un
    hito más)."""
    l = _llano(que)
    return l.rstrip(" .:") == "entrega" or re.match(r"entrega final\b", l) is not None


def entregas_de_notas(notas, inicio, tz, anio):
    """Las notas de fuerza `dato` que afectan a la entrega y traen una hora que se resuelve como un Hasta (con día de la
    semana o fecha), para otras_entregas (ADR-0013, decisión 1A). Sin el texto de la nota (api.md §6 y §11.2, V):
    `texto` null y `cita`, la de la nota (su «AAAA-MM-DD HH:MM»)."""
    salida = []
    for n in notas:
        if n["fuerza"]["tipo"] != "dato" or not ENTREGA.search(n["afecta_a"] or ""):
            continue
        for m in EN_TEXTO.finditer(n["dijo"]):
            texto = re.sub(r"\s+a\s+las\s+", " ", m.group(0), flags=re.I).strip()
            if not re.search(rf"{_D}|{_M}", texto, re.I):
                continue
            dt, motivo = resolver(texto, inicio, tz, None, anio)
            if dt is not None:
                salida.append({"valor": _iso(dt), "texto": None, "motivo": None, "donde": "criterios.md",
                               "cita": n["cita"], "fuente": "git", "observado_en": n["observado_en"],
                               "declarado": True})
                break
    return salida


def conexiones(comprobacion, texto_servicios):
    """Las claves de las conexiones de servicios.md cuya Prueba aparece tal cual en «Cómo se comprueba» (ADR-0012,
    decisión 4A)."""
    if not texto_servicios:
        return []
    return [f["clave"] for f in servicios_mod.leer(texto_servicios)["filas"]
            if f["tabla"] == servicios_mod.CONEXIONES and f["campos"]["prueba"] and f["campos"]["prueba"] in comprobacion]


# ------------------------------------------------------------------------------------------------ todo junto
def calcular(textos, cts, personas, vista_jurado, ruta_critica):
    """Lo de M10 que va a estado.json, leído de los ficheros de origin/main.

    textos: {criterios, plan, pitch, equipo, servicios} → texto, o None si el fichero no está; cts: lo mismo → hora
    ISO de su último commit, y `punta` → la del commit de la punta (para los que no están). Devuelve
    {jurado, ruta, tareas: {ID: campos}, avisos}; `jurado` y `ruta`, None con su interruptor apagado."""
    def ct(k):
        return cts.get(k) or cts["punta"]

    anio_de = lambda k: int(ct(k)[:4])
    eq = leer_equipo(textos.get("equipo"), ct("equipo"), anio_de("equipo"))
    tz, inicio, entrega = eq["tz"], (eq["inicio"] or {}).get("_dt"), (eq["entrega"] or {}).get("_dt")
    anio = (inicio or entrega).astimezone(tz).year if (inicio or entrega) else anio_de("plan")
    inicio_motivo = (eq["inicio"] or {}).get("motivo")
    salida = {"jurado": None, "ruta": None, "tareas": {}, "avisos": list(eq["avisos"])}
    plan = None
    if textos.get("plan") is not None:
        try:
            plan = leer_plan(textos["plan"], personas, ct("plan"), inicio, tz, anio, inicio_motivo)
        except compilar.PlanMalo:
            plan = None
    if vista_jurado:
        crit = leer_criterios(textos.get("criterios"), ct("criterios"), tz)
        salida["jurado"] = {"fichero": crit["fichero"], "notas": crit["notas"],
                            "pitch": leer_pitch(textos.get("pitch"), ct("pitch")), "zona": eq["zona"]}
        ct_con = max(ct("plan"), ct("servicios"))
        for tid, x in (plan or {}).items():
            campos = salida["tareas"].setdefault(tid, {})
            if x["citas"] is not None:
                campos["criterios"] = _dato(x["citas"], "git", ct("plan"))
            claves = conexiones(x["comprobacion"], textos.get("servicios"))
            if claves:
                campos["conexiones"] = _dato(claves, "git", ct_con)
    if ruta_critica:
        texto_plan = textos.get("plan")
        filas = leer_hitos(texto_plan, inicio, tz, anio, ct("plan"), inicio_motivo) if texto_plan is not None else []
        hitos = [h for h in filas if not es_entrega(h["nombre"])]
        notas = salida["jurado"]["notas"] if salida["jurado"] else \
            leer_criterios(textos.get("criterios"), ct("criterios"), tz)["notas"]
        otras = eq["otras"] + [h for h in filas if es_entrega(h["nombre"])] + entregas_de_notas(notas, inicio, tz, anio)
        salida["ruta"] = {"equipo": eq["equipo"], "zona": eq["zona"], "inicio": _publica(eq["inicio"]),
                          "entrega": _publica(eq["entrega"]), "otras_entregas": otras, "hitos": hitos,
                          "descansos": leer_descansos(texto_plan, personas, inicio, tz, ct("plan"))
                          if texto_plan is not None else []}
        for tid, x in (plan or {}).items():
            campos = salida["tareas"].setdefault(tid, {})
            campos.update(hasta=x["hasta"], franja=x["franja"], orden_plan=x["orden_plan"], titulo_plan=x["titulo_plan"])
    return salida
