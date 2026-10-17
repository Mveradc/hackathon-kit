// Lector de text/event-stream por trozos (el stream se lee con fetch y un ReadableStream: EventSource no admite la
// cabecera X-HK-Token, ADR-0010). Devuelve una función a la que se le pasan los trozos de texto según llegan; llama a
// `alMensaje({event, data, id})` por cada mensaje completo. Ignora los comentarios («: …»).
export function lectorSSE(alMensaje) {
  let resto = "";
  return (trozo) => {
    resto += trozo.replace(/\r\n?/g, "\n");
    let i;
    while ((i = resto.indexOf("\n\n")) >= 0) {
      const bloque = resto.slice(0, i);
      resto = resto.slice(i + 2);
      let event = "message", id = null;
      const datos = [];
      for (const linea of bloque.split("\n")) {
        if (!linea || linea.startsWith(":")) continue;
        const p = linea.indexOf(":");
        const campo = p < 0 ? linea : linea.slice(0, p);
        let valor = p < 0 ? "" : linea.slice(p + 1);
        if (valor.startsWith(" ")) valor = valor.slice(1);
        if (campo === "event") event = valor;
        else if (campo === "data") datos.push(valor);
        else if (campo === "id") id = valor;
      }
      if (datos.length || event !== "message") alMensaje({ event, data: datos.join("\n"), id });
    }
  };
}
