/**
 * Aceptación de H-013 · criterio de interfaz en navegador real (C11).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`), con los escenarios de
 * `aceptacion/H-013/CONTRATO.md` ("API falsa"). Locators exactos y alertas filtradas por texto (L-085).
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const SIN_CONTROLES = "00000000-0000-0000-0000-000000001101";
const CON_DURO = "00000000-0000-0000-0000-000000001201";
const CON_BLOQUEANTE = "00000000-0000-0000-0000-000000001301";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function abrir(page: import("@playwright/test").Page, edificio: string) {
  await page.goto(`/edificios/${edificio}/liquidaciones/2026-11`);
  await expect(page.getByRole("heading", { name: "Preliquidación de noviembre de 2026" })).toBeVisible();
  const boton = page.getByRole("button", { name: "Emitir liquidación", exact: true });
  await expect(boton).toBeVisible();
  return boton;
}

function confirmacion(page: import("@playwright/test").Page) {
  return page.getByRole("dialog").or(page.getByRole("alertdialog"));
}

async function ultimaEscritura(request: import("@playwright/test").APIRequestContext) {
  const r = await request.get(`${baseApi}/api/__debug/ultima-escritura`, { headers: cabecerasDePrueba() });
  expect(r.ok()).toBe(true);
  return r.json();
}

test("C11 · emitir pide confirmación y manda la huella mostrada", async ({ page, request }) => {
  const boton = await abrir(page, SIN_CONTROLES);
  await boton.click();
  const dialogo = confirmacion(page);
  await expect(dialogo).toBeVisible();
  await expect(dialogo).toContainText(/no se deshace/i);
  await expect(dialogo).toContainText("191.500,00");
  await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
  const emitida = page.getByRole("region", { name: "Liquidación emitida", exact: true });
  await expect(emitida).toBeVisible();
  await expect(emitida).toContainText("191.500,00");
  const escritura = await ultimaEscritura(request);
  expect(escritura.metodo).toBe("POST");
  expect(escritura.url).toBe(`/api/complejos/${SIN_CONTROLES}/periodos/2026-11-01/emision`);
  const cuerpo = JSON.parse(escritura.cuerpo);
  expect(cuerpo.emision_id).toMatch(UUID);
  expect(cuerpo.huella).toMatch(/^[0-9a-f]{64}$/);
  expect(cuerpo.alertas_aceptadas).toEqual([]);
});

test("C11 · un bloqueante se acepta con su casilla antes de confirmar", async ({ page, request }) => {
  const boton = await abrir(page, CON_BLOQUEANTE);
  await boton.click();
  const dialogo = confirmacion(page);
  await expect(dialogo).toBeVisible();
  const confirmar = dialogo.getByRole("button", { name: "Confirmar", exact: true });
  await expect(confirmar).toBeDisabled();
  await dialogo.getByRole("checkbox", { name: /Hay 1 factura leída con alertas/ }).check();
  await expect(confirmar).toBeEnabled();
  await confirmar.click();
  await expect(page.getByRole("region", { name: "Liquidación emitida", exact: true })).toBeVisible();
  const cuerpo = JSON.parse((await ultimaEscritura(request)).cuerpo);
  expect(cuerpo.alertas_aceptadas).toEqual(["gastos_en_revision"]);
});

test("C11 · con un control duro no se puede emitir", async ({ page }) => {
  // Control: sin controles el botón está habilitado.
  await expect(await abrir(page, SIN_CONTROLES)).toBeEnabled();
  await expect(await abrir(page, CON_DURO)).toBeDisabled();
});

test("C11 · correr el vencimiento manda la fecha y el motivo", async ({ page, request }) => {
  const boton = await abrir(page, SIN_CONTROLES);
  await boton.click();
  const dialogo = confirmacion(page);
  await expect(dialogo).toBeVisible();
  await dialogo.getByRole("checkbox", { name: "Correr el vencimiento", exact: true }).check();
  await dialogo.getByLabel("Nuevo vencimiento", { exact: true }).fill("2026-11-12");
  await dialogo.getByLabel("Motivo", { exact: true }).fill("Feriado del 10/11");
  await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByRole("region", { name: "Liquidación emitida", exact: true })).toBeVisible();
  const cuerpo = JSON.parse((await ultimaEscritura(request)).cuerpo);
  expect(cuerpo.vencimiento).toEqual({ fecha: "2026-11-12", motivo: "Feriado del 10/11" });
});

test("C11 · la confirmación no tiene errores de axe", async ({ page }) => {
  const boton = await abrir(page, CON_BLOQUEANTE);
  await boton.click();
  await expect(confirmacion(page)).toBeVisible();
  await sinViolacionesEnElNavegador(page);
});
