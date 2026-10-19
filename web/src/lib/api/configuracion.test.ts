import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configuracionVigente } from "./configuracion";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("configuracionVigente", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("pide GET /api/complejos/{id}/configuracion", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: null });
    vi.stubGlobal("fetch", fetchFalso);
    await configuracionVigente("1");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      "http://api-interna:8000/api/complejos/1/configuracion",
    );
  });

  it("un edificio sin configuración vigente da ok con datos null (no fallo)", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: null }));
    expect(await configuracionVigente("1")).toEqual({ estado: "ok", datos: null });
  });
});
