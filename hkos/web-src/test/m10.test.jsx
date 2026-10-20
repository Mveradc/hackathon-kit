import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";
import { fechaHm, sinBidi, zonaJurado, zonaRuta } from "../src/formato.js";
import { Jurado } from "../src/vistas/Jurado.jsx";
import { Ruta } from "../src/vistas/Ruta.jsx";
import { caso, casosM10, demonioFalso, diceAntiguedad, movimientoReducido } from "./ayuda.js";

// K-106 (R-26, R-35, R-36; ADR-0009, ADR-0012, ADR-0013; api.md §11): la parte de Vitest del criterio 4 de M10. Con la
// vista de ejemplo de api.md §11.6 y los momentos de G13 y G14 (scripts/vistas_ejemplo.py, cada bloque validado contra
// $defs/vista_jurado y $defs/vista_ruta), cada campo de los bloques `jurado` y `ruta` sale en el DOM con el mismo texto.
// Las horas se comparan con las que escribe Python en la zona de equipo.md (`horas`) y cada «hace X», con los segundos
// de proyeccion.py (`antiguedades`), sin pasar por el formato de la web. Además: la web no recalcula nada (si la vista
// dice otra cosa, pinta lo que dice), lo estimado se distingue de los hechos, el rojo solo sale para plazo_pasado,
// «no llega» va en ámbar y lo declarado lleva su marca, sin autor.

const CASOS = casosM10();
const JURADO = CASOS.filter((c) => c.respuesta.vista.jurado);
const RUTA = CASOS.filter((c) => c.respuesta.vista.ruta);
const texto = (el) => el.textContent.replace(/\s+/g, " ");
const q = (raiz, sel) => {
  const el = raiz.querySelector(sel);
  expect(el, sel).not.toBeNull();
  return el;
};

function compruebaTiempo(el, obs, edades) {
  const t = el.querySelector(`time[datetime="${obs}"]`);
  expect(t, `antigüedad de ${obs}`).not.toBeNull();
  expect(diceAntiguedad(t.textContent, edades[obs]), `«${t.textContent}» para ${edades[obs]} s (proyeccion.py)`).toBe(true);
}

/** La hora `iso` escrita en `el` como la escribe Python en la zona de equipo.md (`forma`: hm, dia o fecha). */
function compruebaHora(el, iso, horas, forma = "dia") {
  expect(horas[iso], `hora ${iso} en las vistas de ejemplo`).toBeDefined();
  const t = [...el.querySelectorAll(`time[datetime="${iso}"]`)].map((x) => x.textContent);
  expect(t, `hora ${iso}`).toContain(horas[iso][forma]);
}

function compruebaViejo(el, viejo, que) {
  expect(el.querySelector(".hk-prov").classList.contains("is-stale"), `${que}: viejo`).toBe(!!viejo);
}

const DECLARADO_SIN_AUTOR = (el) => {
  const p = el.querySelector(".hk-prov--declarado");
  expect(p, "marca de declarado").not.toBeNull();
  expect(p.textContent).not.toMatch(/declarado por/);
};

// --- jurado ---

const PULSO_COBERTURA = { sin_tarea: "wait", ambigua: "wait", planificada: "idle", en_curso: "live", en_pitch: "idle", cubierta: "ok" };

