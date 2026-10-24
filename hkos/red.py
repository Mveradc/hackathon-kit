"""Lo común de red del relay y del demonio (M8d): servidor HTTP con hilos y lectura de .hackathon/*.md."""
import os
import re
import socket
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer


class Servidor(ThreadingHTTPServer):
    """El puerto es el bloqueo del demonio (ADR-0004): un segundo bind tiene que fallar.

    ThreadingHTTPServer pone SO_REUSEADDR, y en Windows eso deja escuchar a dos procesos en el mismo puerto. Allí se
    pide SO_EXCLUSIVEADDRUSE; en Linux y macOS, SO_REUSEADDR no permite dos escuchas y evita esperar al reiniciar."""
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def leer_texto(ruta):
    """Un .md del equipo, tolerando BOM y UTF-16 (como hk_leer)."""
    try:
        with open(ruta, "rb") as f:
            b = f.read()
    except OSError:
        return ""
    if b.startswith((b"\xff\xfe", b"\xfe\xff")):
        return b.decode("utf-16", errors="replace")
    return b.decode("utf-8-sig", errors="replace")


def conf(ruta, clave):
    """Valor de «clave: valor» en os.md o coordinacion.md, sin el comentario de detrás. "" si no está."""
    for linea in leer_texto(ruta).splitlines():
        m = re.match(rf"^{re.escape(clave)}:[ \t]*([^#]*)", linea.strip())
        if m:
            return m.group(1).strip()
    return ""


def es_si(valor):
    """«sí», «si» o «yes» (como os_activo de comun.sh)."""
    return (valor or "").strip().lower() in ("sí", "si", "yes")


def web_nueva(os_md):
    """M9a (api.md §0): `web_nueva: sí` en os.md. Sin la línea, no."""
    return bool(os_md) and es_si(conf(os_md, "web_nueva"))


def vista_jurado(os_md):
    """M10 (api.md §11.1): `vista_jurado: sí` en os.md. Sin la línea, no. Solo lo lee el relay."""
    return bool(os_md) and es_si(conf(os_md, "vista_jurado"))


def ruta_critica(os_md):
    """M10 (api.md §11.1): `ruta_critica: sí` en os.md. Sin la línea, no. Solo lo lee el relay."""
    return bool(os_md) and es_si(conf(os_md, "ruta_critica"))


def fusion_estructural(os_md):
    """M11 (api.md §0, ADR-0014): `fusion_estructural: sí` en os.md. Sin la línea, no. Lo lee el relay (y el MCP, para
    la descripción de `colisiones`)."""
    return bool(os_md) and es_si(conf(os_md, "fusion_estructural"))


def equipo(ruta):
    """Las personas de la tabla de coordinacion.md: [{persona, nombre}], con el usuario de GitHub en minúsculas.
    Las filas sin GitHub («—») no cuentan."""
    salida = []
    for linea in leer_texto(ruta).splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*@([A-Za-z0-9-]+)\s*\|", linea)
        if m:
            salida.append({"persona": m.group(2).lower(), "nombre": m.group(1)})
    return salida
