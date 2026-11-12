/**
 * Aceptación de H-009 · criterios de interfaz en navegador real (C06 y C10).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`), como el resto de `web/e2e/`. Los edificios de
 * abajo son escenarios que la API falsa tiene que conocer (ver `aceptacion/H-009/CONTRATO.md`, "API
 * falsa"): uno con la migración pendiente y un borrador sin diferencias, uno ya confirmado, uno con
 * diferencias sin aceptar y uno que rechaza la confirmación con 403.
 *
 * Cada test primero espera la pantalla con un `expect`: si la pantalla no existe, el rojo es una
 * aserción, no un timeout de una acción.
 */

import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EDIFICIOS = {
  pendiente: "00000000-0000-0000-0000-000000000901",
  confirmado: "00000000-0000-0000-0000-000000000902",
  conDiferencias: "00000000-0000-0000-0000-000000000903",
  sinPermiso: "00000000-0000-0000-0000-000000000904",
} as const;
const IMPORTACION_901 = "00000000-0000-0000-0000-000000009901";
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function abrirComparacion(page: import("@playwright/test").Page, id: string) {
  await page.goto(`/edificios/${id}/importar/comparacion`);
  await expect(page.getByRole("heading", { name: "Comparación de saldos" })).toBeVisible();
}

test("C06 · Escenario: Resumen confirmado · el resumen dice Saldos iniciales confirmados y no ofrece importar", async ({
  page,
}) => {
  await page.goto(`/edificios/${EDIFICIOS.confirmado}`);
  await expect(
    page.getByText("Saldos iniciales confirmados", { exact: false }).first(),
  ).toBeVisible();
  await expect(page.getByText("Estado de migración desconocido", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Importar desde Excel" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Confirmar sin saldos previos" })).toHaveCount(0);
});

test("C06 · con la migración pendiente, el paso 7 ofrece importar o confirmar sin saldos previos", async ({
  page,
}) => {
  await page.goto(`/edificios/${EDIFICIOS.pendiente}`);
  const importar = page.getByRole("link", { name: "Importar desde Excel" });
  await expect(importar).toBeVisible();
  await expect(importar).toHaveAttribute("href", `/edificios/${EDIFICIOS.pendiente}/importar`);
  const sinSaldos = page.getByRole("link", { name: "Confirmar sin saldos previos" });
  await expect(sinSaldos).toBeVisible();
  await expect(sinSaldos).toHaveAttribute(
    "href",
    `/edificios/${EDIFICIOS.pendiente}/saldos-previos`,
  );
});

test("C06 · confirmar saldos pide confirmación, manda la confirmación a la API y muestra el estado", async ({
  page,
  request,
}) => {
  await abrirComparacion(page, EDIFICIOS.pendiente);
  const boton = page.getByRole("button", { name: "Confirmar saldos" });
  await expect(boton).toBeEnabled();
  await boton.click();
  const confirmacion = page.getByRole("dialog").or(page.getByRole("alertdialog"));
  await expect(confirmacion).toBeVisible();
  await expect(confirmacion).toContainText("no se deshace");
  await confirmacion.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByRole("region", { name: "Saldos iniciales confirmados" })).toBeVisible();
  const ultima = await request.get(`${baseApi}/api/__debug/ultima-escritura`, {
    headers: cabecerasDePrueba(),
  });
  expect(ultima.ok()).toBe(true);
  const escritura = await ultima.json();
  expect(escritura.metodo).toBe("POST");
  expect(escritura.url).toBe(`/api/complejos/${EDIFICIOS.pendiente}/importaciones/confirmacion`);
  expect(JSON.parse(escritura.cuerpo)).toEqual({ importacion_id: IMPORTACION_901 });
});

test("C06 · con diferencias sin aceptar, confirmar saldos está deshabilitado", async ({ page }) => {
  await abrirComparacion(page, EDIFICIOS.conDiferencias);
  await expect(page.getByRole("button", { name: "Aceptar diferencias" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar saldos" })).toBeDisabled();
});

test("C10 · sin permiso para confirmar muestra el aviso y no el estado confirmado", async ({
  page,
}) => {
  await abrirComparacion(page, EDIFICIOS.sinPermiso);
  await page.getByRole("button", { name: "Confirmar saldos" }).click();
  const confirmacion = page.getByRole("dialog").or(page.getByRole("alertdialog"));
  await expect(confirmacion).toBeVisible();
  await confirmacion.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "No podés confirmar saldos en este edificio." })).toContainText(
    "No podés confirmar saldos en este edificio.",
  );
  await expect(page.getByRole("region", { name: "Saldos iniciales confirmados" })).toHaveCount(0);
});
