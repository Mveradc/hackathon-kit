import { act, render, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";
import { CEDE_MS, LATIDO_MS, pestanasDelNavegador, RELEVO_AZAR_MS, RELEVO_MS } from "../src/datos/demonio.js";
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
const lideres = (ps) => ps.map((p) => p.container.querySelector("main")?.dataset.lider);
const avanza = (ms) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });
const NOMBRE = `hk-os-stream-h-${TOKEN}`;
/** `ms` en pasos de 20 s con un ping del demonio en cada uno (sin ellos, la líder cortaría el stream a los 40 s). */
async function conPing(d, ms) {
  for (let t = 0; t < ms; t += 20_000) {
    await avanza(20_000);
    d.ping();
    await flush();
  }
}
// Lo más que tarda una seguidora en relevar a una líder que calla: RELEVO_MS desde el último latido oído, más su azar
// y el segundo de su comprobación.
const RELEVO_MAX = RELEVO_MS + RELEVO_AZAR_MS + 1000;

/** Una pestaña por cada una de `tabs` (navegadorFalso().pestana()), cada una con su visibilidad y su ciclo de vida. */
async function abreEn(d, tabs) {
  const lista = [];
  for (const t of tabs) {
    lista.push(render(<App token={TOKEN} fetchImpl={d.fetchImpl} pestanas={t.pestanas} />));
    await flush();
  }
  return lista;
}

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
    // Visibilidad y eventos: visibilitychange del documento, pagehide y pageshow de la ventana.
    expect(p.visible()).toBe(true);
    const doc = Object.assign(new EventTarget(), { visibilityState: "hidden" }), ventana = new EventTarget();
    const otra = pestanasDelNavegador({ ...completo, document: doc,
      addEventListener: ventana.addEventListener.bind(ventana), removeEventListener: ventana.removeEventListener.bind(ventana) });
    expect(otra.visible()).toBe(false);
    const vistos = [];
    const quitar = [otra.escucha("visibilitychange", () => vistos.push("v")), otra.escucha("pagehide", () => vistos.push("h"))];
    doc.dispatchEvent(new Event("visibilitychange"));
    ventana.dispatchEvent(new Event("pagehide"));
    doc.dispatchEvent(new Event("pagehide"));
    for (const f of quitar) f();
    doc.dispatchEvent(new Event("visibilitychange"));
    expect(vistos).toEqual(["v", "h"]);
    // Con el crypto de verdad (el de Node): 64 caracteres hex y nunca el token.
    const real = pestanasDelNavegador({ ...completo, crypto: globalThis.crypto });
    const h = await real.huella(TOKEN);
    expect(h).toMatch(/^[0-9a-f]{64}$/);
    expect(h).not.toContain(TOKEN);
  });
});

