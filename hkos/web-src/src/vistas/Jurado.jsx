import { CriterioEvidencia, CriterioPrueba, CriterioRow, CriterioTarea, Panel, ProvenanceTag, StatusPulse } from "../componentes/componentes.jsx";
import { canal, ETIQUETAS, fechaHm, hace, hm, textoZona, zonaJurado } from "../formato.js";
import { horaDeLinea, LineaDelMd, Vacio } from "./comun.jsx";

// Jurado (pantallas/jurado.dc.html; R-35, ADR-0012, api.md §11.3): cada nota de criterios.md y lo que la cubre. Todo
// sale del bloque `jurado` de la vista: la cobertura, el orden, la cuenta y el resumen los calcula proyeccion.py
// (hkos/jurado.py). La web agrupa por la cobertura que trae cada nota (sin cubrir, cubiertas, corregidas), formatea
// las horas en la zona de equipo.md y «hace X»; no cuenta, no ordena y no decide nada. Lo declarado (la nota, la
// etiqueta del plan, el pitch, «corrige a») va en violeta con su fuente y sin autor que el contrato no tenga.

const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

function Declarado({ donde, d, servido, children }) {
  return <ProvenanceTag source="declarado" label={children ?? `declarado · ${donde}`} age={hace(d.observado_en, servido)} at={d.observado_en} />;
}

function Tarea({ f, servido }) {
  const { tarjeta: t, enlace: e } = f;
  const declarado = !!t.estado_declarado;
  const notas = [];
  if (t.declarado) notas.push(`⚑ ${ETIQUETAS[t.declarado] || t.declarado} a mano`);
  return (
    <CriterioTarea data-tarea={t.id} id={t.id} title={`«${t.titulo}»`} owner={t.dueno} state={t.estado}
      stateLabel={t.etiqueta} source={declarado ? "declarado" : canal(t.fuente)}
      sourceLabel={declarado ? `declarado (${t.fuente})` : t.fuente} age={hace(t.observado_en, servido)}
      at={t.observado_en} stale={!!t.viejo} notes={notas}
      link={<>
        <span className="hk-crit__tag">(criterios: <span data-cita="">{e.cita}</span>)</span>
        <span>{e.ambiguo ? "ambigua, " : ""}en <span data-donde="">{e.donde}</span></span>
        <Declarado donde={e.donde} d={e} servido={servido} />
      </>} />
  );
}

function Evidencia({ e, servido }) {
  const comun = { "data-evidencia": e.tipo, "data-tarea": e.tarea, task: e.tarea, label: e.fuente,
    age: hace(e.observado_en, servido), at: e.observado_en, stale: !!e.viejo };
  return e.tipo === "prueba"
    ? <CriterioPrueba {...comun} conexion={e.conexion} result={e.valor} source={canal(e.fuente)} />
    : <CriterioEvidencia {...comun} tipo={e.tipo} sha={e.valor} />;
}

function Nota({ x, porClave, zona, servido }) {
  const n = x.nota;
  const cuando = n.hora ? fechaHm(n.hora, zona) : `${n.cita} (sin zona)`;
  const corregida = x.corregida_por;
  const otra = corregida ? porClave[corregida.valor] : null;
  const cobertura = corregida ? "corregida" : x.cobertura.valor;
  return (
    <CriterioRow data-nota={n.clave} data-cobertura={x.cobertura.valor} data-corregida={corregida ? "si" : undefined}
      time={<time dateTime={n.hora || undefined} data-hora-nota="">{cuando}</time>}
      who={<>{n.quien != null ? <>«<span data-quien="">{n.quien}</span>»</> : <span data-quien="">sin nombre</span>} (<span data-papel="">{n.papel}</span>)</>}
      where={n.donde ? <>«<span data-donde-nota="">{n.donde}</span>»</> : null}
      strength={n.fuerza.texto} strengthKind={n.fuerza.tipo}
      said={<>{n.literal ? null : "(paráfrasis) "}«<span data-dijo="">{n.dijo}</span>»</>}
      affects={n.afecta_a ? <>«<span data-afecta="">{n.afecta_a}</span>»</> : null}
      corrects={n.corrige} by={n.anotado_por} age={hace(n.observado_en, servido)} at={n.observado_en}
      coverage={cobertura} coverageStale={!!x.cobertura.viejo}
      coverageLabel={corregida ? `Corregida por la de ${otra ? (otra.nota.hora ? fechaHm(otra.nota.hora, zona) : otra.nota.cita) : "otra nota"}` : undefined}
      coverageTag={corregida
        ? <ProvenanceTag source="declarado" label="declarado · criterios.md" age={hace(corregida.observado_en, servido)} at={corregida.observado_en} data-corregida-por={corregida.valor} />
        : <ProvenanceTag source={canal(x.cobertura.fuente)} label={x.cobertura.fuente} age={hace(x.cobertura.observado_en, servido)}
          at={x.cobertura.observado_en} stale={!!x.cobertura.viejo} data-cobertura-fuente="" />}
      trabajoNuevo={x.trabajo_nuevo_desde ? <>trabajo nuevo desde <time dateTime={x.trabajo_nuevo_desde}>{hm(x.trabajo_nuevo_desde, zona)}</time></> : null}
      pitch={x.pitch ? <Declarado donde={x.pitch.donde} d={x.pitch} servido={servido} /> : null}
      hint={x.cobertura.valor === "sin_tarea" && !corregida
        ? `Para cubrirla, desde la terminal: /hack-plan y «(criterios: ${n.cita})» en la fila de la tarea en plan.md.` : null}>
      {x.tareas.map((f) => <Tarea key={f.tarjeta.id} f={f} servido={servido} />)}
      {x.evidencias.map((e, i) => <Evidencia key={i} e={e} servido={servido} />)}
    </CriterioRow>
  );
}

