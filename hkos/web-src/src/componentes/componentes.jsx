// Los componentes del sistema (docs/hackathon-os/diseno-web/sistema/components/), reescritos para React 19 con sus
// nombres, props y clases hk-*. Añadidos respecto de index.d.ts, todos opcionales:
//   - ProvenanceTag: `label` (la fuente real de estado.schema.json, p. ej. «hook»; el color sigue a `source`) y `at`
//     (el observado_en, en <time dateTime>);
//   - TaskCard: `stateLabel` (la etiqueta de la vista: «en curso», «integrada (sin subir)»), `sourceLabel`, `at` y
//     `children` (notas: espera a…, ⚑ … a mano); el estado `lista`;
//   - todos pasan los `data-*` y `aria-*` que reciban al elemento raíz.

const cx = (...xs) => xs.filter(Boolean).join(" ");

function resto(p, fuera) {
  const r = {};
  for (const k in p) if (!fuera.includes(k) && (k.startsWith("data-") || k.startsWith("aria-"))) r[k] = p[k];
  return r;
}

const PULSE_LABEL = { idle: "Sin empezar", live: "En vivo", ok: "Hecho", wait: "Necesita acción", fail: "Fallo", stale: "Viejo" };

export function StatusPulse({ state = "idle", label, className, ...p }) {
  return (
    <span className={cx("hk-pulse", `hk-pulse--${state}`, className)} role="status" {...resto(p, [])}>
      <span className="hk-pulse__dot" aria-hidden="true" />
      {label === false ? null : <span className="hk-pulse__label">{label || PULSE_LABEL[state]}</span>}
    </span>
  );
}

export function Panel({ title, meta, tone, children, className, ...p }) {
  return (
    <section className={cx("hk-panel", tone && tone !== "normal" && `hk-panel--${tone}`, className)}
      aria-label={title || undefined} {...resto(p, [])}>
      {title || meta ? (
        <header className="hk-panel__head">
          <span className="hk-label">{title}</span>
          {meta != null && meta !== "" ? <span className="hk-panel__meta">{meta}</span> : null}
        </header>
      ) : null}
      <div className="hk-panel__body">{children}</div>
    </section>
  );
}

const SOURCE_LABEL = { relay: "relay", git: "git", github: "github", declarado: "declarado" };

export function ProvenanceTag({ source = "git", age, stale, by, label, at, className, ...p }) {
  const texto = label ?? (source === "declarado" && by ? `declarado por ${by}` : SOURCE_LABEL[source]);
  return (
    <span className={cx("hk-prov", `hk-prov--${source}`, stale && "is-stale", className)}
      title={stale ? `Dato viejo: no se ha actualizado desde ${age || "hace rato"}` : undefined} {...resto(p, [])}>
      <span className="hk-prov__src">{texto}</span>
      {age ? <span>· {at ? <time dateTime={at}>{age}</time> : age}</span> : null}
      {stale ? <span className="hk-prov__stale">viejo</span> : null}
    </span>
  );
}

export function Button({ variant = "ghost", busy, disabled, onClick, children, className, type = "button", ...p }) {
  return (
    <button type={type} className={cx("hk-btn", `hk-btn--${variant}`, busy && "is-busy", className)}
      disabled={disabled || busy} aria-busy={busy || undefined} onClick={onClick} {...resto(p, [])}>
      {children}
    </button>
  );
}

const TASK_STATE = {
  pendiente: ["idle", "Pendiente"], lista: ["idle", "Lista"], reclamada: ["idle", "Reclamada"],
  en_curso: ["live", "En curso"], en_revision: ["live", "En revisión"], integrada: ["ok", "Integrada"],
  publicada: ["ok", "Publicada"], cerrada: ["ok", "Cerrada"], parada: ["wait", "Parada"],
  no_cerrada: ["wait", "Sin cerrar"], fallo: ["fail", "Fallo"],
};

export function TaskCard({ id, title, owner, state, source, age, stale, declaredBy, action, className,
  stateLabel, sourceLabel, at, children, ...p }) {
  const st = TASK_STATE[state] || TASK_STATE.pendiente;
  const tono = stale ? "stale" : st[0];
  return (
    <article className={cx("hk-task", `hk-task--${tono}`, className)} {...resto(p, [])}>
      <span className="hk-task__id">{id}</span>
      <span className="hk-task__title">{title}</span>
      {action ? <div className="hk-task__action">{action}</div> : null}
      <div className="hk-task__foot">
        <StatusPulse state={tono} label={stateLabel || st[1]} />
        <span className="hk-task__owner">{owner ? `@${owner}` : "sin dueño"}</span>
        {source ? <ProvenanceTag source={source} age={age} stale={stale} by={declaredBy} label={sourceLabel} at={at} /> : null}
      </div>
      {children ? <div className="hk-task__notes">{children}</div> : null}
    </article>
  );
}

