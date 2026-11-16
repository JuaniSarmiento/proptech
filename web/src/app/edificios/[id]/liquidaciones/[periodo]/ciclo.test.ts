import { beforeEach, describe, expect, it, vi } from "vitest";

const { distribuirLiquidacion, anularLiquidacion, revalidatePath } = vi.hoisted(() => ({
  distribuirLiquidacion: vi.fn(),
  anularLiquidacion: vi.fn(),
  revalidatePath: vi.fn(),
}));
vi.mock("../../../../../lib/api/liquidaciones", () => ({
  distribuirLiquidacion,
  anularLiquidacion,
}));
vi.mock("next/cache", () => ({ revalidatePath }));

import { anularLiquidacionAction, distribuirLiquidacionAction } from "./ciclo";

const ID = "11111111-1111-1111-1111-111111111111";
const LIQUIDACION = "22222222-2222-2222-2222-222222222222";

function formulario(campos: Record<string, string>): FormData {
  const datos = new FormData();
  for (const [clave, valor] of Object.entries(campos)) datos.append(clave, valor);
  return datos;
}

beforeEach(() => {
  distribuirLiquidacion.mockReset();
  anularLiquidacion.mockReset();
  revalidatePath.mockReset();
});

describe("distribuirLiquidacionAction", () => {
  it("distribuye y revalida el edificio", async () => {
    distribuirLiquidacion.mockResolvedValue({ estado: "ok", datos: { estado: "distribuida" } });
    const estado = await distribuirLiquidacionAction(ID, LIQUIDACION, null, new FormData());
    expect(estado).toEqual({ hecho: "distribuida" });
    expect(distribuirLiquidacion).toHaveBeenCalledWith(ID, LIQUIDACION);
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${ID}`);
  });

  it.each([
    ["ya_distribuida", /ya está distribuida/],
    ["anulada", /ya está anulada/],
  ])("un 409 %s se dice con su mensaje y no con el de la API", async (motivo, mensaje) => {
    distribuirLiquidacion.mockResolvedValue({ estado: "conflicto", campo: "estado", motivo });
    const estado = await distribuirLiquidacionAction(ID, LIQUIDACION, null, new FormData());
    expect(estado?.error).toMatch(mensaje);
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("un código de 409 que no conoce da un mensaje genérico", async () => {
    distribuirLiquidacion.mockResolvedValue({
      estado: "conflicto",
      campo: "estado",
      motivo: "texto-raro-de-la-api",
    });
    const estado = await distribuirLiquidacionAction(ID, LIQUIDACION, null, new FormData());
    expect(estado?.error).toBe("No pudimos distribuir la liquidación.");
  });
});

describe("anularLiquidacionAction", () => {
  it("manda el motivo sin espacios de más", async () => {
    anularLiquidacion.mockResolvedValue({ estado: "ok", datos: { estado: "anulada" } });
    const estado = await anularLiquidacionAction(
      ID,
      LIQUIDACION,
      null,
      formulario({ motivo: "  Se cargó mal una factura " }),
    );
    expect(estado).toEqual({ hecho: "anulada" });
    expect(anularLiquidacion).toHaveBeenCalledWith(ID, LIQUIDACION, "Se cargó mal una factura");
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${ID}`);
  });

  it.each([
    ["vacío", ""],
    ["en blanco", "   "],
    ["demasiado largo", "x".repeat(501)],
  ])("un motivo %s no llega a la API", async (_nombre, motivo) => {
    const estado = await anularLiquidacionAction(ID, LIQUIDACION, null, formulario({ motivo }));
    expect(estado?.error).toMatch(/motivo/);
    expect(anularLiquidacion).not.toHaveBeenCalled();
  });

  it("el período siguiente emitido dice qué hacer", async () => {
    anularLiquidacion.mockResolvedValue({
      estado: "conflicto",
      campo: "periodo",
      motivo: "periodo_siguiente_emitido",
    });
    const estado = await anularLiquidacionAction(
      ID,
      LIQUIDACION,
      null,
      formulario({ motivo: "Error" }),
    );
    expect(estado?.error).toMatch(/primero anulá el siguiente/);
  });

  it("sin permiso, sin sesión y un fallo se dicen distinto", async () => {
    for (const [resultado, mensaje] of [
      [{ estado: "sin_permiso", permiso: "anular_liquidacion" }, /No podés anular/],
      [{ estado: "sin_sesion" }, /sesión/i],
      [{ estado: "fallo" }, /Probá de nuevo/],
    ] as const) {
      anularLiquidacion.mockResolvedValue(resultado);
      const estado = await anularLiquidacionAction(
        ID,
        LIQUIDACION,
        null,
        formulario({ motivo: "Error" }),
      );
      expect(estado?.error).toMatch(mensaje);
    }
  });
});
