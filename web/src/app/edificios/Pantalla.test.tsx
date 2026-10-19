/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sinViolaciones } from "../../lib/test/accesibilidad";
import { PantallaMisEdificios } from "./Pantalla";

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

  it('"Nuevo edificio" abre el panel con el formulario (nombre y localidad)', async () => {
    const usuario = userEvent.setup();
    render(<PantallaMisEdificios edificios={[]} accionCrear={vi.fn()} />);
    await usuario.click(
      screen.getAllByRole("button", { name: "Nuevo edificio" })[0] as HTMLElement,
    );
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
    expect(screen.getByLabelText("Localidad")).toBeTruthy();
  });

  it("403 al crear (colaborador sin permiso) muestra el resumen de error sin marcar un campo", async () => {
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
    await usuario.type(screen.getByLabelText("Localidad"), "Y");
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
