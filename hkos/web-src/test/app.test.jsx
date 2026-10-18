import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";
import { SIN_VISTA_MS } from "../src/datos/demonio.js";
import { tomarToken } from "../src/datos/token.js";
import { horaLocal } from "../src/formato.js";
import { caso, demonioFalso, movimientoReducido, terminaAnimacion } from "./ayuda.js";

// La web contra un demonio falso (el de verdad es K-94/K-95): token fuera de la URL y solo en memoria, stream con
// fetch y X-HK-Token, «sin conexión» tras max(umbral_viejo_s, 40 s), paquetes solo con eventos nuevos y las dos
// acciones tal como dice api.md §4.

const TOKEN = "a".repeat(64);
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });

async function monta(opciones = {}) {
  const d = demonioFalso(opciones);
  const r = render(<App token={TOKEN} fetchImpl={d.fetchImpl} />);
  await flush();
  return { d, ...r };
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
  vi.setSystemTime(new Date("2026-11-25T18:30:00Z"));
  movimientoReducido(false);
});

describe("token (ADR-0010)", () => {
  it("se lee del fragmento, sale de la URL nada más leerlo y no se guarda en ningún almacén", () => {
    window.history.replaceState(null, "", `/?x=1#t=${TOKEN}`);
    const t = tomarToken(window);
    expect(t).toBe(TOKEN);
    expect(window.location.hash).toBe("");
    expect(window.location.href).not.toContain(TOKEN);
    expect(window.location.search).toBe("?x=1");
    expect(JSON.stringify({ ...localStorage })).not.toContain(TOKEN);
    expect(JSON.stringify({ ...sessionStorage })).not.toContain(TOKEN);
    expect(document.cookie).not.toContain(TOKEN);
    expect(tomarToken(window)).toBeNull();
  });

  it("sin token no pide nada y dice cómo abrirla", async () => {
    const d = demonioFalso();
    render(<App token={null} fetchImpl={d.fetchImpl} />);
    await flush();
    expect(d.fetchImpl).not.toHaveBeenCalled();
    expect(screen.getAllByText("hk-os web").length).toBeGreaterThan(0);
  });
});

