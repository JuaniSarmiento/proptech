import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  descargarDocumento,
  documentosDeLaLiquidacion,
  enlaceDelDocumento,
  reprocesarDocumentos,
  tokenDelEnlace,
} from "./documentos";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const LIQUIDACION = "22222222-2222-2222-2222-222222222222";
const DOCUMENTO = "33333333-3333-3333-3333-333333333333";
const TOKEN = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

const DOCUMENTO_BIEN = {
  documento_id: DOCUMENTO,
  unidad_id: "44444444-4444-4444-4444-444444444444",
  identificador: "1A",
  variante: "completa",
  estado: "generado",
  motivo: null,
};

function mockFetch(respuesta: {
  status: number;
  cuerpo?: unknown;
  bytes?: ArrayBuffer;
  disposicion?: string;
}) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    headers: new Headers(
      respuesta.disposicion ? { "content-disposition": respuesta.disposicion } : {},
    ),
    json: async () => respuesta.cuerpo,
    arrayBuffer: async () => respuesta.bytes ?? new ArrayBuffer(0),
  } as unknown as Response);
}

beforeEach(() => {
  process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
});

afterEach(() => {
  vi.unstubAllGlobals();
  delete process.env.PROPTECH_URL_API_INTERNA;
});

describe("documentosDeLaLiquidacion", () => {
  it("pide GET .../liquidaciones/{id}/documentos y devuelve la lista", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: [DOCUMENTO_BIEN] });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await documentosDeLaLiquidacion(EDIFICIO, LIQUIDACION);
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}/documentos`,
    );
    expect(opciones?.method).toBe("GET");
    expect(resultado).toEqual({ estado: "ok", datos: [DOCUMENTO_BIEN] });
  });

  it("un id que no es UUID es no_existe, sin pedido", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await documentosDeLaLiquidacion("x", LIQUIDACION)).toEqual({ estado: "no_existe" });
    expect(await documentosDeLaLiquidacion(EDIFICIO, "../x")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it.each([
    [{ ...DOCUMENTO_BIEN, estado: "raro" }],
    [{ ...DOCUMENTO_BIEN, variante: "otra" }],
    [{ ...DOCUMENTO_BIEN, documento_id: "no-uuid" }],
    [{ ...DOCUMENTO_BIEN, motivo: 5 }],
    ["texto"],
  ])("una respuesta con otra forma es fallo: %j", async (mala) => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: [mala] }));
    expect(await documentosDeLaLiquidacion(EDIFICIO, LIQUIDACION)).toEqual({ estado: "fallo" });
  });
});

describe("reprocesarDocumentos", () => {
  it("manda POST .../documentos/reproceso y devuelve cuántos se encolaron", async () => {
    const fetchFalso = mockFetch({ status: 202, cuerpo: { encolados: 3 } });
    vi.stubGlobal("fetch", fetchFalso);
    expect(await reprocesarDocumentos(EDIFICIO, LIQUIDACION)).toEqual({
      estado: "ok",
      datos: { encolados: 3 },
    });
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}/documentos/reproceso`,
    );
    expect(opciones?.method).toBe("POST");
  });

  it("un 503 (la cola no contesta) es fallo", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 503, cuerpo: { detail: "cola_no_disponible" } }));
    expect(await reprocesarDocumentos(EDIFICIO, LIQUIDACION)).toEqual({ estado: "fallo" });
  });
});

