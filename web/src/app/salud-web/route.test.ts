/**
 * Tests Vitest de `web/src/app/salud-web/route.ts`, camino de respuesta
 * (D8). Cambio 1c, tarea 6.2.
 *
 * Escenarios de `trazabilidad-y-logs`: API saludable; API degradada; API
 * con un error inesperado.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET } from "./route";

const URL_API = "http://api:8000";

function pedido(requestId: string): Request {
  return new Request("http://localhost/salud-web", {
    headers: { "x-request-id": requestId },
  });
}

describe("GET /salud-web, camino de respuesta", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = URL_API;
  });

  afterEach(() => {
    delete process.env.PROPTECH_URL_API_INTERNA;
    vi.unstubAllGlobals();
  });

  it("API 200 da 200 con el mismo X-Request-ID en la llamada a la API y en la respuesta", async () => {
    const fetchSimulado = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchSimulado);

    const respuesta = await GET(pedido("3f2c1a00-0001-4001-8001-000000000001"));

    expect(respuesta.status).toBe(200);
    expect(await respuesta.json()).toEqual({ web: "ok", api: "ok" });
    expect(respuesta.headers.get("Content-Type")).toContain("application/json");
    expect(respuesta.headers.get("X-Request-ID")).toBe("3f2c1a00-0001-4001-8001-000000000001");

    expect(fetchSimulado).toHaveBeenCalledTimes(1);
    const [urlLlamada, initLlamada] = fetchSimulado.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ];
    expect(urlLlamada).toBe(`${URL_API}/api/salud`);
    const encabezadosLlamada = initLlamada.headers as Headers;
    expect(encabezadosLlamada.get("X-Request-ID")).toBe("3f2c1a00-0001-4001-8001-000000000001");
  });

  it("API 503 da 503 con api degradado", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 503 })),
    );

    const respuesta = await GET(pedido("3f2c1a00-0001-4001-8001-000000000002"));

    expect(respuesta.status).toBe(503);
    expect(await respuesta.json()).toEqual({ web: "ok", api: "degradado" });
  });

  it("API 500 con un cuerpo marcado da 503 degradado sin el cuerpo", async () => {
    const marcador = "MARCADOR-SECRETO-DEL-CUERPO-DE-LA-API";
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detalle: marcador }), {
            status: 500,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );

    const respuesta = await GET(pedido("3f2c1a00-0001-4001-8001-000000000003"));

    expect(respuesta.status).toBe(503);
    const texto = await respuesta.text();
    expect(texto).not.toContain(marcador);
    expect(JSON.parse(texto)).toEqual({ web: "ok", api: "degradado" });
  });
});

/**
 * Tarea 6.3, caminos de falla. Escenarios de `trazabilidad-y-logs`: API
 * caída o colgada; API que no contesta; Conexión rechazada; Sin dirección
 * de la API; Error con datos en su mensaje.
 */
describe("GET /salud-web, caminos de falla", () => {
  beforeEach(() => {
    process.env.PROPTECH_URL_API_INTERNA = URL_API;
  });

  afterEach(() => {
    delete process.env.PROPTECH_URL_API_INTERNA;
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("corta a los 2 s cuando la API acepta la conexión y no contesta (cota con temporizadores falsos)", async () => {
    vi.useFakeTimers();
    const fetchQueNoContesta = vi.fn((_url: string, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("se abortó la conexión", "AbortError"));
        });
      });
    });
    vi.stubGlobal("fetch", fetchQueNoContesta);

    const promesaRespuesta = GET(pedido("3f2c1a00-0001-4001-8001-000000000004"));
    await vi.advanceTimersByTimeAsync(2001);
    const respuesta = await promesaRespuesta;

    expect(respuesta.status).toBe(503);
    expect(await respuesta.json()).toEqual({ web: "ok", api: "sin_conexion" });
  });

  it("da sin_conexion cuando la conexión se rechaza al instante", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );

    const respuesta = await GET(pedido("3f2c1a00-0001-4001-8001-000000000005"));

    expect(respuesta.status).toBe(503);
    expect(await respuesta.json()).toEqual({ web: "ok", api: "sin_conexion" });
  });

  it("da sin_configurar sin llamar a fetch cuando falta PROPTECH_URL_API_INTERNA", async () => {
    delete process.env.PROPTECH_URL_API_INTERNA;
    const fetchSimulado = vi.fn();
    vi.stubGlobal("fetch", fetchSimulado);

    const respuesta = await GET(pedido("3f2c1a00-0001-4001-8001-000000000006"));

    expect(respuesta.status).toBe(503);
    expect(await respuesta.json()).toEqual({ web: "ok", api: "sin_configurar" });
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  it("no deja el marcador del mensaje de un error de fetch en la respuesta", async () => {
    const marcador = "marcador de la direccion interna de la api, no es un secreto";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error(marcador);
      }),
    );

    const respuesta = await GET(pedido("3f2c1a00-0001-4001-8001-000000000007"));

    const texto = await respuesta.text();
    expect(texto).not.toContain(marcador);
    expect(respuesta.headers.get("X-Request-ID") ?? "").not.toContain(marcador);
  });
});
