/**
 * Navegador real (D7, tarea 3.8): SÓLO Chromium — una sola instancia menos
 * que mantener, y el DESIGN.md pide un sistema, no tres. `test-web-
 * navegador.sh` arma `next build`, levanta la API falsa y `next start`
 * antes de correr esto; acá sólo se declara contra qué URL.
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Sólo `*.spec.ts`: `*.test.ts` son las pruebas de vitest de este mismo
  // directorio (p.ej. `api-falsa.test.ts`), que usan `describe`/`it` y no
  // el `test` de Playwright.
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.PROPTECH_URL_WEB ?? "http://127.0.0.1:3100",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
