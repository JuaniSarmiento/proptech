/**
 * Aceptación de H-026 · los hallazgos de la demo del 8 en navegador real (C01 a C03, C05 a C07, N01 a N03).
 *
 * Corre contra la API falsa con los escenarios de `aceptacion/H-025/CONTRATO.md` y lo que suma
 * `aceptacion/H-026/CONTRATO.md` ("API falsa"). Locators exactos, alertas filtradas por texto (L-085) y cada test espera
 * la escritura (L-087).
 */

import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";
import { cabecerasDePrueba, cookiesDeContextoDePrueba } from "./sesion-local";

const EDIFICIO = "00000000-0000-0000-0000-000000002501";
const U = {
  "1A": "00000000-0000-0000-0000-000000025101",
  "1B": "00000000-0000-0000-0000-000000025102",
  "2A": "00000000-0000-0000-0000-000000025103",
  "2B": "00000000-0000-0000-0000-000000025104",
};
const REIMPUTADO = "00000000-0000-0000-0000-000000025005";
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;
const PNG = Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), Buffer.alloc(64)]);
const CONFIGURACION = ["Resumen", "Unidades", "Grupos", "Categorías", "Intereses y vencimiento"];

async function comoVecina(context: BrowserContext, baseURL: string | undefined) {
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub: "user_vecina" });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL! },
    { name: "__client_uat", value: clientUat, url: baseURL! },
  ]);
}

async function ultimaEscritura(request: APIRequestContext) {
  const r = await request.get(`${baseApi}/api/__debug/ultima-escritura`, { headers: cabecerasDePrueba() });
  expect(r.ok()).toBe(true);
  return r.json();
}

async function esperarEscritura(request: APIRequestContext, url: string) {
  await expect.poll(async () => (await ultimaEscritura(request))?.url, { timeout: 15000 }).toBe(url);
  return ultimaEscritura(request);
}

function menu(page: Page) {
  return page.getByRole("navigation", { name: "Secciones del edificio" });
}

function item(page: Page, lista: string, numero: string) {
  return page.getByRole("list", { name: lista, exact: true }).getByRole("listitem").filter({ hasText: numero });
}

async function subir(page: Page, ruta: string) {
  await page.goto(ruta);
  await expect(page.getByRole("heading", { name: "Informar un pago", exact: true })).toBeVisible();
  await page.getByLabel("Comprobante", { exact: true }).setInputFiles({
    name: "comprobante.png",
    mimeType: "image/png",
    buffer: PNG,
  });
  await expect(page.getByLabel("Monto", { exact: true })).toBeVisible();
}

// --- C01 y N01: el menú ------------------------------------------------------------------------------

test("C01 · la vecina ve en el menú sólo Mis pagos", async ({ page, context, baseURL }) => {
  await comoVecina(context, baseURL);
  await page.goto(`/edificios/${EDIFICIO}/mis-pagos`);
  await expect(menu(page).getByRole("link", { name: "Mis pagos", exact: true })).toBeVisible();
  for (const nombre of CONFIGURACION) {
    await expect(menu(page).getByRole("link", { name: nombre, exact: true })).toHaveCount(0);
  }
});

test("N01 · el administrador no pierde nada del menú", async ({ page }) => {
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  for (const nombre of [...CONFIGURACION, "Pagos"]) {
    await expect(menu(page).getByRole("link", { name: nombre, exact: true })).toBeVisible();
  }
});

// --- C02 y N02: los montos ---------------------------------------------------------------------------

for (const [escrito, esperado] of [
  ["43350", "43350.00"],
  ["43.350", "43350.00"],
  ["43350,5", "43350.50"],
  ["43.350,00", "43350.00"],
] as const) {
  test(`C02 · el monto "${escrito}" llega como ${esperado}`, async ({ page, context, baseURL, request }) => {
    await comoVecina(context, baseURL);
    await subir(page, `/edificios/${EDIFICIO}/mis-pagos/informar`);
    await page.getByLabel("Monto", { exact: true }).fill(escrito);
    await page.getByLabel("Importe para 1A", { exact: true }).fill(escrito);
    await page.getByRole("button", { name: "Enviar", exact: true }).click();
    const cuerpo = JSON.parse((await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos`)).cuerpo);
    expect(cuerpo.monto).toBe(esperado);
    expect(cuerpo.partes).toEqual([{ unidad_id: U["1A"], importe: esperado }]);
  });
}

test("N02 · la pantalla no redondea: 43350,123 se manda tal cual y se ve el error", async ({
  page,
  context,
  baseURL,
  request,
}) => {
  await comoVecina(context, baseURL);
  await subir(page, `/edificios/${EDIFICIO}/mis-pagos/informar`);
  await page.getByLabel("Monto", { exact: true }).fill("43350,123");
  await page.getByLabel("Importe para 1A", { exact: true }).fill("43350,123");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  const cuerpo = JSON.parse((await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos`)).cuerpo);
  expect(cuerpo.monto).not.toBe("43350.12");
  expect(cuerpo.monto).not.toBe("43350.13");
  await expect(page).toHaveURL(/\/mis-pagos\/informar$/);
});

