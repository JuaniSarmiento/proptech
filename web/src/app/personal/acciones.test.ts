import { afterEach, expect, it, vi } from "vitest";
import * as personalApi from "../../lib/api/personal";
import { invitarAction, quitarAction, revocarAction } from "./acciones";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("../../lib/api/personal", async () => {
  const real = await vi.importActual<typeof personalApi>("../../lib/api/personal");
  return {
    ...real,
    invitarPersonal: vi.fn(),
    revocarInvitacion: vi.fn(),
    quitarAsignacion: vi.fn(),
  };
});

afterEach(() => vi.resetAllMocks());

function formulario(datos: Record<string, string>): FormData {
  const form = new FormData();
  for (const [clave, valor] of Object.entries(datos)) form.set(clave, valor);
  return form;
}

it("invitar con alcance edificio manda complejo_id; con principal no lo manda", async () => {
  vi.mocked(personalApi.invitarPersonal).mockResolvedValue({
    estado: "ok",
    datos: { persona_id: "p", asignacion_id: "a", invitacion_id: "i" },
  });
  await invitarAction(
    null,
    formulario({
      nombre: "Ana",
      email: "ana@test.com",
      rol: "auxiliar",
      alcance: "edificio",
      complejo_id: "e1",
    }),
  );
  expect(vi.mocked(personalApi.invitarPersonal).mock.calls[0]?.[0]).toEqual({
    nombre: "Ana",
    email: "ana@test.com",
    rol: "auxiliar",
    alcance: "edificio",
    complejo_id: "e1",
  });

  await invitarAction(
    null,
    formulario({
      nombre: "Ana",
      email: "ana@test.com",
      rol: "administrador",
      alcance: "principal",
    }),
  );
  expect(vi.mocked(personalApi.invitarPersonal).mock.calls[1]?.[0]).toEqual({
    nombre: "Ana",
    email: "ana@test.com",
    rol: "administrador",
    alcance: "principal",
  });
});

it("un conflicto de rol se asocia al campo rol, nunca al resumen", async () => {
  vi.mocked(personalApi.invitarPersonal).mockResolvedValue({ estado: "conflicto", campo: "rol" });
  const resultado = await invitarAction(
    null,
    formulario({ nombre: "Ana", email: "ana@test.com", rol: "contador", alcance: "principal" }),
  );
  expect(resultado).toEqual({
    erroresPorCampo: { rol: "Esta persona ya tiene asignado ese perfil." },
    erroresDesconocidos: [],
  });
});

it("revocar y quitar devuelven ok y el error no revela el texto de la API (L-007)", async () => {
  vi.mocked(personalApi.revocarInvitacion).mockResolvedValue({
    estado: "ok",
    datos: { revocada: true },
  });
  expect(await revocarAction(null, formulario({ invitacion_id: "i1" }))).toEqual({ ok: true });

  vi.mocked(personalApi.quitarAsignacion).mockResolvedValue({
    estado: "sin_permiso",
    permiso: "x",
  });
  expect(await quitarAction(null, formulario({ asignacion_id: "a1" }))).toEqual({
    error: "No podés quitar personal.",
  });
});
