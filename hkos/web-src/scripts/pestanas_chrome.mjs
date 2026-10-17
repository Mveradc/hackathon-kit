// Issue #15, de punta a punta: N pestañas (9 por defecto) de Chrome headless contra un demonio de verdad
// (scripts/demonio_prueba.py, en un repo temporal). Comprueba que:
//   1. todas las pestañas pintan la web (Chrome abre como mucho 6 conexiones por host: antes, la 7.ª ni cargaba);
//   2. el demonio tiene un solo cliente de /v1/stream, y lo sigue teniendo tras varios ping;
//   3. lo que manda el demonio después (una novedad nueva) llega a todas;
//   4. al cerrar pestañas, empezando por la primera (la que cogió el cerrojo), otra coge el relevo: sigue habiendo un
//      solo cliente y lo nuevo sigue llegando a las que quedan.
// Uso (desde hkos/web-src, tras `npm run build`): node scripts/pestanas_chrome.mjs [--pestanas N] [--web DIR]
//   CHROME=<ruta> si Chrome no está en su sitio de siempre. Sale con 0 si todo va bien y 1 si no.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const WEB_SRC = fileURLToPath(new URL("..", import.meta.url));
const { values: op } = parseArgs({ options: { pestanas: { type: "string", default: "9" }, web: { type: "string" } } });
const N = Number(op.pestanas);
const PING_S = 2;
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

