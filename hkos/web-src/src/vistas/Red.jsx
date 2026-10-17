import { Panel, StatusPulse } from "../componentes/componentes.jsx";
import { tarjetas } from "../formato.js";
import { Colision, Desajuste, Grafo, Leyenda, Tarea, Vacio } from "./comun.jsx";

// La red (pantallas/red.dc.html): el grafo del equipo como centro, las cifras y «Necesita acción» como unión de campos
// que ya trae la vista (ADR-0009). Los hitos y la cuenta atrás del diseño no están en la vista: no se pintan.

export function Red({ respuesta, eventos, sinConexion }) {
  const { vista, persona, servido_en: servido } = respuesta;
  const todas = tarjetas(vista);
  const c = vista.columnas || {};
  const hechas = (c.hecho || []).length;
  const pct = todas.length ? Math.round((100 * hechas) / todas.length) : 0;
  const papeles = {};
  for (const p of vista.personas || []) for (const [k, n] of Object.entries(p.papeles || {})) papeles[k] = (papeles[k] || 0) + n;
  const sesiones = Object.entries(papeles).filter(([k]) => k !== "worker" && k !== "revisor").reduce((a, [, n]) => a + n, 0);
  const atascadas = todas.filter((t) => t.estado === "parada" || t.estado === "no_cerrada");
  const desajustes = (vista.servicios?.desajustes || []);
  const propuestas = (vista.servicios?.propuestas || []).length;
  const colisiones = vista.colisiones || [];
  const rojas = colisiones.filter((x) => x.gravedad === "rojo");
  const accion = atascadas.length + desajustes.length + propuestas;

  return (
    <div className="hk-col" data-vista="red">
      <h1 className="hk-titulo">La red</h1>
      <div className="hk-cifras">
        <div className="hk-cifra">
          <span className="hk-label">Tareas hechas</span>
          <span className="hk-cifra__valor">{hechas}<span className="hk-cifra__de">/{todas.length}</span></span>
          <div className="hk-barra"><div style={{ width: `${pct}%` }} /></div>
        </div>
        <div className="hk-cifra">
          <span className="hk-label">En curso</span>
          <span className="hk-cifra__valor" style={{ color: "var(--relay)" }}>{(c.haciendo || []).length}</span>
          <span className="hk-texto-sec">{sesiones} {sesiones === 1 ? "sesión" : "sesiones"} · {papeles.worker || 0} workers</span>
        </div>
        <div className={`hk-cifra${accion ? " hk-cifra--wait" : ""}`}>
          <span className="hk-label">Necesitan acción</span>
          <span className="hk-cifra__valor" style={{ color: accion ? "var(--state-wait)" : undefined }}>{accion}</span>
          {accion ? <StatusPulse state="wait" label={`${atascadas.length} paradas o sin cerrar · ${desajustes.length} no cuadran · ${propuestas} propuestas`} /> : null}
        </div>
        <div className={`hk-cifra${rojas.length ? " hk-cifra--fail" : ""}`}>
          <span className="hk-label">Colisiones</span>
          <span className="hk-cifra__valor" style={{ color: rojas.length ? "var(--state-fail)" : colisiones.length ? "var(--state-wait)" : undefined }}>{colisiones.length}</span>
          {colisiones.length ? <StatusPulse state={rojas.length ? "fail" : "wait"} label={`${rojas.length} rojas · ${colisiones.length - rojas.length} amarillas`} /> : null}
        </div>
      </div>
      <div className="hk-fila">
        <div className="hk-col" style={{ flex: "999 1 640px" }}>
          <Panel title="Equipo en vivo" meta="eventos del relay">
            <Grafo respuesta={respuesta} yo={persona} eventos={eventos} w={860} h={400} paused={sinConexion}
              label="El equipo: relay, GitHub, personas y sus agentes" />
            <Leyenda />
          </Panel>
        </div>
        <div className="hk-col" style={{ flex: "1 1 400px" }}>
          <Panel title="Necesita acción" meta={String(colisiones.length + accion)}
            tone={rojas.length ? "fail" : colisiones.length + accion ? "wait" : undefined}>
            {colisiones.map((x) => <Colision key={x.id} c={x} servido={servido} />)}
            {atascadas.map((t) => <Tarea key={t.id} t={t} servido={servido} />)}
            {desajustes.map((d, i) => <Desajuste key={i} d={d} servido={servido} />)}
            {propuestas ? <span className="hk-texto-sec">{propuestas} {propuestas === 1 ? "propuesta" : "propuestas"} de servicios sin confirmar (vista Servicios).</span> : null}
            {!colisiones.length && !accion ? <Vacio>Nada.</Vacio> : null}
          </Panel>
        </div>
      </div>
      <Panel title="En curso" meta={`${(c.haciendo || []).length} tareas`}>
        <div className="hk-rejilla">
          {(c.haciendo || []).map((t) => <Tarea key={t.id} t={t} servido={servido} />)}
        </div>
        {!(c.haciendo || []).length ? <Vacio>Nadie tiene nada en curso.</Vacio> : null}
      </Panel>
    </div>
  );
}
