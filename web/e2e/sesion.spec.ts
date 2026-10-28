import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

test("6.1: sesión local abre Mis edificios y el token no está en HTML ni RSC", async ({
  page,
  context,
}) => {
  const token = (await context.cookies()).find((cookie) => cookie.name === "__session")?.value;
  expect(token).toBeTruthy();
  const respuesta = await page.goto("/edificios");
  expect(respuesta?.status()).toBe(200);
  expect(page.url()).toMatch(/\/edificios$/);
  await expect(page.getByRole("heading", { name: "Mis edificios" })).toBeVisible();
  expect(await respuesta?.text()).not.toContain(token);
});
test("6.1: sin sesión lleva al ingreso con el regreso propio", async ({ page, context }) => {
  await context.clearCookies();
  await page.goto("/edificios/00000000-0000-0000-0000-000000000001/unidades");
  await expect(page).toHaveURL(/\/ingresar\?/);
  expect(new URL(page.url()).searchParams.get("regreso")).toBe(
    "/edificios/00000000-0000-0000-0000-000000000001/unidades",
  );
});

test("6.1: el 401 de la API lleva al ingreso y conserva el padrón como regreso", async ({
  page,
}) => {
  const ruta = "/edificios/00000000-0000-0000-0000-000000000006/unidades";
  await page.goto(ruta);
  await expect(page).toHaveURL(/\/ingresar\?/);
  expect(new URL(page.url()).searchParams.get("regreso")).toBe(ruta);
});

test("R2B-4: el fixture de sesión nunca dispara el handshake de Clerk", async ({ page }) => {
  // El rompedor 2b encontró que `prueba.ts` leía el reloj dos veces (una
  // para `crearToken()`, otra para `__client_uat`): si el segundo
  // cambiaba entre medio, @clerk/backend veía `iat < __client_uat` y
  // respondía con un handshake (307) hacia el emisor `.invalid`, que esta
  // suite no sabe resolver. Con `cookiesDeContextoDePrueba` (una sola
  // lectura) ese handshake no tiene que dispararse nunca.
  const motivos: string[] = [];
  page.on("response", (respuesta) => {
    const motivo = respuesta.headers()["x-clerk-auth-reason"];
    if (motivo) motivos.push(motivo);
  });
  const respuesta = await page.goto("/edificios/00000000-0000-0000-0000-000000000001/unidades");
  expect(respuesta?.status(), JSON.stringify(motivos)).toBe(200);
  expect(motivos).toEqual([]);
});

for (const ancho of [320, 1280]) {
  test(`2d sin persona termina sin-acceso y teclado a ${ancho}`, async ({
    page,
    context,
    baseURL,
  }) => {
    const { session, clientUat } = cookiesDeContextoDePrueba({ sub: "user_sin_persona" });
    await context.addCookies([
      { name: "__session", value: session, url: baseURL ?? "http://127.0.0.1:3100" },
      { name: "__client_uat", value: clientUat, url: baseURL ?? "http://127.0.0.1:3100" },
    ]);
    await page.setViewportSize({ width: ancho, height: 900 });
    const navegaciones: string[] = [];
    const respuestas: number[] = [];
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) navegaciones.push(frame.url());
    });
    page.on("response", (r) => {
      if (r.request().isNavigationRequest()) respuestas.push(r.status());
    });
    await page.goto("/edificios");
    await expect(page).toHaveURL(/\/sin-acceso$/);
    await expect(
      page.getByRole("heading", { name: "Tu cuenta no tiene acceso todavía" }),
    ).toBeVisible();
    expect(navegaciones.length).toBeLessThanOrEqual(3);
    // Guarda: el widget real no carga; el anidamiento se prueba en ciclo.test.tsx.
    expect(respuestas).not.toContain(431);
    for (const ruta of navegaciones) {
      const regreso = new URL(ruta).searchParams.get("regreso");
      expect(regreso ?? "").not.toContain("regreso=");
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      ancho,
    );
    await sinViolacionesEnElNavegador(page);
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    for (const nombre of ["Cerrar sesión", "Volver a intentar"]) {
      const accion = page.getByRole("link", { name: nombre });
      await expect(accion).toBeFocused();
      expect(
        await accion.evaluate((n) => parseFloat(getComputedStyle(n).outlineWidth)),
      ).toBeGreaterThan(0);
      expect(await accion.evaluate((n) => getComputedStyle(n).outlineStyle)).not.toBe("none");
      await page.keyboard.press("Tab");
    }
  });
}
test("2d API rechaza: selector se queda y no redirige al ingreso", async ({
  page,
  context,
  baseURL,
}) => {
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub: "user_api_rechaza" });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL ?? "http://127.0.0.1:3100" },
    { name: "__client_uat", value: clientUat, url: baseURL ?? "http://127.0.0.1:3100" },
  ]);
  const ingresos: string[] = [];
  page.on("request", (r) => {
    if (r.isNavigationRequest() && new URL(r.url()).pathname === "/ingresar")
      ingresos.push(r.url());
  });
  await page.goto("/elegir-administracion");
  await expect(page.getByRole("heading", { name: "No pudimos validar tu sesión" })).toBeVisible();
  await expect(page).toHaveURL(/\/elegir-administracion$/);
  expect(ingresos).toEqual([]);
  await expect(page.getByRole("link", { name: "Cerrar sesión" })).toHaveAttribute(
    "href",
    "/ingresar?cerrar=1",
  );
});
