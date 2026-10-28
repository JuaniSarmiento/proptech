/** @vitest-environment jsdom */
import { headers } from "next/headers";
import { afterEach, expect, it, vi } from "vitest";
import RootLayout from "./layout";

const api = vi.hoisted(() => vi.fn(async () => ({ estado: "fallo" })));
vi.mock("../lib/api/cliente", () => ({ pedirApi: api }));
vi.mock("@clerk/nextjs", () => ({
  ClerkProvider: ({ children }: { children: React.ReactNode }) => children,
}));
afterEach(() => vi.clearAllMocks());
it.each(["/sin-acceso", "/edificios", "/personal"])(
  "layout %s pide API sólo en dominio",
  async (ruta) => {
    vi.mocked(headers).mockResolvedValue(
      new Headers({ "x-proptech-ruta": ruta }) as Awaited<ReturnType<typeof headers>>,
    );
    await RootLayout({ children: <p>Contenido</p> });
    expect(api).toHaveBeenCalledTimes(ruta === "/sin-acceso" ? 0 : 1);
  },
);