// --- C03: el motivo en su renglón --------------------------------------------------------------------

async function motivoDebajoDeLaUnidad(pago: import("@playwright/test").Locator, motivo: string) {
  const elMotivo = pago.getByText(`Motivo: ${motivo}`, { exact: true });
  await expect(elMotivo).toBeVisible();
  const laUnidad = pago.getByText(/· Unidad \w+/);
  await expect(laUnidad.first()).toBeVisible();
  const caja = await elMotivo.boundingBox();
  const cajaUnidad = await laUnidad.first().boundingBox();
  expect(caja && cajaUnidad).toBeTruthy();
  // En su propio renglón: el motivo empieza debajo de donde termina la línea de la unidad (nunca "Unidad 2BMotivo:").
  expect(caja!.y).toBeGreaterThanOrEqual(cajaUnidad!.y + cajaUnidad!.height - 1);
}

test("C03 · el motivo va en su propio renglón, nunca pegado a la unidad", async ({ page, context, baseURL }) => {
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  await motivoDebajoDeLaUnidad(item(page, "Pagos del edificio", "11110003"), "El monto no coincide con el comprobante");
  await comoVecina(context, baseURL);
  await page.goto(`/edificios/${EDIFICIO}/mis-pagos`);
  await motivoDebajoDeLaUnidad(item(page, "Pagos informados", "11110004"), "Cheque rechazado");
});

// --- C05: la unidad vigente --------------------------------------------------------------------------

test("C05 · un pago reimputado dice dónde está y se reimputa desde ahí", async ({ page, request }) => {
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  const pago = item(page, "Pagos del edificio", "11110005");
  await expect(pago.getByText("Ahora en 2A", { exact: false })).toBeVisible();
  await pago.getByRole("button", { name: "Reimputar", exact: true }).click();
  const dialogo = page.getByRole("dialog");
  const destino = dialogo.getByLabel("Unidad de destino", { exact: true });
  await expect(destino.locator("option", { hasText: /^2A$/ })).toHaveCount(0);
  await destino.selectOption({ label: "1B" });
  await dialogo.getByLabel("Motivo", { exact: true }).fill("Era de 1B");
  await dialogo.getByRole("button", { name: "Reimputar", exact: true }).click();
  const cuerpo = JSON.parse(
    (await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos/${REIMPUTADO}/reimputacion`)).cuerpo,
  );
  expect(cuerpo).toEqual({ desde_unidad_id: U["2A"], hacia_unidad_id: U["1B"], motivo: "Era de 1B" });
});

// --- C06 y N03: el administrador informa -----------------------------------------------------------

test("C06 · el administrador informa un pago por un vecino desde la bandeja", async ({ page, request }) => {
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  const informar = page.getByRole("link", { name: "Informar un pago", exact: true });
  await expect(informar).toBeVisible();
  await informar.click();
  await expect(page).toHaveURL(new RegExp(`/edificios/${EDIFICIO}/pagos/informar$`));
  await page.getByLabel("Comprobante", { exact: true }).setInputFiles({
    name: "comprobante.png",
    mimeType: "image/png",
    buffer: PNG,
  });
  for (const u of ["1A", "1B", "2A", "2B"]) {
    await expect(page.getByLabel(`Importe para ${u}`, { exact: true })).toBeVisible();
  }
  await page.getByLabel("Monto", { exact: true }).fill("48.350,00");
  await page.getByLabel("Importe para 1B", { exact: true }).fill("48.350,00");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  const cuerpo = JSON.parse((await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos`)).cuerpo);
  expect(cuerpo.partes).toEqual([{ unidad_id: U["1B"], importe: "48350.00" }]);
  await expect(page).toHaveURL(new RegExp(`/edificios/${EDIFICIO}/pagos$`));
});

test("N03 · la vecina no ve la bandeja ni su Informar", async ({ page, context, baseURL }) => {
  await comoVecina(context, baseURL);
  await page.goto(`/edificios/${EDIFICIO}/mis-pagos`);
  await expect(menu(page).getByRole("link", { name: "Pagos", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Informar un pago", exact: true })).toHaveAttribute(
    "href",
    `/edificios/${EDIFICIO}/mis-pagos/informar`,
  );
});

// --- C07: 320 px y axe ------------------------------------------------------------------------------

test("C07 · a 320 px sin scroll horizontal y sin errores de axe", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  await expect(item(page, "Pagos del edificio", "11110005")).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  await page.goto(`/edificios/${EDIFICIO}/pagos/informar`);
  await expect(page.getByRole("heading", { name: "Informar un pago", exact: true })).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
});
