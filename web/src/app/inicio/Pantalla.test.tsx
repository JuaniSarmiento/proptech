/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { MisUnidades, UnidadDelVecino } from "../../lib/api/vecino";
import { PantallaInicio } from "./Pantalla";

afterEach(cleanup);

const unidad = (identificador: string, extra: Partial<UnidadDelVecino> = {}): UnidadDelVecino => ({
  unidad_id: `id-${identificador}`,
  identificador,
  vinculo: "propietario",
  complejo_id: "e1",
  edificio: "Torre Ficticia",
  total_a_pagar: "40250.00",
  vencimiento: "2026-11-10",
  deuda_anterior: "0.00",
  intereses: "0.00",
  credito_aplicable: "1200.00",
  credito_retenido: "800.50",
  ...extra,
});

const conjunto = {
  total_a_pagar: "86750.01",
  intereses: "1250.00",
  credito_aplicable: "1200.00",
  credito_retenido: "800.50",
};

const datos = (unidades: UnidadDelVecino[]): MisUnidades => ({
  fecha: "2026-11-18",
  conjunto,
  unidades,
});

describe("PantallaInicio", () => {
  it("cada unidad con sus cifras y su enlace, y el conjunto tal cual lo da la API (N02)", () => {
    render(
      <PantallaInicio
        datos={datos([unidad("2B"), unidad("9A", { vencimiento: null, total_a_pagar: "0.00" })])}
      />,
    );
    const region = screen.getByRole("region", { name: "Total del conjunto" });
    expect(region.textContent).toContain("86.750,01");
    const filas = within(screen.getByRole("list", { name: "Mis unidades" })).getAllByRole(
      "listitem",
    );
    expect(filas).toHaveLength(2);
    expect(filas[0]?.textContent).toContain("40.250,00");
    expect(filas[0]?.textContent).toContain("10/11/2026");
    expect(filas[1]?.textContent).toContain("Sin vencimiento");
    expect(
      within(filas[0] as HTMLElement)
        .getByRole("link", { name: "Ver liquidaciones de 2B" })
        .getAttribute("href"),
    ).toBe("/mis-liquidaciones/id-2B");
  });

  it("con una sola unidad no repite su total como 'del conjunto'", () => {
    render(<PantallaInicio datos={datos([unidad("1B", { vinculo: "inquilino" })])} />);
    expect(screen.queryByRole("region", { name: "Total del conjunto" })).toBeNull();
    expect(document.body.textContent ?? "").not.toMatch(/extraordinari/i);
  });

  it("sin unidades lo dice, sin listas ni cifras", () => {
    render(<PantallaInicio datos={datos([])} />);
    expect(screen.getByRole("status").textContent).toContain("Todavía no tenés unidades");
    expect(screen.queryByRole("list", { name: "Mis unidades" })).toBeNull();
  });
});
