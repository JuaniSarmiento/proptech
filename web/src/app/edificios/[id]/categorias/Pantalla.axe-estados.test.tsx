/**
 * @vitest-environment jsdom
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import type { Categoria } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaCategorias } from "./Pantalla";

// pulido-2 (3d), escenario "axe cubre más de un estado": el test de la pantalla
// sólo mide el estado feliz. Acá: vacío, panel de alta abierto y panel con un error de campo.
afterEach(cleanup);

const PORTON: Categoria = {
  id: "c1",
  complejo_id: "e1",
  clave: "porton",
  nombre: "Portón",
  orden: 0,
  activa: true,
};

function accionNula() {
  return Promise.resolve(null);
}

function accionConError() {
  return Promise.resolve({
    erroresPorCampo: { nombre: "Ya existe una categoría con este nombre." },
    erroresDesconocidos: [],
  });
}

function pantalla(categorias: Categoria[], accionCrear: typeof accionNula | typeof accionConError) {
  return (
    <PantallaCategorias
      id="e1"
      nombreEdificio="Edificio API"
      categorias={categorias}
      accionCrear={accionCrear}
      accionEditar={accionNula}
      accionEstado={accionNula}
      accionReordenar={accionNula}
    />
  );
}

describe("PantallaCategorias · axe por estado", () => {
  it("estado vacío, sin violaciones", async () => {
    const { container } = render(pantalla([], accionNula));
    expect(screen.getByText("Todavía no tenés categorías")).toBeTruthy();
    await sinViolaciones(container);
  });

  it("panel de alta abierto, sin violaciones", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla([PORTON], accionNula));
    await usuario.click(screen.getByRole("button", { name: "Agregar categoría" }));
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
    await sinViolaciones(container);
  });

  it("panel con un error de campo, sin violaciones", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla([PORTON], accionConError));
    await usuario.click(screen.getByRole("button", { name: "Agregar categoría" }));
    const nombre = screen.getByLabelText("Nombre");
    fireEvent.change(nombre, { target: { value: "Portón" } });
    await act(async () => {
      fireEvent.submit(nombre.closest("form") as HTMLFormElement);
    });
    expect(nombre.getAttribute("aria-invalid")).toBe("true");
    await sinViolaciones(container);
  });
});
