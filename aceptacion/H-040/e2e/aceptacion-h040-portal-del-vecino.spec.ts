/**
 * Aceptación de H-040 · las pantallas del portal del vecino y la app instalable en navegador real
 * (C01 a C05, N01 a N04).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts` y `web/e2e/escenarios-portal.ts`, que escribe la aceptación)
 * con las formas y los filtros EXACTOS de las rutas reales de H-038 y H-039 (L-107). Los textos, roles y rutas son
 * los de `aceptacion/H-040/CONTRATO.md`. Locators exactos (L-085). Cada test abre con una verificación de
 * visibilidad de la pantalla, para que falle por aserción y no por un timeout de acción.
 *
 * Ana (`user_vecino_portal`): `9A` (Otro Edificio Ficticio), `1A` y `2B` (Torre Ficticia), propietaria.
 * Beto (`user_inquilino_portal`): `1B` (Torre Ficticia), inquilino.
 */

import type { BrowserContext, Page } from "@playwright/test";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

const TORRE = "00000000-0000-0000-0000-000000004001";
const U1A = "00000000-0000-0000-0000-000000004101";
const U1B = "00000000-0000-0000-0000-000000004102";
const U2B = "00000000-0000-0000-0000-000000004103";
const U9A = "00000000-0000-0000-0000-000000004104";
const NOV = "00000000-0000-0000-0000-000000004201";
const OCT = "00000000-0000-0000-0000-000000004202";
/** La liquidación que no existe para nadie (un UUID bien formado). */
const INEXISTENTE = "00000000-0000-0000-0000-000000004299";
/** El edificio de pagos de la API falsa de H-025, donde `user_vecina` informa pagos. */
const PAGOS = "00000000-0000-0000-0000-000000002501";

const ANA = "user_vecino_portal";
const BETO = "user_inquilino_portal";

async function como(context: BrowserContext, baseURL: string | undefined, sub: string) {
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL! },
    { name: "__client_uat", value: clientUat, url: baseURL! },
  ]);
}

const inicio = "/inicio";
const liquidaciones = (u: string) => `/mis-liquidaciones/${u}`;
const expensa = (u: string, l: string) => `/mis-liquidaciones/${u}/${l}`;
const comprobantes = "/comprobantes";

const menu = (page: Page) =>
  page.getByRole("navigation", { name: "Portal del vecino", exact: true });
const titulo = (page: Page, nombre: string) =>
  page.getByRole("heading", { name: nombre, exact: true, level: 1 });

async function abrir(page: Page, ruta: string, nombre: string) {
  await page.goto(ruta);
  await expect(titulo(page, nombre)).toBeVisible();
}

/** El valor (`dd`) de una cifra rotulada (`dt`) dentro de `contenedor`. */
function cifra(contenedor: ReturnType<Page["locator"]>, rotulo: string) {
  return contenedor
    .locator("dt")
    .filter({ hasText: new RegExp(`^\\s*${rotulo}\\s*$`) })
    .first()
    .locator("xpath=following-sibling::dd[1]");
}

const unidades = (page: Page) => page.getByRole("list", { name: "Mis unidades", exact: true });
const fila = (page: Page, identificador: string) =>
  unidades(page)
    .getByRole("listitem")
    .filter({
      has: page.getByRole("link", { name: `Ver liquidaciones de ${identificador}`, exact: true }),
    });

// --- C01 --------------------------------------------------------------------------------------------------

