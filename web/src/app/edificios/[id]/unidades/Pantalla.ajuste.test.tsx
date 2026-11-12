/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SesionDePantalla, type SesionVisible } from "../../../../componentes/SesionDePantalla";
import { PantallaPadron } from "./Pantalla";

afterEach(cleanup);

/** Un elemento que tiene que estar: falla por `expect`, no por la excepción de `getBy`. */
function ahi(elemento: HTMLElement | null): HTMLElement {
  expect(elemento).not.toBeNull();
  return elemento as HTMLElement;
}
const accion = async () => null;

function sesion(acciones: string[]): SesionVisible {
  return {
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
  };
}

function padron(estadoMigracion?: string) {
  return (
    <PantallaPadron
      id="1"
      nombreEdificio="Edificio"
      pisosDelEdificio={4}
      subsuelosDelEdificio={1}
      estadoMigracion={estadoMigracion}
      unidades={[
        {
          id: "u1",
          complejo_id: "1",
          identificador: "1A",
          tipo: "departamento",
          piso: "1",
          coeficiente: "1.000000",
          superficie_m2: "60.00",
        },
      ]}
      informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
      accionCrear={accion}
      accionEditar={accion}
      vecinosPorUnidad={new Map()}
    />
  );
}

it("con la migración confirmada y el permiso, cada unidad ofrece ajustar su saldo inicial", () => {
  render(
    <SesionDePantalla value={sesion(["ajustar_saldo_inicial"])}>
      {padron("confirmada")}
    </SesionDePantalla>,
  );
  const enlace = ahi(screen.queryByRole("link", { name: "Ajustar saldo inicial de 1A" }));
  expect(enlace.getAttribute("href")).toBe("/edificios/1/unidades/u1/ajuste-de-saldo-inicial");
});

it.each([
  ["pendiente", ["ajustar_saldo_inicial"]],
  ["sin_saldos_previos", ["ajustar_saldo_inicial"]],
  [undefined, ["ajustar_saldo_inicial"]],
  ["confirmada", ["configurar_padron"]],
])("con la migración %s y las acciones %j no ofrece ajustar", (estado, acciones) => {
  render(<SesionDePantalla value={sesion(acciones)}>{padron(estado)}</SesionDePantalla>);
  expect(ahi(screen.queryByText("1A"))).toBeTruthy();
  expect(screen.queryByRole("link", { name: /Ajustar saldo inicial/ })).toBeNull();
});
