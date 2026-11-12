/**
 * La API falsa de la confirmación de saldos (change 5, H-009): los cuatro edificios del contrato
 * (901 a 904), por HTTP real. Los de H-007 (701 a 703) y H-008 (801 a 803) siguen contestando lo
 * suyo.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const PENDIENTE = "00000000-0000-0000-0000-000000000901";
const CONFIRMADO = "00000000-0000-0000-0000-000000000902";
const CON_DIFERENCIAS = "00000000-0000-0000-0000-000000000903";
const SIN_PERMISO = "00000000-0000-0000-0000-000000000904";
const IMPORTACION = "00000000-0000-0000-0000-000000009901";

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

const comparacionDe = (id: string) => pedir(`/api/complejos/${id}/importaciones/comparacion`);

/** El cuerpo de una respuesta con el estado esperado: falla por `expect`, no por un JSON vacío. */
async function cuerpoDe(respuesta: Response, estado: number) {
  expect(respuesta.status).toBe(estado);
  return respuesta.json();
}

const confirmar = (id: string, cuerpo: unknown = { importacion_id: IMPORTACION }) =>
  pedir(`/api/complejos/${id}/importaciones/confirmacion`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(cuerpo),
  });

describe("api-falsa · confirmar saldos", () => {
  it("901 y 904: sin diferencias, sin aviso y nada que aceptar, con la importación del contrato", async () => {
    for (const id of [PENDIENTE, SIN_PERMISO]) {
      const cuerpo = await cuerpoDe(await comparacionDe(id), 200);
      expect(cuerpo.importacion_id).toBe(IMPORTACION);
      expect(cuerpo.unidades).toHaveLength(1);
      expect(cuerpo.unidades[0]).toMatchObject({
        unidad: "1A",
        borrador: "169000.00",
        control: "169000.00",
        diferencia: "0.00",
        aviso: null,
      });
      expect(cuerpo.unidades_con_diferencia).toBe(0);
      expect(cuerpo.requiere_aceptacion).toBe(false);
      expect(cuerpo.aceptacion).toBeNull();
    }
  });

  it("903: una diferencia sin aceptar", async () => {
    const cuerpo = await cuerpoDe(await comparacionDe(CON_DIFERENCIAS), 200);
    expect(cuerpo.unidades[0]).toMatchObject({
      unidad: "1A",
      borrador: "169000.00",
      control: "159000.00",
      diferencia: "10000.00",
    });
    expect(cuerpo.unidades_con_diferencia).toBe(1);
    expect(cuerpo.requiere_aceptacion).toBe(true);
  });

  it("confirmar: 201 en el 901 con el cuerpo del contrato, y el cuerpo crudo queda como última escritura", async () => {
    const confirmada = await cuerpoDe(await confirmar(PENDIENTE), 201);
    expect(confirmada).toMatchObject({
      importacion_id: IMPORTACION,
      estado_migracion: "confirmada",
      totales: { capital: "320000.00", interes_importado: "6000.00", credito: "6000.00" },
    });
    expect(typeof confirmada.carga_id).toBe("string");
    expect(typeof confirmada.confirmada_por).toBe("string");
    expect(Number.isNaN(Date.parse(confirmada.confirmada_en))).toBe(false);
    const ultima = await (await pedir("/api/__debug/ultima-escritura")).json();
    expect(ultima.metodo).toBe("POST");
    expect(ultima.url).toBe(`/api/complejos/${PENDIENTE}/importaciones/confirmacion`);
    expect(JSON.parse(ultima.cuerpo)).toEqual({ importacion_id: IMPORTACION });
  });

  it("confirmar: 403 sin_permiso en el 904", async () => {
    expect((await cuerpoDe(await confirmar(SIN_PERMISO), 403)).detail).toMatchObject({
      codigo: "sin_permiso",
      permiso_faltante: "confirmar_saldos_iniciales",
    });
  });

  it("902: el resumen y el edificio dicen confirmada, con el paso 7 hecho; los otros tres, pendiente", async () => {
    const resumen = await cuerpoDe(await pedir(`/api/complejos/${CONFIRMADO}/resumen`), 200);
    expect(resumen.estado_migracion).toBe("confirmada");
    expect(resumen.pasos.saldos_previos).toBe("hecho");
    expect((await pedir(`/api/complejos/${CONFIRMADO}`)).status).toBe(200);
    for (const id of [PENDIENTE, CON_DIFERENCIAS, SIN_PERMISO]) {
      const otro = await cuerpoDe(await pedir(`/api/complejos/${id}/resumen`), 200);
      expect(otro.estado_migracion).toBe("pendiente");
      expect(otro.pasos.saldos_previos).toBe("falta");
    }
  });

  it("los métodos que no son los de cada ruta dan 405 y un edificio que no es del contrato da 404", async () => {
    expect((await pedir(`/api/complejos/${PENDIENTE}/importaciones/confirmacion`)).status).toBe(
      405,
    );
    expect(
      (await pedir(`/api/complejos/${PENDIENTE}/importaciones/comparacion`, { method: "POST" }))
        .status,
    ).toBe(405);
    expect((await comparacionDe("00000000-0000-0000-0000-000000000999")).status).toBe(404);
  });

  it("la comparación de H-008 y la subida de H-007 siguen igual", async () => {
    const h008 = await cuerpoDe(await comparacionDe("00000000-0000-0000-0000-000000000801"), 200);
    expect(h008.unidades_con_diferencia).toBe(2);
    expect(
      (await pedir("/api/complejos/00000000-0000-0000-0000-000000000701/importaciones/plantilla"))
        .status,
    ).toBe(200);
  });
});
