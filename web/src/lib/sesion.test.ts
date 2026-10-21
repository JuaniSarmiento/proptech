import { auth } from "@clerk/nextjs/server";
import { cookies, headers } from "next/headers";
import { afterEach, expect, it, vi } from "vitest";
import { elegirAdministracionAction } from "../app/elegir-administracion/acciones";
import { regresoSeguro, sesionActual } from "./sesion";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it.each(["//otro", "https://otro", "/\\otro", "/\notro", "/a/..//otro", ""])(
  "el regreso %j abre Mis edificios",
  (regreso) => expect(regresoSeguro(regreso)).toBe("/edificios"),
);
it("conserva una ruta propia con su consulta", () => {
  expect(regresoSeguro("/edificios/uno/unidades?pagina=2")).toBe(
    "/edificios/uno/unidades?pagina=2",
  );
});
it("lee el regreso del pedido y no transmite la cookie de Clerk", async () => {
  vi.mocked(headers).mockResolvedValueOnce(
    new Headers({ "x-proptech-ruta": "/edificios/uno/unidades" }) as Awaited<
      ReturnType<typeof headers>
    >,
  );
  expect(await sesionActual()).toEqual({
    token: "token-local",
    administracionId: "10000000-0000-0000-0000-000000000001",
    regreso: "/edificios/uno/unidades",
  });
});
it("sin token no fabrica una sesión", async () => {
  vi.mocked(auth).mockResolvedValueOnce({
    userId: "user_prueba",
    getToken: async () => null,
  } as Awaited<ReturnType<typeof auth>>);
  expect(await sesionActual()).toBeNull();
});

const ID = "10000000-0000-0000-0000-000000000001";
it.each([true, false])(
  "escribe sólo una administración que devolvió la API (producción=%s)",
  async (produccion) => {
    vi.stubEnv("NODE_ENV", produccion ? "production" : "test");
    vi.stubEnv("PROPTECH_URL_API_INTERNA", "http://api-interna:8000");
    const set = vi.fn();
    vi.mocked(cookies).mockResolvedValue({ get: () => ({ value: ID }), set } as unknown as Awaited<
      ReturnType<typeof cookies>
    >);
    const fetchFalso = vi.fn().mockImplementation(
      async () =>
        new Response(
          JSON.stringify({
            persona: { nombre: "Persona inventada" },
            administraciones: [{ id: ID, nombre: "A" }],
          }),
        ),
    );
    vi.stubGlobal("fetch", fetchFalso);
    await elegirAdministracionAction(ID);
    expect(set).toHaveBeenCalledExactlyOnceWith("proptech_administracion", ID, {
      httpOnly: true,
      sameSite: "lax",
      secure: produccion,
      path: "/",
    });
  },
);
it("rechaza la administración ajena sin escribir la cookie", async () => {
  vi.stubEnv("PROPTECH_URL_API_INTERNA", "http://api-interna:8000");
  const set = vi.fn();
  vi.mocked(cookies).mockResolvedValue({ get: () => ({ value: ID }), set } as unknown as Awaited<
    ReturnType<typeof cookies>
  >);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          persona: { nombre: "Persona inventada" },
          administraciones: [{ id: ID, nombre: "A" }],
        }),
      ),
    ),
  );
  await expect(elegirAdministracionAction("10000000-0000-0000-0000-000000000002")).resolves.toBe(
    false,
  );
  expect(set).not.toHaveBeenCalled();
});
