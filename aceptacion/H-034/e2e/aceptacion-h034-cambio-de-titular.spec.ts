/**
 * Aceptación de H-034 · las pantallas del cambio de titular y de las cuentas de vendedores en navegador
 * real (C01 a C05, N01 a N03).
 *
 * Corre contra la API falsa (`web/e2e/api-falsa.ts`, escenarios de `web/e2e/escenarios-cambio-de-titular.ts`,
 * edificios 3401 a 3406) con las formas EXACTAS de las rutas reales de H-030 a H-033. Los textos, roles y
 * rutas son los de `aceptacion/H-034/CONTRATO.md`. Locators exactos y alertas filtradas por texto (L-085).
 * Cada test que escribe tiene su propio edificio (la API falsa guarda estado en memoria).
 */

import type { BrowserContext, Page } from "@playwright/test";
import { sinViolacionesEnElNavegador } from "./accesibilidad";
import { anchoExcedeLaVentana } from "./comprobaciones";
import { expect, test } from "./prueba";
import { cookiesDeContextoDePrueba } from "./sesion-local";

const edificio = (k: number) => `00000000-0000-0000-0000-00000000340${k}`;
const unidad = (k: number, n: number) => `00000000-0000-0000-0000-0000034${1}0${k}0${n}`;
const cuenta = (k: number, n: number) => `00000000-0000-0000-0000-0000034${3}0${k}0${n}`;
/** Las unidades de la semilla: 1A (dos propietarios y 45.230,10 de deuda), 1B y 2A (con un inquilino). */
const U1A = 1;
const U2A = 3;
/** Las cuentas de la semilla: Ana (30.000,00), Luis (12.500,51 a propósito) y Pedro (en cero). */
const ANA = 1;
const LUIS = 2;
const PEDRO = 3;

const LECTURA = 1;
const COBROS = 2;
const VENTA_CON_TRASLADO = 3;
const VENTA_EN_LA_UNIDAD = 4;
const ERRORES = 5;
const RECORRIDO = 6;

// Los mensajes por campo de C05 (CONTRATO.md): propios de la pantalla, nunca el "valor inválido" de la API.
const MENSAJES = {
  fecha: "Poné una fecha válida, que no sea posterior a hoy.",
  vendedores: "Elegí al menos un vendedor entre los propietarios actuales.",
  compradores:
    "Revisá los compradores: tiene que haber al menos uno y ninguno puede ser también vendedor.",
  vendedor_deudor: "Elegí cuál de los vendedores queda con la deuda.",
  expensa_del_mes: "Ya hay un prorrateo para esta unidad en ese mes. Elegí la expensa entera.",
  importe: "Poné un importe mayor a cero y que no supere la deuda de la cuenta.",
};

async function como(context: BrowserContext, baseURL: string | undefined, sub: string) {
  const { session, clientUat } = cookiesDeContextoDePrueba({ sub });
  await context.addCookies([
    { name: "__session", value: session, url: baseURL! },
    { name: "__client_uat", value: clientUat, url: baseURL! },
  ]);
}

const menu = (page: Page) => page.getByRole("navigation", { name: "Secciones del edificio" });
const padron = (k: number) => `/edificios/${edificio(k)}/unidades`;
const formulario = (k: number, n: number) =>
  `/edificios/${edificio(k)}/unidades/${unidad(k, n)}/cambio-de-titular`;
const cuentas = (k: number) => `/edificios/${edificio(k)}/cuentas-de-vendedores`;
const detalle = (k: number, n: number) => `${cuentas(k)}/${cuenta(k, n)}`;

async function abrirFormulario(page: Page, k: number, n: number, identificador: string) {
  await page.goto(formulario(k, n));
  await expect(
    page.getByRole("heading", { name: `Cambiar titular de ${identificador}`, exact: true }),
  ).toBeVisible();
  return page.getByRole("form", { name: `Cambiar titular de ${identificador}`, exact: true });
}

