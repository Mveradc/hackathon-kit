import { useEffect, useRef, useState } from "react";
import { lectorSSE } from "./sse.js";

// Lo que la web recibe de su demonio (api.md §4, ADR-0010):
//   - GET /v1/stream con fetch y X-HK-Token: `vista` (lo mismo que /v1/vista), `eventos` (solo animan) y `ping`;
//   - si el stream se corta, reconecta con espera creciente (1 s → 30 s) y, mientras, pide /v1/vista cada 3 s. Si el
//     demonio contesta 429 (ya tiene todos los streams que admite), lo mismo, y la web dice por qué;
//   - «sin conexión» (ADR-0009, la excepción del transporte): nada del demonio (ni vista, ni eventos, ni ping) en
//     max(umbral_viejo_s, 40 s). No es el estado de ningún dato: es que la propia web ha dejado de recibir. Al pasar
//     a «sin conexión» se aborta el stream (una conexión medio abierta dejaría `read()` esperando para siempre) y
//     arrancan el sondeo y la reconexión;
//   - si el stream conecta pero no trae ninguna `vista` en SIN_VISTA_MS (el demonio aún sin estado solo manda
//     `ping`), pide /v1/vista una vez: su 503 dice «aún no tiene estado».
//
// Un solo stream por navegador y origen (issue #15): Chrome abre como mucho 6 conexiones por host y cada stream ocupa
// una, así que desde la 7.ª pestaña ni se cargaba la página. Con navigator.locks y BroadcastChannel, la pestaña que
// tiene el cerrojo (la líder) es la única que habla con el demonio (stream y sondeo) y reparte a las demás, por el
// canal, lo que recibe tal cual: la vista, los eventos, los ping, el modo y los fallos. No calcula nada (ADR-0009).
// Una pestaña que llega pide con `hola` la última vista, el modo y el fallo. Si la líder se cierra, el navegador suelta
// su cerrojo y otra pestaña lo coge y abre el stream. Cada mensaje lleva `en`, la hora a la que la líder lo recibió:
// «sin conexión» y «último dato» se miden igual en todas. El cerrojo y el canal llevan la huella SHA-256 del token: el
// token no sale de la memoria de la pestaña, y solo comparten stream las que tienen el mismo. Sin esas APIs, cada
// pestaña lee su propio stream, como antes.
export const PING_DOBLE_S = 40;
export const SIN_VISTA_MS = 5000;
const ESPERA_MIN = 1000, ESPERA_MAX = 30000, SONDEO_MS = 3000, COMPRUEBA_MS = 1000, EVENTOS_MAX = 200;
const FOTO = ["vista", "modo", "fallo"];          // lo que la líder vuelve a mandar a una pestaña que llega (no eventos)

export function umbralSinConexion(respuesta) {
  const s = Number(respuesta?.vista?.umbrales?.fuente_s) || 0;
  return Math.max(s, PING_DOBLE_S) * 1000;
}

/** Lo que hace falta para compartir el stream entre pestañas, o null si el navegador no lo tiene. */
export function pestanasDelNavegador(w = globalThis) {
  const locks = w.navigator?.locks, Canal = w.BroadcastChannel, subtle = w.crypto?.subtle;
  if (typeof locks?.request !== "function" || typeof Canal !== "function" || typeof subtle?.digest !== "function") return null;
  return {
    locks, Canal,
    huella: async (token) => [...new Uint8Array(await subtle.digest("SHA-256", new TextEncoder().encode(token)))]
      .map((b) => b.toString(16).padStart(2, "0")).join(""),
  };
}

/** El transporte con el demonio: stream, sondeo y reconexión. Lo que recibe lo pasa a `emite` como mensajes
 *  {t: vista|eventos|ping, …, en} y {t: modo|fallo, …}. Devuelve la función que lo para. */
