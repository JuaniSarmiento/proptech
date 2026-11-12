import { beforeEach, describe, expect, it, vi } from "vitest";

const aceptarDiferencias = vi.fn();
const revalidatePath = vi.fn();
vi.mock("next/cache", () => ({ revalidatePath: (...args: unknown[]) => revalidatePath(...args) }));
vi.mock("../../../../../lib/api/importaciones", () => ({
  aceptarDiferencias: (...args: unknown[]) => aceptarDiferencias(...args),
}));

import { aceptarDiferenciasAction } from "./acciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const IMPORTACION = "22222222-2222-2222-2222-222222222222";

function formulario(importacion: string | null): FormData {
  const datos = new FormData();
  if (importacion !== null) datos.append("importacion_id", importacion);
  return datos;
}

describe("aceptarDiferenciasAction", () => {
  beforeEach(() => {
    aceptarDiferencias.mockReset();
    revalidatePath.mockReset();
  });

  it("sin importacion_id no llama a la API", async () => {
    const estado = await aceptarDiferenciasAction(EDIFICIO, null, formulario(null));
    expect(estado?.error).toBe("No pudimos leer el pedido. Probá de nuevo.");
    expect(aceptarDiferencias).not.toHaveBeenCalled();
  });

  it("aceptada devuelve la aceptación y revalida la comparación", async () => {
    const datos = { aceptacion_id: "a1", diferencias: [], aceptada_por: "p", aceptada_en: "x" };
    aceptarDiferencias.mockResolvedValue({ estado: "ok", datos });
    const estado = await aceptarDiferenciasAction(EDIFICIO, null, formulario(IMPORTACION));
    expect(estado?.aceptada).toBe(datos);
    expect(aceptarDiferencias).toHaveBeenCalledWith(EDIFICIO, IMPORTACION);
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${EDIFICIO}/importar/comparacion`);
  });

  it.each([
    [{ estado: "sin_permiso", permiso: "x" }, "No podés aceptar diferencias en este edificio."],
    [
      { estado: "conflicto", campo: "aceptacion" },
      "Estas diferencias ya fueron aceptadas. Volvé a cargar la pantalla.",
    ],
    [{ estado: "conflicto", campo: "diferencias" }, "No hay diferencias para aceptar."],
    [
      { estado: "conflicto", campo: "importacion_id" },
      "Este borrador ya no es el vigente: se subió un archivo nuevo. Volvé a cargar la pantalla.",
    ],
    [
      { estado: "conflicto", campo: "estado_migracion" },
      "Los saldos de este edificio ya están resueltos: no se pueden aceptar diferencias.",
    ],
    [{ estado: "no_existe" }, "Este edificio ya no existe o no tenés acceso."],
    [{ estado: "invalido", errores: [] }, "No pudimos leer el pedido. Probá de nuevo."],
    [{ estado: "fallo" }, "No pudimos aceptar las diferencias. Probá de nuevo."],
  ])(
    "%j se explica en castellano simple y no devuelve una aceptación",
    async (resultado, mensaje) => {
      aceptarDiferencias.mockResolvedValue(resultado);
      const estado = await aceptarDiferenciasAction(EDIFICIO, null, formulario(IMPORTACION));
      expect(estado?.error).toBe(mensaje);
      expect(estado?.aceptada).toBeUndefined();
      expect(revalidatePath).not.toHaveBeenCalled();
    },
  );
});