// CriterioRow (0.5.0): una nota de criterios.md y lo que la cubre. La cobertura y el orden llegan hechos en la vista.
// Cambios respecto de index.d.ts: `said`, `who`, `affects`… pueden ser nodos (cada dato en su elemento); `at` es el
// observado_en de la nota; las tareas, evidencias y pruebas van como `children` (CriterioTarea, CriterioEvidencia,
// CriterioPrueba); `trabajoNuevo` es la línea «trabajo nuevo desde…».
const COVER = {
  sin_tarea: ["wait", "Sin tarea"], planificada: ["idle", "Planificada"], en_curso: ["live", "En curso"],
  ambigua: ["wait", "Ambigua: la cita casa con varias notas"], en_pitch: ["idle", "En el pitch (declarado)"],
  cubierta: ["ok", "Cubierta"], corregida: ["idle", "Corregida"],
};

export function CriterioRow({ time, who, where, strength, strengthKind, said, affects, corrects, by, age, at, coverage,
  coverageLabel, coverageStale, coverageTag, trabajoNuevo, pitch, hint, children, className, ...p }) {
  const cov = COVER[coverage] ? coverage : "sin_tarea", c = COVER[cov];
  return (
    <article className={cx("hk-crit", `hk-crit--${cov}`, coverageStale && "is-stale", className)} {...resto(p, [])}>
      <div className="hk-crit__when">
        <span className="hk-crit__time">{time}</span>
        <span className="hk-crit__who">{who}</span>
        {where ? <span className="hk-crit__where">{where}</span> : null}
        {strength ? (
          <span className="hk-crit__strength">fuerza{" "}
            <span className={cx("hk-crit__force", `hk-crit__force--${strengthKind || "sin_precisar"}`)} data-fuerza="">{strength}</span>
          </span>
        ) : null}
      </div>
      <div className="hk-crit__said">
        <span className="hk-crit__quote">{said}</span>
        {affects ? <span className="hk-crit__muted">Afecta a: {affects}</span> : null}
        {corrects ? <span className="hk-crit__muted">Corrige a la nota de <span className="hk-crit__tag" data-corrige="">{corrects}</span>.</span> : null}
        <ProvenanceTag source="declarado" label={<>declarado por <span data-anotado="">{by}</span> · criterios.md</>} age={age} at={at} />
      </div>
      <div className="hk-crit__cover">
        <span className="hk-acciones">
          <StatusPulse state={coverageStale ? "stale" : c[0]} label={coverageLabel || c[1]} data-cobertura-pulso="" />
          {coverageTag}
        </span>
        {trabajoNuevo ? <span className="hk-crit__note" data-trabajo-nuevo="">{trabajoNuevo}</span> : null}
        {children}
        {pitch ? <span className="hk-crit__link" data-pitch="">citada en pitch.md {pitch}</span> : null}
        {hint ? <span className="hk-crit__hint">{hint}</span> : null}
      </div>
    </article>
  );
}

/** Una tarea que cita la nota, con su enlace (la etiqueta «(criterios: …)» de plan.md: declarado, sin autor). */
export function CriterioTarea({ id, title, owner, state, stateLabel, source, sourceLabel, age, at, stale, notes, link, ...p }) {
  const st = TASK_STATE[state] || TASK_STATE.pendiente;
  return (
    <div className={cx("hk-crit__item", stale && "is-stale")} {...resto(p, [])}>
      <span className="hk-crit__line"><span className="hk-crit__id">{id}</span><span className="hk-crit__title">{title}</span></span>
      <span className="hk-crit__foot">
        <StatusPulse state={stale ? "stale" : st[0]} label={stateLabel || st[1]} />
        <span className="hk-task__owner">{owner ? `@${owner}` : "sin dueño"}</span>
        {source ? <ProvenanceTag source={source} label={sourceLabel} age={age} at={at} stale={stale} /> : null}
      </span>
      {notes?.length ? notes.map((n) => <span key={n} className="hk-crit__note">{n}</span>) : null}
      {link ? <span className="hk-crit__link" data-enlace="">{link}</span> : null}
    </div>
  );
}

/** El commit o la fusión que publicó la tarea (el último). Siempre de git. */
export function CriterioEvidencia({ tipo, task, sha, label, age, at, stale, ...p }) {
  return (
    <div className={cx("hk-crit__item", stale && "is-stale")} {...resto(p, [])}>
      <span className="hk-crit__line"><span className="hk-crit__id">{task}</span>
        <span className="hk-crit__muted">{tipo === "fusion" ? "fusión" : "commit"} <span className="hk-mono" data-sha="">{sha}</span> · el último publicado</span>
      </span>
      <span className="hk-crit__foot">
        <StatusPulse state={stale ? "stale" : "ok"} label="En main" />
        <ProvenanceTag source="git" label={label} age={age} at={at} stale={stale} />
      </span>
    </div>
  );
}

