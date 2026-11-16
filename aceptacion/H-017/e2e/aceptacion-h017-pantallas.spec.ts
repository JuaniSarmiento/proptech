/**
 * Aceptación de H-017 · pantallas (C01, C02, C03, C05, C06, C07, N01, N02), contra la API falsa con los
 * escenarios de `aceptacion/H-017/CONTRATO.md`. Locators exactos y escrituras esperadas (L-085, L-087).
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EMITIDA = "00000000-0000-0000-0000-000000001401";
const LISTA = "00000000-0000-0000-0000-000000001701";
const SIN_VER = "00000000-0000-0000-0000-000000001702";
const SIN_CORREGIR = "00000000-0000-0000-0000-000000001703";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function ultimaEscritura(request: import("@playwright/test").APIRequestContext) {
  const r = await request.get(`${baseApi}/api/__debug/ultima-escritura`, { headers: cabecerasDePrueba() });
  expect(r.ok()).toBe(true);
  return r.json();
}

test("C01 · el menú del edificio lleva a Liquidaciones", async ({ page }) => {
  await page.goto(`/edificios/${LISTA}`);
  const link = page.getByRole("link", { name: "Liquidaciones", exact: true });
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("href", `/edificios/${LISTA}/liquidaciones`);
});

test("C01 · C06 · la lista muestra cada liquidación con su estado, también las anuladas", async ({ page }) => {
  await page.goto(`/edificios/${LISTA}/liquidaciones`);
  await expect(page.getByRole("heading", { name: "Liquidaciones", exact: true })).toBeVisible();
  const items = page.getByRole("list").filter({ hasText: "noviembre de 2026" }).getByRole("listitem");
  await expect(items).toHaveCount(2);
  await expect(items.nth(0)).toContainText("noviembre de 2026");
  await expect(items.nth(0)).toContainText("Distribuida");
  await expect(items.nth(0)).toContainText("191.500,00");
  await expect(items.nth(0).getByRole("link")).toHaveAttribute("href", `/edificios/${LISTA}/liquidaciones/2026-11`);
  await expect(items.nth(1)).toContainText("octubre de 2026");
  await expect(items.nth(1)).toContainText("Anulada");
  await expect(items.nth(1).getByRole("button", { name: /Anular|Distribuir/ })).toHaveCount(0);
});

test("C02 · ofrece preparar el mes siguiente al último emitido", async ({ page }) => {
  await page.goto(`/edificios/${LISTA}/liquidaciones`);
  const preparar = page.getByRole("link", { name: "Preparar la liquidación de diciembre de 2026", exact: true });
  await expect(preparar).toHaveAttribute("href", `/edificios/${LISTA}/liquidaciones/2026-12`);
});

test("C03 · la emitida muestra lo que paga cada unidad", async ({ page }) => {
  await page.goto(`/edificios/${EMITIDA}/liquidaciones/2026-11`);
  const tabla = page.getByRole("table").filter({ hasText: "Saldo anterior" });
  await expect(tabla).toBeVisible();
  const fila = tabla.getByRole("row").filter({ has: page.getByRole("cell", { name: "1A", exact: true }) });
  await expect(fila).toContainText("27.000,00");
  await expect(fila).toContainText("43.350,00");
});

test("C05 · el cargo cobrado de menos se registra desde la pantalla", async ({ page, request }) => {
  await page.goto(`/edificios/${EMITIDA}/liquidaciones/2026-11`);
  const boton = page.getByRole("button", { name: "Cargo cobrado de menos de 1A", exact: true });
  await expect(boton).toBeVisible();
  await boton.click();
  const dialogo = page.getByRole("dialog").or(page.getByRole("alertdialog"));
  await expect(dialogo).toBeVisible();
  await dialogo.getByLabel("Importe", { exact: true }).fill("1500,00");
  await dialogo.getByLabel("Concepto", { exact: true }).selectOption({ label: "Ordinaria" });
  await dialogo.getByLabel("Motivo", { exact: true }).fill("Faltó cobrar la reparación del portón");
  await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect
    .poll(async () => (await ultimaEscritura(request))?.url)
    .toBe(`/api/complejos/${EMITIDA}/unidades/00000000-0000-0000-0000-000000140111/cargos-cobrados-de-menos`);
  const cuerpo = JSON.parse((await ultimaEscritura(request)).cuerpo);
  expect(cuerpo.operacion_id).toMatch(UUID);
  expect({ ...cuerpo, operacion_id: "x" }).toEqual({
    operacion_id: "x",
    obligacion_origen_id: "00000000-0000-0000-0000-000000140101",
    importe: "1500.00",
    componente: "ordinaria",
    motivo: "Faltó cobrar la reparación del portón",
  });
});

test("C07 · la lista a 320 px sin scroll horizontal y sin errores de axe", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto(`/edificios/${LISTA}/liquidaciones`);
  await expect(page.getByRole("heading", { name: "Liquidaciones", exact: true })).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
});

test("N01 · sin ver_liquidaciones no aparece el link", async ({ page }) => {
  // Control: con el permiso, el link está.
  await page.goto(`/edificios/${LISTA}`);
  await expect(page.getByRole("link", { name: "Liquidaciones", exact: true })).toHaveCount(1);
  await page.goto(`/edificios/${SIN_VER}`);
  await expect(page.getByRole("link", { name: "Resumen", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Liquidaciones", exact: true })).toHaveCount(0);
});

test("N02 · sin corregir_movimiento no hay cargo cobrado de menos", async ({ page }) => {
  await page.goto(`/edificios/${EMITIDA}/liquidaciones/2026-11`);
  await expect(page.getByRole("button", { name: "Cargo cobrado de menos de 1A", exact: true })).toHaveCount(1);
  await page.goto(`/edificios/${SIN_CORREGIR}/liquidaciones/2026-11`);
  await expect(page.getByRole("table").filter({ hasText: "Saldo anterior" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Cargo cobrado de menos/ })).toHaveCount(0);
});
