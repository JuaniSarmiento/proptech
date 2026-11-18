/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { PagoInformado } from "../../../../lib/api/pagos";
import { PantallaMisPagos } from "./Pantalla";

afterEach(cleanup);

const pago = (numero: string, estado: PagoInformado["estado"], motivo: string | null = null) =>
  ({
    pago_id: `00000000-0000-0000-0000-0000000000${numero.slice(-2)}`,
    estado,
    motivo,
    banco: "Banco Nación",
    numero_de_operacion: numero,
    fecha_de_transferencia: "2026-11-05",
    monto: "43350.00",
    partes: [{ unidad_id: "u1", identificador: "1A", importe: "43350.00" }],
  }) satisfies PagoInformado;

function pintar(pagos: PagoInformado[]) {
  render(<PantallaMisPagos id="e1" nombreEdificio="Torre Ficticia" pagos={pagos} />);
}

describe("PantallaMisPagos (H-025)", () => {
  it("cada pago con su número, su monto con punto de miles y su estado en texto", () => {
    pintar([pago("11110001", "informado"), pago("11110002", "confirmado")]);
    const filas = within(screen.getByRole("list", { name: "Pagos informados" })).getAllByRole(
      "listitem",
    );
    expect(filas).toHaveLength(2);
    expect(filas[0]?.textContent).toContain("11110001");
    expect(filas[0]?.textContent).toContain("43.350,00");
    expect(filas[0]?.textContent).toContain("Informado");
    expect(filas[1]?.textContent).toContain("Confirmado");
    expect(filas[0]?.textContent).toContain("Unidad 1A");
  });

  it("un rechazo y una reversión muestran su motivo", () => {
    pintar([
      pago("11110003", "rechazado", "El monto no coincide con el comprobante"),
      pago("11110004", "revertido", "Cheque rechazado"),
    ]);
    const filas = within(screen.getByRole("list", { name: "Pagos informados" })).getAllByRole(
      "listitem",
    );
    expect(filas[0]?.textContent).toContain("Rechazado");
    expect(filas[0]?.textContent).toContain("El monto no coincide con el comprobante");
    expect(filas[1]?.textContent).toContain("Revertido");
    expect(filas[1]?.textContent).toContain("Cheque rechazado");
  });

  it("ofrece Informar un pago, y sin pagos lo dice", () => {
    pintar([]);
    expect(screen.getByRole("heading", { name: "Mis pagos", level: 1 })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Informar un pago" }).getAttribute("href")).toBe(
      "/edificios/e1/mis-pagos/informar",
    );
    expect(screen.getByText("Todavía no informaste ningún pago.")).toBeTruthy();
    expect(screen.queryByRole("list", { name: "Pagos informados" })).toBeNull();
  });
});
