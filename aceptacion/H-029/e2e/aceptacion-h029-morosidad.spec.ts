/**
 * Aceptación de H-029 · la pantalla de la morosidad en navegador real (C01 a C06, N01 a N03).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`) con los escenarios de `aceptacion/H-029/CONTRATO.md`
 * ("API falsa"). Locators exactos y alertas filtradas por texto (L-085).
 */

import type { BrowserContext, Page } from "@playwright/test";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

const EDIFICIO = "00000000-0000-0000-0000-000000002701";
const AL_DIA = "00000000-0000-0000-0000-000000002702";

async function como(context: BrowserContext, baseURL: string | undefined, sub: string) {
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL! },
    { name: "__client_uat", value: clientUat, url: baseURL! },
  ]);
}

function menu(page: Page) {
  return page.getByRole("navigation", { name: "Secciones del edificio" });
}

function lista(page: Page) {
  return page.getByRole("list", { name: "Unidades con deuda", exact: true });
}

function fila(page: Page, n: number) {
  return lista(page).getByRole("listitem").nth(n);
}

async function abrir(page: Page, edificio = EDIFICIO) {
  await page.goto(`/edificios/${edificio}/morosidad`);
  await expect(page.getByRole("heading", { name: "Morosidad", exact: true })).toBeVisible();
}

// --- C01 a C06 -------------------------------------------------------------------------------------------

test("C01 · Morosidad está en el menú, en Liquidación, y lleva a la pantalla", async ({ page }) => {
  await page.goto(`/edificios/${EDIFICIO}/liquidaciones`);
  const link = menu(page).getByRole("link", { name: "Morosidad", exact: true });
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("href", `/edificios/${EDIFICIO}/morosidad`);
  // Cada grupo del menú es una lista rotulada por su título (`MenuDelEdificio`).
  const grupo = menu(page).getByRole("list", { name: "Liquidación", exact: true });
  await expect(grupo.getByRole("link", { name: "Morosidad", exact: true })).toBeVisible();
  await link.click();
  await expect(page).toHaveURL(new RegExp(`/edificios/${EDIFICIO}/morosidad$`));
  await expect(page.getByRole("heading", { name: "Morosidad", exact: true })).toBeVisible();
});

test("C02 · el resumen y la fecha de los intereses", async ({ page }) => {
  await abrir(page);
  const resumen = page.getByRole("region", { name: "Resumen de la morosidad", exact: true });
  await expect(resumen).toContainText("Unidades que deben");
  await expect(resumen).toContainText("4");
  await expect(resumen).toContainText("Morosos críticos");
  await expect(resumen).toContainText("1");
  await expect(resumen).toContainText("Total vencido");
  await expect(page.getByText("Intereses al 31/10/2026", { exact: false })).toBeVisible();
});

test("C03 · una fila por unidad en el orden de la API, con todos sus datos", async ({ page }) => {
  await abrir(page);
  await expect(lista(page).getByRole("listitem")).toHaveCount(4);
  const primera = fila(page, 0);
  for (const texto of ["1A", "Ana Prueba", "Moroso crítico", "30.812,34", "30.000,00", "812,34", "3",
    "Desde el 10/09/2026 · 69 días"]) {
    await expect(primera).toContainText(texto);
  }
  await expect(fila(page, 1)).toContainText("1B");
  await expect(fila(page, 1)).toContainText("Carla Prueba");
  await expect(fila(page, 1)).toContainText("Con deuda vencida");
  await expect(fila(page, 1)).toContainText("40.000,00");
  await expect(fila(page, 1)).toContainText("Desde el 10/11/2026 · 8 días");
  await expect(fila(page, 2)).toContainText("2B");
  await expect(fila(page, 3)).toContainText("2A");
  await expect(fila(page, 3)).toContainText("Bajo el umbral");
  await expect(fila(page, 3)).toContainText("Sin propietarios cargados");
  await expect(fila(page, 3)).toContainText("300,00");
});

test("C04 · Exportar a Excel baja el archivo de la API", async ({ page }) => {
  await abrir(page);
  const link = page.getByRole("link", { name: "Exportar a Excel", exact: true });
  await expect(link).toHaveAttribute("href", `/edificios/${EDIFICIO}/morosidad/excel`);
  const descarga = page.waitForEvent("download");
  await link.click();
  const archivo = await descarga;
  expect(archivo.suggestedFilename()).toBe("morosidad-torre-ficticia-2026-11-18.xlsx");
  const ruta = await archivo.path();
  const { readFile } = await import("node:fs/promises");
  const bytes = await readFile(ruta);
  expect(bytes.subarray(0, 4).toString("binary")).toBe("PK\x03\x04");
});

test("C05 · sin deuda vencida lo dice", async ({ page }) => {
  await abrir(page, AL_DIA);
  await expect(page.getByRole("status").filter({ hasText: "No hay unidades con deuda vencida" })).toBeVisible();
  await expect(lista(page)).toHaveCount(0);
  await expect(page.getByText("Sin intereses registrados", { exact: false })).toBeVisible();
});

test("C06 · a 320 px sin scroll horizontal y sin errores de axe", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await abrir(page);
  await expect(fila(page, 0)).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  await abrir(page, AL_DIA);
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
});

// --- N01 a N03 -------------------------------------------------------------------------------------------

test("N01 · Escenario: El consejo no ve el botón de exportar · ve la lista pero no exporta", async ({ page, context, baseURL }) => {
  await como(context, baseURL, "user_consejo");
  await abrir(page);
  await expect(fila(page, 0)).toContainText("1A");
  await expect(menu(page).getByRole("link", { name: "Morosidad", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Exportar a Excel", exact: true })).toHaveCount(0);
  const r = await page.request.get(`/edificios/${EDIFICIO}/morosidad/excel`);
  expect(r.status()).toBe(403);
});

test("N02 · la vecina no ve Morosidad ni su pantalla", async ({ page, context, baseURL }) => {
  await como(context, baseURL, "user_vecina");
  await page.goto(`/edificios/${EDIFICIO}/morosidad`);
  await expect(menu(page).getByRole("link", { name: "Morosidad", exact: true })).toHaveCount(0);
  await expect(page.getByText("ver_morosidad", { exact: false })).toBeVisible();
  await expect(lista(page)).toHaveCount(0);
  await expect(page.getByText("Ana Prueba", { exact: false })).toHaveCount(0);
});

test("N03 · la pantalla no suma: el total es el de la API", async ({ page }) => {
  await abrir(page);
  const resumen = page.getByRole("region", { name: "Resumen de la morosidad", exact: true });
  await expect(resumen).toContainText("79.112,35");
  await expect(resumen).not.toContainText("79.112,34");
});
