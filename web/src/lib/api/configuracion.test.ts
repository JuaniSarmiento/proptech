import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  configuracionVigente,
  crearVersionDeConfiguracion,
  versionesDeConfiguracion,
} from "./configuracion";

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

describe("versionesDeConfiguracion / crearVersionDeConfiguracion", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("versionesDeConfiguracion pide GET /api/complejos/{id}/configuracion/versiones", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: [] });
    vi.stubGlobal("fetch", fetchFalso);
    await versionesDeConfiguracion("1");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      "http://api-interna:8000/api/complejos/1/configuracion/versiones",
    );
  });

  it("crearVersionDeConfiguracion manda POST con los datos de la versión", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "v1" } });
    vi.stubGlobal("fetch", fetchFalso);
    await crearVersionDeConfiguracion("e1", {
      tasa_mensual: "3.00",
      dias_de_gracia: 0,
      forma_de_calculo: "proporcional_por_dia",
      porcentaje_fondo: "0.00",
      dia_de_vencimiento: 10,
      modalidad_de_vencimiento: "unico",
      dia_segundo_vencimiento: null,
      recargo_segundo_vencimiento: null,
      vigente_desde: "2026-10-20",
    });
    const llamada = fetchFalso.mock.calls[0];
    expect(llamada?.[0]).toBe("http://api-interna:8000/api/complejos/e1/configuracion/versiones");
    expect(llamada?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({
      tasa_mensual: "3.00",
      dias_de_gracia: 0,
      forma_de_calculo: "proporcional_por_dia",
      porcentaje_fondo: "0.00",
      dia_de_vencimiento: 10,
      modalidad_de_vencimiento: "unico",
      dia_segundo_vencimiento: null,
      recargo_segundo_vencimiento: null,
      vigente_desde: "2026-10-20",
    });
  });

  it("crearVersionDeConfiguracion con 422 da inválido con el campo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 422,
        cuerpo: { detail: [{ loc: ["body", "vigente_desde"], type: "value_error" }] },
      }),
    );
    expect(
      await crearVersionDeConfiguracion("e1", {
        tasa_mensual: "3.00",
        dias_de_gracia: 0,
        forma_de_calculo: "proporcional_por_dia",
        porcentaje_fondo: "0.00",
        dia_de_vencimiento: 10,
        modalidad_de_vencimiento: "unico",
        dia_segundo_vencimiento: null,
        recargo_segundo_vencimiento: null,
        vigente_desde: "2026-10-01",
      }),
    ).toEqual({
      estado: "invalido",
      errores: [{ campo: "vigente_desde", motivo: "value_error" }],
    });
  });
});
