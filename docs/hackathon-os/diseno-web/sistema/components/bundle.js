/* @ds-bundle: {"format":4,"namespace":"HkOS","components":[{"name":"Panel"},{"name":"StatusPulse"},{"name":"ProvenanceTag"},{"name":"Button"},{"name":"TaskCard"},{"name":"CollisionAlert"},{"name":"TeamGraph"}]} */
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

  window.HkOS = { Panel: Panel, StatusPulse: StatusPulse, ProvenanceTag: ProvenanceTag, Button: Button,
    TaskCard: TaskCard, CollisionAlert: CollisionAlert, TeamGraph: TeamGraph };
})();
