import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { crearGrupo, editarGrupo, fijarMiembrosDeGrupo, gruposDelEdificio } from "./grupos";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("gruposDelEdificio / crearGrupo / editarGrupo / fijarMiembrosDeGrupo", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("gruposDelEdificio pide GET /api/complejos/{id}/grupos", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: [] });
    vi.stubGlobal("fetch", fetchFalso);
    await gruposDelEdificio("1");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api-interna:8000/api/complejos/1/grupos");
  });

  it("crearGrupo manda POST con clave, nombre, metodo, modo y unidades en el mismo pedido (D9)", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "g1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await crearGrupo("c1", {
      clave: "ascensor",
      nombre: "Ascensor",
      metodo: "coeficiente",
      modo_de_coeficientes: "renormalizado",
      unidades: [{ unidad_id: "u1", coeficiente: null }],
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos/c1/grupos");
    expect(llamada?.[1]?.method).toBe("POST");
  });

  it("editarGrupo manda PATCH a /api/grupos/{id} (D9: primer pedido, sólo datos)", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "g1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await editarGrupo("g1", { nombre: "Ascensor 2" });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/grupos/g1");
    expect(llamada?.[1]?.method).toBe("PATCH");
  });

  it("fijarMiembrosDeGrupo manda PUT a /api/grupos/{id}/unidades (D9: segundo pedido)", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "g1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await fijarMiembrosDeGrupo("g1", {
      modo_de_coeficientes: "propios",
      unidades: [{ unidad_id: "u1", coeficiente: "0.500000" }],
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/grupos/g1/unidades");
    expect(llamada?.[1]?.method).toBe("PUT");
  });
});
