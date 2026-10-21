import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";

for (const ancho of [1440, 320]) {
  test(`7.2: aviso completo sin sesión, teclado y axe a ${ancho}`, async ({ page, context }) => {
    await context.clearCookies();
    await page.setViewportSize({ width: ancho, height: 900 });
    const respuesta = await page.goto("/privacidad");
    expect(respuesta?.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "Aviso de privacidad", exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Responsable y contacto", { exact: true })).toBeVisible();
    expect(await page.locator("main").textContent()).toContain("fuera de la Argentina");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      ancho,
    );
    await sinViolacionesEnElNavegador(page);
    const dir = resolve("../.git/informes-2b/pantallas");
    mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: `${dir}/privacidad-${ancho}.png`, fullPage: true });
    const ayuda = page.getByRole("button", { name: "Ayuda", exact: true });
    await ayuda.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "¿Y después?" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(ayuda).toBeFocused();
    expect(await ayuda.evaluate((n) => getComputedStyle(n).outlineStyle)).toBe("solid");
  });
}