function fuente({ token, fetchImpl, emite }) {
  let vivo = true, espera = ESPERA_MIN, ctrl = null, sondeo = null, dormido = null, sinVista = null, cortado = 0;
  let ultimo = Date.now(), umbral = PING_DOBLE_S * 1000;
  const cabeceras = { "X-HK-Token": token };

  const recibido = (m) => {
    if (!vivo) return;
    ultimo = Date.now();
    if (m.t === "vista") umbral = umbralSinConexion(m.r);
    emite({ ...m, en: ultimo });
  };
  const fallo = (f) => vivo && emite({ t: "fallo", fallo: f });
  const modo = (modo, motivo = null) => vivo && emite({ t: "modo", modo, motivo });

  const alMensaje = ({ event, data }) => {
    if (!vivo) return;
    espera = ESPERA_MIN;            // solo un stream que trae algo reinicia la espera (no uno que se corta enseguida)
    if (event === "vista") {
      clearTimeout(sinVista);
      recibido({ t: "vista", r: JSON.parse(data) });
    } else if (event === "eventos") {
      recibido({ t: "eventos", lista: (JSON.parse(data).eventos || []).filter((e) => e && e.id) });
    } else if (event === "ping") recibido({ t: "ping" });
  };

  async function pideVista() {
    try {
      const r = await fetchImpl("/v1/vista", { headers: cabeceras, cache: "no-store" });
      if (!vivo) return;
      if (r.status === 401) return fallo("token");
      if (r.status === 503) return fallo("sin estado");
      if (r.ok) recibido({ t: "vista", r: await r.json() });
    } catch {
      /* el demonio no responde: lo dirá «sin conexión» */
    }
  }
  const arrancaSondeo = () => {
    if (sondeo) return;
    pideVista();
    sondeo = setInterval(pideVista, SONDEO_MS);
  };
  const paraSondeo = () => {
    clearInterval(sondeo);
    sondeo = null;
  };

  async function stream() {
    ctrl = new AbortController();
    const { signal } = ctrl;
    // Abortar corta también un fetch o un read() que no respeten la señal (una conexión medio abierta).
    const abortado = new Promise((_, rechaza) => signal.addEventListener("abort", () => rechaza(new Error("abortado"))));
    abortado.catch(() => {});
    const r = await Promise.race([fetchImpl("/v1/stream", {
      headers: { ...cabeceras, Accept: "text/event-stream" }, cache: "no-store", signal,
    }), abortado]);
    if (r.status === 401) return "token";
    if (r.status === 429) return "lleno";
    if (!r.ok || !r.body) throw new Error(`stream ${r.status}`);
    modo("stream");
    paraSondeo();
    const lector = r.body.getReader();
    signal.addEventListener("abort", () => lector.cancel?.().catch(() => {}));
    sinVista = setTimeout(() => { if (vivo && !signal.aborted) pideVista(); }, SIN_VISTA_MS);
    const dec = new TextDecoder();
    const leer = lectorSSE(alMensaje);
    try {
      for (;;) {
        const { value, done } = await Promise.race([lector.read(), abortado]);
        if (done || !vivo) throw new Error("stream cerrado");
        leer(typeof value === "string" ? value : dec.decode(value, { stream: true }));
      }
    } finally {
      clearTimeout(sinVista);
    }
  }

  const dormir = (ms) => new Promise((res) => { dormido = setTimeout(res, ms); });

  (async () => {
    while (vivo) {
      let motivo = null;
      try {
        motivo = await stream();
        if (motivo === "token") return fallo("token");
      } catch {
        motivo = null;              /* cortado: sondeo y otro intento */
      }
      if (!vivo) return;
      modo("sondeo", motivo);
      arrancaSondeo();
      await dormir(espera);
      espera = Math.min(espera * 2, ESPERA_MAX);
    }
  })();

  // Cada umbral sin nada del demonio (desde lo último recibido o desde el último corte): fuera el stream y a sondear
  // y reconectar.
  const comprueba = setInterval(() => {
    const ahora = Date.now();
    if (ahora - Math.max(ultimo, cortado) <= umbral) return;
    cortado = ahora;
    ctrl?.abort();
    arrancaSondeo();
  }, COMPRUEBA_MS);

  return () => {
    vivo = false;
    ctrl?.abort();
    paraSondeo();
    clearTimeout(dormido);
    clearTimeout(sinVista);
    clearInterval(comprueba);
  };
}