type Pedido = {
  fecha: string;
  vendedores: string[];
  compradores: { nombre: string; email?: string }[];
  expensa?: "Entera" | "Prorrateo por días";
  deuda?: "Queda en la unidad" | "A nombre del vendedor";
  deudor?: string;
};

async function llenar(page: Page, p: Pedido) {
  const f = page.getByRole("form", { name: /^Cambiar titular de / });
  await f.getByLabel("Fecha del cambio", { exact: true }).fill(p.fecha);
  for (const v of p.vendedores) {
    await f
      .getByRole("group", { name: "Vendedores", exact: true })
      .getByLabel(v, { exact: true })
      .check();
  }
  for (const [i, c] of p.compradores.entries()) {
    if (i > 0) await f.getByRole("button", { name: "Agregar otro comprador", exact: true }).click();
    await f.getByLabel(`Nombre del comprador ${i + 1}`, { exact: true }).fill(c.nombre);
    if (c.email) {
      await f.getByLabel(`Email del comprador ${i + 1} (opcional)`, { exact: true }).fill(c.email);
    }
  }
  if (p.expensa) {
    await f
      .getByRole("group", { name: "Expensa del mes", exact: true })
      .getByRole("radio", { name: p.expensa, exact: true })
      .check();
  }
  if (p.deuda) {
    await f
      .getByRole("group", { name: "Deuda previa", exact: true })
      .getByRole("radio", { name: p.deuda, exact: true })
      .check();
  }
  if (p.deudor) {
    await f
      .getByLabel("Vendedor que queda con la deuda", { exact: true })
      .selectOption({ label: p.deudor });
  }
  await f.getByRole("button", { name: "Registrar cambio de titular", exact: true }).click();
}

const resultado = (page: Page) =>
  page.getByRole("region", { name: "Resultado del cambio de titular", exact: true });

async function sinTextoTecnico(page: Page) {
  await expect(page.getByText("valor inválido", { exact: false })).toHaveCount(0);
  await expect(page.getByText("Este valor no es válido", { exact: false })).toHaveCount(0);
}

async function cobrar(page: Page, importe: string, fecha: string) {
  const f = page.getByRole("form", { name: "Registrar cobro", exact: true });
  await expect(f).toBeVisible();
  await f.getByLabel("Importe", { exact: true }).fill(importe);
  await f.getByLabel("Fecha del cobro", { exact: true }).fill(fecha);
  await f.getByRole("button", { name: "Registrar cobro", exact: true }).click();
}

const deuda = (page: Page) => page.getByRole("region", { name: "Deuda de la cuenta", exact: true });
const dialogoDeCobro = (page: Page) =>
  page.getByRole("dialog", { name: "Confirmar cobro", exact: true });

// --- C01 a C05 -------------------------------------------------------------------------------------------

