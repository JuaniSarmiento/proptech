import { beforeEach, describe, expect, it, vi } from "vitest";

const importarPadron = vi.fn();
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("../../../../lib/api/importaciones", () => ({
  importarPadron: (...args: unknown[]) => importarPadron(...args),
}));

import { importarPadronAction } from "./acciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";

function formulario(archivo: File | null, fecha: string | null): FormData {
  const datos = new FormData();
  if (archivo) datos.append("archivo", archivo);
  if (fecha !== null) datos.append("fecha_de_migracion", fecha);
  return datos;
}

const ARCHIVO = new File(["PK"], "padron.xlsx");

describe("importarPadronAction", () => {
  beforeEach(() => importarPadron.mockReset());

  it("sin archivo o sin fecha, avisa en el campo y no llama a la API", async () => {
    const estado = await importarPadronAction(EDIFICIO, null, formulario(null, ""));
    expect(estado?.erroresPorCampo).toEqual({
      archivo: "Elegí el archivo de Excel.",
      fecha_de_migracion: "Elegí la fecha de migración.",
    });
    expect(importarPadron).not.toHaveBeenCalled();
  });

  it("aceptada devuelve el resumen", async () => {
    const datos = { unidades_creadas: 12 };
    importarPadron.mockResolvedValue({ estado: "ok", datos });
    const estado = await importarPadronAction(EDIFICIO, null, formulario(ARCHIVO, "2026-10-15"));
    expect(estado?.aceptada).toBe(datos);
    expect(importarPadron).toHaveBeenCalledWith(EDIFICIO, ARCHIVO, "2026-10-15");
  });

  it("rechazada devuelve los errores del archivo tal cual", async () => {
    const errores = [{ hoja: "Unidades", fila: 9, columna: "Piso", motivo: "x" }];
    importarPadron.mockResolvedValue({ estado: "rechazado", errores });
    const estado = await importarPadronAction(EDIFICIO, null, formulario(ARCHIVO, "2026-10-15"));
    expect(estado?.rechazo).toEqual(errores);
  });

  it.each([
    [{ estado: "sin_permiso", permiso: "x" }, "No podés importar en este edificio."],
    [{ estado: "conflicto", campo: "archivo" }, "Este archivo ya se importó en este edificio."],
    [{ estado: "fallo" }, "No pudimos importar el archivo. Probá de nuevo."],
  ])("%j se explica en castellano simple", async (resultado, mensaje) => {
    importarPadron.mockResolvedValue(resultado);
    const estado = await importarPadronAction(EDIFICIO, null, formulario(ARCHIVO, "2026-10-15"));
    expect(estado?.erroresDesconocidos).toEqual([mensaje]);
  });

  it("una fecha rechazada por la API queda en su campo", async () => {
    importarPadron.mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: "fecha_de_migracion", motivo: "value_error" }],
    });
    const estado = await importarPadronAction(EDIFICIO, null, formulario(ARCHIVO, "2999-01-01"));
    expect(Object.keys(estado?.erroresPorCampo ?? {})).toEqual(["fecha_de_migracion"]);
  });
});
