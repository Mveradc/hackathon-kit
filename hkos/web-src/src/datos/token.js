// Token local de la web (ADR-0010): llega en el fragmento (/#t=<token>), que el navegador no envía. Nada más leerlo se
// quita de la URL con history.replaceState y se devuelve para guardarlo solo en memoria (ni localStorage, ni
// sessionStorage, ni cookies). Al recargar, se vuelve a abrir con `hk-os web`.
export function tomarToken(w = window) {
  const frag = w.location.hash || "";
  const m = /^#(?:.*&)?t=([^&]*)/.exec(frag);
  if (!m) return null;
  w.history.replaceState(w.history.state, "", w.location.pathname + w.location.search);
  let t = m[1];
  try {
    t = decodeURIComponent(t);
  } catch {
    return null;
  }
  return t || null;
}