test("C01 · el padrón ofrece Cambiar titular en cada unidad y abre el formulario con sus campos", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.goto(padron(LECTURA));
  for (const u of ["1A", "1B", "2A"]) {
    await expect(page.getByRole("row", { name: new RegExp(`^${u}`) })).toBeVisible();
    await expect(
      page.getByRole("link", { name: `Cambiar titular de ${u}`, exact: true }),
    ).toBeVisible();
  }
  await page.getByRole("link", { name: "Cambiar titular de 2A", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${formulario(LECTURA, U2A)}$`));
  const f = page.getByRole("form", { name: "Cambiar titular de 2A", exact: true });
  await expect(
    page.getByRole("heading", { name: "Cambiar titular de 2A", exact: true }),
  ).toBeVisible();
  await expect(f.getByLabel("Fecha del cambio", { exact: true })).toBeVisible();
  // Sólo los propietarios actuales se ofrecen como vendedores: el inquilino no.
  const vendedores = f.getByRole("group", { name: "Vendedores", exact: true });
  await expect(
    vendedores.getByRole("checkbox", { name: "Carla Prueba", exact: true }),
  ).toBeVisible();
  await expect(vendedores.getByRole("checkbox")).toHaveCount(1);
  await expect(f.getByLabel("Nombre del comprador 1", { exact: true })).toBeVisible();
  await expect(f.getByLabel("Email del comprador 1 (opcional)", { exact: true })).toBeVisible();
  const expensa = f.getByRole("group", { name: "Expensa del mes", exact: true });
  await expect(expensa.getByRole("radio", { name: "Entera", exact: true })).toBeChecked();
  await expect(
    expensa.getByRole("radio", { name: "Prorrateo por días", exact: true }),
  ).not.toBeChecked();
  const previa = f.getByRole("group", { name: "Deuda previa", exact: true });
  await expect(
    previa.getByRole("radio", { name: "Queda en la unidad", exact: true }),
  ).toBeChecked();
  await expect(
    previa.getByRole("radio", { name: "A nombre del vendedor", exact: true }),
  ).not.toBeChecked();
  await expect(
    f.getByRole("button", { name: "Registrar cambio de titular", exact: true }),
  ).toBeVisible();
  // Con un solo propietario no hay a quién elegir como deudor.
  await expect(f.getByLabel("Vendedor que queda con la deuda", { exact: true })).toHaveCount(0);
});

test("C01 · cada opción dice qué pasa y el deudor se elige sólo con más de un vendedor", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  const f = await abrirFormulario(page, LECTURA, U1A, "1A");
  await expect(
    f.getByText("La expensa del mes completa queda en la unidad.", { exact: true }),
  ).toBeVisible();
  await expect(
    f.getByText(
      "El vendedor paga los días del mes anteriores a la fecha del cambio y la unidad el resto.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    f.getByText(
      "La deuda de meses anteriores queda en la unidad y el comprador la hereda; se le avisa el monto.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    f.getByText(
      "La deuda de meses anteriores pasa a una cuenta del vendedor y la unidad queda sin ella.",
      { exact: true },
    ),
  ).toBeVisible();
  const vendedores = f.getByRole("group", { name: "Vendedores", exact: true });
  await expect(vendedores.getByRole("checkbox")).toHaveCount(2);
  const deudor = f.getByLabel("Vendedor que queda con la deuda", { exact: true });
  await vendedores.getByLabel("Ana Prueba", { exact: true }).check();
  await vendedores.getByLabel("Bruno Prueba", { exact: true }).check();
  await expect(deudor).toHaveCount(0);
  await f.getByRole("radio", { name: "A nombre del vendedor", exact: true }).check();
  await expect(deudor).toBeVisible();
  await expect(deudor.getByRole("option", { name: "Ana Prueba", exact: true })).toHaveCount(1);
  await expect(deudor.getByRole("option", { name: "Bruno Prueba", exact: true })).toHaveCount(1);
  await f.getByRole("radio", { name: "Queda en la unidad", exact: true }).check();
  await f.getByRole("radio", { name: "Prorrateo por días", exact: true }).check();
  await expect(deudor).toBeVisible();
  await f.getByRole("radio", { name: "Entera", exact: true }).check();
  await expect(deudor).toHaveCount(0);
  // Uno o más compradores.
  await f.getByRole("button", { name: "Agregar otro comprador", exact: true }).click();
  await expect(f.getByLabel("Nombre del comprador 2", { exact: true })).toBeVisible();
  await expect(f.getByLabel("Email del comprador 2 (opcional)", { exact: true })).toBeVisible();
});

test("C02 · la venta con la deuda a nombre del vendedor y el prorrateo pendiente muestra su resultado", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await abrirFormulario(page, VENTA_CON_TRASLADO, U1A, "1A");
  await llenar(page, {
    fecha: "2026-11-10",
    vendedores: ["Ana Prueba", "Bruno Prueba"],
    compradores: [
      { nombre: "Carlos Comprador", email: "carlos@prueba.test" },
      { nombre: "Diana Compradora" },
    ],
    expensa: "Prorrateo por días",
    deuda: "A nombre del vendedor",
    deudor: "Bruno Prueba",
  });
  const r = resultado(page);
  await expect(
    r.getByRole("heading", { name: "Cambio de titular registrado", exact: true }),
  ).toBeVisible();
  // El traslado dejó a la unidad sin deuda: no hay aviso que dar.
  await expect(r).toContainText("Aviso de deuda");
  await expect(r).toContainText("La unidad no tiene deuda para avisar.");
  await expect(r).toContainText("Deuda pasada al vendedor");
  await expect(r).toContainText("45.230,10");
  const cuentaDelVendedor = r.getByRole("link", {
    name: "Ver la cuenta del vendedor",
    exact: true,
  });
  await expect(cuentaDelVendedor).toHaveAttribute(
    "href",
    new RegExp(`^${cuentas(VENTA_CON_TRASLADO)}/[0-9a-f-]{36}$`),
  );
  await expect(r).toContainText("Prorrateo de la expensa");
  await expect(r).toContainText("Pendiente");
  await expect(r).toContainText("11/2026");
  await expect(r).toContainText("9 de 30 días");
  await expect(r).not.toContainText("Aplicado");
  // El padrón ya muestra a los compradores como los vecinos de la unidad.
  await r.getByRole("link", { name: "Volver al padrón", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${padron(VENTA_CON_TRASLADO)}$`));
  await page.getByRole("button", { name: "1A", exact: true }).click();
  const panel = page.getByRole("dialog", { name: "Editar unidad" });
  await expect(panel.getByText("Carlos Comprador", { exact: false })).toBeVisible();
  await expect(panel.getByText("Diana Compradora", { exact: false })).toBeVisible();
  await expect(panel.getByText("Ana Prueba", { exact: false })).toHaveCount(0);
  // Y la cuenta del vendedor existe, con la deuda que se le pasó.
  await page.goto(cuentas(VENTA_CON_TRASLADO));
  const bruno = page
    .getByRole("list", { name: "Cuentas de vendedores", exact: true })
    .getByRole("listitem")
    .filter({ hasText: "Bruno Prueba" });
  await expect(bruno).toContainText("45.230,10");
  await expect(bruno).toContainText("1A");
});

