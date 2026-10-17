import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { arroba, ETIQUETAS, hace, serviciosDe, tarjetas, TRABAJO, trabajoDe } from "../src/formato.js";
import { Cabina } from "../src/vistas/Cabina.jsx";
import { Fuentes } from "../src/vistas/comun.jsx";
import { Red } from "../src/vistas/Red.jsx";
import { Servicios } from "../src/vistas/Servicios.jsx";
import { Tablero } from "../src/vistas/Tablero.jsx";
import { casos, tablas } from "./ayuda.js";

// Criterio 3 de M9a y ADR-0009 (prueba doble, parte 2): con las vistas de G1–G6, G12 y el estado de 5×20 (que validan
// contra estado.schema.json: scripts/vistas_ejemplo.py), cada vista pinta cada estado, dueño, colisión, antigüedad y
// desajuste con el mismo texto que trae la vista. Lo que la web repite de proyeccion.py (trabajoDe, serviciosDe,
// ETIQUETAS y TRABAJO) se compara con lo que calculó Python (`esperado` y tablas.json), no con la propia web.

const CASOS = casos();

/** serviciosDe en la forma de las claves de proyeccion.servicios_de, en su orden: lo que no cuadra, lo sin confirmar
 *  (filas y luego propuestas) y lo de fuera de servicios. */
function clavesServicios(s) {
  return [
    ...s.noCuadra.map((d) => [d.tipo, d.clave ?? null, d.detalle]),
    ...s.sinConfirmar.map(({ x }) => ["fila", x.clave]),
    ...s.propuestas.map((p) => ["propuesta", p.clave]),
    ...s.fuera.map((d) => ["codigo_fuera", [...(d.rutas || [])].sort()]),
  ];
}

describe("las tablas que la web repite de proyeccion.py", () => {
  it("ETIQUETAS y TRABAJO son las de Python", () => {
    const py = tablas();
    expect(ETIQUETAS).toEqual(py.ETIQUETAS);
    expect(TRABAJO).toEqual(py.TRABAJO);
  });
});

const reclamo = { reclamar: () => {}, ocupado: null, aviso: null };
const anotar = async () => ({ ok: true, texto: "" });
const props = (respuesta) => ({ respuesta, eventos: [], sinConexion: false, reclamo, anotar });

function texto(el) {
  return el.textContent.replace(/\s+/g, " ");
}

function compruebaTarea(raiz, t, servido) {
  const tarjetas = raiz.querySelectorAll(`[data-tarea="${t.id}"]`);
  expect(tarjetas.length, `tarjeta de ${t.id}`).toBeGreaterThan(0);
  for (const el of tarjetas) {
    const s = texto(el);
    expect(s).toContain(t.id);
    expect(s).toContain(t.etiqueta);
    expect(el.querySelector(".hk-task__owner").textContent).toBe(arroba(t.dueno));
    expect(s).toContain(t.estado_declarado ? `declarado (${t.fuente})` : t.fuente);
    const tiempo = el.querySelector(`time[datetime="${t.observado_en}"]`);
    expect(tiempo, `antigüedad de ${t.id}`).not.toBeNull();
    expect(tiempo.textContent).toBe(hace(t.observado_en, servido));
    if (t.declarado) expect(s).toContain("a mano");
    for (const d of t.cumplidas_por_cierre || []) expect(s).toContain(`⚑ ${d} cerrada a mano`);
    for (const e of t.espera || []) expect(s).toContain(e.id);
  }
}

function compruebaColision(raiz, c, servido) {
  const el = raiz.querySelector(`[data-colision="${c.id}"]`);
  expect(el, `colisión ${c.id}`).not.toBeNull();
  const s = texto(el);
  expect(s).toContain(c.gravedad === "rojo" ? "Colisión roja" : "Colisión amarilla");
  expect(s).toContain(`NIVEL ${c.nivel}`);
  for (const r of c.rutas) expect(s).toContain(r);
  for (const p of c.personas) expect(s).toContain(`@${p}`);
  if (c.contrato) expect(s).toContain(`contrato «${c.contrato}»`);
  expect(s).toContain(hace(c.observado_en, servido));
}

