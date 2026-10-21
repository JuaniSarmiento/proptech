import { afterEach, expect, it, vi } from "vitest";
import * as personalApi from "../../../../lib/api/personal";
import { altaVecinoAction, quitarVecinoAction, revocarVecinoAction } from "./acciones";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("../../../../lib/api/personal", async () => {
  const real = await vi.importActual<typeof personalApi>("../../../../lib/api/personal");
  return { ...real, altaDeVecino: vi.fn(), revocarInvitacion: vi.fn(), quitarAsignacion: vi.fn() };
});

afterEach(() => vi.resetAllMocks());

function formulario(datos: Record<string, string>): FormData {
  const form = new FormData();
  for (const [clave, valor] of Object.entries(datos)) form.set(clave, valor);
  return form;
}

it("alta de vecino manda unidad_id, nombre, email y vínculo", async () => {
  vi.mocked(personalApi.altaDeVecino).mockResolvedValue({
    estado: "ok",
    datos: { persona_id: "p", asignacion_id: "a", invitacion_id: "i" },
  });
  await altaVecinoAction(
    "complejo-1",
    null,
    formulario({ unidad_id: "u1", nombre: "Vecino", email: "v@test.com", vinculo: "inquilino" }),
  );
  expect(vi.mocked(personalApi.altaDeVecino).mock.calls[0]).toEqual([
    "u1",
    { nombre: "Vecino", email: "v@test.com", vinculo: "inquilino" },
  ]);
});

it("un conflicto de vínculo se asocia al campo, nunca al resumen", async () => {
  vi.mocked(personalApi.altaDeVecino).mockResolvedValue({ estado: "conflicto", campo: "vinculo" });
  const resultado = await altaVecinoAction(
    "complejo-1",
    null,
    formulario({ unidad_id: "u1", nombre: "Vecino", email: "v@test.com", vinculo: "propietario" }),
  );
  expect(resultado).toEqual({
    erroresPorCampo: { vinculo: "Ya está vinculada a esta unidad." },
    erroresDesconocidos: [],
  });
});

it("revocar y quitar devuelven ok; sin permiso no revela el texto de la API (L-007)", async () => {
  vi.mocked(personalApi.revocarInvitacion).mockResolvedValue({
    estado: "ok",
    datos: { revocada: true },
  });
  expect(
    await revocarVecinoAction("complejo-1", null, formulario({ invitacion_id: "i1" })),
  ).toEqual({ ok: true });

  vi.mocked(personalApi.quitarAsignacion).mockResolvedValue({
    estado: "sin_permiso",
    permiso: "x",
  });
  expect(await quitarVecinoAction("complejo-1", null, formulario({ asignacion_id: "a1" }))).toEqual(
    { error: "No podés quitar un vecino." },
  );
});
