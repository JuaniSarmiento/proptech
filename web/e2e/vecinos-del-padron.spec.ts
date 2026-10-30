import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { EDIFICIO_API } from "./api-falsa";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

const DIR = resolve("../.git/informes-2b/pantallas");

for (const ancho of [1440, 320]) {
  test(`7.4 vecinos en el padrón: columna, panel y alta, a ${ancho}`, async ({ page }) => {
    await page.setViewportSize({ width: ancho, height: 900 });
    await page.goto(`/edificios/${EDIFICIO_API}/unidades`);
    await expect(page.getByRole("columnheader", { name: "Vecinos" })).toBeVisible();
    const fila1A = page.getByRole("row", { name: /^1A/ });
    await expect(fila1A).toContainText("1 (1 pendiente)");

    await page.getByRole("button", { name: "1A", exact: true }).click();
    const panel = page.getByRole("dialog", { name: "Editar unidad" });
    await expect(panel.getByRole("heading", { name: "Vecinos" })).toBeVisible();
    await expect(panel.getByText("Deco Vecino")).toBeVisible();
    await expect(panel.getByText(/Propietario.*Pendiente/)).toBeVisible();

    mkdirSync(DIR, { recursive: true });
    await sinViolacionesEnElNavegador(page);
    await page.screenshot({ path: `${DIR}/vecinos-${ancho}.png`, fullPage: true });

    // Error asociado al campo (formato inválido para el servidor, válido
    // para el navegador: mismo gotcha que en `personal.spec.ts`).
    await panel.getByLabel("Nombre del vecino", { exact: true }).fill("Nuevo Vecino");
    await panel.getByLabel("Email del vecino", { exact: true }).fill("invalido@test");
    await panel.getByRole("button", { name: "Agregar vecino" }).click();
    await expect(panel.getByRole("link", { name: "Este valor no es válido." })).toBeVisible();

    await panel.getByLabel("Email del vecino", { exact: true }).fill("nuevo@test.com");
    await panel.getByRole("button", { name: "Agregar vecino" }).click();
    await expect(panel.getByRole("alert", { name: "Resumen de errores" })).toHaveCount(0);
  });
}

test("7.4 revocar y quitar un vecino", async ({ page }) => {
  await page.goto(`/edificios/${EDIFICIO_API}/unidades`);
  await page.getByRole("button", { name: "1A", exact: true }).click();
  const panel = page.getByRole("dialog", { name: "Editar unidad" });
  const filaVecino = panel.locator("li", { hasText: "Deco Vecino" });
  await filaVecino.getByRole("button", { name: "Revocar" }).click();
  await expect(filaVecino.getByText("Revocada")).toBeVisible();
  await filaVecino.getByRole("button", { name: "Quitar" }).click();
  await expect(filaVecino.getByText("Quitado")).toBeVisible();
});

test("7.4 sin permiso para leer personal: padrón normal, sin columna ni sección Vecinos", async ({
  page,
  context,
  baseURL,
}) => {
  await context.clearCookies();
  // R2B-4: una sola lectura del reloj para iat y __client_uat.
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub: "user_sin_permiso" });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL! },
    { name: "__client_uat", value: clientUat, url: baseURL! },
  ]);
  await page.goto(`/edificios/${EDIFICIO_API}/unidades`);
  await expect(page.getByRole("heading", { name: "Padrón de unidades" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Vecinos" })).toHaveCount(0);
  // D11/7.6: sin acciones, el identificador sigue siendo lectura, no edición.
  await expect(page.getByRole("row", { name: /^1A/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "1A", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Agregar unidad" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Guardar" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Agregar vecino" })).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
