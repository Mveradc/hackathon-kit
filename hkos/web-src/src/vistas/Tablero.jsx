import { Panel, ProvenanceTag, StatusPulse } from "../componentes/componentes.jsx";
import { hace, hora, tarjetas } from "../formato.js";
import { BotonReclamar, AvisoReclamo } from "./Cabina.jsx";
import { Colision, Tarea, Vacio } from "./comun.jsx";

// Tablero por persona (pantallas/tablero.dc.html): una columna por persona más «Sin dueño», agrupando las tarjetas de
// la vista por su campo `dueno`; la banda de colisiones y la actividad (novedades y lo que va sin tarea).

function Columna({ titulo, glifo, p, tareas, servido, reclamo, persona }) {
  const st = p?.viejo ? "stale" : p?.activos ? "live" : "idle";
  let estado = "Sin sesión";
  if (!p) estado = titulo === "Sin dueño" ? `${tareas.length} sin dueño` : "fuera del equipo";
  else if (p.activos) estado = `${p.activos} ${p.activos === 1 ? "activo" : "activos"}`;
  else if (p.ultima_senal) estado = `Sin señal desde ${hora(p.ultima_senal)}`;
  const agentes = p ? Object.entries(p.papeles || {}).map(([k, n]) => `${n} ${k}`).join(" · ") || "sin agentes" : "";
  return (
    <section className="hk-columna" aria-label={titulo} data-columna={p ? p.persona : titulo}>
      <header className="hk-columna__cab">
        <span className={`hk-avatar${st === "stale" ? " is-stale" : ""}`} aria-hidden="true">{glifo}</span>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
          <span style={{ fontWeight: 600 }}>{titulo}</span>
          <StatusPulse state={st} label={estado} />
        </div>
      </header>
      {agentes ? <span className="hk-meta">{agentes}</span> : null}
      {tareas.map((t) => (
        <Tarea key={t.id} t={t} servido={servido}
          action={(t.estado === "lista" || t.estado === "pendiente") && (!t.dueno || t.dueno === persona)
            ? <BotonReclamar t={t} reclamo={reclamo} /> : null} />
      ))}
      {!tareas.length ? <Vacio>Sin tareas.</Vacio> : null}
    </section>
  );
}

export function Tablero({ respuesta, reclamo }) {
  const { vista, persona, servido_en: servido } = respuesta;
  const todas = tarjetas(vista);
  const personas = vista.personas || [];
  const conocidas = new Set(personas.map((p) => p.persona));
  const otros = [...new Set(todas.map((t) => t.dueno).filter((d) => d && !conocidas.has(d)))];
  const de = (d) => todas.filter((t) => (t.dueno || "") === d);
  const colisiones = vista.colisiones || [];
  const actividad = [
    ...(vista.novedades || []).map((n) => ({ texto: `${n.tipo === "decision" ? "decisión" : n.tipo} · «${n.resumen}»${n.autor ? ` (${n.autor})` : ""}`, fuente: "git", obs: n.observado_en })),
    ...(vista.sin_tarea || []).map((x) => ({ texto: `@${x.persona} sin tarea: «${x.que}»`, fuente: "relay", label: "sin tarea", obs: x.observado_en })),
    ...(vista.reservas || []).map((r) => ({ texto: `@${r.persona} reserva ${r.rutas.map((x) => `«${x}»`).join(", ")} hasta ${hora(r.hasta)} · ${r.modo}`, fuente: "relay", label: "reserva", obs: null })),
  ];

  return (
    <div className="hk-col" data-vista="tablero" style={{ gap: 20 }}>
      <h1 className="hk-titulo">Tablero por persona</h1>
      {colisiones.length ? (
        <div className="hk-rejilla">
          {colisiones.map((c) => <Colision key={c.id} c={c} servido={servido} />)}
        </div>
      ) : null}
      <AvisoReclamo reclamo={reclamo} />
      <div className="hk-fila" style={{ gap: 20 }}>
        <div className="hk-columnas">
          {personas.map((p) => (
            <Columna key={p.persona} titulo={p.persona === persona ? `@${p.persona} (tú)` : `@${p.persona}`}
              glifo={(p.nombre || p.persona).slice(0, 2).toUpperCase()} p={p} tareas={de(p.persona)}
              servido={servido} reclamo={reclamo} persona={persona} />
          ))}
          {otros.map((d) => (
            <Columna key={d} titulo={d} glifo={d.slice(0, 2).toUpperCase()} tareas={de(d)}
              servido={servido} reclamo={reclamo} persona={persona} />
          ))}
          <Columna titulo="Sin dueño" glifo="—" tareas={de("")} servido={servido} reclamo={reclamo}
            persona={persona} />
        </div>
        <aside style={{ flex: "1 1 300px", minWidth: 0 }}>
          <Panel title="Actividad" meta={String(actividad.length)}>
            {actividad.length ? actividad.map((a, i) => (
              <div key={i} className="hk-bloque">
                <span className="hk-texto-sec hk-dato">{a.texto}</span>
                {a.obs ? <ProvenanceTag source={a.fuente} label={a.label} age={hace(a.obs, servido)} at={a.obs} /> : null}
              </div>
            )) : <Vacio>Sin actividad que contar.</Vacio>}
          </Panel>
        </aside>
      </div>
    </div>
  );
}