describe("relevo sin que la líder se cierre (issue #23)", () => {
  it("una líder congelada: una seguidora visible la releva en RELEVO_MS y, al despertar, la vieja deja su stream", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const tabs = [nav.pestana(), nav.pestana(), nav.pestana()];
    const ps = await abreEn(d, tabs);
    const r = caso("G12");
    d.vista(r);
    await flush();
    expect(lideres(ps)).toEqual(["si", "no", "no"]);
    await avanza(LATIDO_MS * 3);                          // con latidos, nadie la releva
    expect(streams(d)).toBe(1);
    tabs[0].congela();
    await avanza(RELEVO_MS - LATIDO_MS - 100);
    expect(streams(d)).toBe(1);
    await avanza(RELEVO_MAX - (RELEVO_MS - LATIDO_MS - 100));
    expect(streams(d)).toBe(2);
    expect(lideres(ps)[0]).toBe("si");                    // la congelada aún no se ha enterado
    expect(lideres(ps.slice(1)).filter((x) => x === "si").length).toBe(1);
    expect(nav.duenos(NOMBRE)).toBe(1);
    expect(d.peticiones[0].signal.aborted).toBe(false);
    // Lo que trae el stream de la nueva líder llega a la otra seguidora; a la congelada, no.
    const otra = structuredClone(r);
    otra.persona = "persona-b";
    d.vista(otra);
    await flush();
    for (const p of ps.slice(1)) expect(sub(p)).toContain("@persona-b");
    expect(sub(ps[0])).toContain("@persona-a");
    // Al despertar: deja de ser líder, corta su stream y pinta lo de la nueva líder. No abre otro.
    tabs[0].despierta();
    await flush();
    expect(lideres(ps)[0]).toBe("no");
    expect(d.peticiones[0].signal.aborted).toBe(true);
    expect(sub(ps[0])).toContain("@persona-b");
    // Sin bucles: con latidos, nadie más la releva.
    await conPing(d, 200_000);
    expect(streams(d)).toBe(2);
    expect(lideres(ps).filter((x) => x === "si").length).toBe(1);
    expect(ps.map(sinConexion)).toEqual(["no", "no", "no"]);
  });

  it("lo que manda una líder de una era anterior no se pinta; lo de una era nueva, sí", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const ps = await abreEn(d, [nav.pestana(), nav.pestana()]);
    const r = caso("G12");
    d.vista(r);
    await flush();
    const intruso = new (nav.pestana().pestanas.Canal)(NOMBRE);
    const otra = structuredClone(r);
    otra.persona = "persona-b";
    intruso.postMessage({ t: "vista", r: otra, en: Date.now(), era: 1, de: "vieja" });
    await flush();
    expect(sub(ps[1])).toContain("@persona-a");
    intruso.postMessage({ t: "vista", r: otra, en: Date.now(), era: Date.now() + 1, de: "nueva" });
    await flush();
    expect(sub(ps[1])).toContain("@persona-b");
    // La líder que oye una era más nueva deja de serlo aunque nadie le haya quitado el cerrojo, y corta su stream.
    expect(lideres(ps)[0]).toBe("no");
    expect(d.peticiones[0].signal.aborted).toBe(true);
    intruso.close();
  });

  it("una líder oculta CEDE_MS con una seguidora visible: la visible coge el cerrojo, y sin bucles", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const tabs = [nav.pestana(), nav.pestana(), nav.pestana()];
    const ps = await abreEn(d, tabs);
    d.vista(caso("G12"));
    await flush();
    tabs[2].oculta(true);
    tabs[0].oculta(true);                                 // la líder
    await avanza(CEDE_MS - 1000);
    expect(streams(d)).toBe(1);
    await avanza(RELEVO_AZAR_MS + 2000);
    expect(streams(d)).toBe(2);
    expect(lideres(ps)).toEqual(["no", "si", "no"]);      // la única visible, no la oculta que esperaba en la cola
    expect(d.peticiones[0].signal.aborted).toBe(true);
    await conPing(d, 120_000);
    expect(streams(d)).toBe(2);
    // Todas ocultas: nadie releva a nadie (con los timers frenados, se relevarían cada minuto).
    tabs[1].oculta(true);
    await conPing(d, 120_000);
    expect(streams(d)).toBe(2);
    expect(lideres(ps)).toEqual(["no", "si", "no"]);
    // La primera que vuelve a verse releva en el acto a la líder, que lleva oculta más de CEDE_MS.
    tabs[2].oculta(false);
    await flush();
    expect(streams(d)).toBe(3);
    expect(lideres(ps)).toEqual(["no", "no", "si"]);
    await conPing(d, 120_000);
    expect(streams(d)).toBe(3);
  });

  it("con todas ocultas y la líder congelada, nadie la releva hasta que una se ve; entonces, en el acto", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const tabs = [nav.pestana(), nav.pestana()];
    const ps = await abreEn(d, tabs);
    d.vista(caso("G12"));
    await flush();
    tabs[1].oculta(true);
    tabs[0].congela();
    await avanza(60_000);
    expect(streams(d)).toBe(1);
    tabs[1].oculta(false);
    await flush();
    expect(streams(d)).toBe(2);
    expect(lideres(ps)[1]).toBe("si");
  });

  it("bfcache: una seguidora cierra el canal en pagehide y, en pageshow, vuelve a pintar sin stream propio ni token nuevo", async () => {
    const d = demonioFalso(), nav = navegadorFalso();
    const tabs = [nav.pestana(), nav.pestana(), nav.pestana()];
    const ps = await abreEn(d, tabs);
    const r = caso("G12");
    d.vista(r);
    await flush();
    tabs[1].sale();
    expect(nav.canales()).toBe(2);
    await avanza(LATIDO_MS * 5);                          // los latidos no le llegan: no la sacan de la caché
    const otra = structuredClone(r);
    otra.persona = "persona-b";
    d.vista(otra);
    await flush();
    expect(tabs[1].desalojada).toBe(false);
    expect(sub(ps[1])).toContain("@persona-a");
    tabs[1].vuelve();
    await flush();
    expect(sub(ps[1])).toContain("@persona-b");           // la última vista, de la líder (hola)
    expect(streams(d)).toBe(1);
    expect(nav.canales()).toBe(3);
    for (const p of d.peticiones) expect(p.headers["X-HK-Token"]).toBe(TOKEN);
    // La líder que sale suelta el cerrojo y corta su stream; otra lo coge. Al volver, es seguidora.
    tabs[0].sale();
    await flush();
    expect(d.peticiones[0].signal.aborted).toBe(true);
    expect(streams(d)).toBe(2);
    expect(lideres(ps).slice(1).filter((x) => x === "si").length).toBe(1);
    tabs[0].vuelve();
    d.vista(r);
    await flush();
    expect(sub(ps[0])).toContain("@persona-a");
    expect(streams(d)).toBe(2);
    expect(lideres(ps)[0]).toBe("no");
    expect(tabs[0].desalojada).toBe(false);
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
