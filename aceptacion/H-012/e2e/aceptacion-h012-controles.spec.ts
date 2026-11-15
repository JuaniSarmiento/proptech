/**
 * Aceptación de H-012 · criterio de interfaz en navegador real (C08).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`). Los edificios de abajo son escenarios que la API
 * falsa tiene que conocer (ver `aceptacion/H-012/CONTRATO.md`, "API falsa"). Cada test primero espera la
 * pantalla con un `expect`. Los locators por nombre llevan `exact: true` y un `role="alert"` se filtra
 * por texto (L-085).
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";

const CON_CONTROLES = "00000000-0000-0000-0000-000000001201";
const SIN_CONTROLES = "00000000-0000-0000-0000-000000001101";

async function abrir(page: import("@playwright/test").Page, edificio: string) {
  await page.goto(`/edificios/${edificio}/liquidaciones/2026-11`);
  await expect(page.getByRole("heading", { name: "Preliquidación de noviembre de 2026" })).toBeVisible();
  const region = page.getByRole("region", { name: "Controles antes de emitir", exact: true });
  await expect(region).toBeVisible();
  return region;
}

test("C08 · cada control muestra su nivel en texto y su mensaje", async ({ page }) => {
  const region = await abrir(page, CON_CONTROLES);
  const items = region.getByRole("listitem");
  await expect(items).toHaveCount(3);
  await expect(items.nth(0)).toContainText("Duro");
  await expect(items.nth(0)).toContainText("Faltan validar los saldos iniciales del edificio");
  await expect(items.nth(1)).toContainText("Bloqueante");
  await expect(items.nth(1)).toContainText("Hay 1 factura leída con alertas");
  await expect(items.nth(2)).toContainText("Advertencia");
  await expect(items.nth(2)).toContainText("Hay 2 facturas sin cargar");
});

test("C08 · un control duro dice que no se puede aceptar y los otros no", async ({ page }) => {
  const region = await abrir(page, CON_CONTROLES);
  const items = region.getByRole("listitem");
  await expect(items.nth(0)).toContainText(/no se puede aceptar/i);
  await expect(items.nth(1)).not.toContainText(/no se puede aceptar/i);
  await expect(items.nth(2)).not.toContainText(/no se puede aceptar/i);
});

test("C08 · sin controles, la región dice que no hay pendientes", async ({ page }) => {
  const region = await abrir(page, SIN_CONTROLES);
  await expect(region.getByRole("listitem")).toHaveCount(0);
  await expect(region).toContainText(/no hay controles pendientes/i);
});

test("C08 · a 320 px sin scroll horizontal y sin errores de axe", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  const region = await abrir(page, CON_CONTROLES);
  await expect(region.getByRole("listitem")).toHaveCount(3);
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
});
