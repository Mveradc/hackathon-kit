import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./estilos/fuentes.css";
import "./estilos/tokens.css";
import "./estilos/componentes.css";
import "./estilos/app.css";
import { App } from "./App.jsx";
import { tomarToken } from "./datos/token.js";

// El token se toma del fragmento y se quita de la URL antes de pintar nada; vive solo en esta variable (ADR-0010).
const token = tomarToken(window);
const fetchImpl = window.fetch.bind(window);

createRoot(document.getElementById("raiz")).render(
  <StrictMode>
    <App token={token} fetchImpl={fetchImpl} />
  </StrictMode>,
);
