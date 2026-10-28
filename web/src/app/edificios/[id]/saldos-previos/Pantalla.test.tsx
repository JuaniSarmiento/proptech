/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaSaldosPrevios } from "./Pantalla";

afterEach(cleanup);
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
                todos_los_edificios: ["confirmar_sin_saldos_previos"],
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

function accionNula() {
  return Promise.resolve(null);
}

describe("PantallaSaldosPrevios", () => {
  it("el envío sin tildar la casilla no llama a la acción y el error queda en la casilla", async () => {
    const accionConfirmar = vi.fn().mockResolvedValue(null);
    render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="pendiente"
        accionConfirmar={accionConfirmar}
      />,
    );
    const boton = screen.getByRole("button", { name: "Confirmar" }) as HTMLButtonElement;
    expect(boton.disabled).toBe(true);

    // Envío directo (sin pasar por el botón deshabilitado): simula un
    // `requestSubmit()` o un Enter en un formulario sin botón deshabilitado.
    const formulario = screen.getByRole("form", { name: "Confirmar sin saldos previos" });
    formulario.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));

    expect(accionConfirmar).not.toHaveBeenCalled();
    expect((await screen.findAllByText(/Tildá la casilla/i)).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/Entiendo que el edificio arranca sin deudas anteriores/)).toBe(
      document.activeElement,
    );
  });

  it("tildar la casilla habilita el botón y confirmar llama a la acción", async () => {
    const accionConfirmar = vi.fn().mockResolvedValue({
      erroresPorCampo: {},
      erroresDesconocidos: [],
      ok: true,
    });
    const usuario = userEvent.setup();
    render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="pendiente"
        accionConfirmar={accionConfirmar}
      />,
    );
    await usuario.click(
      screen.getByLabelText(/Entiendo que el edificio arranca sin deudas anteriores/),
    );
    expect((screen.getByRole("button", { name: "Confirmar" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
    await usuario.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(accionConfirmar).toHaveBeenCalledTimes(1);
  });

  it('"no se puede deshacer" está explícito en la pantalla', () => {
    render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="pendiente"
        accionConfirmar={accionNula}
      />,
    );
    expect(screen.getByText(/no se puede deshacer/i)).toBeTruthy();
  });

  it("con el estado ya confirmado muestra el estado y no el formulario", () => {
    render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="sin_saldos_previos"
        accionConfirmar={accionNula}
      />,
    );
    expect(screen.getByText("Confirmado: arranca sin saldos previos")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Confirmar" })).toBeNull();
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="pendiente"
        accionConfirmar={accionNula}
      />,
    );
    await sinViolaciones(container);
  });
});
