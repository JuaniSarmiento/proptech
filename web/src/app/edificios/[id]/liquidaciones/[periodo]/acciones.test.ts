import { beforeEach, describe, expect, it, vi } from "vitest";

const { emitirLiquidacion } = vi.hoisted(() => ({ emitirLiquidacion: vi.fn() }));
vi.mock("../../../../../lib/api/liquidaciones", () => ({ emitirLiquidacion }));
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import { emitirLiquidacionAction } from "./acciones";

const ID = "11111111-1111-1111-1111-111111111111";
const EMISION = "22222222-2222-2222-2222-222222222222";

function formulario(campos: Record<string, string | string[]>): FormData {
  const datos = new FormData();
  for (const [clave, valor] of Object.entries(campos)) {
    for (const v of Array.isArray(valor) ? valor : [valor]) datos.append(clave, v);
  }
  return datos;
}

const BASE = { emision_id: EMISION, huella: "h" };

beforeEach(() => emitirLiquidacion.mockReset());

describe("emitirLiquidacionAction", () => {
  it("manda la huella, las alertas marcadas y ningún vencimiento si no se corre", async () => {
    emitirLiquidacion.mockResolvedValue({ estado: "ok", datos: { liquidacion_id: "l" } });
    const estado = await emitirLiquidacionAction(
      ID,
      "2026-11-01",
      null,
      formulario({ ...BASE, alerta: ["gastos_en_revision"] }),
    );
    expect(estado).toEqual({ emitida: { liquidacion_id: "l" } });
    expect(emitirLiquidacion).toHaveBeenCalledWith(ID, "2026-11-01", {
      emision_id: EMISION,
      huella: "h",
      alertas_aceptadas: ["gastos_en_revision"],
    });
  });

  it("corre el vencimiento con la fecha y el motivo sin espacios de más", async () => {
    emitirLiquidacion.mockResolvedValue({ estado: "ok", datos: {} });
    await emitirLiquidacionAction(
      ID,
      "2026-11-01",
      null,
      formulario({
        ...BASE,
        correr_vencimiento: "on",
        vencimiento_fecha: "2026-11-12",
        motivo_del_vencimiento: "  Feriado ",
      }),
    );
    expect(emitirLiquidacion.mock.calls[0]?.[2].vencimiento).toEqual({
      fecha: "2026-11-12",
      motivo: "Feriado",
    });
  });

  it.each([
    ["sin fecha", { vencimiento_fecha: "", motivo_del_vencimiento: "x" }],
    ["sin motivo", { vencimiento_fecha: "2026-11-12", motivo_del_vencimiento: "  " }],
    [
      "con un motivo de más",
      { vencimiento_fecha: "2026-11-12", motivo_del_vencimiento: "x".repeat(501) },
    ],
  ])("un vencimiento corrido %s no llega a la API", async (_nombre, campos) => {
    const estado = await emitirLiquidacionAction(
      ID,
      "2026-11-01",
      null,
      formulario({ ...BASE, correr_vencimiento: "on", ...campos }),
    );
    expect(estado?.error).toBeTruthy();
    expect(emitirLiquidacion).not.toHaveBeenCalled();
  });

  it("sin huella no hay pedido", async () => {
    const estado = await emitirLiquidacionAction(
      ID,
      "2026-11-01",
      null,
      formulario({ emision_id: EMISION }),
    );
    expect(estado?.error).toBeTruthy();
    expect(emitirLiquidacion).not.toHaveBeenCalled();
  });

  it("un 409 de la huella se traduce, sin mostrar el texto de la API", async () => {
    emitirLiquidacion.mockResolvedValue({
      estado: "conflicto",
      campo: "huella",
      motivo: "preliquidacion_cambio",
    });
    const estado = await emitirLiquidacionAction(ID, "2026-11-01", null, formulario(BASE));
    expect(estado?.error).toMatch(/cambió desde que la revisaste/);
  });

  it("un conflicto desconocido recibe un mensaje genérico", async () => {
    emitirLiquidacion.mockResolvedValue({ estado: "conflicto", campo: "otro" });
    const estado = await emitirLiquidacionAction(ID, "2026-11-01", null, formulario(BASE));
    expect(estado?.error).toMatch(/No pudimos emitir/);
  });

  it("sin permiso y fallo se dicen", async () => {
    emitirLiquidacion.mockResolvedValue({ estado: "sin_permiso", permiso: "x" });
    expect(
      (await emitirLiquidacionAction(ID, "2026-11-01", null, formulario(BASE)))?.error,
    ).toMatch(/No podés emitir/);
    emitirLiquidacion.mockResolvedValue({ estado: "fallo" });
    expect(
      (await emitirLiquidacionAction(ID, "2026-11-01", null, formulario(BASE)))?.error,
    ).toMatch(/No pudimos emitir/);
  });
});
