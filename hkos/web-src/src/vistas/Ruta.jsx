import { Cadena, Panel, ProvenanceTag, StatusPulse, TaskCard } from "../componentes/componentes.jsx";
import { arroba, canal, diaHm, duracion, fechaHm, hace, hm, minutosZona, ms, tarjetas, textoZona, zonaRuta } from "../formato.js";
import { Vacio } from "./comun.jsx";

// Ruta crítica (pantallas/ruta-critica.dc.html; R-36, ADR-0013, api.md §11.4). Todo sale del bloque `ruta` de la
// vista, que calcula proyeccion.py (hkos/ruta.py): el veredicto, el rango, el margen, la base, los hechos, la cadena y
// los riesgos. La web solo los escribe (las horas en la zona de equipo.md, «hace X») y coloca en la línea de tiempo las
// horas que trae la vista. Sin hora central, sin previsión por hito y sin «fiabilidad» (issue #46). Colores: el rojo,
// solo para un plazo que ya pasó (un hecho); «no llega» y «justo», ámbar (una previsión); sin estimación, gris; lo
// estimado, discontinuo y con la palabra «estimación»; lo declarado (plan.md, equipo.md), en violeta con su fuente.

const VEREDICTO = {
  a_tiempo: ["ok", "A tiempo", "ok"], justo: ["wait", "Justo", "wait"], no_llega: ["wait", "No llega", "wait"],
  sin_estimacion: ["idle", "Sin estimación", "idle"],
};
// sin_plazo y sin_usuario (K-108) son motivos solo si no queda ninguna tarea abierta estimable: cada uno, con sus tareas.
const MOTIVO_SIN = { sin_entrega: "sin hora de entrega", ciclo: "ciclo en las dependencias", sin_plazo: "sin plazo",
  sin_usuario: "de personas sin usuario de GitHub (no se miden)", pocos_datos: "pocos datos: hacen falta 3 tareas medidas por persona" };
const MOTIVO = {
  vacio: "«Hasta» vacío", relativo_sin_inicio: "H+N sin Inicio en equipo.md", sin_inicio: "sin Inicio en equipo.md",
  sin_zona: "sin zona en equipo.md", por_confirmar: "por confirmar", formato: "un formato que no se entiende",
  sin_plazo: "sin plazo", orden: "su «Hasta» no va después del anterior", sin_dato: "falta la línea", dos_horas: "dos horas",
};
const FUERA = { condicional: "empieza por «Si …»", si_da_tiempo: "lleva [SI DA TIEMPO]" };
const POR = { inicio: "la primera de la cadena", depende_de: "depende de la anterior (plan.md)", orden_del_plan: "va detrás en el orden del plan (inferido)" };
const HECHO = {
  plazo_pasado: ["fail", "HECHO · PLAZO PASADO"], parada: ["wait", "HECHO · PARADA"], no_cerrada: ["wait", "HECHO · SIN CERRAR"],
  sin_senales: ["stale", "HECHO · SIN SEÑALES"], ciclo: ["stale", "HECHO · CICLO"],
};

function Hora({ iso, zona, dia = true }) {
  return iso ? <time dateTime={iso}>{dia ? diaHm(iso, zona) : hm(iso, zona)}</time> : null;
}

// K-108, punto 2, e issue #77, A3: si el fin temprano y el tarde se escriben con la misma HH:MM en la zona del equipo,
// no es un rango (ajuste 5, punto 2 de ADR-0013), como en el resumen de ruta.py. La web solo compara las dos horas que
// trae la vista, como las escribe, para elegir el texto (y un punto en vez de una barra); no calcula nada.
const igual = (temprano, tarde, zona) => hm(temprano, zona) === hm(tarde, zona);
// A11 (#77, decisión del usuario): el plazo pasado, con el día solo si no es el de ahora en la zona del equipo, como el
// resumen («plazo pasado vie 23:00»).
const mismoDia = (a, b, zona) => fechaHm(a, zona).split(" · ")[0] === fechaHm(b, zona).split(" · ")[0];

