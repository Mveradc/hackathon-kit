"""GitHub falso para las pruebas del Hackathon OS (M8e): un servidor HTTP de la biblioteca estándar con lo que usan
hkos/github.py y hkos/compilar.py, con el mismo comportamiento que se observa en GitHub:
- issues con etiquetas, autor, estado, `state_reason`, `updated_at` y `issue_dependencies_summary`;
- eventos de issue del repo (assigned, closed, reopened, labeled, unlabeled, renamed), los más nuevos primero;
- comentarios del repo;
- dependencias nativas `blocked_by` (por `issue_id`);
- ETag y 304 en las listas, paginación con Link, 429 a voluntad;
- un contador de escrituras por cuenta, para el tope de R-30.

El token es «tok-<usuario>». El reloj es inyectable (`reloj`, segundos de época). Como en GitHub (comprobado en el
sandbox, M8e), añadir o quitar una dependencia deja `blocked_by_added`/`blocking_added` y no cambia el `updated_at`;
`deps_actualizan=True` simula lo contrario."""
import hashlib
import json
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class GitHubFalso:
    def __init__(self, repo="equipo/reto", reloj=time.time, deps_actualizan=False):
        self.repo, self.reloj, self.deps_actualizan = repo, reloj, deps_actualizan
        self.issues, self.eventos, self.comentarios = {}, [], []
        self.etiquetas = set()
        self.escrituras = []                     # (hora, usuario, método, ruta)
        self.lecturas = {"200": 0, "304": 0}
        self.limitar = 0                         # >0: las siguientes peticiones dan 429 (se descuenta)
        self.limitar_403 = 0                     # >0: las siguientes dan 403 con X-RateLimit-Remaining: 0 (M8h)
        self.peticiones = 0                      # todas las que llegan con usuario, también las limitadas (M8h)
        self.lock = threading.Lock()
        self._n, self._ev = 0, 0
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), self._manejador())
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def cerrar(self):
        self.srv.shutdown()
        self.srv.server_close()

    # --- estado ---
    def _evento(self, numero, tipo, actor, **mas):
        self._ev += 1
        e = {"id": self._ev, "event": tipo, "actor": {"login": actor}, "created_at": iso(self.reloj()),
             "issue": {"number": numero}}
        for k, v in mas.items():
            e[k] = {"login": v} if k == "assignee" else v
        self.eventos.append(e)

    def _toca(self, i):
        i["updated_at"] = iso(self.reloj())

    def crear(self, usuario, title, body="", labels=()):
        self._n += 1
        n = self._n
        i = {"id": n * 1000 + 7, "number": n, "title": title, "body": body, "user": {"login": usuario}, "state": "open",
             "state_reason": None, "labels": [{"name": l} for l in labels], "assignees": [], "created_at": iso(self.reloj()),
             "updated_at": iso(self.reloj()), "_bloqueado_por": []}
        self.issues[n] = i
        for l in labels:
            self.etiquetas.add(l)
            self._evento(n, "labeled", usuario, label={"name": l})
        return i

    def _vista(self, i):
        v = {k: x for k, x in i.items() if not k.startswith("_")}
        abiertos = [b for b in i["_bloqueado_por"] if self.issues[b]["state"] == "open"]
        v["issue_dependencies_summary"] = {"blocked_by": len(abiertos), "total_blocked_by": len(i["_bloqueado_por"]),
                                           "blocking": 0, "total_blocking": 0}
        return v

    def escrituras_por_hora(self):
        return [(t, u) for t, u, _, _ in self.escrituras]

    # --- HTTP ---
    def _manejador(self):
        gh = self

        class M(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _usuario(self):
                a = self.headers.get("Authorization", "")
                m = re.match(r"Bearer tok-([A-Za-z0-9-]+)$", a)
                return m.group(1) if m else None

            def _responde(self, codigo, datos=None, cabeceras=()):
                cuerpo = b"" if datos is None else json.dumps(datos).encode("utf-8")
                self.send_response(codigo)
                for k, v in cabeceras:
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                if cuerpo:
                    self.wfile.write(cuerpo)

            def _lista(self, elementos, q):
                por = int(q.get("per_page", ["30"])[0])
                pag = int(q.get("page", ["1"])[0])
                trozo = elementos[(pag - 1) * por: pag * por]
                etag = '"' + hashlib.sha256(json.dumps(trozo, sort_keys=True).encode()).hexdigest()[:20] + '"'
                cab = [("ETag", etag)]
                if pag * por < len(elementos):
                    u = urlparse(self.path)
                    q2 = dict(q, page=[str(pag + 1)])
                    sig = gh.base + u.path + "?" + "&".join(f"{k}={v[0]}" for k, v in q2.items())
                    cab.append(("Link", f'<{sig}>; rel="next"'))
                if self.headers.get("If-None-Match") == etag:
                    gh.lecturas["304"] += 1
                    self._responde(304, cabeceras=[("ETag", etag)])
                else:
                    gh.lecturas["200"] += 1
                    self._responde(200, trozo, cab)

            def _cuerpo(self):
                n = int(self.headers.get("Content-Length", "0"))
                return json.loads(self.rfile.read(n) or b"{}")

            def _previo(self):
                usuario = self._usuario()
                if not usuario:
                    self._responde(401, {"message": "Bad credentials"})
                    return None
                gh.peticiones += 1
                if gh.limitar > 0:
                    gh.limitar -= 1
                    self._responde(429, {"message": "secondary rate limit"}, [("Retry-After", "60")])
                    return None
                if gh.limitar_403 > 0:          # M8h (G7b): el límite primario, 403 con el contador a cero
                    gh.limitar_403 -= 1
                    self._responde(403, {"message": "API rate limit exceeded"},
                                   [("X-RateLimit-Remaining", "0"), ("X-RateLimit-Reset", str(int(gh.reloj()) + 120))])
                    return None
                return usuario

            def do_GET(self):
                if not self._previo():
                    return
                u = urlparse(self.path)
                q = parse_qs(u.query)
                r = f"/repos/{gh.repo}"
                with gh.lock:
                    if u.path == "/user":
                        return self._responde(200, {"login": self._usuario()})
                    if u.path == f"{r}/issues":
                        lab = q.get("labels", [None])[0]
                        estado = q.get("state", ["open"])[0]
                        xs = [gh._vista(i) for i in sorted(gh.issues.values(), key=lambda i: -i["number"])
                              if (not lab or lab in [l["name"] for l in i["labels"]]) and (estado == "all" or i["state"] == estado)]
                        return self._lista(xs, q)
                    if u.path == f"{r}/issues/events":
                        return self._lista(list(reversed(gh.eventos)), q)
                    if u.path == f"{r}/issues/comments":
                        return self._lista(list(reversed(gh.comentarios)), q)
                    m = re.fullmatch(rf"{r}/issues/(\d+)/dependencies/blocked_by", u.path)
                    if m:
                        i = gh.issues[int(m.group(1))]
                        return self._lista([gh._vista(gh.issues[b]) for b in i["_bloqueado_por"]], q)
                    m = re.fullmatch(rf"{r}/labels/(.+)", u.path)
                    if m:
                        nombre = m.group(1).replace("%3A", ":")
                        return self._responde(200 if nombre in gh.etiquetas else 404, {"name": nombre})
                self._responde(404, {"message": "Not Found"})

            def _escribe(self, metodo):
                usuario = self._previo()
                if not usuario:
                    return
                u = urlparse(self.path)
                r = f"/repos/{gh.repo}"
                d = self._cuerpo() if metodo != "DELETE" else {}
                with gh.lock:
                    gh.escrituras.append((gh.reloj(), usuario, metodo, u.path))
                    if metodo == "POST" and u.path == f"{r}/issues":
                        return self._responde(201, gh._vista(gh.crear(usuario, d["title"], d.get("body", ""), d.get("labels", []))))
                    if metodo == "POST" and u.path == f"{r}/labels":
                        gh.etiquetas.add(d["name"])
                        return self._responde(201, {"name": d["name"]})
                    m = re.fullmatch(rf"{r}/issues/(\d+)", u.path)
                    if metodo == "PATCH" and m:
                        i = gh.issues[int(m.group(1))]
                        if "title" in d and d["title"] != i["title"]:
                            gh._evento(i["number"], "renamed", usuario, rename={"from": i["title"], "to": d["title"]})
                            i["title"] = d["title"]
                        if "body" in d:
                            i["body"] = d["body"]
                        if "labels" in d:
                            antes = {l["name"] for l in i["labels"]}
                            for l in set(d["labels"]) - antes:
                                gh.etiquetas.add(l)
                                gh._evento(i["number"], "labeled", usuario, label={"name": l})
                            for l in antes - set(d["labels"]):
                                gh._evento(i["number"], "unlabeled", usuario, label={"name": l})
                            i["labels"] = [{"name": l} for l in d["labels"]]
                        if "state" in d and d["state"] != i["state"]:
                            i["state"] = d["state"]
                            i["state_reason"] = d.get("state_reason") if d["state"] == "closed" else "reopened"
                            gh._evento(i["number"], "closed" if d["state"] == "closed" else "reopened", usuario)
                        gh._toca(i)
                        return self._responde(200, gh._vista(i))
                    m = re.fullmatch(rf"{r}/issues/(\d+)/comments", u.path)
                    if metodo == "POST" and m:
                        n = int(m.group(1))
                        c = {"id": len(gh.comentarios) + 1, "user": {"login": usuario}, "body": d.get("body", ""),
                             "created_at": iso(gh.reloj()), "issue_url": f"{gh.base}{r}/issues/{n}"}
                        gh.comentarios.append(c)
                        gh._toca(gh.issues[n])
                        return self._responde(201, c)
                    m = re.fullmatch(rf"{r}/issues/(\d+)/assignees", u.path)
                    if metodo == "POST" and m:
                        i = gh.issues[int(m.group(1))]
                        for a in d.get("assignees", []):
                            i["assignees"].append({"login": a})
                            gh._evento(i["number"], "assigned", usuario, assignee=a)
                        gh._toca(i)
                        return self._responde(201, gh._vista(i))
                    m = re.fullmatch(rf"{r}/issues/(\d+)/dependencies/blocked_by(?:/(\d+))?", u.path)
                    if m:
                        i = gh.issues[int(m.group(1))]
                        if metodo == "POST":
                            num = next(x["number"] for x in gh.issues.values() if x["id"] == d["issue_id"])
                            if num not in i["_bloqueado_por"]:
                                i["_bloqueado_por"].append(num)
                                gh._evento(i["number"], "blocked_by_added", usuario)
                                gh._evento(num, "blocking_added", usuario)
                        elif metodo == "DELETE":
                            num = next(x["number"] for x in gh.issues.values() if x["id"] == int(m.group(2)))
                            i["_bloqueado_por"].remove(num)
                            gh._evento(i["number"], "blocked_by_removed", usuario)
                            gh._evento(num, "blocking_removed", usuario)
                        if gh.deps_actualizan:
                            gh._toca(i)
                        return self._responde(201 if metodo == "POST" else 200, gh._vista(i))
                self._responde(404, {"message": "Not Found"})

            def do_POST(self):
                self._escribe("POST")

            def do_PATCH(self):
                self._escribe("PATCH")

            def do_DELETE(self):
                self._escribe("DELETE")

        return M
