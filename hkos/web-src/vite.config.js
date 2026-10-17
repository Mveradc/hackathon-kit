import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// El compilado se sube al repo (hkos/web/nueva/) y lo sirve el demonio en / y /assets/ (api.md §4): rutas absolutas,
// todo en assets/ (sin subcarpetas) y ninguna URL externa (principios VII y VIII).
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: fileURLToPath(new URL("../web/nueva", import.meta.url)),
    emptyOutDir: true,
    assetsDir: "assets",
    assetsInlineLimit: 0,
    sourcemap: false,
    modulePreload: { polyfill: false },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./test/setup.js"],
    include: ["test/**/*.test.{js,jsx}"],
  },
});
