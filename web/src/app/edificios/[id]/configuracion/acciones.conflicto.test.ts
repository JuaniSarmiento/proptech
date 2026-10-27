/**
 * D7 (tareas 5.1, 5.2): B-2 — "rige desde" repetido daba el mensaje
 * genérico, nunca marcaba el campo. Mock del cliente de la API (no HTTP
 * real, `acciones.test.ts` ya cubre eso): se prueba sólo el mapeo de
 * `ResultadoApi` → `EstadoFormularioVersion`, que es donde vivía el bug.
 */
import { afterEach, expect, it, vi } from "vitest";
import * as configuracionApi from "../../../../lib/api/configuracion";
import { crearVersionDeConfiguracionAction } from "./acciones";
import type { EstadoFormularioVersion } from "./Pantalla";

function _sinNulo(estado: EstadoFormularioVersion): Exclude<EstadoFormularioVersion, null> {
  if (estado === null) {
    throw new Error("la acción no debería devolver null en estos escenarios");
  }
  return estado;
}

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
vi.mock("../../../../lib/api/configuracion", async () => {
  const real = await vi.importActual<typeof configuracionApi>("../../../../lib/api/configuracion");
  return { ...real, crearVersionDeConfiguracion: vi.fn() };
});

const UUID = "11111111-1111-1111-1111-111111111111";

function _formulario(): FormData {
  const datos = new FormData();
  datos.set("tasa_mensual", "4.00");
  datos.set("dias_de_gracia", "0");
  datos.set("forma_de_calculo", "proporcional_por_dia");
  datos.set("porcentaje_fondo", "2.00");
  datos.set("dia_de_vencimiento", "10");
  datos.set("modalidad_de_vencimiento", "unico");
  datos.set("vigente_desde", "2099-01-01");
  return datos;
}

afterEach(() => {
  vi.clearAllMocks();
});

it('escenario "Rige desde repetido": marca vigente_desde, nada más', async () => {
  vi.mocked(configuracionApi.crearVersionDeConfiguracion).mockResolvedValue({
    estado: "conflicto",
    campo: "vigente_desde",
  });
  const resultado = _sinNulo(await crearVersionDeConfiguracionAction(UUID, null, _formulario()));
  expect(resultado.erroresPorCampo).toEqual({
    vigente_desde: "Ya hay una versión que rige desde esa fecha.",
  });
  expect(resultado.erroresDesconocidos).toEqual([]);
  expect(resultado.ok).toBeUndefined();
});

it('escenario "Día de vencimiento fuera de rango": marca sólo ese campo', async () => {
  vi.mocked(configuracionApi.crearVersionDeConfiguracion).mockResolvedValue({
    estado: "invalido",
    errores: [{ campo: "dia_de_vencimiento", motivo: "value_error" }],
  });
  const resultado = _sinNulo(await crearVersionDeConfiguracionAction(UUID, null, _formulario()));
  expect(Object.keys(resultado.erroresPorCampo)).toEqual(["dia_de_vencimiento"]);
  expect(resultado.erroresPorCampo.tasa_mensual).toBeUndefined();
});

it('escenario "Dos errores a la vez en intereses y vencimiento": cada error en su campo, "tasa mensual" nunca marcada', async () => {
  // El 422 de pydantic (día de vencimiento fuera de rango) llega ANTES
  // que la base vea el conflicto de "rige desde" — la API responde un
  // solo estado por pedido (nunca los dos a la vez), así que esto
  // reproduce el pedido con AMBOS problemas y confirma cuál gana y que
  // ninguno contamina "tasa mensual".
  vi.mocked(configuracionApi.crearVersionDeConfiguracion).mockResolvedValue({
    estado: "invalido",
    errores: [{ campo: "dia_de_vencimiento", motivo: "value_error" }],
  });
  const formulario = _formulario();
  formulario.set("dia_de_vencimiento", "35");
  const resultado = _sinNulo(await crearVersionDeConfiguracionAction(UUID, null, formulario));
  expect(resultado.erroresPorCampo.dia_de_vencimiento).toBeDefined();
  expect(resultado.erroresPorCampo.vigente_desde).toBeUndefined();
  expect(resultado.erroresPorCampo.tasa_mensual).toBeUndefined();
  expect(resultado.erroresDesconocidos).toEqual([]);
});
