import { afterEach, expect, it, vi } from "vitest";
import { pedirApi } from "../../lib/api/cliente";
import { aceptarInvitacionAction } from "./acciones";

vi.mock("../../lib/api/cliente", () => ({ pedirApi: vi.fn() }));
afterEach(() => vi.resetAllMocks());
it.each(["no_existe", "invalido", "fallo"])(
  "aceptación %s no revela el motivo ni consulta datos",
  async (estado) => {
    vi.mocked(pedirApi).mockResolvedValue({ estado } as Awaited<ReturnType<typeof pedirApi>>);
    expect(await aceptarInvitacionAction("sobre-ficticio", null, new FormData())).toEqual({
      error: true,
    });
    expect(vi.mocked(pedirApi).mock.calls).toEqual([
      ["/api/invitaciones/aceptar", { metodo: "POST", cuerpo: { token: "sobre-ficticio" } }],
    ]);
  },
);
it("éxito limpia el sobre de la URL antes de consultar la sesión", async () => {
  vi.mocked(pedirApi).mockResolvedValue({ estado: "ok", datos: { aceptada: true } });
  await expect(
    aceptarInvitacionAction("sobre-ficticio", null, new FormData()),
  ).rejects.toMatchObject({
    digest: "NEXT_REDIRECT;replace;/elegir-administracion?aceptada=1;307;",
  });
});
