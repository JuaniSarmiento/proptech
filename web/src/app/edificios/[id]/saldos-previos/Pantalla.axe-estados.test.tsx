/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaSaldosPrevios } from "./Pantalla";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";

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

// pulido-2 (3d), escenario "axe cubre más de un estado": ya confirmado y formulario con
// el error de la casilla sin tildar (el test de la pantalla sólo mide "pendiente").
afterEach(cleanup);

function accionNula() {
  return Promise.resolve(null);
}

describe("PantallaSaldosPrevios · axe por estado", () => {
  it("ya confirmado, sin violaciones", async () => {
    const { container } = render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="sin_saldos_previos"
        accionConfirmar={accionNula}
      />,
    );
    expect(screen.getByText("Confirmado: arranca sin saldos previos")).toBeTruthy();
    await sinViolaciones(container);
  });

  it("envío sin tildar la casilla (error en la casilla), sin violaciones", async () => {
    const { container } = render(
      <PantallaSaldosPrevios
        id="e1"
        nombreEdificio="Edificio API"
        estadoMigracion="pendiente"
        accionConfirmar={accionNula}
      />,
    );
    const formulario = screen.getByRole("form", { name: "Confirmar sin saldos previos" });
    formulario.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect((await screen.findAllByText(/Tildá la casilla/i)).length).toBeGreaterThan(0);
    await sinViolaciones(container);
  });
});
