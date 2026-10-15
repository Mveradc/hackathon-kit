# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Relay del Hackathon OS (M8d, api.md §3): recibe eventos y latidos de los demonios, calcula estado.json con
modelo.py y lo sirve por GET /v1/estado y por SSE. Desde M8e, sondea GitHub (las tareas `hk-tarea`, api.md §8) con
el gh de quien coordina. Solo biblioteca estándar (ADR-0005).

Uso normal: `hk-os relay` (cli.py). Directo, para pruebas:
  uv run --no-project hkos/relay.py --dir <carpeta> --equipo <coordinacion.md> [--ip 127.0.0.1] [--puerto 7777]
"""
import argparse
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github  # noqa: E402
from esquema import Esquema  # noqa: E402
from estados import fecha, iso  # noqa: E402
from modelo import calcular  # noqa: E402
from red import Servidor, ahora_iso, conf, equipo  # noqa: E402

LOTE_MAX = 200
CUERPO_MAX = 2 * 1024 * 1024
RECALCULO_MIN_S = 0.25          # como mucho 4 recálculos por segundo
RECALCULO_RELOJ_S = 5           # y uno cada 5 s, para que la presencia caduque sola (R-18)
PING_S = 20
SONDEO_GITHUB_S = 30            # api.md §8
TAILNET = ipaddress.ip_network("100.64.0.0/10")
PRIVADAS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


class Invalido(Exception):
    def __init__(self, error, campo=None, indice=None):
        super().__init__(error)
        self.error, self.campo, self.indice = error, campo, indice


def ip_permitida(ip):
    """R-32: 127.0.0.1, LAN privada o Tailscale. Nunca 0.0.0.0 ni una IP pública."""
    try:
        d = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return d.version == 4 and (d.is_loopback or d in TAILNET or any(d in n for n in PRIVADAS))


def ip_de_lan():
    """La IP de la interfaz de la ruta por defecto (no envía nada: connect de UDP solo elige la interfaz)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def iso_us(t):
    """Segundos de época → ISO 8601 en UTC."""
    return iso(datetime.fromtimestamp(t, timezone.utc))


