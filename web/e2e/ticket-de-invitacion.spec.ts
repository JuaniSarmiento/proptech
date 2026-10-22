import { expect, test } from "./prueba";

// 8.2: Clerk manda el link de invitación con `?__clerk_ticket=<ticket>` y la
// web lo perdía al armar los links hacia /ingresar y /registrarse, por lo
// que <SignUp> nunca lo veía en su URL y una instancia restringida rechazaba
// el registro. Este spec sigue el camino completo que recorrió el bug.
const TICKET = "ticket-de-prueba.abc_123-XYZ";

test("8.2: el __clerk_ticket de la invitación llega hasta 'Crear cuenta desde mi invitación'", async ({
  page,
  context,
}) => {
  await context.clearCookies();
  const respuestaInvitacion = await page.goto(`/invitacion/sobre-valido?__clerk_ticket=${TICKET}`);
  expect(respuestaInvitacion?.headers()["referrer-policy"]).toBe("no-referrer");
  expect(respuestaInvitacion?.headers()["cache-control"]).toContain("no-store");
  await expect(page.getByRole("heading", { name: "Aceptá tu invitación" })).toBeVisible();

  const ingreso = page.getByRole("link", { name: "Aceptar e ingresar" });
  await expect(ingreso).toHaveAttribute("href", new RegExp(`__clerk_ticket=${TICKET}`));
  const registroDesdeInvitacion = page.getByRole("link", {
    name: "creá tu cuenta desde esta invitación",
  });
  await expect(registroDesdeInvitacion).toHaveAttribute(
    "href",
    new RegExp(`__clerk_ticket=${TICKET}`),
  );

  await ingreso.click();
  await expect(page).toHaveURL(/\/ingresar\?/);
  const urlIngreso = new URL(page.url());
  expect(urlIngreso.searchParams.get("__clerk_ticket")).toBe(TICKET);
  expect(urlIngreso.searchParams.get("regreso")).toBe("/invitacion/sobre-valido");

  const crearCuenta = page.getByRole("link", { name: "Crear cuenta desde mi invitación" });
  await expect(crearCuenta).toHaveAttribute("href", new RegExp(`__clerk_ticket=${TICKET}`));
  await expect(crearCuenta).toHaveAttribute("href", /regreso=%2Finvitacion%2Fsobre-valido/);
});

test("8.2: /ingresar y /registrarse con __clerk_ticket llevan las mismas cabeceras que /invitacion/", async ({
  page,
  context,
}) => {
  await context.clearCookies();
  const respuestaIngreso = await page.goto(
    `/ingresar?regreso=%2Finvitacion%2Fsobre-valido&__clerk_ticket=${TICKET}`,
  );
  expect(respuestaIngreso?.headers()["referrer-policy"]).toBe("no-referrer");
  expect(respuestaIngreso?.headers()["cache-control"]).toContain("no-store");

  const respuestaRegistro = await page.goto(
    `/registrarse?regreso=%2Finvitacion%2Fsobre-valido&__clerk_ticket=${TICKET}`,
  );
  expect(respuestaRegistro?.headers()["referrer-policy"]).toBe("no-referrer");
  expect(respuestaRegistro?.headers()["cache-control"]).toContain("no-store");
});

test("8.2: sin __clerk_ticket, /ingresar no manda Referrer-Policy: no-referrer de más", async ({
  page,
  context,
}) => {
  await context.clearCookies();
  const respuesta = await page.goto("/ingresar?regreso=%2Fedificios");
  expect(respuesta?.headers()["referrer-policy"]).not.toBe("no-referrer");
});
