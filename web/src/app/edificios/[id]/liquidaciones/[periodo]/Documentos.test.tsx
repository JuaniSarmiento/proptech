/**
 * @vitest-environment jsdom
 */
import { cleanup, render as renderOriginal, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { DocumentoDeExpensa } from "../../../../../lib/api/documentos";
import { Documentos, type EstadoDeDescarga, type EstadoDeReproceso } from "./Documentos";

afterEach(cleanup);

const ID = "e1";

function render(ui: ReactElement, acciones: string[] = ["emitir_y_distribuir_liquidacion"]) {
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

const DOCUMENTOS: DocumentoDeExpensa[] = [
  {
    documento_id: "d1",
    unidad_id: "u1",
    identificador: "1A",
    variante: "completa",
    estado: "generado",
    motivo: null,
  },
  {
    documento_id: "d2",
    unidad_id: "u1",
    identificador: "1A",
    variante: "sin_extraordinaria",
    estado: "fallido",
    motivo: "sin fuentes",
  },
  {
    documento_id: "d3",
    unidad_id: "u2",
    identificador: "1B",
    variante: "completa",
    estado: "pendiente",
    motivo: null,
  },
];

const descargar = (estado: EstadoDeDescarga = null) =>
  vi.fn(async (_previo: EstadoDeDescarga, _formulario: FormData) => estado);
const reprocesar = (estado: EstadoDeReproceso = null) =>
  vi.fn(async (_previo: EstadoDeReproceso, _formulario: FormData) => estado);

describe("Documentos (H-015)", () => {
  it("cada documento dice su estado en texto y el fallido su motivo", () => {
    render(
      <Documentos
        id={ID}
        documentos={DOCUMENTOS}
        accionReprocesar={reprocesar()}
        accionDescargar={descargar()}
      />,
    );
    const region = screen.getByRole("region", { name: "Documentos" });
    expect(within(region).getByText("Generado")).toBeTruthy();
    expect(within(region).getByText("Fallido")).toBeTruthy();
    expect(within(region).getByText("Pendiente")).toBeTruthy();
    expect(within(region).getByText("(sin fuentes)")).toBeTruthy();
  });

  it("sólo el generado ofrece su descarga, con la unidad y la variante en el nombre", () => {
    render(
      <Documentos
        id={ID}
        documentos={DOCUMENTOS}
        accionReprocesar={reprocesar()}
        accionDescargar={descargar()}
      />,
    );
    const botones = screen.getAllByRole("button", { name: /^Descargar/ });
    expect(botones).toHaveLength(1);
    expect(botones[0]?.textContent).toBe("Descargar 1A · Completa");
  });

  it("descargar manda el documento y su variante a la acción y baja la ruta que devuelve", async () => {
    const accion = descargar({ ruta: "/documentos/descarga?token=t", pedido: 1 });
    const clicks: string[] = [];
    const original = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function (this: HTMLAnchorElement) {
      clicks.push(`${this.getAttribute("href")}|${this.hasAttribute("download")}`);
    };
    try {
      render(
        <Documentos
          id={ID}
          documentos={DOCUMENTOS}
          accionReprocesar={reprocesar()}
          accionDescargar={accion}
        />,
      );
      await userEvent.click(screen.getByRole("button", { name: "Descargar 1A · Completa" }));
      await waitFor(() => expect(clicks).toEqual(["/documentos/descarga?token=t|true"]));
    } finally {
      HTMLAnchorElement.prototype.click = original;
    }
    const formulario = accion.mock.calls[0]?.[1];
    expect(formulario?.get("documento_id")).toBe("d1");
    expect(formulario?.get("variante")).toBe("completa");
  });

  it("un error de la descarga se dice en su fila", async () => {
    render(
      <Documentos
        id={ID}
        documentos={DOCUMENTOS}
        accionReprocesar={reprocesar()}
        accionDescargar={descargar({ error: "No podés descargar este documento." })}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Descargar 1A · Completa" }));
    expect((await screen.findByRole("alert")).textContent).toBe(
      "No podés descargar este documento.",
    );
  });

  it("reprocesar dice cuántos se encolaron", async () => {
    const accion = reprocesar({ encolados: 2 });
    render(
      <Documentos
        id={ID}
        documentos={DOCUMENTOS}
        accionReprocesar={accion}
        accionDescargar={descargar()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Reprocesar" }));
    expect((await screen.findByRole("status")).textContent).toBe(
      "Se encolaron 2 documentos para generarse.",
    );
    expect(accion).toHaveBeenCalledTimes(1);
  });

  it("sin el permiso de emitir no hay Reprocesar, pero sí las descargas", () => {
    render(
      <Documentos
        id={ID}
        documentos={DOCUMENTOS}
        accionReprocesar={reprocesar()}
        accionDescargar={descargar()}
      />,
      [],
    );
    expect(screen.queryByRole("button", { name: "Reprocesar" })).toBeNull();
    expect(screen.getByRole("button", { name: /^Descargar 1A/ })).toBeTruthy();
  });

  it("sin poder leer los documentos lo dice, y una lista vacía también", () => {
    const { rerender } = render(
      <Documentos id={ID} documentos={null} accionReprocesar={reprocesar()} />,
    );
    expect(screen.getByText(/No pudimos cargar los documentos/)).toBeTruthy();
    rerender(
      <SesionDePantalla
        value={{ administracionId: "a", datos: { persona: { nombre: "P" }, administraciones: [] } }}
      >
        <Documentos id={ID} documentos={[]} />
      </SesionDePantalla>,
    );
    expect(screen.getByText("Esta liquidación no tiene documentos.")).toBeTruthy();
  });
});
