/**
 * Aceptación de H-007 · criterios de interfaz en navegador real (C08 y C16).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`), como el resto de `web/e2e/`. Los tres
 * edificios de abajo son escenarios que la API falsa tiene que conocer (ver
 * `aceptacion/H-007/CONTRATO.md`, "API falsa"): uno acepta la importación, otro la rechaza con
 * tres errores y otro responde 403.
 *
 * Cada test primero espera la pantalla con un `expect`: si la pantalla no existe, el rojo es una
 * aserción, no un timeout de una acción.
 */

import { expect, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const EDIFICIOS = {
  aceptada: "00000000-0000-0000-0000-000000000701",
  rechazada: "00000000-0000-0000-0000-000000000702",
  sinPermiso: "00000000-0000-0000-0000-000000000703",
} as const;
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;
const ARCHIVO = {
  name: "padron-torre-ficticia.xlsx",
  mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  // La API falsa no lee el Excel: alcanza con bytes que empiecen como un zip.
  buffer: Buffer.from("PK\u0003\u0004plantilla-de-prueba"),
};

async function abrirImportar(page: import("@playwright/test").Page, id: string) {
  await page.goto(`/edificios/${id}/importar`);
  await expect(page.getByRole("heading", { name: "Importar desde Excel" })).toBeVisible();
  await expect(page.getByLabel("Archivo de Excel")).toBeVisible();
  await expect(page.getByLabel("Fecha de migración")).toBeVisible();
}

async function subir(page: import("@playwright/test").Page) {
  await page.getByLabel("Archivo de Excel").setInputFiles(ARCHIVO);
  await page.getByLabel("Fecha de migración").fill("2026-10-15");
  await page.getByRole("button", { name: "Importar", exact: true }).click();
}

test("C08 · subir el archivo válido muestra el resumen de la importación", async ({
  page,
  request,
}) => {
  await abrirImportar(page, EDIFICIOS.aceptada);
  await subir(page);
  const resumen = page.getByRole("region", { name: "Importación aceptada" });
  await expect(resumen).toBeVisible();
  await expect(resumen).toContainText("12 unidades creadas");
  await expect(resumen).toContainText("10 propietarios nuevos");
  // La web manda el archivo y la fecha como multipart a la API, nunca desde el navegador.
  const ultima = await request.get(`${baseApi}/api/__debug/ultima-escritura`, {
    headers: cabecerasDePrueba(),
  });
  expect(ultima.ok()).toBe(true);
  const escritura = await ultima.json();
  expect(escritura.metodo).toBe("POST");
  expect(escritura.url).toBe(`/api/complejos/${EDIFICIOS.aceptada}/importaciones`);
  expect(escritura.contentType).toMatch(/^multipart\/form-data/);
  expect(escritura.cuerpo).toContain('name="archivo"');
  expect(escritura.cuerpo).toContain('filename="padron-torre-ficticia.xlsx"');
  expect(escritura.cuerpo).toContain('name="fecha_de_migracion"');
  expect(escritura.cuerpo).toContain("2026-10-15");
});

test("C08 · un archivo con errores muestra la tabla de errores y no carga nada", async ({
  page,
}) => {
  await abrirImportar(page, EDIFICIOS.rechazada);
  await subir(page);
  await expect(page.getByText("No se cargó nada", { exact: false })).toBeVisible();
  const tabla = page.getByRole("table", { name: "Errores del archivo" });
  await expect(tabla).toBeVisible();
  for (const columna of ["Hoja", "Fila", "Columna", "Motivo"]) {
    await expect(tabla.getByRole("columnheader", { name: columna, exact: true })).toBeVisible();
  }
  // Los tres errores de la API falsa, en el orden en que llegan.
  const filas = tabla.getByRole("row").filter({ has: page.getByRole("cell") });
  await expect(filas).toHaveCount(3);
  await expect(filas.nth(0)).toContainText("Unidades");
  await expect(filas.nth(0)).toContainText("9");
  await expect(filas.nth(0)).toContainText("Piso");
  await expect(filas.nth(1)).toContainText("Tipo");
  await expect(filas.nth(2)).toContainText("Superficie m2");
  await expect(page.getByRole("region", { name: "Importación aceptada" })).toHaveCount(0);
});

test("C08 · el botón descarga la plantilla", async ({ page }) => {
  await abrirImportar(page, EDIFICIOS.aceptada);
  const enlace = page.getByRole("link", { name: "Descargar plantilla" });
  await expect(enlace).toBeVisible();
  const [descarga] = await Promise.all([page.waitForEvent("download"), enlace.click()]);
  expect(descarga.suggestedFilename()).toBe("plantilla-padron.xlsx");
  const ruta = await descarga.path();
  expect(ruta).toBeTruthy();
  const { readFileSync } = await import("node:fs");
  expect(
    readFileSync(ruta as string)
      .subarray(0, 2)
      .toString(),
  ).toBe("PK");
});

test("C16 · sin permiso muestra el aviso y no el resumen", async ({ page }) => {
  await abrirImportar(page, EDIFICIOS.sinPermiso);
  await subir(page);
  await expect(page.getByRole("alert")).toContainText("No podés importar en este edificio.");
  await expect(page.getByRole("region", { name: "Importación aceptada" })).toHaveCount(0);
});
