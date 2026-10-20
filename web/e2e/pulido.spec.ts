/**
 * Pulido visual del 3b (19/10/2026): lo que sólo se ve con layout real. Un
 * test de componente en jsdom no calcula cajas ni estilos: el menú "en una
 * sola línea", el estado pegado a su paso y el panel "lateral" que caía en
 * el flujo debajo de la tabla pasaron todas las suites anteriores.
 */

import { expect, type Page, test } from "@playwright/test";

const _ID_NORMAL = "f760ca3b-7331-4927-96e5-54a3fbb1f3ae";

async function caja(page: Page, selector: string) {
  const elemento = page.locator(selector).first();
  await elemento.waitFor({ state: "visible" });
  const box = await elemento.boundingBox();
  if (!box) throw new Error(`sin caja: ${selector}`);
  return box;
}

test.describe("pulido 3b a 1280 px", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
  });

  test("el menú lateral apila sus secciones, una debajo de la otra", async ({ page }) => {
    await page.goto(`/edificios/${_ID_NORMAL}`);
    // `evaluateAll` no espera: sin esto puede leer el esqueleto de
    // `loading.tsx` (sin menú) antes de que llegue la pantalla.
    await page.waitForLoadState("networkidle");
    const enlaces = page
      .getByRole("navigation", { name: "Secciones del edificio" })
      .getByRole("link");
    const cajas = await enlaces.evaluateAll((nodos) =>
      nodos
        .map((n) => n.getBoundingClientRect())
        .map((r) => ({ top: r.top, bottom: r.bottom, left: r.left })),
    );
    expect(cajas.length).toBe(5);
    for (let i = 1; i < cajas.length; i += 1) {
      expect(cajas[i]?.top ?? 0).toBeGreaterThanOrEqual((cajas[i - 1]?.bottom ?? 0) - 1);
      expect(cajas[i]?.left).toBe(cajas[0]?.left);
    }
  });

  test("en el checklist, el estado queda separado de la etiqueta del paso", async ({ page }) => {
    await page.goto(`/edificios/${_ID_NORMAL}`);
    const enlace = await caja(page, ".resumen__paso a");
    const estado = await caja(page, ".resumen__estado");
    expect(estado.x).toBeGreaterThanOrEqual(enlace.x + enlace.width + 16);
  });

  test("el panel lateral flota pegado al borde derecho, fuera del flujo", async ({ page }) => {
    await page.goto(`/edificios/${_ID_NORMAL}/unidades`);
    await page.getByRole("button", { name: "Agregar unidad" }).click();
    const panel = page.getByRole("dialog", { name: "Agregar unidad" });
    expect(await panel.evaluate((n) => getComputedStyle(n).position)).toBe("fixed");
    const box = await panel.boundingBox();
    expect(Math.round((box?.x ?? 0) + (box?.width ?? 0))).toBe(1280);
  });

  test("en el padrón, los textos van a la izquierda y los números a la derecha", async ({
    page,
  }) => {
    await page.goto(`/edificios/${_ID_NORMAL}/unidades`);
    const alineacion = (sel: string) =>
      page
        .locator(sel)
        .first()
        .evaluate((n) => getComputedStyle(n).textAlign);
    expect(["left", "start"]).toContain(await alineacion(".padron-de-unidades th"));
    expect(["left", "start"]).toContain(await alineacion(".padron-de-unidades td"));
    expect(await alineacion(".padron-de-unidades td.numero-tabular")).toBe("right");
  });
});

/**
 * Rediseño a todo el ancho (enmienda del shape, 20/10/2026): lo que sólo
 * se ve con layout real. La ayuda acoplada EMPUJA el contenido (no lo
 * tapa), el contenido usa el ancho de la ventana y no una columna angosta,
 * y a 320 px la ayuda cae en el flujo a todo el ancho.
 */
