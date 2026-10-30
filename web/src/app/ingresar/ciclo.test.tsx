import { headers } from "next/headers";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import { irAlIngreso } from "../../lib/sesion";
import Selector from "../elegir-administracion/page";
import Ingresar from "./[[...paso]]/page";

const recibido = vi.hoisted(() => vi.fn());
vi.mock("@clerk/nextjs", () => ({
  ClerkLoaded: ({ children }: { children: React.ReactNode }) => children,
  ClerkLoading: () => null,
  SignIn: (props: unknown) => {
    recibido(props);
    return <p>Clerk</p>;
  },
  SignUp: () => null,
  useClerk: () => ({ signOut: vi.fn() }),
}));
vi.mock("server-only", () => ({}));
afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});
it("50 vueltas del selector que redirige conservan tamaño sin regreso anidado", async () => {
  let ruta = "/edificios";
  const largos: number[] = [];
  for (let i = 0; i < 50; i++) {
    vi.mocked(headers).mockResolvedValue(
      new Headers({ "x-proptech-ruta": ruta }) as Awaited<ReturnType<typeof headers>>,
    );
    let ingreso = "";
    try {
      await irAlIngreso();
    } catch (e) {
      ingreso = (e as { digest: string }).digest.split(";")[2] ?? "";
    }
    const url = new URL(ingreso, "https://proptech.invalid");
    renderToStaticMarkup(
      await Ingresar({
        searchParams: Promise.resolve({ regreso: url.searchParams.get("regreso") ?? undefined }),
      }),
    );
    ruta = recibido.mock.lastCall?.[0].forceRedirectUrl;
    largos.push(ruta.length);
    expect(new URL(ruta, "https://proptech.invalid").searchParams.get("regreso")).toBe(
      "/edificios",
    );
  }
  expect(new Set(largos).size).toBe(1);
});
it("con D2 el selector no vuelve al ingreso", async () => {
  vi.stubEnv("PROPTECH_URL_API_INTERNA", "http://api-interna:8000");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
  const redirecciones: string[] = [];
  for (let i = 0; i < 50; i++) {
    try {
      await Selector({ searchParams: Promise.resolve({}) });
    } catch (e) {
      redirecciones.push((e as { digest: string }).digest);
    }
  }
  expect(redirecciones).toEqual([]);
});