class Relay:
    """El estado del relay, sin HTTP. `ahora` se puede inyectar en las pruebas."""

    def __init__(self, carpeta, personas, ahora=ahora_iso, sondeo=None, umbral_parada_s=1200):
        self.carpeta, self.personas, self.ahora = carpeta, personas, ahora
        self.sondeo, self.umbral_parada_s = sondeo, umbral_parada_s
        os.makedirs(carpeta, exist_ok=True)
        self.esquema = Esquema("eventos.schema.json")
        self.token = self._token()
        self.eventos, self.ids = [], set()
        self.latidos = {}             # persona → [eventos latido] (el último latido sustituye al anterior)
        self.corruptas = {}           # persona → {veces, primera_vez, ultima_vez}
        self.descartados = 0
        self.lock = threading.Lock()
        self.cambio = threading.Condition(self.lock)
        self.sucio = threading.Event()
        self.version, self.estado, self.texto, self._huella = 0, None, b"", None
        self._cargar()
        if self.sondeo:                           # sin GitHub al arrancar, el último estado conocido (constitución VIII)
            try:
                with open(os.path.join(carpeta, "github.json"), encoding="utf-8") as f:
                    self.sondeo.de_disco(json.load(f))
            except (OSError, ValueError):
                pass
        self.recalcular()

    # --- persistencia ---
    def _token(self):
        ruta = os.path.join(self.carpeta, "token")
        try:
            with open(ruta, encoding="utf-8") as f:
                t = f.read().strip()
            if t:
                return t
        except OSError:
            pass
        t = secrets.token_urlsafe(24)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(t + "\n")
        return t

    def _cargar(self):
        """Relee eventos.jsonl al arrancar, saltando líneas rotas: los repetidos se reconocen tras reiniciar."""
        try:
            f = open(os.path.join(self.carpeta, "eventos.jsonl"), "rb")
        except OSError:
            return
        with f:
            for linea in f:
                try:
                    e = json.loads(linea.decode("utf-8"))
                except ValueError:
                    continue
                if isinstance(e, dict) and e.get("id") and e["id"] not in self.ids:
                    self.ids.add(e["id"])
                    self.eventos.append(e)

    # --- entradas ---
    def recibir(self, cuerpo):
        """POST /v1/eventos. Lote entero o nada: si un evento no valida, Invalido con su índice y no se guarda nada."""
        if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("eventos"), list):
            raise Invalido("se espera {\"eventos\": [...]}", "eventos")
        lote = cuerpo["eventos"]
        if len(lote) > LOTE_MAX:
            raise Invalido(f"más de {LOTE_MAX} eventos en el lote", "eventos")
        for i, e in enumerate(lote):
            err = self.esquema.error(e)
            if err:
                self.descartados += 1
                raise Invalido(err[1], err[0] or "/", i)
        with self.lock:
            nuevos, vistos = [], set()
            for e in lote:
                if e["id"] in self.ids or e["id"] in vistos:
                    continue
                vistos.add(e["id"])
                nuevos.append(e)
            if nuevos:
                datos = b"".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
                                 for e in nuevos)
                with open(os.path.join(self.carpeta, "eventos.jsonl"), "ab") as f:
                    f.write(datos)
                    f.flush()
                    os.fsync(f.fileno())
                self.ids |= vistos
                self.eventos += nuevos
        if nuevos:
            self.sucio.set()
        return {"aceptados": len(nuevos), "repetidos": len(lote) - len(nuevos)}

    def latido(self, cuerpo):
        """POST /v1/latido: la lista completa de actores abiertos de una persona, cada uno con su última señal."""
        if not isinstance(cuerpo, dict) or not isinstance(cuerpo.get("persona"), str):
            raise Invalido("falta persona", "persona")
        persona = cuerpo["persona"]
        actores = cuerpo.get("actores", [])
        if not isinstance(actores, list):
            raise Invalido("actores debe ser una lista", "actores")
        eventos = []
        for i, a in enumerate(actores):
            if not isinstance(a, dict):
                raise Invalido("actor mal formado", "actores", i)
            actor = {"persona": persona, "papel": a.get("papel")}
            for k in ("sesion", "agente", "worktree"):
                if a.get(k) is not None:
                    actor[k] = a[k]
            e = {"v": 1, "id": f"latido-{persona}-{i}", "ts": a.get("ultima_senal"), "actor": actor,
                 "tipo": "latido", "fuente": "hook"}
            if a.get("tarea"):
                e["tarea"] = a["tarea"]
            err = self.esquema.error(e)
            if err:
                raise Invalido(err[1], f"actores/{i}{err[0]}", i)
            eventos.append(e)
        n = cuerpo.get("lineas_corruptas", 0)
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise Invalido("lineas_corruptas debe ser un entero ≥ 0", "lineas_corruptas")
        with self.lock:
            self.latidos[persona] = eventos
            if n:
                ahora = self.ahora()
                c = self.corruptas.setdefault(persona, {"veces": 0, "primera_vez": ahora})
                if c["veces"] != n:
                    c["veces"], c["ultima_vez"] = n, ahora
        self.sucio.set()

    # --- estado ---
    def recalcular(self):
        with self.lock:
            eventos = list(self.eventos)
            for lista in self.latidos.values():
                eventos += lista
            corruptas = {p: dict(c) for p, c in self.corruptas.items()}
        ahora = self.ahora()
        # Un portátil con el reloj adelantado no debe quedar invisible hasta que el del relay lo alcance.
        if eventos:
            ultimo = max(eventos, key=lambda e: fecha(e["ts"]))["ts"]
            if fecha(ultimo) > fecha(ahora):
                ahora = ultimo
        fuentes = {"relay": {"valor": "ok", "fuente": "derivado", "observado_en": ahora}}
        tareas, issues, disc = [], {}, []
        if self.sondeo:
            with self.lock:
                tareas, issues, disc, escrituras = self.sondeo.resultado(fecha(ahora))
                visto = self.sondeo.ultimo_ok
                fuentes["github"] = {"valor": self.sondeo.estado, "fuente": "github",
                                     "observado_en": iso_us(visto) if visto else ahora}
            if escrituras >= github.TOPE_HORA:
                print(f"relay: {escrituras} escrituras del equipo a GitHub en la última hora (tope {github.TOPE_HORA}, R-30)",
                      file=sys.stderr, flush=True)
        de_git = [e["ts"] for e in eventos if e.get("fuente") == "git"]
        if de_git:
            fuentes["git"] = {"valor": "ok", "fuente": "git", "observado_en": max(de_git, key=fecha)}
        estado = calcular(tareas, issues, eventos, self.personas, ahora, self.umbral_parada_s, fuentes, disc)
        for p, c in sorted(corruptas.items()):
            estado["discrepancias"].append({"tipo": "linea_corrupta", "persona": p, "veces": c["veces"],
                                            "primera_vez": c["primera_vez"], "ultima_vez": c.get("ultima_vez", c["primera_vez"]),
                                            "detalle": f"{c['veces']} líneas rotas en los JSONL de {p}"})
        # Sin la hora del cálculo ni la del relay: solo hay versión nueva (y SSE) si cambia algo de verdad.
        sin_hora = dict(estado, generado_en=None, fuentes={k: v for k, v in estado["fuentes"].items() if k != "relay"})
        huella = hashlib.sha256(json.dumps(sin_hora, sort_keys=True).encode("utf-8")).hexdigest()
        with self.cambio:
            if huella != self._huella:
                self._huella = huella
                self.version += 1
                self.estado = estado
                self.texto = json.dumps(estado, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                self.cambio.notify_all()

    def bucle(self, parar):
        """Recalcula tras cada lote (como mucho cada RECALCULO_MIN_S) y cada RECALCULO_RELOJ_S."""
        while not parar.is_set():
            self.sucio.wait(RECALCULO_RELOJ_S)
            self.sucio.clear()
            try:
                self.recalcular()
            except Exception as ex:  # un fallo de cálculo no tumba el relay
                print(f"relay: error al recalcular: {ex!r}", file=sys.stderr, flush=True)
            parar.wait(RECALCULO_MIN_S)

    def bucle_github(self, parar):
        """Sondeo de GitHub cada SONDEO_GITHUB_S (api.md §8). Guarda la instantánea para arrancar sin GitHub."""
        while not parar.is_set():
            try:
                with self.lock:
                    estado_antes = self.sondeo.estado
                cambio = self.sondeo.sondear()
                if cambio:
                    with self.lock:
                        foto = self.sondeo.a_disco()
                    tmp = os.path.join(self.carpeta, "github.json.tmp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(foto, f)
                    os.replace(tmp, os.path.join(self.carpeta, "github.json"))
                if cambio or self.sondeo.estado != estado_antes:
                    self.sucio.set()
            except Exception as ex:  # el sondeo no tumba el relay
                print(f"relay: error al sondear GitHub: {ex!r}", file=sys.stderr, flush=True)
            parar.wait(SONDEO_GITHUB_S)

    def actual(self):
        with self.lock:
            return self.version, self.texto


def manejador(relay):
    class Manejador(BaseHTTPRequestHandler):
        server_version = "hk-os-relay"
        sys_version = ""

        def log_message(self, *args):
            pass

        def _json(self, codigo, obj=None, cabeceras=()):
            datos = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            if obj is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            for k, v in cabeceras:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            if datos:
                self.wfile.write(datos)

        def _autorizado(self):
            dado = self.headers.get("Authorization", "")
            if hmac.compare_digest(dado.encode("utf-8"), f"Bearer {relay.token}".encode("utf-8")):
                return True
            self._json(401, {"error": "token"})
            return False

        def _cuerpo(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise Invalido("Content-Length no válido")
            if n > CUERPO_MAX:
                raise Invalido("cuerpo demasiado grande")
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise Invalido("el cuerpo no es JSON")

        def do_POST(self):
            if not self._autorizado():
                return
            try:
                if self.path == "/v1/eventos":
                    self._json(200, relay.recibir(self._cuerpo()))
                elif self.path == "/v1/latido":
                    relay.latido(self._cuerpo())
                    self._json(204)
                else:
                    self._json(404, {"error": "ruta"})
            except Invalido as ex:
                err = {"error": ex.error, "campo": ex.campo}
                if ex.indice is not None:
                    err["indice"] = ex.indice
                self._json(400, err)

        def do_GET(self):
            if not self._autorizado():
                return
            if self.path == "/v1/estado":
                version, texto = relay.actual()
                etiqueta = f'"{version}"'
                if self.headers.get("If-None-Match") == etiqueta:
                    self._json(304, cabeceras=[("ETag", etiqueta)])
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("ETag", etiqueta)
                self.send_header("Content-Length", str(len(texto)))
                self.end_headers()
                self.wfile.write(texto)
            elif self.path == "/v1/stream":
                self._stream()
            else:
                self._json(404, {"error": "ruta"})

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            enviada = None
            try:
                while True:
                    with relay.cambio:
                        if relay.version == enviada:
                            relay.cambio.wait(PING_S)
                        version, texto = relay.version, relay.texto
                    if version != enviada:
                        self.wfile.write(b"id: %d\nevent: estado\ndata: " % version + texto + b"\n\n")
                        enviada = version
                    else:
                        self.wfile.write(b"event: ping\ndata: \n\n")
                    self.wfile.flush()
            except OSError:
                return

    return Manejador


def sondeo_de(os_md, equipo_md, personas, aviso):
    """El sondeo de GitHub del relay: repo de `repo_tareas:` (os.md) o `repo:` (coordinacion.md) y el gh de quien
    coordina. Sin repo o sin sesión de gh, el relay sigue sin GitHub (constitución VIII) y lo dice."""
    repo = (conf(os_md, "repo_tareas") if os_md else "") or conf(equipo_md, "repo")
    if not repo or "<" in repo:
        aviso("Sin GitHub: no hay repo en coordinacion.md ni repo_tareas en os.md.")
        return None
    token = github.token_de_gh()
    if not token:
        aviso("Sin GitHub: gh no tiene sesión en este portátil (gh auth login).")
        return None
    cliente = github.Cliente(repo, token, base=os.environ.get("HKOS_GITHUB_API", github.API))
    return github.Sondeo(cliente, {p["persona"] for p in personas})


def servir(carpeta, equipo_md, ip, puerto, aviso=print, os_md=None, con_github=True):
    if not ip_permitida(ip):
        raise SystemExit(f"hk-os relay: {ip} no es 127.0.0.1, una IP privada de LAN ni una de Tailscale; "
                         "el relay no escucha ahí (R-32). Indica otra con --ip.")
    personas = equipo(equipo_md)
    sondeo = sondeo_de(os_md, equipo_md, personas, aviso) if con_github else None
    try:
        umbral = 60 * float(conf(os_md, "umbral_parada_min") or 20) if os_md else 1200
    except ValueError:
        umbral = 1200
    relay = Relay(carpeta, personas, sondeo=sondeo, umbral_parada_s=umbral)
    servidor = Servidor((ip, puerto), manejador(relay))
    parar = threading.Event()
    threading.Thread(target=relay.bucle, args=(parar,), daemon=True).start()
    if sondeo:
        threading.Thread(target=relay.bucle_github, args=(parar,), daemon=True).start()
        aviso(f"Sondeo de GitHub: {sondeo.c.repo}, cada {SONDEO_GITHUB_S} s.")
    url = f"http://{ip}:{servidor.server_address[1]}"
    aviso(f"Relay del Hackathon OS en {url} ({len(personas)} personas en coordinacion.md, "
          f"{len(relay.eventos)} eventos guardados).")
    aviso(f"Token: {relay.token}")
    aviso(f"Cada persona, en su clon: hk-os unir {url} {relay.token}")
    try:
        servidor.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        servidor.server_close()


def main(argv=None):
    p = argparse.ArgumentParser(description="Relay del Hackathon OS (api.md §3)")
    p.add_argument("--dir", required=True, help="carpeta del registro y del token (<git común>/hackathon/os/relay)")
    p.add_argument("--equipo", required=True, help="ruta de .hackathon/coordinacion.md")
    p.add_argument("--ip", help="IP de escucha (por defecto, la de la LAN)")
    p.add_argument("--puerto", type=int, default=7777)
    p.add_argument("--os", help="ruta de .hackathon/os.md (repo_tareas, umbral_parada_min)")
    p.add_argument("--sin-github", action="store_true", help="no sondear GitHub")
    a = p.parse_args(argv)
    ip = a.ip or ip_de_lan()
    if not ip:
        raise SystemExit("hk-os relay: no encuentro la IP de la LAN; indícala con --ip.")
    servir(a.dir, a.equipo, ip, a.puerto, aviso=lambda s: print(s, flush=True), os_md=a.os, con_github=not a.sin_github)


if __name__ == "__main__":
    main()
