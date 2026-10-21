import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

const DIR = resolve("../.git/informes-2b/pantallas");

for (const ancho of [1440, 320]) {
  test(`7.3 personal: lista, estado fallida ofrece revocar e invitar de nuevo, a ${ancho}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: ancho, height: 900 });
    await page.goto("/personal");
    await expect(page.getByRole("heading", { name: "Personal", exact: true })).toBeVisible();
    await expect(page.getByText("Ana Superadmin")).toBeVisible();
    await expect(page.getByText("Beto Contador")).toBeVisible();
    // Corrección L-026 (21/10/2026): `_PERSONAL_DE_PRUEBA` también trae a
    // "Deco Vecino" (rol "vecino"), igual que puede traer la API real
    // (misma fuente que el padrón de 7.4). Personal es sólo personal.
    await expect(page.getByText("Deco Vecino")).toHaveCount(0);
    await expect(page.getByText(/^vecino$/i)).toHaveCount(0);
    // Ajuste del shape (21/10/2026), corregido por el auditor del 2b (fila 2): sin
    // "Reenviar" ni "Reintentar"; el worker NO reintenta un 4xx definitivo.
    await expect(page.getByText("No se pudo enviar. Revocala e invitá de nuevo.")).toBeVisible();
    await expect(page.getByRole("button", { name: /reenviar/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /reintentar/i })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      ancho,
    );
    mkdirSync(DIR, { recursive: true });
    await sinViolacionesEnElNavegador(page);
    await page.screenshot({ path: `${DIR}/personal-${ancho}.png`, fullPage: true });
  });
}

test("7.3 invitar con éxito refresca la lista; error de email queda asociado al campo y con foco", async ({
  page,
}) => {
  await page.goto("/personal");
  await page.getByRole("button", { name: "Invitar a alguien" }).click();
  const dialogo = page.getByRole("dialog", { name: "Invitar a alguien" });
  await dialogo.getByLabel("Nombre", { exact: true }).fill("Nueva Persona");
  // Formato válido para el navegador (type="email" bloquearía el submit
  // antes de llegar al server), inválido para el servidor (sin punto).
  await dialogo.getByLabel("Email", { exact: true }).fill("invalida@test");
  await dialogo.getByRole("combobox", { name: "Perfil", exact: true }).selectOption("contador");
  await dialogo.getByRole("combobox", { name: "Alcance", exact: true }).selectOption("edificio");
  await dialogo
    .getByRole("combobox", { name: "Edificio", exact: true })
    .selectOption({ label: "Edificio API" });
  await dialogo.getByRole("button", { name: "Invitar" }).click();
  const enlaceDeError = dialogo.getByRole("link", { name: "Este valor no es válido." });
  await expect(enlaceDeError).toBeVisible();
  await enlaceDeError.click();
  await expect(dialogo.getByLabel("Email", { exact: true })).toBeFocused();

  await dialogo.getByLabel("Email", { exact: true }).fill("nueva@test.com");
  await dialogo.getByRole("button", { name: "Invitar" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("7.3 revocar y quitar actualizan la fila sin recargar a mano", async ({ page }) => {
  await page.goto("/personal");
  const filaBeto = page.getByRole("row", { name: /Beto Contador/ });
  await filaBeto.getByRole("button", { name: "Revocar" }).click();
  await expect(filaBeto.getByText("Revocada")).toBeVisible();

  const filaCaro = page.getByRole("row", { name: /Caro Auxiliar/ });
  await filaCaro.getByRole("button", { name: "Quitar" }).click();
  await expect(filaCaro.getByText("Quitada")).toBeVisible();
});

test("7.3 sin permiso: Estados sinPermiso, sin la tabla", async ({ page, context, baseURL }) => {
  await context.clearCookies();
  // R2B-4: una sola lectura del reloj para iat y __client_uat.
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub: "user_sin_permiso" });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL! },
    { name: "__client_uat", value: clientUat, url: baseURL! },
  ]);
  await page.goto("/personal");
  await expect(page.getByRole("heading", { name: /No podés/ })).toBeVisible();
  await expect(page.getByRole("table")).toHaveCount(0);
});
