import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { importarPadron, plantillaDelPadron } from "./importaciones";

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
