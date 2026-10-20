import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { crearGrupo, editarGrupo, fijarMiembrosDeGrupo, gruposDelEdificio } from "./grupos";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const GRUPO = "44444444-4444-4444-4444-444444444444";

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
    await gruposDelEdificio(EDIFICIO);
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/grupos`,
    );
  });

  it("R3C-2 · gruposDelEdificio con un id que no es UUID da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await gruposDelEdificio("1")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("crearGrupo manda POST con clave, nombre, metodo, modo y unidades en el mismo pedido (D9)", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "g1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await crearGrupo(EDIFICIO, {
      clave: "ascensor",
      nombre: "Ascensor",
      metodo: "coeficiente",
      modo_de_coeficientes: "renormalizado",
      unidades: [{ unidad_id: "u1", coeficiente: null }],
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe(`http://api-interna:8000/api/complejos/${EDIFICIO}/grupos`);
    expect(llamada?.[1]?.method).toBe("POST");
  });

  it("editarGrupo manda PATCH a /api/grupos/{id} (D9: primer pedido, sólo datos)", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "g1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await editarGrupo(GRUPO, { nombre: "Ascensor 2" });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe(`http://api-interna:8000/api/grupos/${GRUPO}`);
    expect(llamada?.[1]?.method).toBe("PATCH");
  });

  it("R3C-2 · editarGrupo con un grupoId que no es UUID da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await editarGrupo("g1", { nombre: "Ascensor 2" })).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("fijarMiembrosDeGrupo manda PUT a /api/grupos/{id}/unidades (D9: segundo pedido)", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { id: "g1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await fijarMiembrosDeGrupo(GRUPO, {
      modo_de_coeficientes: "propios",
      unidades: [{ unidad_id: "u1", coeficiente: "0.500000" }],
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe(`http://api-interna:8000/api/grupos/${GRUPO}/unidades`);
    expect(llamada?.[1]?.method).toBe("PUT");
  });
});
