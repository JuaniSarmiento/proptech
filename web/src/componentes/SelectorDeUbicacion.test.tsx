/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as accionesGeoref from "./accionesGeoref";
import { SelectorDeUbicacion } from "./SelectorDeUbicacion";

// Mock explícito (no automock): el automock de vitest igual importa el
// módulo real para inspeccionar su forma, y éste cuelga de `server-only`
// vía `lib/api/cliente.ts` → `lib/sesion.ts` (D3, tarea 6.1).
vi.mock("./accionesGeoref", () => ({
  provinciasAction: vi.fn(),
  departamentosDeAction: vi.fn(),
  localidadesDeAction: vi.fn(),
}));

afterEach(cleanup);

const PROVINCIAS = [{ id: "50", nombre: "Mendoza" }];
const DEPARTAMENTOS = [{ id: "50007", nombre: "Capital" }];
const LOCALIDADES = [{ id: "50007010", nombre: "Mendoza" }];

function _deshabilitado(etiqueta: string): boolean {
  return (screen.getByLabelText(etiqueta) as HTMLSelectElement).disabled;
}

function _valor(etiqueta: string): string {
  return (screen.getByLabelText(etiqueta) as HTMLSelectElement).value;
}

describe("SelectorDeUbicacion", () => {
  it('D3 (6.1) "Encadenar las listas": elegir provincia carga y habilita departamento', async () => {
    const usuario = userEvent.setup();
    vi.mocked(accionesGeoref.provinciasAction).mockResolvedValue({
      estado: "ok",
      datos: PROVINCIAS,
    });
    vi.mocked(accionesGeoref.departamentosDeAction).mockResolvedValue({
      estado: "ok",
      datos: DEPARTAMENTOS,
    });
    render(<SelectorDeUbicacion />);
    await waitFor(() => expect(_deshabilitado("Provincia")).toBe(false));
    expect(_deshabilitado("Departamento")).toBe(true);
    await usuario.selectOptions(screen.getByLabelText("Provincia"), "50");
    await waitFor(() => expect(_deshabilitado("Departamento")).toBe(false));
    expect(screen.getByRole("option", { name: "Capital" })).toBeTruthy();
    expect(accionesGeoref.departamentosDeAction).toHaveBeenCalledWith("50");
  });

  it('D3 (6.1) "Elegir la ubicación con teclado": las tres listas son <select> nativos', async () => {
    vi.mocked(accionesGeoref.provinciasAction).mockResolvedValue({
      estado: "ok",
      datos: PROVINCIAS,
    });
    render(<SelectorDeUbicacion />);
    await waitFor(() => expect(_deshabilitado("Provincia")).toBe(false));
    expect(screen.getByLabelText("Provincia").tagName).toBe("SELECT");
    expect(screen.getByLabelText("Departamento").tagName).toBe("SELECT");
    expect(screen.getByLabelText("Localidad").tagName).toBe("SELECT");
  });

  it('D3 (6.1) "Una lista no carga y se puede reintentar": error con botón, reintentar la recupera', async () => {
    const usuario = userEvent.setup();
    vi.mocked(accionesGeoref.provinciasAction)
      .mockResolvedValueOnce({ estado: "fallo" })
      .mockResolvedValueOnce({ estado: "ok", datos: PROVINCIAS });
    render(<SelectorDeUbicacion />);
    await waitFor(() => expect(screen.getByText(/no pudimos cargar las provincias/i)).toBeTruthy());
    await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() => expect(screen.getByRole("option", { name: "Mendoza" })).toBeTruthy());
  });

  it("vaciar la provincia vacía departamento y localidad (vaciado en cascada)", async () => {
    const usuario = userEvent.setup();
    vi.mocked(accionesGeoref.provinciasAction).mockResolvedValue({
      estado: "ok",
      datos: PROVINCIAS,
    });
    vi.mocked(accionesGeoref.departamentosDeAction).mockResolvedValue({
      estado: "ok",
      datos: DEPARTAMENTOS,
    });
    vi.mocked(accionesGeoref.localidadesDeAction).mockResolvedValue({
      estado: "ok",
      datos: LOCALIDADES,
    });
    render(<SelectorDeUbicacion />);
    await waitFor(() => expect(_deshabilitado("Provincia")).toBe(false));
    await usuario.selectOptions(screen.getByLabelText("Provincia"), "50");
    await waitFor(() => expect(_deshabilitado("Departamento")).toBe(false));
    await usuario.selectOptions(screen.getByLabelText("Departamento"), "50007");
    await waitFor(() => expect(_deshabilitado("Localidad")).toBe(false));
    await usuario.selectOptions(screen.getByLabelText("Localidad"), "50007010");
    expect(_valor("Localidad")).toBe("50007010");

    await usuario.selectOptions(screen.getByLabelText("Provincia"), "");
    expect(_valor("Departamento")).toBe("");
    expect(_valor("Localidad")).toBe("");
    expect(_deshabilitado("Departamento")).toBe(true);
  });

  it('D3 (6.1) "Edificio migrado sin ubicación": con un trío ya guardado, completa las tres listas', async () => {
    vi.mocked(accionesGeoref.provinciasAction).mockResolvedValue({
      estado: "ok",
      datos: PROVINCIAS,
    });
    vi.mocked(accionesGeoref.departamentosDeAction).mockResolvedValue({
      estado: "ok",
      datos: DEPARTAMENTOS,
    });
    vi.mocked(accionesGeoref.localidadesDeAction).mockResolvedValue({
      estado: "ok",
      datos: LOCALIDADES,
    });
    render(
      <SelectorDeUbicacion
        valorInicial={{ provinciaId: "50", departamentoId: "50007", localidadId: "50007010" }}
      />,
    );
    await waitFor(() => expect(_valor("Localidad")).toBe("50007010"));
    expect(_valor("Provincia")).toBe("50");
    expect(_valor("Departamento")).toBe("50007");
  });
});
