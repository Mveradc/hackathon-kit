import { useEffect, useRef, useState } from "react";
import { lectorSSE } from "./sse.js";

// Lo que la web recibe de su demonio (api.md §4, ADR-0010):
//   - GET /v1/stream con fetch y X-HK-Token: `vista` (lo mismo que /v1/vista), `eventos` (solo animan) y `ping`;
//   - si el stream se corta, reconecta con espera creciente (1 s → 30 s) y, mientras, pide /v1/vista cada 3 s;
//   - «sin conexión» (ADR-0009, la excepción del transporte): nada del demonio (ni vista, ni eventos, ni ping) en
//     max(umbral_viejo_s, 40 s). No es el estado de ningún dato: es que la propia web ha dejado de recibir. Al pasar
//     a «sin conexión» se aborta el stream (una conexión medio abierta dejaría `read()` esperando para siempre) y
//     arrancan el sondeo y la reconexión;
//   - si el stream conecta pero no trae ninguna `vista` en SIN_VISTA_MS (el demonio aún sin estado solo manda
//     `ping`), pide /v1/vista una vez: su 503 dice «aún no tiene estado».
export const PING_DOBLE_S = 40;
export const SIN_VISTA_MS = 5000;
const ESPERA_MIN = 1000, ESPERA_MAX = 30000, SONDEO_MS = 3000, COMPRUEBA_MS = 1000, EVENTOS_MAX = 200;

export function umbralSinConexion(respuesta) {
  const s = Number(respuesta?.vista?.umbrales?.fuente_s) || 0;
  return Math.max(s, PING_DOBLE_S) * 1000;
}

export function useDemonio({ token, fetchImpl }) {
  const [respuesta, setRespuesta] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [ultimo, setUltimo] = useState(null);           // reloj local de la última vez que llegó algo
  const [sinConexion, setSinConexion] = useState(false);
  const [modo, setModo] = useState("conectando");       // conectando | stream | sondeo
  const [fallo, setFallo] = useState(null);             // null | token | sin estado
  const ultimoRef = useRef(Date.now());
  const umbralRef = useRef(PING_DOBLE_S * 1000);

  useEffect(() => {
    if (!token) return undefined;
    let vivo = true, espera = ESPERA_MIN, ctrl = null, sondeo = null, dormido = null, sinVista = null, cortado = 0;
    const cabeceras = { "X-HK-Token": token };
    ultimoRef.current = Date.now();

    const marca = () => {
      ultimoRef.current = Date.now();
      setUltimo(ultimoRef.current);
      setSinConexion(false);
    };
    const nuevaVista = (r) => {
      umbralRef.current = umbralSinConexion(r);
      setRespuesta(r);
      setFallo(null);
      marca();
    };
    const alMensaje = ({ event, data }) => {
      if (!vivo) return;
      espera = ESPERA_MIN;            // solo un stream que trae algo reinicia la espera (no uno que se corta enseguida)
      if (event === "vista") {
        clearTimeout(sinVista);
        nuevaVista(JSON.parse(data));
      } else if (event === "eventos") {
        const lista = (JSON.parse(data).eventos || []).filter((e) => e && e.id);
        setEventos((xs) => [...xs, ...lista].slice(-EVENTOS_MAX));
        marca();
      } else if (event === "ping") marca();
    };

    async function pideVista() {
      try {
        const r = await fetchImpl("/v1/vista", { headers: cabeceras, cache: "no-store" });
        if (!vivo) return;
        if (r.status === 401) return setFallo("token");
        if (r.status === 503) return setFallo("sin estado");
        if (r.ok) nuevaVista(await r.json());
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
      if (!r.ok || !r.body) throw new Error(`stream ${r.status}`);
      setModo("stream");
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
        try {
          if ((await stream()) === "token") {
            setFallo("token");
            return;
          }
        } catch {
          /* cortado: sondeo y otro intento */
        }
        if (!vivo) return;
        setModo("sondeo");
        arrancaSondeo();
        await dormir(espera);
        espera = Math.min(espera * 2, ESPERA_MAX);
      }
    })();

    // Cada umbral sin nada del demonio (desde lo último recibido o desde el último corte): «sin conexión», fuera el
    // stream y a sondear y reconectar.
    const comprueba = setInterval(() => {
      const ahora = Date.now();
      if (ahora - Math.max(ultimoRef.current, cortado) <= umbralRef.current) return;
      cortado = ahora;
      setSinConexion(true);
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
  }, [token, fetchImpl]);

  return { respuesta, eventos, ultimo, sinConexion, modo, fallo };
}
