/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { UnidadParaInformar } from "../../../../../lib/api/pagos";
import type { DatosDelPago, ResultadoDeLectura, ResultadoDelEnvio } from "./acciones";
import { PantallaInformarPago } from "./Pantalla";

afterEach(cleanup);

const UNA: UnidadParaInformar[] = [{ unidad_id: "u-1a", identificador: "1A" }];
const DOS: UnidadParaInformar[] = [
  { unidad_id: "u-1a", identificador: "1A" },
  { unidad_id: "u-2b", identificador: "2B" },
];

const LEIDO: ResultadoDeLectura = {
  comprobanteId: "c1",
  lectura: "ok",
  propuesta: {
    banco: "Banco Nación",
    numero_de_operacion: "12345678",
    fecha: "2026-11-05",
    monto: "43350.00",
    cbu_origen: null,
  },
};

const VACIO: ResultadoDelEnvio = { erroresPorCampo: {}, erroresDesconocidos: [] };

function pintar(
  unidades: UnidadParaInformar[],
  lectura: ResultadoDeLectura = LEIDO,
  envio: ResultadoDelEnvio = VACIO,
) {
  const leer = vi.fn(async (_cuerpo: FormData) => lectura);
  const enviar = vi.fn(async (_datos: DatosDelPago) => envio);
  render(
    <PantallaInformarPago
      id="e1"
      nombreEdificio="Torre Ficticia"
      unidades={unidades}
      accionLeer={leer}
      accionEnviar={enviar}
    />,
  );
  return { leer, enviar };
}

async function subir() {
  await userEvent.upload(
    screen.getByLabelText("Comprobante"),
    new File(["x"], "comprobante.png", { type: "image/png" }),
  );
}

describe("PantallaInformarPago (H-025)", () => {
  it("antes de elegir el archivo sólo está el comprobante: ningún dato ni importe", () => {
    pintar(DOS);
    expect(screen.getByLabelText("Comprobante")).toBeTruthy();
    expect(screen.queryByLabelText("Banco")).toBeNull();
    expect(screen.queryByLabelText("Importe para 1A")).toBeNull();
    expect(screen.queryByRole("button", { name: "Enviar" })).toBeNull();
  });

  it("al elegir el archivo lo manda a leer y muestra la propuesta en sus campos", async () => {
    const { leer } = pintar(DOS);
    await subir();
    expect(await screen.findByLabelText("Banco")).toHaveProperty("value", "Banco Nación");
    expect(screen.getByLabelText("Número de operación")).toHaveProperty("value", "12345678");
    expect(screen.getByLabelText("Fecha de la transferencia")).toHaveProperty(
      "value",
      "2026-11-05",
    );
    expect(screen.getByLabelText("Monto")).toHaveProperty("value", "43350.00");
    expect(screen.getByLabelText("CBU de origen")).toHaveProperty("value", "");
    expect(leer.mock.calls[0]?.[0].get("archivo")).toBeInstanceOf(File);
    expect(screen.queryByText(/No pudimos leer el comprobante/)).toBeNull();
  });

  it("con dos unidades los importes empiezan vacíos y el envío manda sólo los que se escribieron", async () => {
    const { enviar } = pintar(DOS);
    await subir();
    await screen.findByLabelText("Banco");
    expect(screen.getByLabelText("Importe para 1A")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Importe para 2B")).toHaveProperty("value", "");
    await userEvent.type(screen.getByLabelText("Importe para 1A"), "43350.00");
    await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
    await waitFor(() => expect(enviar).toHaveBeenCalled());
    expect(enviar.mock.calls[0]?.[0]).toEqual({
      comprobanteId: "c1",
      banco: "Banco Nación",
      numeroDeOperacion: "12345678",
      fechaDeTransferencia: "2026-11-05",
      monto: "43350.00",
      cbuDeOrigen: "",
      partes: [
        { unidadId: "u-1a", importe: "43350.00" },
        { unidadId: "u-2b", importe: "" },
      ],
    });
  });

  it("con una sola unidad el importe ya trae el monto y lo acompaña mientras nadie lo toque", async () => {
    pintar(UNA);
    await subir();
    const importe = await screen.findByLabelText("Importe para 1A");
    expect(importe).toHaveProperty("value", "43350.00");
    const monto = screen.getByLabelText("Monto");
    await userEvent.clear(monto);
    await userEvent.type(monto, "43000.00");
    expect(importe).toHaveProperty("value", "43000.00");
    await userEvent.clear(importe);
    await userEvent.type(importe, "1.00");
    await userEvent.clear(monto);
    await userEvent.type(monto, "50.00");
    expect(importe).toHaveProperty("value", "1.00");
  });

  it("si no se pudo leer, los campos quedan vacíos y lo dice en una alerta", async () => {
    pintar(DOS, {
      comprobanteId: "c1",
      lectura: "fallida",
      propuesta: {
        banco: null,
        numero_de_operacion: null,
        fecha: null,
        monto: null,
        cbu_origen: null,
      },
    });
    await subir();
    expect(await screen.findByText(/No pudimos leer el comprobante/)).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("No pudimos leer el comprobante");
    expect(screen.getByLabelText("Banco")).toHaveProperty("value", "");
    expect(screen.getByLabelText("Monto")).toHaveProperty("value", "");
  });

  it("un archivo que se rechaza se dice en el campo y no muestra el resto", async () => {
    pintar(DOS, {
      error: "Subí una foto o un PDF del comprobante (JPG, PNG o PDF, de hasta 10 MB).",
    });
    await subir();
    await waitFor(() =>
      expect(screen.getAllByText(/Subí una foto o un PDF/).length).toBeGreaterThan(0),
    );
    expect(screen.queryByLabelText("Banco")).toBeNull();
  });

  it("si la API dice que las partes no suman, la alerta lo dice y se conserva lo escrito", async () => {
    pintar(DOS, LEIDO, {
      erroresPorCampo: {},
      erroresDesconocidos: ["Las partes tienen que sumar el monto del pago."],
    });
    await subir();
    await screen.findByLabelText("Banco");
    await userEvent.type(screen.getByLabelText("Importe para 1A"), "100.00");
    await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText(/Las partes tienen que sumar el monto/)).toBeTruthy();
    expect(screen.getByLabelText("Importe para 1A")).toHaveProperty("value", "100.00");
    expect(screen.getByLabelText("Banco")).toHaveProperty("value", "Banco Nación");
  });

  it("sin unidades lo dice y no ofrece subir nada", () => {
    pintar([]);
    expect(screen.getByText(/No tenés unidades en este edificio/)).toBeTruthy();
    expect(screen.queryByLabelText("Comprobante")).toBeNull();
  });
});
