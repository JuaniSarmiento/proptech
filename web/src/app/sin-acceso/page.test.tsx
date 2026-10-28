/** @vitest-environment jsdom */
import { auth } from "@clerk/nextjs/server";
import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import SinAcceso from "./page";

const recibido = vi.hoisted(() => ({ pantalla: vi.fn(), actual: vi.fn(), api: vi.fn() }));
vi.mock("./Pantalla", () => ({
  PantallaSinAcceso: (props: unknown) => {
    recibido.pantalla(props);
    return <p>Sin acceso</p>;
  },
}));
vi.mock("@clerk/nextjs/server", () => ({
  auth: vi.fn(async () => ({ userId: "user_Prueba" })),
  currentUser: recibido.actual,
}));
vi.mock("../../lib/api/cliente", () => ({ pedirApi: recibido.api }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});
it("con sesión dibuja sin prop email, sin currentUser, API ni fetch", async () => {
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  const { container } = render(await SinAcceso());
  expect(container.textContent).toBe("Sin acceso");
  expect(recibido.pantalla.mock.calls[0]?.[0]).toEqual({});
  expect(recibido.actual).not.toHaveBeenCalled();
  expect(recibido.api).not.toHaveBeenCalled();
  expect(fetch).not.toHaveBeenCalled();
});
it("sin sesión redirige al ingreso sin regreso", async () => {
  vi.mocked(auth).mockResolvedValueOnce({ userId: null } as Awaited<ReturnType<typeof auth>>);
  await expect(SinAcceso()).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/ingresar;307;",
  });
});
