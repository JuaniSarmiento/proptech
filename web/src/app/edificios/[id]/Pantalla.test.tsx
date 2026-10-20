/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { Resumen } from "../../../lib/api/tipos";
import { sinViolaciones } from "../../../lib/test/accesibilidad";
import { PantallaResumen } from "./Pantalla";

afterEach(cleanup);

const RESUMEN_EDIFICIO_NUEVO: Resumen = {
  nombre: "Edificio Nuevo",
  localidad: "Mendoza",
  cantidad_unidades: 0,
  estado_migracion: "pendiente",
  informe: { suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" },
  pasos: {
    unidades: "falta",
    coeficientes: "falta",
    grupos: "falta",
    categorias: "falta",
    intereses_y_vencimiento: "falta",
    saldos_previos: "falta",
  },
  listo_para_liquidar: false,
};

describe("PantallaResumen", () => {
  it("un edificio recién creado muestra el checklist con todo en falta (Edificio recién creado)", () => {
    render(<PantallaResumen id="1" resumen={RESUMEN_EDIFICIO_NUEVO} vigente={null} />);
    const items = screen.getAllByText("Falta");
    expect(items.length).toBe(6);
    expect(screen.queryByText("Listo para liquidar")).toBeNull();
  });

  it('"la web no calcula": 13 unidades con el paso 1 en "falta" según la API se muestra en falta (Datos que no cuadran con el informe)', () => {
    render(
      <PantallaResumen
        id="1"
        resumen={{ ...RESUMEN_EDIFICIO_NUEVO, cantidad_unidades: 13 }}
        vigente={null}
      />,
    );
    expect(screen.getByText("13")).toBeTruthy();
    const items = screen.getAllByText("Falta");
    expect(items.length).toBe(6);
  });

  it('cada paso separa la etiqueta de su estado (no "Cargar unidadesFalta") y marca el estado en la fila (pulido 3b)', () => {
    render(<PantallaResumen id="1" resumen={RESUMEN_EDIFICIO_NUEVO} vigente={null} />);
    const checklist = screen.getByRole("list", { name: "Puesta a punto del edificio" });
    const pasos = within(checklist).getAllByRole("listitem");
    const primero = pasos[0] as HTMLElement;
    // Enmienda 20/10: entre la etiqueta y el estado ahora va la línea gris
    // que explica el paso. Lo que se sigue exigiendo: la etiqueta es SU
    // enlace (sin el estado pegado) y el estado es un elemento aparte, al
    // final de la fila.
    expect(within(primero).getByRole("link").textContent).toBe("Cargar unidades");
    const estado = within(primero).getByText("Falta");
    expect(estado.closest("a")).toBeNull();
    expect(primero.textContent).toMatch(/Falta$/);
    expect(primero.getAttribute("data-estado")).toBe("falta");
  });

  it("un edificio completo muestra Listo para liquidar", () => {
    render(
      <PantallaResumen
        id="1"
        resumen={{
          ...RESUMEN_EDIFICIO_NUEVO,
          listo_para_liquidar: true,
          informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" },
          pasos: {
            unidades: "hecho",
            coeficientes: "hecho",
            grupos: "hecho",
            categorias: "hecho",
            intereses_y_vencimiento: "hecho",
            saldos_previos: "hecho",
          },
        }}
        vigente={null}
      />,
    );
    expect(screen.getByText("Listo para liquidar")).toBeTruthy();
    expect(screen.getAllByText("Hecho").length).toBe(6);
  });

  it("cada paso enlaza a su pantalla, y el paso 6 a saldos previos (D11)", () => {
    render(<PantallaResumen id="42" resumen={RESUMEN_EDIFICIO_NUEVO} vigente={null} />);
    expect(screen.getByRole("link", { name: /Cargar unidades/ }).getAttribute("href")).toBe(
      "/edificios/42/unidades",
    );
    expect(screen.getByRole("link", { name: /sin saldos previos/ }).getAttribute("href")).toBe(
      "/edificios/42/saldos-previos",
    );
  });

  it('barra de progreso "N de 6 pasos" contando lo que marcó la API, y "Tu próximo paso" lleva al primero que falta', () => {
    render(
      <PantallaResumen
        id="7"
        resumen={{
          ...RESUMEN_EDIFICIO_NUEVO,
          pasos: { ...RESUMEN_EDIFICIO_NUEVO.pasos, unidades: "hecho", grupos: "hecho" },
        }}
        vigente={null}
      />,
    );
    expect(screen.getByRole("progressbar", { name: "2 de 6 pasos" })).toBeTruthy();
    const proximo = screen.getByRole("region", { name: "Tu próximo paso" });
    expect(within(proximo).getByText(/Revisar coeficientes/)).toBeTruthy();
    expect(
      within(proximo)
        .getByRole("link", { name: /Completar este paso/ })
        .getAttribute("href"),
    ).toBe("/edificios/7/unidades");
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaResumen id="1" resumen={RESUMEN_EDIFICIO_NUEVO} vigente={null} />,
    );
    await sinViolaciones(container);
  });
});