test("C01 · el inicio lista todas las unidades de la persona, de todos sus edificios, con total, vencimiento y créditos", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  const items = unidades(page).getByRole("listitem");
  await expect(items).toHaveCount(3);
  // El orden de la API: por edificio y, dentro, por identificador.
  await expect(items.nth(0)).toContainText("9A");
  await expect(items.nth(0)).toContainText("Otro Edificio Ficticio");
  await expect(items.nth(1)).toContainText("1A");
  await expect(items.nth(2)).toContainText("2B");
  await expect(items.nth(1)).toContainText("Torre Ficticia");
  await expect(items.nth(1)).toContainText("Propietario");

  const una = fila(page, "1A");
  await expect(cifra(una, "Total a pagar")).toHaveText("46.500,00");
  await expect(cifra(una, "Vencimiento")).toHaveText("10/11/2026");
  await expect(cifra(una, "Crédito aplicable")).toHaveText("0,00");
  await expect(cifra(una, "Crédito retenido")).toHaveText("0,00");

  // 2B: cada crédito en su cifra, el retenido nunca descuenta el total.
  const dos = fila(page, "2B");
  await expect(cifra(dos, "Total a pagar")).toHaveText("40.250,00");
  await expect(cifra(dos, "Vencimiento")).toHaveText("10/11/2026");
  await expect(cifra(dos, "Crédito aplicable")).toHaveText("1.200,00");
  await expect(cifra(dos, "Crédito retenido")).toHaveText("800,50");

  // 9A: sin deuda ni vencimiento.
  const nueve = fila(page, "9A");
  await expect(cifra(nueve, "Total a pagar")).toHaveText("0,00");
  await expect(cifra(nueve, "Vencimiento")).toHaveText("Sin vencimiento");
});

test("C01 · el total del conjunto lo da la API, con el crédito aplicable y el retenido por separado", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  const conjunto = page.getByRole("region", { name: "Total del conjunto", exact: true });
  await expect(conjunto).toBeVisible();
  await expect(cifra(conjunto, "Total a pagar")).toHaveText("86.750,01");
  await expect(cifra(conjunto, "Intereses")).toHaveText("1.250,00");
  await expect(cifra(conjunto, "Crédito aplicable")).toHaveText("1.200,00");
  await expect(cifra(conjunto, "Crédito retenido")).toHaveText("800,50");
});

// --- C02 --------------------------------------------------------------------------------------------------

