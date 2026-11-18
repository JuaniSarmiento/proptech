import { beforeEach, describe, expect, it, vi } from "vitest";

const { resolverPago, enlaceDelComprobante, revalidatePath } = vi.hoisted(() => ({
  resolverPago: vi.fn(),
  enlaceDelComprobante: vi.fn(),
  revalidatePath: vi.fn(),
}));
vi.mock("../../../../lib/api/pagos", async (importar) => ({
  ...(await importar<typeof import("../../../../lib/api/pagos")>()),
  resolverPago,
  enlaceDelComprobante,
}));
vi.mock("next/cache", () => ({ revalidatePath }));

import { resolverPagoAction, verComprobanteAction } from "./acciones";

const ID = "11111111-1111-1111-1111-111111111111";
const PAGO = "22222222-2222-2222-2222-222222222222";
const DESDE = "33333333-3333-3333-3333-333333333333";
const HACIA = "44444444-4444-4444-4444-444444444444";
const TOKEN = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

beforeEach(() => {
  resolverPago.mockReset();
  enlaceDelComprobante.mockReset();
  revalidatePath.mockReset();
});

describe("resolverPagoAction", () => {
  it("confirma sin cuerpo y revalida el edificio", async () => {
    resolverPago.mockResolvedValue({
      estado: "ok",
      datos: { pago_id: PAGO, estado: "confirmado" },
    });
    const r = await resolverPagoAction(ID, PAGO, { accion: "confirmacion" });
    expect(r).toEqual({ hecho: "Pago confirmado." });
    expect(resolverPago).toHaveBeenCalledWith(ID, PAGO, "confirmacion", undefined);
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${ID}`);
  });

  it("rechazar y revertir mandan sólo el motivo, sin los espacios de los bordes", async () => {
    resolverPago.mockResolvedValue({ estado: "ok", datos: { pago_id: PAGO, estado: "x" } });
    await resolverPagoAction(ID, PAGO, { accion: "rechazo", motivo: "  No coincide  " });
    expect(resolverPago).toHaveBeenLastCalledWith(ID, PAGO, "rechazo", { motivo: "No coincide" });
    await resolverPagoAction(ID, PAGO, { accion: "reversion", motivo: "Cheque rechazado" });
    expect(resolverPago).toHaveBeenLastCalledWith(ID, PAGO, "reversion", {
      motivo: "Cheque rechazado",
    });
  });

  it("reimputar manda las dos unidades y el motivo, y nada más", async () => {
    resolverPago.mockResolvedValue({ estado: "ok", datos: { pago_id: PAGO, estado: "x" } });
    await resolverPagoAction(ID, PAGO, {
      accion: "reimputacion",
      motivo: "Era de 2A",
      desdeUnidadId: DESDE,
      haciaUnidadId: HACIA,
    });
    expect(resolverPago).toHaveBeenCalledWith(ID, PAGO, "reimputacion", {
      desde_unidad_id: DESDE,
      hacia_unidad_id: HACIA,
      motivo: "Era de 2A",
    });
  });

  it.each([
    [{ accion: "rechazo" as const, motivo: "  " }],
    [{ accion: "rechazo" as const, motivo: "ab" }],
    [{ accion: "reversion" as const }],
    [{ accion: "reimputacion" as const, motivo: "Era de 2A" }],
  ])("%j no llega a la API", async (pedido) => {
    const r = await resolverPagoAction(ID, PAGO, pedido);
    expect(r.error).toBeTruthy();
    expect(resolverPago).not.toHaveBeenCalled();
  });

  it("un 409 se dice con un mensaje propio y no revalida", async () => {
    resolverPago.mockResolvedValue({ estado: "conflicto", campo: "pago", motivo: "estado" });
    const r = await resolverPagoAction(ID, PAGO, { accion: "confirmacion" });
    expect(r.error).toMatch(/cambió de estado/);
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("un 403, un 404 y una falla se dicen sin el texto de la API", async () => {
    resolverPago.mockResolvedValueOnce({ estado: "sin_permiso", permiso: "x" });
    expect((await resolverPagoAction(ID, PAGO, { accion: "confirmacion" })).error).toMatch(
      /No podés confirmar/,
    );
    resolverPago.mockResolvedValueOnce({ estado: "no_existe" });
    expect((await resolverPagoAction(ID, PAGO, { accion: "confirmacion" })).error).toMatch(
      /ya no existe/,
    );
    resolverPago.mockResolvedValueOnce({ estado: "fallo" });
    expect((await resolverPagoAction(ID, PAGO, { accion: "confirmacion" })).error).toMatch(
      /No pudimos confirmar/,
    );
  });
});

describe("verComprobanteAction", () => {
  it("convierte el enlace de la API en la ruta de la web", async () => {
    enlaceDelComprobante.mockResolvedValue({
      estado: "ok",
      datos: { url: `/api/comprobantes/descarga?token=${TOKEN}`, vence_en: "x" },
    });
    expect(await verComprobanteAction(ID, PAGO)).toEqual({
      ruta: `/comprobantes/descarga?token=${TOKEN}`,
    });
  });

  it("una dirección que no es la esperada no se entrega", async () => {
    enlaceDelComprobante.mockResolvedValue({
      estado: "ok",
      datos: { url: "https://otro.example/x?token=1", vence_en: "x" },
    });
    const r = await verComprobanteAction(ID, PAGO);
    expect(r.ruta).toBeUndefined();
    expect(r.error).toBeTruthy();
  });

  it("un 403 se dice con su mensaje", async () => {
    enlaceDelComprobante.mockResolvedValue({ estado: "sin_permiso", permiso: "x" });
    expect((await verComprobanteAction(ID, PAGO)).error).toBe("No podés ver este comprobante.");
  });
});
