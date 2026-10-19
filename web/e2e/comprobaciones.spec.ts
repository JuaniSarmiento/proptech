/**
 * Prueba los CHEQUEOS genéricos de `comprobaciones.ts` en el navegador
 * real (D7, tarea 3.8), con contenido mínimo propio: el grupo 4 todavía no
 * construyó ninguna pantalla, así que no hay "siete pantallas" contra las
 * que correr todavía (eso es 5.1). Lo que exige esta tarea son los dos
 * rojos del chequeo en sí, y que el chequeo también pase contra la
 * portada real servida por `next start` (prueba que el script arma bien
 * el stack).
 */

import { expect, test } from "@playwright/test";
import { anchoExcedeLaVentana, contornoDeFocoCalculado } from "./comprobaciones";

test.describe("320 px sin scroll horizontal", () => {
  test("la portada real, servida por next start, entra en 320 px", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto("/");
    expect(await anchoExcedeLaVentana(page)).toBe(false);
  });

  test("ROJO a propósito: el chequeo detecta un elemento de 400 px puesto adrede", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.setContent('<div style="width:400px;height:10px;">demasiado ancho</div>');
    expect(await anchoExcedeLaVentana(page)).toBe(true);
  });
});

test.describe("foco visible", () => {
  test("un botón con el contorno por defecto del navegador se ve enfocado", async ({ page }) => {
    await page.setContent('<button id="normal">Guardar</button>');
    expect(await contornoDeFocoCalculado(page, "#normal")).not.toBe("none");
  });

  test("ROJO a propósito: el chequeo detecta outline:none puesto adrede", async ({ page }) => {
    await page.setContent('<button id="sin-foco" style="outline:none">Guardar</button>');
    expect(await contornoDeFocoCalculado(page, "#sin-foco")).toBe("none");
  });
});

test("prefers-reduced-motion deja --duracion-transicion en 0ms en la portada real", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const duracion = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue("--duracion-transicion").trim(),
  );
  // El navegador normaliza un `<time>` en cero a "0s" al leerlo de vuelta,
  // sin importar la unidad del CSS fuente ("0ms" en `tokens.css`): no es
  // un error del token, es cómo CSSOM serializa cero (gotcha real, visto
  // fallar antes de corregir esta aserción).
  expect(duracion).toBe("0s");
});