export function Jurado({ respuesta }) {
  const { vista, servido_en: servido } = respuesta;
  const j = vista.jurado;
  const zona = zonaJurado(vista);
  const c = j.cuenta;
  const porClave = Object.fromEntries(j.notas.map((x) => [x.nota.clave, x]));
  const sin = j.notas.filter((x) => !x.corregida_por && x.cobertura.valor !== "cubierta");
  const con = j.notas.filter((x) => !x.corregida_por && x.cobertura.valor === "cubierta");
  const corregidas = j.notas.filter((x) => x.corregida_por);
  const fila = (x) => <Nota key={x.nota.clave} x={x} porClave={porClave} zona={zona} servido={servido} />;

  return (
    <div className="hk-col" data-vista="jurado">
      <div>
        <h1 className="hk-titulo">Jurado</h1>
        <span className="hk-texto-sec">Cada nota de criterios.md y lo que la cubre. Las notas y sus enlaces a tareas (la
          etiqueta «(criterios: …)» en la fila de plan.md) los escribe el equipo; el estado de cada tarea y las
          evidencias en main, el OS. Calculado a las <span className="hk-mono" data-calculado="">{hm(j.observado_en, zona)}</span>,
          horas en {j.zona ? <span data-zona="">{j.zona.valor}</span> : "la zona de equipo.md"}{typeof zona === "number" ? ` (${textoZona(zona)})` : ""}.</span>
      </div>
      <div className="hk-acciones">
        <ProvenanceTag source={canal(j.fuente)} label={j.fuente} age={hace(horaDeLinea(vista, "jurado"), servido)}
          at={horaDeLinea(vista, "jurado")} stale={!!j.viejo} data-bloque="jurado" />
        {j.fichero ? <StatusPulse state={j.fichero === "ok" ? "ok" : "wait"} label={`criterios.md ${j.fichero}`} data-fichero="" /> : null}
        {j.zona ? <ProvenanceTag source="declarado" label="zona · equipo.md" age={hace(j.zona.observado_en, servido)} at={j.zona.observado_en} /> : null}
      </div>
      <div className="hk-cifras" data-cuenta="">
        <div className="hk-cifra">
          <span className="hk-label">Notas</span>
          <span className="hk-cifra__valor" data-cuenta-notas="">{c.notas}</span>
          <span className="hk-texto-sec" data-cuenta-corregidas="">{plural(c.corregidas, "corregida", "corregidas")}</span>
        </div>
        <div className={`hk-cifra${c.sin_cubrir ? " hk-cifra--wait" : ""}`}>
          <span className="hk-label">Sin cubrir</span>
          <span className="hk-cifra__valor" style={{ color: c.sin_cubrir ? "var(--state-wait)" : undefined }} data-cuenta-sin-cubrir="">{c.sin_cubrir}</span>
          <span className="hk-texto-sec" data-desglose="">{c.sin_tarea} sin tarea · {plural(c.ambiguas, "ambigua", "ambiguas")} · {plural(c.planificadas, "planificada", "planificadas")} · {c.en_curso} en curso · {c.en_pitch} en el pitch</span>
        </div>
        <div className="hk-cifra">
          <span className="hk-label">Sin cubrir, por fuerza</span>
          {c.sin_cubrir_por_fuerza.length ? c.sin_cubrir_por_fuerza.map((f) => (
            <span key={f.texto} className="hk-texto" data-por-fuerza={f.texto}><b className="hk-mono">{f.n}</b> {f.texto}</span>
          )) : <Vacio>Ninguna.</Vacio>}
          <span className="hk-texto-sec">de la más fuerte a la más floja</span>
        </div>
        <div className="hk-cifra">
          <span className="hk-label">Cubiertas</span>
          <span className="hk-cifra__valor" style={{ color: c.cubiertas ? "var(--state-ok)" : undefined }} data-cuenta-cubiertas="">{c.cubiertas}</span>
          <span className="hk-texto-sec">todas sus tareas publicadas, con el último commit de cada una</span>
        </div>
      </div>
      <div className="hk-fila">
        <div className="hk-col" style={{ flex: "999 1 860px" }}>
          <Panel title="Sin cubrir" meta={c.sin_cubrir ? `${c.sin_cubrir} · por fuerza y luego por hora` : "0"} tone={c.sin_cubrir ? "wait" : undefined}>
            {sin.length ? sin.map(fila) : <Vacio>Ninguna: todas las notas de criterios.md están cubiertas.</Vacio>}
          </Panel>
          <Panel title="Cubiertas" meta={c.cubiertas ? `${c.cubiertas} · por hora` : "0"}>
            {con.length ? con.map(fila) : <Vacio>Aún ninguna.</Vacio>}
          </Panel>
          {corregidas.length ? <Panel title="Corregidas" meta={String(c.corregidas)}>{corregidas.map(fila)}</Panel> : null}
          {j.sin_nota.length ? (
            <Panel title="Enlaces rotos" meta={String(j.sin_nota.length)} tone="wait">
              {j.sin_nota.map((s) => (
                <div key={`${s.tarea}-${s.cita}`} className="hk-bloque" data-sin-nota={s.tarea}>
                  <span className="hk-texto"><b className="hk-mono">{s.tarea}</b> cita <span className="hk-crit__tag">(criterios: <span data-cita="">{s.cita}</span>)</span>, que no casa con ninguna nota de criterios.md.</span>
                  <Declarado donde="plan.md" d={s} servido={servido} />
                </div>
              ))}
            </Panel>
          ) : null}
          <Panel title="Lo que ve el agente" meta="estado-equipo.md">
            <LineaDelMd vista={vista} clave="jurado" />
            <span className="hk-texto-sec">La línea de «## Jurado y ruta». El detalle de arriba sale del mismo bloque y es el que da el MCP (jurado).</span>
          </Panel>
        </div>
        <aside className="hk-col" style={{ flex: "1 1 320px" }}>
          <Panel title="Cómo se lee">
            <span className="hk-texto-sec">«Sin cubrir» es todo lo que no está cubierto ni corregido. Va primero, por fuerza (dato, «obligatorio», «se valora», «nos gustaría ver», otra palabra, comentario suelto, sin precisar) y luego por hora. El orden llega hecho.</span>
            <span className="hk-texto-sec"><b className="hk-espera">Sin tarea</b>: ninguna tarea de plan.md ni pitch.md la cita. <b className="hk-espera">Ambigua</b>: la etiqueta casa con varias notas del mismo minuto. <b>Planificada</b>: la citan tareas, pero ninguna ha empezado. <b style={{ color: "var(--relay)" }}>En curso</b>: alguna ha empezado. <b>En el pitch</b>: solo la cita pitch.md (declarado). <b className="hk-ok">Cubierta</b>: todas las tareas que la citan están publicadas (o cerradas sin ⚑).</span>
            <span className="hk-texto-sec"><ProvenanceTag source="declarado" label="declarado" /> la nota, la etiqueta «(criterios: …)» de plan.md y la cita en pitch.md: lo escribió el equipo, con la hora del commit de cada fichero.</span>
            <span className="hk-texto-sec">La evidencia es el último commit que publicó cada tarea, y el último resultado de su Prueba si tiene una. La Prueba se enseña, pero no cambia la cobertura.</span>
          </Panel>
          <Panel title="Desde la terminal" meta="no se hace aquí">
            <span className="hk-texto-sec">Anotar lo que dice el jurado: <span className="hk-mono">/hack-note</span> o Anotar en la Cabina.</span>
            <span className="hk-texto-sec">Enlazar una tarea a una nota: <span className="hk-mono">/hack-plan</span>, con la etiqueta <span className="hk-mono">(criterios: &lt;fecha hora de la nota&gt;)</span> en la fila de la tarea.</span>
            <span className="hk-texto-sec">Recogerla en el pitch: <span className="hk-mono">/hack-pitch</span>, con la misma etiqueta. Corregir una nota: una nota nueva que diga a cuál corrige.</span>
          </Panel>
        </aside>
      </div>
    </div>
  );
}
