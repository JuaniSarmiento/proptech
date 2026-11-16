/**
 * La API falsa de la lista de liquidaciones y del cargo cobrado de menos (change 7, H-017): 1701 da la
 * lista, 1401 la liquidación emitida con `unidades` y el `POST` del cargo, y la sesión da
 * `ver_liquidaciones` y `corregir_movimiento` sólo en los edificios que corresponden.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const EMITIDA = "00000000-0000-0000-0000-000000001401";
const LISTA = "00000000-0000-0000-0000-000000001701";
const SIN_VER = "00000000-0000-0000-0000-000000001702";
const SIN_CORREGIR = "00000000-0000-0000-0000-000000001703";

let servidor: Server;
let origen: string;

beforeAll(async () => {
  servidor = crearServidor({ jwtKey: PUBLICA, origen: "http://127.0.0.1:3100" });
  await new Promise<void>((resolve) => servidor.listen(0, resolve));
  const direccion = servidor.address();
  origen = `http://127.0.0.1:${typeof direccion === "object" && direccion ? direccion.port : 0}`;
});

afterAll(() => {
  servidor.close();
});

const leer = (ruta: string) => fetch(`${origen}${ruta}`, { headers: cabecerasDePrueba() });

describe("api-falsa · la lista de liquidaciones (1701)", () => {
  it("trae noviembre distribuida y octubre anulada, la más nueva primero", async () => {
    const lista = await (await leer(`/api/complejos/${LISTA}/liquidaciones`)).json();
    expect(
      lista.map((l: { periodo: string; estado: string; total: string }) => [
        l.periodo,
        l.estado,
        l.total,
      ]),
    ).toEqual([
      ["2026-11-01", "distribuida", "191500.00"],
      ["2026-10-01", "anulada", "180000.00"],
    ]);
  });
});

describe("api-falsa · la emitida con unidades (1401)", () => {
  it("la liquidación trae lo que paga cada unidad, con la obligación de 1A", async () => {
    const r = await leer(
      `/api/complejos/${EMITIDA}/liquidaciones/00000000-0000-0000-0000-000000014011`,
    );
    expect(r.status).toBe(200);
    const cuerpo = await r.json();
    expect(cuerpo.unidades).toHaveLength(4);
    expect(cuerpo.unidades[0]).toMatchObject({
      unidad_id: "00000000-0000-0000-0000-000000140111",
      identificador: "1A",
      ordinaria: "27000.00",
      saldo_anterior: "0.00",
      total: "43350.00",
      obligacion_id: "00000000-0000-0000-0000-000000140101",
    });
  });

  it("el cargo cobrado de menos contesta 201 y guarda la escritura", async () => {
    const pedido = {
      operacion_id: "00000000-0000-0000-0000-00000000a001",
      obligacion_origen_id: "00000000-0000-0000-0000-000000140101",
      importe: "1500.00",
      componente: "ordinaria",
      motivo: "Faltó",
    };
    const ruta = `/api/complejos/${EMITIDA}/unidades/00000000-0000-0000-0000-000000140111/cargos-cobrados-de-menos`;
    const r = await fetch(`${origen}${ruta}`, {
      method: "POST",
      headers: { ...cabecerasDePrueba(), "content-type": "application/json" },
      body: JSON.stringify(pedido),
    });
    expect(r.status).toBe(201);
    expect(await r.json()).toMatchObject({ importe: "1500.00", componente: "ordinaria" });
    const escrita = await (await leer("/api/__debug/ultima-escritura")).json();
    expect(escrita.url).toBe(ruta);
    expect(JSON.parse(escrita.cuerpo)).toEqual(pedido);
  });
});

describe("api-falsa · las acciones por edificio en la sesión", () => {
  async function accionesDe(edificio: string): Promise<string[]> {
    const sesion = await (await leer("/api/sesion")).json();
    const { todos_los_edificios, por_edificio } = sesion.administraciones[0].acciones;
    return [...todos_los_edificios, ...(por_edificio[edificio] ?? [])];
  }

  it("1401 y 1701 tienen las dos; 1703 sólo ver; 1702 ninguna", async () => {
    for (const edificio of [EMITIDA, LISTA]) {
      const acciones = await accionesDe(edificio);
      expect(acciones).toContain("ver_liquidaciones");
      expect(acciones).toContain("corregir_movimiento");
    }
    const sinCorregir = await accionesDe(SIN_CORREGIR);
    expect(sinCorregir).toContain("ver_liquidaciones");
    expect(sinCorregir).not.toContain("corregir_movimiento");
    const sinVer = await accionesDe(SIN_VER);
    expect(sinVer).not.toContain("ver_liquidaciones");
    expect(sinVer).not.toContain("corregir_movimiento");
  });
});