describe.each(JURADO)("jurado · $nombre", ({ respuesta, antiguedades: edades, horas: { jurado: horas } }) => {
  const j = respuesta.vista.jurado;

  it("la cuenta, el desglose de «sin cubrir» en cinco grupos, por fuerza y el resumen, tal cual", () => {
    const { container } = render(<Jurado respuesta={respuesta} />);
    const c = j.cuenta;
    expect(q(container, "[data-cuenta-notas]").textContent).toBe(String(c.notas));
    expect(q(container, "[data-cuenta-sin-cubrir]").textContent).toBe(String(c.sin_cubrir));
    expect(q(container, "[data-cuenta-cubiertas]").textContent).toBe(String(c.cubiertas));
    expect(q(container, "[data-cuenta-corregidas]").textContent).toMatch(new RegExp(`^${c.corregidas} corregidas?$`));
    expect(texto(q(container, "[data-desglose]"))).toBe(`${c.sin_tarea} sin tarea · ${c.ambiguas} ambigua${c.ambiguas === 1 ? "" : "s"} · `
      + `${c.planificadas} planificada${c.planificadas === 1 ? "" : "s"} · ${c.en_curso} en curso · ${c.en_pitch} en el pitch`);
    const fuerza = [...container.querySelectorAll("[data-por-fuerza]")];
    expect(fuerza.map((el) => [el.dataset.porFuerza, texto(el)])).toEqual(c.sin_cubrir_por_fuerza.map((f) => [f.texto, `${f.n} ${f.texto}`]));
    expect(q(container, "[data-resumen-jurado]").textContent).toBe(j.resumen);
    compruebaTiempo(q(container, '[data-bloque="jurado"]'), j.observado_en, edades);
    compruebaViejo(q(container, '[data-bloque="jurado"]').parentElement, j.viejo, "bloque");
    expect(q(container, "[data-calculado]").textContent).toBe(horas[j.observado_en].hm);
    if (j.fichero) expect(q(container, "[data-fichero]").textContent).toBe(`criterios.md ${j.fichero}`);
    if (j.zona) expect(q(container, "[data-zona]").textContent).toBe(j.zona.valor);
  });

  it("cada nota, en el orden de la vista, con todos sus campos, su cobertura, sus tareas, evidencias y pitch", () => {
    const { container } = render(<Jurado respuesta={respuesta} />);
    const pintadas = [...container.querySelectorAll("[data-nota]")];
    expect(pintadas.map((el) => el.dataset.nota)).toEqual(j.notas.map((x) => x.nota.clave));
    const porClave = Object.fromEntries(j.notas.map((x) => [x.nota.clave, x]));
    for (const x of j.notas) {
      const n = x.nota, el = q(container, `[data-nota="${n.clave}"]`);
      expect(el.dataset.cobertura).toBe(x.cobertura.valor);
      expect(q(el, "[data-dijo]").textContent).toBe(n.dijo);
      // Texto libre de criterios.md (issue #63): siempre entre «», también en paráfrasis, y la nota con su
      // «declarado por … · criterios.md».
      expect(texto(q(el, ".hk-crit__quote"))).toBe(n.literal ? `«${n.dijo}»` : `(paráfrasis) «${n.dijo}»`);
      expect(texto(q(el, ".hk-crit__said .hk-prov"))).toContain("· criterios.md");
      expect(q(el, "[data-quien]").textContent).toBe(n.quien ?? "sin nombre");
      expect(texto(q(el, ".hk-crit__who"))).toBe(`${n.quien != null ? `«${n.quien}»` : "sin nombre"} (${n.papel})`);
      expect(q(el, "[data-papel]").textContent).toBe(n.papel);
      if (n.donde) {
        expect(q(el, "[data-donde-nota]").textContent).toBe(n.donde);
        expect(texto(q(el, ".hk-crit__where"))).toBe(`«${n.donde}»`);
      }
      expect(q(el, "[data-fuerza]").textContent).toBe(n.fuerza.texto);
      expect(q(el, "[data-fuerza]").classList.contains(`hk-crit__force--${n.fuerza.tipo}`)).toBe(true);
      if (n.afecta_a) {
        expect(q(el, "[data-afecta]").textContent).toBe(n.afecta_a);
        expect(texto(q(el, "[data-afecta]").parentElement)).toBe(`Afecta a: «${n.afecta_a}»`);
      }
      expect(q(el, "[data-anotado]").textContent).toBe(n.anotado_por);
      if (n.corrige) expect(q(el, "[data-corrige]").textContent).toBe(n.corrige);
      if (n.hora) compruebaHora(el, n.hora, horas, "fecha");
      else expect(q(el, "[data-hora-nota]").textContent).toBe(`${n.cita} (sin zona)`);
      compruebaTiempo(q(el, ".hk-crit__said"), n.observado_en, edades);
      // La nota es declarada (la escribió una persona): violeta, con «Anotado por».
      expect(q(el, ".hk-crit__said .hk-prov").classList.contains("hk-prov--declarado")).toBe(true);
      const pulso = q(el, "[data-cobertura-pulso]");
      if (x.corregida_por) {
        const otra = porClave[x.corregida_por.valor];
        expect(q(el, "[data-corregida-por]").dataset.corregidaPor).toBe(x.corregida_por.valor);
        compruebaTiempo(el, x.corregida_por.observado_en, edades);
        expect(el.classList.contains("hk-crit--corregida")).toBe(true);
        expect(pulso.textContent).toBe(`Corregida por la de ${otra.nota.hora ? horas[otra.nota.hora].fecha : otra.nota.cita}`);
        expect(q(el, "[data-corregida-por]").classList.contains("hk-prov--declarado")).toBe(true);
      } else {
        const fuente = q(el, "[data-cobertura-fuente]");
        expect(texto(fuente)).toContain(x.cobertura.fuente);
        compruebaTiempo(fuente, x.cobertura.observado_en, edades);
        expect(fuente.classList.contains("is-stale")).toBe(x.cobertura.viejo);
        expect(pulso.classList.contains(`hk-pulse--${x.cobertura.viejo ? "stale" : PULSO_COBERTURA[x.cobertura.valor]}`), `pulso de ${x.cobertura.valor}`).toBe(true);
      }
      if (x.trabajo_nuevo_desde) compruebaHora(q(el, "[data-trabajo-nuevo]"), x.trabajo_nuevo_desde, horas, "hm");
      else expect(el.querySelector("[data-trabajo-nuevo]")).toBeNull();
      for (const f of x.tareas) {
        const t = f.tarjeta, e = f.enlace;
        const tel = q(el, `.hk-crit__item[data-tarea="${t.id}"]:not([data-evidencia])`);
        const s = texto(tel);
        expect(s).toContain(`«${t.titulo}»`);
        expect(s).toContain(t.etiqueta);
        expect(q(tel, ".hk-task__owner").textContent).toBe(t.dueno ? `@${t.dueno}` : "sin dueño");
        expect(s).toContain(t.estado_declarado ? `declarado (${t.fuente})` : t.fuente);
        compruebaTiempo(q(tel, ".hk-crit__foot"), t.observado_en, edades);
        compruebaViejo(q(tel, ".hk-crit__foot"), t.viejo, `tarjeta ${t.id}`);
        if (t.declarado) expect(s).toContain(`⚑ ${t.declarado} a mano`);
        const enl = q(tel, "[data-enlace]");
        expect(q(enl, "[data-cita]").textContent).toBe(e.cita);
        expect(q(enl, "[data-donde]").textContent).toBe(e.donde);
        expect(texto(enl).includes("ambigua, ")).toBe(e.ambiguo);
        compruebaTiempo(enl, e.observado_en, edades);
        DECLARADO_SIN_AUTOR(enl);
      }
      expect(el.querySelectorAll(".hk-crit__item:not([data-evidencia])").length).toBe(x.tareas.length);
      const evs = [...el.querySelectorAll("[data-evidencia]")];
      expect(evs.map((ev) => [ev.dataset.evidencia, ev.dataset.tarea])).toEqual(x.evidencias.map((e) => [e.tipo, e.tarea]));
      x.evidencias.forEach((e, i) => {
        const ev = evs[i];
        if (e.tipo === "prueba") {
          expect(texto(ev)).toContain(e.conexion);
          expect(texto(ev)).toContain(e.valor === "falla" ? "Falla" : "Pasa");
        } else {
          expect(q(ev, "[data-sha]").textContent).toBe(e.valor);
          expect(texto(ev)).toContain(e.tipo === "fusion" ? "fusión" : "commit");
        }
        expect(texto(q(ev, ".hk-prov"))).toContain(e.fuente);
        compruebaTiempo(ev, e.observado_en, edades);
        compruebaViejo(ev, e.viejo, `evidencia de ${e.tarea}`);
      });
      const pitch = el.querySelector("[data-pitch]");
      expect(!!pitch, "pitch").toBe(!!x.pitch);
      if (x.pitch) {
        expect(texto(pitch)).toContain(x.pitch.donde);
        compruebaTiempo(pitch, x.pitch.observado_en, edades);
        DECLARADO_SIN_AUTOR(pitch);
      }
    }
  });

  it("los enlaces rotos (sin_nota), con su tarea, su cita y declarados", () => {
    const { container } = render(<Jurado respuesta={respuesta} />);
    expect([...container.querySelectorAll("[data-sin-nota]")].map((el) => el.dataset.sinNota)).toEqual(j.sin_nota.map((s) => s.tarea));
    for (const s of j.sin_nota) {
      const el = q(container, `[data-sin-nota="${s.tarea}"]`);
      expect(q(el, "[data-cita]").textContent).toBe(s.cita);
      compruebaTiempo(el, s.observado_en, edades);
      DECLARADO_SIN_AUTOR(el);
    }
  });

  it("sin rojo en el jurado (el rojo es solo para un plazo pasado)", () => {
    const { container } = render(<Jurado respuesta={respuesta} />);
    expect(container.querySelector(".hk-pulse--fail, .hk-panel--fail, .hk-cifra--fail")).toBeNull();
  });
});

// --- ruta ---

const VEREDICTO = { a_tiempo: ["A tiempo", "ok"], justo: ["Justo", "wait"], no_llega: ["No llega", "wait"], sin_estimacion: ["Sin estimación", "idle"] };
const ROJO = ".hk-pulse--fail, .hk-panel--fail, .hk-chain__bar--plazo_pasado, .hk-chain__deadline.is-past, .hk-riesgo__cuerpo--fail, .hk-chain__note--plazo_pasado";

/** «+15 h 30» o «−0 h 40» → minutos. */
function minutos(s) {
  const m = /^([+−])(\d+) h (\d\d)$/.exec(s);
  expect(m, `margen «${s}»`).not.toBeNull();
  return (m[1] === "−" ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]));
}