test("C02 · la venta con la deuda en la unidad avisa el monto y muestra el prorrateo aplicado con su parte", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await abrirFormulario(page, VENTA_EN_LA_UNIDAD, U1A, "1A");
  await llenar(page, {
    fecha: "2026-11-10",
    vendedores: ["Ana Prueba"],
    compradores: [{ nombre: "Carlos Comprador" }],
    expensa: "Prorrateo por días",
    deuda: "Queda en la unidad",
  });
  const r = resultado(page);
  await expect(
    r.getByRole("heading", { name: "Cambio de titular registrado", exact: true }),
  ).toBeVisible();
  await expect(r).toContainText("Aviso de deuda");
  await expect(r).toContainText("La unidad queda con una deuda de 45.230,10.");
  await expect(r).not.toContainText("Deuda pasada al vendedor");
  await expect(
    r.getByRole("link", { name: "Ver la cuenta del vendedor", exact: true }),
  ).toHaveCount(0);
  await expect(r).toContainText("Prorrateo de la expensa");
  await expect(r).toContainText("Aplicado");
  await expect(r).toContainText("8.333,33");
  await expect(r).toContainText("9 de 30 días");
  await expect(r).not.toContainText("Pendiente");
  await r.getByRole("link", { name: "Volver al padrón", exact: true }).click();
  await page.getByRole("button", { name: "1A", exact: true }).click();
  const panel = page.getByRole("dialog", { name: "Editar unidad" });
  await expect(panel.getByText("Carlos Comprador", { exact: false })).toBeVisible();
  await expect(panel.getByText("Bruno Prueba", { exact: false })).toBeVisible();
  await expect(panel.getByText("Ana Prueba", { exact: false })).toHaveCount(0);
});

