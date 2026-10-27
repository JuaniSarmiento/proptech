import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  confirmarSinSaldosPrevios,
  crearEdificio,
  edificioPorId,
  listaDeEdificios,
} from "./edificios";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("listaDeEdificios / edificioPorId / crearEdificio", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("listaDeEdificios pide GET /api/complejos", async () => {
    const fetchFalso = mockFetch({
      status: 200,
      cuerpo: [{ id: "1", nombre: "A", localidad: "M" }],
    });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await listaDeEdificios();
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api-interna:8000/api/complejos");
    expect(resultado).toEqual({
      estado: "ok",
      datos: [{ id: "1", nombre: "A", localidad: "M" }],
    });
  });

  it("edificioPorId pide GET /api/complejos/{id}", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await edificioPorId("11111111-1111-1111-1111-111111111111");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      "http://api-interna:8000/api/complejos/11111111-1111-1111-1111-111111111111",
    );
  });

  it("R3C-2 · edificioPorId con un id que no es UUID da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await edificioPorId("../../salud")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("crearEdificio manda POST con el trío de ubicación, pisos y subsuelos (D3)", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "nuevo" } });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await crearEdificio({
      nombre: "Edificio X",
      provincia_id: "50",
      departamento_id: "50007",
      localidad_id: "50007010",
      pisos: 4,
      subsuelos: 1,
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos");
    expect(llamada?.[1]?.method).toBe("POST");
    expect(JSON.parse(llamada?.[1]?.body as string)).toEqual({
      nombre: "Edificio X",
      provincia_id: "50",
      departamento_id: "50007",
      localidad_id: "50007010",
      pisos: 4,
      subsuelos: 1,
    });
    expect(resultado).toEqual({ estado: "ok", datos: { id: "nuevo" } });
  });

  it("crearEdificio con 403 da sin_permiso (administrador sin permiso de crear)", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 403,
        cuerpo: { detail: { permiso_faltante: "crear_edificio" } },
      }),
    );
    expect(
      await crearEdificio({
        nombre: "X",
        provincia_id: "50",
        departamento_id: "50007",
        localidad_id: "50007010",
        pisos: 4,
        subsuelos: 1,
      }),
    ).toEqual({
      estado: "sin_permiso",
      permiso: "crear_edificio",
    });
  });

  it("confirmarSinSaldosPrevios manda POST sin cuerpo a estado-de-migracion/sin-saldos-previos", async () => {
    const fetchFalso = mockFetch({
      status: 200,
      cuerpo: { id: "1", estado_migracion: "sin_saldos_previos" },
    });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await confirmarSinSaldosPrevios("11111111-1111-1111-1111-111111111111");
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe(
      "http://api-interna:8000/api/complejos/11111111-1111-1111-1111-111111111111/estado-de-migracion/sin-saldos-previos",
    );
    expect(llamada?.[1]?.method).toBe("POST");
    expect(resultado).toEqual({
      estado: "ok",
      datos: { id: "1", estado_migracion: "sin_saldos_previos" },
    });
  });

  it("confirmarSinSaldosPrevios con 409 da conflicto (otro lo confirmó en el medio)", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 409, cuerpo: { detail: "conflicto", campo: "estado_migracion" } }),
    );
    expect(await confirmarSinSaldosPrevios("11111111-1111-1111-1111-111111111111")).toEqual({
      estado: "conflicto",
      campo: "estado_migracion",
    });
  });

  it("R3C-2 · confirmarSinSaldosPrevios con un id que no es UUID da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await confirmarSinSaldosPrevios("1")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
