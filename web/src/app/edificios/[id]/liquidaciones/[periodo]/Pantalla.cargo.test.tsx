/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { LiquidacionDeLaLista, UnidadLiquidada } from "../../../../../lib/api/liquidaciones";
import { type EstadoDelCargo, PantallaLiquidacionEmitida } from "./Pantalla";

afterEach(cleanup);

const PROPS = {
  id: "e1",
  nombreEdificio: "Torre Ficticia",
  periodoEnPalabras: "noviembre de 2026",
};

function render(ui: ReactElement, acciones: string[] = ["corregir_movimiento"]) {
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

const LIQUIDACION: LiquidacionDeLaLista = {
  liquidacion_id: "l1",
  periodo: "2026-11-01",
  estado: "emitida",
  total: "191500.00",
  emitida_en: "2026-11-02T15:00:00+00:00",
};

const unidad = (identificador: string, extra: Partial<UnidadLiquidada> = {}): UnidadLiquidada => ({
  unidad_id: `u-${identificador}`,
  identificador,
  ordinaria: "27000.00",
  fondo_de_reserva: "1350.00",
  extraordinaria: "15000.00",
  cargos_particulares: [],
  intereses: "0.00",
  saldo_anterior: "250.50",
  total: "43350.00",
  sin_obligacion: false,
  obligacion_id: `o-${identificador}`,
  ...extra,
});

const UNIDADES = [unidad("1A"), unidad("1B", { obligacion_id: null, sin_obligacion: true })];

const accion = (estado: EstadoDelCargo = null) =>
  vi.fn(async (_previo: EstadoDelCargo, _formulario: FormData) => estado);

describe("PantallaLiquidacionEmitida · lo que paga cada unidad y el cargo (H-017)", () => {
  it("muestra la tabla con lo guardado, el saldo anterior incluido", () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LIQUIDACION}
        unidades={UNIDADES}
        accionCargo={accion()}
      />,
    );
    const tabla = screen.getByRole("table", { name: "Lo que paga cada unidad" });
    const fila = within(tabla).getByRole("row", { name: /^1A/ });
    expect(fila.textContent).toContain("27.000,00");
    expect(fila.textContent).toContain("250,50");
    expect(fila.textContent).toContain("43.350,00");
    expect(within(tabla).getByRole("columnheader", { name: "Saldo anterior" })).toBeTruthy();
  });

  it("sin unidades leídas no hay tabla", () => {
    render(<PantallaLiquidacionEmitida {...PROPS} liquidacion={LIQUIDACION} unidades={null} />);
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("el botón sólo está en la unidad con obligación y con corregir_movimiento", () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LIQUIDACION}
        unidades={UNIDADES}
        accionCargo={accion()}
      />,
    );
    expect(screen.getByRole("button", { name: "Cargo cobrado de menos de 1A" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Cargo cobrado de menos de 1B" })).toBeNull();
  });

  it("sin el permiso no hay botón, pero la tabla sí", () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LIQUIDACION}
        unidades={UNIDADES}
        accionCargo={accion()}
      />,
      [],
    );
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Cargo cobrado de menos/ })).toBeNull();
  });

  it("el diálogo manda importe, concepto, motivo y la obligación de la unidad", async () => {
    const enviar = accion();
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LIQUIDACION}
        unidades={UNIDADES}
        accionCargo={enviar}
      />,
    );
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Cargo cobrado de menos de 1A" }));
    const dialogo = screen.getByRole("dialog", { name: "Cargo cobrado de menos de 1A" });
    const confirmar = within(dialogo).getByRole("button", { name: "Confirmar" });
    expect((confirmar as HTMLButtonElement).disabled).toBe(true);
    await usuario.type(within(dialogo).getByLabelText("Importe"), "1500,00");
    await usuario.selectOptions(within(dialogo).getByLabelText("Concepto"), "Fondo de reserva");
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "Faltó el portón");
    await usuario.click(confirmar);
    const datos = enviar.mock.calls[0]?.[1] as FormData;
    expect(Object.fromEntries(datos.entries())).toMatchObject({
      unidad_id: "u-1A",
      obligacion_origen_id: "o-1A",
      importe: "1500,00",
      componente: "fondo_de_reserva",
      motivo: "Faltó el portón",
    });
    expect(String(datos.get("operacion_id"))).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("un cargo registrado cierra el diálogo y lo dice", async () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LIQUIDACION}
        unidades={UNIDADES}
        accionCargo={accion({ hecho: { importe: "1500.00", motivo: "m" } })}
      />,
    );
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Cargo cobrado de menos de 1A" }));
    const dialogo = screen.getByRole("dialog");
    await usuario.type(within(dialogo).getByLabelText("Importe"), "1500,00");
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "m");
    await usuario.click(within(dialogo).getByRole("button", { name: "Confirmar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect((await screen.findByRole("status")).textContent).toContain("1.500,00");
  });

  it("un error de la acción queda dicho en el diálogo, que sigue abierto", async () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LIQUIDACION}
        unidades={UNIDADES}
        accionCargo={accion({ erroresPorCampo: { importe: "Poné un importe mayor que cero." } })}
      />,
    );
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Cargo cobrado de menos de 1A" }));
    const dialogo = screen.getByRole("dialog");
    await usuario.type(within(dialogo).getByLabelText("Importe"), "0");
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "m");
    await usuario.click(within(dialogo).getByRole("button", { name: "Confirmar" }));
    expect(
      within(screen.getByRole("dialog")).getByText("Poné un importe mayor que cero."),
    ).toBeTruthy();
  });
});
