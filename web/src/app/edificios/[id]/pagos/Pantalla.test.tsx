/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type { PagoInformado, UnidadParaInformar } from "../../../../lib/api/pagos";
import type { PedidoDeResolucion, ResultadoDeResolucion } from "./acciones";
import { PantallaPagos } from "./Pantalla";

afterEach(cleanup);

const TODAS = ["confirmar_pago_informado", "revertir_o_reimputar_pago"];

function render(ui: ReactElement, acciones: string[] = TODAS) {
  return renderOriginal(
    <SesionDePantalla
      value={{
        administracionId: "a",
        datos: {
          persona: { nombre: "Prueba" },
          administraciones: [
            {
              id: "a",
              nombre: "A",
              acciones: { administracion: [], todos_los_edificios: acciones, por_edificio: {} },
            },
          ],
        },
      }}
    >
      {ui}
    </SesionDePantalla>,
  );
}

const pago = (
  numero: string,
  estado: PagoInformado["estado"],
  unidad = { id: "u-2b", nombre: "2B" },
  vigente = unidad,
): PagoInformado => ({
  pago_id: `p-${numero}`,
  estado,
  motivo: null,
  banco: "Banco Nación",
  numero_de_operacion: numero,
  fecha_de_transferencia: "2026-11-05",
  monto: "37425.00",
  partes: [
    {
      unidad_id: unidad.id,
      identificador: unidad.nombre,
      importe: "37425.00",
      unidad_vigente_id: vigente.id,
      identificador_vigente: vigente.nombre,
    },
  ],
});

const UNIDADES: UnidadParaInformar[] = [
  { unidad_id: "u-1a", identificador: "1A" },
  { unidad_id: "u-2a", identificador: "2A" },
  { unidad_id: "u-2b", identificador: "2B" },
];

function pintar(
  pagos: PagoInformado[],
  opciones: {
    acciones?: string[];
    resolver?: (id: string, pedido: PedidoDeResolucion) => Promise<ResultadoDeResolucion>;
  } = {},
) {
  const resolver = vi.fn(opciones.resolver ?? (async () => ({ hecho: "Pago confirmado." })));
  const verComprobante = vi.fn(async () => ({ error: "No pudimos preparar el comprobante." }));
  render(
    <PantallaPagos
      id="e1"
      nombreEdificio="Torre Ficticia"
      pagos={pagos}
      unidades={UNIDADES}
      accionResolver={resolver}
      accionVerComprobante={verComprobante}
    />,
    opciones.acciones,
  );
  return { resolver, verComprobante };
}

const fila = (numero: string) =>
  within(screen.getByRole("list", { name: "Pagos del edificio" }))
    .getAllByRole("listitem")
    .find((li) => li.textContent?.includes(numero)) as HTMLElement;

