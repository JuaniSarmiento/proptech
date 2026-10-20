/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Panel } from "./Panel";

afterEach(cleanup);

describe("Panel", () => {
  it("es una región con el nombre de su título y la línea que dice para qué sirve", () => {
    render(
      <Panel titulo="Suma de coeficientes" descripcion="Tiene que dar 100%.">
        <p>110,0000 %</p>
      </Panel>,
    );
    const region = screen.getByRole("region", { name: "Suma de coeficientes" });
    expect(within(region).getByRole("heading", { level: 2 }).textContent).toBe(
      "Suma de coeficientes",
    );
    expect(within(region).getByText("Tiene que dar 100%.")).toBeTruthy();
    expect(within(region).getByText("110,0000 %")).toBeTruthy();
  });

  it("dos paneles en la misma pantalla no comparten el id de su título", () => {
    render(
      <>
        <Panel titulo="Uno">a</Panel>
        <Panel titulo="Dos">b</Panel>
      </>,
    );
    expect(screen.getByRole("region", { name: "Uno" })).toBeTruthy();
    expect(screen.getByRole("region", { name: "Dos" })).toBeTruthy();
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <Panel titulo="Datos del edificio" variante="apoyo">
        <p>Mendoza</p>
      </Panel>,
    );
    await sinViolaciones(container);
  });
});
