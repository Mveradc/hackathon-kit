import { CollisionAlert, ProvenanceTag, StatusPulse, TaskCard } from "../componentes/componentes.jsx";
import { TeamGraph } from "../componentes/TeamGraph.jsx";
import { arroba, canal, DESAJUSTE, ETIQUETAS, hace, hora } from "../formato.js";

// Piezas que comparten las cuatro vistas. Cada una pinta campos de la vista tal cual (ADR-0009).

export function Tarea({ t, servido, action }) {
  const declarado = !!t.estado_declarado;
  const notas = [];
  if (t.declarado) notas.push(`⚑ ${ETIQUETAS[t.declarado] || t.declarado} a mano`);
  for (const d of t.cumplidas_por_cierre || []) notas.push(`⚑ ${d} cerrada a mano`);
  if (t.espera?.length) {
    notas.push("espera a " + t.espera
      .map((e) => `${e.id} (${e.dueno ? `@${e.dueno}, ` : ""}${ETIQUETAS[e.estado] || e.estado})`).join(", "));
  }
  if (t.bloquea_a?.length) notas.push(`bloquea a ${t.bloquea_a.join(", ")}`);
  if (t.issue) notas.push(`issue #${t.issue}`);
  return (
    <TaskCard data-tarea={t.id} id={t.id} title={`«${t.titulo}»`} owner={t.dueno} state={t.estado}
      stateLabel={t.etiqueta} source={declarado ? "declarado" : canal(t.fuente)}
      sourceLabel={declarado ? `declarado (${t.fuente})` : t.fuente} age={hace(t.observado_en, servido)}
      at={t.observado_en} action={action}>
      {notas.length ? notas.map((n) => <span key={n}>{n}</span>) : null}
    </TaskCard>
  );
}

export function Colision({ c, servido, actions }) {
  return (
    <CollisionAlert data-colision={c.id} severity={c.gravedad} level={c.nivel} path={c.rutas.join(", ")}
      contract={c.contrato} people={c.personas} age={hace(c.observado_en, servido)} actions={actions} />
  );
}

export function Desajuste({ d, servido }) {
  const [pulso, palabra] = DESAJUSTE[d.tipo] || ["wait", d.tipo];
  return (
    <div className="hk-bloque" data-desajuste={d.tipo}>
      <StatusPulse state={pulso} label={palabra} />
      <span className="hk-texto-sec hk-dato">{d.detalle}</span>
      {d.rutas?.length ? <span className="hk-mono hk-dato">{d.rutas.join(", ")}</span> : null}
      {d.personas?.length ? <span className="hk-texto-sec">{d.personas.map(arroba).join(", ")}</span> : null}
      <ProvenanceTag source={canal(d.fuente)} label={d.fuente} age={hace(d.observado_en, servido)} at={d.observado_en} />
    </div>
  );
}

export function Vacio({ children }) {
  return <span className="hk-vacio">{children}</span>;
}

/** Las fuentes de la vista con su antigüedad y su «viejo» (que calcula proyeccion.py, no la web). */
export function Fuentes({ respuesta }) {
  const { vista, servido_en: servido, relay } = respuesta;
  const f = vista.fuentes || {};
  return (
    <>
      {["relay", "github", "git"].filter((k) => f[k]).map((k) => {
        const d = f[k];
        const texto = k === "github" && d.valor === "no" ? "sin GitHub" : d.valor === "ok" ? k : `${k} ${d.valor}`;
        return <ProvenanceTag key={k} data-fuente={k} source={k} label={texto} age={hace(d.observado_en, servido)}
          at={d.observado_en} stale={d.viejo} />;
      })}
      {relay && relay.conectado === false ? (
        <StatusPulse state="stale" label={`Tu demonio no oye al relay desde ${hora(relay.desde)}`} />
      ) : null}
    </>
  );
}

function iniciales(p) {
  const base = (p.nombre || p.persona || "?").replace(/[^\p{L}\p{N}]/gu, "");
  return (base.slice(0, 2) || "?").toUpperCase();
}

/** El equipo como red: relay en el centro, GitHub aparte, personas alrededor y sus agentes activos (vista.personas).
 *  Cada nodo pinta solo campos de la vista: una persona es «viejo» si lo dice `p.viejo` y nada más (ADR-0009). Sin
 *  GitHub (`fuentes.github.valor === "no"`, M8h) no es un dato viejo: el nodo sale apagado y sin arista. */
