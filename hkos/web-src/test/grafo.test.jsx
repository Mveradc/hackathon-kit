import { act, render } from "@testing-library/react";
import { createRef } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DESTELLOS_MAX, PAQUETES_MAX, TeamGraph } from "../src/componentes/TeamGraph.jsx";
import { Cabina } from "../src/vistas/Cabina.jsx";
import { construirGrafo, Grafo } from "../src/vistas/comun.jsx";
import { caso, casos, movimientoReducido, pestanaOculta, terminaAnimacion } from "./ayuda.js";

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
    pestanaOculta(false);
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

  it("con la pestaña oculta es como en pausa: retira lo que está en vuelo y al volver no anima lo que pasó mientras", () => {
    const { container, rerender } = render(grafo({ events: [] }));
    rerender(grafo({ events: [{ id: "h1", edge: "e-a" }] }));
    expect(paquetes(container).length).toBe(1);
    act(() => pestanaOculta(true));
    expect(paquetes(container).length).toBe(0);
    expect(container.querySelectorAll(".hk-edge-flash").length).toBe(0);
    const mientras = [{ id: "h1", edge: "e-a" }, { id: "h2", edge: "e-a" }, { id: "h3", edge: "e-a" }];
    rerender(grafo({ events: mientras }));
    expect(paquetes(container).length).toBe(0);
    act(() => pestanaOculta(false));
    expect(paquetes(container).length).toBe(0);
    expect(container.querySelectorAll(".hk-edge-flash").length).toBe(0);
    rerender(grafo({ events: [...mientras, { id: "h4", edge: "e-a" }] }));
    expect([...paquetes(container)].map((p) => p.dataset.paquete)).toEqual(["h4"]);
  });

  it("como mucho PAQUETES_MAX paquetes y DESTELLOS_MAX destellos a la vez: se quedan los más nuevos", () => {
    const { container, rerender } = render(grafo({ events: [] }));
    const muchos = Array.from({ length: 100 }, (_, i) => ({ id: `m${i}`, edge: "e-a" }));
    rerender(grafo({ events: muchos.slice(0, 60) }));
    rerender(grafo({ events: muchos }));
    const ids = [...paquetes(container)].map((p) => p.dataset.paquete);
    expect(ids).toEqual(muchos.slice(-PAQUETES_MAX).map((e) => e.id));
    expect(container.querySelectorAll(".hk-edge-flash").length).toBe(DESTELLOS_MAX);
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

  // ADR-0009: la web no calcula estados de persona. Bajo cada persona, «VIEJO» si la vista dice `viejo` y nada más
  // (ni FALLO por una colisión roja ni ESPERA por una tarea parada, que estado-equipo.md tampoco tiene).
  it.each(casos().map((c) => [c.nombre, c.respuesta]))("%s: bajo cada persona solo el «viejo» de la vista", (_, r) => {
    const reclamo = { reclamar: () => {}, ocupado: null, aviso: null };
    const { container } = render(<Cabina respuesta={r} eventos={[]} sinConexion={false} reclamo={reclamo} anotar={async () => ({})} />);
    const grafo = container.querySelector(".hk-graph");
    for (const p of r.vista.personas) {
      const nodo = grafo.querySelector(`[data-nodo="p-${p.persona}"]`);
      expect(nodo, `nodo de @${p.persona}`).not.toBeNull();
      expect(nodo.querySelector(".hk-node__state")?.textContent ?? null, `@${p.persona}`).toBe(p.viejo ? "VIEJO" : null);
      expect(nodo.classList.contains("is-stale")).toBe(!!p.viejo);
      expect(nodo.classList.contains("is-fail") || nodo.classList.contains("is-wait")).toBe(false);
    }
    expect(grafo.textContent).not.toMatch(/FALLO|ESPERA/);
  });

  it("sin GitHub no es viejo: el nodo sale apagado, sin palabra y sin arista (no viaja ningún pulso)", () => {
    const r = structuredClone(caso("G12"));
    r.vista.fuentes.github = { valor: "no", observado_en: r.servido_en, viejo: false };
    const { nodes, edges } = construirGrafo(r, r.persona, 400, 280);
    expect(nodes.find((n) => n.id === "gh")).toMatchObject({ state: "off", label: "sin GitHub" });
    expect(edges.find((e) => e.id === "e-gh")).toBeUndefined();
    const pulso = [{ id: "github-1", tipo: "github.sondeo", persona: null, papel: null, ts: r.servido_en }];
    const { container } = render(<Grafo respuesta={r} yo={r.persona} eventos={pulso} w={400} h={280} />);
    const gh = container.querySelector('[data-nodo="gh"]');
    expect(gh.classList.contains("is-off")).toBe(true);
    expect(gh.classList.contains("is-stale")).toBe(false);
    expect(gh.querySelector(".hk-node__state")).toBeNull();
    expect(container.querySelector('[data-arista="e-gh"]')).toBeNull();
    expect(container.querySelectorAll("[data-paquete]").length).toBe(0);
  });
});
