"""Validador mínimo de JSON Schema para los contratos del Hackathon OS (M8d). Solo biblioteca estándar (ADR-0005).

Lee los esquemas de docs/hackathon-os/contratos/ (no una copia) y cubre solo las palabras clave que usan: type,
required, properties, additionalProperties, const, enum, pattern, format date-time, items, maxLength, minimum,
maximum, anyOf y $ref locales. Una palabra clave que no conoce hace fallar la carga, para que un cambio en el
esquema no se valide a medias sin avisar. Las pruebas comparan sus veredictos con los de jsonschema.
"""
import json
import os
import re

CONTRATOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "hackathon-os", "contratos")
CONOCIDAS = {"$schema", "$id", "$defs", "$ref", "title", "description", "default", "type", "required", "properties",
             "additionalProperties", "const", "enum", "pattern", "format", "items", "maxLength", "minimum", "maximum",
             "anyOf"}
# RFC 3339 (format date-time de JSON Schema): fecha, «T», hora con fracción opcional y zona obligatoria.
FECHA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])[Tt]([01]\d|2[0-3]):[0-5]\d:([0-5]\d|60)(\.\d+)?"
                   r"([Zz]|[+-]([01]\d|2[0-3]):[0-5]\d)$")
TIPOS = {"object": dict, "array": list, "string": str, "boolean": bool}


class Esquema:
    def __init__(self, nombre):
        with open(os.path.join(CONTRATOS, nombre), encoding="utf-8") as f:
            self.raiz = json.load(f)
        self._revisar(self.raiz)

    def _revisar(self, s):
        if not isinstance(s, dict):
            return
        desconocidas = set(s) - CONOCIDAS
        if desconocidas:
            raise ValueError(f"palabras clave no soportadas: {sorted(desconocidas)}")
        for k in ("properties", "$defs"):
            for v in s.get(k, {}).values():
                self._revisar(v)
        for k in ("items", "additionalProperties"):
            self._revisar(s.get(k))
        for v in s.get("anyOf", []):
            self._revisar(v)

    def error(self, valor):
        """None si valida; si no, (ruta del campo, motivo) del primer fallo."""
        return self._error(self.raiz, valor, "")

    def valido(self, valor):
        return self.error(valor) is None

    def _error(self, s, v, ruta):
        if "$ref" in s:
            destino = self.raiz
            for parte in s["$ref"].lstrip("#/").split("/"):
                destino = destino[parte]
            return self._error(destino, v, ruta)
        if "const" in s and not _igual(v, s["const"]):
            return ruta, f"debe ser {s['const']!r}"
        if "enum" in s and not any(_igual(v, x) for x in s["enum"]):
            return ruta, "valor fuera de la lista"
        if "anyOf" in s and all(self._error(x, v, ruta) for x in s["anyOf"]):
            return ruta, "no cumple ninguna alternativa"
        t = s.get("type")
        if t == "integer":
            if isinstance(v, bool) or not isinstance(v, int):
                return ruta, "debe ser un entero"
        elif t == "null":
            if v is not None:
                return ruta, "debe ser null"
        elif t and (isinstance(v, bool) != (t == "boolean") or not isinstance(v, TIPOS[t])):
            return ruta, f"debe ser {t}"
        if isinstance(v, str):
            if "maxLength" in s and len(v) > s["maxLength"]:
                return ruta, f"más de {s['maxLength']} caracteres"
            if "pattern" in s and not re.search(s["pattern"], v):
                return ruta, "no cumple el patrón"
            if s.get("format") == "date-time" and not FECHA.match(v):
                return ruta, "no es una fecha RFC 3339"
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if "minimum" in s and v < s["minimum"]:
                return ruta, f"menor que {s['minimum']}"
            if "maximum" in s and v > s["maximum"]:
                return ruta, f"mayor que {s['maximum']}"
        if isinstance(v, dict):
            for k in s.get("required", []):
                if k not in v:
                    return f"{ruta}/{k}", "falta"
            props = s.get("properties", {})
            for k, x in v.items():
                if k in props:
                    e = self._error(props[k], x, f"{ruta}/{k}")
                elif s.get("additionalProperties") is False:
                    return f"{ruta}/{k}", "campo no permitido"
                elif isinstance(s.get("additionalProperties"), dict):
                    e = self._error(s["additionalProperties"], x, f"{ruta}/{k}")
                else:
                    e = None
                if e:
                    return e
        if isinstance(v, list) and isinstance(s.get("items"), dict):
            for i, x in enumerate(v):
                e = self._error(s["items"], x, f"{ruta}/{i}")
                if e:
                    return e
        return None


def _igual(a, b):
    """Igualdad de JSON: 1 no es True."""
    return type(a) is type(b) and a == b if isinstance(a, bool) or isinstance(b, bool) else a == b
