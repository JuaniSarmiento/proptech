/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Armazon } from "./Armazon";
import { SesionDePantalla } from "./SesionDePantalla";

afterEach(cleanup);

describe("Armazon", () => {
  it("barra superior con el edificio actual en la miga y el contenido en el único <main>", () => {
    render(
      <Armazon edificio={{ nombre: "Alsina 123" }}>
        <h1>Resumen del edificio</h1>
      </Armazon>,
    );
    const migas = screen.getByRole("navigation", { name: "Estás en" });
    expect(within(migas).getByRole("link", { name: "Mis edificios" }).getAttribute("href")).toBe(
      "/edificios",
    );
    expect(within(migas).getByText("Alsina 123").closest("li")?.getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(within(screen.getByRole("main")).getByRole("heading", { level: 1 })).toBeTruthy();
  });

  it("fuera de un edificio muestra la persona y su administración real", () => {
    render(
      <SesionDePantalla
        value={{
          datos: {
            persona: { nombre: "Ana Ejemplo" },
            administraciones: [
              {
                id: "a",
                nombre: "Administración del Parque",
                acciones: { administracion: [], todos_los_edificios: [], por_edificio: {} },
              },
            ],
          },
          administracionId: "a",
        }}
      >
        <Armazon>
          <h1>Mis edificios</h1>
        </Armazon>
      </SesionDePantalla>,
    );
    expect(screen.queryByRole("navigation", { name: "Estás en" })).toBeNull();
    expect(within(screen.getByRole("banner")).getByText("Ana Ejemplo")).toBeTruthy();
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <Armazon edificio={{ nombre: "Alsina 123" }}>
        <h1>Resumen</h1>
      </Armazon>,
    );
    await sinViolaciones(container);
  });
});