/** El último resultado de la Prueba de una conexión de la tarea. No cambia la cobertura; «falla» en ámbar (el rojo es
 *  solo para un plazo pasado). */
export function CriterioPrueba({ task, conexion, result, source, label, age, at, stale, ...p }) {
  return (
    <div className={cx("hk-crit__item", stale && "is-stale")} {...resto(p, [])}>
      <span className="hk-crit__line"><span className="hk-crit__id">{task}</span><span className="hk-crit__muted">Prueba</span>
        <span className="hk-crit__path">{conexion}</span></span>
      <span className="hk-crit__foot">
        <StatusPulse state={stale ? "stale" : result === "falla" ? "wait" : "ok"} label={result === "falla" ? "Falla" : "Pasa"} />
        <ProvenanceTag source={source} label={label} age={age} at={at} stale={stale} />
      </span>
    </div>
  );
}

// Cadena (0.5.0): la ruta crítica, solo con tareas abiertas. Las horas llegan en la vista; el componente solo las
// coloca en la escala `min`–`max` (milisegundos). Cambios respecto de index.d.ts: la barra de cada fila es su franja
// del plan (`kind`: `franja`, declarada; `plazo_pasado`, un hecho, en rojo; `vieja`); `est` es el tramo estimado, siempre
// discontinuo (`estKind`: `prevista` o `no_llega`, en ámbar), o `estAt` si es una sola hora (un punto, no una barra de
// anchura cero; lo mismo `end.at` en vez de `end.from`/`end.to`); `pulse` = [estado, palabra]; `sub`, `note` y `extra`
// pueden ser nodos; `data` va al elemento de la fila.
const CHAIN = {
  franja: "franja del plan (declarado)", curso: "en curso", prevista: "fin estimado (estimación)",
  plazo_pasado: "su plazo ya pasó (hecho)", no_llega: "acaba después de la entrega (estimación)",
  vieja: "dato viejo",
};
const MARK = { ahora: "ahora", hito: "hito del plan", entrega: "entrega (equipo.md)" };

