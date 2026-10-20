/**
 * R3C-7 (rompedor 3b): `loading.tsx` reemplaza TODA la pantalla mientras
 * el segmento carga — ningún `page.tsx` lo anida dentro de
 * `ArmazonDelEdificio` (a diferencia de "cargando" en el flujo normal), así
 * que sin su propio `<main>`/`<h1>` el documento quedaba sin landmark
 * principal y sin encabezado de nivel 1. jsdom no corre esas reglas de
 * axe (son de documento completo); hace falta el navegador real.
 */

import { expect, test } from "@playwright/test";
import { sinViolacionesEnElNavegador } from "./accesibilidad";

const _LENTO = "00000000-0000-0000-0000-000000000002"; // escenarios.ts: "lento", responde a los 3s

test.describe("R3C-7 · estado de carga en el navegador real", () => {
  test("axe sin violaciones mientras se ve el esqueleto de /unidades", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(`/edificios/${_LENTO}/unidades`, { waitUntil: "commit" });
    await page.getByRole("status", { name: "Cargando" }).waitFor({ state: "visible" });
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await sinViolacionesEnElNavegador(page);
  });
});
