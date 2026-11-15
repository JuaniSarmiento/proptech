/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../../../../../lib/test/accesibilidad";
import { PRELIQUIDACION } from "../../../../../lib/test/preliquidacion";
import { PantallaPreliquidacion, PantallaSinPreliquidar } from "./Pantalla";

afterEach(cleanup);

const PROPS = {
  id: "e1",
  nombreEdificio: "Torre Ficticia",
  periodoEnPalabras: "noviembre de 2026",
};

function fila(identificador: string): HTMLElement {
  const tabla = screen.getAllByRole("table")[0];
  if (!tabla) throw new Error("no hay tabla");
  const celda = within(tabla).getByRole("cell", { name: identificador });
  const laFila = celda.closest("tr");
  if (!laFila) throw new Error("la celda no está en una fila");
  return laFila;
}

describe("PantallaPreliquidacion", () => {
  it("el título dice el período en palabras", () => {
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Preliquidación de noviembre de 2026" }),
    ).toBeTruthy();
  });

  it("la tabla trae las seis columnas con fondo y una fila por unidad con punto de miles", () => {
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} />);
    for (const columna of [
      "Ordinaria",
      "Fondo de reserva",
      "Extraordinaria",
      "Cargos particulares",
      "Intereses",
      "Total",
    ]) {
      expect(screen.getAllByRole("columnheader", { name: columna }).length).toBeGreaterThan(0);
    }
    const unaFila = fila("1A");
    for (const importe of ["27.000,00", "1.350,00", "15.000,00", "5.000,00", "48.350,00"]) {
      expect(unaFila.textContent).toContain(importe);
    }
    expect(unaFila.textContent).toContain("Multa");
  });

  it("con fondo 0% no hay columna ni renglón del fondo", () => {
    const sinFondo: typeof PRELIQUIDACION = {
      ...PRELIQUIDACION,
      porcentaje_fondo: "0.00",
      totales: { ...PRELIQUIDACION.totales, fondo_de_reserva: "0.00" },
    };
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={sinFondo} />);
    expect(screen.queryByRole("columnheader", { name: "Fondo de reserva" })).toBeNull();
    expect(screen.queryByText("Fondo de reserva")).toBeNull();
  });

  it("con fondo, el renglón de totales y la columna están", () => {
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} />);
    expect(screen.getAllByText("Fondo de reserva").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("6.500,00")).toBeTruthy();
    expect(screen.getByText("191.500,00")).toBeTruthy();
  });

  it("los bloques muestran categoría, importe, porcentaje y subtotal", () => {
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} />);
    const ordinaria = screen.getByRole("region", { name: "Ordinaria" });
    for (const texto of ["Limpieza", "90.000,00", "69,23 %", "130.000,00"]) {
      expect(ordinaria.textContent).toContain(texto);
    }
    const extraordinaria = screen.getByRole("region", { name: "Extraordinaria" });
    for (const texto of ["Pintura", "50.000,00", "100,00 %"]) {
      expect(extraordinaria.textContent).toContain(texto);
    }
  });

  it("un bloque sin gastos lo dice y no arma una tabla vacía", () => {
    const sinExtra: typeof PRELIQUIDACION = {
      ...PRELIQUIDACION,
      bloques: { ...PRELIQUIDACION.bloques, extraordinario: { subtotal: "0.00", categorias: [] } },
    };
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={sinExtra} />);
    const extraordinaria = screen.getByRole("region", { name: "Extraordinaria" });
    expect(within(extraordinaria).queryByRole("table")).toBeNull();
    expect(extraordinaria.textContent).toContain("No hay gastos de este tipo");
  });

  it("una unidad sin obligación lo dice en su fila", () => {
    const [primera] = PRELIQUIDACION.unidades;
    if (!primera) throw new Error("falta la unidad de la base");
    const sinObligacion: typeof PRELIQUIDACION = {
      ...PRELIQUIDACION,
      unidades: [
        {
          ...primera,
          ordinaria: "0.00",
          fondo_de_reserva: "0.00",
          extraordinaria: "0.00",
          cargos_particulares: [],
          total: "0.00",
          sin_obligacion: true,
          por_grupo: [],
        },
      ],
    };
    render(<PantallaPreliquidacion {...PROPS} preliquidacion={sinObligacion} />);
    expect(fila("1A").textContent).toContain("Sin obligación este período");
  });

  it("no tiene violaciones de accesibilidad", async () => {
    const { container } = render(
      <PantallaPreliquidacion {...PROPS} preliquidacion={PRELIQUIDACION} />,
    );
    await sinViolaciones(container);
  });
});

describe("PantallaSinPreliquidar", () => {
  it("el período anterior sin emitir se dice en una alerta y no hay tabla", () => {
    render(
      <PantallaSinPreliquidar {...PROPS} campo="periodo" motivo="periodo_anterior_sin_emitir" />,
    );
    expect(screen.getByRole("alert").textContent).toMatch(/período anterior/i);
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("un período ya emitido tiene su propio mensaje", () => {
    render(<PantallaSinPreliquidar {...PROPS} campo="periodo" motivo="periodo_emitido" />);
    expect(screen.getByRole("alert").textContent).toMatch(/ya está emitido/i);
  });

  it("una configuración que falta manda a configurarla", () => {
    render(
      <PantallaSinPreliquidar
        {...PROPS}
        campo="configuracion"
        motivo="configuracion_sin_definir"
      />,
    );
    expect(
      screen.getByRole("link", { name: "Ir a intereses y vencimiento" }).getAttribute("href"),
    ).toBe("/edificios/e1/configuracion");
  });

  it("un código que no conoce recibe el mensaje genérico y nunca repite el texto de la API", () => {
    render(<PantallaSinPreliquidar {...PROPS} campo="otro" motivo="TRACEBACK_TECNICO_PRIVADO" />);
    const alerta = screen.getByRole("alert");
    expect(alerta.textContent).toMatch(/No se puede preparar este período ahora/);
    expect(alerta.textContent).not.toContain("TRACEBACK");
  });

  it("no tiene violaciones de accesibilidad", async () => {
    const { container } = render(
      <PantallaSinPreliquidar {...PROPS} campo="periodo" motivo="periodo_emitido" />,
    );
    await sinViolaciones(container);
  });
});