test("C03 · cada unidad muestra su historial de cambios de titular, el más nuevo primero", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.goto(padron(LECTURA));
  const verHistorial = page.getByRole("link", {
    name: "Ver historial de cambios de titular de 1A",
    exact: true,
  });
  await expect(verHistorial).toBeVisible();
  await verHistorial.click();
  await expect(page).toHaveURL(new RegExp(`${formulario(LECTURA, U1A)}(#historial)?$`));
  const historial = page.getByRole("list", {
    name: "Historial de cambios de titular",
    exact: true,
  });
  await expect(historial.getByRole("listitem")).toHaveCount(2);
  const nuevo = historial.getByRole("listitem").nth(0);
  for (const t of [
    "11/09/2025",
    "Luis Intermedio",
    "Ana Prueba, Bruno Prueba",
    "Prorrateo por días",
    "A nombre del vendedor",
    "9.000,50",
    "Aplicado",
    "3.500,00",
    "10 de 30 días",
  ]) {
    await expect(nuevo).toContainText(t);
  }
  const viejo = historial.getByRole("listitem").nth(1);
  for (const t of [
    "20/05/2024",
    "Pedro Anterior",
    "Luis Intermedio",
    "Entera",
    "Queda en la unidad",
  ]) {
    await expect(viejo).toContainText(t);
  }
  await expect(viejo).not.toContainText("Deuda pasada al vendedor");
  // Una unidad sin cambios lo dice.
  await page.goto(formulario(LECTURA, 2));
  await expect(
    page.getByRole("status").filter({ hasText: "Esta unidad todavía no tuvo cambios de titular" }),
  ).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Historial de cambios de titular", exact: true }),
  ).toHaveCount(0);
});

test("C04 · Cuentas de vendedores está en el menú y lista persona, deuda y unidades", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.goto(padron(LECTURA));
  const link = menu(page).getByRole("link", { name: "Cuentas de vendedores", exact: true });
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("href", cuentas(LECTURA));
  await expect(
    menu(page)
      .getByRole("list", { name: "Liquidación", exact: true })
      .getByRole("link", { name: "Cuentas de vendedores", exact: true }),
  ).toBeVisible();
  await link.click();
  await expect(
    page.getByRole("heading", { name: "Cuentas de vendedores", exact: true }),
  ).toBeVisible();
  const lista = page.getByRole("list", { name: "Cuentas de vendedores", exact: true });
  await expect(lista.getByRole("listitem")).toHaveCount(3);
  // En el orden de la API (deuda de mayor a menor), también la que quedó en cero.
  const filas = lista.getByRole("listitem");
  for (const [i, textos] of [
    ["Ana Prueba", "30.000,00", "1B, 2A"],
    ["Luis Intermedio", "12.500,51", "1A"],
    ["Pedro Anterior", "0,00", "1A"],
  ].entries()) {
    for (const t of textos ?? []) await expect(filas.nth(i)).toContainText(t as string);
  }
  await expect(filas.nth(0).getByRole("link", { name: "Ana Prueba", exact: true })).toHaveAttribute(
    "href",
    detalle(LECTURA, ANA),
  );
});

