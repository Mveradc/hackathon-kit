import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { vi } from "vitest";

// En el entorno jsdom, `URL` es la de jsdom: la ruta se arma con node:path.
const DIR = join(dirname(fileURLToPath(import.meta.url)), "vistas") + "/";

/** Las vistas de ejemplo (scripts/vistas_ejemplo.py): [{nombre, caso, respuesta}] con lo que serviría el demonio. */
export function casos() {
  const salida = [];
  for (const f of readdirSync(DIR).filter((x) => x.endsWith(".json")).sort()) {
    const { nombre, casos: lista } = JSON.parse(readFileSync(DIR + f, "utf-8"));
    lista.forEach((c, i) => {
      const { tras, ...respuesta } = c;
      salida.push({ nombre: `${nombre}${tras != null ? ` t=${tras}` : ""} #${i} @${c.persona}`, respuesta });
    });
  }
  return salida;
}

export function caso(nombre, i = 0) {
  return JSON.parse(readFileSync(DIR + `${nombre}.json`, "utf-8")).casos[i];
}

/** Un stream que el test va llenando: body.getReader().read() espera hasta el siguiente trozo. */
function streamFalso() {
  const cola = [];
  let espera = null;
  const entrega = (v) => {
    if (espera) {
      const r = espera;
      espera = null;
      r(v);
    } else cola.push(v);
  };
  const enc = new TextEncoder();
  return {
    body: { getReader: () => ({ read: () => (cola.length ? Promise.resolve(cola.shift()) : new Promise((r) => { espera = r; })) }) },
    manda: (texto) => entrega({ value: enc.encode(texto), done: false }),
    cierra: () => entrega({ value: undefined, done: true }),
  };
}

const respuestaHttp = (status, datos, body) => ({
  ok: status >= 200 && status < 300, status, body,
  json: async () => (datos === undefined ? Promise.reject(new Error("sin cuerpo")) : datos),
});

/**
 * Demonio falso (api.md §4) para probar la web sin el de verdad, que hace otra persona (K-94, K-95):
 *   - `fetchImpl` hace de fetch; guarda cada petición en `peticiones`;
 *   - GET /v1/stream devuelve un stream que el test llena con `vista(r)`, `eventos([…])`, `ping()` o `corta()`;
 *   - GET /v1/vista devuelve `vistaActual`;
 *   - POST /v1/anotar y /v1/reclamar contestan lo que diga `acciones[ruta]` ({status, datos}), por defecto 200.
 */
export function demonioFalso({ vistaActual = null, acciones = {} } = {}) {
  const d = { peticiones: [], streams: [], vistaActual, acciones };
  d.fetchImpl = vi.fn(async (url, init = {}) => {
    d.peticiones.push({ url, ...init, headers: { ...(init.headers || {}) } });
    if (url === "/v1/stream") {
      const s = streamFalso();
      d.streams.push(s);
      return respuestaHttp(200, undefined, s.body);
    }
    if (url === "/v1/vista") return d.vistaActual ? respuestaHttp(200, d.vistaActual) : respuestaHttp(503, { error: "sin estado" });
    const a = d.acciones[url] || { status: 200, datos: { ok: true } };
    return respuestaHttp(a.status, a.datos);
  });
  const ultimo = () => d.streams[d.streams.length - 1];
  d.vista = (r) => ultimo().manda(`event: vista\ndata: ${JSON.stringify(r)}\n\n`);
  d.eventos = (lista) => ultimo().manda(`event: eventos\ndata: ${JSON.stringify({ eventos: lista })}\n\n`);
  d.ping = () => ultimo().manda("event: ping\ndata: \n\n");
  d.corta = () => ultimo().cierra();
  return d;
}

/** El fin de la animación CSS de un paquete o destello. En jsdom, React decide por el estilo del <div> si escucha
 *  `animationend` o `webkitAnimationEnd`: se mandan los dos (en un navegador solo llega el que toca). */
export function terminaAnimacion(el) {
  for (const tipo of ["animationend", "webkitAnimationEnd"]) el.dispatchEvent(new Event(tipo, { bubbles: true }));
}

/** prefers-reduced-motion simulado (jsdom no trae matchMedia). */
export function movimientoReducido(si) {
  window.matchMedia = (q) => ({
    matches: si && q.includes("prefers-reduced-motion"), media: q,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
  });
}
