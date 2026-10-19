/* @ds-bundle: {"format":4,"namespace":"HkOS","components":[{"name":"Panel"},{"name":"StatusPulse"},{"name":"ProvenanceTag"},{"name":"Button"},{"name":"TaskCard"},{"name":"CollisionAlert"},{"name":"TeamGraph"},{"name":"CriterioRow"},{"name":"Cadena"}]} */
(function () {
  var React = window.React;
  var h = React.createElement;
  function cx() { return Array.prototype.filter.call(arguments, Boolean).join(" "); }

  var PULSE_LABEL = { idle: "Sin empezar", live: "En vivo", ok: "Hecho", wait: "Necesita acción", fail: "Fallo", stale: "Viejo" };

  function StatusPulse(p) {
    var s = p.state || "idle";
    return h("span", { className: cx("hk-pulse", "hk-pulse--" + s, p.className), role: "status" },
      h("span", { className: "hk-pulse__dot", "aria-hidden": true }),
      p.label === false ? null : h("span", { className: "hk-pulse__label" }, p.label || PULSE_LABEL[s]));
  }

  function Panel(p) {
    return h("section", { className: cx("hk-panel", p.tone && p.tone !== "normal" && "hk-panel--" + p.tone, p.className) },
      (p.title || p.meta) ? h("header", { className: "hk-panel__head" },
        h("span", { className: "hk-label" }, p.title),
        p.meta ? h("span", { className: "hk-panel__meta" }, p.meta) : null) : null,
      h("div", { className: "hk-panel__body" }, p.children));
  }

  var SOURCE_LABEL = { relay: "relay", git: "git", github: "github", declarado: "declarado" };
  function ProvenanceTag(p) {
    var src = p.source || "git";
    return h("span", { className: cx("hk-prov", "hk-prov--" + src, p.stale && "is-stale", p.className),
      title: p.stale ? "Dato viejo: no se ha actualizado desde " + (p.age || "hace rato") : undefined },
      h("span", { className: "hk-prov__src" }, src === "declarado" && p.by ? "declarado por " + p.by : SOURCE_LABEL[src]),
      p.age ? h("span", null, "· " + p.age) : null,
      p.stale ? h("span", { className: "hk-prov__stale" }, "viejo") : null);
  }

  function Button(p) {
    var v = p.variant || "ghost";
    var rest = {};
    for (var k in p) if (k !== "variant" && k !== "busy" && k !== "children" && k !== "className") rest[k] = p[k];
    rest.className = cx("hk-btn", "hk-btn--" + v, p.busy && "is-busy", p.className);
    rest.type = p.type || "button";
    if (p.busy) rest["aria-busy"] = true;
    return h("button", rest, p.children);
  }

  var TASK_STATE = {
    pendiente: ["idle", "Pendiente"], reclamada: ["idle", "Reclamada"], en_curso: ["live", "En curso"],
    en_revision: ["live", "En revisión"], integrada: ["ok", "Integrada"], publicada: ["ok", "Publicada"],
    cerrada: ["ok", "Cerrada"], parada: ["wait", "Parada"], no_cerrada: ["wait", "Sin cerrar"],
    fallo: ["fail", "Fallo"]
  };
  function TaskCard(p) {
    var st = TASK_STATE[p.state] || TASK_STATE.pendiente;
    var tone = p.stale ? "stale" : st[0];
    return h("article", { className: cx("hk-task", "hk-task--" + tone, p.className) },
      h("span", { className: "hk-task__id" }, p.id),
      h("span", { className: "hk-task__title" }, p.title),
      p.action ? h("div", { className: "hk-task__action" }, p.action) : null,
      h("div", { className: "hk-task__foot" },
        h(StatusPulse, { state: p.stale ? "stale" : st[0], label: st[1] }),
        p.owner ? h("span", null, "@" + p.owner) : h("span", null, "sin dueño"),
        p.source ? h(ProvenanceTag, { source: p.source, age: p.age, stale: p.stale, by: p.declaredBy }) : null));
  }

  function CollisionAlert(p) {
    var sev = p.severity || "amarillo";
    return h("div", { className: cx("hk-alert", "hk-alert--" + sev, p.className), role: sev === "rojo" ? "alert" : "status" },
      h("div", { className: "hk-alert__head" },
        h(StatusPulse, { state: sev === "rojo" ? "fail" : "wait", label: sev === "rojo" ? "Colisión roja" : "Colisión amarilla" }),
        h("span", { className: "hk-alert__level" }, "NIVEL " + (p.level || 1))),
      h("span", { className: "hk-alert__path" }, p.path),
      h("span", { className: "hk-alert__detail" },
        [p.contract ? "contrato «" + p.contract + "»" : null, (p.people || []).map(function (x) { return "@" + x; }).join(", "), p.age]
          .filter(Boolean).join(" · ")),
      p.actions ? h("div", { className: "hk-alert__actions" }, p.actions) : null);
  }

  /* TeamGraph: los paquetes solo viajan cuando el consumidor pasa un evento nuevo en `events`.
     Sin eventos, el grafo está quieto: la animación nunca inventa actividad (principio III). */
  var R = { relay: 26, github: 22, person: 20, orchestrator: 15, worker: 11 };
  function reduced() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }
  function Packet(p) {
    var ref = React.useRef(null);
    React.useEffect(function () {
      var el = ref.current, t0 = null, dur = p.duration || 900, raf;
      function step(t) {
        if (t0 === null) t0 = t;
        var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        if (el) {
          el.setAttribute("cx", p.x1 + (p.x2 - p.x1) * e);
          el.setAttribute("cy", p.y1 + (p.y2 - p.y1) * e);
          el.setAttribute("opacity", k < .85 ? 1 : (1 - k) / .15);
        }
        if (k < 1) raf = requestAnimationFrame(step); else p.onDone();
      }
      raf = requestAnimationFrame(step);
      return function () { cancelAnimationFrame(raf); };
    }, []);
    return h("circle", { ref: ref, r: 3.5, cx: p.x1, cy: p.y1, className: "hk-packet hk-packet--" + p.channel });
  }

  function TeamGraph(p) {
    var nodes = p.nodes || [], edges = p.edges || [], w = p.width || 640, hgt = p.height || 320;
    var byId = {}; nodes.forEach(function (n) { byId[n.id] = n; });
    var st = React.useState([]), packets = st[0], setPackets = st[1];
    var hs = React.useState({}), hot = hs[0], setHot = hs[1];
    var seen = React.useRef({});
    React.useEffect(function () {
      var fresh = (p.events || []).filter(function (ev) { return !seen.current[ev.id]; });
      if (!fresh.length) return;
      fresh.forEach(function (ev) { seen.current[ev.id] = true; });
      var still = reduced();
      setHot(function (old) {
        var n = Object.assign({}, old);
        fresh.forEach(function (ev) { n[ev.edge] = (n[ev.edge] || 0) + 1; });
        return n;
      });
      fresh.forEach(function (ev) {
        setTimeout(function () {
          setHot(function (old) { var n = Object.assign({}, old); n[ev.edge] = Math.max(0, (n[ev.edge] || 1) - 1); return n; });
        }, 1200);
      });
      if (!still) setPackets(function (old) { return old.concat(fresh); });
    }, [p.events]);

    function edgeEnds(e) {
      var a = byId[e.from], b = byId[e.to];
      if (!a || !b) return null;
      var dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
      var ra = (R[a.kind] || 14) + 2, rb = (R[b.kind] || 14) + 2;
      return { x1: a.x + dx / d * ra, y1: a.y + dy / d * ra, x2: b.x - dx / d * rb, y2: b.y - dy / d * rb };
    }

    return h("svg", { className: cx("hk-graph", p.className), viewBox: "0 0 " + w + " " + hgt, role: "img",
      "aria-label": p.label || "Grafo del equipo" },
      edges.map(function (e) {
        var c = edgeEnds(e); if (!c) return null;
        return h("line", { key: e.id, x1: c.x1, y1: c.y1, x2: c.x2, y2: c.y2,
          className: cx("hk-edge", "hk-edge--" + (e.channel || "relay"), e.stale && "is-stale", !e.stale && hot[e.id] && "is-hot") });
      }),
      packets.map(function (ev) {
        var e = edges.filter(function (x) { return x.id === ev.edge; })[0]; if (!e || e.stale) return null;
        var c = edgeEnds(e); if (!c) return null;
        var rev = ev.reverse;
        return h(Packet, { key: ev.id, channel: e.channel || "relay", duration: p.packetMs,
          x1: rev ? c.x2 : c.x1, y1: rev ? c.y2 : c.y1, x2: rev ? c.x1 : c.x2, y2: rev ? c.y1 : c.y2,
          onDone: function () { setPackets(function (old) { return old.filter(function (x) { return x.id !== ev.id; }); }); } });
      }),
      nodes.map(function (n) {
        var r = R[n.kind] || 14, s = n.state && n.state !== "live" && n.state !== "idle" ? n.state : null;
        var word = { wait: "ESPERA", fail: "FALLO", stale: "VIEJO", ok: "OK" }[s];
        return h("g", { key: n.id, className: cx("hk-node", "hk-node--" + n.kind, s && "is-" + s) },
          h("circle", { className: "hk-node__halo", cx: n.x, cy: n.y, r: r }),
          h("circle", { className: "hk-node__core", cx: n.x, cy: n.y, r: r }),
          n.glyph ? h("text", { className: "hk-node__glyph", x: n.x, y: n.y }, n.glyph) : null,
          n.label ? h("text", { className: "hk-node__label", x: n.x, y: n.y + r + 15 }, n.label) : null,
          word ? h("text", { className: "hk-node__state", x: n.x, y: n.y + r + 28 }, word) : null);
      }));
  }

  /* CriterioRow: una nota de criterios.md y lo que la cubre. La cobertura y el orden llegan hechos en la vista;
     aquí solo se pintan. Nunca sale «cubierta» porque algo lo declare: lo declarado va en violeta, con su fuente.
     Todo lo que no es «cubierta» ni «corregida» está sin cubrir: sin tarea, planificada, en curso, ambigua o en el pitch. */
  var COVER = {
    sin_tarea: ["wait", "Sin tarea"], planificada: ["idle", "Planificada"], en_curso: ["live", "En curso"],
    ambigua: ["wait", "Ambigua: la cita casa con varias notas"], en_pitch: ["idle", "En el pitch (declarado)"],
    cubierta: ["ok", "Cubierta"], corregida: ["idle", "Corregida"]
  };
  function CriterioItem(it) {
    var foot;
    if (it.kind === "evidencia") {
      return h("div", { className: cx("hk-crit__item", it.stale && "is-stale") },
        h("span", { className: "hk-crit__line" }, h("span", { className: "hk-crit__id" }, it.task),
          h("span", { className: "hk-crit__muted" }, (it.tipo === "fusion" ? "fusión " : "commit ") + it.sha + " · el último publicado")),
        h("span", { className: "hk-crit__foot" }, h(StatusPulse, { state: it.stale ? "stale" : "ok", label: "En main" }), h(ProvenanceTag, { source: "git", age: it.age, stale: it.stale })));
    }
    if (it.kind === "prueba") {
      return h("div", { className: cx("hk-crit__item", it.stale && "is-stale") },
        h("span", { className: "hk-crit__line" }, h("span", { className: "hk-crit__muted" }, "Prueba"), h("span", { className: "hk-crit__path" }, it.conexion)),
        h("span", { className: "hk-crit__foot" },
          h(StatusPulse, { state: it.stale ? "stale" : it.result === "falla" ? "fail" : "ok", label: it.result === "falla" ? "Falla" : "Pasa" }),
          h(ProvenanceTag, { source: "relay", age: it.age, stale: it.stale })));
    }
    var st = TASK_STATE[it.state] || TASK_STATE.pendiente;
    foot = h("span", { className: "hk-crit__foot" },
      h(StatusPulse, { state: it.stale ? "stale" : st[0], label: st[1] }),
      it.owner ? h("span", null, "@" + it.owner) : h("span", null, "sin dueño"),
      it.source ? h(ProvenanceTag, { source: it.source, age: it.age, stale: it.stale }) : null);
    return h("div", { className: cx("hk-crit__item", it.stale && "is-stale") },
      h("span", { className: "hk-crit__line" }, h("span", { className: "hk-crit__id" }, it.id), h("span", { className: "hk-crit__title" }, it.title)),
      foot,
      it.note ? h("span", { className: "hk-crit__note" }, it.note) : null,
      it.since ? h("span", { className: "hk-crit__note" }, "trabajo nuevo desde " + it.since) : null,
      it.link ? h("span", { className: "hk-crit__link" }, h("span", { className: "hk-crit__tag" }, "(criterios: " + it.link.cita + ")"),
        h("span", null, (it.link.ambiguous ? "ambigua, " : "") + "en " + (it.link.where || "plan.md")), h(ProvenanceTag, { source: "declarado", age: it.link.age })) : null);
  }
  function CriterioRow(p) {
    var cov = COVER[p.coverage] ? p.coverage : "sin_tarea", c = COVER[cov];
    return h("article", { className: cx("hk-crit", "hk-crit--" + cov, p.coverageStale && "is-stale", p.className) },
      h("div", { className: "hk-crit__when" },
        h("span", { className: "hk-crit__time" }, p.time),
        h("span", { className: "hk-crit__who" }, p.who),
        p.where ? h("span", { className: "hk-crit__where" }, p.where) : null,
        p.strength ? h("span", { className: "hk-crit__strength" }, "fuerza ",
          h("span", { className: cx("hk-crit__force", "hk-crit__force--" + (p.strengthKind || "sin_precisar")) }, p.strength)) : null),
      h("div", { className: "hk-crit__said" },
        h("span", { className: "hk-crit__quote" }, p.said),
        p.affects ? h("span", { className: "hk-crit__muted" }, "Afecta a: " + p.affects) : null,
        p.corrects ? h("span", { className: "hk-crit__muted" }, "Corrige a la nota de ", h("span", { className: "hk-crit__tag" }, p.corrects), ".") : null,
        h(ProvenanceTag, { source: "declarado", by: p.by, age: p.age })),
      h("div", { className: "hk-crit__cover" },
        h(StatusPulse, { state: p.coverageStale ? "stale" : c[0], label: p.coverageLabel || c[1] }),
        (p.items || []).map(function (it, i) { return h(CriterioItem, Object.assign({ key: i }, it)); }),
        p.pitch ? h("span", { className: "hk-crit__link" }, h("span", null, "citada en pitch.md"),
          h(ProvenanceTag, { source: "declarado", age: p.pitch.age })) : null,
        p.hint ? h("span", { className: "hk-crit__hint" }, p.hint) : null,
        p.children));
  }

  /* Cadena: la ruta crítica en una línea de tiempo, solo con tareas abiertas (lo hecho no está en la cadena). Las
     posiciones llegan en la vista, en la escala que diga `min`–`max` (por ejemplo, horas desde el inicio); el componente
     solo las coloca. El fin es un rango, nunca una sola hora. Con layout="cajas" no hay barras: cada tarea sale con su
     franja declarada, para que lo que dice el plan no parezca una previsión. */
  var CHAIN = {
    curso: ["live", "En curso", "en curso"], prevista: ["idle", "Pendiente", "prevista (estimación)"],
    plazo_pasado: ["fail", "Plazo pasado", "su plazo ya pasó (hecho)"], no_llega: ["wait", "No llega", "acaba después de la entrega (estimación)"],
    vieja: ["stale", "Dato viejo", "espera a un dato viejo"]
  };
  var MARK = { ahora: "ahora", hito: "hito del plan", entrega: "entrega" };
  function Cadena(p) {
    var rows = p.rows || [], marks = p.marks || [], min = p.min || 0, max = p.max || 1;
    function pct(x) { return Math.max(0, Math.min(100, (x - min) / (max - min) * 100)) + "%"; }
    function span(a, b) { return { left: pct(a), width: "calc(" + pct(b) + " - " + pct(a) + ")" }; }
    if (p.layout === "cajas") {
      return h("div", { className: cx("hk-chain", "hk-chain--cajas", p.className) },
        h("div", { className: "hk-chain__boxes" }, rows.map(function (r, i) {
          return h("div", { key: r.id, className: "hk-chain__box" },
            h("span", { className: "hk-chain__id" }, r.id, i < rows.length - 1 ? h("span", { className: "hk-chain__arrow" }, " →") : null),
            h("span", { className: "hk-chain__title" }, r.title),
            h("span", { className: "hk-chain__sub" }, (r.owner ? "@" + r.owner : "sin dueño") + (r.state ? " · " + r.state : "")),
            r.franja ? h("span", { className: "hk-chain__franja" }, "franja " + r.franja) : null,
            r.franja ? h(ProvenanceTag, { source: "declarado", age: "plan" }) : null);
        })),
        p.children);
    }
    function lane(extra, key) {
      return h("div", { className: "hk-chain__lane", key: key },
        marks.map(function (m, i) { return h("span", { key: "m" + i, className: "hk-chain__mark hk-chain__mark--" + (m.kind || "hito"), style: { left: pct(m.at) } }); }),
        extra);
    }
    var used = {};
    rows.forEach(function (r) { used[r.kind || "prevista"] = true; });
    var ticks = p.ticks || [];
    return h("div", { className: cx("hk-chain", p.className) },
      h("div", { className: "hk-chain__grid" },
        h("span", null),
        h("div", { className: "hk-chain__ticks" }, ticks.map(function (k, i) {
          return h("span", { key: i, className: "hk-chain__tick", style: { left: pct(k.at), transform: "translateX(" + (i === 0 ? "0" : i === ticks.length - 1 ? "-100%" : "-50%") + ")" } }, k.label);
        })),
        h("span", null),
        rows.map(function (r) {
          var k = CHAIN[r.kind] ? r.kind : "prevista", st = CHAIN[k];
          return h(React.Fragment, { key: r.id },
            h("div", { className: "hk-chain__who" },
              h("span", { className: "hk-chain__line" }, h("span", { className: "hk-chain__id" }, r.id), " ", h("span", { className: "hk-chain__title" }, r.title)),
              h("span", { className: "hk-chain__sub" }, (r.owner ? "@" + r.owner : "sin dueño") + (r.franja ? " · franja " + r.franja : ""))),
            lane([
              r.deadline != null ? h("span", { key: "d", className: cx("hk-chain__deadline", k === "plazo_pasado" && "is-past"), style: { left: pct(r.deadline) } }) : null,
              r.from != null ? h("span", { key: "b", className: "hk-chain__bar hk-chain__bar--" + k, style: span(r.from, r.to) }) : null,
              r.est ? h("span", { key: "e", className: "hk-chain__bar hk-chain__bar--prevista", style: span(r.est[0], r.est[1]) }) : null
            ], "l"),
            h("div", { className: "hk-chain__state" },
              h(StatusPulse, { state: st[0], label: r.label || st[1] }),
              r.note ? h("span", { className: "hk-chain__note hk-chain__note--" + k }, r.note) : null));
        }),
        p.end ? h(React.Fragment, null,
          h("div", { className: "hk-chain__who" }, h("span", { className: "hk-chain__line" }, p.end.title || "Fin previsto"),
            h("span", { className: "hk-chain__sub" }, p.end.sub || "un rango, con el ritmo real; nunca una sola hora")),
          lane([
            h("span", { key: "r", className: "hk-chain__range hk-chain__range--" + (p.end.tone || "idle"), style: span(p.end.from, p.end.to) })
          ]),
          h("div", { className: "hk-chain__state" },
            h("span", { className: "hk-chain__end hk-chain__end--" + (p.end.tone || "idle") }, p.end.label),
            p.end.range ? h("span", { className: "hk-chain__note" }, p.end.range) : null)) : null),
      p.legend === false ? null : h("div", { className: "hk-chain__legend" },
        Object.keys(CHAIN).filter(function (k) { return used[k]; }).map(function (k) {
          return h("span", { key: k, className: "hk-chain__key" }, h("span", { className: "hk-chain__swatch hk-chain__bar--" + k }), CHAIN[k][2]);
        }),
        h("span", { className: "hk-chain__key" }, h("span", { className: "hk-chain__swatch hk-chain__swatch--deadline" }), "su «Hasta» (plan.md)"),
        Object.keys(MARK).filter(function (k) { return marks.some(function (m) { return (m.kind || "hito") === k; }); }).map(function (k) {
          return h("span", { key: k, className: "hk-chain__key" }, h("span", { className: "hk-chain__swatch hk-chain__mark--" + k }), MARK[k]);
        })),
      p.children);
  }

  window.HkOS = { Panel: Panel, StatusPulse: StatusPulse, ProvenanceTag: ProvenanceTag, Button: Button,
    TaskCard: TaskCard, CollisionAlert: CollisionAlert, TeamGraph: TeamGraph, CriterioRow: CriterioRow, Cadena: Cadena };
})();
