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
//
// Relevo sin que la líder se cierre (issue #23):
//   - la líder manda un `latido` por el canal cada LATIDO_MS, con si está visible y cuánto lleva oculta. Una seguidora
//     visible que no oye a la líder en RELEVO_MS (más un azar de hasta RELEVO_AZAR_MS, para que no salten todas a la
//     vez) le quita el cerrojo con navigator.locks.request(…, {steal: true}) y abre el stream: así se releva a una
//     líder congelada o colgada, que no suelta el cerrojo;
//   - si la líder lleva oculta CEDE_MS y hay una seguidora visible, esa seguidora le quita el cerrojo igual: una
//     pestaña oculta más de 5 min tiene los timers frenados por Chrome (reconexión y sondeo de hasta 1 min);
//   - una líder a la que le quitan el cerrojo (su petición acaba en AbortError, también al despertar) deja de leer su
//     stream y vuelve a la cola. Cada líder firma lo que manda con su `era` (la hora a la que cogió el cerrojo, y
//     siempre más que la última que oyó): lo que llegue de una era anterior es de una líder que ya no lo es y no se
//     pinta, y una líder que oye una era más nueva deja de serlo aunque el navegador no le haya avisado;
//   - sin bucles: solo releva una pestaña visible y la que releva pasa a ser una líder visible, a la que nadie releva.
//     Con todas ocultas no releva ninguna (los timers de las ocultas van frenados y se relevarían cada minuto); la
//     primera que vuelve a estar visible lo mira en el acto.
// bfcache: en pagehide, la pestaña cierra el canal y suelta el cerrojo o sale de la cola (un mensaje del canal la saca
// de la caché, y una pestaña en la caché no puede ser líder); en pageshow con `persisted`, vuelve a abrirlos. El token
// sigue en la memoria de la pestaña, que la caché conserva: no se guarda en ningún almacenamiento.
export const PING_DOBLE_S = 40;
export const SIN_VISTA_MS = 5000;
export const LATIDO_MS = 2000, RELEVO_MS = 8000, RELEVO_AZAR_MS = 1500, CEDE_MS = 20000;
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
    visible: () => w.document?.visibilityState !== "hidden",
    /** visibilitychange (del documento), pagehide y pageshow (de la ventana). Devuelve la función que deja de escuchar. */
    escucha: (tipo, fn) => {
      const t = tipo === "visibilitychange" ? w.document : w;
      t?.addEventListener?.(tipo, fn);
      return () => t?.removeEventListener?.(tipo, fn);
    },
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
  const [liderEs, setLider] = useState(false);          // si esta pestaña es la que habla con el demonio
  const umbralRef = useRef(PING_DOBLE_S * 1000);

  useEffect(() => {
    if (!token) return undefined;
    let vivo = true, parar = null;
    let desde = Date.now(), dato = 0;                   // desde cuándo se cuenta para «sin conexión»; último dato
    const foto = {};
    // Con pestañas: el nombre del cerrojo y del canal, si esta pestaña está en marcha (no en la bfcache), si es la
    // líder y con qué era, la mayor era oída, lo último oído a la líder y cuándo, y la petición del cerrojo en curso.
    let nombre = null, enMarcha = false, canal = null, lider = false, era = 0, eraMax = 0;
    let oido = 0, latido = null, oidoLatido = 0, latidoT = null, cola = null, turno = 0, soltar = null;
    let ocultaDesde = null;
    const yo = Math.random().toString(36).slice(2), azar = Math.random() * RELEVO_AZAR_MS;
    const quita = [];

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
    const guarda = (m) => {
      if (FOTO.includes(m.t)) foto[m.t] = m;
      if (m.t === "vista") delete foto.fallo;           // como setFallo(null) al llegar una vista
    };

    const visible = () => (pestanas?.visible ? pestanas.visible() : true);
    const manda = (m) => canal?.postMessage({ ...m, era, de: yo });
    const late = () => manda({ t: "latido", visible: visible(), oculta_ms: ocultaDesde == null ? 0 : Date.now() - ocultaDesde });

    const dejaDeSerLider = () => {
      lider = false;
      setLider(false);
      clearInterval(latidoT);
      latidoT = null;
      parar?.();
      parar = null;
      const s = soltar;
      soltar = null;
      s?.();
    };
    /** Pide el cerrojo y espera en la cola, o se lo quita a quien lo tenga (`robar`). */
    const pide = (robar = false) => {
      cola?.abort();
      cola = robar ? null : new AbortController();
      const mio = ++turno;
      pestanas.locks.request(nombre, robar ? { steal: true } : { signal: cola.signal }, () => {
        if (!vivo || !enMarcha || mio !== turno) return undefined;
        cola = null;
        lider = true;
        setLider(true);
        era = eraMax = Math.max(Date.now(), eraMax + 1);
        late();
        latidoT = setInterval(late, LATIDO_MS);
        parar = fuente({
          token, fetchImpl, emite: (m) => {
            if (!lider) return;
            guarda(m);
            aplica(m);
            manda(m);
          },
        });
        return new Promise((res) => { soltar = res; });
      }).catch(() => {
        // AbortError: otra pestaña le ha quitado el cerrojo (también si se entera al despertar) o lo ha cancelado ella.
        if (vivo && enMarcha && mio === turno && lider) {
          dejaDeSerLider();
          pide();
        }
      });
    };
    const alMensaje = ({ data: m }) => {
      if (!m) return;
      if (m.t === "hola") {
        if (lider) for (const k of FOTO) if (foto[k]) manda(foto[k]);
        return;
      }
      const e = Number(m.era) || 0;
      if (e < eraMax) return;                           // de una líder que ya no lo es
      eraMax = e;
      if (lider) {
        if (e <= era) return;
        dejaDeSerLider();                               // otra cogió el cerrojo después: ya no es suyo
        pide();
      }
      oido = Date.now();
      if (m.t === "latido") {
        latido = m;
        oidoLatido = oido;
        return;
      }
      guarda(m);
      aplica(m);
    };
    /** Una seguidora visible releva a una líder callada (congelada o colgada) o a una que lleva oculta CEDE_MS. */
    const vigila = () => {
      if (!enMarcha || lider || !visible()) return;
      const ahora = Date.now();
      const callada = ahora - oido > RELEVO_MS + azar;
      const oculta = latido && !latido.visible && latido.oculta_ms + (ahora - oidoLatido) >= CEDE_MS + azar;
      if (!callada && !oculta) return;
      oido = ahora;                                     // no vuelve a intentarlo hasta otro RELEVO_MS
      latido = null;
      pide(true);
    };
    const alVerse = () => {
      if (visible()) ocultaDesde = null;
      else ocultaDesde ??= Date.now();
      if (lider) late();
      else vigila();
    };

    const arranca = () => {
      if (!vivo || enMarcha) return;
      enMarcha = true;
      desde = Math.max(desde, Date.now());
      oido = Date.now();
      latido = null;
      if (!nombre) {
        setLider(true);
        parar = fuente({ token, fetchImpl, emite: aplica });
        return;
      }
      canal = new pestanas.Canal(nombre);
      canal.onmessage = alMensaje;
      canal.postMessage({ t: "hola" });
      pide();
    };
    const para = () => {
      if (!enMarcha) return;
      enMarcha = false;
      turno++;
      cola?.abort();
      cola = null;
      if (lider) dejaDeSerLider();
      parar?.();
      parar = null;
      canal?.close();
      canal = null;
    };

    (async () => {
      try {
        if (pestanas) nombre = `hk-os-stream-${await pestanas.huella(token)}`;
      } catch {
        nombre = null;
      }
      if (!vivo) return;
      if (nombre) {
        if (!visible()) ocultaDesde = Date.now();
        quita.push(pestanas.escucha?.("visibilitychange", alVerse));
        quita.push(pestanas.escucha?.("pagehide", para));
        quita.push(pestanas.escucha?.("pageshow", (ev) => { if (ev?.persisted) arranca(); }));
      }
      arranca();
    })();

    const comprueba = setInterval(() => {
      if (Date.now() - desde > umbralRef.current) setSinConexion(true);
      if (nombre) vigila();
    }, COMPRUEBA_MS);

    return () => {
      para();
      vivo = false;
      for (const f of quita) f?.();
      clearInterval(comprueba);
    };
  }, [token, fetchImpl, pestanas]);

  return { respuesta, eventos, ultimo, sinConexion, modo, motivo, fallo, lider: liderEs };
}
