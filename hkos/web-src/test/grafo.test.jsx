import { act, render } from "@testing-library/react";
import { createRef } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TeamGraph } from "../src/componentes/TeamGraph.jsx";
import { construirGrafo } from "../src/vistas/comun.jsx";
import { caso, movimientoReducido, terminaAnimacion } from "./ayuda.js";

// Criterio 4 de M9a: la animación dice la verdad. Con temporizadores falsos, sin eventos no hay paquetes; N ids dan N
// paquetes y un id repetido, ninguno; con reduced-motion, ninguno; por una arista vieja (presencia vieja, relay caído)
// no viaja nada y la arista queda `stale`.

const nodes = [
  { id: "relay", kind: "relay", x: 200, y: 120 },
  { id: "a", kind: "person", x: 60, y: 60 },
  { id: "b", kind: "person", x: 340, y: 180 },
];
const edges = [
  { id: "e-a", from: "a", to: "relay", channel: "relay" },
  { id: "e-b", from: "b", to: "relay", channel: "relay", stale: true },
];
const paquetes = (c) => c.querySelectorAll("[data-paquete]");

function grafo(props) {
  return <TeamGraph nodes={nodes} edges={edges} width={400} height={240} {...props} />;
}

describe("TeamGraph", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    movimientoReducido(false);
  });

  it("sin eventos no hay paquetes, ni pasando el tiempo: ningún temporizador genera actividad", async () => {
    const { container } = render(grafo({ events: [] }));
    await act(async () => { await vi.advanceTimersByTimeAsync(120_000); });
    expect(paquetes(container).length).toBe(0);
    expect(container.querySelectorAll(".hk-edge-flash").length).toBe(0);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("un paquete solo aparece con un evento nuevo: N ids dan N paquetes y un id repetido, ninguno", async () => {
    const { container, rerender } = render(grafo({ events: [] }));
    rerender(grafo({ events: [{ id: "ev1", edge: "e-a" }] }));
    expect([...paquetes(container)].map((p) => p.dataset.paquete)).toEqual(["ev1"]);
    const tres = [{ id: "ev1", edge: "e-a" }, { id: "ev2", edge: "e-a" }, { id: "ev3", edge: "e-a", reverse: true }];
    rerender(grafo({ events: tres }));
    expect(paquetes(container).length).toBe(3);
    // Se retira al acabar su animación, no por un temporizador.
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(paquetes(container).length).toBe(3);
    act(() => { for (const p of paquetes(container)) terminaAnimacion(p); });
    expect(paquetes(container).length).toBe(0);
    // Los mismos ids otra vez (un render más, otra vista): ninguno.
    rerender(grafo({ events: [...tres] }));
    rerender(grafo({ events: [...tres, { id: "ev2", edge: "e-a" }] }));
    expect(paquetes(container).length).toBe(0);
    rerender(grafo({ events: [...tres, { id: "ev4", edge: "e-a" }] }));
    expect([...paquetes(container)].map((p) => p.dataset.paquete)).toEqual(["ev4"]);
  });

  it("por una arista vieja no viaja nada: queda `stale` y quieta", () => {
    const { container, rerender } = render(grafo({ events: [] }));
    rerender(grafo({ events: [{ id: "x1", edge: "e-b" }] }));
    expect(paquetes(container).length).toBe(0);
    expect(container.querySelectorAll(".hk-edge-flash").length).toBe(0);
    expect(container.querySelector('[data-arista="e-b"]').classList.contains("is-stale")).toBe(true);
  });

  it("con prefers-reduced-motion no hay paquetes: la arista solo se ilumina", () => {
    movimientoReducido(true);
    const { container, rerender } = render(grafo({ events: [] }));
    rerender(grafo({ events: [{ id: "r1", edge: "e-a" }, { id: "r2", edge: "e-a" }] }));
    expect(paquetes(container).length).toBe(0);
    const destellos = container.querySelectorAll(".hk-edge-flash");
    expect(destellos.length).toBe(2);
    act(() => { for (const d of destellos) terminaAnimacion(d); });
    expect(container.querySelectorAll(".hk-edge-flash").length).toBe(0);
  });

  it("en pausa (la web sin conexión) no lanza nada, y lo que llegó entonces no se anima después", () => {
    const { container, rerender } = render(grafo({ events: [], paused: true }));
    rerender(grafo({ events: [{ id: "p1", edge: "e-a" }], paused: true }));
    expect(paquetes(container).length).toBe(0);
    rerender(grafo({ events: [{ id: "p1", edge: "e-a" }], paused: false }));
    expect(paquetes(container).length).toBe(0);
  });

  it("la ref llega como prop (sin forwardRef) y apunta al <svg>", () => {
    const ref = createRef();
    render(grafo({ ref }));
    expect(ref.current.tagName.toLowerCase()).toBe("svg");
  });
});

describe("el grafo de la vista", () => {
  it("presencia vieja o relay caído dejan la arista de la persona `stale`", () => {
    const r = caso("G12");
    const { edges: e1 } = construirGrafo(r, r.persona, 400, 280);
    for (const p of r.vista.personas) expect(e1.find((e) => e.id === `e-${p.persona}`).stale).toBe(!!p.viejo || !!r.vista.fuentes.relay.viejo);
    const caido = { ...r, relay: { conectado: false, desde: r.servido_en } };
    const { edges: e2, nodes } = construirGrafo(caido, r.persona, 400, 280);
    expect(e2.every((e) => !e.id.startsWith("e-") || e.stale)).toBe(true);
    expect(nodes.find((n) => n.id === "relay").state).toBe("stale");
  });
});
