/**
 * Aceptación de H-015 · criterio de interfaz en navegador real (C08).
 *
 * Corre contra la API falsa con el escenario de `aceptacion/H-015/CONTRATO.md` ("API falsa"). Locators
 * exactos y alertas filtradas por texto (L-085).
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EDIFICIO = "00000000-0000-0000-0000-000000001501";
const LIQUIDACION = "00000000-0000-0000-0000-000000015011";
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function abrir(page: import("@playwright/test").Page) {
  await page.goto(`/edificios/${EDIFICIO}/liquidaciones/2026-11`);
  const region = page.getByRole("region", { name: "Documentos", exact: true });
  await expect(region).toBeVisible();
  return region;
}

async function ultimaEscritura(request: import("@playwright/test").APIRequestContext) {
  const r = await request.get(`${baseApi}/api/__debug/ultima-escritura`, { headers: cabecerasDePrueba() });
  expect(r.ok()).toBe(true);
  return r.json();
}

test("C08 · cada documento muestra su estado en texto", async ({ page }) => {
  const region = await abrir(page);
  await expect(region).toContainText("Generado");
  await expect(region).toContainText("Fallido");
  await expect(region).toContainText("sin fuentes");
});

test("C08 · reprocesar manda el pedido a la API", async ({ page, request }) => {
  const region = await abrir(page);
  await region.getByRole("button", { name: "Reprocesar", exact: true }).click();
  await expect
    .poll(async () => (await ultimaEscritura(request))?.url)
    .toBe(`/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}/documentos/reproceso`);
});

test("C08 · un documento generado se descarga con su enlace y sin errores de axe", async ({ page, request }) => {
  const region = await abrir(page);
  const boton = region.getByRole("button", { name: /^Descargar 1A/ });
  await expect(boton).toHaveCount(1);
  await sinViolacionesEnElNavegador(page);
  await boton.click();
  await expect
    .poll(async () => (await ultimaEscritura(request))?.url)
    .toBe(`/api/complejos/${EDIFICIO}/documentos/00000000-0000-0000-0000-000000015101/enlace`);
});
