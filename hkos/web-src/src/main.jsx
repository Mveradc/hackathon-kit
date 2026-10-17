import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./estilos/fuentes.css";
import "./estilos/tokens.css";
import "./estilos/componentes.css";
import "./estilos/app.css";
import { App } from "./App.jsx";
import { pestanasDelNavegador } from "./datos/demonio.js";
import { tomarToken } from "./datos/token.js";

// El token se toma del fragmento y se quita de la URL antes de pintar nada; vive solo en esta variable (ADR-0010).
const token = tomarToken(window);
const fetchImpl = window.fetch.bind(window);
// Un solo /v1/stream por navegador y origen (issue #15); sin navigator.locks o BroadcastChannel, uno por pestaña.
const pestanas = pestanasDelNavegador(window);

createRoot(document.getElementById("raiz")).render(
  <StrictMode>
    <App token={token} fetchImpl={fetchImpl} pestanas={pestanas} />
  </StrictMode>,
);
