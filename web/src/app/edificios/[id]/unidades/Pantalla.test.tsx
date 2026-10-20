/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Unidad } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaPadron } from "./Pantalla";

afterEach(cleanup);

const UNIDAD_1A: Unidad = {
  id: "u1",
  complejo_id: "1",
  identificador: "1A",
  tipo: "departamento",
  piso: "1",
  coeficiente: "0.500000",
  superficie_m2: "60.00",
};

function accionNula() {
  return Promise.resolve(null);
}

describe("PantallaPadron", () => {
  it('informe "fuera_de_tolerancia" con diferencia -0.000200 se muestra en texto (Fuera de tolerancia)', () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[UNIDAD_1A]}
        informe={{ suma: "0.999800", diferencia: "-0.000200", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText(/falta 0,0200 %/)).toBeTruthy();
  });

  it("sin unidades muestra el estado vacío con Agregar unidad", () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText(/Todavía no cargaste unidades/)).toBeTruthy();
  });

  it("la tabla muestra números tabulares alineados a la derecha, con formato argentino (D6)", () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText("60,00")).toBeTruthy();
    expect(screen.getByText("0,500000")).toBeTruthy();
  });

  it('"Agregar unidad" abre el panel con el formulario de alta', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    expect(screen.getByLabelText("Identificador")).toBeTruthy();
  });

  it("tocar una fila abre el panel con los datos de esa unidad (edición)", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    expect(screen.getByLabelText("Identificador")).toHaveProperty("value", "1A");
  });

  it("409 de identificador repetido marca el campo identificador, sin el texto técnico (Identificador repetido)", async () => {
    const accionCrear = vi.fn().mockResolvedValue({
      erroresPorCampo: { identificador: "Ya existe una unidad con este identificador." },
      erroresDesconocidos: [],
    });
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    await usuario.type(screen.getByLabelText("Identificador"), "1A");
    await usuario.type(screen.getByLabelText("Superficie (m²)"), "60.00");
    await usuario.type(screen.getByLabelText("Coeficiente"), "0.500000");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      (await screen.findAllByText("Ya existe una unidad con este identificador.")).length,
    ).toBeGreaterThan(0);
  });

  it('el tipo se muestra con su etiqueta ("Departamento"), no con la clave cruda de la API (pulido 3b)', () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByRole("cell", { name: "Departamento" })).toBeTruthy();
  });

  it("prueba con 200 unidades: la tabla renderiza sin romper", () => {
    const unidades: Unidad[] = Array.from({ length: 200 }, (_, i) => ({
      ...UNIDAD_1A,
      id: `u${i}`,
      identificador: `U${i}`,
    }));
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={unidades}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getAllByRole("row").length).toBe(201); // 200 + encabezado
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await sinViolaciones(container);
  });
});
