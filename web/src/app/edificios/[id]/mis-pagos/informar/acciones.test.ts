import { beforeEach, describe, expect, it, vi } from "vitest";

const { informarPago, subirComprobante, revalidatePath, redirect } = vi.hoisted(() => ({
  informarPago: vi.fn(),
  subirComprobante: vi.fn(),
  revalidatePath: vi.fn(),
  redirect: vi.fn((destino: string) => {
    throw new Error(`REDIRECT:${destino}`);
  }),
}));
vi.mock("../../../../../lib/api/pagos", async (importar) => ({
  ...(await importar<typeof import("../../../../../lib/api/pagos")>()),
  informarPago,
  subirComprobante,
}));
vi.mock("next/cache", () => ({ revalidatePath }));
vi.mock("next/navigation", () => ({ redirect }));

import { type DatosDelPago, enviarPagoAction, leerComprobanteAction } from "./acciones";

const ID = "11111111-1111-1111-1111-111111111111";
const COMPROBANTE = "22222222-2222-2222-2222-222222222222";
const U1 = "33333333-3333-3333-3333-333333333333";
const U2 = "44444444-4444-4444-4444-444444444444";

const DATOS: DatosDelPago = {
  comprobanteId: COMPROBANTE,
  banco: " Banco Nación ",
  numeroDeOperacion: "12345678",
  fechaDeTransferencia: "2026-11-05",
  monto: "80775,00",
  cbuDeOrigen: "",
  partes: [
    { unidadId: U1, importe: "43350,00" },
    { unidadId: U2, importe: "" },
  ],
};

beforeEach(() => {
  informarPago.mockReset();
  subirComprobante.mockReset();
  revalidatePath.mockReset();
  redirect.mockClear();
});

describe("leerComprobanteAction", () => {
  it("sube el archivo y devuelve lo que se leyó", async () => {
    const propuesta = {
      banco: "B",
      numero_de_operacion: null,
      fecha: null,
      monto: null,
      cbu_origen: null,
    };
    subirComprobante.mockResolvedValue({
      estado: "ok",
      datos: { comprobante_id: COMPROBANTE, lectura: "ok", propuesta },
    });
    const cuerpo = new FormData();
    cuerpo.append("archivo", new File(["x"], "c.png", { type: "image/png" }));
    expect(await leerComprobanteAction(ID, cuerpo)).toEqual({
      comprobanteId: COMPROBANTE,
      lectura: "ok",
      propuesta,
    });
    expect(subirComprobante).toHaveBeenCalledWith(ID, expect.any(File));
  });

  it("sin archivo no llega a la API", async () => {
    const r = await leerComprobanteAction(ID, new FormData());
    expect("error" in r).toBe(true);
    expect(subirComprobante).not.toHaveBeenCalled();
  });

  it("un archivo que la API rechaza se dice con los tipos y el tope, no con el texto de la API", async () => {
    subirComprobante.mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: "archivo", motivo: "value_error" }],
    });
    const cuerpo = new FormData();
    cuerpo.append("archivo", new File(["x"], "c.exe"));
    const r = await leerComprobanteAction(ID, cuerpo);
    expect(r).toEqual({
      error: "Subí una foto o un PDF del comprobante (JPG, PNG o PDF, de hasta 10 MB).",
    });
  });
});

describe("enviarPagoAction", () => {
  it("manda lo que hay: las unidades con importe, la coma pasada a punto y nada sumado", async () => {
    informarPago.mockResolvedValue({ estado: "ok", datos: { pago_id: "p", estado: "informado" } });
    await expect(enviarPagoAction(ID, DATOS)).rejects.toThrow(
      `REDIRECT:/edificios/${ID}/mis-pagos`,
    );
    expect(informarPago).toHaveBeenCalledWith(ID, {
      comprobante_id: COMPROBANTE,
      banco: "Banco Nación",
      numero_de_operacion: "12345678",
      fecha_de_transferencia: "2026-11-05",
      monto: "80775.00",
      partes: [{ unidad_id: U1, importe: "43350.00" }],
    });
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${ID}`);
  });

  it("el CBU sólo viaja si se escribió", async () => {
    informarPago.mockResolvedValue({ estado: "ok", datos: { pago_id: "p", estado: "informado" } });
    await expect(enviarPagoAction(ID, { ...DATOS, cbuDeOrigen: "0".repeat(22) })).rejects.toThrow(
      "REDIRECT",
    );
    expect(informarPago.mock.calls[0]?.[1]).toMatchObject({ cbu_origen: "0".repeat(22) });
  });

  it("sin ningún importe no llega a la API", async () => {
    const r = await enviarPagoAction(ID, {
      ...DATOS,
      partes: [{ unidadId: U1, importe: " " }],
    });
    expect(r.erroresDesconocidos).toEqual(["Escribí el importe de al menos una unidad."]);
    expect(informarPago).not.toHaveBeenCalled();
  });

  it("un 422 de partes dice que tienen que sumar, y no redirige", async () => {
    informarPago.mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: "partes", motivo: "value_error" }],
    });
    const r = await enviarPagoAction(ID, DATOS);
    expect(r.erroresDesconocidos.join(" ")).toContain("Las partes tienen que sumar el monto");
    expect(redirect).not.toHaveBeenCalled();
  });

  it("un 422 de un campo lo marca en su campo", async () => {
    informarPago.mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: "fecha_de_transferencia", motivo: "value_error" }],
    });
    const r = await enviarPagoAction(ID, DATOS);
    expect(Object.keys(r.erroresPorCampo)).toEqual(["fecha_de_transferencia"]);
  });

  it("un número de operación repetido se marca en su campo", async () => {
    informarPago.mockResolvedValue({
      estado: "conflicto",
      campo: "numero_de_operacion",
      motivo: "repetido",
    });
    const r = await enviarPagoAction(ID, DATOS);
    expect(r.erroresPorCampo.numero_de_operacion).toBe("Ese número de operación ya se informó.");
  });

  it("un 403 y una falla se dicen sin el texto de la API", async () => {
    informarPago.mockResolvedValueOnce({ estado: "sin_permiso", permiso: "x" });
    expect((await enviarPagoAction(ID, DATOS)).erroresDesconocidos[0]).toMatch(/No podés informar/);
    informarPago.mockResolvedValueOnce({ estado: "fallo" });
    expect((await enviarPagoAction(ID, DATOS)).erroresDesconocidos[0]).toMatch(/No pudimos enviar/);
  });
});
