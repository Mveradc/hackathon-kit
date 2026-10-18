import { useState } from "react";
import { Button, Panel, ProvenanceTag, StatusPulse } from "../componentes/componentes.jsx";
import { arroba, autorPropuesta, canal, hace, hora, nombrePropuesta, serviciosDe, trabajoDe } from "../formato.js";
import { Colision, Desajuste, Grafo, Tarea, TextoNovedad, Vacio } from "./comun.jsx";

// Cabina (pantallas/cabina.dc.html), la vista por defecto: lo de una persona. Lo tuyo, lo que puedes reclamar, lo que
// te necesita, el equipo de un vistazo y Anotar. Confirmar no está en la web (M9a): se dice como texto.

export function BotonReclamar({ t, reclamo }) {
  return (
    <Button variant="primary" busy={reclamo.ocupado === t.id} disabled={!!reclamo.ocupado}
      onClick={() => reclamo.reclamar(t.id)} aria-label={`Reclamar ${t.id}`}>Reclamar</Button>
  );
}

export function AvisoReclamo({ reclamo }) {
  if (!reclamo.aviso) return null;
  return <div role="status" className={`hk-aviso hk-aviso--${reclamo.aviso.ok ? "ok" : "error"}`}>{reclamo.aviso.texto}</div>;
}

const PAPEL = { jurado: "Jurado", mentor: "Mentor", organizacion: "Organización" };
const FUERZAS = ["sin precisar", "dato", "obligatorio", "se valora", "nos gustaría ver", "comentario suelto"];

