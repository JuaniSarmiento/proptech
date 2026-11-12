/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { ComparacionDelBorrador } from "../../../../../lib/api/importaciones";
import { sinViolaciones } from "../../../../../lib/test/accesibilidad";
import { PantallaComparacion, PantallaSinBorrador } from "./Pantalla";

afterEach(cleanup);

const AVISO = "El primer interés del sistema cubre octubre de 2026";

function render(ui: ReactElement, acciones: string[] = ["aceptar_diferencias_de_saldos"]) {
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

const CON_DIFERENCIAS: ComparacionDelBorrador = {
  importacion_id: "i1",
  unidades: [
    {
      unidad: "1A",
      unidad_id: "u1",
      borrador: "169000.00",
      control: "159000.00",
      diferencia: "10000.00",
      aviso: AVISO,
    },
    {
      unidad: "1B",
      unidad_id: "u2",
      borrador: "105000.00",
      control: "105000.00",
      diferencia: "0.00",
      aviso: AVISO,
    },
    {
      unidad: "2A",
      unidad_id: "u3",
      borrador: "52000.00",
      control: "62000.00",
      diferencia: "-10000.00",
      aviso: AVISO,
    },
  ],
  total_borrador: "326000.00",
  total_control: "326000.00",
  unidades_con_diferencia: 2,
  requiere_aceptacion: true,
  aceptacion: null,
};

const SIN_DIFERENCIAS: ComparacionDelBorrador = {
  importacion_id: "i2",
  unidades: [
    {
      unidad: "1A",
      unidad_id: "u1",
      borrador: "169000.00",
      control: "169000.00",
      diferencia: "0.00",
      aviso: null,
    },
  ],
  total_borrador: "169000.00",
  total_control: "169000.00",
  unidades_con_diferencia: 0,
  requiere_aceptacion: false,
  aceptacion: null,
};

const ACEPTADA = {
  aceptacion_id: "a1",
  diferencias: [
    { unidad: "1A", borrador: "169000.00", control: "159000.00", diferencia: "10000.00" },
    { unidad: "2A", borrador: "52000.00", control: "62000.00", diferencia: "-10000.00" },
  ],
  aceptada_por: "p1",
  aceptada_en: "2026-11-12T15:00:00+00:00",
};

/** Un elemento que tiene que estar: falla por `expect`, no por la excepción de `getBy`. */
function ahi(elemento: HTMLElement | null): HTMLElement {
  expect(elemento).not.toBeNull();
  return elemento as HTMLElement;
}

const tabla = () => ahi(screen.queryByRole("table", { name: "Comparación por unidad" }));
const botonAceptar = () => ahi(screen.queryByRole("button", { name: "Aceptar diferencias" }));
const confirmacion = () => ahi(screen.queryByRole("dialog"));
const botonConfirmar = () => ahi(within(confirmacion()).queryByRole("button", { name: "Aceptar" }));

function pantalla(comparacion = CON_DIFERENCIAS, accion = vi.fn().mockResolvedValue(null)) {
  return (
    <PantallaComparacion
      id="e1"
      nombreEdificio="Edificio API"
      comparacion={comparacion}
      accionAceptar={accion}
    />
  );
}

describe("PantallaComparacion", () => {
  it("el encabezado y la tabla con sus cuatro columnas y una fila por unidad en formato argentino", () => {
    render(pantalla());
    expect(
      screen.queryByRole("heading", { name: "Comparación de saldos", level: 1 }),
    ).not.toBeNull();
    for (const columna of ["Unidad", "Borrador", "Control", "Diferencia"]) {
      expect(within(tabla()).queryByRole("columnheader", { name: columna })).not.toBeNull();
    }
    const filas = within(tabla()).getAllByRole("row").slice(1);
    expect(filas).toHaveLength(3);
    expect(filas[0]?.textContent).toContain("169.000,00");
    expect(filas[0]?.textContent).toContain("159.000,00");
    expect(filas[0]?.textContent).toContain("10.000,00");
    expect(filas[2]?.textContent).toContain("-10.000,00");
  });

  it("la tabla se desplaza dentro de una región que el teclado alcanza (a 320 px axe lo exige)", () => {
    render(pantalla());
    const region = ahi(
      screen.queryByRole("region", { name: "Unidades comparadas, con desplazamiento horizontal" }),
    );
    expect(region.getAttribute("tabindex")).toBe("0");
    expect(region.contains(tabla())).toBe(true);
  });

  it("el aviso de mes entero va dentro de la fila de cada unidad que lo tiene, y sólo ahí", () => {
    render(pantalla());
    const filas = within(tabla()).getAllByRole("row").slice(1);
    for (const fila of filas) expect(fila.textContent).toContain(AVISO);
    expect(screen.queryAllByText(AVISO, { exact: false })).toHaveLength(3);
  });

  it("sin ningún aviso no hay columna de avisos", () => {
    render(pantalla(SIN_DIFERENCIAS));
    expect(screen.queryByRole("columnheader", { name: "Aviso" })).toBeNull();
    expect(screen.queryByText(AVISO, { exact: false })).toBeNull();
  });

  it("los totales y la cantidad de unidades con diferencia (aunque los totales coincidan)", () => {
    render(pantalla());
    expect(screen.queryByText("Total del borrador")).not.toBeNull();
    expect(screen.queryByText("Total de control")).not.toBeNull();
    expect(screen.queryAllByText("326.000,00")).toHaveLength(2);
    expect(screen.queryByText("2 unidades con diferencia")).not.toBeNull();
  });

  it("cada total va con su rótulo cuando los dos son distintos", () => {
    render(
      pantalla({ ...CON_DIFERENCIAS, total_borrador: "326000.00", total_control: "300500.50" }),
    );
    const valorDe = (rotulo: string) =>
      ahi(screen.queryByText(rotulo)).parentElement?.querySelector("dd")?.textContent;
    expect(valorDe("Total del borrador")).toBe("326.000,00");
    expect(valorDe("Total de control")).toBe("300.500,50");
  });

  it("cero y una diferencia se dicen bien", () => {
    render(pantalla(SIN_DIFERENCIAS));
    expect(screen.queryByText("0 unidades con diferencia")).not.toBeNull();
    cleanup();
    render(pantalla({ ...CON_DIFERENCIAS, unidades_con_diferencia: 1 }));
    expect(screen.queryByText("1 unidad con diferencia")).not.toBeNull();
  });

  it("sin diferencias no hay botón de aceptar", () => {
    render(pantalla(SIN_DIFERENCIAS));
    expect(screen.queryByRole("button", { name: "Aceptar diferencias" })).toBeNull();
  });

  it("sin el permiso de aceptar no hay botón y se explica, sin alert", () => {
    render(pantalla(), []);
    expect(screen.queryByRole("button", { name: "Aceptar diferencias" })).toBeNull();
    expect(screen.queryByText(/No tenés permiso para aceptar diferencias/)).not.toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("aceptar abre una confirmación que nombra la cantidad, y cancelar no manda nada", async () => {
    const accion = vi.fn().mockResolvedValue(null);
    render(pantalla(CON_DIFERENCIAS, accion));
    const boton = botonAceptar();
    await userEvent.click(boton);
    const dialogo = confirmacion();
    expect(within(dialogo).queryByText(/2 unidades con diferencia/)).not.toBeNull();
    await userEvent.click(ahi(within(dialogo).queryByRole("button", { name: "Cancelar" })));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(accion).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(boton);
  });

  it("Esc cierra la confirmación y devuelve el foco al botón", async () => {
    render(pantalla());
    const boton = botonAceptar();
    await userEvent.click(boton);
    expect(screen.queryByRole("dialog")).not.toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(boton);
  });

  it("confirmar manda el importacion_id y muestra la región de diferencias aceptadas", async () => {
    const accion = vi.fn().mockResolvedValue({ aceptada: ACEPTADA });
    render(pantalla(CON_DIFERENCIAS, accion));
    await userEvent.click(botonAceptar());
    await userEvent.click(botonConfirmar());
    const region = await screen.findByRole("region", { name: "Diferencias aceptadas" });
    expect(accion).toHaveBeenCalledTimes(1);
    const datos = accion.mock.calls[0]?.[1] as FormData;
    expect(datos.get("importacion_id")).toBe("i1");
    expect(region.textContent).toContain("1A");
    expect(region.textContent).toContain("-10.000,00");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("button", { name: "Aceptar diferencias" })).toBeNull();
    await sinViolaciones(region.ownerDocument.body);
  });

  it("una aceptación que ya venía con la comparación se muestra sin botón", () => {
    render(pantalla({ ...CON_DIFERENCIAS, requiere_aceptacion: false, aceptacion: ACEPTADA }));
    expect(screen.queryByRole("region", { name: "Diferencias aceptadas" })).not.toBeNull();
    expect(screen.queryByRole("button", { name: "Aceptar diferencias" })).toBeNull();
  });

  it("el rechazo de la API se dice en un alert y no hay región de aceptadas", async () => {
    const accion = vi
      .fn()
      .mockResolvedValue({ error: "No podés aceptar diferencias en este edificio." });
    render(pantalla(CON_DIFERENCIAS, accion));
    await userEvent.click(botonAceptar());
    await userEvent.click(botonConfirmar());
    const alerta = await screen.findByRole("alert");
    expect(alerta.textContent).toContain("No podés aceptar diferencias en este edificio.");
    expect(screen.queryByRole("region", { name: "Diferencias aceptadas" })).toBeNull();
  });

  it("sin violaciones de accesibilidad con diferencias, sin ellas y con la confirmación abierta", async () => {
    const { container } = render(pantalla());
    await sinViolaciones(container);
    await userEvent.click(botonAceptar());
    await sinViolaciones(container);
    cleanup();
    const otra = render(pantalla(SIN_DIFERENCIAS));
    await sinViolaciones(otra.container);
  });
});

describe("PantallaSinBorrador", () => {
  it("dice que todavía no hay borrador y lleva a importar, sin violaciones", async () => {
    const { container } = render(<PantallaSinBorrador id="e1" nombreEdificio="Edificio API" />);
    expect(
      screen.queryByRole("heading", { name: "Comparación de saldos", level: 1 }),
    ).not.toBeNull();
    expect(screen.queryByText(/Todavía no hay un borrador de saldos/)).not.toBeNull();
    const enlace = ahi(screen.queryByRole("link", { name: "Importar desde Excel" }));
    expect(enlace.getAttribute("href")).toBe("/edificios/e1/importar");
    await sinViolaciones(container);
  });
});
