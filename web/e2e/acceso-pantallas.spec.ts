import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

// 2d/7.8 (D10): sin el claim de email en el token de prueba (`sesion-local.ts`
// no lo manda), el mensaje de rechazo con sesión es el genérico.
const mensaje =
  "Este enlace no sirve con la cuenta con la que ingresaste. Si la invitación es para otro " +
  "email, usá otra cuenta; si es para ésta, pedile a tu administración que te invite de nuevo.";
for (const ancho of [1440, 320]) {
  test(`7.1 ingreso sin Clerk, selector, invitación y barra a ${ancho}`, async ({
    page,
    context,
    baseURL,
  }) => {
    await page.setViewportSize({ width: ancho, height: 900 });
    await context.clearCookies();
    await page.goto("/ingresar");
    await expect(page.getByRole("heading", { name: "Ingresar", exact: true })).toBeVisible();
    await expect(page.getByText("No pudimos conectar con el servicio de ingreso.")).toBeVisible({
      timeout: 15000,
    });
    const dir = resolve("../.git/informes-2b/pantallas");
    mkdirSync(dir, { recursive: true });
    await sinViolacionesEnElNavegador(page);
    await page.screenshot({ path: `${dir}/ingresar-${ancho}.png`, fullPage: true });
    // R2B-4: una sola lectura del reloj para iat y __client_uat.
    const { session, clientUat } = cookiesDeContextoDePrueba({ sub: "user_varias" });
    await context.addCookies([
      { name: "__session", value: session, url: baseURL! },
      { name: "__client_uat", value: clientUat, url: baseURL! },
    ]);
    await page.goto("/elegir-administracion");
    await expect(page.getByRole("heading", { name: "Elegí una administración" })).toBeVisible();
    await sinViolacionesEnElNavegador(page);
    await page.screenshot({ path: `${dir}/selector-${ancho}.png`, fullPage: true });
    await page.getByRole("button", { name: "Administración de prueba", exact: true }).click();
    await expect(page).toHaveURL(/edificios$/);
    await expect(page.getByRole("banner")).toContainText("Persona de prueba");
    await page.locator(".cuenta-en-barra summary").click();
    await expect(page.getByRole("link", { name: "Cambiar de administración" })).toBeVisible();
    await page.screenshot({ path: `${dir}/barra-${ancho}.png`, fullPage: true });
    await page.goto("/invitacion/sobre-valido");
    await expect(page.getByRole("heading", { name: "Aceptá tu invitación" })).toBeVisible();
    await expect(page.getByText("Administración de prueba", { exact: true })).toHaveCount(0);
    await sinViolacionesEnElNavegador(page);
    await page.screenshot({ path: `${dir}/invitacion-${ancho}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      ancho,
    );
    await page.getByRole("button", { name: "Aceptar e ingresar", exact: true }).click();
    await expect(page).toHaveURL(/elegir-administracion\?aceptada=1/);
    await expect(page.getByText("Invitación aceptada.", { exact: true })).toBeVisible();
  });
}
for (const sobre of ["sobre-vencido", "sobre-usado", "sobre-revocado", "email-distinto"]) {
  test(`7.1 rechazo uniforme: ${sobre}, sin recursos de terceros`, async ({ page }) => {
    const terceros: string[] = [];
    page.on("request", (r) => {
      if (!r.url().startsWith("http://127.0.0.1:")) terceros.push(r.url());
    });
    const res = await page.goto(`/invitacion/${sobre}`);
    expect(res?.headers()["referrer-policy"]).toBe("no-referrer");
    expect(res?.headers()["cache-control"]).toContain("no-store");
    await page.getByRole("button", { name: "Aceptar e ingresar" }).click();
    await expect(page.getByRole("alert").filter({ hasText: mensaje })).toHaveText(mensaje);
    await expect(page.getByRole("link", { name: "Usar otra cuenta" })).toBeVisible();
    expect(terceros).toEqual([]);
  });
}
test("7.1 una sola entra directo, cookie httpOnly y salida disponible", async ({
  page,
  context,
}) => {
  await page.goto("/elegir-administracion");
  await expect(page).toHaveURL(/edificios$/);
  expect(
    (await context.cookies()).find((c) => c.name === "proptech_administracion")?.httpOnly,
  ).toBe(true);
  await page.locator(".cuenta-en-barra summary").click();
  await expect(page.getByRole("link", { name: "Cerrar sesión" })).toBeVisible();
});
