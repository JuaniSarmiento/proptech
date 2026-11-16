import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PRELIQUIDACION } from "../test/preliquidacion";
import {
  liquidacionEmitida,
  preliquidacionDelPeriodo,
  registrarCargoCobradoDeMenos,
} from "./liquidaciones";

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

describe("liquidacionEmitida y registrarCargoCobradoDeMenos (H-017)", () => {
  const LIQUIDACION = "22222222-2222-2222-2222-222222222222";
  const UNIDAD = "33333333-3333-3333-3333-333333333333";
  const OBLIGACION = "44444444-4444-4444-4444-444444444444";
  const unidadBien = {
    unidad_id: UNIDAD,
    identificador: "1A",
    ordinaria: "27000.00",
    fondo_de_reserva: "1350.00",
    extraordinaria: "15000.00",
    cargos_particulares: [],
    intereses: "0.00",
    saldo_anterior: "0.00",
    total: "43350.00",
    sin_obligacion: false,
    obligacion_id: OBLIGACION,
  };

  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("lee GET .../liquidaciones/{id} con lo que paga cada unidad", async () => {
    const cuerpo = { liquidacion_id: LIQUIDACION, unidades: [unidadBien] };
    const fetchFalso = mockFetch({ status: 200, cuerpo });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await liquidacionEmitida(EDIFICIO, LIQUIDACION);
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}`,
    );
    expect(resultado).toEqual({ estado: "ok", datos: cuerpo });
  });

  it("una unidad sin obligación llega con obligacion_id null", async () => {
    const cuerpo = { unidades: [{ ...unidadBien, obligacion_id: null, sin_obligacion: true }] };
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo }));
    expect((await liquidacionEmitida(EDIFICIO, LIQUIDACION)).estado).toBe("ok");
  });

  it.each([
    ["un importe que no es texto con dos decimales", { ...unidadBien, total: "43350" }],
    ["un saldo anterior numérico", { ...unidadBien, saldo_anterior: 0 }],
    ["una obligación que no es UUID", { ...unidadBien, obligacion_id: "x" }],
  ])("%s es fallo", async (_nombre, unidad) => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: { unidades: [unidad] } }));
    expect(await liquidacionEmitida(EDIFICIO, LIQUIDACION)).toEqual({ estado: "fallo" });
  });

  it("un id que no es UUID es no_existe, sin pedido", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await liquidacionEmitida("no", LIQUIDACION)).toEqual({ estado: "no_existe" });
    expect(await liquidacionEmitida(EDIFICIO, "no")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("el cargo cobrado de menos es un POST a la unidad con el cuerpo tal cual", async () => {
    const pedido = {
      operacion_id: "55555555-5555-5555-5555-555555555555",
      obligacion_origen_id: OBLIGACION,
      importe: "1500.00",
      componente: "ordinaria",
      motivo: "Faltó cobrar el portón",
    };
    const registrado = {
      cargo_id: "66666666-6666-6666-6666-666666666666",
      obligacion_id: "77777777-7777-7777-7777-777777777777",
      importe: "1500.00",
      componente: "ordinaria",
      motivo: "Faltó cobrar el portón",
    };
    const fetchFalso = mockFetch({ status: 201, cuerpo: registrado });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await registrarCargoCobradoDeMenos(EDIFICIO, UNIDAD, pedido);
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/unidades/${UNIDAD}/cargos-cobrados-de-menos`,
    );
    expect(opciones?.method).toBe("POST");
    expect(JSON.parse(String(opciones?.body))).toEqual(pedido);
    expect(resultado).toEqual({ estado: "ok", datos: registrado });
  });

  it("un id que no es UUID es no_existe, sin pedido", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    const pedido = {
      operacion_id: "x",
      obligacion_origen_id: "x",
      importe: "1.00",
      componente: "ordinaria",
      motivo: "m",
    };
    expect(await registrarCargoCobradoDeMenos("no", UNIDAD, pedido)).toEqual({
      estado: "no_existe",
    });
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
