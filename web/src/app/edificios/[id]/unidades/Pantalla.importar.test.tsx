/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SesionDePantalla, type SesionVisible } from "../../../../componentes/SesionDePantalla";
import { PantallaPadron } from "./Pantalla";

afterEach(cleanup);

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

function padron(acciones: string[], estadoMigracion?: string | null) {
  render(
    <SesionDePantalla value={sesion(acciones)}>
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        estadoMigracion={estadoMigracion ?? undefined}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "1.000000", estado: "ok" }}
        accionCrear={accion}
        accionEditar={accion}
        vecinosPorUnidad={new Map()}
      />
    </SesionDePantalla>,
  );
  return screen.queryByRole("link", { name: "Importar desde Excel" });
}

it("con la migración pendiente y el permiso, el padrón ofrece importar desde Excel", () => {
  const link = padron(["importar_padron_y_saldos", "configurar_padron"], "pendiente");
  expect(link).not.toBeNull();
  expect(link?.getAttribute("href")).toBe("/edificios/1/importar");
});

it.each([
  ["sin el permiso de importar", ["configurar_padron"], "pendiente"],
  ["con la migración confirmada", ["importar_padron_y_saldos"], "confirmada"],
  ["sin saldos previos", ["importar_padron_y_saldos"], "sin_saldos_previos"],
  ["sin dato del resumen", ["importar_padron_y_saldos"], null],
])("no ofrece importar %s", (_caso, acciones, estado) => {
  expect(padron(acciones, estado)).toBeNull();
});
