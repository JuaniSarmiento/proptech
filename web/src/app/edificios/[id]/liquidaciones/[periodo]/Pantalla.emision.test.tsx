/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { EmisionRegistrada } from "../../../../../lib/api/liquidaciones";
import { PRELIQUIDACION } from "../../../../../lib/test/preliquidacion";
import { type EstadoEmision, PantallaPreliquidacion } from "./Pantalla";

afterEach(cleanup);

const PROPS = {
  id: "e1",
  nombreEdificio: "Torre Ficticia",
  periodoEnPalabras: "noviembre de 2026",
};

const TODAS = ["emitir_y_distribuir_liquidacion", "aceptar_alertas_bloqueantes"];

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

const EMITIDA: EmisionRegistrada = {
  liquidacion_id: "l1",
  emision_id: "x",
  periodo: "2026-11-01",
  vencimiento: "2026-11-10",
  huella: "a".repeat(64),
  obligaciones: [],
};

const CON_BLOQUEANTE: typeof PRELIQUIDACION = {
  ...PRELIQUIDACION,
  controles: [
    { codigo: "gastos_en_revision", nivel: "bloqueante", mensaje: "Hay 1 factura", detalle: {} },
    { codigo: "gastos_sin_ia", nivel: "advertencia", mensaje: "Hay 2 sin cargar", detalle: {} },
  ],
};

const CON_DURO: typeof PRELIQUIDACION = {
  ...PRELIQUIDACION,
  controles: [{ codigo: "bloque_negativo", nivel: "duro", mensaje: "Un duro", detalle: {} }],
};

const accion = (estado: EstadoEmision = null) =>
  vi.fn(async (_previo: EstadoEmision, _formulario: FormData) => estado);

describe("PantallaPreliquidacion · emitir (H-013)", () => {
  it("sin la acción o sin el permiso no hay botón de emitir", () => {
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} />);
    expect(screen.queryByRole("button", { name: "Emitir liquidación" })).toBeNull();
    cleanup();
    render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} accionEmitir={accion()} />,
      ["aceptar_alertas_bloqueantes"],
    );
    expect(screen.queryByRole("button", { name: "Emitir liquidación" })).toBeNull();
  });

  it("con un duro activo el botón está deshabilitado", () => {
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={CON_DURO} accionEmitir={accion()} />);
    expect(
      (screen.getByRole("button", { name: "Emitir liquidación" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("la confirmación dice que no se deshace, con el total, y no ofrece casillas sin bloqueantes", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} accionEmitir={accion()} />,
    );
    await usuario.click(screen.getByRole("button", { name: "Emitir liquidación" }));
    const dialogo = screen.getByRole("dialog");
    expect(dialogo.textContent).toMatch(/no se deshace/i);
    expect(dialogo.textContent).toContain("191.500,00");
    expect(within(dialogo).queryAllByRole("checkbox", { name: /Acepto/ })).toHaveLength(0);
    expect(
      (within(dialogo).getByRole("button", { name: "Confirmar" }) as HTMLButtonElement).disabled,
    ).toBe(false);
  });

  it("un bloqueante pide su casilla antes de confirmar; la advertencia no tiene casilla", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={CON_BLOQUEANTE} accionEmitir={accion()} />,
    );
    await usuario.click(screen.getByRole("button", { name: "Emitir liquidación" }));
    const dialogo = screen.getByRole("dialog");
    const confirmar = within(dialogo).getByRole("button", {
      name: "Confirmar",
    }) as HTMLButtonElement;
    expect(confirmar.disabled).toBe(true);
    expect(within(dialogo).getAllByRole("checkbox", { name: /Acepto/ })).toHaveLength(1);
    expect(within(dialogo).queryByRole("checkbox", { name: /Hay 2 sin cargar/ })).toBeNull();
    await usuario.click(within(dialogo).getByRole("checkbox", { name: /Hay 1 factura/ }));
    expect(confirmar.disabled).toBe(false);
  });

  it("sin el permiso de aceptar, la casilla queda deshabilitada y no se puede confirmar", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={CON_BLOQUEANTE} accionEmitir={accion()} />,
      ["emitir_y_distribuir_liquidacion"],
    );
    await usuario.click(screen.getByRole("button", { name: "Emitir liquidación" }));
    const dialogo = screen.getByRole("dialog");
    expect(
      (within(dialogo).getByRole("checkbox", { name: /Hay 1 factura/ }) as HTMLInputElement)
        .disabled,
    ).toBe(true);
    expect(
      (within(dialogo).getByRole("button", { name: "Confirmar" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(dialogo.textContent).toMatch(/no tenés permiso para aceptar alertas/i);
  });

  it("correr el vencimiento muestra la fecha y el motivo", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} accionEmitir={accion()} />,
    );
    await usuario.click(screen.getByRole("button", { name: "Emitir liquidación" }));
    const dialogo = screen.getByRole("dialog");
    expect(within(dialogo).queryByLabelText("Nuevo vencimiento")).toBeNull();
    await usuario.click(within(dialogo).getByRole("checkbox", { name: "Correr el vencimiento" }));
    expect(within(dialogo).getByLabelText("Nuevo vencimiento")).toBeTruthy();
    expect(within(dialogo).getByLabelText("Motivo")).toBeTruthy();
  });

  it("al emitir sale la región 'Liquidación emitida' con el período y el total, y el botón se va", async () => {
    const usuario = userEvent.setup();
    const emitir = accion({ emitida: EMITIDA });
    render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} accionEmitir={emitir} />,
    );
    await usuario.click(screen.getByRole("button", { name: "Emitir liquidación" }));
    await usuario.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmar" }),
    );
    const region = await screen.findByRole("region", { name: "Liquidación emitida" });
    expect(region.textContent).toContain("noviembre de 2026");
    expect(region.textContent).toContain("191.500,00");
    expect(screen.queryByRole("button", { name: "Emitir liquidación" })).toBeNull();
    const enviado = emitir.mock.calls[0]?.[1] as FormData;
    expect(enviado.get("huella")).toBe("a".repeat(64));
    expect(String(enviado.get("emision_id"))).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("un error de la acción se dice en la confirmación y no la cierra", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPreliquidacion
        {...PROPS}
        preliquidacion={PRELIQUIDACION}
        accionEmitir={accion({ error: "La preliquidación cambió" })}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Emitir liquidación" }));
    await usuario.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Confirmar" }),
    );
    const alerta = await screen.findByText("La preliquidación cambió");
    expect(alerta.getAttribute("role")).toBe("alert");
    expect(screen.getByRole("dialog")).toBeTruthy();
  });
});