test("C02 · una unidad muestra sus liquidaciones, la más nueva primero, y cada una abre su expensa", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  await page.getByRole("link", { name: "Ver liquidaciones de 1A", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${liquidaciones(U1A)}$`));
  await expect(titulo(page, "Liquidaciones de 1A")).toBeVisible();
  const lista = page.getByRole("list", { name: "Liquidaciones", exact: true });
  const items = lista.getByRole("listitem");
  await expect(items).toHaveCount(2);
  await expect(items.nth(0)).toContainText("noviembre de 2026");
  await expect(items.nth(0)).toContainText("10/11/2026");
  await expect(items.nth(0)).toContainText("46.500,00");
  await expect(items.nth(1)).toContainText("octubre de 2026");
  await expect(items.nth(1)).toContainText("31.200,00");
  await items
    .nth(0)
    .getByRole("link", { name: "Ver expensa de noviembre de 2026", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`${expensa(U1A, NOV)}$`));
  await expect(titulo(page, "Expensa de noviembre de 2026")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Volver a las liquidaciones de 1A", exact: true }),
  ).toBeVisible();
});

test("C02 · la expensa se explica por categoría y por grupo, y cierra con el detalle de la unidad", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, expensa(U1A, NOV), "Expensa de noviembre de 2026");

  const ordinarios = page.getByRole("region", { name: "Gastos ordinarios", exact: true });
  await expect(ordinarios).toContainText("Subtotal");
  await expect(ordinarios).toContainText("140.000,00");
  const categoriasOrdinarias = ordinarios.getByRole("listitem");
  await expect(categoriasOrdinarias).toHaveCount(2);
  await expect(categoriasOrdinarias.filter({ hasText: "Limpieza" })).toContainText("100.000,00");
  await expect(categoriasOrdinarias.filter({ hasText: "Limpieza" })).toContainText("71,43 %");
  await expect(categoriasOrdinarias.filter({ hasText: "Ascensor" })).toContainText("40.000,00");
  await expect(categoriasOrdinarias.filter({ hasText: "Ascensor" })).toContainText("28,57 %");

  const extraordinarios = page.getByRole("region", { name: "Gastos extraordinarios", exact: true });
  await expect(extraordinarios).toContainText("50.000,00");
  await expect(extraordinarios.getByRole("listitem").filter({ hasText: "Pintura" })).toContainText(
    "100,00 %",
  );

  const grupos = page.getByRole("region", { name: "Por grupo de reparto", exact: true });
  const generales = grupos.getByRole("listitem").filter({ hasText: "Generales" });
  await expect(generales).toHaveCount(1);
  await expect(generales).toContainText("Ordinaria 30.000,00");
  await expect(generales).toContainText("Extraordinaria 15.000,00");

  const tabla = page.getByRole("table", { name: "Tu expensa", exact: true });
  await expect(tabla.getByRole("row", { name: /^Ordinaria 30\.000,00$/ })).toBeVisible();
  await expect(tabla.getByRole("row", { name: /^Fondo de reserva 1\.500,00$/ })).toBeVisible();
  await expect(tabla.getByRole("row", { name: /^Extraordinaria 15\.000,00$/ })).toBeVisible();
  await expect(tabla.getByRole("row", { name: /^Intereses 0,00$/ })).toBeVisible();
  await expect(tabla.getByRole("row", { name: /^Total 46\.500,00$/ })).toBeVisible();

  // Un cargo particular propio y los dos grupos de 2B y 1B.
  await abrir(page, expensa(U2B, NOV), "Expensa de noviembre de 2026");
  const gruposDeDos = page.getByRole("region", { name: "Por grupo de reparto", exact: true });
  await expect(gruposDeDos.getByRole("listitem")).toHaveCount(2);
  await expect(gruposDeDos.getByRole("listitem").filter({ hasText: "Ascensor" })).toContainText(
    "Ordinaria 20.000,00",
  );
  await expect(
    page
      .getByRole("table", { name: "Tu expensa", exact: true })
      .getByRole("row", { name: /^Intereses 1\.250,00$/ }),
  ).toBeVisible();
});

test("C02 · la expensa se compara con el mes anterior; sin anterior lo dice", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, expensa(U1A, NOV), "Expensa de noviembre de 2026");
  const comparacion = page.getByRole("region", {
    name: "Comparación con el mes anterior",
    exact: true,
  });
  await expect(
    comparacion.getByRole("heading", { name: "Comparación con octubre de 2026", exact: true }),
  ).toBeVisible();
  await expect(cifra(comparacion, "Total del mes anterior")).toHaveText("31.200,00");
  // N02: la diferencia es la de la API (un centavo más que la cuenta a propósito).
  await expect(cifra(comparacion, "Diferencia")).toHaveText("15.300,01");
  const tabla = comparacion.getByRole("table", { name: "Comparación por categoría", exact: true });
  await expect(
    tabla.getByRole("row", { name: /^Limpieza 100\.000,00 80\.000,00 20\.000,00$/ }),
  ).toBeVisible();
  await expect(
    tabla.getByRole("row", { name: /^Ascensor 40\.000,00 0,00 40\.000,00$/ }),
  ).toBeVisible();
  await expect(
    tabla.getByRole("row", { name: /^Pintura 50\.000,00 20\.000,00 30\.000,00$/ }),
  ).toBeVisible();

  // Octubre es la primera: no hay con qué comparar.
  await abrir(page, expensa(U1A, OCT), "Expensa de octubre de 2026");
  await expect(
    page.getByRole("status").filter({ hasText: "No hay una liquidación anterior para comparar." }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Comparación con el mes anterior", exact: true }),
  ).toHaveCount(0);
});

// --- C03 --------------------------------------------------------------------------------------------------

test("C03 · los PDFs de cada unidad bajan por el enlace firmado desde la web, nunca desde /api", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, comprobantes, "Comprobantes");
  const una = page.getByRole("region", { name: "Comprobantes de 1A", exact: true });
  await expect(una).toBeVisible();
  const pdfs = una.getByRole("list", { name: "PDFs de 1A", exact: true });
  await expect(pdfs.getByRole("listitem")).toHaveCount(1);
  const enlace = pdfs.getByRole("link", {
    name: "Descargar PDF de noviembre de 2026",
    exact: true,
  });
  await expect(enlace).toBeVisible();
  const href = await enlace.getAttribute("href");
  expect(href).toMatch(/^\/documentos\/descarga\?token=[A-Za-z0-9_-]+\.[0-9a-f]{64}$/);
  const bajado = await page.request.get(href ?? "");
  expect(bajado.status()).toBe(200);
  expect(bajado.headers()["content-type"]).toContain("application/pdf");
  expect(bajado.headers()["content-disposition"]).toContain("attachment");
  expect((await bajado.body()).subarray(0, 4).toString()).toBe("%PDF");

  // Otra unidad, otra región; y la que no tiene nada lo dice.
  await expect(
    page.getByRole("region", { name: "Comprobantes de 2B", exact: true }).getByRole("link", {
      name: "Descargar PDF de noviembre de 2026",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "Comprobantes de 9A", exact: true })
      .getByRole("status")
      .filter({
        hasText: "No hay PDFs disponibles.",
      }),
  ).toBeVisible();
});

test("C03 · los pagos confirmados de cada unidad se listan con fecha, banco, operación e importe", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, comprobantes, "Comprobantes");
  const una = page.getByRole("region", { name: "Comprobantes de 1A", exact: true });
  const pagos = una.getByRole("list", { name: "Pagos confirmados de 1A", exact: true });
  const items = pagos.getByRole("listitem");
  await expect(items).toHaveCount(2);
  // Del más nuevo al más viejo.
  await expect(items.nth(0)).toContainText("05/11/2026");
  await expect(items.nth(0)).toContainText("Banco Nación");
  await expect(items.nth(0)).toContainText("OP-0001");
  await expect(items.nth(0)).toContainText("10.000,00");
  await expect(items.nth(1)).toContainText("03/11/2026");
  await expect(items.nth(1)).toContainText("OP-0002");
  await expect(items.nth(1)).toContainText("1.000,00");
  // El pago de dos unidades: en 2B, su parte.
  const dos = page
    .getByRole("region", { name: "Comprobantes de 2B", exact: true })
    .getByRole("list", { name: "Pagos confirmados de 2B", exact: true });
  await expect(dos.getByRole("listitem")).toHaveCount(1);
  await expect(dos.getByRole("listitem")).toContainText("5.000,00");
  await expect(
    page
      .getByRole("region", { name: "Comprobantes de 9A", exact: true })
      .getByRole("status")
      .filter({
        hasText: "No hay pagos confirmados.",
      }),
  ).toBeVisible();
});

// --- C04 --------------------------------------------------------------------------------------------------

test("C04 · el menú del vecino suma Inicio, Mis liquidaciones y Comprobantes junto a Mis pagos", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, BETO);
  await abrir(page, inicio, "Inicio");
  const m = menu(page);
  await expect(m).toBeVisible();
  await expect(m.getByRole("link", { name: "Inicio", exact: true })).toHaveAttribute(
    "href",
    inicio,
  );
  await expect(m.getByRole("link", { name: "Inicio", exact: true })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(m.getByRole("link", { name: "Mis liquidaciones", exact: true })).toHaveAttribute(
    "href",
    "/mis-liquidaciones",
  );
  await expect(m.getByRole("link", { name: "Comprobantes", exact: true })).toHaveAttribute(
    "href",
    comprobantes,
  );
  // Mis pagos es del edificio (el de la primera unidad de la lista).
  await expect(m.getByRole("link", { name: "Mis pagos", exact: true })).toHaveAttribute(
    "href",
    `/edificios/${TORRE}/mis-pagos`,
  );

  await m.getByRole("link", { name: "Mis liquidaciones", exact: true }).click();
  await expect(titulo(page, "Mis liquidaciones")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Ver liquidaciones de 1B", exact: true }),
  ).toBeVisible();
  await expect(
    menu(page).getByRole("link", { name: "Mis liquidaciones", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await menu(page).getByRole("link", { name: "Comprobantes", exact: true }).click();
  await expect(titulo(page, "Comprobantes")).toBeVisible();
  await menu(page).getByRole("link", { name: "Inicio", exact: true }).click();
  await expect(titulo(page, "Inicio")).toBeVisible();
});

test("C04 · dentro de un edificio, quien informa pagos ve las tres secciones del portal junto a Mis pagos", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_vecina");
  await page.goto(`/edificios/${PAGOS}/mis-pagos`);
  await expect(page.getByRole("heading", { name: "Mis pagos", level: 1 })).toBeVisible();
  const m = page.getByRole("navigation", { name: "Secciones del edificio", exact: true });
  await expect(m.getByRole("link", { name: "Mis pagos", exact: true })).toBeVisible();
  await expect(m.getByRole("link", { name: "Inicio", exact: true })).toHaveAttribute(
    "href",
    inicio,
  );
  await expect(m.getByRole("link", { name: "Mis liquidaciones", exact: true })).toHaveAttribute(
    "href",
    "/mis-liquidaciones",
  );
  await expect(m.getByRole("link", { name: "Comprobantes", exact: true })).toHaveAttribute(
    "href",
    comprobantes,
  );
});

// --- C05 --------------------------------------------------------------------------------------------------

test("C05 · el manifest dice nombre, íconos y colores, y lo baja cualquiera sin sesión", async ({
  page,
  context,
  baseURL,
  request,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
    "href",
    "/manifest.webmanifest",
  );
  const r = await request.get("/manifest.webmanifest");
  expect(r.status()).toBe(200);
  expect(r.headers()["content-type"]).toMatch(/json/);
  const m = await r.json();
  expect(typeof m.name).toBe("string");
  expect(m.name.length).toBeGreaterThan(0);
  expect(typeof m.short_name).toBe("string");
  expect(m.short_name.length).toBeGreaterThan(0);
  expect(m.short_name.length).toBeLessThanOrEqual(12);
  expect(m.start_url).toBe("/inicio");
  expect(m.scope).toBe("/");
  expect(m.display).toBe("standalone");
  expect(m.lang).toMatch(/^es/);
  expect(m.theme_color).toMatch(/^#[0-9a-fA-F]{6}$/);
  expect(m.background_color).toMatch(/^#[0-9a-fA-F]{6}$/);
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute("content", m.theme_color);
  const tamanios = m.icons.map((i: { sizes: string }) => i.sizes);
  expect(tamanios).toContain("192x192");
  expect(tamanios).toContain("512x512");
  expect(
    m.icons.some((i: { purpose?: string }) => (i.purpose ?? "").split(" ").includes("maskable")),
  ).toBe(true);
  for (const icono of m.icons as { src: string; type: string }[]) {
    expect(icono.type).toBe("image/png");
    const bajado = await request.get(icono.src);
    expect(bajado.status(), icono.src).toBe(200);
    expect(bajado.headers()["content-type"]).toContain("image/png");
  }
});

test("C05 · el service worker queda registrado en /sw.js con alcance en toda la app", async ({
  page,
  context,
  baseURL,
  request,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  await expect
    .poll(
      () =>
        page.evaluate(async () => {
          const registro = await navigator.serviceWorker.getRegistration();
          return registro?.active ? new URL(registro.active.scriptURL).pathname : null;
        }),
      { timeout: 15000 },
    )
    .toBe("/sw.js");
  const alcance = await page.evaluate(
    async () => new URL((await navigator.serviceWorker.getRegistration())?.scope ?? "").pathname,
  );
  expect(alcance).toBe("/");
  // El script lo baja cualquiera, como JavaScript.
  const script = await request.get("/sw.js");
  expect(script.status()).toBe(200);
  expect(script.headers()["content-type"]).toMatch(/javascript/);
});

const IPHONE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1";

test.describe("en iPhone", () => {
  test.use({ userAgent: IPHONE, viewport: { width: 390, height: 844 } });

  const aviso = (page: Page) =>
    page.getByRole("region", { name: "Agregar a la pantalla de inicio", exact: true });

  test("C05 · en iPhone, la primera vez, un aviso explica cómo agregarla a la pantalla de inicio y se puede cerrar", async ({
    page,
    context,
    baseURL,
  }) => {
    await como(context, baseURL, ANA);
    await abrir(page, inicio, "Inicio");
    await expect(aviso(page)).toBeVisible();
    await expect(aviso(page)).toContainText("Compartir");
    await expect(aviso(page)).toContainText("Agregar a inicio");
    await aviso(page).getByRole("button", { name: "Cerrar aviso", exact: true }).click();
    await expect(aviso(page)).toHaveCount(0);
    // Cerrado, no vuelve: ni al recargar ni en otra pantalla.
    await page.reload();
    await expect(titulo(page, "Inicio")).toBeVisible();
    await expect(aviso(page)).toHaveCount(0);
    await abrir(page, comprobantes, "Comprobantes");
    await expect(aviso(page)).toHaveCount(0);
  });

  test("N04 · el aviso de iPhone también va a 320 px, sin scroll horizontal y sin errores de axe", async ({
    page,
    context,
    baseURL,
  }) => {
    await como(context, baseURL, ANA);
    await page.setViewportSize({ width: 320, height: 900 });
    await abrir(page, inicio, "Inicio");
    await expect(aviso(page)).toBeVisible();
    expect(await anchoExcedeLaVentana(page)).toBe(false);
    await sinViolacionesEnElNavegador(page);
    // Con teclado: el botón se enfoca y se activa.
    const cerrar = aviso(page).getByRole("button", { name: "Cerrar aviso", exact: true });
    await cerrar.focus();
    await expect(cerrar).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(aviso(page)).toHaveCount(0);
    expect(await anchoExcedeLaVentana(page)).toBe(false);
  });
});

test("C05 · fuera de iPhone no hay aviso de instalación", async ({ page, context, baseURL }) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  await expect(unidades(page).getByRole("listitem")).toHaveCount(3);
  await expect(
    page.getByRole("region", { name: "Agregar a la pantalla de inicio", exact: true }),
  ).toHaveCount(0);
});

// --- N01 a N04 --------------------------------------------------------------------------------------------

test("N01 · el inquilino no ve montos ni categorías extraordinarias en ninguna pantalla", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, BETO);
  await abrir(page, inicio, "Inicio");
  await expect(cifra(fila(page, "1B"), "Total a pagar")).toHaveText("36.500,00");
  await expect(cifra(fila(page, "1B"), "Total a pagar")).not.toHaveText("51.500,00");
  await expect(fila(page, "1B")).toContainText("Inquilino");
  await expect(page.locator("body")).not.toContainText(/extraordinari/i);
  await expect(page.locator("body")).not.toContainText("Pintura");

  for (const [ruta, nombre] of [
    ["/mis-liquidaciones", "Mis liquidaciones"],
    [liquidaciones(U1B), "Liquidaciones de 1B"],
    [expensa(U1B, NOV), "Expensa de noviembre de 2026"],
    [expensa(U1B, OCT), "Expensa de octubre de 2026"],
    [comprobantes, "Comprobantes"],
  ] as const) {
    await abrir(page, ruta, nombre);
    await expect(page.locator("body"), ruta).not.toContainText(/extraordinari/i);
    await expect(page.locator("body"), ruta).not.toContainText("Pintura");
  }
  // Lo que sí ve: la ordinaria, el fondo y la multa de su unidad, con el total sin lo extraordinario.
  await abrir(page, expensa(U1B, NOV), "Expensa de noviembre de 2026");
  const tabla = page.getByRole("table", { name: "Tu expensa", exact: true });
  await expect(tabla.getByRole("row", { name: /^Multa 5\.000,00$/ })).toBeVisible();
  await expect(tabla.getByRole("row", { name: /^Total 36\.500,00$/ })).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Gastos extraordinarios", exact: true }),
  ).toHaveCount(0);
  const comparacion = page.getByRole("region", {
    name: "Comparación con el mes anterior",
    exact: true,
  });
  await expect(cifra(comparacion, "Total del mes anterior")).toHaveText("25.200,00");
  // Su pago sólo muestra lo imputado sin la extraordinaria; el PDF es el suyo.
  await abrir(page, comprobantes, "Comprobantes");
  await expect(
    page.getByRole("list", { name: "Pagos confirmados de 1B", exact: true }),
  ).toContainText("33.350,00");
});

test("N01 · una unidad o una liquidación ajena da 404 sin ningún dato", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, BETO);
  // Lo propio sí existe.
  await abrir(page, liquidaciones(U1B), "Liquidaciones de 1B");
  // La unidad de Ana, la de otro edificio, una inexistente y una liquidación que no existe.
  for (const ruta of [
    liquidaciones(U1A),
    expensa(U1A, NOV),
    liquidaciones(U9A),
    liquidaciones(INEXISTENTE),
    expensa(U1B, INEXISTENTE),
  ]) {
    const r = await page.goto(ruta);
    expect(r?.status(), ruta).toBe(404);
    await expect(page.locator("body"), ruta).not.toContainText("Torre Ficticia");
    await expect(page.locator("body"), ruta).not.toContainText("46.500,00");
  }
});

test("N02 · la pantalla no calcula: muestra los montos de la API con formato argentino", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  // La suma de las unidades es 86.750,00; el conjunto dice lo que dice la API.
  const conjunto = page.getByRole("region", { name: "Total del conjunto", exact: true });
  await expect(cifra(conjunto, "Total a pagar")).toHaveText("86.750,01");
  await expect(page.locator("body")).not.toContainText("86.750,00");
  await expect(page.locator("body")).not.toContainText(/\d{4,}\.\d{2}\b/);
  for (const [ruta, nombre] of [
    [liquidaciones(U1A), "Liquidaciones de 1A"],
    [expensa(U1A, NOV), "Expensa de noviembre de 2026"],
    [comprobantes, "Comprobantes"],
  ] as const) {
    await abrir(page, ruta, nombre);
    await expect(page.locator("body"), ruta).not.toContainText(/\d{4,}\.\d{2}\b/);
  }
  await abrir(page, expensa(U1A, NOV), "Expensa de noviembre de 2026");
  const comparacion = page.getByRole("region", {
    name: "Comparación con el mes anterior",
    exact: true,
  });
  await expect(cifra(comparacion, "Diferencia")).toHaveText("15.300,01");
  await expect(comparacion).not.toContainText("15.300,00");
});

/** Registra el service worker y lo deja controlando la página (una recarga después de activarse). */
async function conServiceWorkerActivo(page: Page) {
  await expect
    .poll(
      () =>
        page.evaluate(
          async () => (await navigator.serviceWorker.getRegistration())?.active?.state ?? null,
        ),
      { timeout: 15000 },
    )
    .toBe("activated");
  await page.reload();
  await expect(titulo(page, "Inicio")).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null), {
      timeout: 15000,
    })
    .toBe(true);
}

test("N03 · el service worker no guarda respuestas de /api ni páginas con datos del vecino", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  await conServiceWorkerActivo(page);
  for (const [ruta, nombre] of [
    [liquidaciones(U1A), "Liquidaciones de 1A"],
    [expensa(U1A, NOV), "Expensa de noviembre de 2026"],
    [comprobantes, "Comprobantes"],
    [inicio, "Inicio"],
  ] as const) {
    await abrir(page, ruta, nombre);
  }
  // Pedidos a /api desde la página con el service worker controlando (la respuesta no importa).
  await page.evaluate(async () => {
    for (const ruta of ["/api/mis-unidades", "/api/salud", "/api/sesion"]) {
      try {
        await (await fetch(ruta)).text();
      } catch {
        /* sin API en el origen de la web: lo que importa es qué quedó guardado */
      }
    }
  });
  const guardado = await page.evaluate(async () => {
    const entradas: { url: string; cuerpo: string }[] = [];
    for (const nombre of await caches.keys()) {
      const cache = await caches.open(nombre);
      for (const pedido of await cache.keys()) {
        let cuerpo = "";
        try {
          cuerpo = await (await cache.match(pedido))!.clone().text();
        } catch {
          /* respuesta opaca */
        }
        entradas.push({ url: pedido.url, cuerpo });
      }
    }
    return entradas;
  });
  for (const e of guardado) {
    expect(e.url, "una dirección con datos quedó guardada").not.toMatch(
      /\/api\/|\/inicio|\/mis-liquidaciones|\/comprobantes|\/documentos|\/edificios|\/_next\/data/,
    );
    expect(e.cuerpo, `el cuerpo de ${e.url}`).not.toContain("46.500,00");
    expect(e.cuerpo, `el cuerpo de ${e.url}`).not.toContain("Torre Ficticia");
    expect(e.cuerpo, `el cuerpo de ${e.url}`).not.toContain("Persona de prueba");
  }
});

test("N03 · sin conexión no se sirve ninguna pantalla con datos del vecino", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await abrir(page, inicio, "Inicio");
  await conServiceWorkerActivo(page);
  await abrir(page, expensa(U1A, NOV), "Expensa de noviembre de 2026");
  await context.setOffline(true);
  try {
    for (const ruta of [inicio, expensa(U1A, NOV), comprobantes]) {
      await page.goto(ruta).catch(() => null);
      await expect(page.locator("body"), ruta).not.toContainText("46.500,00");
      await expect(page.locator("body"), ruta).not.toContainText("Torre Ficticia");
    }
  } finally {
    await context.setOffline(false);
  }
});

test("N04 · a 320 px sin scroll horizontal, con teclado y sin errores de axe", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, ANA);
  await page.setViewportSize({ width: 320, height: 900 });
  await abrir(page, inicio, "Inicio");
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  // Con teclado: el enlace de la unidad se enfoca y se activa con Enter.
  const enlace = page.getByRole("link", { name: "Ver liquidaciones de 1A", exact: true });
  await enlace.focus();
  await expect(enlace).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(titulo(page, "Liquidaciones de 1A")).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  for (const [ruta, nombre] of [
    ["/mis-liquidaciones", "Mis liquidaciones"],
    [expensa(U1A, NOV), "Expensa de noviembre de 2026"],
    [expensa(U2B, NOV), "Expensa de noviembre de 2026"],
    [expensa(U1A, OCT), "Expensa de octubre de 2026"],
    [comprobantes, "Comprobantes"],
  ] as const) {
    await abrir(page, ruta, nombre);
    expect(await anchoExcedeLaVentana(page), ruta).toBe(false);
    await sinViolacionesEnElNavegador(page);
  }
  // Las tablas de la expensa se recorren con el foco sin salirse de la pantalla.
  await abrir(page, expensa(U1A, NOV), "Expensa de noviembre de 2026");
  await page.keyboard.press("Tab");
  expect(await anchoExcedeLaVentana(page)).toBe(false);
});
