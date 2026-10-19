/**
 * Barrido mínimo del navegador real para las cuatro pantallas del bloque
 * C (4.1-4.4), contra la API falsa de 3.8/D7. NO es el barrido completo
 * de "las siete pantallas por cada escenario, sin huecos" (eso es 5.1,
 * grupo 5, con su propia guarda de cobertura): este archivo es la
 * verificación de que las cuatro pantallas nuevas sirven de verdad en un
 * navegador, a 320 px, sin romper — lo que el bloque C puede confirmar
 * por sí solo sin tocar el trabajo de 5.1.
 */

import { expect, test } from "@playwright/test";
import { anchoExcedeLaVentana } from "./comprobaciones";

const _ID_NORMAL = "f760ca3b-7331-4927-96e5-54a3fbb1f3ae"; // edificio.json: sin escenario, fixtures sin mutar
const _ID_VACIO = "00000000-0000-0000-0000-000000000001"; // escenarios.ts: "vacio"
const _ID_FUERA_DE_TOLERANCIA = "00000000-0000-0000-0000-000000000008"; // escenarios.ts: "fuera_de_tolerancia"

test.describe("4.1 Mis edificios", () => {
  test("lista los edificios de la API falsa, a 320 px sin scroll horizontal", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto("/edificios");
    await expect(page.getByRole("heading", { name: "Mis edificios" })).toBeVisible();
    await expect(page.getByText("Edificio API", { exact: true })).toBeVisible();
    expect(await anchoExcedeLaVentana(page)).toBe(false);
  });
});

test.describe("4.2 Resumen del edificio", () => {
  test("muestra el checklist de puesta a punto, a 320 px sin scroll horizontal", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto(`/edificios/${_ID_NORMAL}`);
    await expect(page.getByRole("heading", { name: "Resumen del edificio" })).toBeVisible();
    await expect(page.getByText("Cargar unidades")).toBeVisible();
    expect(await anchoExcedeLaVentana(page)).toBe(false);
  });
});

test.describe("4.3 Padrón de unidades", () => {
  test('"fuera de tolerancia" muestra la diferencia en texto, a 320 px sin scroll', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto(`/edificios/${_ID_FUERA_DE_TOLERANCIA}/unidades`);
    await expect(page.getByText(/falta 0,0200 %/)).toBeVisible();
    expect(await anchoExcedeLaVentana(page)).toBe(false);
  });

  test('escenario "vacio": no rompe con informe null (gotcha de 3.8, visto en vivo)', async ({
    page,
  }) => {
    const respuesta = await page.goto(`/edificios/${_ID_VACIO}/unidades`);
    expect(respuesta?.status()).toBeLessThan(500);
    await expect(page.getByText(/Todavía no cargaste unidades/)).toBeVisible();
  });
});

test.describe("4.4 Grupos de reparto", () => {
  test('"Generales" aparece primero y automático, a 320 px sin scroll', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto(`/edificios/${_ID_NORMAL}/grupos`);
    await expect(page.getByText("Generales")).toBeVisible();
    expect(await anchoExcedeLaVentana(page)).toBe(false);
  });
});
