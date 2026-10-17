import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// Tema oscuro y claro con los tokens de docs/hackathon-os/diseno-web/sistema/tokens.json: la copia de tokens.css que
// compila la web tiene que llevar cada color y cada sombra con su valor en los dos temas.
const AQUI = dirname(fileURLToPath(import.meta.url));
const tokens = JSON.parse(readFileSync(join(AQUI, "../../../docs/hackathon-os/diseno-web/sistema/tokens.json"), "utf-8"));
const css = readFileSync(join(AQUI, "../src/estilos/tokens.css"), "utf-8");

function bloque(selector) {
  const i = css.indexOf(selector);
  return css.slice(i, css.indexOf("}", i));
}

describe("tokens", () => {
  const temas = { dark: bloque(':root, [data-theme="dark"]'), light: bloque('[data-theme="light"]') };
  for (const t of [...tokens.color.tokens, ...tokens.shadow.tokens]) {
    it(`${t.name} en oscuro y claro`, () => {
      for (const [tema, b] of Object.entries(temas)) expect(b).toContain(`--${t.name}: ${t.value[tema]};`);
    });
  }
  it("espaciado, radios y familias", () => {
    for (const t of [...tokens.spacing.tokens, ...tokens.radius.tokens]) expect(css).toContain(`--${t.name}: ${t.value};`);
    for (const [k, v] of Object.entries(tokens.type.families)) expect(css).toContain(`--font-${k}: ${v};`);
  });
});