describe.each(RUTA)("ruta · $nombre", ({ respuesta, antiguedades: edades, horas: { ruta: horas } }) => {
  const r = respuesta.vista.ruta;
  const pasados = new Set(r.hechos.filter((h) => h.tipo === "plazo_pasado").map((h) => h.tarea));

  it("el veredicto con su palabra y su color, y la estimación (rango y margen) o sus motivos, tal cual", () => {
    const { container } = render(<Ruta respuesta={respuesta} />);
    const v = q(container, "[data-veredicto]");
    expect(v.dataset.veredicto).toBe(r.veredicto.valor);
    expect(v.classList.contains(`hk-veredicto--${r.veredicto.gravedad}`)).toBe(true);
    const [palabra, tono] = VEREDICTO[r.veredicto.valor];
    const pulso = q(v, "[data-veredicto-palabra]");
    expect(pulso.textContent).toBe(palabra);
    expect(pulso.classList.contains(`hk-pulse--${tono}`)).toBe(true);
    compruebaTiempo(v, r.veredicto.observado_en, edades);
    const est = r.estimacion;
    if (est) {
      expect(q(v, ".hk-estimacion").textContent).toBe("estimación");
      compruebaHora(q(v, "[data-temprano]"), est.temprano, horas);
      compruebaHora(q(v, "[data-tarde]"), est.tarde, horas);
      expect(minutos(q(v, "[data-margen-min]").textContent)).toBe(est.margen_min);
      expect(minutos(q(v, "[data-margen-max]").textContent)).toBe(est.margen_max);
      expect(q(container, "[data-fin]")).not.toBeNull();
      // K-108, punto 2: con temprano = tarde, «hacia» y un punto; si no, «entre … y …» y la barra del rango.
      const uno = Date.parse(est.temprano) === Date.parse(est.tarde);
      expect(texto(q(v, "[data-margen]").nextElementSibling)).toMatch(uno ? /fin hacia .+ \(las medidas no varían\)$/ : /fin entre .+ y .+$/);
      if (r.cadena.length) {
        const fin = q(container, ".hk-chain__fila[data-fin]");
        expect(!!fin.querySelector(".hk-chain__range")).toBe(!uno);
        expect(!!fin.querySelector(".hk-chain__punto")).toBe(uno);
      }
    } else {
      expect(v.querySelector("[data-margen]")).toBeNull();
      expect(texto(v)).toContain("Sin cifra");
      expect([...v.querySelectorAll("[data-motivo]")].map((el) => el.dataset.motivo)).toEqual(r.veredicto.motivos);
      expect(container.querySelector("[data-fin]")).toBeNull();
    }
    // Sin hora central ni «fiabilidad» (issue #46): solo el rango de la vista.
    expect(texto(container)).not.toMatch(/fiabilidad/i);
    expect(q(container, "[data-resumen-ruta]").textContent).toBe(r.resumen);
    expect(q(container, "[data-calculado]").textContent).toBe(horas[r.observado_en].hm);
    // La zona de equipo.md (issue #56): con `ruta.zona`, su valor y declarada; sin ella, el desfase, como antes.
    const cab = q(container, '[data-vista="ruta"] > div');
    if (r.zona?.valor != null) {
      expect(q(cab, "[data-zona]").textContent).toBe(r.zona.valor);
      compruebaTiempo(cab, r.zona.observado_en, edades);
      DECLARADO_SIN_AUTOR(cab);
    } else expect(cab.querySelector("[data-zona], .hk-prov")).toBeNull();
  });

  it("la base por persona, la entrega que manda y las otras al lado, declaradas", () => {
    const { container } = render(<Ruta respuesta={respuesta} />);
    expect([...container.querySelectorAll("[data-base-persona]")].map((el) => el.dataset.basePersona)).toEqual(r.base.personas.map((b) => b.persona));
    for (const b of r.base.personas) {
      const el = q(container, `[data-base-persona="${b.persona}"]`);
      expect(q(el, "[data-n]").textContent).toBe(String(b.n));
      if (b.ritmo_min != null) {
        expect(q(el, "[data-ritmo-min]").textContent).toBe(String(b.ritmo_min));
        expect(q(el, "[data-ritmo-max]").textContent).toBe(String(b.ritmo_max));
      } else {
        expect(q(el, "[data-minimo]").textContent).toBe(String(r.base.minimo));
        expect(texto(el)).toContain("sin ritmo todavía");
      }
    }
    if (r.base.desde) compruebaHora(q(container, "[data-base-desde]"), r.base.desde, horas);
    const o = r.objetivo, obj = q(container, "[data-objetivo]");
    if (o) {
      if (o.valor) compruebaHora(obj, o.valor, horas);
      expect(q(obj, "[data-texto]").textContent).toBe(o.texto ?? "—");
      expect(texto(obj).includes("(confirmar)")).toBe(!!o.confirmar);
      expect(texto(obj)).toContain(`declarado · ${o.donde}`);
      compruebaTiempo(obj, o.observado_en, edades);
      DECLARADO_SIN_AUTOR(obj);
    }
    const otras = [...container.querySelectorAll("[data-otra-entrega]")];
    expect(otras.map((el) => el.dataset.otraEntrega)).toEqual(r.otras_entregas.map((x) => x.donde));
    r.otras_entregas.forEach((x, i) => {
      if (x.nombre) {
        expect(q(otras[i], "[data-nombre]").textContent).toBe(x.nombre);
        expect(texto(otras[i])).toContain(`«${x.nombre}»`);
      }
      if (x.valor) compruebaHora(otras[i], x.valor, horas);
      if (x.donde !== "criterios.md") expect(q(otras[i], "[data-texto]").textContent).toBe(x.texto ?? "—");
      compruebaTiempo(otras[i], x.observado_en, edades);
      DECLARADO_SIN_AUTOR(otras[i]);
    });
  });

  it("los hechos (con su color: rojo solo el plazo pasado) y los riesgos por estimación, en ámbar y con su fin tarde", () => {
    const { container } = render(<Ruta respuesta={respuesta} />);
    const hechos = [...container.querySelectorAll("[data-hecho]")];
    expect(hechos.map((el) => el.dataset.hecho)).toEqual(r.hechos.map((h) => h.tipo));
    r.hechos.forEach((h, i) => {
      const el = hechos[i];
      const cuerpo = q(el, ".hk-riesgo__cuerpo");
      expect(cuerpo.classList.contains(`hk-riesgo__cuerpo--${{ rojo: "fail", ambar: "wait", gris: "stale" }[h.gravedad]}`), `${h.tipo}: ${h.gravedad}`).toBe(true);
      if (h.tarea) expect(texto(el)).toContain(h.tarea);
      if (h.tipo === "plazo_pasado") {
        compruebaHora(cuerpo, h.plazo, horas);
        if (h.arrastra.length) expect(q(el, "[data-arrastra]").textContent).toBe(h.arrastra.join(", "));
      }
      if (h.tipo === "sin_senales") {
        expect(texto(el)).toContain(`@${h.persona}`);
        expect(texto(el)).not.toMatch(/va lent|es lent/);
        if (h.desde) compruebaHora(cuerpo, h.desde, horas, "hm");
      }
      if (h.tipo === "ciclo") expect(q(el, "[data-ciclo]").textContent).toBe(h.ciclo.join(" → "));
      compruebaTiempo(cuerpo, h.observado_en, edades);
      compruebaViejo(cuerpo, h.viejo, `hecho ${h.tipo}`);
    });
    const riesgos = [...container.querySelectorAll("[data-riesgo]")];
    expect(riesgos.map((el) => el.dataset.riesgo)).toEqual(r.riesgos.map((x) => x.tarea));
    r.riesgos.forEach((x, i) => {
      const el = riesgos[i];
      expect(q(el, ".hk-riesgo__tipo").textContent).toBe("ESTIMACIÓN");
      expect(q(el, ".hk-riesgo__cuerpo").classList.contains("hk-riesgo__cuerpo--wait")).toBe(true);
      compruebaHora(q(el, "[data-fin-tarde]"), x.fin_tarde, horas);
      expect(texto(el)).toContain(`@${x.dueno}`);
      expect(q(el, "[data-en-cadena]").dataset.enCadena).toBe(x.en_cadena ? "si" : "no");
      expect(!!el.querySelector(".hk-riesgo__cuerpo .hk-pulse--stale")).toBe(x.viejo);
      expect(el.querySelector(ROJO)).toBeNull();
    });
  });

  it("la cadena: solo sus tareas abiertas, en su orden, con «Hasta», franja declarada y fin estimado discontinuo", () => {
    const { container } = render(<Ruta respuesta={respuesta} />);
    const eslabones = [...container.querySelectorAll("[data-eslabon]")];
    expect(eslabones.map((el) => el.dataset.eslabon)).toEqual(r.cadena.map((e) => e.tarjeta.id));
    r.cadena.forEach((e, i) => {
      const el = eslabones[i], t = e.tarjeta;
      expect(el.dataset.por).toBe(e.por);
      expect(texto(el)).toContain(`«${t.titulo}»`);
      expect(q(el, "[data-etiqueta]").textContent).toBe(t.etiqueta);
      expect(texto(el)).toContain(`@${t.dueno}`);
      compruebaTiempo(el, t.observado_en, edades);
      expect(texto(q(el, "[data-hasta]"))).toContain(`«Hasta» ${e.hasta.texto ?? "—"}`);
      compruebaTiempo(q(el, "[data-franja]"), e.hasta.observado_en, edades);
      DECLARADO_SIN_AUTOR(q(el, "[data-franja]"));
      const fr = e.franja.valor;
      if (fr) {
        compruebaHora(q(el, "[data-franja]"), fr.desde, horas);
        compruebaHora(q(el, "[data-franja]"), fr.hasta, horas);
        expect(q(el, "[data-min]").textContent).toBe(String(fr.min));
        if (fr.compartida > 1) expect(q(el, "[data-compartida]").textContent).toBe(String(fr.compartida));
      }
      if (e.fin_tarde) {
        const f = q(el, "[data-fin-eslabon]");
        expect(f.textContent).toMatch(/^estimación: /);
        compruebaHora(f, e.fin_temprano, horas);
        compruebaHora(f, e.fin_tarde, horas);
      } else expect(el.querySelector("[data-fin-eslabon]")).toBeNull();
    });
    if (r.estimacion) {
      // En la línea de tiempo: la franja (declarada) y, aparte, el tramo estimado, siempre discontinuo y nunca rojo.
      eslabones.forEach((el, i) => {
        const e = r.cadena[i], pasado = pasados.has(e.tarjeta.id);
        const estimado = el.querySelector(".hk-chain__bar--est");
        // K-108, punto 2: con sus dos fines iguales, un punto y no una barra de anchura cero.
        const uno = !!e.fin_tarde && Date.parse(e.fin_temprano) === Date.parse(e.fin_tarde);
        expect(!!estimado).toBe(!!e.fin_tarde && !uno);
        expect(!!el.querySelector(".hk-chain__punto")).toBe(uno);
        if (estimado) expect(estimado.classList.contains("hk-chain__bar--plazo_pasado")).toBe(false);
        expect(!!el.querySelector(".hk-chain__bar--plazo_pasado")).toBe(pasado && !!e.franja.valor);
        expect(!!el.querySelector(".hk-chain__deadline.is-past")).toBe(pasado && !!e.hasta.valor);
      });
    } else {
      // Sin estimación, sin barras: las franjas del plan parecerían una previsión.
      expect(container.querySelector(".hk-chain__bar, .hk-chain__range")).toBeNull();
    }
  });

  it("sin plazo, fuera de la entrega, hitos sin previsión, descansos y «viejo», tal cual", () => {
    const { container } = render(<Ruta respuesta={respuesta} />);
    expect([...container.querySelectorAll("[data-sin-plazo]")].map((el) => el.dataset.sinPlazo)).toEqual(r.sin_plazo.map((x) => x.tarea));
    for (const x of r.sin_plazo) compruebaTiempo(q(container, `[data-sin-plazo="${x.tarea}"]`), x.observado_en, edades);
    // K-108, punto 1 (las vistas de antes de K-108 no traen `sin_usuario`).
    const sinUsuario = r.sin_usuario ?? [];
    expect([...container.querySelectorAll("[data-sin-usuario]")].map((el) => el.dataset.sinUsuario)).toEqual(sinUsuario.map((x) => x.tarea));
    for (const x of sinUsuario) {
      const el = q(container, `[data-sin-usuario="${x.tarea}"]`);
      expect(q(el, "[data-dueno]").textContent).toBe(x.dueno);
      expect(texto(el)).toContain("sin usuario de GitHub: no se mide");
      compruebaTiempo(el, x.observado_en, edades);
      DECLARADO_SIN_AUTOR(el);
    }
    expect([...container.querySelectorAll("[data-fuera]")].map((el) => el.dataset.fuera)).toEqual(r.fuera_de_entrega.map((x) => x.tarea));
    for (const x of r.fuera_de_entrega) compruebaTiempo(q(container, `[data-fuera="${x.tarea}"]`), x.observado_en, edades);
    const hitos = [...container.querySelectorAll("[data-hito]")];
    expect(hitos.map((el) => el.dataset.hito)).toEqual(r.hitos.map((h) => h.hito.nombre));
    r.hitos.forEach((h, i) => {
      if (h.hito.valor) compruebaHora(hitos[i], h.hito.valor, horas);
      expect(q(hitos[i], "[data-pasado]").dataset.pasado).toBe(h.pasado ? "si" : "no");
      expect(texto(hitos[i])).toContain(`«${h.hito.texto}»`);
      expect(q(hitos[i], "[data-nombre]").textContent).toBe(h.hito.nombre);
      expect(texto(q(hitos[i], "[data-nombre]").parentElement)).toBe(`«${h.hito.nombre}»`);
      expect(texto(hitos[i])).toContain(`declarado · ${h.hito.donde}`);
      expect(texto(hitos[i])).not.toMatch(/estimación|acaba/);
      compruebaTiempo(hitos[i], h.hito.observado_en, edades);
      DECLARADO_SIN_AUTOR(hitos[i]);
    });
    const descansos = [...container.querySelectorAll("[data-descanso]")];
    expect(descansos.length).toBe(r.descansos.length);
    r.descansos.forEach((d, i) => {
      expect(q(descansos[i], "[data-texto]").textContent).toBe(d.texto);
      expect(texto(q(descansos[i], "[data-texto]").parentElement)).toBe(`«${d.texto}»`);
      expect(texto(descansos[i])).toContain("declarado · plan.md");
      expect(texto(descansos[i])).toContain(d.personas ? d.personas.map((p) => `@${p}`).join(", ") : "Todos");
      if (d.desde) {
        compruebaHora(descansos[i], d.desde, horas);
        compruebaHora(descansos[i], d.hasta, horas);
      }
      compruebaTiempo(descansos[i], d.observado_en, edades);
    });
    const viejo = q(container, "[data-viejo-bloque]");
    expect(viejo.dataset.viejoBloque).toBe(r.viejo ? "si" : "no");
    if (r.dato_mas_viejo) compruebaTiempo(viejo, r.dato_mas_viejo, edades);
  });

  it("el rojo solo para plazo_pasado; «no llega» y «justo», ámbar", () => {
    const { container } = render(<Ruta respuesta={respuesta} />);
    for (const el of container.querySelectorAll(ROJO)) {
      const hecho = el.closest("[data-hecho]")?.dataset.hecho;
      const eslabon = el.closest("[data-eslabon]")?.dataset.eslabon;
      const general = el.matches(".hk-panel--fail") || !!el.closest(".hk-chain__legend");    // el panel y la leyenda
      expect(hecho === "plazo_pasado" || pasados.has(eslabon) || (general && pasados.size > 0), el.outerHTML.slice(0, 120)).toBe(true);
    }
    if (r.veredicto.valor === "no_llega" || r.veredicto.valor === "justo") {
      expect(q(container, "[data-veredicto-palabra]").classList.contains("hk-pulse--wait")).toBe(true);
    }
  });
});