/** «entre X y Y» o, si X = Y, «hacia X (las medidas no varían)». */
function Fin({ temprano, tarde, zona, marcas = false }) {
  return igual(temprano, tarde, zona)
    ? <>hacia <span {...(marcas ? { "data-temprano": "", "data-tarde": "" } : {})}><Hora iso={temprano} zona={zona} /></span> <span data-sin-rango="">(las medidas no varían)</span></>
    : <>entre <span {...(marcas ? { "data-temprano": "" } : {})}><Hora iso={temprano} zona={zona} /></span> y <span {...(marcas ? { "data-tarde": "" } : {})}><Hora iso={tarde} zona={zona} /></span></>;
}

function Declarado({ donde, d, servido }) {
  return <ProvenanceTag source="declarado" label={`declarado · ${donde}`} age={hace(d.observado_en, servido)} at={d.observado_en} />;
}

function Derivado({ d, servido, stale }) {
  return <ProvenanceTag source={canal(d.fuente)} label={d.fuente} age={hace(d.observado_en, servido)} at={d.observado_en} stale={!!stale} />;
}

/** Una fecha declarada (la entrega, un hito): su hora resuelta y su texto tal cual, o el motivo de que no se resuelva. */
function HoraDeclarada({ d, zona }) {
  return d.valor
    ? <><Hora iso={d.valor} zona={zona} /> <span className="hk-texto-sec">(«<span data-texto="">{d.texto}</span>»)</span></>
    : <span>sin hora · <span data-texto="">{d.texto ?? "—"}</span>{d.motivo ? ` (${MOTIVO[d.motivo] || d.motivo})` : ""}</span>;
}

function Tarjeta({ t, servido }) {
  return (
    <TaskCard data-tarea={t.id} id={t.id} title={`«${t.titulo}»`} owner={t.dueno} state={t.estado} stateLabel={t.etiqueta}
      source={canal(t.fuente)} sourceLabel={t.fuente} age={hace(t.observado_en, servido)} at={t.observado_en} stale={!!t.viejo} />
  );
}

function Hecho({ h, tarjeta, zona, servido, ahora }) {
  const [tono, tipo] = HECHO[h.tipo] || ["stale", h.tipo];
  let texto;
  if (h.tipo === "plazo_pasado") {
    texto = <>Su plazo, <Hora iso={h.plazo} zona={zona} dia={!mismoDia(h.plazo, ahora, zona)} /> (plan.md), ya pasó y sigue abierta.{h.arrastra.length
      ? <> Arrastra a <span data-arrastra="">{h.arrastra.join(", ")}</span>.</> : null}</>;
  } else if (h.tipo === "sin_senales") {
    texto = <>{h.desde ? <>Sin señales de {arroba(h.persona)} desde <Hora iso={h.desde} zona={zona} dia={false} /></> : <>Ninguna señal de {arroba(h.persona)}</>}. No quiere decir que vaya lenta: puede estar trabajando sin commits con ID.</>;
  } else if (h.tipo === "ciclo") {
    texto = <>Ciclo en las dependencias: <span data-ciclo="">{h.ciclo.join(" → ")}</span>.</>;
  } else {
    texto = <>En la cadena: {h.tipo === "parada" ? "parada" : "sin cerrar"}.</>;
  }
  return (
    <div className="hk-riesgo" data-hecho={h.tipo} data-tarea={h.tarea} data-persona={h.persona}>
      {tarjeta ? <Tarjeta t={tarjeta} servido={servido} /> : null}
      <div className={`hk-riesgo__cuerpo hk-riesgo__cuerpo--${tono}`}>
        <span className="hk-riesgo__tipo">{tipo}</span>
        <span className="hk-texto">{h.tarea && !tarjeta ? <><b className="hk-mono">{h.tarea}</b> ({arroba(h.persona)}) · </> : null}{texto}</span>
        <Derivado d={h} servido={servido} stale={h.viejo} />
      </div>
    </div>
  );
}

