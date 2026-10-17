// Formato de lo que trae la vista (ADR-0009): la web agrupa, filtra y formatea «hace X» con `servido_en` y el
// `observado_en` de cada dato. Nada de aquí calcula estados, columnas, colisiones, «viejo» ni confirmaciones.

// Las horas de estado.json llevan microsegundos (`…:11.123456Z`): Date.parse no está obligado a aceptarlos.
export function ms(iso) {
  if (!iso) return NaN;
  return Date.parse(String(iso).replace(/(\.\d{3})\d+/, "$1"));
}

/** «hace X» de un dato respecto de la hora a la que el demonio sirvió la vista (no la del dispositivo). */
export function hace(observado, servido) {
  const s = Math.max(0, Math.floor((ms(servido) - ms(observado)) / 1000));
  if (!Number.isFinite(s)) return "";
  if (s < 60) return `hace ${s} s`;
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  if (s < 86400) return `hace ${Math.floor(s / 3600)} h`;
  return `hace ${Math.floor(s / 86400)} d`;
}

function dos(n) {
  return String(n).padStart(2, "0");
}

/** HH:MM en la hora local del portátil (como estado-equipo.md). */
export function hora(iso) {
  const d = new Date(ms(iso));
  return Number.isNaN(d.getTime()) ? "" : `${dos(d.getHours())}:${dos(d.getMinutes())}`;
}

/** HH:MM:SS de un instante del reloj local (la última vez que la web recibió algo del demonio). */
export function horaLocal(t) {
  const d = new Date(t);
  return `${dos(d.getHours())}:${dos(d.getMinutes())}:${dos(d.getSeconds())}`;
}

export const arroba = (p) => (p ? `@${p}` : "sin dueño");

// Color por procedencia (sistema/README.md, principio 1): de qué canal viene cada `fuente` de estado.schema.json.
// La palabra que se pinta es siempre la fuente real; esto solo elige el color.
const CANAL = {
  hook: "relay", demonio: "relay",
  git: "git", orquestador: "git", compuerta: "git", derivado: "git",
  github: "github",
  mcp: "declarado", web: "declarado", humano: "declarado",
};
export const canal = (fuente) => CANAL[fuente] || "git";

// Estado de tarea (identificador de la vista) → latido del sistema. La palabra es la `etiqueta` de la vista.
const PULSO = {
  pendiente: "idle", lista: "idle", reclamada: "idle", en_curso: "live", en_revision: "live",
  integrada: "ok", publicada: "ok", cerrada: "ok", parada: "wait", no_cerrada: "wait",
};
export const pulsoDe = (estado) => PULSO[estado] || "idle";

// Etiqueta legible de un estado que la vista da solo como identificador (el `declarado` a mano y el de las
// dependencias de `espera`): la misma tabla que proyeccion.ETIQUETAS, para que diga lo mismo que estado-equipo.md.
export const ETIQUETAS = {
  pendiente: "pendiente", lista: "lista", reclamada: "reclamada", en_curso: "en curso", parada: "parada",
  en_revision: "en revisión", integrada: "integrada (sin subir)", no_cerrada: "no cerrada", publicada: "publicada",
  cerrada: "cerrada",
};

// «Tu trabajo» (api.md §6): el orden de proyeccion.TRABAJO; publicada y cerrada ya no son trabajo.
export const TRABAJO = ["en_curso", "parada", "no_cerrada", "en_revision", "reclamada", "integrada", "lista", "pendiente"];

export function tarjetas(vista) {
  const c = vista?.columnas || {};
  return [...(c.haciendo || []), ...(c.hecho || []), ...(c.falta || [])];
}

export function trabajoDe(vista, persona) {
  return tarjetas(vista)
    .filter((t) => t.dueno === persona && TRABAJO.includes(t.estado))
    .sort((a, b) => TRABAJO.indexOf(a.estado) - TRABAJO.indexOf(b.estado) || a.id.localeCompare(b.id));
}

export const DESAJUSTE = {
  puerto_sin_respuesta: ["wait", "No responde"],
  salud_falla: ["fail", "La salud falla"],
  formato_invalido: ["fail", "Formato no válido"],
  codigo_fuera: ["wait", "Código sin servicio"],
  prueba_falla: ["fail", "La prueba falla"],
  dueno_distinto: ["wait", "Dueño distinto"],
  contrato_inexistente: ["fail", "Contrato inexistente"],
};

/** Lo de servicios que afecta a una persona: el mismo filtro de campos que proyeccion.servicios_de (api.md §6). */
export function serviciosDe(vista, persona) {
  const s = vista?.servicios;
  if (!s) return { noCuadra: [], sinConfirmar: [], propuestas: [], fuera: [] };
  const noCuadra = [], fuera = [];
  for (const d of s.desajustes) {
    if (d.tipo === "codigo_fuera") fuera.push(d);
    else if (!d.personas?.length || d.personas.includes(persona)) noCuadra.push(d);
  }
  const filas = [
    ...s.lista.map((x) => ({ tipo: "servicio", nombre: x.nombre, x })),
    ...s.conexiones.map((x) => ({ tipo: "conexión", nombre: `${x.de} → ${x.a}`, x })),
  ];
  const sinConfirmar = filas.filter(
    ({ x }) => x.confirmacion.valor === "sin_confirmar" && x.confirmacion.faltan.includes(persona));
  const propuestas = s.propuestas.filter((p) => (p.duenos || []).includes(persona) && p.autor_git !== persona);
  return { noCuadra, sinConfirmar, propuestas, fuera };
}

export function nombrePropuesta(p) {
  const c = p.campos || {};
  return p.tipo === "servicio" ? `servicio «${c.nombre || ""}»` : `conexión «${c.de || ""} → ${c.a || ""}»`;
}

export function autorPropuesta(p) {
  return p.autor_git ? `@${p.autor_git}` : p.autor_declarado || "sin autor";
}
