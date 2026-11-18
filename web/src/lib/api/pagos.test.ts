import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  descargarComprobante,
  enlaceDelComprobante,
  informarPago,
  pagosDelEdificio,
  resolverPago,
  subirComprobante,
  tokenDelComprobante,
  unidadesParaInformar,
} from "./pagos";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const PAGO = "22222222-2222-2222-2222-222222222222";
const UNIDAD = "33333333-3333-3333-3333-333333333333";
const TOKEN = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

vi.mock("../sesion", () => ({
  sesionActual: async () => ({ token: "jwt", administracionId: undefined }),
  irAlIngreso: () => {
    throw new Error("sin sesión");
  },
}));

const PAGO_BIEN = {
  pago_id: PAGO,
  estado: "informado",
  motivo: null,
  banco: "Banco Nación",
  numero_de_operacion: "11110001",
  fecha_de_transferencia: "2026-11-05",
  monto: "43350.00",
  partes: [
    {
      unidad_id: UNIDAD,
      identificador: "1A",
      importe: "43350.00",
      unidad_vigente_id: UNIDAD,
      identificador_vigente: "1A",
    },
  ],
};

function mockFetch(respuesta: {
  status: number;
  cuerpo?: unknown;
  bytes?: ArrayBuffer;
  tipo?: string;
}) {
  const f = vi.fn().mockResolvedValue({
    status: respuesta.status,
    headers: new Headers(respuesta.tipo ? { "content-type": respuesta.tipo } : {}),
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

describe("pagosDelEdificio", () => {
  it("pide GET .../pagos y devuelve la lista", async () => {
    const f = mockFetch({ status: 200, cuerpo: [PAGO_BIEN] });
    const resultado = await pagosDelEdificio(EDIFICIO);
    expect(resultado).toEqual({ estado: "ok", datos: [PAGO_BIEN] });
    expect(f.mock.calls[0]?.[0]).toBe(`http://api-interna:8000/api/complejos/${EDIFICIO}/pagos`);
  });

  it("un id que no es UUID es 'no existe' y no llama a la API", async () => {
    const f = mockFetch({ status: 200, cuerpo: [] });
    expect(await pagosDelEdificio("../x")).toEqual({ estado: "no_existe" });
    expect(f).not.toHaveBeenCalled();
  });

  it("un pago con un estado desconocido es fallo, nunca un ok que la pantalla no sabría mostrar", async () => {
    mockFetch({ status: 200, cuerpo: [{ ...PAGO_BIEN, estado: "raro" }] });
    expect(await pagosDelEdificio(EDIFICIO)).toEqual({ estado: "fallo" });
  });

  it("un 403 llega como sin permiso", async () => {
    mockFetch({
      status: 403,
      cuerpo: { detail: { codigo: "sin_permiso", permiso_faltante: "informar_pago" } },
    });
    expect(await pagosDelEdificio(EDIFICIO)).toEqual({
      estado: "sin_permiso",
      permiso: "informar_pago",
    });
  });
});

describe("unidadesParaInformar", () => {
  it("pide GET .../pagos/unidades", async () => {
    const f = mockFetch({ status: 200, cuerpo: [{ unidad_id: UNIDAD, identificador: "1A" }] });
    const resultado = await unidadesParaInformar(EDIFICIO);
    expect(resultado.estado).toBe("ok");
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/pagos/unidades`,
    );
  });

  it("una unidad sin identificador es fallo", async () => {
    mockFetch({ status: 200, cuerpo: [{ unidad_id: UNIDAD }] });
    expect(await unidadesParaInformar(EDIFICIO)).toEqual({ estado: "fallo" });
  });
});

describe("subirComprobante", () => {
  it("manda el archivo por multipart y devuelve la propuesta, con lo que falta como null", async () => {
    const f = mockFetch({
      status: 201,
      cuerpo: {
        comprobante_id: PAGO,
        lectura: "ok",
        propuesta: { banco: "Banco Nación", monto: "100.00" },
      },
    });
    const resultado = await subirComprobante(EDIFICIO, new File(["x"], "c.png"));
    expect(resultado).toEqual({
      estado: "ok",
      datos: {
        comprobante_id: PAGO,
        lectura: "ok",
        propuesta: {
          banco: "Banco Nación",
          numero_de_operacion: null,
          fecha: null,
          monto: "100.00",
          cbu_origen: null,
        },
      },
    });
    const init = f.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/pagos/lectura`,
    );
  });

  it("una lectura con otra forma es fallo", async () => {
    mockFetch({ status: 201, cuerpo: { comprobante_id: PAGO, lectura: "rara", propuesta: {} } });
    expect(await subirComprobante(EDIFICIO, new File(["x"], "c.png"))).toEqual({
      estado: "fallo",
    });
  });
});

describe("informarPago y resolverPago", () => {
  it("informar manda el pedido tal cual, sin tocar ningún monto", async () => {
    const f = mockFetch({ status: 201, cuerpo: { pago_id: PAGO, estado: "informado" } });
    const pedido = {
      comprobante_id: PAGO,
      banco: "B",
      numero_de_operacion: "1",
      fecha_de_transferencia: "2026-11-05",
      monto: "43000.00",
      partes: [{ unidad_id: UNIDAD, importe: "43000.00" }],
    };
    await informarPago(EDIFICIO, pedido);
    const init = f.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual(pedido);
  });

  it("un 422 de partes llega con su campo", async () => {
    mockFetch({
      status: 422,
      cuerpo: { detail: [{ type: "value_error", loc: ["body", "partes"] }] },
    });
    const resultado = await informarPago(EDIFICIO, {
      comprobante_id: PAGO,
      banco: "B",
      numero_de_operacion: "1",
      fecha_de_transferencia: "2026-11-05",
      monto: "1.00",
      partes: [],
    });
    expect(resultado).toEqual({
      estado: "invalido",
      errores: [{ campo: "partes", motivo: "value_error" }],
    });
  });

  it.each(["confirmacion", "rechazo", "reversion", "reimputacion"] as const)(
    "%s va a su ruta con su cuerpo",
    async (accion) => {
      const f = mockFetch({ status: 200, cuerpo: { pago_id: PAGO, estado: "x" } });
      await resolverPago(
        EDIFICIO,
        PAGO,
        accion,
        accion === "confirmacion" ? undefined : { motivo: "m" },
      );
      expect(f.mock.calls[0]?.[0]).toBe(
        `http://api-interna:8000/api/complejos/${EDIFICIO}/pagos/${PAGO}/${accion}`,
      );
      const init = f.mock.calls[0]?.[1] as RequestInit;
      expect(init.method).toBe("POST");
      expect(init.body).toBe(
        accion === "confirmacion" ? undefined : JSON.stringify({ motivo: "m" }),
      );
    },
  );

  it("un id malo no llama a la API", async () => {
    const f = mockFetch({ status: 200, cuerpo: {} });
    expect(await resolverPago(EDIFICIO, "../x", "rechazo", { motivo: "m" })).toEqual({
      estado: "no_existe",
    });
    expect(f).not.toHaveBeenCalled();
  });
});

describe("el enlace del comprobante", () => {
  it("pide el enlace por POST", async () => {
    const f = mockFetch({
      status: 201,
      cuerpo: { url: `/api/comprobantes/descarga?token=${TOKEN}`, vence_en: "x" },
    });
    const resultado = await enlaceDelComprobante(EDIFICIO, PAGO);
    expect(resultado.estado).toBe("ok");
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/pagos/${PAGO}/comprobante/enlace`,
    );
  });

  it("sólo reconoce la dirección esperada con un token bien formado", () => {
    expect(tokenDelComprobante(`/api/comprobantes/descarga?token=${TOKEN}`)).toBe(TOKEN);
    expect(tokenDelComprobante(`/api/documentos/descarga?token=${TOKEN}`)).toBeNull();
    expect(tokenDelComprobante("/api/comprobantes/descarga?token=../x")).toBeNull();
  });
});

describe("descargarComprobante", () => {
  it("baja el archivo con el token y sin credenciales", async () => {
    const bytes = new ArrayBuffer(8);
    const f = mockFetch({ status: 200, bytes, tipo: "image/png" });
    expect(await descargarComprobante(TOKEN)).toEqual({
      estado: "ok",
      datos: bytes,
      tipo: "image/png",
    });
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/comprobantes/descarga?token=${TOKEN}`,
    );
    expect(f.mock.calls[0]?.[1]).toEqual({ cache: "no-store" });
  });

  it.each([
    [410, "vencido"],
    [403, "invalido"],
    [500, "fallo"],
  ])("un %i es %s", async (status, estado) => {
    mockFetch({ status });
    expect(await descargarComprobante(TOKEN)).toEqual({ estado });
  });

  it("un tipo que la API no guarda es fallo", async () => {
    mockFetch({ status: 200, tipo: "text/html" });
    expect(await descargarComprobante(TOKEN)).toEqual({ estado: "fallo" });
  });

  it("un token mal formado ni se pide", async () => {
    const f = mockFetch({ status: 200, tipo: "image/png" });
    expect(await descargarComprobante("../x")).toEqual({ estado: "invalido" });
    expect(f).not.toHaveBeenCalled();
  });
});
