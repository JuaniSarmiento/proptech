import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cambiosDeUnaUnidad,
  cuentaDeVendedor,
  cuentasDeVendedores,
  registrarCambioDeTitular,
  registrarCobroDeVendedor,
} from "./titularidad";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";
const UNIDAD = "22222222-2222-2222-2222-222222222222";
const CUENTA = "33333333-3333-3333-3333-333333333333";

const CAMBIO = {
  id: "44444444-4444-4444-4444-444444444444",
  unidad_id: UNIDAD,
  fecha: "2026-11-10",
  vendedores: ["55555555-5555-5555-5555-555555555555"],
  compradores: [
    { nombre: "Carlos", email: null, persona_id: "66666666-6666-6666-6666-666666666666" },
  ],
  expensa_del_mes: "entera",
  deuda_previa: "en_la_unidad",
};
const DETALLE = {
  cuenta_id: CUENTA,
  persona: { id: "p", nombre: "Ana Prueba" },
  deuda: "30000.00",
  unidades: [{ id: UNIDAD, identificador: "1A" }],
  periodos: [
    {
      periodo: "2026-09-01",
      componentes: { ordinaria: { debe: "100.00", cobrado: "0.00", pendiente: "100.00" } },
    },
  ],
  movimientos: [
    { id: "m", tipo: "traslado", sentido: "debito", importe: "100.00", fecha: "2026-10-31" },
  ],
};

function mockFetch(status: number, cuerpo?: unknown) {
  const f = vi.fn().mockResolvedValue({
    status,
    headers: new Headers(),
    json: async () => cuerpo,
  } as unknown as Response);
  vi.stubGlobal("fetch", f);
  return f;
}

beforeEach(() => {
  process.env.PROPTECH_URL_API_INTERNA = "http://api-interna:8000";
});
afterEach(() => {
  vi.unstubAllGlobals();
  delete process.env.PROPTECH_URL_API_INTERNA;
});

describe("cambiosDeUnaUnidad", () => {
  it("lee los cambios tal como los manda la API", async () => {
    const f = mockFetch(200, [CAMBIO]);
    expect(await cambiosDeUnaUnidad(EDIFICIO, UNIDAD)).toEqual({ estado: "ok", datos: [CAMBIO] });
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/unidades/${UNIDAD}/cambios-de-titular`,
    );
  });

  it("un monto que no es texto con dos decimales es fallo", async () => {
    mockFetch(200, [{ ...CAMBIO, trasladado: 45230.1 }]);
    expect(await cambiosDeUnaUnidad(EDIFICIO, UNIDAD)).toEqual({ estado: "fallo" });
  });

  it("un id que no es UUID no hace pedido", async () => {
    const f = mockFetch(200, []);
    expect(await cambiosDeUnaUnidad("../x", UNIDAD)).toEqual({ estado: "no_existe" });
    expect(f).not.toHaveBeenCalled();
  });

  it("un 403 es sin_permiso con el permiso que falta", async () => {
    mockFetch(403, {
      detail: { codigo: "sin_permiso", permiso_faltante: "registrar_cambio_de_titular" },
    });
    expect(await cambiosDeUnaUnidad(EDIFICIO, UNIDAD)).toEqual({
      estado: "sin_permiso",
      permiso: "registrar_cambio_de_titular",
    });
  });
});

describe("registrarCambioDeTitular", () => {
  it("manda sólo las claves del contrato y omite el deudor si no hay", async () => {
    const f = mockFetch(201, { ...CAMBIO, aviso: null });
    const r = await registrarCambioDeTitular(EDIFICIO, UNIDAD, {
      fecha: "2026-11-10",
      vendedores: ["a"],
      compradores: [{ nombre: "Carlos", email: null }],
      expensa_del_mes: "entera",
      deuda_previa: "en_la_unidad",
    });
    expect(r.estado).toBe("ok");
    const init = f.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      fecha: "2026-11-10",
      vendedores: ["a"],
      compradores: [{ nombre: "Carlos", email: null }],
      expensa_del_mes: "entera",
      deuda_previa: "en_la_unidad",
    });
  });

  it("un 422 vuelve con el campo que nombra", async () => {
    mockFetch(422, {
      detail: [{ type: "value_error", loc: ["body", "fecha"], msg: "valor inválido" }],
    });
    const r = await registrarCambioDeTitular(EDIFICIO, UNIDAD, {
      fecha: "2099-01-01",
      vendedores: ["a"],
      compradores: [{ nombre: "C", email: null }],
      expensa_del_mes: "entera",
      deuda_previa: "en_la_unidad",
    });
    expect(r).toEqual({ estado: "invalido", errores: [{ campo: "fecha", motivo: "value_error" }] });
  });
});

describe("cuentas de vendedores", () => {
  it("la lista respeta el orden de la API", async () => {
    const cuerpo = { cuentas: [DETALLE, { ...DETALLE, deuda: "0.00" }] };
    mockFetch(200, cuerpo);
    expect(await cuentasDeVendedores(EDIFICIO)).toEqual({ estado: "ok", datos: cuerpo });
  });

  it("el detalle con una deuda sin dos decimales es fallo", async () => {
    mockFetch(200, { ...DETALLE, deuda: "30000" });
    expect(await cuentaDeVendedor(EDIFICIO, CUENTA)).toEqual({ estado: "fallo" });
  });

  it("el cobro manda exactamente importe y fecha y devuelve el detalle", async () => {
    const f = mockFetch(201, DETALLE);
    const r = await registrarCobroDeVendedor(EDIFICIO, CUENTA, {
      importe: "20000.00",
      fecha: "2026-11-20",
    });
    expect(r).toEqual({ estado: "ok", datos: DETALLE });
    expect(f.mock.calls[0]?.[0]).toBe(
      `http://api-interna:8000/api/complejos/${EDIFICIO}/cuentas-de-vendedores/${CUENTA}/cobros`,
    );
    const init = f.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual({
      importe: "20000.00",
      fecha: "2026-11-20",
    });
  });
});
