import { useCallback, useEffect, useState } from "react";
import { accion, textoAnotar, textoReclamar } from "./datos/acciones.js";
import { useDemonio } from "./datos/demonio.js";
import { horaLocal } from "./formato.js";
import { Cabina } from "./vistas/Cabina.jsx";
import { Fuentes } from "./vistas/comun.jsx";
import { Red } from "./vistas/Red.jsx";
import { Servicios } from "./vistas/Servicios.jsx";
import { Tablero } from "./vistas/Tablero.jsx";

const VISTAS = [["cabina", "Cabina"], ["red", "Red"], ["tablero", "Tablero"], ["servicios", "Servicios"]];

function temaInicial() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function Portada({ children }) {
  return <main className="hk-app"><div className="hk-portada"><span className="hk-producto">Hackathon OS</span>{children}</div></main>;
}

/** `token`: el de /#t=, solo en memoria. `fetchImpl`: el fetch del navegador (los tests pasan un demonio falso). */
export function App({ token, fetchImpl }) {
  const [vista, setVista] = useState("cabina");
  const [tema, setTema] = useState(temaInicial);
  const [ocupado, setOcupado] = useState(null);
  const [aviso, setAviso] = useState(null);
  const d = useDemonio({ token, fetchImpl });

  useEffect(() => {
    document.documentElement.dataset.theme = tema;
  }, [tema]);

  const reclamar = useCallback(async (tarea) => {
    if (ocupado) return;
    setOcupado(tarea);
    const r = await accion(fetchImpl, token, "/v1/reclamar", { tarea });
    setAviso({ ok: r.ok, texto: textoReclamar(tarea, r) });
    setOcupado(null);
  }, [fetchImpl, token, ocupado]);

  const anotar = useCallback(async (cuerpo) => {
    const r = await accion(fetchImpl, token, "/v1/anotar", cuerpo);
    return { ok: r.ok, texto: textoAnotar(r) };
  }, [fetchImpl, token]);

  if (!token) {
    return (
      <Portada>
        <p className="hk-texto">Esta web la abre tu demonio con su token: ejecuta <code>hk-os web</code> en tu clon.</p>
        <p className="hk-texto-sec">El token va en la URL solo al abrirla y la página lo quita enseguida; al recargar, vuelve a abrirla con <code>hk-os web</code>.</p>
      </Portada>
    );
  }
  if (d.fallo === "token") {
    return <Portada><p className="hk-texto" role="alert">Tu demonio no acepta este token. Vuelve a abrir la web con <code>hk-os web</code>.</p></Portada>;
  }

  const banda = d.sinConexion ? (
    <div className="hk-sinconexion" role="alert" data-sin-conexion="">
      <strong>Sin conexión con tu demonio.</strong>
      <span>Último dato a las {d.ultimo ? horaLocal(d.ultimo) : "—"}. Lo de abajo es de entonces.</span>
    </div>
  ) : null;

  if (!d.respuesta) {
    return (
      <Portada>
        {banda}
        <p className="hk-texto" role="status">
          {d.fallo === "sin estado" ? "Tu demonio aún no tiene estado del equipo (¿está unido al relay?)." : "Conectando con tu demonio…"}
        </p>
      </Portada>
    );
  }

  const reclamo = { reclamar, ocupado, aviso };
  const props = { respuesta: d.respuesta, eventos: d.eventos, sinConexion: d.sinConexion, reclamo, anotar };
  const Vista = { cabina: Cabina, red: Red, tablero: Tablero, servicios: Servicios }[vista];

  return (
    <main className={`hk-app${d.sinConexion ? " is-offline" : ""}`} data-sin-conexion={d.sinConexion ? "si" : "no"}>
      <div className="hk-app__marco">
        <header className="hk-cabecera">
          <div className="hk-cabecera__izq">
            <span className="hk-producto">Hackathon OS</span>
            <span className="hk-sub">@{d.respuesta.persona}{d.modo === "sondeo" ? " · sin stream, pidiendo cada 3 s" : ""}</span>
          </div>
          <div className="hk-cabecera__der">
            <Fuentes respuesta={d.respuesta} />
            <nav className="hk-nav" aria-label="Vistas">
              {VISTAS.map(([k, t]) => (
                <button key={k} type="button" aria-current={vista === k ? "page" : undefined} onClick={() => setVista(k)}>{t}</button>
              ))}
            </nav>
            <button type="button" className="hk-tema" onClick={() => setTema(tema === "dark" ? "light" : "dark")}>
              {tema === "dark" ? "Tema claro" : "Tema oscuro"}
            </button>
          </div>
        </header>
        {banda}
        <div className="hk-app__contenido">
          <Vista {...props} />
        </div>
      </div>
    </main>
  );
}
