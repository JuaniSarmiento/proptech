/**
 * Aceptación de H-025 · las pantallas de pagos en navegador real (C01 a C08, N01 a N03).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`) con los escenarios de `aceptacion/H-025/CONTRATO.md`
 * ("API falsa"). Locators exactos, alertas filtradas por texto (L-085) y cada test espera la escritura (L-087).
 */

import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";
import { cabecerasDePrueba, cookiesDeContextoDePrueba } from "./sesion-local";

const EDIFICIO = "00000000-0000-0000-0000-000000002501";
const FALLIDA = "00000000-0000-0000-0000-000000002502";
const COMPROBANTE = "00000000-0000-0000-0000-000000025900";
const U = {
  "1A": "00000000-0000-0000-0000-000000025101",
  "1B": "00000000-0000-0000-0000-000000025102",
  "2A": "00000000-0000-0000-0000-000000025103",
  "2B": "00000000-0000-0000-0000-000000025104",
};
const INFORMADO = "00000000-0000-0000-0000-000000025001";
const CONFIRMADO = "00000000-0000-0000-0000-000000025002";
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;
const PNG = Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), Buffer.alloc(64)]);

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

async function abrirInformar(page: Page, edificio = EDIFICIO) {
  await page.goto(`/edificios/${edificio}/mis-pagos/informar`);
  await expect(page.getByRole("heading", { name: "Informar un pago", exact: true })).toBeVisible();
  await page.getByLabel("Comprobante", { exact: true }).setInputFiles({
    name: "comprobante.png",
    mimeType: "image/png",
    buffer: PNG,
  });
}

function item(page: Page, lista: string, numero: string) {
  return page.getByRole("list", { name: lista, exact: true }).getByRole("listitem").filter({ hasText: numero });
}

// --- C01 a C03: informar ----------------------------------------------------------------------------

test("C01 · la vecina revisa lo que leyó la IA, corrige y envía", async ({ page, context, baseURL, request }) => {
  await comoVecina(context, baseURL);
  await abrirInformar(page);
  await expect(page.getByLabel("Banco", { exact: true })).toHaveValue("Banco Nación");
  await expect(page.getByLabel("Número de operación", { exact: true })).toHaveValue("12345678");
  await expect(page.getByLabel("Fecha de la transferencia", { exact: true })).toHaveValue("2026-11-05");
  await expect(page.getByLabel("Monto", { exact: true })).toHaveValue("43350.00");
  await page.getByLabel("Monto", { exact: true }).fill("43000.00");
  await page.getByLabel("Importe para 1A", { exact: true }).fill("43000.00");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  const escritura = await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos`);
  expect(escritura.metodo).toBe("POST");
  const cuerpo = JSON.parse(escritura.cuerpo);
  expect(cuerpo.comprobante_id).toBe(COMPROBANTE);
  expect(cuerpo.monto).toBe("43000.00");
  expect(cuerpo.banco).toBe("Banco Nación");
  expect(cuerpo.numero_de_operacion).toBe("12345678");
  expect(cuerpo.fecha_de_transferencia).toBe("2026-11-05");
  expect(cuerpo.partes).toEqual([{ unidad_id: U["1A"], importe: "43000.00" }]);
  await expect(page).toHaveURL(new RegExp(`/edificios/${EDIFICIO}/mis-pagos$`));
});

test("C02 · con dos unidades reparte el pago", async ({ page, context, baseURL, request }) => {
  await comoVecina(context, baseURL);
  await abrirInformar(page);
  await page.getByLabel("Monto", { exact: true }).fill("80775.00");
  await page.getByLabel("Importe para 1A", { exact: true }).fill("43350.00");
  await page.getByLabel("Importe para 2B", { exact: true }).fill("37425.00");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  const cuerpo = JSON.parse((await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos`)).cuerpo);
  expect(cuerpo.partes).toEqual([
    { unidad_id: U["1A"], importe: "43350.00" },
    { unidad_id: U["2B"], importe: "37425.00" },
  ]);
});