describe("transporte", () => {
  it("lee /v1/stream con fetch y X-HK-Token, nunca con EventSource ni con el token en la URL", async () => {
    window.EventSource = vi.fn();
    const { d } = await monta();
    d.vista(caso("G12"));
    await flush();
    expect(window.EventSource).not.toHaveBeenCalled();
    expect(d.peticiones[0].url).toBe("/v1/stream");
    for (const p of d.peticiones) {
      expect(p.headers["X-HK-Token"]).toBe(TOKEN);
      expect(p.url).not.toContain(TOKEN);
      expect(p.url).not.toMatch(/[?&](t|token)=/);
    }
    expect(screen.getByRole("heading", { name: /Hola, @persona-a/ })).toBeTruthy();
    delete window.EventSource;
  });

  it("si el stream se corta, pide /v1/vista cada 3 s y vuelve a conectar con espera creciente", async () => {
    const { d } = await monta({ vistaActual: caso("G12") });
    d.vista(caso("G12"));
    await flush();
    d.corta();
    await flush();
    const vistas = () => d.peticiones.filter((p) => p.url === "/v1/vista").length;
    const streams = () => d.peticiones.filter((p) => p.url === "/v1/stream").length;
    expect(vistas()).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(streams()).toBe(2);
    d.corta();
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(streams()).toBe(2);                            // la segunda espera es de 2 s
    await act(async () => { await vi.advanceTimersByTimeAsync(600); });
    expect(streams()).toBe(3);
    expect(vistas()).toBeGreaterThanOrEqual(2);
    for (const p of d.peticiones) expect(p.headers["X-HK-Token"]).toBe(TOKEN);
  });

  it("una conexión medio abierta (sin cierre ni datos): al pasar a «sin conexión» aborta el stream, sondea y reconecta", async () => {
    const r = caso("G12");
    r.vista.umbrales.fuente_s = 10;                       // mandan los 40 s
    const { d, container } = await monta();
    d.vista(r);
    await flush();
    const vistas = () => d.peticiones.filter((p) => p.url === "/v1/vista").length;
    const streams = () => d.peticiones.filter((p) => p.url === "/v1/stream");
    await act(async () => { await vi.advanceTimersByTimeAsync(39_000); });
    expect(streams()[0].signal.aborted).toBe(false);
    expect(vistas()).toBe(0);
    // El stream sigue «abierto» (read() no vuelve nunca): sin el aborto, la web se quedaría colgada aquí.
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(container.querySelector("main").dataset.sinConexion).toBe("si");
    expect(streams()[0].signal.aborted).toBe(true);
    expect(vistas()).toBeGreaterThanOrEqual(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(streams().length).toBe(2);
    d.vista(r);
    await flush();
    expect(container.querySelector("main").dataset.sinConexion).toBe("no");
    expect(container.querySelector(".hk-sub").textContent).not.toContain("sin stream");
  });

  it("stream conectado pero sin ninguna `vista` (el demonio aún sin estado): pide /v1/vista una vez y dice que no tiene estado", async () => {
    const { d } = await monta();
    const vistas = () => d.peticiones.filter((p) => p.url === "/v1/vista").length;
    d.ping();
    await act(async () => { await vi.advanceTimersByTimeAsync(SIN_VISTA_MS - 100); });
    expect(screen.getByRole("status").textContent).toContain("Conectando con tu demonio");
    expect(vistas()).toBe(0);
    await act(async () => { await vi.advanceTimersByTimeAsync(200); });
    expect(screen.getByRole("status").textContent).toContain("aún no tiene estado");
    expect(vistas()).toBe(1);
    for (let i = 0; i < 3; i++) {
      d.ping();
      await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    }
    expect(vistas()).toBe(1);
    expect(d.peticiones.filter((p) => p.url === "/v1/stream").length).toBe(1);
    // Cuando el demonio ya tiene estado, la `vista` del stream lo pinta tal cual.
    d.vista(caso("G12"));
    await flush();
    expect(screen.getByRole("heading", { name: /Hola, @persona-a/ })).toBeTruthy();
  });
});

describe("«sin conexión» (ADR-0009)", () => {
  it("sin nada del demonio en max(umbral_viejo_s, 40 s), toda la página gris y quieta con la hora del último dato", async () => {
    const r = caso("G12");                                // umbrales.fuente_s = 300
    const { d, container } = await monta();
    d.vista(r);
    await flush();
    const ultimo = horaLocal(Date.now());
    await act(async () => { await vi.advanceTimersByTimeAsync(295_000); });
    expect(container.querySelector("main").dataset.sinConexion).toBe("no");
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    const main = container.querySelector("main");
    expect(main.dataset.sinConexion).toBe("si");
    expect(main.classList.contains("is-offline")).toBe(true);
    expect(screen.getByRole("alert").textContent).toContain(`Último dato a las ${ultimo}`);
    expect(container.querySelector(".hk-graph").classList.contains("is-paused")).toBe(true);
    // Un ping basta para volver: no es el estado de ningún dato, es que la web vuelve a recibir.
    d.ping();
    await flush();
    expect(container.querySelector("main").dataset.sinConexion).toBe("no");
  });

  it("con un umbral_viejo_s bajo mandan los 40 s (el doble del ping)", async () => {
    const r = caso("G12");
    r.vista.umbrales.fuente_s = 10;
    const { d, container } = await monta();
    d.vista(r);
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(container.querySelector("main").dataset.sinConexion).toBe("no");
    d.ping();
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(39_000); });
    expect(container.querySelector("main").dataset.sinConexion).toBe("no");
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    expect(container.querySelector("main").dataset.sinConexion).toBe("si");
  });
});

