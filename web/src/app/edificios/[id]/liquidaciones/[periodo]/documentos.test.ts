import { beforeEach, describe, expect, it, vi } from "vitest";

const { reprocesarDocumentos, enlaceDelDocumento, revalidatePath } = vi.hoisted(() => ({
  reprocesarDocumentos: vi.fn(),
  enlaceDelDocumento: vi.fn(),
  revalidatePath: vi.fn(),
}));
vi.mock("../../../../../lib/api/documentos", async () => ({
  ...(await vi.importActual<object>("../../../../../lib/api/documentos")),
  reprocesarDocumentos,
  enlaceDelDocumento,
}));
vi.mock("next/cache", () => ({ revalidatePath }));

import { descargarDocumentoAction, reprocesarDocumentosAction } from "./documentos";

const ID = "11111111-1111-1111-1111-111111111111";
const LIQUIDACION = "22222222-2222-2222-2222-222222222222";
const DOCUMENTO = "33333333-3333-3333-3333-333333333333";
const TOKEN = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

function formulario(campos: Record<string, string>): FormData {
  const datos = new FormData();
  for (const [clave, valor] of Object.entries(campos)) datos.append(clave, valor);
  return datos;
}

beforeEach(() => {
  reprocesarDocumentos.mockReset();
  enlaceDelDocumento.mockReset();
  revalidatePath.mockReset();
});

describe("reprocesarDocumentosAction", () => {
  it("reprocesa, dice cuántos se encolaron y revalida el edificio", async () => {
    reprocesarDocumentos.mockResolvedValue({ estado: "ok", datos: { encolados: 2 } });
    const estado = await reprocesarDocumentosAction(ID, LIQUIDACION, null, new FormData());
    expect(estado).toEqual({ encolados: 2 });
    expect(reprocesarDocumentos).toHaveBeenCalledWith(ID, LIQUIDACION);
    expect(revalidatePath).toHaveBeenCalledWith(`/edificios/${ID}`);
  });

  it.each([
    [{ estado: "sin_permiso", permiso: "emitir_y_distribuir_liquidacion" }, /No podés reprocesar/],
    [{ estado: "no_existe" }, /ya no existe/],
    [{ estado: "fallo" }, /No pudimos reprocesar/],
  ])("%j se dice con su mensaje y no revalida", async (resultado, mensaje) => {
    reprocesarDocumentos.mockResolvedValue(resultado);
    const estado = await reprocesarDocumentosAction(ID, LIQUIDACION, null, new FormData());
    expect(estado?.error).toMatch(mensaje);
    expect(revalidatePath).not.toHaveBeenCalled();
  });
});

describe("descargarDocumentoAction", () => {
  it("pide el enlace y devuelve la ruta de descarga de la web, no la de la API", async () => {
    enlaceDelDocumento.mockResolvedValue({
      estado: "ok",
      datos: { url: `/api/documentos/descarga?token=${TOKEN}`, vence_en: "2026-11-02T15:15:00Z" },
    });
    const estado = await descargarDocumentoAction(
      ID,
      null,
      formulario({ documento_id: DOCUMENTO, variante: "completa" }),
    );
    expect(enlaceDelDocumento).toHaveBeenCalledWith(ID, DOCUMENTO, "completa");
    expect(estado?.ruta).toBe(`/documentos/descarga?token=${TOKEN}`);
    expect(estado?.error).toBeUndefined();
  });

  it("una dirección que no es la esperada no se entrega", async () => {
    enlaceDelDocumento.mockResolvedValue({
      estado: "ok",
      datos: { url: "https://otro.example/x", vence_en: "2026-11-02T15:15:00Z" },
    });
    const estado = await descargarDocumentoAction(
      ID,
      null,
      formulario({ documento_id: DOCUMENTO, variante: "completa" }),
    );
    expect(estado?.ruta).toBeUndefined();
    expect(estado?.error).toMatch(/No pudimos preparar la descarga/);
  });

  it.each([
    [{ estado: "sin_permiso", permiso: "x" }, /No podés descargar/],
    [
      { estado: "conflicto", campo: "documento", motivo: "no_generado" },
      /todavía no está generado/,
    ],
    [{ estado: "no_existe" }, /ya no existe/],
    [{ estado: "fallo" }, /No pudimos preparar/],
  ])("%j se dice con su mensaje", async (resultado, mensaje) => {
    enlaceDelDocumento.mockResolvedValue(resultado);
    const estado = await descargarDocumentoAction(
      ID,
      null,
      formulario({ documento_id: DOCUMENTO, variante: "completa" }),
    );
    expect(estado?.error).toMatch(mensaje);
  });
});