function compruebaDesajuste(raiz, d, servido) {
  const els = [...raiz.querySelectorAll(`[data-desajuste="${d.tipo}"]`)].filter((el) => texto(el).includes(d.detalle));
  expect(els.length, `desajuste «${d.detalle}»`).toBeGreaterThan(0);
  for (const el of els) {
    expect(el.querySelector(`time[datetime="${d.observado_en}"]`).textContent).toBe(hace(d.observado_en, servido));
    expect(texto(el)).toContain(d.fuente);
    for (const r of d.rutas || []) expect(texto(el)).toContain(r);
  }
}

describe.each(CASOS)("$nombre", ({ respuesta, esperado }) => {
  const { vista, servido_en: servido } = respuesta;

  it("trabajoDe y serviciosDe dan, para cada persona, lo mismo que proyeccion.trabajo y servicios_de", () => {
    expect(Object.keys(esperado).sort()).toEqual(vista.personas.map((p) => p.persona).sort());
    for (const p of vista.personas) {
      const py = esperado[p.persona];
      expect(trabajoDe(vista, p.persona).map((t) => t.id), `trabajo de @${p.persona}`).toEqual(py.trabajo);
      expect(clavesServicios(serviciosDe(vista, p.persona)), `servicios de @${p.persona}`).toEqual(py.servicios);
    }
  });

  it("tablero: todas las tareas por dueño, las colisiones y la presencia «vieja» de la vista", () => {
    const { container } = render(<Tablero {...props(respuesta)} />);
    for (const t of tarjetas(vista)) compruebaTarea(container, t, servido);
    for (const c of vista.colisiones) compruebaColision(container, c, servido);
    for (const p of vista.personas) {
      const col = container.querySelector(`[data-columna="${p.persona}"]`);
      expect(col, `columna de @${p.persona}`).not.toBeNull();
      expect(!!col.querySelector(".hk-columna__cab .hk-pulse--stale")).toBe(p.viejo);
      for (const t of tarjetas(vista).filter((x) => x.dueno === p.persona)) {
        expect(col.querySelector(`[data-tarea="${t.id}"]`), `${t.id} en la columna de @${p.persona}`).not.toBeNull();
      }
    }
  });

  it("red: lo que está en curso, todas las colisiones y todo lo que no cuadra", () => {
    const { container } = render(<Red {...props(respuesta)} />);
    for (const t of vista.columnas.haciendo) compruebaTarea(container, t, servido);
    for (const t of tarjetas(vista).filter((x) => x.estado === "parada" || x.estado === "no_cerrada")) compruebaTarea(container, t, servido);
    for (const c of vista.colisiones) compruebaColision(container, c, servido);
    for (const d of vista.servicios?.desajustes || []) compruebaDesajuste(container, d, servido);
    const hechas = vista.columnas.hecho.length, total = tarjetas(vista).length;
    expect(texto(container)).toContain(`${hechas}/${total}`);
  });

  it("cabina de cada persona: su trabajo, sus colisiones y lo de servicios que le toca (como estado-equipo.md)", () => {
    const porId = new Map(tarjetas(vista).map((t) => [t.id, t]));
    for (const p of vista.personas) {
      const py = esperado[p.persona];
      const r = { ...respuesta, persona: p.persona };
      const { container, unmount } = render(<Cabina {...props(r)} />);
      const lo = container.querySelector('[aria-label="Lo tuyo"]');
      const pintadas = [...lo.querySelectorAll("[data-tarea]")].map((el) => el.getAttribute("data-tarea"));
      expect(pintadas, `«Lo tuyo» de @${p.persona}, en el orden de proyeccion.trabajo`).toEqual(py.trabajo);
      for (const id of py.trabajo) compruebaTarea(lo, porId.get(id), servido);
      const necesitan = container.querySelector('[aria-label="Te necesitan"]');
      for (const c of vista.colisiones.filter((x) => x.personas.includes(p.persona))) compruebaColision(necesitan, c, servido);
      const desajustes = new Map((vista.servicios?.desajustes || []).map((d) => [JSON.stringify([d.tipo, d.clave ?? null, d.detalle]), d]));
      const filas = [...necesitan.querySelectorAll("[data-sin-confirmar]")].map((el) => ["fila", el.getAttribute("data-sin-confirmar")]);
      const propuestas = [...necesitan.querySelectorAll("[data-propuesta]")].map((el) => ["propuesta", el.getAttribute("data-propuesta")]);
      expect(filas, `filas sin confirmar de @${p.persona}`).toEqual(py.servicios.filter((k) => k[0] === "fila"));
      expect(propuestas, `propuestas de @${p.persona}`).toEqual(py.servicios.filter((k) => k[0] === "propuesta"));
      for (const k of py.servicios.filter((x) => x[0] !== "fila" && x[0] !== "propuesta" && x[0] !== "codigo_fuera")) {
        const d = desajustes.get(JSON.stringify(k));
        expect(d, `desajuste ${JSON.stringify(k)} en la vista`).toBeDefined();
        compruebaDesajuste(necesitan, d, servido);
      }
      unmount();
    }
  });

  it("servicios: cada servicio, conexión, propuesta y desajuste", () => {
    const { container } = render(<Servicios {...props(respuesta)} />);
    const s = vista.servicios;
    if (!s) {
      expect(texto(container)).toContain("no trae servicios");
      return;
    }
    expect(texto(container)).toContain(`servicios.md ${s.fichero.valor}`);
    for (const x of s.lista) {
      const el = container.querySelector(`[data-servicio="${x.nombre}"]`);
      expect(el, `servicio ${x.nombre}`).not.toBeNull();
      const t = texto(el);
      expect(t).toContain(x.puerto ? `:${x.puerto}` : "sin puerto");
      expect(t).toContain(x.carpeta);
      expect(t).toContain(x.confirmacion.valor === "confirmada" ? "confirmada" : "sin confirmar");
      for (const f of x.confirmacion.faltan) expect(t).toContain(`@${f}`);
      if (x.comprobado) {
        expect(t).toContain(x.comprobado.valor.escucha ? "responde" : "no responde");
        expect(el.querySelector(`time[datetime="${x.comprobado.observado_en}"]`).textContent)
          .toBe(hace(x.comprobado.observado_en, servido));
      }
    }
    for (const x of s.conexiones) {
      const el = container.querySelector(`[data-conexion="${x.de} → ${x.a}"]`);
      expect(el, `conexión ${x.de} → ${x.a}`).not.toBeNull();
      if (x.contrato) expect(texto(el)).toContain(`contrato «${x.contrato}»`);
      if (x.resultado) expect(texto(el)).toContain(`la prueba ${x.resultado.valor}`);
    }
    for (const p of s.propuestas) expect(container.querySelector(`[data-propuesta="${p.clave}"]`)).not.toBeNull();
    for (const d of s.desajustes) compruebaDesajuste(container, d, servido);
  });

  it("cabecera: cada fuente con su antigüedad y su «viejo» tal cual", () => {
    const { container } = render(<Fuentes respuesta={respuesta} />);
    for (const [k, d] of Object.entries(vista.fuentes)) {
      const el = container.querySelector(`[data-fuente="${k}"]`);
      expect(el, `fuente ${k}`).not.toBeNull();
      expect(el.classList.contains("is-stale")).toBe(d.viejo);
      expect(el.querySelector(`time[datetime="${d.observado_en}"]`).textContent).toBe(hace(d.observado_en, servido));
    }
  });
});

describe("las vistas de ejemplo cubren lo que hay que comprobar", () => {
  it("hay estados de todas las columnas, colisiones rojas y amarillas, presencia vieja, declaradas y desajustes", () => {
    const todas = CASOS.flatMap((c) => tarjetas(c.respuesta.vista));
    const estados = new Set(todas.map((t) => t.estado));
    for (const e of ["pendiente", "lista", "en_curso", "parada", "en_revision", "integrada", "publicada", "cerrada"]) expect(estados).toContain(e);
    const col = CASOS.flatMap((c) => c.respuesta.vista.colisiones);
    expect(col.some((c) => c.gravedad === "rojo")).toBe(true);
    expect(col.some((c) => c.gravedad === "amarillo")).toBe(true);
    expect(CASOS.some((c) => c.respuesta.vista.personas.some((p) => p.viejo))).toBe(true);
    expect(todas.some((t) => t.estado_declarado)).toBe(true);
    expect(CASOS.some((c) => c.respuesta.vista.servicios?.desajustes.length)).toBe(true);
    expect(new Set(CASOS.map((c) => c.nombre.split(" ")[0]))).toEqual(new Set(["5x20", "G1", "G2", "G3", "G4", "G5", "G6", "G12"]));
  });
});
