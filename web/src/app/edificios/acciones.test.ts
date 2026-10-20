import { afterEach, expect, it, vi } from "vitest";
import { crearEdificioAction } from "./acciones";

vi.mock("next/navigation", () => ({ redirect: vi.fn() }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

it("403 al crear un edificio explica que lo puede hacer el super admin", async () => {
  vi.stubEnv("PROPTECH_URL_API_INTERNA", "http://api-interna:8000");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { permiso_faltante: "crear_edificio" } }), {
        status: 403,
        headers: { "content-type": "application/json" },
      }),
    ),
  );
  const datos = new FormData();
  datos.set("nombre", "Inventado");
  datos.set("localidad", "Mendoza");
  expect(await crearEdificioAction(null, datos)).toEqual({
    erroresPorCampo: {},
    erroresDesconocidos: [
      "No podés crear un edificio nuevo. Esto lo puede hacer el super admin de la empresa.",
    ],
  });
});
