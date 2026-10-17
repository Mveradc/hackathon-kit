// Criterio 2 de M9a, lo que se puede comprobar sin el demonio: el compilado de hkos/web/nueva/ es lo que sirve el
// demonio (index.html en / y ficheros sueltos en assets/, con los tipos de api.md §4) y no carga nada de fuera.
// Uso (desde hkos/web-src, tras `npm run build`): node scripts/comprueba_compilado.mjs   (0 bien · 1 mal)
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const NUEVA = fileURLToPath(new URL("../../web/nueva/", import.meta.url));
const NOMBRE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;              // la lista blanca de /assets/<fichero> del demonio
const TIPOS = new Set([".js", ".css", ".woff2", ".svg", ".png"]);
// Cadenas con URL que no son cargas: los espacios de nombres de XML/SVG/MathML que usa react-dom y el enlace de sus
// mensajes de error minificados. Ninguna se pide por la red.
const PERMITIDAS = [/^http:\/\/www\.w3\.org\/(1998\/Math\/MathML|1999\/xlink|2000\/svg|XML\/1998\/namespace)$/, /^https:\/\/react\.dev\/errors\/$/];

const fallos = [];
const mal = (m) => fallos.push(m);

for (const f of readdirSync(NUEVA)) {
  if (f === "index.html" || f === ".gitattributes") continue;
  if (f !== "assets") mal(`fichero que el demonio no sirve: ${f}`);
}
const assets = readdirSync(join(NUEVA, "assets"));
for (const f of assets) {
  const ext = f.slice(f.lastIndexOf(".")).toLowerCase();
  if (statSync(join(NUEVA, "assets", f)).isDirectory()) mal(`subcarpeta en assets/: ${f}`);
  else if (!NOMBRE.test(f)) mal(`nombre que el demonio no sirve: assets/${f}`);
  else if (!TIPOS.has(ext)) mal(`tipo que el demonio no sirve: assets/${f}`);
}

const html = readFileSync(join(NUEVA, "index.html"), "utf-8");
for (const [, ruta] of html.matchAll(/\s(?:src|href)="([^"]*)"/g)) {
  const m = /^\/assets\/([^/]+)$/.exec(ruta);
  if (!m || !assets.includes(m[1])) mal(`index.html carga algo que no está en assets/: ${ruta}`);
}
if (/<script(?![^>]*\ssrc=)[^>]*>/.test(html)) mal("index.html lleva un <script> en línea (la CSP del demonio no lo deja)");

for (const f of ["index.html", ...assets.filter((x) => /\.(js|css|svg)$/.test(x)).map((x) => `assets/${x}`)]) {
  const texto = readFileSync(join(NUEVA, f), "utf-8");
  for (const [url] of texto.matchAll(/https?:\/\/[^\s"'`)\\<>]*/g)) {
    if (!PERMITIDAS.some((r) => r.test(url))) mal(`URL externa en ${f}: ${url}`);
  }
  for (const [, u] of texto.matchAll(/url\(\s*["']?([^"')]+)/g)) {
    if (!u.startsWith("/assets/") && !u.startsWith("data:")) mal(`url() que no es de assets/ en ${f}: ${u}`);
  }
  if (/@import/.test(texto)) mal(`@import en ${f}`);
}

for (const fam of ["ibm-plex-sans", "jetbrains-mono", "space-grotesk"]) {
  if (!assets.some((x) => x.startsWith(fam) && x.endsWith(".woff2"))) mal(`falta la fuente ${fam} en assets/`);
}

if (fallos.length) {
  for (const f of fallos) console.error(`FALLO ${f}`);
  process.exit(1);
}
console.log(`OK    hkos/web/nueva: index.html y ${assets.length} ficheros en assets/, sin URL externas`);
