import { render } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";
import { describe, expect, it } from "vitest";
import { Cabina } from "../src/vistas/Cabina.jsx";
import { Red } from "../src/vistas/Red.jsx";
import { Tablero } from "../src/vistas/Tablero.jsx";
import { diceAntiguedad } from "./ayuda.js";

// K-113 (R-34; ADR-0009, ADR-0014, decisión 7; api.md §6, M11): la parte de Vitest del criterio 3 de M11. Una colisión
// `2b` llega en la vista como cualquier otra (nivel `2b`, gravedad `amarillo`) y la web nueva y la clásica la pintan
// con el mismo texto que la línea de estado-equipo.md: «nivel 2b · fusión estructural sin conflictos», con sus rutas y
// sus personas. La web no calcula nada: el color sale de `gravedad`, no del nivel.
//
// Vistas de ejemplo (test/vistas/m11/G15.json): cada punto de control de G15 con el relay de verdad y los `conflictos`
// del guion (scripts/vistas_ejemplo.py, como igualdad.py); `md`, las líneas de «Colisiones que te afectan» de cada
// persona que da proyeccion.linea_colision. TEXTO_2B se compara con esas líneas: proyeccion.py no lo expone como
// constante (no va en tablas.json).

const DIR = dirname(fileURLToPath(import.meta.url));
const { casos } = JSON.parse(readFileSync(join(DIR, "vistas", "m11", "G15.json"), "utf-8"));
const TEXTO_2B = "fusión estructural sin conflictos";
const con2b = casos.filter((c) => c.vista.colisiones.some((x) => x.nivel === "2b"));
const nombre = (c) => `G15 t=${c.tras} s`;

const reclamo = { reclamar: () => {}, ocupado: null, aviso: null };
const anotar = async () => ({ ok: true, texto: "" });
const props = (r) => ({ respuesta: r, eventos: [], sinConexion: false, reclamo, anotar });
const texto = (el) => el.textContent.replace(/\s+/g, " ").trim();

/** Una línea de colisión del md, por partes: `- AMARILLO · nivel 2b · fusión … · <rutas> · <personas> (HH:MM)`. */
function partesMd(linea) {
  const m = /^- (ROJO|AMARILLO) · nivel (\S+)(?: · (fusión estructural sin conflictos))?(?: · contrato «.*»)? · (.+) · ((?:@[^,\s]+(?:, )?)+) \(\d\d:\d\d\)$/.exec(linea);
  expect(m, `línea del md: ${linea}`).not.toBeNull();
  return { gravedad: m[1].toLowerCase(), nivel: m[2], que: m[3] ?? null, rutas: m[4], personas: m[5] };
}

/** Las rutas de la línea del md (proyeccion.linea_colision: las 3 primeras y «(+n)») son las de la colisión. */
function rutasIguales(mdRutas, c) {
  const resto = c.rutas.length > 3 ? ` (+${c.rutas.length - 3})` : "";
  return mdRutas === c.rutas.slice(0, 3).join(", ") + resto;
}

/** La alerta de la colisión `c` dice lo mismo que su línea del md (si la hay) y que la vista. */
function compruebaColision(raiz, c, linea, edades) {
  const el = raiz.querySelector(`[data-colision="${c.id}"]`);
  expect(el, `colisión ${c.id}`).not.toBeNull();
  const nivel = texto(el.querySelector(".hk-alert__level"));
  expect(nivel).toBe(c.nivel === "2b" ? `NIVEL 2b · ${TEXTO_2B}` : `NIVEL ${c.nivel}`);
  expect(texto(el.querySelector(".hk-alert__path"))).toBe(c.rutas.join(", "));
  expect(texto(el)).toContain(c.gravedad === "rojo" ? "Colisión roja" : "Colisión amarilla");
  expect(el.getAttribute("role")).toBe(c.gravedad === "rojo" ? "alert" : "status");
  const detalle = texto(el.querySelector(".hk-alert__detail"));
  expect(detalle).toContain(c.personas.map((p) => `@${p}`).join(", "));
  const hace = detalle.split(" · ").at(-1);
  expect(diceAntiguedad(hace, edades[c.observado_en]), `«${hace}» para ${edades[c.observado_en]} s (proyeccion.py)`).toBe(true);
  if (linea) {
    const md = partesMd(linea);
    expect(md.gravedad).toBe(c.gravedad);
    // «nivel 2b · fusión estructural sin conflictos» en el md; en la web, con su «NIVEL» de siempre.
    expect(nivel).toBe(`NIVEL ${md.nivel}${md.que ? ` · ${md.que}` : ""}`);
    expect(rutasIguales(md.rutas, c), `rutas del md «${md.rutas}» / ${c.rutas}`).toBe(true);
    expect(detalle).toContain(md.personas);
  }
}

/** La línea del md de la colisión `c` (de `persona` o de cualquiera): el id es nivel y par, así que nivel y personas. */
const lineaDe = (md, c, persona) => (persona ? md[persona] : Object.values(md).flat()).find((l) =>
  l.includes(`nivel ${c.nivel} ·`) && l.includes(` · ${c.personas.map((p) => `@${p}`).join(", ")} (`));