function Riesgo({ r, tarjeta, objetivo, zona, servido }) {
  return (
    <div className="hk-riesgo" data-riesgo={r.tarea} data-tarea={r.tarea}>
      {tarjeta ? <Tarjeta t={tarjeta} servido={servido} /> : null}
      <div className="hk-riesgo__cuerpo hk-riesgo__cuerpo--wait">
        <span className="hk-riesgo__tipo">ESTIMACIÓN</span>
        <span className="hk-texto">{!tarjeta ? <><b className="hk-mono">{r.tarea}</b> · </> : null}Con el ritmo más lento medido de {arroba(r.dueno)}, acaba <span data-fin-tarde=""><Hora iso={r.fin_tarde} zona={zona} /></span> (fin tarde): después de la entrega ({objetivo?.valor ? <Hora iso={objetivo.valor} zona={zona} /> : "—"}).</span>
        <span className="hk-texto-sec" data-en-cadena={r.en_cadena ? "si" : "no"}>{r.en_cadena ? "En la cadena" : "Fuera de la cadena"}</span>
        {r.viejo ? <StatusPulse state="stale" label="con un dato viejo" /> : null}
      </div>
    </div>
  );
}

/** Marcas cada tantas horas en punto (en la zona de equipo.md) entre min y max: solo para leer la escala. */
function marcasDeHora(min, max, zona) {
  const H = 3600000, paso = [1, 2, 3, 4, 6, 12, 24].find((p) => (max - min) / (p * H) <= 8) || 24;
  const salida = [];
  const z = minutosZona(zona, min) * 60000;
  for (let t = Math.ceil((min + z) / H) * H - z; t <= max; t += H) {
    const h = new Date(t + minutosZona(zona, t) * 60000).getUTCHours();
    if (h % paso === 0) salida.push({ at: t, label: diaHm(new Date(t).toISOString(), zona) });
  }
  return salida;
}

function Linea({ r, zona, servido, pasados, riesgos }) {
  const horas = [ms(r.observado_en)];
  for (const e of r.cadena) {
    if (e.franja.valor) horas.push(ms(e.franja.valor.desde), ms(e.franja.valor.hasta));
    if (e.hasta.valor) horas.push(ms(e.hasta.valor));
    if (e.fin_tarde) horas.push(ms(e.fin_temprano), ms(e.fin_tarde));
  }
  if (r.objetivo?.valor) horas.push(ms(r.objetivo.valor));
  if (r.estimacion) horas.push(ms(r.estimacion.temprano), ms(r.estimacion.tarde));
  const min = Math.min(...horas), max = Math.max(...horas);
  const marcas = [{ at: ms(r.observado_en), kind: "ahora", label: "ahora" },
    ...r.hitos.filter((h) => h.hito.valor).map((h) => ({ at: ms(h.hito.valor), kind: "hito", label: `«${h.hito.nombre}» · declarado · ${h.hito.donde}` })),
    ...(r.objetivo?.valor ? [{ at: ms(r.objetivo.valor), kind: "entrega", label: "entrega" }] : [])];
  const filas = r.cadena.map((e) => fila(e, zona, servido, pasados, riesgos, r.veredicto.valor, true));
  const [, , tono] = VEREDICTO[r.veredicto.valor] || VEREDICTO.sin_estimacion;
  const est = r.estimacion;
  const uno = est && igual(est.temprano, est.tarde, zona);
  return (
    <Cadena layout="linea" min={min} max={max} ticks={marcasDeHora(min, max, zona)} marks={marcas} rows={filas}
      end={est ? { ...(uno ? { at: ms(est.temprano), sub: "una hora: las medidas no varían" } : { from: ms(est.temprano), to: ms(est.tarde) }),
        tone: tono, title: "Fin estimado (estimación)",
        label: <span data-fin=""><Fin temprano={est.temprano} tarde={est.tarde} zona={zona} /></span>,
        range: uno ? "el ritmo más rápido y el más lento medidos dan la misma hora" : "con el ritmo más rápido y con el más lento medidos; nunca una sola hora" } : undefined} />
  );
}

