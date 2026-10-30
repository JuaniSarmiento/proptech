import { auth } from "@clerk/nextjs/server";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { elegirAdministracionAction } from "./acciones";
import Selector from "./page";

beforeEach(() => vi.stubEnv("PROPTECH_URL_API_INTERNA", "http://api-interna:8000"));
vi.mock("server-only", () => ({}));
afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
const abrir = () => Selector({ searchParams: Promise.resolve({}) });
it.each([401, "sin_sesion"])("rechazo %s se queda con Cerrar sesión", async (caso) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
  if (caso === "sin_sesion")
    vi.mocked(auth).mockResolvedValueOnce({ userId: null } as Awaited<ReturnType<typeof auth>>);
  let pagina: React.ReactNode;
  try {
    pagina = await abrir();
  } catch {
    pagina = null;
  }
  const html = renderToStaticMarkup(pagina);
  expect(html).toContain("No pudimos validar tu sesión");
  expect(html).toContain('href="/ingresar?cerrar=1"');
});
it("cero administraciones defensivo lleva a sin-acceso", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ persona: { nombre: "Ficticia" }, administraciones: [] })),
      ),
  );
  await expect(abrir()).rejects.toMatchObject({ digest: "NEXT_REDIRECT;replace;/sin-acceso;307;" });
});
it("403 sin_acceso lleva a sin-acceso", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: { codigo: "sin_acceso" } }), { status: 403 }),
      ),
  );
  await expect(abrir()).rejects.toMatchObject({ digest: "NEXT_REDIRECT;replace;/sin-acceso;307;" });
});
it("la acción con 401 no redirige", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
  let resultado: boolean | string;
  try {
    resultado = await elegirAdministracionAction("10000000-0000-0000-0000-000000000001");
  } catch {
    resultado = "redirigió";
  }
  expect(resultado).toBe(false);
});
it.each([1, 2])("guarda %s administraciones", async (n) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          persona: { nombre: "Ficticia" },
          administraciones: Array.from({ length: n }, (_, i) => ({
            id: String(i),
            nombre: `Administración ${i}`,
          })),
        }),
      ),
    ),
  );
  const html = renderToStaticMarkup(
    await Selector({ searchParams: Promise.resolve({ aceptada: "1" }) }),
  );
  expect(html.match(/name="administracion_id"/g)).toHaveLength(n + (n === 1 ? 1 : 0));
});
