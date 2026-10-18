import { Panel, ProvenanceTag, StatusPulse } from "../componentes/componentes.jsx";
import { arroba, autorPropuesta, canal, hace, nombrePropuesta } from "../formato.js";
import { Desajuste, Vacio } from "./comun.jsx";

// Servicios (pantallas/servicios.dc.html): los de servicios.md con lo que el OS comprueba, sus conexiones y contratos,
// lo propuesto sin confirmar y lo que no cuadra; todo el equipo (api.md §6: el md lleva el subconjunto de cada
// persona). Confirmar y rechazar no están en la web (M9a): se dicen como texto.

function Confirmacion({ c, servido }) {
  const ok = c.valor === "confirmada";
  const texto = ok
    ? `confirmada${c.de_scaffold ? " · de /hack-scaffold" : ""}${c.por.length ? ` · por ${c.por.map(arroba).join(", ")}` : ""}`
    : `sin confirmar · cambio de ${c.por.map(arroba).join(", ") || "nadie del equipo conocido"}${c.faltan.length ? ` · faltan ${c.faltan.map(arroba).join(", ")}` : ""}`;
  return (
    <ProvenanceTag source={ok ? canal(c.fuente) : "declarado"} label={texto} age={hace(c.observado_en, servido)}
      at={c.observado_en} />
  );
}

function Comprobado({ x, servido }) {
  const c = x.comprobado;
  if (!c) return <span className="hk-texto-sec">{x.puerto ? "sin comprobar" : "sin puerto"}</span>;
  const { escucha, salud } = c.valor || {};
  const texto = escucha ? `responde${salud != null ? ` · salud ${salud}` : ""}` : "no responde";
  return (
    <span className={c.viejo ? "hk-viejo" : escucha ? "hk-ok" : "hk-espera"} data-comprobado="">
      ● {texto}{" "}
      <ProvenanceTag source={canal(c.fuente)} label={c.fuente} age={hace(c.observado_en, servido)} at={c.observado_en}
        stale={!!c.viejo} />
    </span>
  );
}

