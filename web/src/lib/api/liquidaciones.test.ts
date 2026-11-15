import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PRELIQUIDACION } from "../test/preliquidacion";
import { preliquidacionDelPeriodo } from "./liquidaciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

describe("preliquidacionDelPeriodo", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("pide GET .../periodos/AAAA-MM-01/preliquidacion y devuelve el cuerpo", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: PRELIQUIDACION });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await preliquidacionDelPeriodo(EDIFICIO, "2026-11-01");
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/periodos/2026-11-01/preliquidacion`,
    );
    expect(opciones?.method).toBe("GET");
    expect(resultado).toEqual({ estado: "ok", datos: PRELIQUIDACION });
  });

  it("un id que no es UUID o un período mal escrito es no_existe, sin pedido", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    for (const [id, periodo] of [
      ["no-es-un-id", "2026-11-01"],
      [EDIFICIO, "2026-11"],
      [EDIFICIO, "2026-11-05"],
      [EDIFICIO, "2026-13-01"],
      [EDIFICIO, "../2026-11-01"],
    ] as const) {
      expect(await preliquidacionDelPeriodo(id, periodo)).toEqual({ estado: "no_existe" });
    }
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("un 409 trae su motivo como código", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 409,
        cuerpo: { detail: "conflicto", campo: "periodo", motivo: "periodo_anterior_sin_emitir" },
      }),
    );
    expect(await preliquidacionDelPeriodo(EDIFICIO, "2026-11-01")).toEqual({
      estado: "conflicto",
      campo: "periodo",
      motivo: "periodo_anterior_sin_emitir",
    });
  });

  it("un monto que no es texto con dos decimales es fallo, nunca un ok que la pantalla no sabría mostrar", async () => {
    const unidad = PRELIQUIDACION.unidades[0];
    const categoria = PRELIQUIDACION.bloques.ordinario.categorias[0];
    for (const mala of [
      { ...PRELIQUIDACION, totales: { ...PRELIQUIDACION.totales, total: 191500 } },
      { ...PRELIQUIDACION, totales: { ...PRELIQUIDACION.totales, total: "191500" } },
      { ...PRELIQUIDACION, porcentaje_fondo: "5" },
      { ...PRELIQUIDACION, unidades: [{ ...unidad, total: 48350 }] },
      { ...PRELIQUIDACION, unidades: [{ ...unidad, fondo_de_reserva: "1350" }] },
      {
        ...PRELIQUIDACION,
        unidades: [{ ...unidad, cargos_particulares: [{ concepto: "x", importe: "5000" }] }],
      },
      {
        ...PRELIQUIDACION,
        bloques: {
          ...PRELIQUIDACION.bloques,
          ordinario: { subtotal: "130000.00", categorias: [{ ...categoria, porcentaje: "69,23" }] },
        },
      },
      { ...PRELIQUIDACION, grupos: [{ ...PRELIQUIDACION.grupos[0], ordinario: 90000 }] },
    ]) {
      vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: mala }));
      expect(await preliquidacionDelPeriodo(EDIFICIO, "2026-11-01")).toEqual({ estado: "fallo" });
    }
  });

  it("403 con el permiso que falta y 404 se pasan tal cual", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 403,
        cuerpo: {
          detail: {
            codigo: "sin_permiso",
            permiso_faltante: "cargar_gastos_y_preparar_liquidacion",
          },
        },
      }),
    );
    expect(await preliquidacionDelPeriodo(EDIFICIO, "2026-11-01")).toEqual({
      estado: "sin_permiso",
      permiso: "cargar_gastos_y_preparar_liquidacion",
    });
    vi.stubGlobal("fetch", mockFetch({ status: 404 }));
    expect(await preliquidacionDelPeriodo(EDIFICIO, "2026-11-01")).toEqual({
      estado: "no_existe",
    });
  });
});
