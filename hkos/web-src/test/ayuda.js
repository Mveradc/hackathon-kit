import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { vi } from "vitest";

// En el entorno jsdom, `URL` es la de jsdom: la ruta se arma con node:path.
const DIR = join(dirname(fileURLToPath(import.meta.url)), "vistas") + "/";

const TABLAS = "tablas.json";

/** Las vistas de ejemplo (scripts/vistas_ejemplo.py): [{nombre, respuesta, esperado, antiguedades}], con lo que
 *  serviría el demonio, lo que calcula proyeccion.py para cada persona ({persona: {trabajo, servicios}}) y la
 *  antigüedad en segundos de cada observado_en según proyeccion.py ({observado_en: segundos}). */
export function casos() {
  const salida = [];
  for (const f of readdirSync(DIR).filter((x) => x.endsWith(".json") && x !== TABLAS).sort()) {
    const { nombre, casos: lista } = JSON.parse(readFileSync(DIR + f, "utf-8"));
    lista.forEach((c, i) => {
      const { tras, esperado, antiguedades, ...respuesta } = c;
      salida.push({ nombre: `${nombre}${tras != null ? ` t=${tras}` : ""} #${i} @${c.persona}`, respuesta, esperado, antiguedades });
    });
  }
  return salida;
}

export function caso(nombre, i = 0) {
  const { esperado, antiguedades, ...c } = JSON.parse(readFileSync(DIR + `${nombre}.json`, "utf-8")).casos[i];
  return c;
}

// Unidad del «hace N unidad»: [segundos de la unidad, desde, hasta (sin incluir)].
const UNIDAD = { s: [1, 0, 60], min: [60, 60, 3600], h: [3600, 3600, 86400], d: [86400, 86400, Infinity] };

/** ¿El «hace N unidad» que pinta la web dice los `segundos` que calculó proyeccion.py? Sin usar hace() de la web:
 *  la unidad es la mayor que cabe y N, el entero de segundos / unidad. */
export function diceAntiguedad(texto, segundos) {
  const m = /^hace (\d+) (s|min|h|d)$/.exec(texto);
  if (!m || !Number.isInteger(segundos)) return false;
  const [paso, desde, hasta] = UNIDAD[m[2]];
  return segundos >= desde && segundos < hasta && Math.floor(segundos / paso) === Number(m[1]);
}

/** ETIQUETAS y TRABAJO de proyeccion.py, tal cual. */
export function tablas() {
  return JSON.parse(readFileSync(DIR + TABLAS, "utf-8"));
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
 *   - POST /v1/anotar y /v1/reclamar contestan lo que diga `acciones[ruta]` ({status, datos}), por defecto 200;
 *   - con `streamLleno`, GET /v1/stream contesta 429, como el demonio con todos sus streams ocupados.
 */
export function demonioFalso({ vistaActual = null, acciones = {}, streamLleno = false } = {}) {
  const d = { peticiones: [], streams: [], vistaActual, acciones, streamLleno };
  d.fetchImpl = vi.fn(async (url, init = {}) => {
    d.peticiones.push({ url, ...init, headers: { ...(init.headers || {}) } });
    if (url === "/v1/stream" && d.streamLleno) return respuestaHttp(429, { error: "demasiados clientes" });
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

/**
 * Un navegador falso con varias pestañas del mismo origen: navigator.locks (un cerrojo exclusivo por nombre, que se
 * concede por orden de llegada y se suelta al resolverse la promesa de quien lo tiene; una petición en espera se
 * cancela con su `signal`) y BroadcastChannel (entrega asíncrona, copiada con structuredClone, a los demás canales del
 * mismo nombre, nunca a sí mismo). `pestanas` es lo que espera useDemonio; `duenos(nombre)`, cuántos lo tienen ahora.
 */
export function navegadorFalso() {
  const canales = new Set(), cerrojos = new Map();
  class Canal {
    constructor(nombre) {
      this.nombre = nombre;
      this.onmessage = null;
      canales.add(this);
    }
    postMessage(m) {
      for (const c of canales) {
        if (c !== this && c.nombre === this.nombre) {
          const copia = structuredClone(m);
          queueMicrotask(() => canales.has(c) && c.onmessage?.({ data: copia }));
        }
      }
    }
    close() {
      canales.delete(this);
    }
  }
  const cola = (nombre) => cerrojos.get(nombre) || cerrojos.set(nombre, { dueno: 0, espera: [] }).get(nombre);
  const siguiente = (nombre) => {
    const q = cola(nombre);
    if (q.dueno || !q.espera.length) return;
    const p = q.espera.shift();
    q.dueno = 1;
    queueMicrotask(async () => {
      try {
        p.resolve(await p.cb({ name: nombre, mode: "exclusive" }));
      } catch (e) {
        p.reject(e);
      } finally {
        q.dueno = 0;
        siguiente(nombre);
      }
    });
  };
  const locks = {
    request: (nombre, opciones, cb) => new Promise((resolve, reject) => {
      const p = { cb, resolve, reject }, q = cola(nombre);
      opciones?.signal?.addEventListener("abort", () => {
        const i = q.espera.indexOf(p);
        if (i >= 0) {
          q.espera.splice(i, 1);
          reject(new DOMException("abortado", "AbortError"));
        }
      });
      q.espera.push(p);
      siguiente(nombre);
    }),
  };
  return {
    pestanas: { locks, Canal, huella: async (t) => `h-${t}` },
    duenos: (nombre) => cola(nombre).dueno,
    canales: () => canales.size,
  };
}

/** El fin de la animación CSS de un paquete o destello. En jsdom, React decide por el estilo del <div> si escucha
 *  `animationend` o `webkitAnimationEnd`: se mandan los dos (en un navegador solo llega el que toca). */
export function terminaAnimacion(el) {
  for (const tipo of ["animationend", "webkitAnimationEnd"]) el.dispatchEvent(new Event(tipo, { bubbles: true }));
}

/** La pestaña oculta o visible (document.hidden y visibilitychange, como hace el navegador). */
export function pestanaOculta(si) {
  Object.defineProperty(document, "hidden", { configurable: true, get: () => si });
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => (si ? "hidden" : "visible") });
  document.dispatchEvent(new Event("visibilitychange"));
}

/** prefers-reduced-motion simulado (jsdom no trae matchMedia). */
export function movimientoReducido(si) {
  window.matchMedia = (q) => ({
    matches: si && q.includes("prefers-reduced-motion"), media: q,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
  });
}
