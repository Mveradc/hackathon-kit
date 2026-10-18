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

/** Cómo está cubierta una nota de criterios.md. La calcula el OS; `pitch` es declarado y nunca cuenta como `cubierta`. */
export type Coverage = "sin_cubrir" | "planificada" | "en_curso" | "cubierta" | "pitch" | "corregida";
/** La etiqueta «(criterios: <fecha hora>)» en la fila de la tarea: declarada, con quién la puso y cuándo. */
export interface CriterioLink { cita: string; by?: string; age?: string; where?: string; }
export type CriterioItem =
  | { kind?: "tarea"; id: string; title: string; owner?: string; state?: TaskCardProps["state"]; source?: Source; age?: string; stale?: boolean;
      /** Una línea más, p. ej. «sin señales de @luis desde 10:35». */ note?: string;
      /** Publicada que volvió a en curso: «trabajo nuevo desde <since>». La nota sigue cubierta. */ since?: string;
      link?: CriterioLink; }
  | { kind: "evidencia"; path: string; sha: string; age?: string; };
export interface CriterioRowProps {
  time: string; who: string; where?: string;
  /** La fuerza tal como la anotó el equipo; `strengthKind` solo cambia el tono, no la puntúa. */
  strength?: string; strengthKind?: "dato" | "palabra" | "comentario" | "sin_precisar";
  said: string; affects?: string; corrects?: string; by?: string; age?: string;
  coverage?: Coverage; coverageLabel?: string; coverageStale?: boolean;
  items?: CriterioItem[]; pitch?: { by?: string; age?: string; where?: string }; hint?: string;
  children?: ReactNode; className?: string;
}

/** Una tarea de la ruta. Las posiciones van en la escala de `min`–`max` y llegan hechas en la vista. */
export interface CadenaRow {
  id: string; title: string; owner?: string;
  /** La franja declarada del plan, ya formateada: «sáb 02:30 → 11:00 · con T07». */ franja?: string;
  kind?: "hecha" | "curso" | "prevista" | "plazo_pasado" | "no_llega" | "vieja";
  from?: number; to?: number; /** Tramo estimado detrás del real (p. ej., lo que le queda a una en curso). */ est?: [number, number];
  /** Su «Hasta» en la misma escala. */ deadline?: number;
  /** Solo para layout="cajas": el estado en palabras. */ state?: string;
  label?: string; note?: string;
}
export interface CadenaMark { at: number; kind?: "ahora" | "hito" | "entrega"; label?: string; }
export interface CadenaEnd { from: number; to: number; at: number; tone?: "ok" | "wait" | "idle"; label: string; range?: string; title?: string; sub?: string; }
export interface CadenaProps {
  layout?: "linea" | "cajas"; rows: CadenaRow[]; min?: number; max?: number;
  ticks?: { at: number; label: string }[]; marks?: CadenaMark[]; end?: CadenaEnd; legend?: boolean;
  children?: ReactNode; className?: string;
}