export function Servicios({ respuesta }) {
  const { vista, servido_en: servido } = respuesta;
  const s = vista.servicios;
  if (!s) {
    return (
      <div className="hk-col" data-vista="servicios">
        <h1 className="hk-titulo">Servicios</h1>
        <Panel title="Sin servicios">
          <span className="hk-texto-sec">La vista no trae servicios: no hay .hackathon/servicios.md en main, o el relay
            tiene web_nueva apagado.</span>
        </Panel>
      </div>
    );
  }
  const porClave = {};
  for (const d of s.desajustes) if (d.clave) (porClave[d.clave] ||= []).push(d);
  // Un desajuste `viejo` (de la vista) no pinta la caja de fallo ni de espera: se ve gris en «No cuadra».
  const tono = (clave, confirmacion) => {
    const todos = porClave[clave] || [], ds = todos.filter((d) => !d.viejo);
    if (ds.some((d) => d.tipo.endsWith("falla") || d.tipo === "formato_invalido" || d.tipo === "contrato_inexistente")) return "fail";
    if (ds.length) return "wait";
    if (todos.length) return "stale";
    return confirmacion.valor === "sin_confirmar" ? "declarado" : "";
  };

  return (
    <div className="hk-col" data-vista="servicios">
      <div>
        <h1 className="hk-titulo">Servicios</h1>
        <span className="hk-texto-sec">Lo que hay en marcha y cómo se habla entre sí. El mapa sale de servicios.md; el
          estado de cada caja, de lo que el OS comprueba.</span>
      </div>
      <div className="hk-acciones">
        <StatusPulse state={s.fichero.valor === "ok" ? "ok" : "fail"} label={`servicios.md ${s.fichero.valor}`} />
        <ProvenanceTag source={canal(s.fichero.fuente)} label={s.fichero.fuente} age={hace(s.fichero.observado_en, servido)}
          at={s.fichero.observado_en} />
      </div>
      <div className="hk-fila">
        <div className="hk-col" style={{ flex: "999 1 640px" }}>
          <Panel title="Servicios" meta={String(s.lista.length)}>
            <div className="hk-servicios">
              {s.lista.map((x) => {
                const t = tono(x.clave, x.confirmacion);
                return (
                  <article key={x.clave} className={`hk-servicio${t ? ` hk-servicio--${t}` : ""}`} data-servicio={x.nombre}>
                    <span><span className="hk-servicio__nombre">{x.nombre}</span>{" "}
                      <span className="hk-meta">{x.puerto ? `:${x.puerto}` : "sin puerto"}</span></span>
                    <dl className="hk-ficha">
                      <dt>Dueño</dt>
                      <dd>{x.dueno ? x.dueno : `${arroba(x.dueno_autoridad)} (autoridad.md)`}</dd>
                      <dt>Carpeta</dt><dd className="hk-mono">{x.carpeta}</dd>
                      {x.arranque ? <><dt>Arranque</dt><dd className="hk-mono">{x.arranque}</dd></> : null}
                      {x.salud ? <><dt>Salud</dt><dd className="hk-mono">GET {x.salud}</dd></> : null}
                    </dl>
                    <Comprobado x={x} servido={servido} />
                    <Confirmacion c={x.confirmacion} servido={servido} />
                  </article>
                );
              })}
            </div>
          </Panel>
          <Panel title="Conexiones" meta={String(s.conexiones.length)}>
            {s.conexiones.length ? s.conexiones.map((x) => {
              const t = tono(x.clave, x.confirmacion);
              return (
                <div key={x.clave} className={`hk-caja${t ? ` hk-caja--${t}` : ""}`} data-conexion={`${x.de} → ${x.a}`}>
                  <span className="hk-texto"><b className="hk-mono">{x.de} → {x.a}</b>
                    {x.contrato ? <> · contrato «{x.contrato}»</> : " · sin contrato"}</span>
                  {x.prueba ? <span className="hk-mono hk-dato">{x.prueba}</span> : <span className="hk-texto-sec">sin Prueba</span>}
                  {x.resultado ? (
                    <span className={x.resultado.viejo ? "hk-viejo" : x.resultado.valor === "pasa" ? "hk-ok" : "hk-fallo"}
                      data-resultado="">
                      ● la prueba {x.resultado.valor}{" "}
                      <ProvenanceTag source={canal(x.resultado.fuente)} label={x.resultado.fuente}
                        age={hace(x.resultado.observado_en, servido)} at={x.resultado.observado_en}
                        stale={!!x.resultado.viejo} />
                    </span>
                  ) : <span className="hk-texto-sec">nadie ha corrido la prueba</span>}
                  {x.duenos?.length ? <span className="hk-texto-sec">dueños: {x.duenos.map(arroba).join(", ")}</span> : null}
                  <Confirmacion c={x.confirmacion} servido={servido} />
                </div>
              );
            }) : <Vacio>Sin conexiones.</Vacio>}
          </Panel>
        </div>
        <div className="hk-col" style={{ flex: "1 1 340px" }}>
          <Panel title="Cambio propuesto" meta={String(s.propuestas.length)} tone={s.propuestas.length ? "wait" : undefined}>
            {s.propuestas.length ? s.propuestas.map((p) => (
              <div key={p.clave} className="hk-bloque" data-propuesta={p.clave}>
                <span className="hk-texto">propuesta de {nombrePropuesta(p)} · de {autorPropuesta(p)}</span>
                {p.duenos?.length ? <span className="hk-texto-sec">la confirman {p.duenos.map(arroba).join(", ")}, pasándola a su tabla de servicios.md</span> : null}
                <ProvenanceTag source="declarado" label={`declarado por ${p.autor_declarado || "—"}${p.hora_declarada ? ` · ${p.hora_declarada}` : ""}`}
                  age={hace(p.observado_en, servido)} at={p.observado_en} />
              </div>
            )) : <Vacio>Nada propuesto.</Vacio>}
          </Panel>
          <Panel title="No cuadra" meta={String(s.desajustes.length)}>
            {s.desajustes.length ? s.desajustes.map((d, i) => <Desajuste key={i} d={d} servido={servido} />) : <Vacio>Todo cuadra.</Vacio>}
          </Panel>
          <Panel title="Fuera de servicios" meta={String(s.fuera.length)}>
            <span className="hk-mono hk-dato">{s.fuera.join(", ")}</span>
          </Panel>
        </div>
      </div>
    </div>
  );
}
