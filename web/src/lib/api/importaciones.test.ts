import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  aceptarDiferencias,
  comparacionDelBorrador,
  importarPadron,
  plantillaDelPadron,
} from "./importaciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";

function mockFetch(respuesta: { status: number; cuerpo?: unknown; bytes?: ArrayBuffer }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => respuesta.cuerpo,
    arrayBuffer: async () => respuesta.bytes ?? new ArrayBuffer(0),
  } as unknown as Response);
}

const ARCHIVO = new File(["PK-contenido"], "padron-torre-ficticia.xlsx");

describe("importarPadron / plantillaDelPadron", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("importarPadron manda un multipart con el archivo (y su nombre) y la fecha, sin Content-Type propio", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { unidades_creadas: 12 } });
    vi.stubGlobal("fetch", fetchFalso);
    await importarPadron(EDIFICIO, ARCHIVO, "2026-10-15");
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(`http://api-interna:8000/api/complejos/${EDIFICIO}/importaciones`);
    expect(opciones?.method).toBe("POST");
    const cuerpo = opciones?.body as FormData;
    expect(cuerpo).toBeInstanceOf(FormData);
    expect((cuerpo.get("archivo") as File).name).toBe("padron-torre-ficticia.xlsx");
    expect(cuerpo.get("fecha_de_migracion")).toBe("2026-10-15");
    // `fetch` pone el límite entre partes: un Content-Type a mano lo rompería.
    const cabeceras = opciones?.headers as Headers;
    expect(cabeceras.has("Content-Type")).toBe(false);
  });

  it("un 422 con hoja, fila, columna y motivo es un rechazo del archivo, con los errores en orden", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 422,
        cuerpo: {
          detail: [
            { hoja: "Unidades", fila: 9, columna: "Piso", motivo: "Piso inválido" },
            { hoja: null, fila: null, columna: null, motivo: "No es un .xlsx" },
          ],
        },
      }),
    );
    expect(await importarPadron(EDIFICIO, ARCHIVO, "2026-10-15")).toEqual({
      estado: "rechazado",
      errores: [
        { hoja: "Unidades", fila: 9, columna: "Piso", motivo: "Piso inválido" },
        { hoja: null, fila: null, columna: null, motivo: "No es un .xlsx" },
      ],
    });
  });

  it("un 422 de campo (la fecha) sigue siendo invalido, nunca un rechazo del archivo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 422,
        cuerpo: { detail: [{ loc: ["body", "fecha_de_migracion"], type: "value_error" }] },
      }),
    );
    expect(await importarPadron(EDIFICIO, ARCHIVO, "2999-01-01")).toEqual({
      estado: "invalido",
      errores: [{ campo: "fecha_de_migracion", motivo: "value_error" }],
    });
  });

  it("un 403 sin permiso y un 409 por el archivo repetido llegan con su estado", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 403,
        cuerpo: {
          detail: {
            codigo: "sin_permiso",
            detalle: "sin_permiso",
            permiso_faltante: "importar_padron_y_saldos",
          },
        },
      }),
    );
    expect(await importarPadron(EDIFICIO, ARCHIVO, "2026-10-15")).toEqual({
      estado: "sin_permiso",
      permiso: "importar_padron_y_saldos",
    });
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 409, cuerpo: { detail: "conflicto", campo: "archivo" } }),
    );
    expect(await importarPadron(EDIFICIO, ARCHIVO, "2026-10-15")).toEqual({
      estado: "conflicto",
      campo: "archivo",
    });
  });

  it("R3C-2 · un id que no es UUID da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await importarPadron("1", ARCHIVO, "2026-10-15")).toEqual({ estado: "no_existe" });
    expect(await plantillaDelPadron("1")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("plantillaDelPadron pide GET .../importaciones/plantilla y devuelve los bytes", async () => {
    const bytes = new Uint8Array([0x50, 0x4b, 3, 4]).buffer;
    const fetchFalso = mockFetch({ status: 200, bytes });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await plantillaDelPadron(EDIFICIO);
    expect(fetchFalso.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/importaciones/plantilla`,
    );
    expect(resultado).toEqual({ estado: "ok", datos: bytes });
  });
});

const IMPORTACION = "22222222-2222-2222-2222-222222222222";

const COMPARACION = {
  importacion_id: IMPORTACION,
  unidades: [
    {
      unidad: "1A",
      unidad_id: "33333333-3333-3333-3333-333333333333",
      borrador: "169000.00",
      control: "159000.00",
      diferencia: "10000.00",
      aviso: "El primer interés del sistema cubre octubre de 2026",
    },
    {
      unidad: "2A",
      unidad_id: "44444444-4444-4444-4444-444444444444",
      borrador: "52000.00",
      control: "62000.00",
      diferencia: "-10000.00",
      aviso: null,
    },
  ],
  total_borrador: "221000.00",
  total_control: "221000.00",
  unidades_con_diferencia: 2,
  requiere_aceptacion: true,
  aceptacion: null,
};

describe("comparacionDelBorrador / aceptarDiferencias", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("comparacionDelBorrador pide GET .../importaciones/comparacion y devuelve el cuerpo", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: COMPARACION });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await comparacionDelBorrador(EDIFICIO);
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(`http://api-interna:8000/api/complejos/${EDIFICIO}/importaciones/comparacion`);
    expect(opciones?.method).toBe("GET");
    expect(resultado).toEqual({ estado: "ok", datos: COMPARACION });
  });

  it("un monto que no es texto decimal con dos decimales es fallo, nunca un ok que la pantalla no sabría mostrar", async () => {
    const primera = COMPARACION.unidades[0];
    for (const mala of [
      { ...COMPARACION, total_borrador: 221000 },
      { ...COMPARACION, total_control: "221000" },
      { ...COMPARACION, unidades: [{ ...primera, diferencia: "10000" }] },
      { ...COMPARACION, unidades: [{ ...primera, borrador: 169000 }] },
    ]) {
      vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: mala }));
      expect(await comparacionDelBorrador(EDIFICIO)).toEqual({ estado: "fallo" });
    }
  });

  it("un 404 (sin borrador o sin edificio) y un 403 llegan con su estado", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 404, cuerpo: { detail: "no encontrado" } }));
    expect(await comparacionDelBorrador(EDIFICIO)).toEqual({ estado: "no_existe" });
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 403,
        cuerpo: {
          detail: {
            codigo: "sin_permiso",
            detalle: "sin_permiso",
            permiso_faltante: "importar_padron_y_saldos",
          },
        },
      }),
    );
    expect(await comparacionDelBorrador(EDIFICIO)).toEqual({
      estado: "sin_permiso",
      permiso: "importar_padron_y_saldos",
    });
  });

  it("aceptarDiferencias manda un JSON con sólo importacion_id a .../aceptacion-de-diferencias", async () => {
    const aceptada = {
      aceptacion_id: "55555555-5555-5555-5555-555555555555",
      diferencias: [
        { unidad: "1A", borrador: "169000.00", control: "159000.00", diferencia: "10000.00" },
      ],
      aceptada_por: "66666666-6666-6666-6666-666666666666",
      aceptada_en: "2026-11-12T15:00:00+00:00",
    };
    const fetchFalso = mockFetch({ status: 201, cuerpo: aceptada });
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await aceptarDiferencias(EDIFICIO, IMPORTACION);
    const [url, opciones] = fetchFalso.mock.calls[0] ?? [];
    expect(url).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/importaciones/aceptacion-de-diferencias`,
    );
    expect(opciones?.method).toBe("POST");
    expect(JSON.parse(String(opciones?.body))).toEqual({ importacion_id: IMPORTACION });
    expect((opciones?.headers as Headers).get("Content-Type")).toBe("application/json");
    expect(resultado).toEqual({ estado: "ok", datos: aceptada });
  });

  it.each([
    [403, { detail: { codigo: "sin_permiso", permiso_faltante: "aceptar_diferencias_de_saldos" } }],
    [409, { detail: "conflicto", campo: "aceptacion" }],
  ])("aceptarDiferencias con %s da su estado", async (status, cuerpo) => {
    vi.stubGlobal("fetch", mockFetch({ status, cuerpo }));
    const resultado = await aceptarDiferencias(EDIFICIO, IMPORTACION);
    expect(resultado).toEqual(
      status === 403
        ? { estado: "sin_permiso", permiso: "aceptar_diferencias_de_saldos" }
        : { estado: "conflicto", campo: "aceptacion" },
    );
  });

  it("R3C-2 · un id que no es UUID da no_existe, sin llamar a fetch", async () => {
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    expect(await comparacionDelBorrador("1")).toEqual({ estado: "no_existe" });
    expect(await aceptarDiferencias("1", IMPORTACION)).toEqual({ estado: "no_existe" });
    expect(await aceptarDiferencias(EDIFICIO, "../otra")).toEqual({ estado: "no_existe" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