test("C03 · si no se pudo leer, se carga a mano", async ({ page, context, baseURL, request }) => {
  await comoVecina(context, baseURL);
  await abrirInformar(page, FALLIDA);
  await expect(page.getByRole("alert").filter({ hasText: "No pudimos leer el comprobante" })).toBeVisible();
  await expect(page.getByLabel("Banco", { exact: true })).toHaveValue("");
  await page.getByLabel("Banco", { exact: true }).fill("Mercado Pago");
  await page.getByLabel("Número de operación", { exact: true }).fill("998877");
  await page.getByLabel("Fecha de la transferencia", { exact: true }).fill("2026-11-06");
  await page.getByLabel("Monto", { exact: true }).fill("100.00");
  await page.getByLabel("Importe para 1A", { exact: true }).fill("100.00");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  const cuerpo = JSON.parse((await esperarEscritura(request, `/api/complejos/${FALLIDA}/pagos`)).cuerpo);
  expect(cuerpo.banco).toBe("Mercado Pago");
  expect(cuerpo.numero_de_operacion).toBe("998877");
});

// --- C04: mis pagos --------------------------------------------------------------------------------

test("C04 · mis pagos muestra el estado en texto y el motivo", async ({ page, context, baseURL }) => {
  await comoVecina(context, baseURL);
  await page.goto(`/edificios/${EDIFICIO}/mis-pagos`);
  await expect(page.getByRole("heading", { name: "Mis pagos", exact: true })).toBeVisible();
  await expect(item(page, "Pagos informados", "11110001")).toContainText("Informado");
  await expect(item(page, "Pagos informados", "11110001")).toContainText("43.350,00");
  await expect(item(page, "Pagos informados", "11110002")).toContainText("Confirmado");
  await expect(item(page, "Pagos informados", "11110003")).toContainText("Rechazado");
  await expect(item(page, "Pagos informados", "11110003")).toContainText("El monto no coincide con el comprobante");
  await expect(item(page, "Pagos informados", "11110004")).toContainText("Revertido");
  await expect(item(page, "Pagos informados", "11110004")).toContainText("Cheque rechazado");
  await page.getByRole("link", { name: "Informar un pago", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/edificios/${EDIFICIO}/mis-pagos/informar$`));
});

// --- C05 y C06: la bandeja del administrador ---------------------------------------------------------

async function abrirBandeja(page: Page) {
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  await expect(page.getByRole("heading", { name: "Pagos", exact: true })).toBeVisible();
}

test("C05 · confirmar pide confirmación y manda el pedido", async ({ page, request }) => {
  await abrirBandeja(page);
  await item(page, "Pagos del edificio", "11110001").getByRole("button", { name: "Confirmar", exact: true }).click();
  const dialogo = page.getByRole("dialog");
  await expect(dialogo).toBeVisible();
  await dialogo.getByRole("button", { name: "Confirmar", exact: true }).click();
  const escritura = await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos/${INFORMADO}/confirmacion`);
  expect(escritura.metodo).toBe("POST");
});

test("C05 · rechazar exige motivo", async ({ page, request }) => {
  await abrirBandeja(page);
  await item(page, "Pagos del edificio", "11110001").getByRole("button", { name: "Rechazar", exact: true }).click();
  const dialogo = page.getByRole("dialog");
  const boton = dialogo.getByRole("button", { name: "Rechazar", exact: true });
  await expect(boton).toBeDisabled();
  await dialogo.getByLabel("Motivo", { exact: true }).fill("El monto no coincide con el comprobante");
  await expect(boton).toBeEnabled();
  await boton.click();
  const cuerpo = JSON.parse(
    (await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos/${INFORMADO}/rechazo`)).cuerpo,
  );
  expect(cuerpo).toEqual({ motivo: "El monto no coincide con el comprobante" });
});

test("C06 · revertir un confirmado", async ({ page, request }) => {
  await abrirBandeja(page);
  const pago = item(page, "Pagos del edificio", "11110002");
  await expect(pago.getByRole("button", { name: "Confirmar", exact: true })).toHaveCount(0);
  await pago.getByRole("button", { name: "Revertir", exact: true }).click();
  const dialogo = page.getByRole("dialog");
  await dialogo.getByLabel("Motivo", { exact: true }).fill("Cheque rechazado");
  await dialogo.getByRole("button", { name: "Revertir", exact: true }).click();
  const cuerpo = JSON.parse(
    (await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos/${CONFIRMADO}/reversion`)).cuerpo,
  );
  expect(cuerpo).toEqual({ motivo: "Cheque rechazado" });
});