export function Anotar({ anotar }) {
  const vacio = { papel: "jurado", quien: "", que_dijo: "", literal: false, fuerza: "sin precisar", donde: "" };
  const [f, setF] = useState(vacio);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState(null);
  const pon = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function enviar(e) {
    e.preventDefault();
    if (ocupado || !f.que_dijo.trim()) return;
    setOcupado(true);
    const cuerpo = { papel: f.papel, que_dijo: f.que_dijo.trim(), literal: f.literal, fuerza: f.fuerza };
    if (f.quien.trim()) cuerpo.quien = f.quien.trim();
    if (f.donde.trim()) cuerpo.donde = f.donde.trim();
    const r = await anotar(cuerpo);
    setAviso(r);
    if (r.ok) setF(vacio);
    setOcupado(false);
  }

  return (
    <Panel title="Anotar" meta="va a criterios.md">
      <form className="hk-form" onSubmit={enviar}>
        <div className="hk-form__dos">
          <div className="hk-form">
            <label htmlFor="an-papel">Quién lo dijo</label>
            <select id="an-papel" value={f.papel} onChange={pon("papel")}>
              {Object.entries(PAPEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="hk-form">
            <label htmlFor="an-quien">Nombre (opcional)</label>
            <input id="an-quien" type="text" maxLength={80} value={f.quien} onChange={pon("quien")} />
          </div>
        </div>
        <label htmlFor="an-que">Qué dijo</label>
        <textarea id="an-que" rows={3} maxLength={500} required value={f.que_dijo} onChange={pon("que_dijo")}
          placeholder="«Valoraremos que la demo funcione con datos reales»" />
        <label className="hk-form__check">
          <input type="checkbox" checked={f.literal} onChange={pon("literal")} /> Es literal
        </label>
        <div className="hk-form__dos">
          <div className="hk-form">
            <label htmlFor="an-fuerza">Fuerza</label>
            <select id="an-fuerza" value={f.fuerza} onChange={pon("fuerza")}>
              {FUERZAS.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </div>
          <div className="hk-form">
            <label htmlFor="an-donde">Dónde (opcional)</label>
            <input id="an-donde" type="text" maxLength={80} value={f.donde} onChange={pon("donde")} />
          </div>
        </div>
        <div className="hk-acciones" style={{ justifyContent: "space-between" }}>
          <span className="hk-meta">Tu demonio la añade con tu nombre y la hora, commit y push, sin tocar tu copia.</span>
          <Button type="submit" variant="primary" busy={ocupado} disabled={!f.que_dijo.trim()}>Anotar</Button>
        </div>
      </form>
      {aviso ? <div role="status" className={`hk-aviso hk-aviso--${aviso.ok ? "ok" : "error"}`}>{aviso.texto}</div> : null}
    </Panel>
  );
}

export function Cabina({ respuesta, eventos, sinConexion, reclamo, anotar }) {
  const { vista, persona, servido_en: servido } = respuesta;
  const yo = (vista.personas || []).find((p) => p.persona === persona);
  const mias = trabajoDe(vista, persona);
  const libres = (vista.columnas?.falta || []).filter((t) => !t.dueno && (t.estado === "lista" || t.estado === "pendiente"));
  const colisiones = (vista.colisiones || []).filter((c) => c.personas.includes(persona));
  const s = serviciosDe(vista, persona);
  const necesitan = colisiones.length + s.noCuadra.length + s.sinConfirmar.length + s.propuestas.length;
  const rojo = colisiones.some((c) => c.gravedad === "rojo") || s.noCuadra.some((d) => d.tipo.endsWith("falla"));

  let pulso = <StatusPulse state="idle" label="Sin sesión" />;
  if (yo) {
    const papeles = Object.entries(yo.papeles || {}).map(([k, n]) => `${n} ${k}`).join(", ");
    pulso = yo.activos
      ? <StatusPulse state={yo.viejo ? "stale" : "live"} label={`Tu sesión: ${papeles}${yo.haciendo.length ? ` · ${yo.haciendo.join(", ")}` : ""}`} />
      : <StatusPulse state={yo.viejo ? "stale" : "idle"} label={yo.ultima_senal ? `Sin sesión desde ${hora(yo.ultima_senal)}` : "Sin sesión"} />;
  }

  return (
    <div className="hk-col" data-vista="cabina">
      <header className="hk-cabecera">
        <div className="hk-cabecera__izq">
          <span className={`hk-avatar${yo?.viejo ? " is-stale" : ""}`} aria-hidden="true">{(yo?.nombre || persona || "?").slice(0, 2).toUpperCase()}</span>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <h1 className="hk-titulo">Hola, {arroba(persona)}</h1>
            {pulso}
          </div>
        </div>
      </header>
      <div className="hk-fila">
        <div className="hk-col" style={{ flex: "1 1 380px" }}>
          <Panel title="Lo tuyo" meta={String(mias.length)}>
            {mias.length ? mias.map((t) => (
              <Tarea key={t.id} t={t} servido={servido}
                action={t.estado === "lista" || t.estado === "pendiente" ? <BotonReclamar t={t} reclamo={reclamo} /> : null} />
            )) : <Vacio>Nada abierto.</Vacio>}
            <AvisoReclamo reclamo={reclamo} />
          </Panel>
          <Panel title="Para reclamar" meta={String(libres.length)}>
            {libres.length ? libres.map((t) => (
              <div key={t.id} className="hk-reclamar">
                <Tarea t={t} servido={servido} />
                <BotonReclamar t={t} reclamo={reclamo} />
              </div>
            )) : <Vacio>No hay tareas sin dueño listas o pendientes.</Vacio>}
          </Panel>
        </div>
        <div className="hk-col" style={{ flex: "1 1 420px" }}>
          <Panel title="Te necesitan" meta={String(necesitan)} tone={rojo ? "fail" : necesitan ? "wait" : undefined}>
            {colisiones.map((c) => <Colision key={c.id} c={c} servido={servido} />)}
            {s.noCuadra.map((d, i) => <Desajuste key={`d${i}`} d={d} servido={servido} />)}
            {s.sinConfirmar.map(({ tipo, nombre, x }) => (
              <div key={x.clave} className="hk-caja hk-caja--wait" data-sin-confirmar={x.clave}>
                <StatusPulse state="wait" label="Tu confirmación" />
                <span className="hk-texto">{tipo} «{nombre}» · cambio de {x.confirmacion.por.map(arroba).join(", ") || "nadie del equipo conocido"}</span>
                <ProvenanceTag source={canal(x.confirmacion.fuente)} label={x.confirmacion.fuente}
                  age={hace(x.confirmacion.observado_en, servido)} at={x.confirmacion.observado_en} />
                <span className="hk-meta">Se confirma pasando la fila desde tu portátil (no desde la web).</span>
              </div>
            ))}
            {s.propuestas.map((p) => (
              <div key={p.clave} className="hk-caja hk-caja--declarado" data-propuesta={p.clave}>
                <StatusPulse state="wait" label="Propuesta" />
                <span className="hk-texto">propuesta de {nombrePropuesta(p)} · de {autorPropuesta(p)}</span>
                <ProvenanceTag source="declarado" label={`declarado por ${p.autor_declarado || "—"}${p.hora_declarada ? ` · ${p.hora_declarada}` : ""}`}
                  age={hace(p.observado_en, servido)} at={p.observado_en} />
                <span className="hk-meta">La confirmas pasándola a su tabla de servicios.md desde tu portátil.</span>
              </div>
            ))}
            {!necesitan ? <Vacio>Nada te necesita ahora.</Vacio> : null}
          </Panel>
          <Panel title="Novedades" meta={String((vista.novedades || []).length)}>
            {(vista.novedades || []).length ? vista.novedades.map((n, i) => (
              <div key={i} className="hk-bloque" data-novedad={i}>
                <span className="hk-texto"><TextoNovedad n={n} /></span>
                <ProvenanceTag source="git" label={hora(n.observado_en)} age={hace(n.observado_en, servido)} at={n.observado_en} />
              </div>
            )) : <Vacio>Ninguna.</Vacio>}
          </Panel>
        </div>
        <div className="hk-col" style={{ flex: "1 1 380px" }}>
          <Panel title="Equipo" meta={`${(vista.personas || []).length} personas`}>
            <Grafo respuesta={respuesta} yo={persona} eventos={eventos} w={400} h={280} paused={sinConexion}
              label="El equipo de un vistazo" />
          </Panel>
          <Anotar anotar={anotar} />
        </div>
      </div>
    </div>
  );
}
