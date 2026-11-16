import { beforeEach, describe, expect, it, vi } from "vitest";

const registrarCargoCobradoDeMenos = vi.fn();
const revalidatePath = vi.fn();
vi.mock("next/cache", () => ({ revalidatePath: (...args: unknown[]) => revalidatePath(...args) }));
vi.mock("../../../../../lib/api/liquidaciones", () => ({
  registrarCargoCobradoDeMenos: (...args: unknown[]) => registrarCargoCobradoDeMenos(...args),
}));

import { cargoCobradoDeMenosAction } from "./cargos";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const UNIDAD = "22222222-2222-2222-2222-222222222222";
const OPERACION = "33333333-3333-3333-3333-333333333333";
const ORIGEN = "44444444-4444-4444-4444-444444444444";

function formulario(campos: Record<string, string> = {}): FormData {
  const datos = new FormData();
  const base = {
    operacion_id: OPERACION,
    unidad_id: UNIDAD,
    obligacion_origen_id: ORIGEN,
    importe: "1500,00",
    componente: "ordinaria",
    motivo: "  Faltó cobrar el portón  ",
    ...campos,
  };
  for (const [clave, valor] of Object.entries(base)) datos.append(clave, valor);
  return datos;
}

describe("cargoCobradoDeMenosAction (H-017)", () => {
  beforeEach(() => {
    registrarCargoCobradoDeMenos.mockReset();
    revalidatePath.mockReset();
  });

  it("manda el importe con punto, la obligación de origen y la operación", async () => {
    registrarCargoCobradoDeMenos.mockResolvedValue({
      estado: "ok",
      datos: { importe: "1500.00", motivo: "Faltó cobrar el portón" },
    });
    const estado = await cargoCobradoDeMenosAction(EDIFICIO, null, formulario());
    expect(registrarCargoCobradoDeMenos).toHaveBeenCalledWith(EDIFICIO, UNIDAD, {
      operacion_id: OPERACION,
      obligacion_origen_id: ORIGEN,
      importe: "1500.00",
      componente: "ordinaria",
      motivo: "Faltó cobrar el portón",
    });
    expect(estado?.hecho?.importe).toBe("1500.00");
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${EDIFICIO}/liquidaciones`);
  });

  it.each([
    ["1500", "1500.00"],
    ["1500,5", "1500.50"],
    ["0,05", "0.05"],
  ])("el importe %s viaja como %s", async (escrito, enviado) => {
    registrarCargoCobradoDeMenos.mockResolvedValue({ estado: "ok", datos: {} });
    await cargoCobradoDeMenosAction(EDIFICIO, null, formulario({ importe: escrito }));
    expect(registrarCargoCobradoDeMenos.mock.calls[0]?.[2].importe).toBe(enviado);
  });

  it.each([
    ["importe", { importe: "" }],
    ["importe", { importe: "0,00" }],
    ["importe", { importe: "-5,00" }],
    ["importe", { importe: "1,234" }],
    ["componente", { componente: "intereses" }],
    ["motivo", { motivo: "   " }],
    ["motivo", { motivo: "x".repeat(501) }],
  ])("un %s inválido vuelve al campo y no sale a la API", async (campo, cambio) => {
    const estado = await cargoCobradoDeMenosAction(EDIFICIO, null, formulario(cambio));
    expect(Object.keys(estado?.erroresPorCampo ?? {})).toContain(campo);
    expect(registrarCargoCobradoDeMenos).not.toHaveBeenCalled();
  });

  it("sin operación, unidad u obligación no sale a la API", async () => {
    for (const campo of ["operacion_id", "unidad_id", "obligacion_origen_id"]) {
      const estado = await cargoCobradoDeMenosAction(EDIFICIO, null, formulario({ [campo]: "" }));
      expect(estado?.error).toBeTruthy();
    }
    expect(registrarCargoCobradoDeMenos).not.toHaveBeenCalled();
  });

  it.each([
    [{ estado: "sin_permiso", permiso: "corregir_movimiento" }, /No podés registrar/],
    [{ estado: "conflicto", campo: "operacion_id" }, /ya se registró con otros datos/],
    [{ estado: "conflicto", campo: "otro" }, /No pudimos registrar el cargo/],
    [{ estado: "no_existe" }, /ya no existe/],
    [{ estado: "fallo" }, /No pudimos registrar el cargo/],
  ])("%j se dice con un mensaje propio, sin revalidar", async (resultado, mensaje) => {
    registrarCargoCobradoDeMenos.mockResolvedValue(resultado);
    const estado = await cargoCobradoDeMenosAction(EDIFICIO, null, formulario());
    expect(estado?.error).toMatch(mensaje);
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it("un 422 de la API vuelve al campo que nombra", async () => {
    registrarCargoCobradoDeMenos.mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: "importe", motivo: "x" }],
    });
    const estado = await cargoCobradoDeMenosAction(EDIFICIO, null, formulario());
    expect(Object.keys(estado?.erroresPorCampo ?? {})).toEqual(["importe"]);
  });
});
