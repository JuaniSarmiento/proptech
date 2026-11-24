import { beforeEach, describe, expect, it, vi } from "vitest";

const excelDeLaMorosidad = vi.fn();
vi.mock("../../../../../lib/api/morosidad", () => ({
  excelDeLaMorosidad: (...args: unknown[]) => excelDeLaMorosidad(...args),
}));

import { GET } from "./route";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const contexto = { params: Promise.resolve({ id: EDIFICIO }) };
const bytes = new Uint8Array([0x50, 0x4b, 3, 4]).buffer;

describe("GET /edificios/{id}/morosidad/excel", () => {
  beforeEach(() => excelDeLaMorosidad.mockReset());

  it("entrega los bytes con el nombre de archivo que decidió la API, sin cachear", async () => {
    excelDeLaMorosidad.mockResolvedValue({
      estado: "ok",
      datos: {
        bytes,
        disposicion: 'attachment; filename="morosidad-torre-ficticia-2026-11-18.xlsx"',
      },
    });
    const respuesta = await GET(new Request("http://web/x"), contexto);
    expect(respuesta.status).toBe(200);
    expect(respuesta.headers.get("content-type")).toBe(
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    );
    expect(respuesta.headers.get("content-disposition")).toBe(
      'attachment; filename="morosidad-torre-ficticia-2026-11-18.xlsx"',
    );
    expect(respuesta.headers.get("cache-control")).toBe("no-store");
    expect(new Uint8Array(await respuesta.arrayBuffer())).toEqual(new Uint8Array(bytes));
    expect(excelDeLaMorosidad).toHaveBeenCalledWith(EDIFICIO);
  });

  it.each([[null], ['attachment; filename="../../x.xlsx"'], ['inline; filename="a.xlsx"']])(
    "sin una disposición segura (%s) baja como morosidad.xlsx",
    async (disposicion) => {
      excelDeLaMorosidad.mockResolvedValue({ estado: "ok", datos: { bytes, disposicion } });
      const respuesta = await GET(new Request("http://web/x"), contexto);
      expect(respuesta.headers.get("content-disposition")).toBe(
        'attachment; filename="morosidad.xlsx"',
      );
    },
  );

  it.each([
    [{ estado: "sin_sesion" }, 401],
    [{ estado: "sin_permiso", permiso: "exportar_morosidad" }, 403],
    [{ estado: "no_existe" }, 404],
    [{ estado: "fallo" }, 502],
  ])("%j da %i, sin cuerpo", async (resultado, estado) => {
    excelDeLaMorosidad.mockResolvedValue(resultado);
    const respuesta = await GET(new Request("http://web/x"), contexto);
    expect(respuesta.status).toBe(estado);
    expect(await respuesta.text()).toBe("");
  });
});