describe("las vistas de M10 cubren lo que hay que comprobar", () => {
  it("la vista de ejemplo de api.md §11.6, G13 y G14, con todas las coberturas y veredictos que traen", () => {
    expect(CASOS.some((c) => c.nombre.startsWith("ejemplo"))).toBe(true);
    expect(JURADO.filter((c) => c.nombre.startsWith("G13")).length).toBeGreaterThanOrEqual(3);
    expect(RUTA.filter((c) => c.nombre.startsWith("G14")).length).toBe(3);
    const coberturas = new Set(JURADO.flatMap((c) => c.respuesta.vista.jurado.notas.map((x) => x.cobertura.valor)));
    for (const v of ["sin_tarea", "en_curso", "cubierta", "en_pitch"]) expect(coberturas).toContain(v);
    expect(JURADO.some((c) => c.respuesta.vista.jurado.notas.some((x) => x.corregida_por))).toBe(true);
    expect(JURADO.some((c) => c.respuesta.vista.jurado.notas.some((x) => x.trabajo_nuevo_desde))).toBe(true);
    const veredictos = new Set(RUTA.map((c) => c.respuesta.vista.ruta.veredicto.valor));
    for (const v of ["sin_estimacion", "a_tiempo", "no_llega"]) expect(veredictos).toContain(v);
    const hechos = new Set(RUTA.flatMap((c) => c.respuesta.vista.ruta.hechos.map((h) => h.tipo)));
    for (const v of ["plazo_pasado", "sin_senales"]) expect(hechos).toContain(v);
    expect(RUTA.some((c) => c.respuesta.vista.ruta.riesgos.length)).toBe(true);
  });
});

