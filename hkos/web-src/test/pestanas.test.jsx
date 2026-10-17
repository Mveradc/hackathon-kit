import { act, render, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";
import { pestanasDelNavegador } from "../src/datos/demonio.js";
import { caso, demonioFalso, movimientoReducido, navegadorFalso } from "./ayuda.js";

// Issue #15: Chrome abre como mucho 6 conexiones por host y cada pestaña tenía su /v1/stream, así que desde la 7.ª la
// página ni cargaba. Ahora una pestaña líder (navigator.locks) lee el único stream y reparte por BroadcastChannel, tal
// cual, lo que llega; si se cierra, otra coge el relevo. Sin esas APIs, una por pestaña, como antes.

const TOKEN = "a".repeat(64);
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });
const streams = (d) => d.peticiones.filter((p) => p.url === "/v1/stream").length;
const vistas = (d) => d.peticiones.filter((p) => p.url === "/v1/vista").length;
const pinta = (p) => !!within(p.container).queryByRole("heading", { name: /Hola, @persona-a/ });
const sub = (p) => p.container.querySelector(".hk-sub")?.textContent || "";
const sinConexion = (p) => p.container.querySelector("main").dataset.sinConexion;

async function abre(d, pestanas, n, token = TOKEN) {
  const lista = [];
  for (let i = 0; i < n; i++) {
    lista.push(render(<App token={token} fetchImpl={d.fetchImpl} pestanas={pestanas} />));
    await flush();
  }
  return lista;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
  vi.setSystemTime(new Date("2026-11-25T18:30:00Z"));
  movimientoReducido(false);
});

describe("un solo /v1/stream por navegador (issue #15)", () => {
  it("con 9 pestañas, un solo stream y todas pintan la vista, los eventos y los ping que llegan", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const ps = await abre(d, nav.pestanas, 9);
    expect(streams(d)).toBe(1);
    expect(nav.duenos(`hk-os-stream-h-${TOKEN}`)).toBe(1);
    const r = caso("G12");
    for (const p of r.vista.personas) p.viejo = false;
    d.vista(r);
    await flush();
    expect(ps.map(pinta)).toEqual(Array(9).fill(true));
    // Un evento llega a todas tal cual (en todas lanza su paquete).
    d.eventos([{ id: "s-a-7", tipo: "edicion", persona: "persona-a", papel: "principal", ts: "2026-11-25T18:20:01Z" }]);
    await flush();
    for (const p of ps) expect([...p.container.querySelectorAll("[data-paquete]")].map((x) => x.dataset.paquete)).toEqual(["s-a-7"]);
    // Los ping de la líder mantienen a todas fuera de «sin conexión» (umbral de G12: 300 s).
    for (let i = 0; i < 20; i++) {
      await act(async () => { await vi.advanceTimersByTimeAsync(20_000); });
      d.ping();
      await flush();
    }
    expect(ps.map(sinConexion)).toEqual(Array(9).fill("no"));
    expect(streams(d)).toBe(1);
    expect(vistas(d)).toBe(0);                            // las demás no sondean por su cuenta
    for (const p of d.peticiones) expect(p.headers["X-HK-Token"]).toBe(TOKEN);
  });

  it("una pestaña que llega después pinta enseguida la última vista, sin pedir nada al demonio", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    await abre(d, nav.pestanas, 2);
    d.vista(caso("G12"));
    await flush();
    const antes = d.peticiones.length;
    const [nueva] = await abre(d, nav.pestanas, 1);
    expect(pinta(nueva)).toBe(true);
    expect(d.peticiones.length).toBe(antes);
  });

  it("si la líder se cierra, otra coge el relevo: abre el stream y las demás siguen pintando lo que llega", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const ps = await abre(d, nav.pestanas, 8);
    const r = caso("G12");
    d.vista(r);
    await flush();
    expect(d.streams.length).toBe(1);
    ps[0].unmount();                                      // la líder (la primera que pidió el cerrojo)
    await flush();
    expect(streams(d)).toBe(2);
    expect(d.peticiones.at(-1).signal.aborted).toBe(false);
    expect(nav.duenos(`hk-os-stream-h-${TOKEN}`)).toBe(1);
    // La vista nueva del stream de la nueva líder llega a las 7 que quedan.
    const otra = structuredClone(r);
    otra.persona = "persona-b";
    d.vista(otra);
    await flush();
    for (const p of ps.slice(1)) expect(sub(p)).toContain("@persona-b");
    // Y así una tras otra, hasta que solo queda una.
    for (let i = 1; i < 7; i++) {
      ps[i].unmount();
      await flush();
    }
    expect(streams(d)).toBe(8);
    d.vista(r);
    await flush();
    expect(sub(ps[7])).toContain("@persona-a");
    ps[7].unmount();
    await flush();
    expect(nav.canales()).toBe(0);
    expect(nav.duenos(`hk-os-stream-h-${TOKEN}`)).toBe(0);
  });

  it("«sin conexión» en todas cuando la líder deja de recibir, y vuelven con lo siguiente que llega", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const ps = await abre(d, nav.pestanas, 3);
    const r = caso("G12");
    r.vista.umbrales.fuente_s = 10;                       // mandan los 40 s
    d.vista(r);
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(39_000); });
    expect(ps.map(sinConexion)).toEqual(["no", "no", "no"]);
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(ps.map(sinConexion)).toEqual(["si", "si", "si"]);
    // La líder aborta el stream, sondea y reconecta (una sola vez por navegador).
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(streams(d)).toBe(2);
    d.vista(r);
    await flush();
    expect(ps.map(sinConexion)).toEqual(["no", "no", "no"]);
  });

  it("pestañas con otro token no comparten stream (el cerrojo y el canal van por la huella del token)", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    await abre(d, nav.pestanas, 3);
    await abre(d, nav.pestanas, 3, "b".repeat(64));
    expect(streams(d)).toBe(2);
    expect(new Set(d.peticiones.map((p) => p.headers["X-HK-Token"])).size).toBe(2);
  });

  it("sin navigator.locks ni BroadcastChannel, cada pestaña lee su stream, como antes", async () => {
    const d = demonioFalso();
    const ps = await abre(d, null, 3);
    expect(streams(d)).toBe(3);
    for (const s of d.streams) s.manda(`event: vista\ndata: ${JSON.stringify(caso("G12"))}\n\n`);
    await flush();
    expect(ps.map(pinta)).toEqual([true, true, true]);
  });

  it("pestanasDelNavegador: solo con navigator.locks, BroadcastChannel y crypto.subtle; la huella es SHA-256 en hex", async () => {
    const subtle = { digest: async () => new Uint8Array([0, 1, 254, 255]).buffer };
    const completo = { navigator: { locks: { request() {} } }, BroadcastChannel: class {}, crypto: { subtle } };
    const p = pestanasDelNavegador(completo);
    expect(await p.huella(TOKEN)).toBe("0001feff");
    expect(pestanasDelNavegador({ ...completo, navigator: {} })).toBeNull();
    expect(pestanasDelNavegador({ ...completo, BroadcastChannel: undefined })).toBeNull();
    expect(pestanasDelNavegador({ ...completo, crypto: {} })).toBeNull();
    // Con el crypto de verdad (el de Node): 64 caracteres hex y nunca el token.
    const real = pestanasDelNavegador({ ...completo, crypto: globalThis.crypto });
    const h = await real.huella(TOKEN);
    expect(h).toMatch(/^[0-9a-f]{64}$/);
    expect(h).not.toContain(TOKEN);
  });
});