test("C06 · reimputar un confirmado a otra unidad", async ({ page, request }) => {
  await abrirBandeja(page);
  await item(page, "Pagos del edificio", "11110002").getByRole("button", { name: "Reimputar", exact: true }).click();
  const dialogo = page.getByRole("dialog");
  await dialogo.getByLabel("Unidad de destino", { exact: true }).selectOption({ label: "2A" });
  await dialogo.getByLabel("Motivo", { exact: true }).fill("Era de 2A");
  await dialogo.getByRole("button", { name: "Reimputar", exact: true }).click();
  const cuerpo = JSON.parse(
    (await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos/${CONFIRMADO}/reimputacion`)).cuerpo,
  );
  expect(cuerpo).toEqual({ desde_unidad_id: U["2B"], hacia_unidad_id: U["2A"], motivo: "Era de 2A" });
});

// --- C07: ver el comprobante --------------------------------------------------------------------------

test("C07 · ver el comprobante pide el enlace y lo abre por la web", async ({ page, request }) => {
  await abrirBandeja(page);
  const abierta = page.context().waitForEvent("page", { timeout: 15000 }).catch(() => null);
  const navegacion = page.waitForURL(/\/comprobantes\/descarga\?token=/, { timeout: 15000 }).catch(() => null);
  await item(page, "Pagos del edificio", "11110001").getByRole("button", { name: "Ver comprobante", exact: true }).click();
  await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos/${INFORMADO}/comprobante/enlace`);
  const nueva = await abierta;
  const urls = [page.url(), nueva?.url() ?? ""];
  await navegacion;
  if (nueva) await nueva.waitForLoadState().catch(() => undefined);
  const final = [page.url(), nueva?.url() ?? "", ...urls];
  expect(final.some((u) => /\/comprobantes\/descarga\?token=/.test(u) && !/\/api\//.test(u))).toBe(true);
});

// --- C08: 320 px y axe ----------------------------------------------------------------------------

test("C08 · las tres pantallas a 320 px sin scroll horizontal y sin errores de axe", async ({ page, context, baseURL }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await abrirBandeja(page);
  await expect(item(page, "Pagos del edificio", "11110001")).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  await comoVecina(context, baseURL);
  await page.goto(`/edificios/${EDIFICIO}/mis-pagos`);
  await expect(item(page, "Pagos informados", "11110001")).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  await abrirInformar(page);
  await expect(page.getByLabel("Importe para 1A", { exact: true })).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
});

// --- N01 a N03 ------------------------------------------------------------------------------------

test("N01 · el menú muestra a cada uno lo suyo", async ({ page, context, baseURL }) => {
  await page.goto(`/edificios/${EDIFICIO}/pagos`);
  const menu = page.getByRole("navigation", { name: "Secciones del edificio" });
  await expect(menu.getByRole("link", { name: "Pagos", exact: true })).toBeVisible();
  await expect(menu.getByRole("link", { name: "Mis pagos", exact: true })).toHaveCount(0);
  await comoVecina(context, baseURL);
  await page.goto(`/edificios/${EDIFICIO}/mis-pagos`);
  const delVecino = page.getByRole("navigation", { name: "Secciones del edificio" });
  await expect(delVecino.getByRole("link", { name: "Mis pagos", exact: true })).toBeVisible();
  await expect(delVecino.getByRole("link", { name: "Pagos", exact: true })).toHaveCount(0);
});

test("N02 · la vecina sólo ve sus unidades para repartir", async ({ page, context, baseURL }) => {
  await comoVecina(context, baseURL);
  await abrirInformar(page);
  await expect(page.getByLabel("Importe para 1A", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Importe para 2B", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Importe para 1B", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Importe para 2A", { exact: true })).toHaveCount(0);
});

test("N03 · la pantalla no suma: manda lo que hay y muestra el error de la API", async ({
  page,
  context,
  baseURL,
  request,
}) => {
  await comoVecina(context, baseURL);
  await abrirInformar(page);
  await page.getByLabel("Monto", { exact: true }).fill("80775.00");
  await page.getByLabel("Importe para 1A", { exact: true }).fill("43350.00");
  await page.getByLabel("Importe para 2B", { exact: true }).fill("37000.00");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  const cuerpo = JSON.parse((await esperarEscritura(request, `/api/complejos/${EDIFICIO}/pagos`)).cuerpo);
  expect(cuerpo.monto).toBe("80775.00");
  expect(cuerpo.partes).toEqual([
    { unidad_id: U["1A"], importe: "43350.00" },
    { unidad_id: U["2B"], importe: "37000.00" },
  ]);
  await expect(page.getByRole("alert").filter({ hasText: "Las partes tienen que sumar el monto" })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`/mis-pagos/informar$`));
});
