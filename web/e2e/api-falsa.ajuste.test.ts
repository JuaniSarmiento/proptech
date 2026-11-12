/**
 * La API falsa del ajuste de saldo inicial (change 5, H-010): los tres edificios del contrato
 * (1001 a 1003), por HTTP real. Los de H-007 a H-009 siguen contestando lo suyo.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const CONFIRMADO = "00000000-0000-0000-0000-000000001001";
const PENDIENTE = "00000000-0000-0000-0000-000000001002";
const SIN_PERMISO = "00000000-0000-0000-0000-000000001003";
const UNIDAD_1A = {
  [CONFIRMADO]: "00000000-0000-0000-0000-000000100101",
  [PENDIENTE]: "00000000-0000-0000-0000-000000100201",
  [SIN_PERMISO]: "00000000-0000-0000-0000-000000100301",
};
const OPERACION = "33333333-3333-3333-3333-333333333333";
const PEDIDO = {
  operacion_id: OPERACION,
  importe: "5000.00",
  componente: "ordinaria",
  motivo: "Faltó la expensa extraordinaria de julio",
};

let servidor: Server;
let base: string;

beforeAll(async () => {
  servidor = crearServidor({ jwtKey: PUBLICA, origen: "http://127.0.0.1:3100" });
  await new Promise<void>((resolve) => servidor.listen(0, resolve));
  const direccion = servidor.address();
  base = `http://127.0.0.1:${typeof direccion === "object" && direccion ? direccion.port : 0}`;
});

afterAll(() => {
  servidor.close();
});

function pedir(ruta: string, opciones: RequestInit = {}) {
  return fetch(`${base}${ruta}`, {
    ...opciones,
    headers: { ...cabecerasDePrueba(), ...opciones.headers },
  });
}

const ajustar = (id: string, unidad: string, cuerpo: unknown = PEDIDO) =>
  pedir(`/api/complejos/${id}/unidades/${unidad}/ajustes-de-saldo-inicial`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(cuerpo),
  });

async function cuerpoDe(respuesta: Response, estado: number) {
  expect(respuesta.status).toBe(estado);
  return respuesta.json();
}

describe("los edificios del ajuste", () => {
  it.each([CONFIRMADO, PENDIENTE, SIN_PERMISO])(
    "el %s trae su 1A con el id del contrato",
    async (id) => {
      const padron = await cuerpoDe(await pedir(`/api/complejos/${id}/unidades`), 200);
      expect(padron.unidades).toHaveLength(1);
      expect(padron.unidades[0].identificador).toBe("1A");
      expect(padron.unidades[0].id).toBe(UNIDAD_1A[id as keyof typeof UNIDAD_1A]);
    },
  );

  it.each([
    [CONFIRMADO, "confirmada"],
    [SIN_PERMISO, "confirmada"],
    [PENDIENTE, "pendiente"],
  ])("el resumen del %s dice migración %s", async (id, estado) => {
    const resumen = await cuerpoDe(await pedir(`/api/complejos/${id}/resumen`), 200);
    expect(resumen.estado_migracion).toBe(estado);
  });

  it("el 1001 responde 201 con el ajuste que se mandó y deja su cuerpo crudo", async () => {
    const ajuste = await cuerpoDe(await ajustar(CONFIRMADO, UNIDAD_1A[CONFIRMADO]), 201);
    expect(ajuste).toMatchObject({
      operacion_id: OPERACION,
      unidad_id: UNIDAD_1A[CONFIRMADO],
      importe: "5000.00",
      componente: "ordinaria",
      motivo: PEDIDO.motivo,
    });
    const ultima = await cuerpoDe(await pedir("/api/__debug/ultima-escritura"), 200);
    expect(ultima.metodo).toBe("POST");
    expect(ultima.url).toBe(
      `/api/complejos/${CONFIRMADO}/unidades/${UNIDAD_1A[CONFIRMADO]}/ajustes-de-saldo-inicial`,
    );
    expect(JSON.parse(ultima.cuerpo)).toEqual(PEDIDO);
  });

  it("el 1003 rechaza el ajuste con 403 sin_permiso y el 1002 no lo acepta (409)", async () => {
    const sinPermiso = await cuerpoDe(await ajustar(SIN_PERMISO, UNIDAD_1A[SIN_PERMISO]), 403);
    expect(sinPermiso.detail.permiso_faltante).toBe("ajustar_saldo_inicial");
    const pendiente = await cuerpoDe(await ajustar(PENDIENTE, UNIDAD_1A[PENDIENTE]), 409);
    expect(pendiente).toEqual({ detail: "conflicto", campo: "estado_migracion" });
  });

  it("un GET a la ruta del ajuste es 405", async () => {
    const respuesta = await pedir(
      `/api/complejos/${CONFIRMADO}/unidades/${UNIDAD_1A[CONFIRMADO]}/ajustes-de-saldo-inicial`,
    );
    expect(respuesta.status).toBe(405);
  });
});
