/**
 * Comparación de saldos (change 5, H-008, tarea 2.5): accesibilidad y teclado de la pantalla
 * `/edificios/{id}/importar/comparacion`, a 320 px y a 1280 px, contra los tres edificios de la API
 * falsa de H-008 (801 con diferencias, 802 sin ellas). Lo funcional (los números, el aviso, aceptar
 * y el 403) lo prueba la aceptación congelada (`aceptacion-h008-comparacion.spec.ts`); acá: axe con
 * contraste real, sin scroll horizontal, la confirmación abierta con el teclado, el foco que vuelve
 * y que el Esc la cierra.
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana, contornoDelElementoEnfocado } from "./comprobaciones";
import { expect, test } from "./prueba";

const CON_DIFERENCIAS = "00000000-0000-0000-0000-000000000801";
const SIN_DIFERENCIAS = "00000000-0000-0000-0000-000000000802";
const ANCHOS = [320, 1280] as const;

async function abrir(page: import("@playwright/test").Page, id: string, ancho: number) {
  await page.setViewportSize({ width: ancho, height: 900 });
  await page.goto(`/edificios/${id}/importar/comparacion`);
  await expect(
    page.getByRole("heading", { name: "Comparación de saldos", level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole("table", { name: "Comparación por unidad" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

for (const ancho of ANCHOS) {
  test(`H-008 · con diferencias: sin desborde ni violaciones de axe a ${ancho} px`, async ({
    page,
  }) => {
    await abrir(page, CON_DIFERENCIAS, ancho);
    expect(await anchoExcedeLaVentana(page), `desborda la página a ${ancho} px`).toBe(false);
    await sinViolacionesEnElNavegador(page);
  });

  test(`H-008 · sin diferencias: sin desborde ni violaciones de axe a ${ancho} px`, async ({
    page,
  }) => {
    await abrir(page, SIN_DIFERENCIAS, ancho);
    expect(await anchoExcedeLaVentana(page), `desborda la página a ${ancho} px`).toBe(false);
    await sinViolacionesEnElNavegador(page);
  });

  test(`H-008 · la confirmación con el teclado: abre, atrapa el foco, Esc la cierra y el foco vuelve a ${ancho} px`, async ({
    page,
  }) => {
    await abrir(page, CON_DIFERENCIAS, ancho);
    const boton = page.getByRole("button", { name: "Aceptar diferencias" });
    await boton.focus();
    expect(await contornoDelElementoEnfocado(page), "el botón no muestra el foco").not.toBe("none");
    await page.keyboard.press("Enter");
    const confirmacion = page.getByRole("dialog", { name: "Aceptar diferencias" });
    await expect(confirmacion).toBeVisible();
    // El foco entra a la confirmación y `Tab` no se escapa de ella.
    for (let paso = 0; paso < 6; paso += 1) {
      const adentro = await page.evaluate(() => {
        const dialogo = document.querySelector('[role="dialog"]');
        return Boolean(dialogo?.contains(document.activeElement));
      });
      expect(adentro, `el foco salió de la confirmación en el Tab ${paso}`).toBe(true);
      await page.keyboard.press("Tab");
    }
    expect(await anchoExcedeLaVentana(page)).toBe(false);
    await sinViolacionesEnElNavegador(page);
    await page.keyboard.press("Escape");
    await expect(confirmacion).toHaveCount(0);
    await expect(boton).toBeFocused();
  });
}
