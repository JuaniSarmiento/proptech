/**
 * Aceptación de H-014 · criterio de interfaz en navegador real (C09).
 *
 * Corre contra la API falsa, con los escenarios de `aceptacion/H-014/CONTRATO.md` ("API falsa"). Locators
 * exactos y alertas filtradas por texto (L-085).
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EMITIDA = "00000000-0000-0000-0000-000000001401";
const DISTRIBUIDA = "00000000-0000-0000-0000-000000001402";
const LIQUIDACION_EMITIDA = "00000000-0000-0000-0000-000000014011";
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function abrir(page: import("@playwright/test").Page, edificio: string, estado: string) {
  await page.goto(`/edificios/${edificio}/liquidaciones/2026-11`);
  await expect(page.getByText(estado, { exact: true }).first()).toBeVisible();
  await expect(page.getByText("191.500,00").first()).toBeVisible();
}

function confirmacion(page: import("@playwright/test").Page) {
  return page.getByRole("dialog").or(page.getByRole("alertdialog"));
}

async function ultimaEscritura(request: import("@playwright/test").APIRequestContext) {
  const r = await request.get(`${baseApi}/api/__debug/ultima-escritura`, { headers: cabecerasDePrueba() });
  expect(r.ok()).toBe(true);
  return r.json();
}

test("C09 · una emitida muestra su estado y se distribuye con confirmación", async ({ page, request }) => {
  await abrir(page, EMITIDA, "Emitida");
  await page.getByRole("button", { name: "Distribuir", exact: true }).click();
  const dialogo = confirmacion(page);
  await expect(dialogo).toBeVisible();
  await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
  const escritura = await ultimaEscritura(request);
  expect(escritura.metodo).toBe("POST");
  expect(escritura.url).toBe(`/api/complejos/${EMITIDA}/liquidaciones/${LIQUIDACION_EMITIDA}/distribucion`);
});

test("C09 · anular pide el motivo antes de confirmar y lo manda", async ({ page, request }) => {
  await abrir(page, EMITIDA, "Emitida");
  await page.getByRole("button", { name: "Anular", exact: true }).click();
  const dialogo = confirmacion(page);
  await expect(dialogo).toBeVisible();
  const confirmar = dialogo.getByRole("button", { name: "Confirmar", exact: true });
  await expect(confirmar).toBeDisabled();
  await dialogo.getByLabel("Motivo", { exact: true }).fill("Se cargó mal una factura");
  await expect(confirmar).toBeEnabled();
  await confirmar.click();
  const escritura = await ultimaEscritura(request);
  expect(escritura.url).toBe(`/api/complejos/${EMITIDA}/liquidaciones/${LIQUIDACION_EMITIDA}/anulacion`);
  expect(JSON.parse(escritura.cuerpo)).toEqual({ motivo: "Se cargó mal una factura" });
});

test("C09 · una distribuida no ofrece distribuir ni anular", async ({ page }) => {
  // Control: la emitida sí los ofrece.
  await abrir(page, EMITIDA, "Emitida");
  await expect(page.getByRole("button", { name: "Anular", exact: true })).toHaveCount(1);
  await abrir(page, DISTRIBUIDA, "Distribuida");
  await expect(page.getByRole("button", { name: "Anular", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Distribuir", exact: true })).toHaveCount(0);
});

test("C09 · la liquidación emitida no tiene errores de axe", async ({ page }) => {
  await abrir(page, EMITIDA, "Emitida");
  await sinViolacionesEnElNavegador(page);
});
