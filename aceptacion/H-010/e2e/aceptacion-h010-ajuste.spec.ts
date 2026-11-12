/**
 * Aceptación de H-010 · criterios de interfaz en navegador real (C08 y C12).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`), como el resto de `web/e2e/`. Los edificios y
 * unidades de abajo son escenarios que la API falsa tiene que conocer (ver
 * `aceptacion/H-010/CONTRATO.md`, "API falsa"): uno con la migración confirmada, uno pendiente y uno
 * confirmado que rechaza el ajuste con 403.
 *
 * Cada test primero espera la pantalla con un `expect`: si la pantalla no existe, el rojo es una
 * aserción, no un timeout de una acción.
 */

import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EDIFICIOS = {
  confirmado: "00000000-0000-0000-0000-000000001001",
  pendiente: "00000000-0000-0000-0000-000000001002",
  sinPermiso: "00000000-0000-0000-0000-000000001003",
} as const;
const UNIDAD_1A = {
  confirmado: "00000000-0000-0000-0000-000000100101",
  pendiente: "00000000-0000-0000-0000-000000100201",
  sinPermiso: "00000000-0000-0000-0000-000000100301",
} as const;
const MOTIVO = "Faltó la expensa extraordinaria de julio";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function abrirAjuste(
  page: import("@playwright/test").Page,
  edificio: string,
  unidad: string,
) {
  await page.goto(`/edificios/${edificio}/unidades/${unidad}/ajuste-de-saldo-inicial`);
  await expect(page.getByRole("heading", { name: "Ajustar saldo inicial" })).toBeVisible();
}

async function registrar(page: import("@playwright/test").Page) {
  await page.getByLabel("Importe").fill("5000,00");
  await page.getByLabel("Concepto").selectOption({ label: "Ordinaria" });
  await page.getByLabel("Motivo").fill(MOTIVO);
  await page.getByRole("button", { name: "Registrar ajuste" }).click();
  const confirmacion = page.getByRole("dialog").or(page.getByRole("alertdialog"));
  await expect(confirmacion).toBeVisible();
  await expect(confirmacion).toContainText("no se deshace");
  await confirmacion.getByRole("button", { name: "Confirmar", exact: true }).click();
}

test("C08 · el padrón de un edificio confirmado ofrece ajustar el saldo inicial de cada unidad", async ({
  page,
}) => {
  await page.goto(`/edificios/${EDIFICIOS.confirmado}/unidades`);
  const enlace = page.getByRole("link", { name: "Ajustar saldo inicial de 1A" });
  await expect(enlace).toBeVisible();
  await expect(enlace).toHaveAttribute(
    "href",
    `/edificios/${EDIFICIOS.confirmado}/unidades/${UNIDAD_1A.confirmado}/ajuste-de-saldo-inicial`,
  );
});

test("C08 · con la migración pendiente, el padrón no ofrece ajustar", async ({ page }) => {
  // Control: el mismo padrón de un edificio confirmado sí lo ofrece (si no, la ausencia no prueba nada).
  await page.goto(`/edificios/${EDIFICIOS.confirmado}/unidades`);
  await expect(page.getByRole("link", { name: "Ajustar saldo inicial de 1A" })).toBeVisible();
  await page.goto(`/edificios/${EDIFICIOS.pendiente}/unidades`);
  await expect(page.getByText("1A", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Ajustar saldo inicial/ })).toHaveCount(0);
});

test("C08 · ajustar con motivo pide confirmación, manda el ajuste y muestra la deuda nueva", async ({
  page,
  request,
}) => {
  await abrirAjuste(page, EDIFICIOS.confirmado, UNIDAD_1A.confirmado);
  await registrar(page);
  const registrado = page.getByRole("region", { name: "Ajuste registrado" });
  await expect(registrado).toBeVisible();
  await expect(registrado).toContainText("5.000,00");
  await expect(registrado).toContainText(MOTIVO);
  const ultima = await request.get(`${baseApi}/api/__debug/ultima-escritura`, {
    headers: cabecerasDePrueba(),
  });
  expect(ultima.ok()).toBe(true);
  const escritura = await ultima.json();
  expect(escritura.metodo).toBe("POST");
  expect(escritura.url).toBe(
    `/api/complejos/${EDIFICIOS.confirmado}/unidades/${UNIDAD_1A.confirmado}/ajustes-de-saldo-inicial`,
  );
  const cuerpo = JSON.parse(escritura.cuerpo);
  expect(cuerpo.operacion_id).toMatch(UUID);
  expect({ ...cuerpo, operacion_id: "x" }).toEqual({
    operacion_id: "x",
    importe: "5000.00",
    componente: "ordinaria",
    motivo: MOTIVO,
  });
});

test("C12 · sin permiso para ajustar muestra el aviso y no el ajuste registrado", async ({
  page,
}) => {
  await abrirAjuste(page, EDIFICIOS.sinPermiso, UNIDAD_1A.sinPermiso);
  await registrar(page);
  await expect(page.getByRole("alert").filter({ hasText: "No podés ajustar saldos en este edificio." })).toContainText("No podés ajustar saldos en este edificio.");
  await expect(page.getByRole("region", { name: "Ajuste registrado" })).toHaveCount(0);
});
