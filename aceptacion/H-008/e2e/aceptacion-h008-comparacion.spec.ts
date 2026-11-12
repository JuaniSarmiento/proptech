/**
 * Aceptación de H-008 · criterios de interfaz en navegador real (C12 y C15).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`), como el resto de `web/e2e/`. Los tres
 * edificios de abajo son escenarios que la API falsa tiene que conocer (ver
 * `aceptacion/H-008/CONTRATO.md`, "API falsa"): uno con dos diferencias de signo opuesto y mes
 * entero, otro sin diferencias y con proporcional, y otro que rechaza la aceptación con 403.
 *
 * Cada test primero espera la pantalla con un `expect`: si la pantalla no existe, el rojo es una
 * aserción, no un timeout de una acción.
 */

import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EDIFICIOS = {
  conDiferencias: "00000000-0000-0000-0000-000000000801",
  sinDiferencias: "00000000-0000-0000-0000-000000000802",
  sinPermiso: "00000000-0000-0000-0000-000000000803",
} as const;
const IMPORTACION_801 = "00000000-0000-0000-0000-000000008801";
const AVISO = "El primer interés del sistema cubre octubre de 2026";
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function abrirComparacion(page: import("@playwright/test").Page, id: string) {
  await page.goto(`/edificios/${id}/importar/comparacion`);
  await expect(page.getByRole("heading", { name: "Comparación de saldos" })).toBeVisible();
  const tabla = page.getByRole("table", { name: "Comparación por unidad" });
  await expect(tabla).toBeVisible();
  return tabla;
}

function filaDe(tabla: import("@playwright/test").Locator, unidad: string) {
  return tabla
    .getByRole("row")
    .filter({ has: tabla.page().getByRole("cell", { name: unidad, exact: true }) });
}

test("C12 · la comparación muestra las diferencias aunque el total coincida, con el aviso de mes entero", async ({
  page,
}) => {
  const tabla = await abrirComparacion(page, EDIFICIOS.conDiferencias);
  for (const columna of ["Unidad", "Borrador", "Control", "Diferencia"]) {
    await expect(tabla.getByRole("columnheader", { name: columna, exact: true })).toBeVisible();
  }
  const a1 = filaDe(tabla, "1A");
  await expect(a1).toContainText("169.000,00");
  await expect(a1).toContainText("159.000,00");
  await expect(a1).toContainText("10.000,00");
  const a2 = filaDe(tabla, "2A");
  await expect(a2).toContainText("52.000,00");
  await expect(a2).toContainText("62.000,00");
  await expect(a2).toContainText("10.000,00");
  // Los dos totales son iguales y aun así se cuentan dos unidades con diferencia.
  await expect(page.getByText("Total del borrador", { exact: false })).toBeVisible();
  await expect(page.getByText("Total de control", { exact: false })).toBeVisible();
  await expect(page.getByText("326.000,00", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("2 unidades con diferencia", { exact: false })).toBeVisible();
  // El aviso de mes entero (E13), al menos en la fila de 1A.
  await expect(a1).toContainText(AVISO);
  await expect(page.getByRole("button", { name: "Aceptar diferencias" })).toBeVisible();
});

test("C12 · aceptar diferencias pide confirmación y manda la aceptación a la API", async ({
  page,
  request,
}) => {
  await abrirComparacion(page, EDIFICIOS.conDiferencias);
  await page.getByRole("button", { name: "Aceptar diferencias" }).click();
  const confirmacion = page.getByRole("dialog").or(page.getByRole("alertdialog"));
  await expect(confirmacion).toBeVisible();
  await expect(confirmacion).toContainText("2 unidades con diferencia");
  await confirmacion.getByRole("button", { name: "Aceptar", exact: true }).click();
  await expect(page.getByRole("region", { name: "Diferencias aceptadas" })).toBeVisible();
  const ultima = await request.get(`${baseApi}/api/__debug/ultima-escritura`, {
    headers: cabecerasDePrueba(),
  });
  expect(ultima.ok()).toBe(true);
  const escritura = await ultima.json();
  expect(escritura.metodo).toBe("POST");
  expect(escritura.url).toBe(
    `/api/complejos/${EDIFICIOS.conDiferencias}/importaciones/aceptacion-de-diferencias`,
  );
  expect(JSON.parse(escritura.cuerpo)).toEqual({ importacion_id: IMPORTACION_801 });
});

test("C12 · sin diferencias y con proporcional no hay aviso ni nada que aceptar", async ({
  page,
}) => {
  const tabla = await abrirComparacion(page, EDIFICIOS.sinDiferencias);
  await expect(filaDe(tabla, "1A")).toContainText("169.000,00");
  await expect(page.getByText("0 unidades con diferencia", { exact: false })).toBeVisible();
  await expect(page.getByText(AVISO, { exact: false })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Aceptar diferencias" })).toHaveCount(0);
});

test("C15 · sin permiso para aceptar muestra el aviso y no la aceptación", async ({ page }) => {
  await abrirComparacion(page, EDIFICIOS.sinPermiso);
  await page.getByRole("button", { name: "Aceptar diferencias" }).click();
  const confirmacion = page.getByRole("dialog").or(page.getByRole("alertdialog"));
  await expect(confirmacion).toBeVisible();
  await confirmacion.getByRole("button", { name: "Aceptar", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "No podés aceptar diferencias en este edificio." })).toContainText(
    "No podés aceptar diferencias en este edificio.",
  );
  await expect(page.getByRole("region", { name: "Diferencias aceptadas" })).toHaveCount(0);
});
