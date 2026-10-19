/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { EncabezadoDePantalla } from "./EncabezadoDePantalla";

afterEach(cleanup);

describe("EncabezadoDePantalla", () => {
  it("muestra el título como encabezado, la ayuda y la acción principal", () => {
    render(
      <EncabezadoDePantalla
        titulo="Padrón de unidades"
        ayuda={<button type="button">Ayuda de prueba</button>}
        accionPrincipal={<button type="button">Agregar unidad</button>}
      />,
    );
    expect(screen.getByRole("heading", { name: "Padrón de unidades" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Ayuda de prueba" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Agregar unidad" })).toBeTruthy();
  });

  it("funciona sin acción principal (no toda pantalla tiene una)", () => {
    render(<EncabezadoDePantalla titulo="Mis edificios" ayuda={null as ReactNode} />);
    expect(screen.getByRole("heading", { name: "Mis edificios" })).toBeTruthy();
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <EncabezadoDePantalla
        titulo="Grupos de reparto"
        ayuda={<button type="button">Ayuda</button>}
        accionPrincipal={<button type="button">Nuevo grupo</button>}
      />,
    );
    await sinViolaciones(container);
  });
});
