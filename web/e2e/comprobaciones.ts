/**
 * Chequeos genéricos del navegador real (D7, tarea 3.8): 320 px sin scroll
 * horizontal y foco visible. Los usa `comprobaciones.spec.ts` (contra
 * contenido mínimo, para probar los chequeos en sí) y los va a reusar el
 * barrido de 5.1 contra las siete pantallas.
 */

import type { Page } from "@playwright/test";

/** `true` si el documento se desborda del ancho de la ventana (320 px es
 * el caso que pide D7/3.8; funciona para cualquier ancho emulado). */
export function anchoExcedeLaVentana(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
}

/** El `outline` calculado del elemento enfocado. "none" es la señal de que
 * el foco no se ve (D7: "contorno calculado distinto de `none`"). */
export async function contornoDeFocoCalculado(page: Page, selector: string): Promise<string> {
  await page.locator(selector).focus();
  return page.evaluate((sel) => {
    const elemento = document.querySelector(sel);
    if (!(elemento instanceof HTMLElement)) {
      throw new Error(`no se encontró ${sel}`);
    }
    return getComputedStyle(elemento).outlineStyle;
  }, selector);
}

/** El `outline` calculado de QUIEN TENGA el foco en este momento (tarea
 * 5.1: recorrido real con `Tab`, sin saber de antemano qué selector va a
 * recibirlo — a diferencia de `contornoDeFocoCalculado`, que enfoca un
 * elemento puntual). */
export function contornoDelElementoEnfocado(page: Page): Promise<string> {
  return page.evaluate(() => {
    const elemento = document.activeElement;
    if (!(elemento instanceof HTMLElement)) {
      return "none";
    }
    return getComputedStyle(elemento).outlineStyle;
  });
}

/** `true` si `Tab` ya no tiene a dónde ir y el foco volvió a `<body>`
 * (tarea 5.1): una pantalla puede tener menos de tres controles
 * enfocables a propósito (p.ej. "sin permiso"/"sin sesión", D8 — ninguna
 * de las dos pide un enlace), y eso NO es "foco invisible", es que el
 * recorrido de teclado ya terminó. */
export function elFocoVolvioAlCuerpo(page: Page): Promise<boolean> {
  return page.evaluate(() => document.activeElement === document.body);
}
