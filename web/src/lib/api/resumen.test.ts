import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resumenDelEdificio } from "./resumen";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("resumenDelEdificio", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("pide GET /api/complejos/{id}/resumen", async () => {
    const fetchFalso = mockFetch({
      status: 200,
      cuerpo: { informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" } },
    });
    vi.stubGlobal("fetch", fetchFalso);
    await resumenDelEdificio(EDIFICIO);
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/resumen`,
    );
  });

  it("si informe.suma no es texto decimal, da fallo (D2: la web no calcula sobre un dato roto)", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 200,
        cuerpo: { informe: { suma: "no-es-decimal", diferencia: "0.000000", estado: "ok" } },
      }),
    );
    expect(await resumenDelEdificio(EDIFICIO)).toEqual({ estado: "fallo" });
  });

  it("R3C-2 · con un id que no es UUID (podría venir de params.id de la URL) da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await resumenDelEdificio("..%2F..%2Fsalud")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