// Lo que dice cada fila sale de campos de la vista (ADR-0009, issue #63): «No llega» solo si el veredicto es no_llega
// (si no, el eslabón en `riesgos` es un «Riesgo»), y la barra `vieja` solo si la tarjeta trae `viejo` («sin señales»
// no es «viejo»).
function fila(e, zona, servido, pasados, riesgos, veredicto, linea) {
  const t = e.tarjeta;
  const pasado = pasados.has(t.id), riesgo = riesgos.has(t.id);
  const fr = e.franja.valor;
  const pulse = pasado ? ["fail", "Plazo pasado"] : riesgo ? ["wait", veredicto === "no_llega" ? "No llega (estimación)" : "Riesgo (estimación)"]
    : t.viejo ? ["stale", t.etiqueta] : t.estado === "en_curso" ? ["live", t.etiqueta] : ["idle", t.etiqueta];
  return {
    id: t.id, title: `«${t.titulo}»`,
    data: { "data-eslabon": t.id, "data-por": e.por },
    sub: <>{arroba(t.dueno)} · <span data-etiqueta="">{t.etiqueta}</span> · {POR[e.por] || e.por} <Derivado d={t} servido={servido} stale={t.viejo} /></>,
    franja: <span data-franja="">{fr
      ? <>franja <Hora iso={fr.desde} zona={zona} /> → <Hora iso={fr.hasta} zona={zona} /> · <span data-min="">{fr.min}</span> min{fr.compartida > 1 ? <> · compartida entre <span data-compartida="">{fr.compartida}</span></> : null}</>
      : <>sin franja ({MOTIVO[e.franja.motivo] || e.franja.motivo})</>}
      {" "}<span data-hasta="">«Hasta» {e.hasta.texto ?? "—"}{e.hasta.valor ? null : ` (${MOTIVO[e.hasta.motivo] || e.hasta.motivo})`}</span>
      {" "}<Declarado donde="plan.md" d={e.hasta} servido={servido} /></span>,
    pulse,
    note: e.fin_tarde ? <span data-fin-eslabon="">estimación: acaba <Fin temprano={e.fin_temprano} tarde={e.fin_tarde} zona={zona} /></span> : null,
    noteKind: riesgo ? "no_llega" : "normal",
    ...(linea ? {
      kind: pasado ? "plazo_pasado" : t.viejo ? "vieja" : "franja",
      from: fr ? ms(fr.desde) : undefined, to: fr ? ms(fr.hasta) : undefined,
      ...(e.fin_tarde ? (igual(e.fin_temprano, e.fin_tarde, zona) ? { estAt: ms(e.fin_temprano) } : { est: [ms(e.fin_temprano), ms(e.fin_tarde)] }) : {}), estKind: riesgo ? "no_llega" : "prevista",
      deadline: e.hasta.valor ? ms(e.hasta.valor) : undefined, deadlinePast: pasado,
    } : {}),
  };
}

