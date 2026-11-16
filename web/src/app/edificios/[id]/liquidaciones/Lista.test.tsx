/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { LiquidacionDeLaLista } from "../../../../lib/api/liquidaciones";
import { PantallaListaDeLiquidaciones } from "./Lista";

afterEach(cleanup);

const fila = (
  periodo: string,
  estado: LiquidacionDeLaLista["estado"],
  total: string,
): LiquidacionDeLaLista => ({
  liquidacion_id: `00000000-0000-0000-0000-0000000000${periodo.slice(5, 7)}`,
  periodo,
  estado,
  total,
  emitida_en: "2026-11-02T15:00:00+00:00",
});

function pintar(liquidaciones: LiquidacionDeLaLista[], periodoParaPreparar = "2026-12") {
  render(
    <PantallaListaDeLiquidaciones
      id="e1"
      nombreEdificio="Torre Ficticia"
      liquidaciones={liquidaciones}
      periodoParaPreparar={periodoParaPreparar}
    />,
  );
}

/** Las filas de la lista de períodos (el menú también tiene listas). */
function filas(): HTMLElement[] {
  const lista = document.querySelector("ul.lista-de-filas") as HTMLElement;
  return within(lista).getAllByRole("listitem");
}

describe("PantallaListaDeLiquidaciones (H-017)", () => {
  it("cada liquidación con su período en palabras, su estado en texto y su total", () => {
    pintar([fila("2026-11-01", "distribuida", "191500.00"), fila("2026-10-01", "emitida", "1.00")]);
    const items = filas();
    expect(items).toHaveLength(2);
    expect(items[0]?.textContent).toContain("noviembre de 2026");
    expect(items[0]?.textContent).toContain("Distribuida");
    expect(items[0]?.textContent).toContain("191.500,00");
    expect(
      within(items[0] as HTMLElement)
        .getByRole("link")
        .getAttribute("href"),
    ).toBe("/edificios/e1/liquidaciones/2026-11");
    expect(items[1]?.textContent).toContain("Emitida");
  });

  it("una anulada se ve como Anulada y sin ningún link", () => {
    pintar([fila("2026-10-01", "anulada", "180000.00")]);
    const [item] = filas() as [HTMLElement];
    expect(item.textContent).toContain("Anulada");
    expect(within(item).queryByRole("link")).toBeNull();
    expect(within(item).queryByRole("button")).toBeNull();
  });

  it("ofrece preparar el período que le pasan, en palabras", () => {
    pintar([fila("2026-11-01", "emitida", "1.00")], "2026-12");
    expect(
      screen
        .getByRole("link", { name: "Preparar la liquidación de diciembre de 2026" })
        .getAttribute("href"),
    ).toBe("/edificios/e1/liquidaciones/2026-12");
  });

  it("sin liquidaciones lo dice y igual ofrece preparar", () => {
    pintar([], "2026-06");
    expect(screen.getByText("Todavía no se emitió ninguna liquidación.")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /Preparar la liquidación de junio de 2026/ }),
    ).toBeTruthy();
  });
});