describe("enlaceDelDocumento", () => {
  it("manda la variante y devuelve la dirección firmada", async () => {
    const cuerpo = {
      url: `/api/documentos/descarga?token=${TOKEN}`,
      vence_en: "2026-11-02T15:15:00Z",
    };
    const fetchFalso = mockFetch({ status: 201, cuerpo });
    vi.stubGlobal("fetch", fetchFalso);
    expect(await enlaceDelDocumento(EDIFICIO, DOCUMENTO, "completa")).toEqual({
      estado: "ok",
      datos: cuerpo,
    });
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/documentos/${DOCUMENTO}/enlace`,
    );
    expect(JSON.parse(String(opciones?.body))).toEqual({ variante: "completa" });
  });

  it("un 409 no_generado llega como conflicto", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 409,
        cuerpo: { detail: "conflicto", campo: "documento", motivo: "no_generado" },
      }),
    );
    expect(await enlaceDelDocumento(EDIFICIO, DOCUMENTO, "completa")).toEqual({
      estado: "conflicto",
      campo: "documento",
      motivo: "no_generado",
    });
  });

  it("una variante desconocida o un id mal escrito no piden nada", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    // @ts-expect-error: una variante que el tipo no admite
    expect(await enlaceDelDocumento(EDIFICIO, DOCUMENTO, "otra")).toEqual({ estado: "no_existe" });
    expect(await enlaceDelDocumento(EDIFICIO, "x", "completa")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});

describe("tokenDelEnlace", () => {
  it("saca el token de la dirección de la API", () => {
    expect(tokenDelEnlace(`/api/documentos/descarga?token=${TOKEN}`)).toBe(TOKEN);
  });

  it.each([
    "/api/documentos/descarga?token=",
    `/api/otra?token=${TOKEN}`,
    `https://otro.example/api/documentos/descarga?token=${TOKEN}`,
    `/api/documentos/descarga?token=${TOKEN}&x=1`,
    "/api/documentos/descarga?token=../../etc",
    `/api/documentos/descarga?token=${TOKEN.toUpperCase()}`,
  ])("una dirección que no es la esperada da null: %s", (url) => {
    expect(tokenDelEnlace(url)).toBeNull();
  });
});

describe("descargarDocumento", () => {
  it("baja el PDF sin mandar ninguna credencial", async () => {
    const bytes = new TextEncoder().encode("%PDF-1.7").buffer as ArrayBuffer;
    const fetchFalso = mockFetch({ status: 200, bytes });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await descargarDocumento(TOKEN);
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(`http://api-interna:8000/api/documentos/descarga?token=${TOKEN}`);
    expect(opciones?.headers).toBeUndefined();
    expect(resultado).toEqual({ estado: "ok", datos: bytes, nombre: "expensa.pdf" });
  });

  it("conserva el nombre que manda la API", async () => {
    const bytes = new TextEncoder().encode("%PDF-1.7").buffer as ArrayBuffer;
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 200,
        bytes,
        disposicion: 'attachment; filename="expensa-2026-11-1b-completa.pdf"',
      }),
    );
    expect(await descargarDocumento(TOKEN)).toEqual({
      estado: "ok",
      datos: bytes,
      nombre: "expensa-2026-11-1b-completa.pdf",
    });
  });

  it("un nombre con otra forma no pasa: vuelve a expensa.pdf", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 200, disposicion: 'attachment; filename="../x.pdf"' }),
    );
    const resultado = await descargarDocumento(TOKEN);
    expect(resultado).toMatchObject({ estado: "ok", nombre: "expensa.pdf" });
  });

  it.each([
    [410, "vencido"],
    [403, "invalido"],
    [500, "fallo"],
    [404, "fallo"],
  ])("un %i es %s", async (status, estado) => {
    vi.stubGlobal("fetch", mockFetch({ status }));
    expect(await descargarDocumento(TOKEN)).toEqual({ estado });
  });

  it("un token con otra forma no sale de la web", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await descargarDocumento("../x")).toEqual({ estado: "invalido" });
    expect(await descargarDocumento("")).toEqual({ estado: "invalido" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("sin la dirección interna de la API es fallo, sin pedido", async () => {
    delete process.env.PROPTECH_URL_API_INTERNA;
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await descargarDocumento(TOKEN)).toEqual({ estado: "fallo" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("si la red falla es fallo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("sin red")));
    expect(await descargarDocumento(TOKEN)).toEqual({ estado: "fallo" });
  });
});
