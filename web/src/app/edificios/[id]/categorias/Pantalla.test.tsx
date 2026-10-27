/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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
  it("RF-F-2: guardar desde el estado vacío devuelve el foco al encabezado tras revalidar", async () => {
    const usuario = userEvent.setup();
    const accionCrear = vi
      .fn()
      .mockResolvedValue({ ok: true, erroresPorCampo: {}, erroresDesconocidos: [] });
    const vista = (conDatos: boolean) => (
      <PantallaCategorias
        id="1"
        nombreEdificio="Edificio API"
        categorias={conDatos ? [PORTON] : []}
        accionEstado={accionNula}
        accionReordenar={accionNula}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />
    );
    const { rerender } = render(vista(false));
    const botones = screen.getAllByRole("button", { name: "Agregar categoría" });
    const encabezado = botones[0];
    await usuario.click(botones[1] as HTMLElement);
    await usuario.type(screen.getByLabelText("Nombre"), "Portón");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(accionCrear).toHaveBeenCalledTimes(1);
    // La respuesta del servidor reemplaza el vacío y desmonta su botón.
    rerender(vista(true));
    expect(document.activeElement).toBe(encabezado);
    expect(encabezado?.isConnected).toBe(true);
  });

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

  it('el botón de estado dice sólo "Desactivar" a la vista y el nombre completo al lector de pantalla (pulido 3b)', () => {
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
    const boton = screen.getByRole("button", { name: "Desactivar Portón" });
    expect(boton.querySelector(".sr-only")?.textContent).toBe("Portón");
  });

  it('6.3 "Sin campo de clave" (categorías): "Agregar categoría" abre el panel sin campo "Clave", sólo "Nombre" — la clave se autogenera en el backend (4.1-4.4)', async () => {
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
    expect(screen.queryByLabelText("Clave")).toBeNull();
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

  it("R3C-4 · tocar otra categoría con el panel abierto no mezcla el nombre tipeado con el id de la otra", async () => {
    const accionEditar = vi.fn().mockResolvedValue(null);
    const usuario = userEvent.setup();
    const { container } = render(
      <PantallaCategorias
        id="e1"
        nombreEdificio="Edificio API"
        categorias={[PORTON, LIMPIEZA, ASCENSOR]}
        accionCrear={accionNula}
        accionEditar={accionEditar}
        accionEstado={accionNula}
        accionReordenar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Portón" }));
    const nombre = screen.getByLabelText("Nombre") as HTMLInputElement;
    await usuario.clear(nombre);
    await usuario.type(nombre, "Portón renombrado a medias");
    await usuario.click(screen.getByRole("button", { name: "Limpieza" }));
    // `querySelector` simple matchearía el hidden de activar/desactivar de
    // la primera fila (mismo `name`, D-ficha 4.5): el del panel es el que
    // vive dentro de `.formulario` (D8).
    const oculto = container.querySelector(
      '.formulario input[name="categoria_id"]',
    ) as HTMLInputElement;
    expect({
      id: oculto.value,
      nombre: (screen.getByLabelText("Nombre") as HTMLInputElement).value,
    }).toEqual({ id: "c2", nombre: "Limpieza" });
  });
});
