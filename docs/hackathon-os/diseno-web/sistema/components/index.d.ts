import type { ReactNode } from "react";

/** Estado visual. idle: sin empezar · live: actividad real reciente · ok: cumplido · wait: necesita acción · fail: fallo · stale: dato viejo. */
export type Pulse = "idle" | "live" | "ok" | "wait" | "fail" | "stale";
/** De dónde viene un dato (principios II y III). */
export type Source = "relay" | "git" | "github" | "declarado";

export interface PanelProps { title?: string; meta?: ReactNode; tone?: "normal" | "wait" | "fail"; children?: ReactNode; className?: string; }
export interface StatusPulseProps { state?: Pulse; label?: string | false; className?: string; }
export interface ProvenanceTagProps { source?: Source; age?: string; stale?: boolean; by?: string; className?: string; }
export interface ButtonProps { variant?: "ghost" | "primary" | "solid" | "danger"; busy?: boolean; disabled?: boolean; onClick?: () => void; children?: ReactNode; className?: string; }
export interface TaskCardProps {
  id: string; title: string; owner?: string;
  state?: "pendiente" | "reclamada" | "en_curso" | "en_revision" | "integrada" | "publicada" | "cerrada" | "parada" | "no_cerrada" | "fallo";
  source?: Source; age?: string; stale?: boolean; declaredBy?: string; action?: ReactNode; className?: string;
}
export interface CollisionAlertProps { severity?: "amarillo" | "rojo"; level?: 1 | 2 | 3; path: string; contract?: string; people?: string[]; age?: string; actions?: ReactNode; className?: string; }
export interface GraphNode { id: string; kind: "relay" | "github" | "person" | "orchestrator" | "worker"; x: number; y: number; label?: string; glyph?: string; state?: Pulse; }
export interface GraphEdge { id: string; from: string; to: string; channel?: "relay" | "github" | "local"; stale?: boolean; }
/** Un evento real que pasó por una arista. Cada id nuevo lanza un paquete una vez. */
export interface GraphEvent { id: string; edge: string; reverse?: boolean; }
export interface TeamGraphProps { nodes: GraphNode[]; edges: GraphEdge[]; events?: GraphEvent[]; width?: number; height?: number; packetMs?: number; label?: string; className?: string; }
