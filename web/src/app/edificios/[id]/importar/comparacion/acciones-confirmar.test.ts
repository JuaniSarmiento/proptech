import { beforeEach, describe, expect, it, vi } from "vitest";

const confirmarSaldos = vi.fn();
const revalidatePath = vi.fn();
vi.mock("next/cache", () => ({ revalidatePath: (...args: unknown[]) => revalidatePath(...args) }));
vi.mock("../../../../../lib/api/importaciones", () => ({
  confirmarSaldos: (...args: unknown[]) => confirmarSaldos(...args),
}));

import { confirmarSaldosAction } from "./acciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const IMPORTACION = "22222222-2222-2222-2222-222222222222";

function formulario(importacion: string | null): FormData {
  const datos = new FormData();
  if (importacion !== null) datos.append("importacion_id", importacion);
  return datos;
}

describe("confirmarSaldosAction", () => {
  beforeEach(() => {
    confirmarSaldos.mockReset();
    revalidatePath.mockReset();
  });

  it("sin importacion_id no llama a la API", async () => {
    const estado = await confirmarSaldosAction(EDIFICIO, null, formulario(null));
    expect(estado?.error).toBe("No pudimos leer el pedido. Probá de nuevo.");
    expect(confirmarSaldos).not.toHaveBeenCalled();
  });

  it("confirmada devuelve la confirmación y revalida el resumen, no la comparación", async () => {
    const datos = { importacion_id: IMPORTACION, estado_migracion: "confirmada" };
    confirmarSaldos.mockResolvedValue({ estado: "ok", datos });
    const estado = await confirmarSaldosAction(EDIFICIO, null, formulario(IMPORTACION));
    expect(estado?.confirmada).toBe(datos);
    expect(confirmarSaldos).toHaveBeenCalledWith(EDIFICIO, IMPORTACION);
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${EDIFICIO}`);
    expect(revalidatePath).not.toHaveBeenCalledWith(`/edificios/${EDIFICIO}/importar/comparacion`);
  });

  it.each([
    [{ estado: "sin_permiso", permiso: "x" }, "No podés confirmar saldos en este edificio."],
    [
      { estado: "conflicto", campo: "diferencias" },
      "Hay diferencias sin aceptar. Aceptalas antes de confirmar.",
    ],
    [
      { estado: "conflicto", campo: "importacion_id" },
      "Este borrador ya no es el vigente: se subió un archivo nuevo. Volvé a cargar la pantalla.",
    ],
    [
      { estado: "conflicto", campo: "saldos" },
      "El archivo no trae saldos: no hay nada que confirmar.",
    ],
    [
      { estado: "conflicto", campo: "estado_migracion" },
      "Los saldos de este edificio ya están resueltos: no se pueden confirmar de nuevo.",
    ],
    [{ estado: "no_existe" }, "Este edificio ya no existe o no tenés acceso."],
    [
      { estado: "invalido", errores: [{ campo: "fecha_de_migracion", motivo: "value_error" }] },
      "La fecha de migración no es válida. Subí el archivo de nuevo con otra fecha.",
    ],
    [
      { estado: "invalido", errores: [{ campo: "vencimiento", motivo: "value_error" }] },
      "El libro no acepta algún dato del archivo. Subí el archivo de nuevo.",
    ],
    [{ estado: "sin_sesion" }, "Tu sesión expiró. Iniciá sesión de nuevo."],
    [{ estado: "fallo" }, "No pudimos confirmar los saldos. Probá de nuevo."],
  ])(
    "%j se explica en castellano simple y no devuelve una confirmación",
    async (resultado, mensaje) => {
      confirmarSaldos.mockResolvedValue(resultado);
      const estado = await confirmarSaldosAction(EDIFICIO, null, formulario(IMPORTACION));
      expect(estado?.error).toBe(mensaje);
      expect(estado?.confirmada).toBeUndefined();
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );
});
