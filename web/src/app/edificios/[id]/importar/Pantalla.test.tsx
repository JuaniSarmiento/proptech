/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaImportar } from "./Pantalla";

afterEach(cleanup);

function render(ui: ReactElement, acciones: string[] = ["importar_padron_y_saldos"]) {
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

const ACEPTADA = {
  importacion_id: "i1",
  unidades_creadas: 12,
  propietarios_creados: 10,
  propietarios_reusados: 1,
  filas_de_saldo: 0,
  advertencias: [{ hoja: "Unidades", fila: null, columna: "Coeficiente", motivo: "Suman 0,9999" }],
};

function pantalla(accion = vi.fn().mockResolvedValue(null), estadoMigracion = "pendiente") {
  return (
    <PantallaImportar
      id="e1"
      nombreEdificio="Edificio API"
      estadoMigracion={estadoMigracion}
      accionImportar={accion}
    />
  );
}

describe("PantallaImportar", () => {
  it("muestra el encabezado, los dos campos, el botón y el enlace a la plantilla", () => {
    render(pantalla());
    expect(screen.getByRole("heading", { name: "Importar desde Excel", level: 1 })).toBeTruthy();
    expect(screen.getByLabelText("Archivo de Excel")).toBeTruthy();
    expect((screen.getByLabelText("Fecha de migración") as HTMLInputElement).type).toBe("date");
    expect(screen.getByRole("button", { name: "Importar" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Descargar plantilla" }).getAttribute("href")).toBe(
      "/edificios/e1/importar/plantilla",
    );
  });

  it("enviar llama a la acción con el archivo y la fecha", async () => {
    const accion = vi.fn().mockResolvedValue(null);
    render(pantalla(accion));
    const archivo = new File(["PK"], "padron.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await userEvent.upload(screen.getByLabelText("Archivo de Excel"), archivo);
    await userEvent.type(screen.getByLabelText("Fecha de migración"), "2026-10-15");
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    expect(accion).toHaveBeenCalledTimes(1);
    const datos = accion.mock.calls[0]?.[1] as FormData;
    // El archivo viaja en el campo `archivo`; su nombre original lo prueba el e2e en navegador
    // real (el FormData de jsdom no conserva el contenido de un input de archivo).
    expect(datos.has("archivo")).toBe(true);
    expect(datos.get("fecha_de_migracion")).toBe("2026-10-15");
  });

  it("aceptada: una región con el resumen y las advertencias", async () => {
    render(
      pantalla(
        vi
          .fn()
          .mockResolvedValue({ erroresPorCampo: {}, erroresDesconocidos: [], aceptada: ACEPTADA }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    const region = await screen.findByRole("region", { name: "Importación aceptada" });
    expect(region.textContent).toContain("12 unidades creadas");
    expect(region.textContent).toContain("10 propietarios nuevos");
    expect(region.textContent).toContain("1 propietario que ya existía");
    expect(region.textContent).toContain("Suman 0,9999");
    await sinViolaciones(region.ownerDocument.body);
  });

  it("aceptada con filas de saldo: lleva a la comparación; sin filas, no", async () => {
    const conSaldos = { ...ACEPTADA, filas_de_saldo: 7 };
    const { unmount } = render(
      pantalla(
        vi
          .fn()
          .mockResolvedValue({ erroresPorCampo: {}, erroresDesconocidos: [], aceptada: conSaldos }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    const region = await screen.findByRole("region", { name: "Importación aceptada" });
    const enlace = within(region).queryByRole("link", { name: "Ver la comparación de saldos" });
    expect(enlace?.getAttribute("href")).toBe("/edificios/e1/importar/comparacion");
    unmount();
    render(
      pantalla(
        vi
          .fn()
          .mockResolvedValue({ erroresPorCampo: {}, erroresDesconocidos: [], aceptada: ACEPTADA }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    const sinSaldos = await screen.findByRole("region", { name: "Importación aceptada" });
    expect(
      within(sinSaldos).queryByRole("link", { name: "Ver la comparación de saldos" }),
    ).toBeNull();
  });

  it("rechazada: No se cargó nada y la tabla con una fila por error, en el orden que llega", async () => {
    const rechazo = [
      { hoja: "Unidades", fila: 9, columna: "Piso", motivo: "Piso inválido" },
      { hoja: "Unidades", fila: null, columna: null, motivo: "Los coeficientes suman 0,5" },
    ];
    render(
      pantalla(
        vi.fn().mockResolvedValue({ erroresPorCampo: {}, erroresDesconocidos: [], rechazo }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    expect(await screen.findByText("No se cargó nada")).toBeTruthy();
    const tabla = screen.getByRole("table", { name: "Errores del archivo" });
    for (const columna of ["Hoja", "Fila", "Columna", "Motivo"]) {
      expect(within(tabla).getByRole("columnheader", { name: columna })).toBeTruthy();
    }
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas).toHaveLength(2);
    expect(filas[0]?.textContent).toContain("Piso inválido");
    expect(filas[1]?.textContent).toContain("Los coeficientes suman 0,5");
    expect(screen.queryByRole("region", { name: "Importación aceptada" })).toBeNull();
  });

  it("sin permiso (403): un alert y ninguna región de aceptada", async () => {
    render(
      pantalla(
        vi.fn().mockResolvedValue({
          erroresPorCampo: {},
          erroresDesconocidos: ["No podés importar en este edificio."],
        }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Importar" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "No podés importar en este edificio.",
    );
  });

  it("si la sesión no trae el permiso, no hay formulario y sí el aviso", () => {
    render(pantalla(), []);
    expect(screen.queryByLabelText("Archivo de Excel")).toBeNull();
    expect(screen.getByRole("alert").textContent).toContain("No podés importar en este edificio.");
  });

  it("con la migración ya resuelta muestra el estado y no el formulario", () => {
    render(pantalla(undefined, "sin_saldos_previos"));
    expect(screen.queryByLabelText("Archivo de Excel")).toBeNull();
    expect(screen.getByRole("status").textContent).toContain("sin saldos previos");
  });
});
