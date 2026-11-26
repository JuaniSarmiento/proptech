import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  direccionDeDescarga,
  expensaDeLaUnidad,
  misUnidades,
  pagosConfirmadosDeLaUnidad,
  pdfsDeLaUnidad,
} from "./vecino";

const UNIDAD = "00000000-0000-0000-0000-000000004101";
const LIQ = "00000000-0000-0000-0000-000000004201";
const TOKEN = `abc-DEF_123.${"a".repeat(64)}`;

function mockFetch(respuesta: { status: number; cuerpo?: unknown }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
  } as unknown as Response);
}

const unidad = {
  unidad_id: UNIDAD,
  identificador: "1A",
  vinculo: "propietario",
  complejo_id: "00000000-0000-0000-0000-000000004001",
  edificio: "Torre Ficticia",
  total_a_pagar: "46500.00",
  vencimiento: "2026-11-10",
  deuda_anterior: "0.00",
  intereses: "0.00",
  credito_aplicable: "0.00",
  credito_retenido: "0.00",
};
const conjunto = {
  total_a_pagar: "46500.00",
  intereses: "0.00",
  credito_aplicable: "0.00",
  credito_retenido: "0.00",
};

const bloque = {
  subtotal: "80000.00",
  categorias: [
    {
      categoria_id: "00000000-0000-0000-0000-000000004311",
      nombre: "Limpieza",
      importe: "80000.00",
      porcentaje: "100.00",
    },
  ],
};
// El inquilino: sin `extraordinario`, sin `extraordinaria` (D-170.2).
const expensaDeInquilino = {
  liquidacion_id: LIQ,
  complejo_id: unidad.complejo_id,
  unidad_id: UNIDAD,
  identificador: "1B",
  periodo: "2026-10-01",
  vencimiento: "2026-10-10",
  vinculo: "inquilino",
  bloques: { ordinario: bloque },
  grupos: [
    {
      grupo_id: "00000000-0000-0000-0000-000000004301",
      nombre: "Generales",
      ordinaria: "24000.00",
    },
  ],
  ordinaria: "24000.00",
  cargos_particulares: [],
  fondo_de_reserva: "1200.00",
  intereses: "0.00",
  total: "25200.00",
  comparacion: null,
};

beforeEach(() => {
  process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
});

afterEach(() => {
  vi.unstubAllGlobals();
  delete process.env.PROPTECH_URL_API_INTERNA;
});

describe("misUnidades", () => {
  it("pide GET /api/mis-unidades y devuelve el cuerpo tal cual", async () => {
    const cuerpo = { fecha: "2026-11-18", conjunto, unidades: [unidad] };
    const f = mockFetch({ status: 200, cuerpo });
    vi.stubGlobal("fetch", f);
    expect(await misUnidades()).toEqual({ estado: "ok", datos: cuerpo });
    expect(f.mock.calls[0]?.[0]).toBe("http://api-interna:8000/api/mis-unidades");
  });

  it("un monto que no es texto con dos decimales es fallo, nunca un ok", async () => {
    const cuerpo = {
      fecha: "2026-11-18",
      conjunto: { ...conjunto, total_a_pagar: 46500 },
      unidades: [unidad],
    };
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo }));
    expect(await misUnidades()).toEqual({ estado: "fallo" });
  });
});

describe("expensaDeLaUnidad", () => {
  it("acepta la expensa del inquilino sin ninguna clave extraordinaria", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: expensaDeInquilino }));
    const r = await expensaDeLaUnidad(UNIDAD, LIQ);
    expect(r).toEqual({ estado: "ok", datos: expensaDeInquilino });
  });

  it("un 404 de la API es no_existe (lo ajeno no se distingue de lo inexistente)", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 404, cuerpo: { detail: "no encontrado" } }));
    expect(await expensaDeLaUnidad(UNIDAD, LIQ)).toEqual({ estado: "no_existe" });
  });

  it("un id que no es UUID es no_existe, sin pedido", async () => {
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    expect(await expensaDeLaUnidad("../x", LIQ)).toEqual({ estado: "no_existe" });
    expect(await expensaDeLaUnidad(UNIDAD, "no-es-un-id")).toEqual({ estado: "no_existe" });
    expect(f).not.toHaveBeenCalled();
  });

  it("un total que no es plata es fallo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 200, cuerpo: { ...expensaDeInquilino, total: "25200" } }),
    );
    expect(await expensaDeLaUnidad(UNIDAD, LIQ)).toEqual({ estado: "fallo" });
  });
});

describe("pagosConfirmadosDeLaUnidad y pdfsDeLaUnidad", () => {
  it("los pagos con otra forma son fallo", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: [{ pago_id: "x" }] }));
    expect(await pagosConfirmadosDeLaUnidad(UNIDAD)).toEqual({ estado: "fallo" });
  });

  it("un PDF cuyo enlace no es el firmado del 7 es fallo: nunca llega una dirección rara a la pantalla", async () => {
    const pdf = {
      documento_id: "00000000-0000-0000-0000-000000004501",
      liquidacion_id: LIQ,
      complejo_id: unidad.complejo_id,
      periodo: "2026-11-01",
      variante: "completa",
      url: "https://otro.example/descarga?token=x",
      vence_en: "2026-11-18T15:15:00+00:00",
    };
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: [pdf] }));
    expect(await pdfsDeLaUnidad(UNIDAD)).toEqual({ estado: "fallo" });
  });
});

describe("direccionDeDescarga", () => {
  it("cambia /api/documentos/descarga por la ruta de la web, con el mismo token", () => {
    expect(direccionDeDescarga(`/api/documentos/descarga?token=${TOKEN}`)).toBe(
      `/documentos/descarga?token=${TOKEN}`,
    );
  });

  it("rechaza lo que no tiene la forma del enlace firmado", () => {
    for (const url of [
      "/api/documentos/descarga?token=x",
      `/api/otra?token=${TOKEN}`,
      `/api/documentos/descarga?token=${TOKEN}&x=1`,
      `https://evil.example/api/documentos/descarga?token=${TOKEN}`,
    ]) {
      expect(direccionDeDescarga(url), url).toBeNull();
    }
  });
});