// --- la web no calcula (ADR-0009): si la vista dice otra cosa, pinta lo que dice ---

describe("la web pinta lo que dice el bloque y no lo recalcula (ADR-0009)", () => {
  const ej = CASOS.find((c) => c.nombre.startsWith("ejemplo")).respuesta;
  const con = (cambia) => {
    const v = structuredClone(ej.vista);
    cambia(v);
    return { ...ej, vista: v };
  };

  it("jurado: una cobertura, una cuenta, un orden y un «viejo» imposibles salen tal cual", () => {
    const r = con((v) => {
      const j = v.jurado;
      j.notas[0].cobertura.valor = "cubierta";        // sin tareas ni evidencia: la web no lo discute
      j.notas[1].cobertura.viejo = true;              // con horas recientes
      j.notas.reverse();                              // ni ordena
      Object.assign(j.cuenta, { notas: 99, sin_cubrir: 41, cubiertas: 7, sin_tarea: 13 });
      j.resumen = "jurado: lo que diga el bloque";
    });
    const { container } = render(<Jurado respuesta={r} />);
    const j = r.vista.jurado;
    expect([...container.querySelectorAll("[data-nota]")].map((el) => el.dataset.nota)).toEqual(
      [...j.notas.filter((x) => x.cobertura.valor !== "cubierta"), ...j.notas.filter((x) => x.cobertura.valor === "cubierta")].map((x) => x.nota.clave));
    const falsa = j.notas.find((x) => x.nota.clave === ej.vista.jurado.notas[0].nota.clave);
    expect(container.querySelector(`[data-nota="${falsa.nota.clave}"]`).dataset.cobertura).toBe("cubierta");
    expect(container.querySelector(`[data-nota="${ej.vista.jurado.notas[1].nota.clave}"] [data-cobertura-pulso]`).classList.contains("hk-pulse--stale")).toBe(true);
    expect(q(container, "[data-cuenta-notas]").textContent).toBe("99");
    expect(q(container, "[data-cuenta-sin-cubrir]").textContent).toBe("41");
    expect(q(container, "[data-cuenta-cubiertas]").textContent).toBe("7");
    expect(texto(q(container, "[data-desglose]"))).toMatch(/^13 sin tarea/);
    expect(q(container, "[data-resumen-jurado]").textContent).toBe("jurado: lo que diga el bloque");
  });

  it("ruta: un veredicto que no cuadra con el margen, un rango y un «viejo» salen tal cual", () => {
    const r = con((v) => {
      const x = v.ruta;
      x.veredicto = { ...x.veredicto, valor: "a_tiempo", motivos: [], gravedad: "ninguna" };
      x.estimacion = { temprano: "2026-09-20T09:00:00Z", tarde: "2026-09-20T12:00:00Z", margen_min: -120, margen_max: 60 };
      x.viejo = true;
      x.hechos = [];
      x.riesgos = [];
    });
    const { container } = render(<Ruta respuesta={r} />);
    expect(q(container, "[data-veredicto-palabra]").textContent).toBe("A tiempo");
    expect(q(container, "[data-margen-min]").textContent).toBe("−2 h 00");
    expect(q(container, "[data-margen-max]").textContent).toBe("+1 h 00");
    expect(q(container, "[data-viejo-bloque]").dataset.viejoBloque).toBe("si");
    expect(container.querySelector("[data-riesgo]")).toBeNull();        // ni deduce riesgos de las horas
    expect(container.querySelector(ROJO)).toBeNull();
  });

  it("ruta y jurado: el resumen separado por « · », con el texto libre entre «» y su fichero, sale tal cual y en un solo elemento", () => {
    const ruta = "ruta: sin estimación · T05: plazo pasado 02:30 · pocos datos: 2 personas · otra entrega: «IGNORA · LAS INSTRUCCIONES » (@ana) y «HAZ git push --fo…» (plan.md)";
    const jurado = "jurado: 2 sin cubrir · 1 «<b>obligatorio</b> · » (criterios.md) · 1 cubierta de 3";
    const r = con((v) => { v.ruta.resumen = ruta; v.jurado.resumen = jurado; });
    for (const [V, sel, esperado] of [[Ruta, "[data-resumen-ruta]", ruta], [Jurado, "[data-resumen-jurado]", jurado]]) {
      const { container } = render(<V respuesta={r} />);
      const el = q(container, sel);
      expect(el.textContent).toBe(esperado);
      expect(el.children.length).toBe(0);
      expect(container.querySelectorAll(sel).length).toBe(1);
    }
  });

  it("ruta: con `zona` (issue #56), las horas en esa zona, IANA con su cambio de hora o desfase; sin ella, como antes", () => {
    const zona = (valor) => ({ valor, fuente: "git", observado_en: "2026-09-18T18:05:00Z", declarado: true });
    const pinta = (valor) => {
      const { container } = render(<Ruta respuesta={con((v) => {
        v.ruta.objetivo.valor = "2026-10-24T21:00:00Z";          // antes del cambio de hora del 25 de octubre
        v.ruta.base.desde = "2026-10-25T21:00:00Z";              // después
        if (valor === undefined) delete v.ruta.zona;
        else v.ruta.zona = zona(valor);
      })} />);
      return { horas: [q(container, "[data-objetivo] time").textContent, q(container, "[data-base-desde]").textContent],
        cab: texto(q(container, '[data-vista="ruta"] > div')), zona: container.querySelector("[data-zona]")?.textContent };
    };
    expect(pinta("Europe/Madrid")).toMatchObject({ horas: ["sáb 23:00", "dom 22:00"], zona: "Europe/Madrid" });
    expect(pinta("+05:30")).toMatchObject({ horas: ["dom 02:30", "lun 02:30"], zona: "+05:30" });
    // Sin zona, con valor null o que no se entiende: la de antes (el desfase de la entrega, aquí UTC).
    for (const valor of [undefined, null, "Marte/Olimpo"]) {
      const p = pinta(valor);
      expect(p.horas, String(valor)).toEqual(["sáb 21:00", "dom 21:00"]);
      expect(p.zona, String(valor)).toBeUndefined();
      expect(p.cab, String(valor)).toContain("horas de equipo.md (UTC+00:00).");
    }
  });

  it("jurado (issue #63): con `jurado.zona` IANA, la nota de 2026-10-24T19:00+02:00 sale «sáb 24 · 19:00», como en Ruta; sin ella, como antes", () => {
    const NOTA = "2026-10-24T19:00:00+02:00";
    const zona = { valor: "Europe/Madrid", fuente: "git", observado_en: "2026-09-18T18:05:00Z", declarado: true };
    const vista = (conZona) => con((v) => {
      v.ruta.objetivo.valor = "2026-10-25T12:00:00+01:00";       // la entrega, ya con el horario de invierno
      v.ruta.zona = zona;
      v.ruta.otras_entregas = [{ nombre: null, valor: NOTA, texto: null, motivo: null, donde: "criterios.md",
        cita: "2026-10-24 19:00", fuente: "git", observado_en: "2026-09-19T07:30:00Z", declarado: true }];
      v.jurado.notas[0].nota.hora = NOTA;
      if (conZona) v.jurado.zona = zona;
      else delete v.jurado.zona;
    });
    const r = vista(true), clave = r.vista.jurado.notas[0].nota.clave;
    const jur = render(<Jurado respuesta={r} />).container;
    expect(q(jur, `[data-nota="${clave}"] [data-hora-nota]`).textContent).toBe("sáb 24 · 19:00");
    expect(texto(q(jur, '[data-vista="jurado"] > div'))).toContain("horas en Europe/Madrid.");
    const rut = render(<Ruta respuesta={r} />).container;
    expect(q(rut, '[data-otra-entrega="criterios.md"] time').textContent).toBe("sáb 19:00");
    // Las dos pantallas, con la misma zona: el mismo instante, la misma hora.
    expect(fechaHm(NOTA, zonaJurado(r.vista))).toBe("sáb 24 · 19:00");
    expect(fechaHm(NOTA, zonaRuta(r.vista))).toBe("sáb 24 · 19:00");
    // Sin `jurado.zona`: el desfase de la entrega (+01:00), como antes.
    const sin = vista(false);
    const jur2 = render(<Jurado respuesta={sin} />).container;
    expect(q(jur2, `[data-nota="${clave}"] [data-hora-nota]`).textContent).toBe("sáb 24 · 18:00");
    expect(texto(q(jur2, '[data-vista="jurado"] > div'))).toContain("horas en la zona de equipo.md (UTC+01:00).");
  });

  it("ruta (issue #63, ADR-0009): «No llega» solo con el veredicto no_llega, y la barra `vieja` solo con `viejo`, nunca por sin_senales", () => {
    const pinta = (veredicto, viejo) => {
      const r = con((v) => {
        const x = v.ruta, t = x.cadena[1].tarjeta;              // T06 (@ana), sin plazo pasado
        x.veredicto = { ...x.veredicto, valor: veredicto, motivos: [], gravedad: "ambar" };
        x.estimacion = { temprano: "2026-09-20T09:00:00Z", tarde: "2026-09-20T12:00:00Z", margen_min: -60, margen_max: 30 };
        x.riesgos = [{ tarea: t.id, dueno: t.dueno, fin_tarde: "2026-09-20T12:00:00Z", en_cadena: true, viejo: false }];
        x.hechos = [{ ...x.hechos.find((h) => h.tipo === "sin_senales"), persona: t.dueno }];
        t.viejo = viejo;
      });
      const { container } = render(<Ruta respuesta={r} />);
      const el = q(container, `[data-eslabon="${r.vista.ruta.cadena[1].tarjeta.id}"]`);
      return { palabra: q(el, ".hk-pulse__label").textContent, vieja: !!el.querySelector(".hk-chain__bar--vieja"),
        franja: !!el.querySelector(".hk-chain__bar--franja"), leyenda: texto(q(container, ".hk-chain__legend")) };
    };
    const justo = pinta("justo", false);
    expect(justo.palabra).toBe("Riesgo (estimación)");
    expect(justo).toMatchObject({ vieja: false, franja: true });
    expect(justo.leyenda).not.toMatch(/sin señales|viejo/);
    expect(pinta("a_tiempo", false).palabra).toBe("Riesgo (estimación)");
    expect(pinta("no_llega", false).palabra).toBe("No llega (estimación)");
    const vieja = pinta("justo", true);
    expect(vieja).toMatchObject({ vieja: true, franja: false });
    expect(vieja.leyenda).toContain("dato viejo");
    expect(vieja.leyenda).not.toContain("sin señales");
  });

  it("los hitos, en la línea de tiempo, con su nombre entre «» y su fichero (issue #63)", () => {
    const r = con((v) => {
      v.ruta.estimacion = { temprano: "2026-09-20T09:00:00Z", tarde: "2026-09-20T12:00:00Z", margen_min: -60, margen_max: 30 };
    });
    const { container } = render(<Ruta respuesta={r} />);
    const h = r.vista.ruta.hitos.find((x) => x.hito.valor);
    expect([...container.querySelectorAll(".hk-chain__mark--hito")].map((m) => m.title)).toContain(`«${h.hito.nombre}» · declarado · ${h.hito.donde}`);
  });
});

