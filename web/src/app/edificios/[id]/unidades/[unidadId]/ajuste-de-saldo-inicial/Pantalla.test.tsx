/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../../../componentes/SesionDePantalla";
import { sinViolaciones } from "../../../../../../lib/test/accesibilidad";
import { type EstadoAjuste, PantallaAjuste } from "./Pantalla";

afterEach(cleanup);

/** Un elemento que tiene que estar: falla por `expect`, no por la excepción de `getBy`. */
function ahi(elemento: HTMLElement | null): HTMLElement {
  expect(elemento).not.toBeNull();
  return elemento as HTMLElement;
}

function render(ui: ReactElement) {
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
              acciones: {
                administracion: [],
                todos_los_edificios: ["ajustar_saldo_inicial"],
                por_edificio: {},
              },
            },
          ],
        },
      }}
    >
      {ui}
    </SesionDePantalla>,
  );
}

const AJUSTADO = {
  ajuste_id: "a",
  operacion_id: "o",
  obligacion_id: "ob",
  cuenta_id: "c",
  unidad_id: "u1",
  importe: "5000.00",
  componente: "ordinaria",
  periodo: "2026-10-01",
  vencimiento: "2026-11-12",
  motivo: "Faltó la expensa extraordinaria de julio",
  registrado_por: "p",
  registrado_en: "2026-11-12T15:00:00+00:00",
};

function pantalla(
  accion: (e: EstadoAjuste, f: FormData) => Promise<EstadoAjuste>,
  estado = "confirmada",
) {
  return (
    <PantallaAjuste
      id="1"
      nombreEdificio="Edificio"
      identificadorDeUnidad="1A"
      estadoMigracion={estado}
      accionAjustar={accion}
    />
  );
}

async function llenar(usuario: ReturnType<typeof userEvent.setup>) {
  await usuario.type(ahi(screen.queryByLabelText("Importe")), "5000,00");
  await usuario.type(ahi(screen.queryByLabelText("Motivo")), AJUSTADO.motivo);
}

describe("pantalla del ajuste de saldo inicial", () => {
  it("dice qué unidad se ajusta y tiene los tres campos con sus conceptos", () => {
    render(pantalla(vi.fn()));
    expect(ahi(screen.queryByRole("heading", { name: "Ajustar saldo inicial" }))).toBeTruthy();
    expect(ahi(screen.queryByText(/1A/))).toBeTruthy();
    expect(ahi(screen.queryByLabelText("Importe"))).toBeTruthy();
    const concepto = ahi(screen.queryByLabelText("Concepto")) as HTMLSelectElement;
    expect([...concepto.options].map((o) => o.text)).toEqual([
      "Ordinaria",
      "Fondo de reserva",
      "Extraordinaria",
    ]);
    expect(ahi(screen.queryByLabelText("Motivo"))).toBeTruthy();
    expect(ahi(screen.queryByRole("button", { name: "Registrar ajuste" }))).toBeTruthy();
  });

  it("registrar sin llenar no abre la confirmación y marca los campos", async () => {
    const accion = vi.fn();
    render(pantalla(accion));
    await userEvent.setup().click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(ahi(screen.queryByLabelText("Importe")).getAttribute("aria-invalid")).toBe("true");
    expect(ahi(screen.queryByLabelText("Motivo")).getAttribute("aria-invalid")).toBe("true");
    expect(accion).not.toHaveBeenCalled();
  });

  it("registrar pide confirmación que dice que no se deshace y no manda nada hasta confirmar", async () => {
    const accion = vi.fn().mockResolvedValue(null);
    const usuario = userEvent.setup();
    render(pantalla(accion));
    await llenar(usuario);
    await usuario.click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
    const dialogo = ahi(screen.queryByRole("dialog"));
    expect(dialogo.textContent).toContain("no se deshace");
    expect(accion).not.toHaveBeenCalled();
    await usuario.click(ahi(within(dialogo).queryByRole("button", { name: "Cancelar" })));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(accion).not.toHaveBeenCalled();
  });

  it("al confirmar manda importe, concepto, motivo y una operación; muestra el ajuste registrado", async () => {
    const accion = vi.fn().mockResolvedValue({ ajustado: AJUSTADO });
    const usuario = userEvent.setup();
    render(pantalla(accion));
    await llenar(usuario);
    await usuario.click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
    await usuario.click(
      ahi(
        within(ahi(screen.queryByRole("dialog"))).queryByRole("button", {
          name: /^Confirmar$/,
        }),
      ),
    );
    const datos = accion.mock.calls[0]?.[1] as FormData;
    expect(datos.get("importe")).toBe("5000,00");
    expect(datos.get("componente")).toBe("ordinaria");
    expect(datos.get("motivo")).toBe(AJUSTADO.motivo);
    expect(String(datos.get("operacion_id"))).toMatch(/^[0-9a-f-]{36}$/);
    const region = await screen.findByRole("region", { name: "Ajuste registrado" });
    expect(region.textContent).toContain("5.000,00");
    expect(region.textContent).toContain(AJUSTADO.motivo);
    expect(screen.queryByRole("button", { name: "Registrar ajuste" })).toBeNull();
  });

  it("un reintento con los mismos datos reusa la operación; con otros datos usa otra", async () => {
    const accion = vi
      .fn()
      .mockResolvedValue({ error: "No pudimos registrar el ajuste. Probá de nuevo." });
    const usuario = userEvent.setup();
    render(pantalla(accion));
    await llenar(usuario);
    const confirmar = async () => {
      await usuario.click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
      await usuario.click(
        ahi(
          within(ahi(screen.queryByRole("dialog"))).queryByRole("button", {
            name: /^Confirmar$/,
          }),
        ),
      );
    };
    await confirmar();
    await confirmar();
    await usuario.type(ahi(screen.queryByLabelText("Motivo")), " otra vez");
    await confirmar();
    const op = (n: number) => {
      const llamada = accion.mock.calls[n] ?? [];
      return (llamada[1] as FormData).get("operacion_id");
    };
    expect(op(0)).toBe(op(1));
    expect(op(2)).not.toBe(op(0));
  });

  it("un 403 muestra el aviso, cierra la confirmación y no muestra el ajuste", async () => {
    const accion = vi
      .fn()
      .mockResolvedValue({ error: "No podés ajustar saldos en este edificio." });
    const usuario = userEvent.setup();
    render(pantalla(accion));
    await llenar(usuario);
    await usuario.click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
    await usuario.click(
      ahi(
        within(ahi(screen.queryByRole("dialog"))).queryByRole("button", {
          name: /^Confirmar$/,
        }),
      ),
    );
    expect((await screen.findByRole("alert")).textContent).toContain(
      "No podés ajustar saldos en este edificio.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("region", { name: "Ajuste registrado" })).toBeNull();
    // Lo cargado no se pierde.
    expect((ahi(screen.queryByLabelText("Importe")) as HTMLInputElement).value).toBe("5000,00");
  });

  it("con la migración sin confirmar no hay formulario y se manda a importar", () => {
    render(pantalla(vi.fn(), "pendiente"));
    expect(screen.queryByRole("button", { name: "Registrar ajuste" })).toBeNull();
    expect(ahi(screen.queryByText(/todavía no están confirmados/i))).toBeTruthy();
  });

  it("no tiene violaciones de accesibilidad: formulario, error y confirmación", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla(vi.fn().mockResolvedValue(null)));
    await sinViolaciones(container);
    await usuario.click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
    await sinViolaciones(container);
    await llenar(usuario);
    await usuario.click(ahi(screen.queryByRole("button", { name: "Registrar ajuste" })));
    await sinViolaciones(container);
  });
});
