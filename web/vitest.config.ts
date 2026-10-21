import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    setupFiles: ["./src/lib/test/sesion.ts"],
    maxWorkers: 1,
    environment: "node",
    // Sin `*.spec.ts`: ahí viven las pruebas de Playwright (D7, tarea
    // 3.8), que usan su propio `test()` y rompen si vitest las corre.
    include: ["src/**/*.test.{ts,tsx}", "e2e/**/*.test.ts"],
  },
});