export function Cadena({ layout = "linea", rows = [], min = 0, max = 1, ticks = [], marks = [], end, legend = true,
  children, className, ...p }) {
  const pct = (x) => `${Math.max(0, Math.min(100, ((x - min) / (max - min || 1)) * 100))}%`;
  const span = (a, b) => ({ left: pct(a), width: `calc(${pct(b)} - ${pct(a)})` });
  if (layout === "cajas") {
    return (
      <div className={cx("hk-chain", "hk-chain--cajas", className)} {...resto(p, [])}>
        <div className="hk-chain__boxes">
          {rows.map((r, i) => (
            <div key={r.id} className="hk-chain__box" {...(r.data || {})}>
              <span className="hk-chain__id">{r.id}{i < rows.length - 1 ? <span className="hk-chain__arrow"> →</span> : null}</span>
              <span className="hk-chain__title">{r.title}</span>
              <span className="hk-chain__sub">{r.sub}</span>
              {r.pulse ? <StatusPulse state={r.pulse[0]} label={r.pulse[1]} /> : null}
              {r.franja ? <span className="hk-chain__franja">{r.franja}</span> : null}
              {r.note ? <span className="hk-chain__note">{r.note}</span> : null}
              {r.extra}
            </div>
          ))}
        </div>
        {children}
      </div>
    );
  }
  const usados = new Set();
  for (const r of rows) {
    if (r.from != null) usados.add(r.kind || "franja");
    if (r.est || r.estAt != null) usados.add(r.estKind || "prevista");
  }
  const lane = (extra) => (
    <div className="hk-chain__lane">
      {marks.map((m, i) => <span key={`m${i}`} className={`hk-chain__mark hk-chain__mark--${m.kind || "hito"}`}
        style={{ left: pct(m.at) }} title={m.label} />)}
      {extra}
    </div>
  );
  return (
    <div className={cx("hk-chain", className)} {...resto(p, [])}>
      <div className="hk-chain__grid">
        <span />
        <div className="hk-chain__ticks">
          {ticks.map((k, i) => (
            <span key={i} className="hk-chain__tick" style={{ left: pct(k.at),
              transform: `translateX(${i === 0 ? "0" : i === ticks.length - 1 ? "-100%" : "-50%"})` }}>{k.label}</span>
          ))}
        </div>
        <span />
        {rows.map((r) => (
          <div key={r.id} className="hk-chain__fila" {...(r.data || {})}>
            <div className="hk-chain__who">
              <span className="hk-chain__line"><span className="hk-chain__id">{r.id}</span> <span className="hk-chain__title">{r.title}</span></span>
              <span className="hk-chain__sub">{r.sub}</span>
              {r.franja ? <span className="hk-chain__sub">{r.franja}</span> : null}
            </div>
            {lane([
              r.deadline != null ? <span key="d" className={cx("hk-chain__deadline", r.deadlinePast && "is-past")} style={{ left: pct(r.deadline) }} /> : null,
              r.from != null ? <span key="b" className={`hk-chain__bar hk-chain__bar--${r.kind || "franja"}`} style={span(r.from, r.to)} /> : null,
              r.est ? <span key="e" className={`hk-chain__bar hk-chain__bar--est hk-chain__bar--${r.estKind || "prevista"}`} style={span(r.est[0], r.est[1])} /> : null,
              r.estAt != null ? <span key="p" className={`hk-chain__punto hk-chain__punto--${r.estKind || "prevista"}`} style={{ left: pct(r.estAt) }} /> : null,
            ])}
            <div className="hk-chain__state">
              {r.pulse ? <StatusPulse state={r.pulse[0]} label={r.pulse[1]} /> : null}
              {r.note ? <span className={`hk-chain__note hk-chain__note--${r.noteKind || "normal"}`}>{r.note}</span> : null}
              {r.extra}
            </div>
          </div>
        ))}
        {end ? (
          <div className="hk-chain__fila" data-fin="">
            <div className="hk-chain__who"><span className="hk-chain__line">{end.title || "Fin estimado"}</span>
              <span className="hk-chain__sub">{end.sub || "un rango, con el ritmo real; nunca una sola hora"}</span></div>
            {lane(end.at != null
              ? <span className={`hk-chain__punto hk-chain__punto--${end.tone || "idle"}`} style={{ left: pct(end.at) }} />
              : <span className={`hk-chain__range hk-chain__range--${end.tone || "idle"}`} style={span(end.from, end.to)} />)}
            <div className="hk-chain__state">
              <span className={`hk-chain__end hk-chain__end--${end.tone || "idle"}`}>{end.label}</span>
              {end.range ? <span className="hk-chain__note">{end.range}</span> : null}
            </div>
          </div>
        ) : null}
      </div>
      {legend ? (
        <div className="hk-chain__legend">
          {Object.keys(CHAIN).filter((k) => usados.has(k)).map((k) => (
            <span key={k} className="hk-chain__key"><span className={`hk-chain__swatch hk-chain__bar--${k}${k === "prevista" || k === "no_llega" ? " hk-chain__bar--est" : ""}`} />{CHAIN[k]}</span>
          ))}
          <span className="hk-chain__key"><span className="hk-chain__swatch hk-chain__swatch--deadline" />su «Hasta» (plan.md)</span>
          {Object.keys(MARK).filter((k) => marks.some((m) => (m.kind || "hito") === k)).map((k) => (
            <span key={k} className="hk-chain__key"><span className={`hk-chain__swatch hk-chain__mark--${k}`} />{MARK[k]}</span>
          ))}
        </div>
      ) : null}
      {children}
    </div>
  );
}

// Lo que dice cada nivel detrás de su número, con el mismo texto que la línea de estado-equipo.md (api.md §6). Solo 2b
// lleva texto (ADR-0014, decisión 7): «nivel 2b» a secas no dice qué es.
const LEVEL_TEXT = { "2b": "fusión estructural sin conflictos" };

export function CollisionAlert({ severity = "amarillo", level = 1, path, contract, people = [], age, actions, className, ...p }) {
  const rojo = severity === "rojo";
  return (
    <div className={cx("hk-alert", `hk-alert--${severity}`, className)} role={rojo ? "alert" : "status"} {...resto(p, [])}>
      <div className="hk-alert__head">
        <StatusPulse state={rojo ? "fail" : "wait"} label={rojo ? "Colisión roja" : "Colisión amarilla"} />
        <span className="hk-alert__level">NIVEL {level}{LEVEL_TEXT[level] ? ` · ${LEVEL_TEXT[level]}` : ""}</span>
      </div>
      <span className="hk-alert__path">{path}</span>
      <span className="hk-alert__detail">
        {[contract ? `contrato «${contract}»` : null, people.map((x) => `@${x}`).join(", "), age].filter(Boolean).join(" · ")}
      </span>
      {actions ? <div className="hk-alert__actions">{actions}</div> : null}
    </div>
  );
}
