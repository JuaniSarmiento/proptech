/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import type { VersionDelHistorial } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaConfiguracion } from "./Pantalla";

afterEach(cleanup);

const V1: VersionDelHistorial = {
  id: "v1",
  complejo_id: "e1",
  vigente_desde: "2026-10-19",
  tasa_mensual: "3.00",
  dias_de_gracia: 0,
  forma_de_calculo: "proporcional_por_dia",
  porcentaje_fondo: "0.00",
  dia_de_vencimiento: 10,
  modalidad_de_vencimiento: "unico",
  dia_segundo_vencimiento: null,
  recargo_segundo_vencimiento: null,
  autor_id: "a1",
  autor_nombre: "Alberto",
  creada_en: "2026-10-19T22:06:28Z",
};

const V2: VersionDelHistorial = {
  ...V1,
  id: "v2",
  vigente_desde: "2026-10-20",
  tasa_mensual: "4.00",
  dias_de_gracia: 5,
  porcentaje_fondo: "2.00",
  autor_nombre: "Mariela",
  creada_en: "2026-10-19T22:06:28.9Z",
};

function accionNula() {
  return Promise.resolve(null);
}

describe("PantallaConfiguracion", () => {
  it("Auditor fila 6: el ejemplo de ayuda explica la vigencia de versiones guardadas", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={V1}
        historial={[V1]}
        accionCrear={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Ayuda" }));
    expect(
      screen.getByText(
        /La versión anterior queda guardada y rige hasta que entra en vigencia la nueva\./,
      ),
    ).toBeTruthy();
  });

  it("el historial muestra las dos versiones, la nueva con su autor y la tasa como campo cambiado", () => {
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={V2}
        historial={[V1, V2]}
        accionCrear={accionNula}
      />,
    );
    const historial = screen.getByRole("list", { name: "Historial de configuración" });
    const filas = within(historial).getAllByRole("listitem");
    expect(filas).toHaveLength(2);
    // Más nueva primero (línea de tiempo, tarea 4.6).
    expect(filas[0]?.textContent).toContain("Mariela");
    expect(filas[0]?.textContent).toContain("tasa");
    expect(filas[1]?.textContent).toContain("Alberto");
  });

  it('el historial muestra "rige desde" en día/mes/año y la vigente como renglones etiqueta/valor (pulido 3b)', () => {
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={V2}
        historial={[V1, V2]}
        accionCrear={accionNula}
      />,
    );
    const historial = screen.getByRole("list", { name: "Historial de configuración" });
    expect(historial.textContent).toContain("20/10/2026");
    expect(historial.textContent).not.toContain("2026-10-20");
    const vigente = screen.getByRole("region", { name: "Configuración vigente" });
    const terminos = within(vigente)
      .getAllByRole("term")
      .map((t) => t.textContent);
    expect(terminos).toEqual([
      "Tasa de interés mensual",
      "Fondo de reserva",
      "Días de gracia",
      "Forma de cálculo",
      "Vencimiento",
    ]);
    const valores = within(vigente)
      .getAllByRole("definition")
      .map((d) => d.textContent);
    expect(valores).toEqual(["4,00 %", "2,00 %", "5", "Proporcional por día", "Día 10"]);
  });

  it("la primera versión del historial no muestra campos cambiados", () => {
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={V1}
        historial={[V1]}
        accionCrear={accionNula}
      />,
    );
    const historial = screen.getByRole("list", { name: "Historial de configuración" });
    expect(historial.textContent).toContain("Alberto");
  });

  it('"Cambiar configuración" abre el panel con "rige desde" y el aviso de que la anterior no se borra', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={V1}
        historial={[V1]}
        accionCrear={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Cambiar configuración" }));
    expect(screen.getByLabelText("Rige desde")).toBeTruthy();
    expect(screen.getByText(/la versión anterior no se borra/i)).toBeTruthy();
    expect(screen.getByLabelText("Tasa mensual")).toHaveProperty("value", "3,00"); // edición en formato argentino
    expect(screen.getByLabelText("Fondo de reserva")).toHaveProperty("value", "0,00");
  });

  it("decimales: el recargo se muestra con coma y conserva la coma al escribir y enviar", async () => {
    const usuario = userEvent.setup();
    let envio: FormData | undefined;
    const accionCrear = async (_previo: unknown, datos: FormData) => {
      envio = datos;
      return { erroresPorCampo: { tasa_mensual: "Revisá la tasa" }, erroresDesconocidos: [] };
    };
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={{
          ...V1,
          modalidad_de_vencimiento: "doble",
          dia_segundo_vencimiento: 20,
          recargo_segundo_vencimiento: "1.50",
        }}
        historial={[V1]}
        accionCrear={accionCrear}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Cambiar configuración" }));
    const recargo = screen.getByLabelText("Recargo del segundo vencimiento");
    expect(recargo).toHaveProperty("value", "1,50");
    await usuario.clear(recargo);
    await usuario.type(recargo, "2,75");
    await usuario.type(screen.getByLabelText("Rige desde"), "2026-11-01");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findAllByText("Revisá la tasa");
    expect(envio?.get("recargo_segundo_vencimiento")).toBe("2,75");
    expect(recargo).toHaveProperty("value", "2,75");
  });

  it("sin configuración vigente muestra el estado y permite crear la primera versión", () => {
    render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={null}
        historial={[]}
        accionCrear={accionNula}
      />,
    );
    expect(screen.getByText("Todavía no configuraste la tasa ni el vencimiento.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Cambiar configuración" })).toBeTruthy();
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaConfiguracion
        id="e1"
        nombreEdificio="Edificio API"
        vigente={V2}
        historial={[V1, V2]}
        accionCrear={accionNula}
      />,
    );
    await sinViolaciones(container);
  });
});