test("C04 · el detalle de la cuenta muestra la deuda por período y sus movimientos", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.goto(cuentas(LECTURA));
  const luisLink = page.getByRole("link", { name: "Luis Intermedio", exact: true });
  await expect(luisLink).toBeVisible();
  await luisLink.click();
  await expect(page).toHaveURL(new RegExp(`${detalle(LECTURA, LUIS)}$`));
  await expect(
    page.getByRole("heading", { name: "Cuenta de Luis Intermedio", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Volver a cuentas de vendedores", exact: true }),
  ).toHaveAttribute("href", cuentas(LECTURA));
  await expect(deuda(page)).toContainText("12.500,51");
  await expect(deuda(page)).toContainText("1A");
  const periodos = page.getByRole("table", { name: "Deuda por período", exact: true });
  for (const c of ["Período", "Componente", "Debe", "Cobrado", "Pendiente"]) {
    await expect(periodos.getByRole("columnheader", { name: c, exact: true })).toBeVisible();
  }
  await expect(periodos.getByRole("row")).toHaveCount(3);
  const agosto = periodos.getByRole("row").filter({ hasText: "08/2025" });
  for (const t of ["Ordinaria", "9.000,50", "0,00"]) await expect(agosto).toContainText(t);
  await expect(periodos.getByRole("row").filter({ hasText: "09/2025" })).toContainText("3.500,00");
  const movimientos = page.getByRole("table", { name: "Movimientos", exact: true });
  for (const c of ["Fecha", "Movimiento", "Importe"]) {
    await expect(movimientos.getByRole("columnheader", { name: c, exact: true })).toBeVisible();
  }
  const traslado = movimientos.getByRole("row").filter({ hasText: "Traslado de deuda" }).first();
  await expect(traslado).toContainText("11/09/2025");
  await expect(traslado).toContainText("9.000,50");
  // La cuenta en cero muestra su cobro.
  await page.goto(detalle(LECTURA, PEDRO));
  await expect(deuda(page)).toContainText("0,00");
  const cobro = page
    .getByRole("table", { name: "Movimientos", exact: true })
    .getByRole("row")
    .filter({ hasText: "Cobro" });
  await expect(cobro).toContainText("10/06/2024");
  await expect(cobro).toContainText("5.000,00");
});

test("C04 · Registrar cobro pide confirmación, descuenta lo cobrado y se puede cobrar hasta cero", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.goto(detalle(COBROS, ANA));
  await expect(deuda(page)).toContainText("30.000,00");
  await cobrar(page, "20000,00", "2026-11-20");
  const dialogo = dialogoDeCobro(page);
  await expect(dialogo).toContainText("Vas a registrar un cobro de 20.000,00 del 20/11/2026.");
  await dialogo.getByRole("button", { name: "Cancelar", exact: true }).click();
  await expect(dialogo).toHaveCount(0);
  await expect(deuda(page)).toContainText("30.000,00");
  await cobrar(page, "20000,00", "2026-11-20");
  await dialogoDeCobro(page).getByRole("button", { name: "Confirmar cobro", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Cobro registrado" })).toBeVisible();
  await expect(deuda(page)).toContainText("10.000,00");
  await expect(deuda(page)).not.toContainText("30.000,00");
  const movimientos = page.getByRole("table", { name: "Movimientos", exact: true });
  const cobro = movimientos.getByRole("row").filter({ hasText: "Cobro" });
  await expect(cobro).toContainText("20/11/2026");
  await expect(cobro).toContainText("20.000,00");
  const interes = page
    .getByRole("table", { name: "Deuda por período", exact: true })
    .getByRole("row")
    .filter({ hasText: "Interés" });
  await expect(interes).toContainText("1.500,00");
  // Hasta cero.
  await cobrar(page, "10000,00", "2026-11-21");
  await dialogoDeCobro(page).getByRole("button", { name: "Confirmar cobro", exact: true }).click();
  await expect(deuda(page)).toContainText("0,00");
  await expect(deuda(page)).not.toContainText("10.000,00");
  await page.goto(cuentas(COBROS));
  await expect(
    page
      .getByRole("list", { name: "Cuentas de vendedores", exact: true })
      .getByRole("listitem")
      .filter({ hasText: "Ana Prueba" }),
  ).toContainText("0,00");
});

test("C05 · un 422 del cambio se muestra en su campo con el mensaje de la pantalla", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  // Fecha posterior a hoy.
  await abrirFormulario(page, ERRORES, U1A, "1A");
  await llenar(page, {
    fecha: "2099-01-01",
    vendedores: ["Ana Prueba"],
    compradores: [{ nombre: "Carlos Comprador" }],
  });
  await expect(page.getByLabel("Fecha del cambio", { exact: true })).toHaveAccessibleDescription(
    new RegExp(MENSAJES.fecha),
  );
  await sinTextoTecnico(page);
  // El comprador es también vendedor (se reconoce por el email).
  await abrirFormulario(page, ERRORES, U1A, "1A");
  await llenar(page, {
    fecha: "2026-11-10",
    vendedores: ["Ana Prueba"],
    compradores: [{ nombre: "Ana de nuevo", email: "ana@prueba.test" }],
  });
  await expect(page.getByRole("group", { name: "Compradores", exact: true })).toContainText(
    MENSAJES.compradores,
  );
  await sinTextoTecnico(page);
  // Un segundo prorrateo en la misma unidad y el mismo mes.
  await abrirFormulario(page, ERRORES, U1A, "1A");
  await llenar(page, {
    fecha: "2026-11-10",
    vendedores: ["Ana Prueba"],
    compradores: [{ nombre: "Carlos Comprador" }],
    expensa: "Prorrateo por días",
  });
  await expect(page.getByRole("group", { name: "Expensa del mes", exact: true })).toContainText(
    MENSAJES.expensa_del_mes,
  );
  await sinTextoTecnico(page);
  await expect(
    page.getByRole("region", { name: "Resultado del cambio de titular", exact: true }),
  ).toHaveCount(0);
});

test("C05 · un 422 del cobro se muestra en el importe o en la fecha con el mensaje de la pantalla", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.goto(detalle(ERRORES, ANA));
  await cobrar(page, "99999,00", "2026-11-20");
  await dialogoDeCobro(page).getByRole("button", { name: "Confirmar cobro", exact: true }).click();
  const f = page.getByRole("form", { name: "Registrar cobro", exact: true });
  await expect(f.getByLabel("Importe", { exact: true })).toHaveAccessibleDescription(
    new RegExp(MENSAJES.importe),
  );
  await sinTextoTecnico(page);
  await expect(deuda(page)).toContainText("30.000,00");
  await cobrar(page, "100,00", "2099-01-01");
  await dialogoDeCobro(page).getByRole("button", { name: "Confirmar cobro", exact: true }).click();
  await expect(f.getByLabel("Fecha del cobro", { exact: true })).toHaveAccessibleDescription(
    new RegExp(MENSAJES.fecha),
  );
  await sinTextoTecnico(page);
  await expect(deuda(page)).toContainText("30.000,00");
});

