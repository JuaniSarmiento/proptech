import { beforeEach, describe, expect, it, vi } from "vitest";

const ajustarSaldoInicial = vi.fn();
const revalidatePath = vi.fn();
vi.mock("next/cache", () => ({ revalidatePath: (...args: unknown[]) => revalidatePath(...args) }));
vi.mock("../../../../../../lib/api/importaciones", () => ({
  ajustarSaldoInicial: (...args: unknown[]) => ajustarSaldoInicial(...args),
}));

import { ajustarSaldoInicialAction } from "./acciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const UNIDAD = "22222222-2222-2222-2222-222222222222";
const OPERACION = "33333333-3333-3333-3333-333333333333";

function formulario(campos: Record<string, string> = {}): FormData {
  const datos = new FormData();
  const base = {
    operacion_id: OPERACION,
    importe: "5000,00",
    componente: "ordinaria",
    motivo: "  Faltó la expensa de julio  ",
    ...campos,
  };
  for (const [clave, valor] of Object.entries(base)) datos.append(clave, valor);
  return datos;
}

describe("ajustarSaldoInicialAction", () => {
  beforeEach(() => {
    ajustarSaldoInicial.mockReset();
    revalidatePath.mockReset();
  });

  it("pasa el importe con punto y dos decimales, el concepto, el motivo y la operación", async () => {
    const datos = { importe: "5000.00", motivo: "Faltó la expensa de julio" };
    ajustarSaldoInicial.mockResolvedValue({ estado: "ok", datos });
    const estado = await ajustarSaldoInicialAction(EDIFICIO, UNIDAD, null, formulario());
    expect(ajustarSaldoInicial).toHaveBeenCalledWith(EDIFICIO, UNIDAD, {
      operacion_id: OPERACION,
      importe: "5000.00",
      componente: "ordinaria",
      motivo: "Faltó la expensa de julio",
    });
    expect(estado?.ajustado).toBe(datos);
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${EDIFICIO}/unidades`);
  });

  it.each([
    ["5000", "5000.00"],
    ["5000,5", "5000.50"],
    ["0,05", "0.05"],
  ])("el importe %s viaja como %s", async (escrito, enviado) => {
    ajustarSaldoInicial.mockResolvedValue({ estado: "ok", datos: {} });
    await ajustarSaldoInicialAction(EDIFICIO, UNIDAD, null, formulario({ importe: escrito }));
    expect(ajustarSaldoInicial.mock.calls[0]?.[2].importe).toBe(enviado);
  });

  it.each([
    ["importe", ""],
    ["importe", "mil"],
    ["importe", "0,00"],
    ["importe", "-5,00"],
    ["importe", "1,234"],
    ["motivo", "   "],
    ["motivo", "x".repeat(501)],
    ["componente", "interes"],
  ])("%s %j no llama a la API y lo dice en su campo", async (campo, valor) => {
    const estado = await ajustarSaldoInicialAction(
      EDIFICIO,
      UNIDAD,
      null,
      formulario({ [campo]: valor }),
    );
    expect(ajustarSaldoInicial).not.toHaveBeenCalled();
    expect(Object.keys(estado?.erroresPorCampo ?? {})).toEqual([campo]);
  });

  it("sin operacion_id no llama a la API", async () => {
    const estado = await ajustarSaldoInicialAction(
      EDIFICIO,
      UNIDAD,
      null,
      formulario({ operacion_id: "" }),
    );
    expect(estado?.error).toBe("No pudimos leer el pedido. Probá de nuevo.");
    expect(ajustarSaldoInicial).not.toHaveBeenCalled();
  });

  it.each([
    [
      { estado: "sin_permiso", permiso: "ajustar_saldo_inicial" },
      "No podés ajustar saldos en este edificio.",
    ],
    [
      { estado: "conflicto", campo: "estado_migracion" },
      "Los saldos iniciales de este edificio todavía no están confirmados.",
    ],
    [
      { estado: "conflicto", campo: "operacion_id" },
      "Este pedido ya se registró con otros datos. Volvé a cargar la pantalla.",
    ],
    [{ estado: "no_existe" }, "Esta unidad ya no existe o no tenés acceso."],
    [{ estado: "sin_sesion" }, "Tu sesión expiró. Iniciá sesión de nuevo."],
    [{ estado: "fallo" }, "No pudimos registrar el ajuste. Probá de nuevo."],
  ])("%j muestra %s", async (resultado, mensaje) => {
    ajustarSaldoInicial.mockResolvedValue(resultado);
    const estado = await ajustarSaldoInicialAction(EDIFICIO, UNIDAD, null, formulario());
    expect(estado?.error).toBe(mensaje);
    expect(estado?.ajustado).toBeUndefined();
  });

  it("un 422 del servidor queda en el campo que nombra", async () => {
    ajustarSaldoInicial.mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: "importe", motivo: "value_error" }],
    });
    const estado = await ajustarSaldoInicialAction(EDIFICIO, UNIDAD, null, formulario());
    expect(Object.keys(estado?.erroresPorCampo ?? {})).toEqual(["importe"]);
  });
});
