// Las dos acciones de M9a (api.md §4, ADR-0010), solo a tu demonio: JSON, X-HK-Token y nada en la query. El demonio
// valida y decide; la web solo dice lo que ha contestado.
export async function accion(fetchImpl, token, ruta, cuerpo) {
  let r;
  try {
    r = await fetchImpl(ruta, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-HK-Token": token },
      body: JSON.stringify(cuerpo),
      cache: "no-store",
    });
  } catch {
    return { ok: false, status: 0, datos: {} };
  }
  let datos = {};
  try {
    datos = await r.json();
  } catch {
    /* sin cuerpo JSON */
  }
  return { ok: r.ok, status: r.status, datos: datos || {} };
}

function comun(status, datos) {
  if (status === 0) return "Tu demonio no responde.";
  if (status === 401) return "El token no vale: vuelve a abrir la web con hk-os web.";
  if (status === 403) return "Tu demonio ha rechazado la petición (Host u Origin ajenos).";
  if (status === 413) return "Demasiado largo para tu demonio (4 KB como mucho).";
  if (status === 415) return "Tu demonio solo acepta JSON.";
  return `Tu demonio ha contestado ${status}${datos.error ? `: ${datos.error}` : ""}.`;
}

export function textoReclamar(tarea, { ok, status, datos }) {
  if (ok) {
    return datos.issue != null
      ? `${tarea} es tuya. Issue #${datos.issue} asignado con tu gh; tu monitor abre un turno con un texto fijo.`
      : `${tarea} es tuya (sin issue: solo el evento). Tu monitor abre un turno con un texto fijo.`;
  }
  if (status === 404) return `${tarea} no existe en el estado de tu demonio.`;
  if (status === 409) return datos.error ? `No se puede reclamar ${tarea}: ${datos.error}.` : `${tarea} no está libre o es de otra persona.`;
  if (status === 429) return "Has llegado al tope de reclamos por hora.";
  if (status === 502) return `gh ha fallado${datos.error ? `: ${datos.error}` : ""}. No se ha asignado nada.`;
  if (status === 503 && datos.error === "ocupado") return "Tu demonio está terminando otra acción; prueba en unos segundos.";
  return comun(status, datos);
}

export function textoAnotar({ ok, status, datos }) {
  if (ok) return `Anotado en criterios.md de main${datos.sha ? ` (${String(datos.sha).slice(0, 7)})` : ""}. Tu copia no cambia: llegará con tu próximo git pull.`;
  if (status === 400) return `No vale${datos.campo ? ` «${datos.campo}»` : ""}${datos.error ? `: ${datos.error}` : ""}.`;
  if (status === 409) return "Otra nota se subió a la vez, también al reintentar. Tu copia no ha cambiado: prueba otra vez o usa /hack-note.";
  if (status === 502) return `git ha fallado${datos.error ? `: ${datos.error}` : ""}. Tu copia no ha cambiado.`;
  return comun(status, datos);
}
