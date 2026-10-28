/**
 * @vitest-environment jsdom
 */
import { act, cleanup, fireEvent, render as renderOriginal, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type { VersionDelHistorial } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaConfiguracion } from "./Pantalla";

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
                todos_los_edificios: ["crear_version_de_configuracion"],
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

// pulido-2 (3d), escenario "axe cubre más de un estado": sin configuración vigente,
// panel abierto y panel con un error de campo (el test de la pantalla sólo mide el feliz).
afterEach(cleanup);

const V1: VersionDelHistorial = {
  id: "v1",
  complejo_id: "e1",
  vigente_desde: "2026-10-19",
  tasa_mensual: "3.00",
  dias_de_gracia: 0,
  forma_de_calculo: "proporcional_por_dia",
  porcentaje_fondo: "0.00",
  dia_de_vencimiento: 10,
  modalidad_de_vencimiento: "unico",
  dia_segundo_vencimiento: null,
  recargo_segundo_vencimiento: null,
  umbral_saldo_chico: "500.00",
  autor_id: "a1",
  autor_nombre: "Alberto",
  creada_en: "2026-10-19T22:06:28Z",
};

function accionNula() {
  return Promise.resolve(null);
}

function accionConError() {
  return Promise.resolve({
    erroresPorCampo: { tasa_mensual: "Este valor no es válido." },
    erroresDesconocidos: [],
  });
}

function pantalla(
  vigente: VersionDelHistorial | null,
  accionCrear: typeof accionNula | typeof accionConError,
) {
  return (
    <PantallaConfiguracion
      id="e1"
      nombreEdificio="Edificio API"
      vigente={vigente}
      historial={vigente ? [vigente] : []}
      accionCrear={accionCrear}
    />
  );
}

describe("PantallaConfiguracion · axe por estado", () => {
  it("sin configuración vigente, sin violaciones", async () => {
    const { container } = render(pantalla(null, accionNula));
    expect(screen.getByText("Todavía no configuraste la tasa ni el vencimiento.")).toBeTruthy();
    await sinViolaciones(container);
  });

  it("panel de cambio abierto, sin violaciones", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla(V1, accionNula));
    await usuario.click(screen.getByRole("button", { name: "Cambiar configuración" }));
    expect(screen.getByLabelText("Rige desde")).toBeTruthy();
    await sinViolaciones(container);
  });

  it("panel con un error de campo, sin violaciones", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla(V1, accionConError));
    await usuario.click(screen.getByRole("button", { name: "Cambiar configuración" }));
    const tasa = screen.getByLabelText("Tasa mensual");
    await act(async () => {
      fireEvent.submit(tasa.closest("form") as HTMLFormElement);
    });
    expect(tasa.getAttribute("aria-invalid")).toBe("true");
    await sinViolaciones(container);
  });
});