function chrome() {
  const candidatos = [process.env.CHROME,
    "C:/Program Files/Google/Chrome/Application/chrome.exe", "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  const c = candidatos.find((x) => x && existsSync(x));
  if (!c) throw new Error("no encuentro Chrome: pon su ruta en CHROME");
  return c;
}

async function hasta(desc, fn, ms = 20_000) {
  const fin = Date.now() + ms;
  let ultimo;
  while (Date.now() < fin) {
    ultimo = await fn();
    if (ultimo === true) return;
    await dormir(200);
  }
  throw new Error(`${desc}: ${JSON.stringify(ultimo)}`);
}

function cdp(url) {
  const ws = new WebSocket(url);
  let n = 0;
  const pendientes = new Map();
  ws.addEventListener("message", ({ data }) => {
    const m = JSON.parse(data);
    const p = pendientes.get(m.id);
    if (!p) return;
    pendientes.delete(m.id);
    if (m.error) p.rechaza(new Error(`${p.metodo}: ${m.error.message}`));
    else p.resuelve(m.result);
  });
  const abierto = new Promise((r, e) => { ws.addEventListener("open", r); ws.addEventListener("error", e); });
  return {
    abierto,
    manda: (metodo, params = {}, sessionId) => new Promise((resuelve, rechaza) => {
      const id = ++n;
      pendientes.set(id, { resuelve, rechaza, metodo });
      ws.send(JSON.stringify({ id, method: metodo, params, ...(sessionId ? { sessionId } : {}) }));
    }),
    cierra: () => ws.close(),
  };
}

const fallos = [];
const bien = (m) => console.log(`OK    ${m}`);
const mal = (m) => { fallos.push(m); console.error(`FALLO ${m}`); };

const demonio = spawn("uv", ["run", "--no-project", "scripts/demonio_prueba.py", "--ping", String(PING_S),
  ...(op.web ? ["--web", op.web] : [])], { cwd: WEB_SRC, stdio: ["pipe", "pipe", "inherit"] });
const perfil = mkdtempSync(join(tmpdir(), "hk-chrome-"));
let navegador = null, c = null;

try {
  const datos = await new Promise((resuelve, rechaza) => {
    let buf = "";
    demonio.stdout.on("data", (b) => {
      buf += b;
      const i = buf.indexOf("\n");
      if (i >= 0) resuelve(JSON.parse(buf.slice(0, i)));
    });
    demonio.on("exit", (code) => rechaza(new Error(`el demonio de prueba salió con ${code}`)));
  });
  const base = `http://127.0.0.1:${datos.puerto}`;
  const clientes = async () => Number(await (await fetch(`http://127.0.0.1:${datos.control}/clientes`)).text());
  const marca = (texto) => fetch(`http://127.0.0.1:${datos.control}/marca?texto=${encodeURIComponent(texto)}`, { method: "POST" });

  navegador = spawn(chrome(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${perfil}`, "--no-first-run",
    "--no-default-browser-check", "--disable-extensions", "about:blank"], { stdio: "ignore" });
  const activo = join(perfil, "DevToolsActivePort");
  await hasta("Chrome no abre el puerto de depuración", () => existsSync(activo) && readFileSync(activo, "utf-8").includes("\n"));
  const [puertoCdp, ruta] = readFileSync(activo, "utf-8").trim().split("\n");
  c = cdp(`ws://127.0.0.1:${puertoCdp}${ruta.trim()}`);
  await c.abierto;

  const pestanas = [];
  for (let i = 0; i < N; i++) {
    const { targetId } = await c.manda("Target.createTarget", { url: `${base}/#t=${datos.token}` });
    const { sessionId } = await c.manda("Target.attachToTarget", { targetId, flatten: true });
    pestanas.push({ i: i + 1, targetId, sessionId });
  }
  const evalua = async (p, expr) => {
    try {
      const r = await c.manda("Runtime.evaluate", { expression: expr, returnByValue: true }, p.sessionId);
      return r.result?.value;
    } catch (e) {
      return `error: ${e.message}`;
    }
  };
  const estado = (p) => evalua(p, `({host: location.host, sub: document.querySelector(".hk-sub")?.textContent || "",
    texto: document.body?.innerText || ""})`);
  const pintan = async (vivas, texto) => {
    const r = await Promise.all(vivas.map(estado));
    const no = vivas.filter((p, k) => !(r[k]?.sub?.includes("@persona-a") && (!texto || r[k].texto.includes(texto))));
    return no.length ? `no pintan${texto ? ` «${texto}»` : ""}: ${no.map((p) => `#${p.i} (${JSON.stringify((r[vivas.indexOf(p)] || {}).host)})`).join(", ")}` : true;
  };

  // 1 y 2. Todas pintan y el demonio tiene un solo stream.
  try {
    await hasta(`${N} pestañas`, () => pintan(pestanas));
    bien(`las ${N} pestañas pintan la web (@persona-a)`);
  } catch (e) {
    mal(e.message);
  }
  for (let k = 0; k < 3; k++) {
    await dormir(PING_S * 1000 + 300);
    const n = await clientes();
    if (n !== 1) mal(`tras ${k + 1} ping, el demonio tiene ${n} clientes de /v1/stream (debe ser 1)`);
  }
  if (!fallos.length) bien(`el demonio tiene 1 cliente de /v1/stream con ${N} pestañas, también tras 3 ping`);

  // 3. Lo nuevo llega a todas.
  await marca("marca-0");
  try {
    await hasta("la novedad nueva", () => pintan(pestanas, "marca-0"), 10_000);
    bien(`una novedad nueva del demonio llega a las ${N} pestañas`);
  } catch (e) {
    mal(e.message);
  }

  // 4. Relevo: se cierran las tres primeras, una a una.
  let vivas = [...pestanas];
  for (let k = 1; k <= 3 && !fallos.length; k++) {
    const p = vivas.shift();
    await c.manda("Target.closeTarget", { targetId: p.targetId });
    try {
      // El demonio solo nota que la pestaña cerrada se ha ido al escribirle (el siguiente ping).
      await hasta(`tras cerrar #${p.i}, un solo cliente`, async () => (await clientes()) === 1 || `clientes: ${await clientes()}`, 15_000);
      await dormir(PING_S * 1000 + 300);
      const n = await clientes();
      if (n !== 1) throw new Error(`tras cerrar #${p.i}, el demonio tiene ${n} clientes`);
      await marca(`marca-${k}`);
      await hasta(`tras cerrar #${p.i}`, () => pintan(vivas, `marca-${k}`), 10_000);
      bien(`cerrada la pestaña #${p.i}: 1 cliente y las ${vivas.length} que quedan reciben lo nuevo`);
    } catch (e) {
      mal(e.message);
    }
  }
} catch (e) {
  mal(e.message);
} finally {
  c?.cierra();
  navegador?.kill();
  demonio.stdin.end();
  await dormir(500);
  demonio.kill();
  try {
    rmSync(perfil, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 });
  } catch {
    /* Chrome aún suelta ficheros del perfil en Windows: el temporal se queda */
  }
}
if (fallos.length) process.exit(1);
console.log(`OK    ${N} pestañas, un solo /v1/stream`);
