import { auth } from "@clerk/nextjs/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { pedirApi } from "./cliente";

beforeEach(() => {
  vi.stubEnv("PROPTECH_URL_API_INTERNA", "http://api-interna:8000");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.mocked(auth).mockClear();
});

it.each(["GET", "POST", "PATCH", "PUT"] as const)(
  "%s manda sólo sesión y selector del servidor, nunca cookies ni credenciales entrantes",
  async (metodo) => {
    const fetchFalso = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetchFalso);
    await pedirApi("/api/complejos", {
      metodo,
      cabeceras: new Headers({
        cookie: "__session=robada",
        authorization: "Bearer robado",
        "x-proptech-administracion": "ajena",
      }),
    });
    const opciones = fetchFalso.mock.calls[0]?.[1];
    expect(Object.fromEntries(opciones.headers)).toEqual({
      authorization: "Bearer token-local",
      "x-proptech-administracion": "10000000-0000-0000-0000-000000000001",
      "x-request-id": expect.any(String),
    });
    expect(opciones.cache).toBe("no-store");
  },
);

it("sin sesión no llama a la API y lleva al ingreso", async () => {
  vi.mocked(auth).mockResolvedValueOnce({ userId: null } as Awaited<ReturnType<typeof auth>>);
  const fetchFalso = vi.fn();
  vi.stubGlobal("fetch", fetchFalso);
  await expect(pedirApi("/api/complejos")).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/ingresar?regreso=%2Fedificios;307;",
  });
  expect(fetchFalso).not.toHaveBeenCalled();
});

it("401 de la API redirige al ingreso", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
  await expect(pedirApi("/api/complejos")).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/ingresar?regreso=%2Fedificios;307;",
  });
});