test.describe("rediseño a todo el ancho", () => {
  test("a 1440 px el contenido ocupa el ancho disponible, sin columna angosta", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/edificios/${_ID_NORMAL}`);
    await page.waitForLoadState("networkidle");
    const main = await caja(page, "main");
    const menu = await caja(page, ".menu-del-edificio");
    // el <main> arranca donde termina el menú y llega al borde derecho
    expect(Math.round(main.x)).toBe(Math.round(menu.x + menu.width));
    expect(Math.round(main.x + main.width)).toBe(1440);
    // y el panel principal más la columna de apoyo van lado a lado
    const principal = await caja(page, ".disposicion > .panel");
    const apoyo = await caja(page, ".disposicion__lateral");
    expect(apoyo.x).toBeGreaterThan(principal.x + principal.width);
  });

  test("la ayuda acoplada empuja el contenido y conserva el foco en su botón", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/edificios/${_ID_NORMAL}/unidades`);
    await page.waitForLoadState("networkidle");
    const mainAntes = await caja(page, "main");
    const boton = page.getByRole("button", { name: "Ayuda", exact: true });
    await boton.click();
    const ayuda = page.getByRole("region", { name: "Ayuda: para qué sirve esta pantalla" });
    await expect(ayuda).toBeVisible();
    await expect(boton).toBeFocused();

    const panel = await ayuda.boundingBox();
    const main = await caja(page, "main");
    const tabla = await caja(page, ".padron-de-unidades");
    if (!panel) throw new Error("sin caja: ayuda");
    expect(Math.round(panel.x + panel.width)).toBe(1440);
    // empuja: el contenido se angostó lo que ocupa la ayuda, y nada del
    // contenido queda debajo de ella (la columna de apoyo baja, por eso la
    // tabla puede quedar incluso más ancha que antes)
    expect(Math.round(main.width)).toBe(Math.round(mainAntes.width - panel.width));
    expect(tabla.x + tabla.width).toBeLessThanOrEqual(panel.x);

    // sigue abierta mientras se trabaja: abrir "Agregar unidad" no la cierra,
    // y el panel lateral se corre a su izquierda en vez de taparla
    await page.getByRole("button", { name: "Agregar unidad" }).first().click();
    const formulario = await page.getByRole("dialog", { name: "Agregar unidad" }).boundingBox();
    await expect(ayuda).toBeVisible();
    expect((formulario?.x ?? 0) + (formulario?.width ?? 0)).toBeLessThanOrEqual(panel.x + 1);
  });

  test("a 320 px la ayuda abierta queda en el flujo, a todo el ancho y sin scroll horizontal", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await page.goto(`/edificios/${_ID_NORMAL}/unidades`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Ayuda", exact: true }).click();
    const ayuda = page.getByRole("region", { name: "Ayuda: para qué sirve esta pantalla" });
    expect(await ayuda.evaluate((n) => getComputedStyle(n).position)).toBe("static");
    const box = await ayuda.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(280);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth),
    ).toBe(false);
  });

  test('el resumen muestra la barra "N de 6 pasos" y el formulario de configuración usa todo el ancho', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`/edificios/${_ID_NORMAL}`);
    await expect(page.getByRole("progressbar", { name: /de 6 pasos/ })).toBeVisible();

    await page.goto(`/edificios/${_ID_NORMAL}/configuracion`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Cambiar configuración" }).click();
    const formulario = await page
      .getByRole("dialog", { name: "Cambiar configuración" })
      .boundingBox();
    const main = await caja(page, "main");
    // más que la vieja hoja de 28rem: ocupa el ancho del contenido
    expect(formulario?.width ?? 0).toBeGreaterThan(main.width * 0.85);
    const tasa = await caja(page, "#campo-tasa_mensual");
    const rige = await caja(page, "#campo-vigente_desde");
    expect(Math.round(tasa.y)).toBe(Math.round(rige.y)); // campos en columnas
  });
});