describe("429 del stream (issue #15, hallazgo 10)", () => {
  it("dice que hay demasiadas pestañas o clientes abiertos, sondea /v1/vista y reintenta el stream", async () => {
    const d = demonioFalso({ vistaActual: caso("G12"), streamLleno: true });
    const [p] = await abre(d, null, 1);
    expect(pinta(p)).toBe(true);
    expect(sub(p)).toContain("demasiadas pestañas o clientes abiertos");
    expect(sub(p)).toContain("pidiendo cada 3 s");
    expect(vistas(d)).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(streams(d)).toBe(2);                           // primer reintento al segundo, el siguiente a los 2 s más
    expect(sub(p)).toContain("demasiadas pestañas o clientes abiertos");
    // Cuando el demonio vuelve a admitir el stream, se va el aviso.
    d.streamLleno = false;
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(vistas(d)).toBe(2);                            // cada 3 s mientras tanto
    expect(streams(d)).toBe(3);
    d.vista(caso("G12"));
    await flush();
    expect(sub(p)).not.toContain("sin stream");
  });

  it("un corte que no es 429 sigue diciendo solo «sin stream, pidiendo cada 3 s»", async () => {
    const d = demonioFalso({ vistaActual: caso("G12") });
    const [p] = await abre(d, null, 1);
    d.vista(caso("G12"));
    await flush();
    d.corta();
    await flush();
    expect(sub(p)).toContain("sin stream, pidiendo cada 3 s");
    expect(sub(p)).not.toContain("demasiadas");
  });

  it("con pestañas, el aviso del 429 de la líder llega también a las demás", async () => {
    const d = demonioFalso({ vistaActual: caso("G12"), streamLleno: true });
    const nav = navegadorFalso();
    const ps = await abre(d, nav.pestanas, 4);
    await flush();
    for (const p of ps) expect(sub(p)).toContain("demasiadas pestañas o clientes abiertos");
    expect(streams(d)).toBe(1);
  });
});
