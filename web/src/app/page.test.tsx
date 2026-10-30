import { afterEach, describe, expect, it, vi } from "vitest";

// pulido-2 (3d), grupo 9: la raíz `/` deja de ser el placeholder del change 1a.
// Con sesión lleva a la lista de edificios; sin sesión, a la pantalla de ingreso.
// PENDIENTE DE CONFIRMAR CON JUANI: qué debe ser la raíz (ver design.md).
const { redirect, sesionActual } = vi.hoisted(() => ({ redirect: vi.fn(), sesionActual: vi.fn() }));
vi.mock("next/navigation", () => ({ redirect }));
vi.mock("../lib/sesion", () => ({ sesionActual }));

import Page from "./page";

afterEach(() => {
  vi.clearAllMocks();
});

describe("raíz /", () => {
  it('escenario "Con sesión": lleva a /edificios', async () => {
    sesionActual.mockResolvedValue({
      token: "t",
      administracionId: undefined,
      regreso: "/edificios",
    });
    await Page();
    expect(redirect).toHaveBeenCalledTimes(1);
    expect(redirect).toHaveBeenCalledWith("/edificios");
  });

  it('escenario "Sin sesión": lleva a /ingresar', async () => {
    sesionActual.mockResolvedValue(null);
    await Page();
    expect(redirect).toHaveBeenCalledTimes(1);
    expect(redirect).toHaveBeenCalledWith("/ingresar");
  });

  it("ya no es el placeholder: no devuelve el texto PropTech suelto", async () => {
    sesionActual.mockResolvedValue(null);
    const resultado = await Page();
    expect(resultado).toBeUndefined();
  });
});
