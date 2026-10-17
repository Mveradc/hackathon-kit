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

export function CollisionAlert({ severity = "amarillo", level = 1, path, contract, people = [], age, actions, className, ...p }) {
  const rojo = severity === "rojo";
  return (
    <div className={cx("hk-alert", `hk-alert--${severity}`, className)} role={rojo ? "alert" : "status"} {...resto(p, [])}>
      <div className="hk-alert__head">
        <StatusPulse state={rojo ? "fail" : "wait"} label={rojo ? "Colisión roja" : "Colisión amarilla"} />
        <span className="hk-alert__level">NIVEL {level}</span>
      </div>
      <span className="hk-alert__path">{path}</span>
      <span className="hk-alert__detail">
        {[contract ? `contrato «${contract}»` : null, people.map((x) => `@${x}`).join(", "), age].filter(Boolean).join(" · ")}
      </span>
      {actions ? <div className="hk-alert__actions">{actions}</div> : null}
    </div>
  );
}
