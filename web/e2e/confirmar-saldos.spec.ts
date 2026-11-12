/**
 * Confirmar saldos (change 5, H-009, tarea 3.3): accesibilidad y teclado de lo que suma a las
 * pantallas, a 320 px y a 1280 px, contra los edificios de la API falsa de H-009 (901 pendiente sin
 * diferencias, 902 confirmado, 903 con diferencias sin aceptar). Lo funcional (el botón habilitado o
 * no, lo que se manda, el 403, el resumen) lo prueba la aceptación congelada
 * (`aceptacion-h009-confirmar.spec.ts`); acá: axe con contraste real, sin scroll horizontal, la
 * confirmación abierta con el teclado, el foco que vuelve y la región confirmada.
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana, contornoDelElementoEnfocado } from "./comprobaciones";
import { expect, test } from "./prueba";

const PENDIENTE = "00000000-0000-0000-0000-000000000901";
const CONFIRMADO = "00000000-0000-0000-0000-000000000902";
const CON_DIFERENCIAS = "00000000-0000-0000-0000-000000000903";
const ANCHOS = [320, 1280] as const;

async function abrirComparacion(page: import("@playwright/test").Page, id: string, ancho: number) {
  await page.setViewportSize({ width: ancho, height: 900 });
  await page.goto(`/edificios/${id}/importar/comparacion`);
  await expect(
    page.getByRole("heading", { name: "Comparación de saldos", level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole("table", { name: "Comparación por unidad" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

for (const ancho of ANCHOS) {
  test(`H-009 · sin diferencias: sin desborde ni violaciones de axe a ${ancho} px`, async ({
    page,
  }) => {
    await abrirComparacion(page, PENDIENTE, ancho);
    expect(await anchoExcedeLaVentana(page), `desborda la página a ${ancho} px`).toBe(false);
    await sinViolacionesEnElNavegador(page);
  });

  test(`H-009 · con diferencias sin aceptar (botón deshabilitado): sin desborde ni violaciones de axe a ${ancho} px`, async ({
    page,
  }) => {
    await abrirComparacion(page, CON_DIFERENCIAS, ancho);
    expect(await anchoExcedeLaVentana(page), `desborda la página a ${ancho} px`).toBe(false);
    await sinViolacionesEnElNavegador(page);
  });

  test(`H-009 · la confirmación con el teclado: abre, atrapa el foco, Esc la cierra y el foco vuelve a ${ancho} px`, async ({
    page,
  }) => {
    await abrirComparacion(page, PENDIENTE, ancho);
    const boton = page.getByRole("button", { name: "Confirmar saldos" });
    await boton.focus();
    expect(await contornoDelElementoEnfocado(page), "el botón no muestra el foco").not.toBe("none");
    await page.keyboard.press("Enter");
    const confirmacion = page.getByRole("dialog", { name: "Confirmar saldos" });
    await expect(confirmacion).toBeVisible();
    await expect(confirmacion).toContainText("no se deshace");
    for (let paso = 0; paso < 6; paso += 1) {
      const adentro = await page.evaluate(() => {
        const dialogo = document.querySelector('[role="dialog"]');
        const ayuda = document.querySelector(".ayuda");
        return Boolean(
          dialogo?.contains(document.activeElement) || ayuda?.contains(document.activeElement),
        );
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

  test(`H-009 · después de confirmar: la región con los totales, sin botones y sin violaciones a ${ancho} px`, async ({
    page,
  }) => {
    await abrirComparacion(page, PENDIENTE, ancho);
    await page.getByRole("button", { name: "Confirmar saldos" }).click();
    await page
      .getByRole("dialog", { name: "Confirmar saldos" })
      .getByRole("button", { name: "Confirmar", exact: true })
      .click();
    const region = page.getByRole("region", { name: "Saldos iniciales confirmados" });
    await expect(region).toBeVisible();
    await expect(region).toContainText("320.000,00");
    await expect(page.getByRole("button", { name: "Confirmar saldos" })).toHaveCount(0);
    expect(await anchoExcedeLaVentana(page), `desborda la página a ${ancho} px`).toBe(false);
    await sinViolacionesEnElNavegador(page);
  });

  test(`H-009 · el resumen pendiente y el confirmado: sin violaciones de axe a ${ancho} px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: ancho, height: 900 });
    for (const id of [PENDIENTE, CONFIRMADO]) {
      await page.goto(`/edificios/${id}`);
      await expect(
        page.getByRole("heading", { name: "Resumen del edificio", level: 1 }),
      ).toBeVisible();
      await page.waitForLoadState("networkidle");
      expect(await anchoExcedeLaVentana(page), `desborda la página a ${ancho} px`).toBe(false);
      await sinViolacionesEnElNavegador(page);
    }
  });
}
