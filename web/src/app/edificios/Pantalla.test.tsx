/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sinViolaciones } from "../../lib/test/accesibilidad";
import { PantallaMisEdificios } from "./Pantalla";

// `SelectorDeUbicacion` llama a estas server actions; mockeadas para que
// el árbol de imports nunca llegue a `server-only` (D3, tarea 6.1).
vi.mock("../../componentes/accionesGeoref", () => ({
  provinciasAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
  departamentosDeAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
  localidadesDeAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
}));

afterEach(cleanup);

describe("PantallaMisEdificios", () => {
  it('sin edificios muestra "Todavía no tenés edificios" con "Nuevo edificio" (Sin edificios)', () => {
    render(<PantallaMisEdificios edificios={[]} accionCrear={vi.fn()} />);
    expect(screen.getByText("Todavía no tenés edificios")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Nuevo edificio" }).length).toBeGreaterThan(0);
  });

  it("con un solo edificio muestra la lista igual, no entra directo (D11)", () => {
    render(
      <PantallaMisEdificios
        edificios={[
          {
            id: "1",
            nombre: "Edificio Único",
            localidad: "Mendoza",
            cantidadUnidades: 5,
            estadoCoeficientes: "ok",
            diferencia: "0.000000",
            estadoMigracion: "pendiente",
          },
        ]}
        accionCrear={vi.fn()}
      />,
    );
    expect(screen.getByRole("link", { name: /Edificio Único/ })).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Nuevo edificio" }).length).toBeGreaterThan(0);
  });

  it("cada fila muestra localidad, unidades, estado de coeficientes (con texto) y estado de migración", () => {
    render(
      <PantallaMisEdificios
        edificios={[
          {
            id: "1",
            nombre: "Edificio API",
            localidad: "Mendoza",
            cantidadUnidades: 13,
            estadoCoeficientes: "fuera_de_tolerancia",
            diferencia: "-0.000200",
            estadoMigracion: "pendiente",
          },
        ]}
        accionCrear={vi.fn()}
      />,
    );
    expect(screen.getByText(/Mendoza/)).toBeTruthy();
    expect(screen.getByText(/13/)).toBeTruthy();
    expect(screen.getByText(/falta 0,0200 %/)).toBeTruthy();
    expect(screen.getByText("Pendiente de confirmar saldos previos")).toBeTruthy();
  });

  it("el enlace de cada fila se llama como el edificio, no con todos los estados pegados (pulido 3b)", () => {
    render(
      <PantallaMisEdificios
        edificios={[
          {
            id: "7",
            nombre: "Edificio API",
            localidad: "Mendoza",
            cantidadUnidades: 13,
            estadoCoeficientes: "ok",
            diferencia: "0.000000",
            estadoMigracion: "pendiente",
          },
        ]}
        accionCrear={vi.fn()}
      />,
    );
    const enlace = screen.getByRole("link", { name: "Edificio API" });
    expect(enlace.getAttribute("href")).toBe("/edificios/7");
  });

  it('"Nuevo edificio" abre el panel con el formulario (nombre, ubicación, pisos y subsuelos)', async () => {
    const usuario = userEvent.setup();
    render(<PantallaMisEdificios edificios={[]} accionCrear={vi.fn()} />);
    await usuario.click(
      screen.getAllByRole("button", { name: "Nuevo edificio" })[0] as HTMLElement,
    );
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
    expect(screen.getByLabelText("Provincia")).toBeTruthy();
    expect(screen.getByLabelText("Pisos")).toBeTruthy();
    expect(screen.getByLabelText("Subsuelos")).toBeTruthy();
  });

  it("403 al crear (administrador sin permiso) muestra el resumen de error sin marcar un campo", async () => {
    const accionCrear = vi.fn().mockResolvedValue({
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés crear un edificio nuevo."],
    });
    render(<PantallaMisEdificios edificios={[]} accionCrear={accionCrear} />);
    const usuario = userEvent.setup();
    await usuario.click(
      screen.getAllByRole("button", { name: "Nuevo edificio" })[0] as HTMLElement,
    );
    await usuario.type(screen.getByLabelText("Nombre"), "X");
    await usuario.type(screen.getByLabelText("Pisos"), "4");
    await usuario.type(screen.getByLabelText("Subsuelos"), "1");
    await usuario.click(screen.getByRole("button", { name: "Crear edificio" }));
    expect(await screen.findByText("No podés crear un edificio nuevo.")).toBeTruthy();
  });

  it("sin violaciones de axe, vacío y con edificios", async () => {
    const { container, rerender } = render(
      <PantallaMisEdificios edificios={[]} accionCrear={vi.fn()} />,
    );
    await sinViolaciones(container);
    rerender(
      <PantallaMisEdificios
        edificios={[
          {
            id: "1",
            nombre: "Edificio API",
            localidad: "Mendoza",
            cantidadUnidades: 3,
            estadoCoeficientes: "ok",
            diferencia: "0.000000",
            estadoMigracion: "pendiente",
          },
        ]}
        accionCrear={vi.fn()}
      />,
    );
    await sinViolaciones(container);
  });
});
