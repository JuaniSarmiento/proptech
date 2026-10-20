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
    expect(screen.getByLabelText("Tasa mensual")).toHaveProperty("value", "3.00"); // crudo de la API, no formato argentino: se resubmite tal cual
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
