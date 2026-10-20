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