/** `pestanas`: lo de pestanasDelNavegador() para compartir un solo stream entre pestañas; sin él (o null), esta
 *  pestaña lee su propio stream. */
export function useDemonio({ token, fetchImpl, pestanas = null }) {
  const [respuesta, setRespuesta] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [ultimo, setUltimo] = useState(null);           // reloj local de la última vez que llegó algo
  const [sinConexion, setSinConexion] = useState(false);
  const [modo, setModo] = useState("conectando");       // conectando | stream | sondeo
  const [motivo, setMotivo] = useState(null);           // null | lleno (el demonio dio 429 al stream)
  const [fallo, setFallo] = useState(null);             // null | token | sin estado
  const umbralRef = useRef(PING_DOBLE_S * 1000);

  useEffect(() => {
    if (!token) return undefined;
    let vivo = true, parar = null, soltar = null, canal = null, lider = false;
    let desde = Date.now(), dato = 0;                   // desde cuándo se cuenta para «sin conexión»; último dato
    const foto = {};
    const peticion = new AbortController();

    const marca = (en) => {
      dato = Math.max(dato, en || 0);
      desde = Math.max(desde, dato);
      setUltimo(dato);
      setSinConexion(Date.now() - desde > umbralRef.current);
    };
    const aplica = (m) => {
      if (!vivo || !m) return;
      if (m.t === "vista") {
        umbralRef.current = umbralSinConexion(m.r);
        setRespuesta(m.r);
        setFallo(null);
        marca(m.en);
      } else if (m.t === "eventos") {
        setEventos((xs) => [...xs, ...m.lista].slice(-EVENTOS_MAX));
        marca(m.en);
      } else if (m.t === "ping") marca(m.en);
      else if (m.t === "modo") {
        setModo(m.modo);
        setMotivo(m.motivo || null);
      } else if (m.t === "fallo") setFallo(m.fallo);
    };

    (async () => {
      let nombre = null;
      try {
        if (pestanas) nombre = `hk-os-stream-${await pestanas.huella(token)}`;
      } catch {
        nombre = null;
      }
      if (!vivo) return;
      if (!nombre) {
        parar = fuente({ token, fetchImpl, emite: aplica });
        return;
      }
      canal = new pestanas.Canal(nombre);
      canal.onmessage = ({ data: m }) => {
        if (m?.t !== "hola") return aplica(m);
        if (lider) for (const k of FOTO) if (foto[k]) canal.postMessage(foto[k]);
      };
      canal.postMessage({ t: "hola" });
      pestanas.locks.request(nombre, { signal: peticion.signal }, () => {
        if (!vivo) return undefined;
        lider = true;
        parar = fuente({
          token, fetchImpl, emite: (m) => {
            if (FOTO.includes(m.t)) foto[m.t] = m;
            if (m.t === "vista") delete foto.fallo;     // como setFallo(null) al llegar una vista
            aplica(m);
            canal?.postMessage(m);
          },
        });
        return new Promise((res) => { soltar = res; });
      }).catch(() => {});
    })();

    const comprueba = setInterval(() => {
      if (Date.now() - desde > umbralRef.current) setSinConexion(true);
    }, COMPRUEBA_MS);

    return () => {
      vivo = false;
      peticion.abort();
      parar?.();
      soltar?.();
      canal?.close();
      clearInterval(comprueba);
    };
  }, [token, fetchImpl, pestanas]);

  return { respuesta, eventos, ultimo, sinConexion, modo, motivo, fallo };
}
