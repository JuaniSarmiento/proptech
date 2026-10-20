/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Categoria } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaCategorias } from "./Pantalla";

afterEach(cleanup);

const PORTON: Categoria = {
  id: "c1",
  complejo_id: "e1",
  clave: "porton",
  nombre: "Portón",
  orden: 0,
  activa: true,
};
const LIMPIEZA: Categoria = {
  id: "c2",
  complejo_id: "e1",
  clave: "limpieza",
  nombre: "Limpieza",
  orden: 1,
  activa: true,
};
const ASCENSOR: Categoria = {
  id: "c3",
  complejo_id: "e1",
  clave: "ascensor",
  nombre: "Ascensor",
  orden: 2,
  activa: false,
};

function accionNula() {
  return Promise.resolve(null);
}

describe("PantallaCategorias", () => {
  it('sube la tercera con el teclado: la API recibe el orden completo con "Ascensor" en segundo lugar, y el foco queda en su botón "subir"', async () => {
    const accionReordenar = vi.fn().mockResolvedValue({ erroresDesconocidos: [], ok: true });
    const usuario = userEvent.setup();
    const { rerender } = render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON, LIMPIEZA, ASCENSOR]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionReordenar}
      />,
    );

    const botonSubir = screen.getByRole("button", { name: "Subir Ascensor" });
    botonSubir.focus();
    await usuario.keyboard("{Enter}");

    expect(accionReordenar).toHaveBeenCalledTimes(1);
    const formData = accionReordenar.mock.calls[0]?.[1] as FormData;
    expect(formData.getAll("orden")).toEqual(["c1", "c3", "c2"]);

    // Simula la revalidación del servidor (D1): la API ya devuelve el orden
    // nuevo. El foco tiene que seguir en el mismo botón "subir", ahora en
    // la segunda fila.
    rerender(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON, ASCENSOR, LIMPIEZA]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionReordenar}
      />,
    );

    expect(document.activeElement?.getAttribute("aria-label")).toBe("Subir Ascensor");
  });

  it('la primera categoría no tiene "subir" ni la última "bajar"', () => {
    render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON, LIMPIEZA, ASCENSOR]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    expect(screen.queryByRole("button", { name: "Subir Portón" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Bajar Ascensor" })).toBeNull();
    expect(screen.getByRole("button", { name: "Bajar Portón" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Subir Ascensor" })).toBeTruthy();
  });

  it("muestra el estado de cada categoría en texto (activa/desactivada)", () => {
    render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON, ASCENSOR]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    const lista = screen.getByRole("list", { name: "Categorías de gasto" });
    expect(within(lista).getByText("Activa")).toBeTruthy();
    expect(within(lista).getByText("Desactivada")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Reactivar Ascensor" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Desactivar Portón" })).toBeTruthy();
  });

  it('"Agregar categoría" abre el panel con clave y nombre', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Agregar categoría" }));
    expect(screen.getByLabelText("Clave")).toBeTruthy();
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
  });

  it("tocar el nombre de una categoría abre el panel de renombrar precargado", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Portón" }));
    expect(screen.getByLabelText("Nombre")).toHaveProperty("value", "Portón");
    expect(screen.queryByLabelText("Clave")).toBeNull();
  });

  it('sin categorías muestra el estado vacío con "Agregar categoría"', () => {
    render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    expect(screen.getByText("Todavía no tenés categorías")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Agregar categoría" }).length).toBeGreaterThan(0);
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON, LIMPIEZA, ASCENSOR]}
        accionCrear={accionNula}
        accionEditar={accionNula}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    await sinViolaciones(container);
  });
});