export function construirGrafo(respuesta, yo, w, h) {
  const v = respuesta.vista;
  const relayCaido = respuesta.relay?.conectado === false;
  const fr = v.fuentes?.relay, fg = v.fuentes?.github;
  const sinGithub = fg?.valor === "no";
  const nodes = [
    { id: "relay", kind: "relay", x: w / 2, y: h / 2, glyph: "RLY", label: "relay", state: relayCaido || fr?.viejo ? "stale" : undefined },
    { id: "gh", kind: "github", x: w - 44, y: 40, glyph: "GH", label: sinGithub ? "sin GitHub" : "GitHub",
      state: sinGithub ? "off" : fg?.viejo ? "stale" : undefined },
  ];
  const edges = sinGithub ? [] : [{ id: "e-gh", from: "relay", to: "gh", channel: "github", stale: relayCaido || !!fg?.viejo }];
  const ps = v.personas || [];
  const rx = w / 2 - 70, ry = h / 2 - 56;
  ps.forEach((p, i) => {
    const a = Math.PI * (0.85 + (2 * i) / Math.max(ps.length, 1));
    const x = w / 2 + rx * Math.cos(a), y = h / 2 + ry * Math.sin(a);
    const id = `p-${p.persona}`;
    const vieja = !!p.viejo;
    nodes.push({ id, kind: "person", x, y, glyph: iniciales(p), label: p.persona === yo ? "tú" : `@${p.persona}`,
      state: vieja ? "stale" : undefined });
    edges.push({ id: `e-${p.persona}`, from: id, to: "relay", channel: "relay", stale: vieja || relayCaido || !!fr?.viejo });
    const orq = Math.min(p.papeles?.orquestador || 0, 1), workers = Math.min(p.papeles?.worker || 0, 4);
    const fuera = (k, d) => ({ x: x + Math.cos(a + k) * d, y: y + Math.sin(a + k) * d });
    let ancla = id;
    if (orq) {
      const o = fuera(0, 52);
      nodes.push({ id: `${id}-o`, kind: "orchestrator", ...o, glyph: "O", state: vieja ? "stale" : undefined });
      edges.push({ id: `l-${p.persona}-o`, from: id, to: `${id}-o`, channel: "local", stale: vieja });
      ancla = `${id}-o`;
    }
    for (let k = 0; k < workers; k++) {
      const pos = fuera((k - (workers - 1) / 2) * 0.5, orq ? 92 : 56);
      nodes.push({ id: `${id}-w${k}`, kind: "worker", ...pos, glyph: `w${k + 1}`, state: vieja ? "stale" : undefined });
      edges.push({ id: `l-${p.persona}-w${k}`, from: ancla, to: `${id}-w${k}`, channel: "local", stale: vieja });
    }
  });
  return { nodes, edges };
}

/** Cada evento real del SSE (api.md §3: {id, tipo, persona, papel, ts}) → un paquete por la arista de su persona. */
export function eventosDelGrafo(eventos) {
  const salida = [];
  for (const e of eventos) {
    if (e.tipo === "github.sondeo") salida.push({ id: e.id, edge: "e-gh", reverse: true });
    else if (e.persona) salida.push({ id: e.id, edge: `e-${e.persona}` });
  }
  return salida;
}

export function Grafo({ respuesta, yo, eventos, w, h, paused, label }) {
  const { nodes, edges } = construirGrafo(respuesta, yo, w, h);
  return <TeamGraph nodes={nodes} edges={edges} events={eventosDelGrafo(eventos)} width={w} height={h}
    paused={paused} label={label} />;
}

export function Leyenda() {
  return (
    <div className="hk-leyenda">
      <span><i style={{ background: "var(--relay)" }} />relay · tiempo real</span>
      <span><i style={{ background: "var(--github)" }} />GitHub · duradero</span>
      <span><i style={{ background: "var(--git)" }} />local · persona y sus agentes</span>
      <span><i style={{ height: 0, borderTop: "2px dashed var(--state-stale)" }} />sin datos recientes</span>
    </div>
  );
}