describe("M11: la colisión 2b de G15", () => {
  it("G15 trae colisiones 2b amarillas junto a una 2 roja del mismo par, y el md el texto de la decisión 7", () => {
    expect(con2b.length).toBeGreaterThan(0);
    for (const caso of con2b) {
      const { vista, md } = caso;
      const b = vista.colisiones.filter((c) => c.nivel === "2b");
      for (const c of b) expect(c.gravedad, nombre(caso)).toBe("amarillo");
      expect(b.some((x) => vista.colisiones.some((c) => c.nivel === "2" && c.gravedad === "rojo"
        && c.personas.join() === x.personas.join())), nombre(caso)).toBe(true);
      const lineas = Object.values(md).flat().filter((l) => l.includes("nivel 2b"));
      expect(lineas.length, nombre(caso)).toBeGreaterThan(0);
      for (const l of lineas) expect(l.startsWith(`- AMARILLO · nivel 2b · ${TEXTO_2B} · `), l).toBe(true);
    }
    // Sin 2b en el guion antes de que Mergiraf resuelva nada (t=30 s y t=60 s).
    expect(casos.filter((c) => !con2b.includes(c)).length).toBeGreaterThan(0);
  });

  it.each([["tablero", Tablero], ["red", Red]])("%s: cada colisión de cada punto, la 2b con el texto del md", (_, V) => {
    for (const caso of casos) {
      const { md, antiguedades: edades, ...respuesta } = caso;
      const { container, unmount } = render(<V {...props(respuesta)} />);
      for (const c of respuesta.vista.colisiones) compruebaColision(container, c, lineaDe(md, c), edades);
      expect(container.querySelectorAll(".hk-alert__level").length).toBeGreaterThanOrEqual(respuesta.vista.colisiones.length);
      unmount();
    }
  });

  it("cabina de cada persona: las mismas colisiones que «Colisiones que te afectan» de su md, con el mismo texto", () => {
    for (const caso of casos) {
      const { md, antiguedades: edades, ...respuesta } = caso;
      const { vista } = respuesta;
      for (const p of vista.personas) {
        const r = { ...respuesta, persona: p.persona };
        const { container, unmount } = render(<Cabina {...props(r)} />);
        const necesitan = container.querySelector('[aria-label="Te necesitan"]');
        const pintadas = [...necesitan.querySelectorAll("[data-colision]")].map((el) => el.getAttribute("data-colision"));
        const suyas = vista.colisiones.filter((c) => c.personas.includes(p.persona));
        expect(pintadas.sort(), `${nombre(caso)}, colisiones de @${p.persona}`).toEqual(suyas.map((c) => c.id).sort());
        expect(suyas.length, `${nombre(caso)}, líneas del md de @${p.persona}`).toBe(md[p.persona].length);
        for (const c of suyas) {
          const linea = lineaDe(md, c, p.persona);
          expect(linea, `${nombre(caso)}, línea del md de ${c.id} para @${p.persona}`).toBeDefined();
          compruebaColision(necesitan, c, linea, edades);
        }
        unmount();
      }
    }
  });

  it("la web no calcula: pinta la gravedad que trae la vista y el texto solo con nivel 2b", () => {
    const { md, antiguedades, ...respuesta } = con2b[0];
    const { vista } = respuesta;
    const base = vista.colisiones.find((c) => c.nivel === "2b");
    const colisiones = [
      { ...base, id: "x-2b-rojo", gravedad: "rojo" },                  // si la vista dijera rojo, rojo
      { ...base, id: "x-2-amarillo", nivel: "2", gravedad: "amarillo" }, // un nivel 2 no lleva el texto de 2b
    ];
    const { container } = render(<Red {...props({ ...respuesta, vista: { ...vista, colisiones } })} />);
    const rojo = container.querySelector('[data-colision="x-2b-rojo"]');
    expect(texto(rojo)).toContain("Colisión roja");
    expect(texto(rojo.querySelector(".hk-alert__level"))).toBe(`NIVEL 2b · ${TEXTO_2B}`);
    const dos = container.querySelector('[data-colision="x-2-amarillo"]');
    expect(texto(dos)).toContain("Colisión amarilla");
    expect(texto(dos.querySelector(".hk-alert__level"))).toBe("NIVEL 2");
  });
});

describe("M11: la web clásica (hkos/web/index.html) pinta la 2b con el texto del md", () => {
  it("cada colisión de cada punto empieza como su línea del md: «AMARILLO · nivel 2b · fusión estructural sin conflictos»", () => {
    const html = readFileSync(join(DIR, "..", "..", "web", "index.html"), "utf-8");
    for (const { md, vista, servido_en, tras } of casos) {
      // Sin token (#t=…), la página no pide nada: solo se le pasa la vista con su recibir().
      const dom = new JSDOM(html, { runScripts: "dangerously", url: "http://127.0.0.1:7777/" });
      try {
        dom.window.recibir({ vista, servido_en }, "prueba");
        const col = dom.window.document.getElementById("colisiones");
        for (const c of vista.colisiones) {
          const el = col.querySelector(`[data-id="${c.id}"]`);
          expect(el, `G15 t=${tras} s, colisión ${c.id}`).not.toBeNull();
          const cab = el.querySelector("strong").textContent;
          const linea = lineaDe(md, c);
          expect(linea, `G15 t=${tras} s, línea del md de ${c.id}`).toBeDefined();
          const m = partesMd(linea);
          expect(cab).toBe(`${m.gravedad.toUpperCase()} · nivel ${m.nivel}${m.que ? ` · ${m.que}` : ""}`);
          expect(el.textContent).toContain(` · ${m.personas} · `);
          if (c.rutas.length <= 3) expect(el.textContent).toContain(` · ${m.rutas} · ${m.personas} · `);
          if (c.nivel === "2b") expect(cab).toBe(`AMARILLO · nivel 2b · ${TEXTO_2B}`);
          else expect(cab).toBe(`${c.gravedad.toUpperCase()} · nivel ${c.nivel}`);
        }
      } finally {
        dom.window.close();
      }
    }
  });
});
