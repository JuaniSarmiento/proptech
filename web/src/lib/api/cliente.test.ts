import { auth } from "@clerk/nextjs/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { esIdValido, esTextoDecimalAscii, pedirApi } from "./cliente";

const MARCADOR = "MARCADOR_TECNICO_PRIVADO";

function mockFetch(respuesta: { status: number; cuerpo?: unknown; cuerpoCrudo?: string }) {
  return vi.fn().mockResolvedValue({
    status: respuesta.status,
    json: async () => {
      if (respuesta.cuerpoCrudo !== undefined) {
        return JSON.parse(respuesta.cuerpoCrudo);
      }
      return respuesta.cuerpo;
    },
  } as unknown as Response);
}

describe("pedirApi", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });

  it("sin PROPTECH_URL_API_INTERNA da fallo sin llamar a fetch", async () => {
    delete process.env.PROPTECH_URL_API_INTERNA;
    const fetchFalso = vi.fn();
    vi.stubGlobal("fetch", fetchFalso);
    const resultado = await pedirApi("/api/complejos");
    expect(resultado).toEqual({ estado: "fallo" });
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("manda el x-request-id", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { ok: true } });
    vi.stubGlobal("fetch", fetchFalso);
    await pedirApi("/api/complejos");
    const llamada = fetchFalso.mock.calls[0];
    if (!llamada) throw new Error("fetch no se llamó");
    const cabeceras = llamada[1]?.headers as Headers;
    expect(cabeceras.get("x-request-id")).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
    );
  });

  it("R3C-1 · con cuerpo, declara Content-Type: application/json (si no, fetch pone text/plain y FastAPI da 422)", async () => {
    const fetchFalso = mockFetch({ status: 201, cuerpo: { id: "nuevo" } });
    vi.stubGlobal("fetch", fetchFalso);
    await pedirApi("/api/complejos/1/categorias", {
      metodo: "POST",
      cuerpo: { clave: "k", nombre: "n" },
    });
    const llamada = fetchFalso.mock.calls[0];
    if (!llamada) throw new Error("fetch no se llamó");
    const cabeceras = llamada[1]?.headers as Headers;
    expect(cabeceras.get("content-type")).toMatch(/^application\/json/);
  });

  it("R3C-1 · sin cuerpo (GET), no fuerza ningún Content-Type", async () => {
    const fetchFalso = mockFetch({ status: 200, cuerpo: { ok: true } });
    vi.stubGlobal("fetch", fetchFalso);
    await pedirApi("/api/complejos");
    const llamada = fetchFalso.mock.calls[0];
    if (!llamada) throw new Error("fetch no se llamó");
    const cabeceras = llamada[1]?.headers as Headers;
    expect(cabeceras.get("content-type")).toBeNull();
  });

  it("200: ok con los datos", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: { nombre: "Edificio" } }));
    expect(await pedirApi("/api/complejos/1")).toEqual({
      estado: "ok",
      datos: { nombre: "Edificio" },
    });
  });

  it("200 con un cuerpo legítimamente null (p.ej. sin configuración vigente)", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpo: null }));
    expect(await pedirApi("/api/complejos/1/configuracion")).toEqual({
      estado: "ok",
      datos: null,
    });
  });

  it("401: redirige al ingreso", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 401, cuerpo: { detail: MARCADOR } }));
    await expect(pedirApi("/api/complejos")).rejects.toMatchObject({
      digest: "NEXT_REDIRECT;replace;/ingresar?regreso=%2Fedificios;307;",
    });
  });

  it("403 con permiso: sin_permiso", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 403,
        cuerpo: {
          detail: {
            codigo: "sin_permiso",
            detalle: MARCADOR,
            permiso_faltante: "ver_configuracion_del_edificio",
          },
        },
      }),
    );
    expect(await pedirApi("/api/complejos/1/resumen")).toEqual({
      estado: "sin_permiso",
      permiso: "ver_configuracion_del_edificio",
    });
  });

  it("404: no_existe", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 404, cuerpo: { detail: MARCADOR } }));
    expect(await pedirApi("/api/complejos/1")).toEqual({ estado: "no_existe" });
  });

  it("409 con campo: conflicto", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 409, cuerpo: { detail: MARCADOR, campo: "identificador" } }),
    );
    expect(await pedirApi("/api/unidades")).toEqual({
      estado: "conflicto",
      campo: "identificador",
    });
  });

  it("422 con loc de un campo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 422,
        cuerpo: { detail: [{ loc: ["body", "localidad"], msg: MARCADOR, type: "missing" }] },
      }),
    );
    expect(await pedirApi("/api/complejos")).toEqual({
      estado: "invalido",
      errores: [{ campo: "localidad", motivo: "missing" }],
    });
  });

  it("422 con loc de varios campos", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        status: 422,
        cuerpo: {
          detail: [
            { loc: ["body", "nombre"], msg: MARCADOR, type: "missing" },
            { loc: ["body", "localidad"], msg: MARCADOR, type: "string_too_short" },
          ],
        },
      }),
    );
    expect(await pedirApi("/api/complejos")).toEqual({
      estado: "invalido",
      errores: [
        { campo: "nombre", motivo: "missing" },
        { campo: "localidad", motivo: "string_too_short" },
      ],
    });
  });

  it("500: fallo", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 500, cuerpo: { detail: MARCADOR } }));
    expect(await pedirApi("/api/complejos")).toEqual({ estado: "fallo" });
  });

  it("red caída: fallo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ECONNREFUSED")));
    expect(await pedirApi("/api/complejos")).toEqual({ estado: "fallo" });
  });

  it("cuerpo que no es JSON: fallo", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 200, cuerpoCrudo: "<html>no soy json</html>" }));
    expect(await pedirApi("/api/complejos")).toEqual({ estado: "fallo" });
  });

  it("un coeficiente que no es texto decimal: fallo", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 200, cuerpo: { informe: { suma: "uno", diferencia: "0.000000" } } }),
    );
    const resultado = await pedirApi("/api/complejos/1/resumen", {
      camposDePlata: ["informe.suma"],
    });
    expect(resultado).toEqual({ estado: "fallo" });
  });

  // El marcador va SÓLO en los campos de texto libre (`detail` como string,
  // `msg`): `permiso_faltante`, `campo` (409) y `type` (422) son vocabulario
  // cerrado que el cliente sí extrae a propósito (D2) — plantarlo ahí
  // probaría otra cosa, no L-007.
  it.each([
    [
      "403",
      {
        status: 403,
        cuerpo: {
          detail: {
            codigo: "sin_permiso",
            detalle: MARCADOR,
            permiso_faltante: "configurar_padron",
          },
        },
      },
    ],
    ["404", { status: 404, cuerpo: { detail: MARCADOR } }],
    ["409", { status: 409, cuerpo: { detail: MARCADOR, campo: "identificador" } }],
    [
      "422",
      {
        status: 422,
        cuerpo: { detail: [{ loc: ["body", "x"], msg: MARCADOR, type: "missing" }] },
      },
    ],
    ["500", { status: 500, cuerpo: { detail: MARCADOR } }],
  ] as const)(
    "%s: el marcador de detail/msg nunca llega al resultado (L-007)",
    async (_status, respuesta) => {
      vi.stubGlobal("fetch", mockFetch(respuesta));
      const resultado = await pedirApi("/api/complejos");
      expect(JSON.stringify(resultado)).not.toContain(MARCADOR);
    },
  );
});

