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

// --- M10: jurado y ruta (ADR-0012, ADR-0013). Solo formato: las horas llegan resueltas en la vista y aquí se escriben
// en la zona de equipo.md; nada de cobertura, orden, rangos, veredicto ni «viejo».

const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];       // los de ruta.DIAS, en el orden de getUTCDay

/** Desfase en minutos de una hora ISO con zona («…+02:00» → 120, «…Z» → 0), o null. */
function desfase(iso) {
  const m = /(Z|([+-])(\d\d):(\d\d))$/.exec(iso || "");
  if (!m) return null;
  return m[1] === "Z" ? 0 : (m[2] === "-" ? -1 : 1) * (Number(m[3]) * 60 + Number(m[4]));
}

/** La zona de las horas de jurado y ruta, la misma con la que ruta.py escribe el resumen (ruta._zona): el desfase de la
 *  entrega de equipo.md; sin ella, el de la primera nota con hora (las resuelve el relay con la zona de equipo.md); si
 *  no, UTC. En minutos. */
export function zonaM10(vista) {
  const candidatas = [vista?.ruta?.objetivo?.valor, ...(vista?.jurado?.notas || []).map((x) => x.nota.hora)];
  for (const h of candidatas) {
    const d = desfase(h);
    if (h && d != null) return d;
  }
  return 0;
}

/** La zona de las horas de un bloque (issue #56): su `zona.valor` de la vista, un desfase «±HH:MM» (en minutos) o un
 *  nombre IANA («Europe/Madrid», que el navegador sabe pasar a cada hora con su horario de verano); sin ella o si no se
 *  entiende, la de zonaM10, como antes. */
function zonaDe(bloque, vista) {
  const v = vista?.[bloque]?.zona?.valor;
  const m = /^([+-])(\d\d):(\d\d)$/.exec(v || "");
  if (m) return (m[1] === "-" ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]));
  return v && formatoIana(v) ? v : zonaM10(vista);
}
export const zonaRuta = (vista) => zonaDe("ruta", vista);
/** La del jurado (issue #63), igual que la de la ruta con `jurado.zona`: las dos pantallas dicen la misma hora. */
export const zonaJurado = (vista) => zonaDe("jurado", vista);

// Controles bidi (U+202A–U+202E, U+2066–U+2069): un texto de un fichero del equipo podría reordenar lo que se ve
// detrás de él (issue #63). Se quitan de todo lo que llega del demonio antes de pintarlo.
const BIDI = /[\u202A-\u202E\u2066-\u2069]/g;
export const quitaBidi = (s) => s.replace(BIDI, "");
export function sinBidi(x) {
  if (typeof x === "string") return quitaBidi(x);
  if (Array.isArray(x)) return x.map(sinBidi);
  if (x && typeof x === "object") return Object.fromEntries(Object.entries(x).map(([k, v]) => [quitaBidi(k), sinBidi(v)]));
  return x;
}

const IANA = new Map();
function formatoIana(nombre) {
  if (!IANA.has(nombre)) {
    let f = null;
    try {
      f = new Intl.DateTimeFormat("en-US", { timeZone: nombre, hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric" });
    } catch { /* nombre que el navegador no conoce */ }
    IANA.set(nombre, f);
  }
  return IANA.get(nombre);
}

/** Minutos de desfase de la zona (minutos fijos o un nombre IANA) en el instante t (ms). */
export function minutosZona(zona, t) {
  if (typeof zona === "number") return zona;
  const p = Object.fromEntries(formatoIana(zona).formatToParts(new Date(t)).map((x) => [x.type, x.value]));
  const local = Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), Number(p.hour), Number(p.minute));
  return Math.round((local - Math.floor(t / 60000) * 60000) / 60000);
}

export function textoZona(min) {
  if (typeof min === "string") return min;
  const a = Math.abs(min);
  return `UTC${min < 0 ? "−" : "+"}${dos(Math.floor(a / 60))}:${dos(a % 60)}`;
}

function partes(iso, zona) {
  const t = ms(iso);
  if (!Number.isFinite(t)) return null;
  const d = new Date(t + minutosZona(zona, t) * 60000);
  return { dia: DIAS[d.getUTCDay()], n: d.getUTCDate(), hm: `${dos(d.getUTCHours())}:${dos(d.getUTCMinutes())}` };
}

/** «02:30» en la zona de equipo.md. */
export const hm = (iso, zona) => partes(iso, zona)?.hm ?? "";
/** «sáb 02:30». */
export const diaHm = (iso, zona) => { const p = partes(iso, zona); return p ? `${p.dia} ${p.hm}` : ""; };
/** «sáb 19 · 02:30». */
export const fechaHm = (iso, zona) => { const p = partes(iso, zona); return p ? `${p.dia} ${p.n} · ${p.hm}` : ""; };

/** Minutos de la vista (el margen) escritos como «+15 h 30» o «−0 h 40». */
export function duracion(min) {
  const a = Math.abs(min);
  return `${min < 0 ? "−" : "+"}${Math.floor(a / 60)} h ${dos(a % 60)}`;
}

/** Quién propone, como proyeccion.autor_propuesta: la persona del commit; sin ella, el Autor de la fila, declarado
 *  (decisión 3A del PR #13). */
export function autorPropuesta(p) {
  if (p.autor_git) return `@${p.autor_git}`;
  return p.autor_declarado ? `${p.autor_declarado} (declarado)` : "sin autor";
}
