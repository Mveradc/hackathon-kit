import { act, fireEvent, render, screen } from "@testing-library/react";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";
import { casos, demonioFalso, movimientoReducido } from "./ayuda.js";

// K-106, «sin los bloques en la vista, la web es la de la 0.4.0» (constitución I, criterio 1 de M10): la web entera
// (cabecera, navegación y las cuatro vistas) con cada vista de ejemplo de la 0.4.0 (G1–G6, G12 y 5×20, que no traen
// `jurado` ni `ruta`) da el mismo DOM, byte a byte, que la web de la 0.4.0. v040/huellas.json guarda el sha256 de cada
// DOM tal como lo pintaba la 0.4.0 (hkos/web-src sin cambios desde v0.4.0); se generó una vez, antes de K-106, con
// HK_HUELLAS_040=escribe, y no se vuelve a generar.

// Las horas «HH:MM» de la 0.4.0 son las del portátil: la huella se toma siempre en UTC (Node relee TZ en cada fecha).
process.env.TZ = "UTC";

const FICHERO = join(dirname(fileURLToPath(import.meta.url)), "v040", "huellas.json");
const ESCRIBE = process.env.HK_HUELLAS_040 === "escribe";
const VISTAS = ["Cabina", "Red", "Tablero", "Servicios"];
const TOKEN = "a".repeat(64);
const huellas = ESCRIBE ? {} : JSON.parse(readFileSync(FICHERO, "utf-8"));
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });
const sha = (s) => createHash("sha256").update(s, "utf8").digest("hex");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
  vi.setSystemTime(new Date("2026-11-25T18:30:00Z"));
  movimientoReducido(false);
});

afterAll(() => {
  if (ESCRIBE) writeFileSync(FICHERO, JSON.stringify(huellas, null, 1) + "\n", "utf-8");
});

describe.each(casos())("$nombre", ({ nombre, respuesta }) => {
  it("sin jurado ni ruta en la vista: la web entera, igual que la de la 0.4.0", async () => {
    expect(respuesta.vista.jurado).toBeUndefined();
    expect(respuesta.vista.ruta).toBeUndefined();
    const d = demonioFalso();
    const { container, unmount } = render(<App token={TOKEN} fetchImpl={d.fetchImpl} />);
    await flush();
    d.vista(respuesta);
    await flush();
    const nav = screen.getByRole("navigation", { name: "Vistas" });
    expect([...nav.querySelectorAll("button")].map((b) => b.textContent)).toEqual(VISTAS);
    for (const v of VISTAS) {
      fireEvent.click(screen.getByRole("button", { name: v }));
      await flush();
      const clave = `${nombre} · ${v}`;
      const h = sha(container.innerHTML);
      if (ESCRIBE) huellas[clave] = h;
      else expect(h, clave).toBe(huellas[clave]);
    }
    unmount();
  });
});