describe("esTextoDecimalAscii", () => {
  it("acepta texto decimal ASCII", () => {
    expect(esTextoDecimalAscii("0.100000")).toBe(true);
  });

  it("rechaza lo que no lo es", () => {
    expect(esTextoDecimalAscii("1e-1")).toBe(false);
    expect(esTextoDecimalAscii(1)).toBe(false);
    expect(esTextoDecimalAscii(null)).toBe(false);
  });
});

describe("R3C-2 · esIdValido", () => {
  it("acepta un UUID", () => {
    expect(esIdValido("f760ca3b-7331-4927-96e5-54a3fbb1f3ae")).toBe(true);
  });

  it("rechaza un id con ../ (intentaría redirigir la ruta de la API)", () => {
    expect(esIdValido("../complejos/00000000-0000-0000-0000-00000000bbbb/categorias?x=")).toBe(
      false,
    );
  });

  it("rechaza un id corto que no es UUID", () => {
    expect(esIdValido("1")).toBe(false);
  });
});

describe("2d · discriminador y selector sin rebote", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    delete process.env.PROPTECH_URL_API_INTERNA;
  });
  it("sin_acceso redirige sin regreso", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 403, cuerpo: { detail: { codigo: "sin_acceso" } } }),
    );
    await expect(pedirApi("/api/sesion")).rejects.toMatchObject({
      digest: "NEXT_REDIRECT;replace;/sin-acceso;307;",
    });
  });
  it.each([undefined, "otro"])("código desconocido %s ignora permiso_faltante", async (codigo) => {
    vi.stubGlobal(
      "fetch",
      mockFetch({ status: 403, cuerpo: { detail: { codigo, permiso_faltante: "sin_acceso" } } }),
    );
    expect(await pedirApi("/api/sesion").catch(() => ({ estado: "redirigio" }))).toEqual({
      estado: "sin_permiso",
      permiso: "desconocido",
    });
  });
  it.each([401, "sin_sesion"])("devolver no redirige con %s", async (caso) => {
    vi.stubGlobal("fetch", mockFetch({ status: 401 }));
    if (caso === "sin_sesion")
      vi.mocked(auth).mockResolvedValueOnce({ userId: null } as Awaited<ReturnType<typeof auth>>);
    expect(
      await pedirApi("/api/sesion", { alNoAutenticar: "devolver" }).catch(() => ({
        estado: "redirigio",
      })),
    ).toEqual({ estado: "sin_sesion" });
  });
  it("sin cuerpo 403 es permiso desconocido", async () => {
    vi.stubGlobal("fetch", mockFetch({ status: 403, cuerpoCrudo: "" }));
    expect(await pedirApi("/api/sesion").catch(() => ({ estado: "redirigio" }))).toEqual({
      estado: "sin_permiso",
      permiso: "desconocido",
    });
  });
  it("sin opción, Clerk nulo redirige al ingreso", async () => {
    vi.mocked(auth).mockResolvedValueOnce({ userId: null } as Awaited<ReturnType<typeof auth>>);
    await expect(pedirApi("/api/sesion")).rejects.toMatchObject({
      digest: "NEXT_REDIRECT;replace;/ingresar?regreso=%2Fedificios;307;",
    });
  });
});
