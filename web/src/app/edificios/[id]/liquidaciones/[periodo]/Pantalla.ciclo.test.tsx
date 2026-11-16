/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { LiquidacionDeLaLista } from "../../../../../lib/api/liquidaciones";
import { type EstadoCiclo, PantallaLiquidacionEmitida } from "./Pantalla";

afterEach(cleanup);

const PROPS = {
  id: "e1",
  nombreEdificio: "Torre Ficticia",
  periodoEnPalabras: "noviembre de 2026",
};

const TODAS = ["emitir_y_distribuir_liquidacion", "anular_liquidacion"];

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

const LISTA = (estado: LiquidacionDeLaLista["estado"]): LiquidacionDeLaLista => ({
  liquidacion_id: "l1",
  periodo: "2026-11-01",
  estado,
  total: "191500.00",
  emitida_en: "2026-11-02T15:00:00+00:00",
});

const accion = (estado: EstadoCiclo = null) =>
  vi.fn(async (_previo: EstadoCiclo, _formulario: FormData) => estado);

describe("PantallaLiquidacionEmitida (H-014)", () => {
  it("una emitida dice su estado en texto y su total, y ofrece distribuir y anular", () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("emitida")}
        accionDistribuir={accion()}
        accionAnular={accion()}
      />,
    );
    expect(screen.getByText("Emitida")).toBeTruthy();
    expect(screen.getByText("191.500,00")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Distribuir" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Anular" })).toBeTruthy();
  });

  it("una distribuida no ofrece ninguna de las dos", () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("distribuida")}
        accionDistribuir={accion()}
        accionAnular={accion()}
      />,
    );
    expect(screen.getByText("Distribuida")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Distribuir" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Anular" })).toBeNull();
  });

  it("cada botón aparece sólo con su permiso", () => {
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("emitida")}
        accionDistribuir={accion()}
        accionAnular={accion()}
      />,
      ["emitir_y_distribuir_liquidacion"],
    );
    expect(screen.getByRole("button", { name: "Distribuir" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Anular" })).toBeNull();
  });

  it("distribuir pide confirmación y manda el pedido al confirmar", async () => {
    const usuario = userEvent.setup();
    const distribuir = accion();
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("emitida")}
        accionDistribuir={distribuir}
        accionAnular={accion()}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Distribuir" }));
    const dialogo = screen.getByRole("dialog");
    expect(dialogo.textContent).toMatch(/ya no se puede anular/);
    expect(distribuir).not.toHaveBeenCalled();
    await usuario.click(within(dialogo).getByRole("button", { name: "Confirmar" }));
    expect(distribuir).toHaveBeenCalledTimes(1);
  });

  it("anular no deja confirmar sin motivo y lo manda con él", async () => {
    const usuario = userEvent.setup();
    const anular = accion();
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("emitida")}
        accionDistribuir={accion()}
        accionAnular={anular}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Anular" }));
    const dialogo = screen.getByRole("dialog");
    const confirmar = within(dialogo).getByRole("button", {
      name: "Confirmar",
    }) as HTMLButtonElement;
    expect(confirmar.disabled).toBe(true);
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "   ");
    expect(confirmar.disabled).toBe(true);
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "Se cargó mal una factura");
    expect(confirmar.disabled).toBe(false);
    await usuario.click(confirmar);
    expect(anular).toHaveBeenCalledTimes(1);
    const formulario = anular.mock.calls[0]?.[1];
    expect(String(formulario?.get("motivo")).trim()).toBe("Se cargó mal una factura");
  });

  it("cancelar cierra sin mandar nada", async () => {
    const usuario = userEvent.setup();
    const anular = accion();
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("emitida")}
        accionDistribuir={accion()}
        accionAnular={anular}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Anular" }));
    await usuario.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }),
    );
    expect(anular).not.toHaveBeenCalled();
  });

  it("un error de la acción se dice en el panel", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaLiquidacionEmitida
        {...PROPS}
        liquidacion={LISTA("emitida")}
        accionDistribuir={accion({ error: "Esta liquidación ya está distribuida." })}
        accionAnular={accion()}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Distribuir" }));
    await usuario.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmar" }),
    );
    expect((await screen.findByRole("alert")).textContent).toMatch(/ya está distribuida/);
  });
});