// --- K-108: decisiones del usuario ---

describe("K-108: tareas sin usuario de GitHub y fin sin rango", () => {
  const ej = CASOS.find((c) => c.nombre.startsWith("ejemplo")).respuesta;
  const con = (cambia) => {
    const v = structuredClone(ej.vista);
    cambia(v);
    return { ...ej, vista: v };
  };
  const estimada = (temprano, tarde, fines) => con((v) => {
    const x = v.ruta;
    x.veredicto = { ...x.veredicto, valor: "a_tiempo", motivos: [], gravedad: "ninguna" };
    x.estimacion = { temprano, tarde, margen_min: 60, margen_max: 60 };
    x.cadena.forEach((e, i) => Object.assign(e, fines[i]));
    x.hechos = [];
    x.riesgos = [];
  });

  it("punto 1: `sin_usuario[]` sale aparte, como las sin plazo, con «sin usuario de GitHub: no se mide» y su procedencia; esa persona no sale en la base", () => {
    const sin = [{ tarea: "T09", dueno: "Persona C", fuente: "git", observado_en: "2026-09-18T18:05:00Z" },
      { tarea: "T11", dueno: "Persona C", fuente: "git", observado_en: "2026-09-18T18:05:00Z" }];
    const r = con((v) => { v.ruta.sin_usuario = sin; });
    const { container } = render(<Ruta respuesta={r} />);
    const els = [...container.querySelectorAll("[data-sin-usuario]")];
    expect(els.map((el) => el.dataset.sinUsuario)).toEqual(["T09", "T11"]);
    for (const el of els) {
      expect(texto(el)).toContain("· Persona C: sin usuario de GitHub: no se mide.");
      expect(texto(el)).not.toContain("@Persona C");
      expect(texto(q(el, ".hk-prov"))).toContain("declarado · equipo.md");
      expect(q(el, `time[datetime="${sin[0].observado_en}"]`).textContent).toBe("hace 14 h");
      DECLARADO_SIN_AUTOR(el);
    }
    // Aparte, en su fila de «De dónde sale», junto a «Sin plazo».
    expect(els[0].closest("dd").previousElementSibling.textContent).toBe("Sin usuario");
    // La base es la de la vista: la web no añade a quien no tiene usuario.
    expect([...container.querySelectorAll("[data-base-persona]")].map((el) => el.dataset.basePersona)).toEqual(r.vista.ruta.base.personas.map((b) => b.persona));
    expect(q(container, '[data-base-persona="ana"]').closest(".hk-veredicto__col").textContent).not.toContain("Persona C");
    expect(texto(q(container, "[data-base]").parentElement)).toContain("Quien no tiene usuario de GitHub no sale aquí");
    // Vacía, o en una vista de antes de K-108 sin el campo: lo dice, sin filas.
    for (const cambia of [(v) => { v.ruta.sin_usuario = []; }, (v) => { delete v.ruta.sin_usuario; }]) {
      const c = render(<Ruta respuesta={con(cambia)} />).container;
      expect(c.querySelector("[data-sin-usuario]")).toBeNull();
      expect(texto(c)).toContain("Ninguna tarea con un dueño sin usuario de GitHub.");
      expect(texto(c)).not.toContain("Quien no tiene usuario de GitHub no sale aquí");
    }
  });

  const usuarioC = (tarea) => ({ tarea, dueno: "Persona C", fuente: "git", observado_en: "2026-09-18T18:05:00Z" });

  it("punto 1: todas las abiertas son de personas sin usuario: sin_estimacion con el motivo sin_usuario, sus tareas y el resumen tal cual", () => {
    const resumen = "ruta: sin estimación · sin usuario: 2 tareas";
    const r = con((v) => {
      const x = v.ruta;
      x.cadena.forEach((e) => { e.tarjeta.dueno = "Persona C"; });
      x.sin_usuario = x.cadena.map((e) => usuarioC(e.tarjeta.id));
      x.sin_plazo = [];
      x.veredicto = { ...x.veredicto, valor: "sin_estimacion", motivos: ["sin_usuario"], gravedad: "gris" };
      x.estimacion = null;
      x.resumen = resumen;
    });
    const { container } = render(<Ruta respuesta={r} />);
    const v = q(container, "[data-veredicto]");
    expect(v.dataset.veredicto).toBe("sin_estimacion");
    expect(q(v, "[data-veredicto-palabra]").textContent).toBe("Sin estimación");
    expect(texto(v)).toContain("Sin cifra");
    expect(v.querySelector("[data-margen]")).toBeNull();
    expect([...v.querySelectorAll("[data-motivo]")].map((el) => [el.dataset.motivo, el.textContent]))
      .toEqual([["sin_usuario", "de personas sin usuario de GitHub (no se miden): T05, T06"]]);
    expect(container.querySelector("[data-fin], .hk-chain__bar, .hk-chain__range, .hk-chain__punto")).toBeNull();
    expect([...container.querySelectorAll("[data-sin-usuario]")].map((el) => el.dataset.sinUsuario)).toEqual(["T05", "T06"]);
    for (const el of container.querySelectorAll("[data-sin-usuario]")) expect(texto(el)).toContain("sin usuario de GitHub: no se mide.");
    expect(q(container, "[data-resumen-ruta]").textContent).toBe(resumen);
  });

  it("punto 1: sin_plazo y sin_usuario a la vez, en el orden de la vista (sin_entrega, ciclo, sin_plazo, sin_usuario, pocos_datos), sin reordenar", () => {
    const motivos = ["sin_entrega", "sin_plazo", "sin_usuario", "pocos_datos"];
    const r = con((v) => {
      const x = v.ruta;
      x.sin_usuario = [usuarioC("T09")];
      x.veredicto = { ...x.veredicto, valor: "sin_estimacion", motivos, gravedad: "gris" };
      x.resumen = "ruta: sin estimación · sin hora de entrega";
    });
    const { container } = render(<Ruta respuesta={r} />);
    expect([...container.querySelectorAll("[data-motivo]")].map((el) => [el.dataset.motivo, el.textContent])).toEqual([
      ["sin_entrega", "sin hora de entrega"], ["sin_plazo", "sin plazo: T21"],
      ["sin_usuario", "de personas sin usuario de GitHub (no se miden): T09"], ["pocos_datos", "pocos datos: hacen falta 3 tareas medidas por persona"]]);
    expect(q(container, "[data-resumen-ruta]").textContent).toBe("ruta: sin estimación · sin hora de entrega");
  });

  it("punto 1: si queda alguna estimable, sin_usuario no es motivo: sale aparte, no se cuenta, y se estima el resto", () => {
    const resumen = "ruta: a tiempo · sin contar T09 (sin usuario)";
    const r = estimada("2026-09-20T09:00:00Z", "2026-09-20T12:00:00Z",
      [{ fin_temprano: "2026-09-20T07:00:00Z", fin_tarde: "2026-09-20T08:00:00Z" }, { fin_temprano: "2026-09-20T09:00:00Z", fin_tarde: "2026-09-20T12:00:00Z" }]);
    r.vista.ruta.sin_usuario = [usuarioC("T09")];
    r.vista.ruta.resumen = resumen;
    const { container } = render(<Ruta respuesta={r} />);
    expect(container.querySelector("[data-motivo]")).toBeNull();
    expect(q(container, "[data-margen]")).not.toBeNull();
    expect(texto(q(container, '[data-sin-usuario="T09"]'))).toContain("T09 · Persona C: sin usuario de GitHub: no se mide, y no se cuenta en la estimación.");
    expect(q(container, "[data-resumen-ruta]").textContent).toBe(resumen);
  });

  it("punto 2: con temprano = tarde, «fin hacia HH:MM (las medidas no varían)», nunca «HH:MM–HH:MM», y un punto en vez de un rango de anchura cero", () => {
    // El mismo instante escrito de dos maneras: la web compara instantes, no textos.
    const r = estimada("2026-09-20T09:00:00Z", "2026-09-20T11:00:00+02:00",
      [{ fin_temprano: "2026-09-20T07:00:00Z", fin_tarde: "2026-09-20T07:00:00Z" }, { fin_temprano: "2026-09-20T09:00:00Z", fin_tarde: "2026-09-20T09:00:00Z" }]);
    const { container } = render(<Ruta respuesta={r} />);
    const v = q(container, "[data-veredicto]");
    expect(texto(q(v, "[data-margen]").nextElementSibling)).toMatch(/· fin hacia dom 11:00 \(las medidas no varían\)$/);
    expect(texto(v)).toContain("la cadena acaba a esa hora");
    expect(q(v, "[data-temprano]")).toBe(q(v, "[data-tarde]"));
    const fin = q(container, ".hk-chain__fila[data-fin]");
    expect(texto(q(fin, ".hk-chain__end"))).toBe("hacia dom 11:00 (las medidas no varían)");
    expect(fin.querySelector(".hk-chain__range")).toBeNull();
    expect(fin.querySelectorAll(".hk-chain__punto").length).toBe(1);
    expect(texto(fin)).not.toContain("nunca una sola hora");
    // Cada eslabón con sus dos fines iguales: lo mismo, sin barra discontinua de anchura cero.
    for (const el of container.querySelectorAll("[data-eslabon]")) {
      expect(texto(q(el, "[data-fin-eslabon]"))).toMatch(/^estimación: acaba hacia dom \d\d:\d\d \(las medidas no varían\)$/);
      expect(el.querySelector(".hk-chain__bar--est")).toBeNull();
      expect(el.querySelectorAll(".hk-chain__punto").length).toBe(1);
    }
    expect(texto(container)).not.toMatch(/(\d\d:\d\d) ?[–-] ?|entre (\S+ \d\d:\d\d) y /);
  });

  it("punto 2: con temprano ≠ tarde, el rango de siempre («entre … y …» y su barra)", () => {
    const r = estimada("2026-09-20T09:00:00Z", "2026-09-20T12:00:00Z",
      [{ fin_temprano: "2026-09-20T07:00:00Z", fin_tarde: "2026-09-20T08:00:00Z" }, { fin_temprano: "2026-09-20T09:00:00Z", fin_tarde: "2026-09-20T12:00:00Z" }]);
    const { container } = render(<Ruta respuesta={r} />);
    const v = q(container, "[data-veredicto]");
    expect(texto(q(v, "[data-margen]").nextElementSibling)).toMatch(/· fin entre dom 11:00 y dom 14:00$/);
    expect(texto(container)).not.toContain("las medidas no varían");
    const fin = q(container, ".hk-chain__fila[data-fin]");
    expect(fin.querySelector(".hk-chain__range")).not.toBeNull();
    expect(fin.querySelector(".hk-chain__punto")).toBeNull();
    for (const el of container.querySelectorAll("[data-eslabon]")) {
      expect(texto(q(el, "[data-fin-eslabon]"))).toMatch(/^estimación: acaba entre /);
      expect(el.querySelector(".hk-chain__bar--est")).not.toBeNull();
    }
  });
});

