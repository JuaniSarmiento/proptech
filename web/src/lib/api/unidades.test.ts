import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { crearUnidad, editarUnidad, padronDelEdificio } from "./unidades";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("padronDelEdificio / crearUnidad / editarUnidad", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("padronDelEdificio pide GET /api/complejos/{id}/unidades", async () => {
    const fetchFalso = mockFetch({
      status: 200,
      cuerpo: { informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" }, unidades: [] },
    });
    vi.stubGlobal("fetch", fetchFalso);
    await padronDelEdificio("1");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api-interna:8000/api/complejos/1/unidades");
  });

  it("si informe.diferencia no es texto decimal, da fallo (la web no calcula sobre un dato roto)", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 200,
        cuerpo: { informe: { suma: "1.000000", diferencia: "no", estado: "ok" }, unidades: [] },
      }),
    );
    expect(await padronDelEdificio("1")).toEqual({ estado: "fallo" });
  });

  it("crearUnidad manda POST con los datos de la unidad", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "u1", identificador: "1A" } });
    vi.stubGlobal("fetch", fetchFalso);
    await crearUnidad("c1", {
      identificador: "1A",
      tipo: "departamento",
      piso: "1",
      coeficiente: "0.500000",
      superficie_m2: "60.00",
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos/c1/unidades");
    expect(llamada?.[1]?.method).toBe("POST");
  });

  it("crearUnidad con 409 da conflicto con el campo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 409, cuerpo: { detail: "conflicto", campo: "identificador" } }),
    );
    expect(
      await crearUnidad("c1", {
        identificador: "1A",
        tipo: "departamento",
        piso: "1",
        coeficiente: "0.500000",
        superficie_m2: "60.00",
      }),
    ).toEqual({ estado: "conflicto", campo: "identificador" });
  });

  it("editarUnidad manda PATCH a /api/unidades/{id}", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "u1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await editarUnidad("u1", { piso: "2" });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/unidades/u1");
    expect(llamada?.[1]?.method).toBe("PATCH");
  });
});