describe("paquetes del grafo con el stream", () => {
  it("un paquete solo aparece con un evento nuevo del SSE y un id repetido no lanza otro", async () => {
    const r = caso("G12");
    const { d, container } = await monta();
    d.vista(r);
    await flush();
    const grafo = container.querySelector(".hk-graph");
    expect(grafo.querySelectorAll("[data-paquete]").length).toBe(0);
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    d.ping();
    await flush();
    expect(grafo.querySelectorAll("[data-paquete]").length).toBe(0);
    // persona-a está vieja en G12: su arista no anima. Con el relay fresco y la presencia al día, sí.
    const viva = structuredClone(r);
    for (const p of viva.vista.personas) p.viejo = false;
    d.vista(viva);
    await flush();
    const ev = { id: "s-a-7", tipo: "edicion", persona: "persona-a", papel: "principal", ts: "2026-11-25T18:20:01Z" };
    d.eventos([ev]);
    await flush();
    expect([...grafo.querySelectorAll("[data-paquete]")].map((p) => p.dataset.paquete)).toEqual(["s-a-7"]);
    act(() => { terminaAnimacion(grafo.querySelector("[data-paquete]")); });
    d.eventos([ev]);
    await flush();
    expect(grafo.querySelectorAll("[data-paquete]").length).toBe(0);
    // El pulso del sondeo de GitHub va por la arista relay–GitHub (al revés: de GitHub al relay).
    d.eventos([{ ...ev, id: "github-12", tipo: "github.sondeo", persona: null, papel: null }]);
    await flush();
    expect([...grafo.querySelectorAll("[data-paquete]")].map((p) => p.dataset.paquete)).toEqual(["github-12"]);
    // Con GitHub viejo, la arista está quieta: otro pulso no lanza nada.
    const vieja = structuredClone(viva);
    vieja.vista.fuentes.github.viejo = true;
    d.vista(vieja);
    await flush();
    expect(grafo.querySelectorAll("[data-paquete]").length).toBe(0);
    d.eventos([{ ...ev, id: "github-13", tipo: "github.sondeo", persona: null, papel: null }]);
    await flush();
    expect(grafo.querySelectorAll("[data-paquete]").length).toBe(0);
    expect(grafo.querySelector('[data-arista="e-gh"]').classList.contains("is-stale")).toBe(true);
  });
});