describe("controles bidi (issue #63)", () => {
  const BIDI = /[\u202A-\u202E\u2066-\u2069]/;

  it("sinBidi quita U+202A–U+202E y U+2066–U+2069 de todo texto, a cualquier profundidad, y nada más", () => {
    const todos = "\u202A\u202B\u202C\u202D\u202E\u2066\u2067\u2068\u2069";
    expect(sinBidi({ a: [`x${todos}y`, 3, null, { b: "a\u202eb" }], [`k\u2066`]: "\u200f«ok»" }))
      .toEqual({ a: ["xy", 3, null, { b: "ab" }], k: "\u200f«ok»" });
  });

  it("la web no pinta ninguno: lo que llega del demonio sale sin ellos en Jurado, Ruta y la Cabina", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
    vi.setSystemTime(new Date("2026-11-25T18:30:00Z"));
    movimientoReducido(false);
    try {
      const base = caso("G12");
      const ej = structuredClone(CASOS.find((c) => c.nombre.startsWith("ejemplo")).respuesta.vista);
      ej.jurado.notas[0].nota.dijo = "dice \u202Esolo esto\u202C ya";
      ej.jurado.notas[0].nota.quien = "Marta\u2066 (Embat)\u2069";
      ej.ruta.descansos[0].texto = "Todos\u202B: cena\u202C";
      ej.ruta.hitos[0].hito.nombre = "Congela\u2067ción";
      const d = demonioFalso();
      render(<App token={TOKEN} fetchImpl={d.fetchImpl} />);
      await flush();
      d.vista({ ...base, vista: { ...base.vista, jurado: ej.jurado, ruta: ej.ruta } });
      await flush();
      const pintado = () => [document.body.textContent,
        ...[...document.body.querySelectorAll("*")].flatMap((el) => [...el.attributes].map((a) => a.value))].join("\n");
      expect(pintado()).not.toMatch(BIDI);
      fireEvent.click(screen.getByRole("button", { name: "Jurado" }));
      await flush();
      expect(document.body.textContent).toContain("«dice solo esto ya»");
      expect(document.body.textContent).toContain("«Marta (Embat)»");
      expect(pintado()).not.toMatch(BIDI);
      fireEvent.click(screen.getByRole("button", { name: "Ruta crítica" }));
      await flush();
      expect(document.body.textContent).toContain("«Todos: cena»");
      expect(document.body.textContent).toContain("«Congelación»");
      expect(pintado()).not.toMatch(BIDI);
    } finally {
      vi.useRealTimers();
    }
  });
});

