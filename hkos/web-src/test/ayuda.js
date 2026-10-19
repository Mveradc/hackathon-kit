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

/** Las vistas de M10 (scripts/vistas_ejemplo.py, test/vistas/m10/): [{nombre, respuesta, antiguedades, horas}], con
 *  la vista de ejemplo de api.md §11.6 y los momentos de G13 y G14. `horas`: cada hora de los bloques escrita por
 *  Python en la zona de equipo.md ({hora: {hm, dia, fecha}}). */
export function casosM10() {
  const salida = [];
  for (const f of readdirSync(DIR + "m10").filter((x) => x.endsWith(".json")).sort()) {
    const { nombre, casos: lista } = JSON.parse(readFileSync(DIR + "m10/" + f, "utf-8"));
    lista.forEach((c, i) => {
      const { momento, antiguedades, horas, ...respuesta } = c;
      salida.push({ nombre: `${nombre}${momento ? ` ${momento}` : ""} #${i}`, respuesta, antiguedades, horas });
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
 * cancela con su `signal`; con `steal`, se concede en el acto y la petición de quien lo tenía acaba en AbortError) y
 * BroadcastChannel (entrega asíncrona, copiada con structuredClone, a los demás canales del mismo nombre, nunca a sí
 * mismo). `pestanas` es lo que espera useDemonio, para pestañas siempre visibles; `duenos(nombre)`, cuántos lo tienen
 * ahora.
 *
 * `pestana()` da una pestaña con su propio `pestanas` y lo que le puede pasar en un navegador:
 *   - `oculta(si)`: visibilityState y visibilitychange;
 *   - `congela()` y `despierta()`: como Page.setWebLifecycleState. Congelada, lo que manda no sale y lo que le llega
 *     (mensajes del canal y el AbortError de un cerrojo que le quitan) espera a que despierte. Sus timers no se paran
 *     (son los de vitest, de todas), pero sin canal no se oye nada de ella;
 *   - `sale()` y `vuelve()`: pagehide y pageshow con `persisted` (la bfcache). Un mensaje del canal a una pestaña que
 *     está en la caché la desaloja, como en Chrome: `desalojada` lo dice.
 */
export function navegadorFalso() {
  const canales = new Set(), cerrojos = new Map();
  const cola = (nombre) => cerrojos.get(nombre) || cerrojos.set(nombre, { actual: null, espera: [] }).get(nombre);
  const concede = (nombre, p) => {
    const q = cola(nombre);
    q.actual = p;
    queueMicrotask(async () => {
      try {
        p.resolve(await p.cb({ name: nombre, mode: "exclusive" }));
      } catch (e) {
        p.reject(e);
      } finally {
        if (q.actual === p) {
          q.actual = null;
          siguiente(nombre);
        }
      }
    });
  };
  const siguiente = (nombre) => {
    const q = cola(nombre);
    if (!q.actual && q.espera.length) concede(nombre, q.espera.shift());
  };

  function pestana() {
    const tab = { visible: true, congelada: false, enCache: false, desalojada: false, pendientes: [], oyentes: new Map() };
    const entrega = (fn) => (tab.congelada ? tab.pendientes.push(fn) : queueMicrotask(fn));
    const avisa = (tipo, ev = {}) => { for (const f of [...(tab.oyentes.get(tipo) || [])]) f(ev); };
    tab.recibe = (c, copia) => {
      if (tab.enCache) tab.desalojada = true;
      else entrega(() => canales.has(c) && c.onmessage?.({ data: copia }));
    };
    class Canal {
      constructor(nombre) {
        this.nombre = nombre;
        this.tab = tab;
        this.onmessage = null;
        canales.add(this);
      }
      postMessage(m) {
        if (tab.congelada) return;
        for (const c of canales) if (c !== this && c.nombre === this.nombre) c.tab.recibe(c, structuredClone(m));
      }
      close() {
        canales.delete(this);
      }
    }
    const locks = {
      request: (nombre, opciones, cb) => new Promise((resolve, reject) => {
        const p = { cb, resolve, reject, entrega }, q = cola(nombre);
        if (opciones?.steal) {
          const viejo = q.actual;
          if (viejo) viejo.entrega(() => viejo.reject(new DOMException("robado", "AbortError")));
          concede(nombre, p);
          return;
        }
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
    const pestanas = {
      locks, Canal, huella: async (t) => `h-${t}`,
      visible: () => tab.visible,
      escucha: (tipo, fn) => {
        if (!tab.oyentes.has(tipo)) tab.oyentes.set(tipo, new Set());
        tab.oyentes.get(tipo).add(fn);
        return () => tab.oyentes.get(tipo).delete(fn);
      },
    };
    return {
      pestanas,
      oculta: (si) => {
        tab.visible = !si;
        avisa("visibilitychange");
      },
      congela: () => { tab.congelada = true; },
      despierta: () => {
        tab.congelada = false;
        for (const f of tab.pendientes.splice(0)) queueMicrotask(f);
      },
      sale: () => {
        avisa("pagehide", { persisted: true });
        tab.enCache = true;
      },
      vuelve: () => {
        tab.enCache = false;
        avisa("pageshow", { persisted: true });
      },
      get desalojada() { return tab.desalojada; },
    };
  }

  return {
    pestanas: pestana().pestanas,
    pestana,
    duenos: (nombre) => (cola(nombre).actual ? 1 : 0),
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
