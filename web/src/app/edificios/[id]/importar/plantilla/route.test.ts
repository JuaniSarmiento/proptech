import { beforeEach, describe, expect, it, vi } from "vitest";

const plantillaDelPadron = vi.fn();
vi.mock("../../../../../lib/api/importaciones", () => ({
  plantillaDelPadron: (...args: unknown[]) => plantillaDelPadron(...args),
}));

import { GET } from "./route";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const contexto = { params: Promise.resolve({ id: EDIFICIO }) };

describe("GET /edificios/{id}/importar/plantilla", () => {
  beforeEach(() => plantillaDelPadron.mockReset());

  it("entrega los bytes como plantilla-padron.xlsx para descargar", async () => {
    const bytes = new Uint8Array([0x50, 0x4b, 3, 4]).buffer;
    plantillaDelPadron.mockResolvedValue({ estado: "ok", datos: bytes });
    const respuesta = await GET(new Request("http://web/x"), contexto);
    expect(respuesta.status).toBe(200);
    expect(respuesta.headers.get("content-type")).toBe(
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    );
    expect(respuesta.headers.get("content-disposition")).toBe(
      'attachment; filename="plantilla-padron.xlsx"',
    );
    expect(new Uint8Array(await respuesta.arrayBuffer())).toEqual(new Uint8Array(bytes));
    expect(plantillaDelPadron).toHaveBeenCalledWith(EDIFICIO);
  });

  it.each([
    [{ estado: "sin_sesion" }, 401],
    [{ estado: "sin_permiso", permiso: "x" }, 403],
    [{ estado: "no_existe" }, 404],
    [{ estado: "fallo" }, 502],
  ])("%j da %i, sin cuerpo", async (resultado, estado) => {
    plantillaDelPadron.mockResolvedValue(resultado);
    const respuesta = await GET(new Request("http://web/x"), contexto);
    expect(respuesta.status).toBe(estado);
    expect(await respuesta.text()).toBe("");
  });
});