// --- N01 a N03 -------------------------------------------------------------------------------------------

test("N01 · quien sólo lee ve el menú y la lista pero ni el botón de cambiar titular ni el cobro", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_lector");
  await page.goto(padron(LECTURA));
  await expect(page.getByRole("row", { name: /^1A/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /^Cambiar titular/ })).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /^Ver historial de cambios de titular/ }),
  ).toHaveCount(0);
  // Lee: el menú y la lista están.
  const enMenu = menu(page).getByRole("link", { name: "Cuentas de vendedores", exact: true });
  await expect(enMenu).toBeVisible();
  await enMenu.click();
  await expect(
    page.getByRole("list", { name: "Cuentas de vendedores", exact: true }).getByRole("listitem"),
  ).toHaveCount(3);
  await page.getByRole("link", { name: "Ana Prueba", exact: true }).click();
  await expect(deuda(page)).toContainText("30.000,00");
  await expect(page.getByRole("form", { name: "Registrar cobro", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Registrar cobro", exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Importe", { exact: true })).toHaveCount(0);
  // La pantalla del cambio dice qué permiso falta y no ofrece el formulario.
  await page.goto(formulario(LECTURA, U1A));
  await expect(page.getByText("registrar_cambio_de_titular", { exact: false })).toBeVisible();
  await expect(page.getByRole("form")).toHaveCount(0);
});