export function Ruta({ respuesta }) {
  const { vista, servido_en: servido } = respuesta;
  const r = vista.ruta;
  const zona = zonaRuta(vista);
  const zonaDada = r.zona?.valor != null && (typeof zona === "string" || /^[+-]\d\d:\d\d$/.test(r.zona.valor));
  const [pulso, palabra, tono] = VEREDICTO[r.veredicto.valor] || VEREDICTO.sin_estimacion;
  const est = r.estimacion;
  const obj = r.objetivo;
  const sinUsuario = r.sin_usuario ?? [];        // K-108, punto 1; las vistas de antes no lo traen
  // Búsquedas por id en lo que ya trae la vista (ADR-0009: agrupar por un campo), no cálculos.
  const porTarea = new Map([...tarjetas(vista), ...r.cadena.map((e) => e.tarjeta)].map((t) => [t.id, t]));
  const pasados = new Set(r.hechos.filter((h) => h.tipo === "plazo_pasado").map((h) => h.tarea));
  const riesgos = new Set(r.riesgos.map((x) => x.tarea));
  const ciclo = r.hechos.find((h) => h.tipo === "ciclo");
  const textoMotivo = (m) => m === "ciclo" && ciclo ? `ciclo ${ciclo.ciclo.join(" → ")}`
    : m === "sin_plazo" ? `${MOTIVO_SIN[m]}: ${r.sin_plazo.map((x) => x.tarea).join(", ")}`
      : m === "sin_usuario" ? `${MOTIVO_SIN[m]}: ${sinUsuario.map((x) => x.tarea).join(", ")}` : MOTIVO_SIN[m] || m;

  return (
    <div className="hk-col" data-vista="ruta">
      <div>
        <h1 className="hk-titulo">Ruta crítica</h1>
        <span className="hk-texto-sec">Si la cadena de tareas abiertas más larga acaba antes de la entrega y con qué margen,
          siempre como un rango. Lo calcula el OS con las dependencias, el orden de cada persona y las franjas de plan.md
          y el ritmo real de cada persona; aquí solo se pinta. Calculado a las <span className="hk-mono" data-calculado="">{hm(r.observado_en, zona)}</span>,
          horas de equipo.md ({zonaDada ? <span data-zona="">{r.zona.valor}</span> : textoZona(zona)}).</span>
        {zonaDada ? <ProvenanceTag source="declarado" label="zona · equipo.md" age={hace(r.zona.observado_en, servido)} at={r.zona.observado_en} /> : null}
      </div>

      <section className={`hk-veredicto hk-veredicto--${r.veredicto.gravedad}`} aria-label="Veredicto" data-veredicto={r.veredicto.valor}>
        <div className="hk-veredicto__col">
          <span className="hk-label">¿Llega a la entrega?</span>
          {est ? <span className="hk-estimacion">estimación</span> : null}
          <StatusPulse state={pulso} label={palabra} data-veredicto-palabra="" />
          {est ? (
            <>
              <span className={`hk-veredicto__cifra hk-veredicto__cifra--${tono}`} data-margen="">
                de <span data-margen-min="">{duracion(est.margen_min)}</span> a <span data-margen-max="">{duracion(est.margen_max)}</span>
              </span>
              <span className="hk-texto-sec">de margen sobre la entrega ({obj?.valor ? <Hora iso={obj.valor} zona={zona} /> : "—"}) ·
                fin <Fin temprano={est.temprano} tarde={est.tarde} zona={zona} marcas /></span>
              <span className="hk-texto">Con el ritmo medido de cada persona, la cadena acaba {igual(est.temprano, est.tarde, zona) ? "a esa hora" : "en ese rango"}. Es una previsión, no un hecho.</span>
            </>
          ) : (
            <>
              <span className="hk-veredicto__cifra hk-veredicto__cifra--idle">Sin cifra</span>
              <ul className="hk-lista hk-texto-sec" data-motivos="">
                {r.veredicto.motivos.map((m) => <li key={m} data-motivo={m}>{textoMotivo(m)}</li>)}
              </ul>
              <span className="hk-texto">Ni margen ni hora de llegada: sin estos datos, una hora sería inventada. Los hechos de abajo valen igual.</span>
            </>
          )}
          <Derivado d={r.veredicto} servido={servido} />
        </div>
        <div className="hk-veredicto__col">
          <span className="hk-label">Con qué ritmo</span>
          <ul className="hk-lista hk-texto" data-base="">
            {r.base.personas.map((b) => (
              <li key={b.persona} data-base-persona={b.persona}>{arroba(b.persona)}: {b.ritmo_min != null
                ? <><span data-n="">{b.n}</span> medidas · entre el <span data-ritmo-min="">{b.ritmo_min}</span> % y el <span data-ritmo-max="">{b.ritmo_max}</span> % de su franja</>
                : <><span data-n="">{b.n}</span> de <span data-minimo="">{r.base.minimo}</span> · sin ritmo todavía</>}</li>
            ))}
          </ul>
          <span className="hk-texto-sec">Por persona: lo que tardó de verdad ÷ su franja del plan, sin descansos, en las tareas ya hechas. Hacen falta {r.base.minimo}; con menos, «n de {r.base.minimo}» y sin cifra.{sinUsuario.length ? " Quien no tiene usuario de GitHub no sale aquí: va aparte, en «Sin usuario»." : ""}{r.base.desde ? <> Medidas desde <span data-base-desde=""><Hora iso={r.base.desde} zona={zona} /></span>.</> : null}</span>
        </div>
        <div className="hk-veredicto__col">
          <span className="hk-label">Contra qué</span>
          <div className="hk-bloque" data-objetivo="">
            {obj ? (
              <>
                <span className="hk-texto"><b>Entrega</b> <HoraDeclarada d={obj} zona={zona} />{obj.confirmar ? <b className="hk-declarado"> (confirmar)</b> : null}</span>
                <Declarado donde={obj.donde} d={obj} servido={servido} />
              </>
            ) : <span className="hk-texto">Sin hora de entrega en equipo.md.</span>}
          </div>
          {r.otras_entregas.map((o, i) => (
            <div key={i} className="hk-bloque" data-otra-entrega={o.donde}>
              <span className="hk-texto"><b>Otra entrega</b>{o.nombre ? <> · «<span data-nombre="">{o.nombre}</span>»</> : null}{" "}
                {o.donde === "criterios.md"
                  ? <><Hora iso={o.valor} zona={zona} /> (criterios.md, nota de <span data-cita="">{o.cita ? o.cita.slice(11, 16) : "—"}</span>)</>
                  : <HoraDeclarada d={o} zona={zona} />}</span>
              <Declarado donde={o.donde} d={o} servido={servido} />
            </div>
          ))}
          <span className="hk-texto-sec">Manda la de equipo.md. Las otras se enseñan al lado, sin elegir, y no quitan la estimación.</span>
        </div>
      </section>

      <Panel title="Hitos del plan" meta="sin previsión">
        <div className="hk-hitos">
          {r.hitos.map((h, i) => (
            <div key={i} className={`hk-hito hk-hito--${h.hito.valor ? (h.pasado ? "pasado" : "viene") : "sin"}`} data-hito={h.hito.nombre}>
              <span className="hk-meta">{h.hito.valor ? <Hora iso={h.hito.valor} zona={zona} /> : "sin hora"}</span>
              <span className="hk-texto"><b>«<span data-nombre="">{h.hito.nombre}</span>»</b></span>
              <span className="hk-texto-sec" data-pasado={h.pasado ? "si" : "no"}>{h.hito.valor ? (h.pasado ? "Ya pasó" : "Por venir") : `Sin hora · ${MOTIVO[h.hito.motivo] || h.hito.motivo || "—"}`} · «{h.hito.texto}»</span>
              <Declarado donde={h.hito.donde} d={h.hito} servido={servido} />
            </div>
          ))}
          {!r.hitos.length ? <Vacio>plan.md no tiene hitos.</Vacio> : null}
        </div>
        <span className="hk-texto-sec">Los hitos son los de plan.md, con su hora y si ya pasó. Sin previsión: el plan no dice qué tareas lleva cada hito.</span>
      </Panel>

      <Panel title="La cadena más larga" meta={r.cadena.length ? `tareas abiertas · ${r.cadena.map((e) => e.tarjeta.id).join(" → ")}` : "ninguna"}>
        {!r.cadena.length ? <Vacio>Ninguna tarea abierta con «Hasta» resuelto.</Vacio>
          : est ? <Linea r={r} zona={zona} servido={servido} pasados={pasados} riesgos={riesgos} />
            : (
              <>
                <Cadena layout="cajas" rows={r.cadena.map((e) => fila(e, zona, servido, pasados, riesgos, r.veredicto.valor, false))} />
                <span className="hk-texto-sec">Sin línea de tiempo mientras no haya estimación: las barras saldrían de las franjas del plan y parecerían una previsión. Es lo que dice plan.md.</span>
              </>
            )}
      </Panel>

      <div className="hk-fila">
        <div className="hk-col" style={{ flex: "999 1 720px" }}>
          <Panel title="Lo que la pone en riesgo" meta={`${r.hechos.length} hechos · ${r.riesgos.length} por estimación`}
            tone={pasados.size ? "fail" : r.riesgos.length || r.hechos.length ? "wait" : undefined}>
            {r.hechos.map((h, i) => <Hecho key={`h${i}`} h={h} tarjeta={h.tarea ? porTarea.get(h.tarea) : null} zona={zona} servido={servido} ahora={r.observado_en} />)}
            {r.riesgos.map((x) => <Riesgo key={`r${x.tarea}`} r={x} tarjeta={porTarea.get(x.tarea)} objetivo={obj} zona={zona} servido={servido} />)}
            {!r.hechos.length && !r.riesgos.length ? <Vacio>Nada: ningún plazo ha pasado sin cumplirse{est ? " y nada acaba después de la entrega ni con el ritmo más lento medido" : ""}.</Vacio> : null}
            <span className="hk-texto-sec">Primero los hechos (plazo pasado en rojo; parada o sin cerrar en ámbar; sin señales en gris). Después, ESTIMACIÓN: cada tarea abierta cuyo fin tarde pasa de la entrega, esté o no en la cadena. Es una previsión: nunca en rojo, y solo con su fin tarde.</span>
          </Panel>
          <Panel title="Lo que ve el agente" meta="estado-equipo.md">
            <span className="hk-mono hk-dato" data-resumen-ruta="">{r.resumen}</span>
            <span className="hk-texto-sec">La línea de «## Jurado y ruta». El detalle sale del mismo bloque y es el que da el MCP (ruta).</span>
          </Panel>
        </div>
        <aside className="hk-col" style={{ flex: "1 1 400px" }}>
          <Panel title="De dónde sale">
            <dl className="hk-ficha hk-ficha--ancha">
              <dt>Sin plazo</dt>
              <dd>{r.sin_plazo.length ? r.sin_plazo.map((x) => (
                <span key={x.tarea} className="hk-bloque" data-sin-plazo={x.tarea}>
                  <span><b className="hk-mono">{x.tarea}</b> · {MOTIVO[x.motivo] || x.motivo}: ni a tiempo ni tarde{est ? ", y no se cuenta en la estimación" : ""}.</span>
                  <Declarado donde="plan.md" d={x} servido={servido} />
                </span>)) : <span className="hk-texto-sec">Ninguna tarea abierta sin plazo.</span>}</dd>
              <dt>Sin usuario</dt>
              <dd>{sinUsuario.length ? sinUsuario.map((x) => (
                <span key={x.tarea} className="hk-bloque" data-sin-usuario={x.tarea}>
                  <span><b className="hk-mono">{x.tarea}</b> · <span data-dueno="">{x.dueno}</span>: sin usuario de GitHub: no se mide{est ? ", y no se cuenta en la estimación" : ""}.</span>
                  <Declarado donde="plan.md" d={x} servido={servido} />
                </span>)) : <span className="hk-texto-sec">Ninguna tarea con un dueño sin usuario de GitHub.</span>}</dd>
              <dt>No cuentan</dt>
              <dd>{r.fuera_de_entrega.length ? r.fuera_de_entrega.map((x) => (
                <span key={x.tarea} className="hk-bloque" data-fuera={x.tarea}>
                  <span><b className="hk-mono">{x.tarea}</b> {FUERA[x.motivo] || x.motivo}: no cuenta para la entrega.</span>
                  <Declarado donde="plan.md" d={x} servido={servido} />
                </span>)) : <span className="hk-texto-sec">Todas cuentan para la entrega.</span>}</dd>
              <dt>Descansos</dt>
              <dd>{r.descansos.length ? r.descansos.map((d, i) => (
                <span key={i} className="hk-bloque" data-descanso={i}>
                  <span className="hk-mono hk-dato">«<span data-texto="">{d.texto}</span>»</span>
                  <span>{d.personas ? d.personas.map(arroba).join(", ") : "Todos"} · {d.desde
                    ? <><Hora iso={d.desde} zona={zona} /> – <Hora iso={d.hasta} zona={zona} /></>
                    : `no se entiende (${MOTIVO[d.motivo] || d.motivo}): se enseña y no se usa`}</span>
                  <Declarado donde="plan.md" d={d} servido={servido} />
                </span>)) : <span className="hk-texto-sec">plan.md no tiene descansos.</span>}</dd>
              <dt>Al día</dt>
              <dd className="hk-bloque" data-viejo-bloque={r.viejo ? "si" : "no"}>
                <StatusPulse state={r.viejo ? "stale" : "ok"} label={r.viejo ? "Dato viejo" : "Al día"} />
                {r.dato_mas_viejo ? <span className="hk-texto-sec">El dato más viejo, <time dateTime={r.dato_mas_viejo}>{hace(r.dato_mas_viejo, servido)}</time>.</span> : null}
              </dd>
            </dl>
          </Panel>
          <Panel title="Para afinarla" meta="no se hace aquí">
            <span className="hk-texto-sec">Cambiar un plazo: <span className="hk-mono">/hack-plan</span>, columna Hasta de plan.md. La franja de cada tarea sale de ahí.</span>
            <span className="hk-texto-sec">La hora de entrega: la línea <span className="hk-mono">- Entrega:</span> de equipo.md. Dependencias, dueños y descansos: plan.md, con <span className="hk-mono">/hack-plan</span>.</span>
            <span className="hk-texto-sec">El ritmo no se toca: sale de lo que cada persona publica en main.</span>
          </Panel>
        </aside>
      </div>
    </div>
  );
}
