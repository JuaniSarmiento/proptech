import { expect, test } from "./prueba";

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
