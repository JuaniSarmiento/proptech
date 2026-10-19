import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { crearEdificio, edificioPorId, listaDeEdificios } from "./edificios";

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
    await edificioPorId("1");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api-interna:8000/api/complejos/1");
  });

  it("crearEdificio manda POST con nombre y localidad", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "nuevo" } });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await crearEdificio({ nombre: "Edificio X", localidad: "Mendoza" });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos");
    expect(llamada?.[1]?.method).toBe("POST");
    expect(JSON.parse(llamada?.[1]?.body as string)).toEqual({
      nombre: "Edificio X",
      localidad: "Mendoza",
    });
    expect(resultado).toEqual({ estado: "ok", datos: { id: "nuevo" } });
  });

  it("crearEdificio con 403 da sin_permiso (colaborador sin permiso de crear)", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 403,
        cuerpo: { detail: { permiso_faltante: "crear_edificio" } },
      }),
    );
    expect(await crearEdificio({ nombre: "X", localidad: "Y" })).toEqual({
      estado: "sin_permiso",
      permiso: "crear_edificio",
    });
  });
});
