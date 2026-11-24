/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type { FilaDeMorosidad, Morosidad } from "../../../../lib/api/morosidad";
import { PantallaMorosidad } from "./Pantalla";

afterEach(cleanup);

const EDIFICIO = "e1";

function render(ui: ReactElement, acciones: string[] = ["ver_morosidad", "exportar_morosidad"]) {
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

const fila = (unidad: string, extra: Partial<FilaDeMorosidad> = {}): FilaDeMorosidad => ({
  unidad_id: `id-${unidad}`,
  unidad,
  propietarios: ["Ana Prueba", "Beto Prueba"],
  etiqueta: "con_deuda_vencida",
  total_vencido: "40000.00",
  capital: "39000.00",
  intereses: "1000.00",
  liquidaciones_vencidas: 2,
  vencida_desde: "2026-11-10",
  dias: 8,
  ...extra,
});

function morosidad(extra: Partial<Morosidad> = {}): Morosidad {
  return {
    fecha: "2026-11-18",
    intereses_al: "2026-10-31",
    // A propósito un centavo distinto de la suma de las filas: la pantalla no suma.
    resumen: { unidades_con_deuda: 2, morosos_criticos: 1, total_vencido: "70000.01" },
    unidades: [fila("1A", { etiqueta: "moroso_critico", total_vencido: "30000.00" }), fila("1B")],
    ...extra,
  };
}

function pintar(m: Morosidad, acciones?: string[]) {
  render(<PantallaMorosidad id={EDIFICIO} nombreEdificio="Torre" morosidad={m} />, acciones);
}

describe("PantallaMorosidad (H-029)", () => {
  it("el resumen muestra el total de la API, no la suma de las filas", () => {
    pintar(morosidad());
    const resumen = screen.getByRole("region", { name: "Resumen de la morosidad" });
    expect(resumen.textContent).toContain("70.000,01");
    expect(resumen.textContent).not.toContain("70.000,00");
    expect(resumen.textContent).toContain("Unidades que deben");
    expect(resumen.textContent).toContain("Morosos críticos");
    expect(resumen.textContent).toContain("Intereses al 31/10/2026");
  });

  it("sin fecha de intereses dice que no hay intereses registrados", () => {
    pintar(morosidad({ intereses_al: null }));
    expect(screen.getByText("Sin intereses registrados")).toBeTruthy();
  });

  it("una fila por unidad en el orden de la API, con todos sus datos", () => {
    pintar(morosidad());
    const items = within(screen.getByRole("list", { name: "Unidades con deuda" })).getAllByRole(
      "listitem",
    );
    expect(items).toHaveLength(2);
    const primera = items[0]?.textContent ?? "";
    for (const t of [
      "1A",
      "Ana Prueba, Beto Prueba",
      "Moroso crítico",
      "30.000,00",
      "39.000,00",
      "1.000,00",
      "Desde el 10/11/2026 · 8 días",
    ]) {
      expect(primera).toContain(t);
    }
    expect(items[1]?.textContent).toContain("Con deuda vencida");
  });

  it("sin propietarios lo dice, y 1 día va en singular", () => {
    pintar(morosidad({ unidades: [fila("2A", { propietarios: [], dias: 1 })] }));
    expect(screen.getByText("Sin propietarios cargados")).toBeTruthy();
    expect(screen.getByText("Desde el 10/11/2026 · 1 día")).toBeTruthy();
  });

  it("sin filas no hay lista: un estado que dice que no hay deuda vencida", () => {
    pintar(morosidad({ unidades: [], intereses_al: null }));
    expect(screen.queryByRole("list", { name: "Unidades con deuda" })).toBeNull();
    expect(screen.getByRole("status").textContent).toBe("No hay unidades con deuda vencida");
  });

  it("Exportar a Excel es un link común a la ruta de Next, sólo con exportar_morosidad en el edificio", () => {
    pintar(morosidad());
    const link = screen.getByRole("link", { name: "Exportar a Excel" });
    expect(link.getAttribute("href")).toBe(`/edificios/${EDIFICIO}/morosidad/excel`);
    cleanup();
    pintar(morosidad(), ["ver_morosidad"]);
    expect(screen.queryByRole("link", { name: "Exportar a Excel" })).toBeNull();
  });
});