describe("PantallaPagos (H-025)", () => {
  it("un informado ofrece Confirmar y Rechazar; un confirmado, Revertir y Reimputar; todos, Ver comprobante", () => {
    pintar([pago("AAA1", "informado"), pago("BBB2", "confirmado"), pago("CCC3", "rechazado")]);
    const botones = (n: string) =>
      within(fila(n))
        .getAllByRole("button")
        .map((b) => b.textContent);
    expect(botones("AAA1")).toEqual(["Confirmar", "Rechazar", "Ver comprobante"]);
    expect(botones("BBB2")).toEqual(["Revertir", "Reimputar", "Ver comprobante"]);
    expect(botones("CCC3")).toEqual(["Ver comprobante"]);
  });

  it("sin permiso de resolver no se ofrece nada de eso, sólo el comprobante", () => {
    pintar([pago("AAA1", "informado"), pago("BBB2", "confirmado")], { acciones: [] });
    expect(within(fila("AAA1")).queryByRole("button", { name: "Confirmar" })).toBeNull();
    expect(within(fila("BBB2")).queryByRole("button", { name: "Revertir" })).toBeNull();
    expect(within(fila("BBB2")).getByRole("button", { name: "Ver comprobante" })).toBeTruthy();
  });

  it("revertir y reimputar piden otro permiso que confirmar y rechazar", () => {
    pintar([pago("AAA1", "informado"), pago("BBB2", "confirmado")], {
      acciones: ["confirmar_pago_informado"],
    });
    expect(within(fila("AAA1")).getByRole("button", { name: "Confirmar" })).toBeTruthy();
    expect(within(fila("BBB2")).queryByRole("button", { name: "Revertir" })).toBeNull();
    expect(within(fila("BBB2")).queryByRole("button", { name: "Reimputar" })).toBeNull();
  });

  it("confirmar pide confirmación y manda el pedido sin cuerpo", async () => {
    const { resolver } = pintar([pago("AAA1", "informado")]);
    await userEvent.click(within(fila("AAA1")).getByRole("button", { name: "Confirmar" }));
    const dialogo = screen.getByRole("dialog");
    expect(resolver).not.toHaveBeenCalled();
    await userEvent.click(within(dialogo).getByRole("button", { name: "Confirmar" }));
    await waitFor(() =>
      expect(resolver).toHaveBeenCalledWith("p-AAA1", { accion: "confirmacion" }),
    );
    expect(await screen.findByText("Pago confirmado.")).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("rechazar exige motivo: el botón está apagado hasta escribirlo", async () => {
    const { resolver } = pintar([pago("AAA1", "informado")]);
    await userEvent.click(within(fila("AAA1")).getByRole("button", { name: "Rechazar" }));
    const dialogo = screen.getByRole("dialog");
    const boton = within(dialogo).getByRole("button", { name: "Rechazar" });
    expect((boton as HTMLButtonElement).disabled).toBe(true);
    await userEvent.type(within(dialogo).getByLabelText("Motivo"), "No coincide");
    expect((boton as HTMLButtonElement).disabled).toBe(false);
    await userEvent.click(boton);
    await waitFor(() =>
      expect(resolver).toHaveBeenCalledWith("p-AAA1", { accion: "rechazo", motivo: "No coincide" }),
    );
  });

  it("reimputar ofrece las otras unidades (no la del pago) y manda desde y hacia", async () => {
    const { resolver } = pintar([pago("BBB2", "confirmado")]);
    await userEvent.click(within(fila("BBB2")).getByRole("button", { name: "Reimputar" }));
    const dialogo = screen.getByRole("dialog");
    const destino = within(dialogo).getByLabelText("Unidad de destino") as HTMLSelectElement;
    expect([...destino.options].map((o) => o.textContent)).toEqual([
      "Elegí una unidad",
      "1A",
      "2A",
    ]);
    await userEvent.selectOptions(destino, "2A");
    await userEvent.type(within(dialogo).getByLabelText("Motivo"), "Era de 2A");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Reimputar" }));
    await waitFor(() =>
      expect(resolver).toHaveBeenCalledWith("p-BBB2", {
        accion: "reimputacion",
        motivo: "Era de 2A",
        desdeUnidadId: "u-2b",
        haciaUnidadId: "u-2a",
      }),
    );
  });

  it("un pago reimputado dice dónde está ahora y reimputa desde ahí (H-026)", async () => {
    const { resolver } = pintar([
      pago("CCC3", "confirmado", { id: "u-1a", nombre: "1A" }, { id: "u-2a", nombre: "2A" }),
    ]);
    expect(fila("CCC3").textContent).toContain("Ahora en 2A");
    await userEvent.click(within(fila("CCC3")).getByRole("button", { name: "Reimputar" }));
    const dialogo = screen.getByRole("dialog");
    const destino = within(dialogo).getByLabelText("Unidad de destino") as HTMLSelectElement;
    expect([...destino.options].map((o) => o.textContent)).toEqual([
      "Elegí una unidad",
      "1A",
      "2B",
    ]);
    await userEvent.selectOptions(destino, "2B");
    await userEvent.type(within(dialogo).getByLabelText("Motivo"), "Era de 2B");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Reimputar" }));
    await waitFor(() =>
      expect(resolver).toHaveBeenCalledWith("p-CCC3", {
        accion: "reimputacion",
        motivo: "Era de 2B",
        desdeUnidadId: "u-2a",
        haciaUnidadId: "u-2b",
      }),
    );
  });

  it("un pago que no se reimputó no dice 'Ahora en'", () => {
    pintar([pago("BBB2", "confirmado")]);
    expect(fila("BBB2").textContent).not.toContain("Ahora en");
  });

  it("la bandeja ofrece Informar un pago, que lleva a /pagos/informar (H-026)", () => {
    pintar([]);
    expect(screen.getByRole("link", { name: "Informar un pago" }).getAttribute("href")).toBe(
      "/edificios/e1/pagos/informar",
    );
  });

  it("si la acción falla, el diálogo queda abierto con el error dicho", async () => {
    pintar([pago("BBB2", "confirmado")], {
      resolver: async () => ({ error: "El pago cambió de estado. Volvé a cargar la pantalla." }),
    });
    await userEvent.click(within(fila("BBB2")).getByRole("button", { name: "Revertir" }));
    const dialogo = screen.getByRole("dialog");
    await userEvent.type(within(dialogo).getByLabelText("Motivo"), "Cheque rechazado");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Revertir" }));
    expect(await within(dialogo).findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("dialog")).toBeTruthy();
  });

  it("si no se pudo abrir el comprobante lo dice", async () => {
    const abrir = vi.spyOn(window, "open").mockReturnValue(null);
    const { verComprobante } = pintar([pago("AAA1", "informado")]);
    await userEvent.click(within(fila("AAA1")).getByRole("button", { name: "Ver comprobante" }));
    await waitFor(() => expect(verComprobante).toHaveBeenCalledWith("p-AAA1"));
    expect(await screen.findByText("No pudimos preparar el comprobante.")).toBeTruthy();
    abrir.mockRestore();
  });
});
