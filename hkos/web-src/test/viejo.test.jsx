import { act, fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";
import { Jurado } from "../src/vistas/Jurado.jsx";
import { Ruta } from "../src/vistas/Ruta.jsx";
import { demonioFalso, movimientoReducido } from "./ayuda.js";

// Restos de la 0.6.0, punto 1 (PR #79, «fuera de mi alcance»; issue #77, A7; constitución III y IV): una línea
// «jurado» o «ruta» vieja de estado-equipo.md lleva la hora del último dato bueno (`fuentes.git.observado_en` en el
// jurado, `dato_mas_viejo` en la ruta), no la del cálculo, y el md lleva `> Git (remoto del equipo): sin leer desde
// HH:MM …` si la vista dice desde cuándo no se lee el remoto. La web tiene que decir lo mismo. Vistas de ejemplo
// (test/vistas/viejo/viejo.json, de scripts/vistas_viejo.py): la vista entera de proyeccion.vista y, por zona, esas
// líneas tal como las escribe proyeccion.markdown. Las horas de la web y del md son las del portátil: se cambia TZ.

const DIR = join(dirname(fileURLToPath(import.meta.url)), "vistas", "viejo");
const CASOS = JSON.parse(readFileSync(join(DIR, "viejo.json"), "utf-8")).casos;
const ZONAS = ["UTC", "Europe/Madrid"];
const TOKEN = "a".repeat(64);
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });
const q = (raiz, sel) => {
  const el = raiz.querySelector(sel);
  expect(el, sel).not.toBeNull();
  return el;
};

function enZona(zona, f) {
  const antes = process.env.TZ;
  process.env.TZ = zona;
  try {
    return f();
  } finally {
    process.env.TZ = antes;
  }
}

describe("los casos cubren lo que hay que comprobar", () => {
  it("jurado y ruta viejos con aviso de git, ruta vieja sin él, todo al día y servicios sin M10", () => {
    const md = CASOS.map((c) => c.md.UTC);
    expect(md.some((m) => m.git.length && m.jurado_y_ruta.length === 2)).toBe(true);
    expect(CASOS.some((c) => c.vista.ruta?.viejo && !c.vista.jurado && !c.md.UTC.git.length)).toBe(true);
    expect(CASOS.some((c) => c.vista.jurado && !c.vista.jurado.viejo && !c.md.UTC.git.length)).toBe(true);
    expect(CASOS.some((c) => c.vista.servicios && !c.vista.jurado && !c.vista.ruta && c.md.UTC.git.length)).toBe(true);
    // Que el caso sirva: la hora del md no es la del cálculo.
    const viejo = CASOS[0];
    expect(viejo.vista.jurado.viejo && viejo.vista.ruta.viejo).toBe(true);
    expect(viejo.md.UTC.jurado_y_ruta.every((l) => !l.includes("(11:00 "))).toBe(true);
  });
});

describe.each(CASOS)("$nombre", (c) => {
  const respuesta = { servido_en: c.servido_en, persona: c.persona, relay: c.relay, vista: c.vista };

  it.each(ZONAS)("en %s, «Lo que ve el agente» es la línea del md, con la misma hora", (zona) => {
    enZona(zona, () => {
      const lineas = [];
      for (const [k, V] of [["jurado", Jurado], ["ruta", Ruta]]) {
        if (!c.vista[k]) continue;
        const { container, unmount } = render(<V respuesta={respuesta} />);
        lineas.push(`- ${q(container, `[data-linea-${k}]`).textContent}`);
        unmount();
      }
      expect(lineas).toEqual(c.md[zona].jurado_y_ruta);
    });
  });

  it("el bloque jurado viejo lleva la antigüedad del último dato bueno, no la del cálculo", () => {
    if (!c.vista.jurado) return;
    const { container } = render(<Jurado respuesta={respuesta} />);
    const j = c.vista.jurado;
    const t = q(container, '[data-bloque="jurado"] time');
    expect(t.getAttribute("datetime")).toBe(j.viejo ? c.vista.fuentes.git.observado_en : j.observado_en);
  });

  it.each(ZONAS)("en %s, el aviso de git de la web es la línea «> Git» del md (o ninguno)", async (zona) => {
    process.env.TZ = zona;
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
    vi.setSystemTime(new Date(c.servido_en));
    movimientoReducido(false);
    try {
      const d = demonioFalso();
      render(<App token={TOKEN} fetchImpl={d.fetchImpl} />);
      await flush();
      d.vista(respuesta);
      await flush();
      const vistas = ["Cabina", ...(c.vista.jurado ? ["Jurado"] : []), ...(c.vista.ruta ? ["Ruta crítica"] : [])];
      for (const v of vistas) {
        fireEvent.click(screen.getByRole("button", { name: v }));
        await flush();
        const avisos = [...document.querySelectorAll("[data-aviso-git]")].map((el) => `> ${el.textContent}`);
        expect(avisos, v).toEqual(c.md[zona].git);
      }
    } finally {
      process.env.TZ = "UTC";
    }
  });
});
