/**
 * Aceptación de H-011 · criterio de interfaz en navegador real (C12).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`), como el resto de `web/e2e/`. Los edificios de
 * abajo son escenarios que la API falsa tiene que conocer (ver `aceptacion/H-011/CONTRATO.md`, "API
 * falsa"): la base de los ejemplos, la base con fondo 0% y uno que responde 409.
 *
 * Cada test primero espera la pantalla con un `expect`: si la pantalla no existe, el rojo es una
 * aserción, no un timeout de una acción.
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana, contornoDelElementoEnfocado } from "./comprobaciones";
import { expect, test } from "./prueba";

const EDIFICIOS = {
  base: "00000000-0000-0000-0000-000000001101",
  fondoCero: "00000000-0000-0000-0000-000000001102",
  sinAnterior: "00000000-0000-0000-0000-000000001103",
} as const;

async function abrir(page: import("@playwright/test").Page, edificio: string) {
  await page.goto(`/edificios/${edificio}/liquidaciones/2026-11`);
  await expect(page.getByRole("heading", { name: "Preliquidación de noviembre de 2026" })).toBeVisible();
}

function fila(page: import("@playwright/test").Page, identificador: string) {
  return page
    .getByRole("table")
    .first()
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: identificador, exact: true }) });
}

test("C12 · la tabla por unidad muestra los importes de la base con punto de miles", async ({ page }) => {
  await abrir(page, EDIFICIOS.base);
  for (const columna of ["Ordinaria", "Fondo de reserva", "Extraordinaria", "Cargos particulares", "Intereses", "Total"]) {
    await expect(page.getByRole("columnheader", { name: columna, exact: true }).first()).toBeVisible();
  }
  const esperado: Record<string, string[]> = {
    "1A": ["27.000,00", "1.350,00", "15.000,00", "43.350,00"],
    "1B": ["27.000,00", "1.350,00", "15.000,00", "5.000,00", "48.350,00"],
    "2A": ["47.500,00", "2.375,00", "12.500,00", "62.375,00"],
    "2B": ["28.500,00", "1.425,00", "7.500,00", "37.425,00"],
  };
  for (const [identificador, importes] of Object.entries(esperado)) {
    const laFila = fila(page, identificador);
    await expect(laFila).toHaveCount(1);
    for (const importe of importes) {
      await expect(laFila).toContainText(importe);
    }
  }
  await expect(page.getByText("191.500,00").first()).toBeVisible();
});

test("C12 · los bloques muestran las categorías con importe y porcentaje", async ({ page }) => {
  await abrir(page, EDIFICIOS.base);
  const ordinaria = page.getByRole("region", { name: "Ordinaria", exact: true });
  await expect(ordinaria).toBeVisible();
  await expect(ordinaria).toContainText("Limpieza");
  await expect(ordinaria).toContainText("90.000,00");
  await expect(ordinaria).toContainText("69,23");
  await expect(ordinaria).toContainText("130.000,00");
  const extraordinaria = page.getByRole("region", { name: "Extraordinaria", exact: true });
  await expect(extraordinaria).toContainText("Pintura");
  await expect(extraordinaria).toContainText("50.000,00");
});

test("C12 · con fondo 0% no está la columna del fondo", async ({ page }) => {
  // Control: con fondo 5% la columna está (si no, la ausencia no prueba nada).
  await abrir(page, EDIFICIOS.base);
  await expect(page.getByRole("columnheader", { name: "Fondo de reserva", exact: true })).toHaveCount(1);
  await abrir(page, EDIFICIOS.fondoCero);
  await expect(fila(page, "1A")).toHaveCount(1);
  await expect(page.getByRole("columnheader", { name: "Fondo de reserva", exact: true })).toHaveCount(0);
});

test("C12 · sin el período anterior emitido, avisa y no muestra la tabla", async ({ page }) => {
  await page.goto(`/edificios/${EDIFICIOS.sinAnterior}/liquidaciones/2026-11`);
  // Next agrega siempre un `role="alert"` vacío (el anunciador de rutas): se filtra por el texto.
  await expect(page.getByRole("alert").filter({ hasText: /período anterior/i })).toHaveCount(1);
  await expect(page.getByRole("table")).toHaveCount(0);
});

for (const ancho of [320, 1280]) {
  test(`C12 · a ${ancho} px sin scroll horizontal de la página y sin errores de axe`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: 900 });
    await abrir(page, EDIFICIOS.base);
    await expect(fila(page, "2B")).toHaveCount(1);
    expect(await anchoExcedeLaVentana(page)).toBe(false);
    await sinViolacionesEnElNavegador(page);
  });
}

test("C12 · con teclado, el foco recorre la pantalla y se ve", async ({ page }) => {
  await abrir(page, EDIFICIOS.base);
  let visitados = 0;
  for (let i = 0; i < 6; i += 1) {
    await page.keyboard.press("Tab");
    const contorno = await contornoDelElementoEnfocado(page);
    if (contorno !== "none" && contorno !== "") {
      visitados += 1;
    }
  }
  expect(visitados).toBeGreaterThan(0);
});