// --- en la web entera ---

const TOKEN = "a".repeat(64);
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });

describe("la web entera con los bloques (y sin ellos)", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"] });
    vi.setSystemTime(new Date("2026-11-25T18:30:00Z"));
    movimientoReducido(false);
  });

  it("Jurado y Ruta crítica solo con su bloque; si el bloque deja de llegar, vuelve a la Cabina", async () => {
    const base = caso("G12");
    const ej = CASOS.find((c) => c.nombre.startsWith("ejemplo")).respuesta.vista;
    const d = demonioFalso();
    render(<App token={TOKEN} fetchImpl={d.fetchImpl} />);
    await flush();
    const nav = () => [...screen.getByRole("navigation", { name: "Vistas" }).querySelectorAll("button")].map((b) => b.textContent);
    d.vista({ ...base, vista: { ...base.vista, jurado: ej.jurado, ruta: ej.ruta } });
    await flush();
    expect(nav()).toEqual(["Cabina", "Red", "Tablero", "Servicios", "Jurado", "Ruta crítica"]);
    fireEvent.click(screen.getByRole("button", { name: "Ruta crítica" }));
    await flush();
    expect(document.querySelector('[data-vista="ruta"]')).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Jurado" }));
    await flush();
    expect(within(document.querySelector('[data-vista="jurado"]')).getByText(ej.jurado.resumen)).toBeTruthy();
    d.vista({ ...base, vista: { ...base.vista, ruta: ej.ruta } });
    await flush();
    expect(nav()).toEqual(["Cabina", "Red", "Tablero", "Servicios", "Ruta crítica"]);
    expect(document.querySelector('[data-vista="cabina"]')).not.toBeNull();
    d.vista(base);
    await flush();
    expect(nav()).toEqual(["Cabina", "Red", "Tablero", "Servicios"]);
  });
});
