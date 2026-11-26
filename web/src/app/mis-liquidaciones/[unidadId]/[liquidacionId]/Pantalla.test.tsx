/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { ExpensaDeLaUnidad, UnidadDelVecino } from "../../../../lib/api/vecino";
import { PantallaExpensa } from "./Pantalla";

afterEach(cleanup);

const unidad: UnidadDelVecino = {
  unidad_id: "u1",
  identificador: "1B",
  vinculo: "inquilino",
  complejo_id: "e1",
  edificio: "Torre Ficticia",
  total_a_pagar: "36500.00",
  vencimiento: "2026-11-10",
  deuda_anterior: "0.00",
  intereses: "0.00",
  credito_aplicable: "0.00",
  credito_retenido: "0.00",
};

// La expensa del inquilino tal como la da la API: sin ninguna clave extraordinaria (D-170.2).
const delInquilino: ExpensaDeLaUnidad = {
  liquidacion_id: "l1",
  complejo_id: "e1",
  unidad_id: "u1",
  identificador: "1B",
  periodo: "2026-11-01",
  vencimiento: "2026-11-10",
  vinculo: "inquilino",
  bloques: {
    ordinario: {
      subtotal: "140000.00",
      categorias: [
        { categoria_id: "c1", nombre: "Limpieza", importe: "140000.00", porcentaje: "100.00" },
      ],
    },
  },
  grupos: [{ grupo_id: "g1", nombre: "Generales", ordinaria: "30000.00" }],
  ordinaria: "30000.00",
  cargos_particulares: [{ concepto: "Multa", importe: "5000.00" }],
  fondo_de_reserva: "1500.00",
  intereses: "0.00",
  total: "36500.00",
  comparacion: null,
};

describe("PantallaExpensa", () => {
  it("N01: sin claves extraordinarias de la API, no dibuja nada extraordinario ni lo inventa", () => {
    render(<PantallaExpensa expensa={delInquilino} unidad={unidad} unidades={[unidad]} />);
    expect(document.body.textContent ?? "").not.toMatch(/extraordinari/i);
    expect(screen.queryByRole("region", { name: "Gastos extraordinarios" })).toBeNull();
  });

  it("la tabla Tu expensa sigue el orden del contrato y el total es el de la API (N02)", () => {
    render(<PantallaExpensa expensa={delInquilino} unidad={unidad} unidades={[unidad]} />);
    const tabla = screen.getByRole("table", { name: "Tu expensa" });
    const filas = within(tabla)
      .getAllByRole("row")
      .map((f) => f.textContent);
    expect(filas).toEqual([
      "Ordinaria30.000,00",
      "Multa5.000,00",
      "Fondo de reserva1.500,00",
      "Intereses0,00",
      "Total36.500,00",
    ]);
  });

  it("sin comparación lo dice en un estado, sin la región", () => {
    render(<PantallaExpensa expensa={delInquilino} unidad={unidad} unidades={[unidad]} />);
    expect(screen.getByRole("status").textContent).toBe(
      "No hay una liquidación anterior para comparar.",
    );
    expect(screen.queryByRole("region", { name: "Comparación con el mes anterior" })).toBeNull();
  });

  it("N02: la diferencia de la comparación es la de la API aunque no cuadre con la resta", () => {
    const conComparacion: ExpensaDeLaUnidad = {
      ...delInquilino,
      comparacion: {
        liquidacion_id: "l0",
        periodo: "2026-10-01",
        total_anterior: "25200.00",
        diferencia_total: "11300.01",
        categorias: [],
      },
    };
    render(<PantallaExpensa expensa={conComparacion} unidad={unidad} unidades={[unidad]} />);
    const region = screen.getByRole("region", { name: "Comparación con el mes anterior" });
    expect(
      within(region).getByRole("heading", { name: "Comparación con octubre de 2026" }),
    ).toBeTruthy();
    expect(region.textContent).toContain("11.300,01");
    expect(region.textContent).not.toContain("11.300,00");
  });
});
