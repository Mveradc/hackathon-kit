import { useEffect, useRef, useState, useSyncExternalStore } from "react";

// TeamGraph, reescrito para React 19 (no copiado de diseno-web): `ref` llega como prop (sin forwardRef) y va al <svg>.
// La animación dice la verdad (sistema/README.md, principio 3):
//   - cada id nuevo de `events` lanza un paquete una vez; un id ya visto no lanza nada;
//   - el paquete es una animación CSS (hk-packet-viaje) y se retira en su `animationend`; la arista se ilumina con
//     otra (hk-edge-flash) que también se retira sola. Ningún temporizador crea ni retira actividad;
//   - por una arista `stale` no viaja nada; con `paused` (la web sin conexión) tampoco;
//   - con prefers-reduced-motion no hay paquetes: la arista solo se ilumina.
// Añadido respecto de index.d.ts: `paused` y `ref`.

const R = { relay: 26, github: 22, person: 20, orchestrator: 15, worker: 11 };
const VISTOS_MAX = 5000;
const CONSULTA = "(prefers-reduced-motion: reduce)";

function suscribir(cb) {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const m = window.matchMedia(CONSULTA);
  m.addEventListener?.("change", cb);
  return () => m.removeEventListener?.("change", cb);
}
const reducido = () => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(CONSULTA).matches;

export function useReducedMotion() {
  return useSyncExternalStore(suscribir, reducido, () => false);
}

const cx = (...xs) => xs.filter(Boolean).join(" ");

function extremos(e, porId) {
  const a = porId[e.from], b = porId[e.to];
  if (!a || !b) return null;
  const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
  const ra = (R[a.kind] || 14) + 2, rb = (R[b.kind] || 14) + 2;
  return { x1: a.x + (dx / d) * ra, y1: a.y + (dy / d) * ra, x2: b.x - (dx / d) * rb, y2: b.y - (dy / d) * rb };
}

export function TeamGraph({ nodes = [], edges = [], events = [], width = 640, height = 320, packetMs = 900, label,
  className, paused = false, ref }) {
  const quieto = useReducedMotion();
  const [paquetes, setPaquetes] = useState([]);
  const [destellos, setDestellos] = useState([]);
  const vistos = useRef(new Set());
  const aristas = useRef(new Map());
  aristas.current = new Map(edges.map((e) => [e.id, e]));

  useEffect(() => {
    const nuevos = [];
    for (const ev of events) {
      if (vistos.current.has(ev.id)) continue;
      vistos.current.add(ev.id);
      nuevos.push(ev);
    }
    if (vistos.current.size > VISTOS_MAX) {
      vistos.current = new Set([...vistos.current].slice(-VISTOS_MAX / 2));
      for (const ev of events) vistos.current.add(ev.id);
    }
    if (paused || !nuevos.length) return;
    const vivos = nuevos.filter((ev) => {
      const e = aristas.current.get(ev.edge);
      return e && !e.stale;
    });
    if (!vivos.length) return;
    setDestellos((d) => [...d, ...vivos.map((ev) => ({ id: ev.id, edge: ev.edge }))]);
    if (!quieto) setPaquetes((p) => [...p, ...vivos]);
  }, [events, paused, quieto]);

  // Lo que estaba en vuelo por una arista que se ha quedado vieja (o con la web sin conexión) se retira: si no, al
  // volver se montaría otra vez y animaría algo que ya no está pasando.
  useEffect(() => {
    const vale = (x) => !paused && aristas.current.get(x.edge) && !aristas.current.get(x.edge).stale;
    const vuela = (x) => !quieto && vale(x);
    setPaquetes((p) => (p.every(vuela) ? p : p.filter(vuela)));
    setDestellos((d) => (d.every(vale) ? d : d.filter(vale)));
  }, [edges, paused, quieto]);

  const porId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const quita = (set, id) => set((xs) => xs.filter((x) => x.id !== id));

  return (
    <svg ref={ref} className={cx("hk-graph", paused && "is-paused", className)} viewBox={`0 0 ${width} ${height}`}
      role="img" aria-label={label || "Grafo del equipo"}>
      {edges.map((e) => {
        const c = extremos(e, porId);
        if (!c) return null;
        return <line key={e.id} data-arista={e.id} {...c}
          className={cx("hk-edge", `hk-edge--${e.channel || "relay"}`, e.stale && "is-stale")} />;
      })}
      {destellos.map((d) => {
        const e = aristas.current.get(d.edge);
        const c = e && !e.stale && !paused ? extremos(e, porId) : null;
        if (!c) return null;
        return <line key={`f-${d.id}`} {...c} className={cx("hk-edge-flash", `hk-edge--${e.channel || "relay"}`)}
          onAnimationEnd={() => quita(setDestellos, d.id)} aria-hidden="true" />;
      })}
      {quieto || paused ? null : paquetes.map((ev) => {
        const e = aristas.current.get(ev.edge);
        const c = e && !e.stale ? extremos(e, porId) : null;
        if (!c) return null;
        const [x1, y1, x2, y2] = ev.reverse ? [c.x2, c.y2, c.x1, c.y1] : [c.x1, c.y1, c.x2, c.y2];
        return <circle key={ev.id} data-paquete={ev.id} r={3.5} cx={x1} cy={y1}
          className={`hk-packet hk-packet--${e.channel || "relay"}`}
          style={{ "--hk-dx": `${x2 - x1}px`, "--hk-dy": `${y2 - y1}px`, animationDuration: `${packetMs}ms` }}
          onAnimationEnd={() => quita(setPaquetes, ev.id)} aria-hidden="true" />;
      })}
      {nodes.map((n) => {
        const r = R[n.kind] || 14;
        const s = n.state && n.state !== "live" && n.state !== "idle" ? n.state : null;
        const palabra = { wait: "ESPERA", fail: "FALLO", stale: "VIEJO", ok: "OK" }[s];
        return (
          <g key={n.id} data-nodo={n.id} className={cx("hk-node", `hk-node--${n.kind}`, s && `is-${s}`, n.state === "live" && "is-live")}>
            <circle className="hk-node__halo" cx={n.x} cy={n.y} r={r} />
            <circle className="hk-node__core" cx={n.x} cy={n.y} r={r} />
            {n.glyph ? <text className="hk-node__glyph" x={n.x} y={n.y}>{n.glyph}</text> : null}
            {n.label ? <text className="hk-node__label" x={n.x} y={n.y + r + 15}>{n.label}</text> : null}
            {palabra ? <text className="hk-node__state" x={n.x} y={n.y + r + 28}>{palabra}</text> : null}
          </g>
        );
      })}
    </svg>
  );
}
