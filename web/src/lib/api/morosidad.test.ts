import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { excelDeLaMorosidad, morosidadDelEdificio } from "./morosidad";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";

const FILA = {
  unidad_id: "22222222-2222-2222-2222-222222222222",
  unidad: "1A",
  propietarios: ["Ana Prueba"],
  etiqueta: "moroso_critico",
  total_vencido: "30812.34",
  capital: "30000.00",
  intereses: "812.34",
  liquidaciones_vencidas: 3,
  vencida_desde: "2026-09-10",
  dias: 69,
};
const CUERPO = {
  fecha: "2026-11-18",
  intereses_al: "2026-10-31",
  resumen: { unidades_con_deuda: 1, morosos_criticos: 1, total_vencido: "30812.34" },
  unidades: [FILA],
};

function mockFetch(respuesta: {
  status: number;
  cuerpo?: unknown;
  bytes?: ArrayBuffer;
  disposicion?: string;
}) {
  const f = vi.fn().mockResolvedValue({
    status: respuesta.status,
    headers: new Headers(
      respuesta.disposicion ? { "content-disposition": respuesta.disposicion } : {},
    ),
    json: async () => respuesta.cuerpo,
    arrayBuffer: async () => respuesta.bytes ?? new ArrayBuffer(0),
  } as unknown as Response);
  vi.stubGlobal("fetch", f);
  return f;
}

beforeEach(() => {
  process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
});
afterEach(() => {
  vi.unstubAllGlobals();
  delete process.env.PROPTECH_URL_API_INTERNA;
});

describe("morosidadDelEdificio", () => {
  it("lee la morosidad del edificio tal como la manda la API", async () => {
    const f = mockFetch({ status: 200, cuerpo: CUERPO });
    const r = await morosidadDelEdificio(EDIFICIO);
    expect(r).toEqual({ estado: "ok", datos: CUERPO });
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/morosidad`,
    );
  });

  it("un 403 es sin_permiso con el permiso que falta", async () => {
    mockFetch({
      status: 403,
      cuerpo: { detail: { codigo: "sin_permiso", permiso_faltante: "ver_morosidad" } },
    });
    expect(await morosidadDelEdificio(EDIFICIO)).toEqual({
      estado: "sin_permiso",
      permiso: "ver_morosidad",
    });
  });

  it("un id que no es UUID es no_existe, sin pedido", async () => {
    const f = mockFetch({ status: 200, cuerpo: CUERPO });
    expect(await morosidadDelEdificio("../x")).toEqual({ estado: "no_existe" });
    expect(f).not.toHaveBeenCalled();
  });

  it.each([
    ["un monto que no es texto con dos decimales", { ...FILA, capital: 30000 }],
    ["una etiqueta desconocida", { ...FILA, etiqueta: "otra" }],
    ["unos propietarios que no son una lista", { ...FILA, propietarios: "Ana" }],
  ])("%s es fallo, nunca un ok que no se sabría mostrar", async (_nombre, fila) => {
    mockFetch({ status: 200, cuerpo: { ...CUERPO, unidades: [fila] } });
    expect(await morosidadDelEdificio(EDIFICIO)).toEqual({ estado: "fallo" });
  });

  it("un total del resumen que no es plata es fallo", async () => {
    mockFetch({
      status: 200,
      cuerpo: { ...CUERPO, resumen: { ...CUERPO.resumen, total_vencido: "mucho" } },
    });
    expect(await morosidadDelEdificio(EDIFICIO)).toEqual({ estado: "fallo" });
  });
});

describe("excelDeLaMorosidad", () => {
  it("devuelve los bytes y el Content-Disposition de la API", async () => {
    const bytes = new Uint8Array([0x50, 0x4b, 3, 4]).buffer;
    const f = mockFetch({
      status: 200,
      bytes,
      disposicion: 'attachment; filename="morosidad-torre-2026-11-18.xlsx"',
    });
    const r = await excelDeLaMorosidad(EDIFICIO);
    expect(r).toEqual({
      estado: "ok",
      datos: { bytes, disposicion: 'attachment; filename="morosidad-torre-2026-11-18.xlsx"' },
    });
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/morosidad/excel`,
    );
  });

  it("un 403 es sin_permiso y un id inválido es no_existe sin pedido", async () => {
    const f = mockFetch({
      status: 403,
      cuerpo: { detail: { codigo: "sin_permiso", permiso_faltante: "exportar_morosidad" } },
    });
    expect(await excelDeLaMorosidad(EDIFICIO)).toEqual({
      estado: "sin_permiso",
      permiso: "exportar_morosidad",
    });
    f.mockClear();
    expect(await excelDeLaMorosidad("x")).toEqual({ estado: "no_existe" });
    expect(f).not.toHaveBeenCalled();
  });
});
