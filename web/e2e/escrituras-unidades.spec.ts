import { ESCRITURAS_UNIDADES } from "./escenarios-escritura";
import { expect, type Page, test } from "./prueba";
import { cabecerasDePrueba } from "./sesion-local";

const datos = {
  identificador: "NUEVA-3B",
  tipo: "cochera",
  piso: "PB",
  coeficiente: "1.000000",
  superficie_m2: "60.25",
};
const baseApi = `http://127.0.0.1:${process.env.PROPTECH_PUERTO_API_FALSA ?? "4100"}`;

async function guardarUnidad(page: Page) {
  const respuesta = page.waitForResponse(
    (respuesta) => respuesta.request().method() === "POST" && respuesta.url().includes("/unidades"),
  );
  await page.getByRole("dialog").getByRole("button", { name: "Guardar", exact: true }).click();
  await respuesta;
}

async function cargarUnidad(page: Page, id: string) {
  await page.goto(`/edificios/${id}/unidades`);
  await page.getByRole("button", { name: "Agregar unidad", exact: true }).last().click();
  const panel = page.getByRole("dialog", { name: "Agregar unidad" });
  await panel.getByLabel("Identificador", { exact: true }).fill(datos.identificador);
  await panel.getByRole("combobox", { name: "Tipo", exact: true }).selectOption(datos.tipo);
  // 3c (D3): el piso es una lista del vocabulario del edificio, no texto libre.
  await panel.getByLabel("Piso", { exact: true }).selectOption(datos.piso);
  await panel
    .getByLabel("Superficie (m²)", { exact: true })
    .fill(datos.superficie_m2.replace(".", ","));
  await panel.getByLabel("Coeficiente", { exact: true }).fill(datos.coeficiente.replace(".", ","));
  await guardarUnidad(page);
  return panel;
}

test("Auditor 4: guarda una unidad por la pantalla y comprueba el JSON recibido por la API falsa", async ({
  page,
  request,
}) => {
  const id = ESCRITURAS_UNIDADES.alta;
  const panel = await cargarUnidad(page, id);
  await expect(panel).toHaveCount(0);
  await expect(page.getByRole("cell", { name: datos.identificador })).toBeVisible();
  await expect(page.getByRole("button", { name: "Agregar unidad", exact: true })).toBeFocused();
  const respuesta = await request.get(`${baseApi}/api/__debug/ultima-escritura`, {
    headers: cabecerasDePrueba(),
  });
  expect(respuesta.ok()).toBe(true);
  const escritura = await respuesta.json();
  expect(escritura).toMatchObject({
    metodo: "POST",
    url: `/api/complejos/${id}/unidades`,
    contentType: "application/json",
  });
  expect(JSON.parse(escritura.cuerpo)).toEqual(datos);
});

for (const [clave, mensaje] of [
  ["rechazo403", "No podés modificar el padrón de unidades."],
  ["rechazo422", "Este valor no es válido."],
] as const) {
  test(`R3C-3 pantalla: ${clave} conserva todos los datos del panel tras dos rechazos`, async ({
    page,
    request,
  }) => {
    const id = ESCRITURAS_UNIDADES[clave];
    const panel = await cargarUnidad(page, id);
    for (let intento = 0; intento < 2; intento += 1) {
      if (intento > 0) await guardarUnidad(page);
      await expect(panel.getByRole("alert")).toContainText(mensaje);
      await expect(panel.getByLabel("Identificador", { exact: true })).toHaveValue(
        datos.identificador,
      );
      await expect(panel.getByRole("combobox", { name: "Tipo", exact: true })).toHaveValue(
        datos.tipo,
      );
      await expect(panel.getByLabel("Piso", { exact: true })).toHaveValue(datos.piso);
      await expect(panel.getByLabel("Superficie (m²)", { exact: true })).toHaveValue(
        datos.superficie_m2.replace(".", ","),
      );
      await expect(panel.getByLabel("Coeficiente", { exact: true })).toHaveValue(
        datos.coeficiente.replace(".", ","),
      );
      const escritura = await (
        await request.get(`${baseApi}/api/__debug/ultima-escritura`, {
          headers: cabecerasDePrueba(),
        })
      ).json();
      expect(escritura.url).toBe(`/api/complejos/${id}/unidades`);
      expect(escritura.contentType).toBe("application/json");
      expect(JSON.parse(escritura.cuerpo)).toEqual(datos);
    }
  });
}