describe("acciones (api.md §4)", () => {
  it("Reclamar: POST /v1/reclamar con JSON y X-HK-Token, y dice lo que contesta el demonio", async () => {
    const r = caso("G12", 1);                             // persona-b: T02 lista y suya
    const { d } = await monta({ acciones: { "/v1/reclamar": { status: 200, datos: { ok: true, issue: 101 } } } });
    d.vista(r);
    await flush();
    fireEvent.click(screen.getByRole("button", { name: "Reclamar T02" }));
    await flush();
    const p = d.peticiones.find((x) => x.url === "/v1/reclamar");
    expect(p.method).toBe("POST");
    expect(p.headers["Content-Type"]).toBe("application/json");
    expect(p.headers["X-HK-Token"]).toBe(TOKEN);
    expect(JSON.parse(p.body)).toEqual({ tarea: "T02" });
    expect(screen.getByText(/T02 es tuya\. Issue #101 asignado con tu gh/)).toBeTruthy();
  });

  it.each([
    [404, {}, /T02 no existe/],
    [409, { error: "es de @persona-a según el plan" }, /es de @persona-a según el plan/],
    [429, {}, /tope de reclamos/],
    [502, { error: "gh: sin red" }, /gh ha fallado: gh: sin red/],
    [503, { error: "ocupado" }, /^Tu demonio está terminando otra acción; prueba en unos segundos\.$/],
    [503, { error: "otra cosa" }, /^Tu demonio ha contestado 503: otra cosa\.$/],
    [401, {}, /vuelve a abrir la web con hk-os web/],
  ])("Reclamar con %i lo dice sin dar la tarea por reclamada", async (status, datos, texto) => {
    const { d } = await monta({ acciones: { "/v1/reclamar": { status, datos } } });
    d.vista(caso("G12", 1));
    await flush();
    fireEvent.click(screen.getByRole("button", { name: "Reclamar T02" }));
    await flush();
    expect(screen.getByText(texto)).toBeTruthy();
    expect(screen.queryByText(/es tuya/)).toBeNull();
  });

  it("Anotar: POST /v1/anotar con los campos de la plantilla; con 409 dice que la copia no ha cambiado", async () => {
    const { d } = await monta({ acciones: { "/v1/anotar": { status: 409, datos: { error: "rechazado dos veces" } } } });
    d.vista(caso("G12"));
    await flush();
    fireEvent.change(screen.getByLabelText("Quién lo dijo"), { target: { value: "mentor" } });
    fireEvent.change(screen.getByLabelText("Nombre (opcional)"), { target: { value: "Laura" } });
    fireEvent.change(screen.getByLabelText("Qué dijo"), { target: { value: "  Que la demo use datos reales  " } });
    fireEvent.click(screen.getByLabelText("Es literal"));
    fireEvent.change(screen.getByLabelText("Fuerza"), { target: { value: "se valora" } });
    fireEvent.click(screen.getByRole("button", { name: "Anotar" }));
    await flush();
    const p = d.peticiones.find((x) => x.url === "/v1/anotar");
    expect(p.method).toBe("POST");
    expect(p.headers["Content-Type"]).toBe("application/json");
    expect(p.headers["X-HK-Token"]).toBe(TOKEN);
    expect(JSON.parse(p.body)).toEqual({ papel: "mentor", quien: "Laura", que_dijo: "Que la demo use datos reales", literal: true, fuerza: "se valora" });
    expect(screen.getByText(/Tu copia no ha cambiado/)).toBeTruthy();
    expect(screen.getByLabelText("Qué dijo").value).toBe("  Que la demo use datos reales  ");
  });

  // PR #24, decisión 13 del PR #13: Anotar también contesta 503 «ocupado» cuando el cerrojo no llega a tiempo, y la web
  // lo dice con el mismo texto que el de Reclamar, sin vaciar el formulario.
  it.each([
    [503, { error: "ocupado" }, /^Tu demonio está terminando otra acción; prueba en unos segundos\.$/],
    [503, { error: "otra cosa" }, /^Tu demonio ha contestado 503: otra cosa\.$/],
  ])("Anotar con %i %o lo dice como Reclamar y no vacía el formulario", async (status, datos, texto) => {
    const { d } = await monta({ acciones: { "/v1/anotar": { status, datos } } });
    d.vista(caso("G12"));
    await flush();
    fireEvent.change(screen.getByLabelText("Qué dijo"), { target: { value: "Valoramos el impacto" } });
    fireEvent.click(screen.getByRole("button", { name: "Anotar" }));
    await flush();
    expect(screen.getByText(texto)).toBeTruthy();
    expect(screen.getByLabelText("Qué dijo").value).toBe("Valoramos el impacto");
  });

  it("Anotar con 200 dice el sha y vacía el formulario", async () => {
    const { d } = await monta({ acciones: { "/v1/anotar": { status: 200, datos: { ok: true, sha: "a3f9c1e0b1" } } } });
    d.vista(caso("G12"));
    await flush();
    fireEvent.change(screen.getByLabelText("Qué dijo"), { target: { value: "Valoramos el impacto" } });
    fireEvent.click(screen.getByRole("button", { name: "Anotar" }));
    await flush();
    expect(screen.getByText(/Anotado en criterios\.md de main \(a3f9c1e\)/)).toBeTruthy();
    expect(screen.getByLabelText("Qué dijo").value).toBe("");
  });
});