test("N01 · la vecina no ve Cuentas de vendedores ni su pantalla ni la del cambio de titular", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_vecina");
  await page.goto(cuentas(LECTURA));
  await expect(page.getByText("ver_morosidad", { exact: false })).toBeVisible();
  await expect(
    menu(page).getByRole("link", { name: "Cuentas de vendedores", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole("list", { name: "Cuentas de vendedores", exact: true })).toHaveCount(
    0,
  );
  await expect(page.getByText("Ana Prueba", { exact: false })).toHaveCount(0);
  await page.goto(formulario(LECTURA, U1A));
  await expect(page.getByText("registrar_cambio_de_titular", { exact: false })).toBeVisible();
  await expect(page.getByRole("form")).toHaveCount(0);
  await expect(page.getByText("Ana Prueba", { exact: false })).toHaveCount(0);
});

test("N02 · la pantalla no calcula montos: muestra los de la API con formato argentino", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  // La deuda de Luis dice 12.500,51 aunque sus períodos suman 12.500,50: es la de la API.
  await page.goto(cuentas(LECTURA));
  const luis = page
    .getByRole("list", { name: "Cuentas de vendedores", exact: true })
    .getByRole("listitem")
    .filter({ hasText: "Luis Intermedio" });
  await expect(luis).toContainText("12.500,51");
  await expect(luis).not.toContainText("12500.51");
  await page.getByRole("link", { name: "Luis Intermedio", exact: true }).click();
  await expect(deuda(page)).toContainText("12.500,51");
  await expect(page.getByText("12.500,50", { exact: false })).toHaveCount(0);
  // Su cobro de 2.500,00 devuelve 10.000,52 (no 10.000,51): la pantalla pone lo que dice la API.
  await page.goto(detalle(COBROS, LUIS));
  await expect(deuda(page)).toContainText("12.500,51");
  await cobrar(page, "2500,00", "2026-11-20");
  await dialogoDeCobro(page).getByRole("button", { name: "Confirmar cobro", exact: true }).click();
  await expect(deuda(page)).toContainText("10.000,52");
  await expect(deuda(page)).not.toContainText("10.000,51");
  await expect(page.getByText("10000.52", { exact: false })).toHaveCount(0);
});

test("N03 · a 320 px sin scroll horizontal, con teclado y sin errores de axe", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto(padron(LECTURA));
  const link = page.getByRole("link", { name: "Cambiar titular de 1A", exact: true });
  await expect(link).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  // Con teclado: el enlace se enfoca y se activa con Enter.
  await link.focus();
  await expect(link).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Cambiar titular de 1A", exact: true }),
  ).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  const prorrateo = page.getByRole("radio", { name: "Prorrateo por días", exact: true });
  await prorrateo.focus();
  await page.keyboard.press("Space");
  await expect(prorrateo).toBeChecked();
  const historial = page.getByRole("list", {
    name: "Historial de cambios de titular",
    exact: true,
  });
  await expect(historial.getByRole("listitem")).toHaveCount(2);
  for (const ruta of [cuentas(LECTURA), detalle(LECTURA, LUIS)]) {
    await page.goto(ruta);
    await expect(page.getByRole("heading", { name: /^Cuenta/ })).toBeVisible();
    expect(await anchoExcedeLaVentana(page)).toBe(false);
    await sinViolacionesEnElNavegador(page);
  }
});

test("N03 · el resultado del cambio y la confirmación del cobro también, a 320 px y sin errores de axe", async ({
  page,
  context,
  baseURL,
}) => {
  await como(context, baseURL, "user_titular");
  await page.setViewportSize({ width: 320, height: 900 });
  await abrirFormulario(page, RECORRIDO, U1A, "1A");
  await llenar(page, {
    fecha: "2026-11-10",
    vendedores: ["Ana Prueba", "Bruno Prueba"],
    compradores: [{ nombre: "Carlos Comprador" }],
    expensa: "Prorrateo por días",
    deuda: "A nombre del vendedor",
    deudor: "Ana Prueba",
  });
  const r = resultado(page);
  await expect(
    r.getByRole("heading", { name: "Cambio de titular registrado", exact: true }),
  ).toBeVisible();
  await expect(r).toContainText("45.230,10");
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  await page.goto(detalle(RECORRIDO, ANA));
  await cobrar(page, "100,00", "2026-11-20");
  await expect(dialogoDeCobro(page)).toBeVisible();
  expect(await anchoExcedeLaVentana(page)).toBe(false);
  await sinViolacionesEnElNavegador(page);
  await dialogoDeCobro(page).getByRole("button", { name: "Cancelar", exact: true }).click();
  await expect(dialogoDeCobro(page)).toHaveCount(0);
});
