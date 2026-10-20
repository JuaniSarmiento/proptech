import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  categoriasDelEdificio,
  crearCategoria,
  editarCategoria,
  reordenarCategorias,
} from "./categorias";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("categoriasDelEdificio / crearCategoria / editarCategoria / reordenarCategorias", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("categoriasDelEdificio pide GET /api/complejos/{id}/categorias", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: [] });
    vi.stubGlobal("fetch", fetchFalso);
    await categoriasDelEdificio("1");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      "http://api-interna:8000/api/complejos/1/categorias",
    );
  });

  it("crearCategoria manda POST con clave y nombre", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "c1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await crearCategoria("e1", { clave: "ascensor", nombre: "Ascensor" });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos/e1/categorias");
    expect(llamada?.[1]?.method).toBe("POST");
  });

  it("crearCategoria con 409 da conflicto con el campo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 409, cuerpo: { detail: "conflicto", campo: "clave" } }),
    );
    expect(await crearCategoria("e1", { clave: "ascensor", nombre: "Ascensor" })).toEqual({
      estado: "conflicto",
      campo: "clave",
    });
  });

  it("editarCategoria manda PATCH a /api/categorias/{id} con los cambios parciales", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "c1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await editarCategoria("c1", { activa: false });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/categorias/c1");
    expect(llamada?.[1]?.method).toBe("PATCH");
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({ activa: false });
  });

  it("reordenarCategorias manda PUT con el orden completo", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "e1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await reordenarCategorias("e1", ["c2", "c1", "c3"]);
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos/e1/categorias/orden");
    expect(llamada?.[1]?.method).toBe("PUT");
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({ orden: ["c2", "c1", "c3"] });
  });
});
