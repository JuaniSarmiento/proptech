/**
 * La API falsa de emitir (change 7, H-013): 1101 y 1301 emiten con 201, 1201 (con un duro) da 422, y
 * el pedido se valida como la API real (huella, alertas exactas, vencimiento corrido).
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const BASE = "00000000-0000-0000-0000-000000001101";
const CON_DURO = "00000000-0000-0000-0000-000000001201";
const CON_BLOQUEANTE = "00000000-0000-0000-0000-000000001301";
const HUELLA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const EMISION = "33333333-3333-4333-8333-333333333333";

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

const emitir = (id: string, cuerpo: unknown, periodo = "2026-11-01") =>
  fetch(`${origen}/api/complejos/${id}/periodos/${periodo}/emision`, {
    method: "POST",
    headers: { ...cabecerasDePrueba(), "content-type": "application/json" },
    body: JSON.stringify(cuerpo),
  });

const pedido = (extra: Record<string, unknown> = {}) => ({
  emision_id: EMISION,
  huella: HUELLA,
  alertas_aceptadas: [],
  ...extra,
});

describe("api-falsa · emitir", () => {
  it("1101: 201 con una obligación por unidad y la ordinaria de 1B con su multa", async () => {
    const r = await emitir(BASE, pedido());
    expect(r.status).toBe(201);
    const cuerpo = await r.json();
    expect(cuerpo).toMatchObject({
      emision_id: EMISION,
      periodo: "2026-11-01",
      vencimiento: "2026-11-10",
    });
    expect(
      cuerpo.obligaciones.map((o: Record<string, string>) => [o.identificador, o.ordinaria]),
    ).toEqual([
      ["1A", "27000.00"],
      ["1B", "32000.00"],
      ["2A", "47500.00"],
      ["2B", "28500.00"],
    ]);
  });

  it("el vencimiento corrido vuelve en cada obligación", async () => {
    const r = await emitir(
      BASE,
      pedido({ vencimiento: { fecha: "2026-11-12", motivo: "Feriado" } }),
    );
    const cuerpo = await r.json();
    expect(cuerpo.vencimiento).toBe("2026-11-12");
    expect(new Set(cuerpo.obligaciones.map((o: Record<string, string>) => o.vencimiento))).toEqual(
      new Set(["2026-11-12"]),
    );
  });

  it("1301 exige aceptar exactamente su bloqueante", async () => {
    const sin = await emitir(CON_BLOQUEANTE, pedido());
    expect(sin.status).toBe(409);
    expect(await sin.json()).toMatchObject({
      campo: "alertas_aceptadas",
      motivo: "alertas_distintas",
    });
    const con = await emitir(CON_BLOQUEANTE, pedido({ alertas_aceptadas: ["gastos_en_revision"] }));
    expect(con.status).toBe(201);
  });

  it("una huella distinta es un 409 preliquidacion_cambio", async () => {
    const r = await emitir(BASE, pedido({ huella: "x".repeat(64) }));
    expect(r.status).toBe(409);
    expect(await r.json()).toMatchObject({ campo: "huella", motivo: "preliquidacion_cambio" });
  });

  it("1201 tiene un duro: 422 control_duro", async () => {
    const r = await emitir(CON_DURO, pedido());
    expect(r.status).toBe(422);
    expect((await r.json()).detail).toBe("control_duro");
  });

  it.each([
    ["sin emision_id", { emision_id: "no" }],
    ["sin motivo", { vencimiento: { fecha: "2026-11-12", motivo: " " } }],
    ["antes del período", { vencimiento: { fecha: "2026-10-31", motivo: "x" } }],
  ])("un pedido %s es un 422", async (_nombre, extra) => {
    expect((await emitir(BASE, pedido(extra))).status).toBe(422);
  });

  it("deja la última escritura para los e2e y un período ajeno no existe", async () => {
    await emitir(BASE, pedido());
    const ultima = await (
      await fetch(`${origen}/api/__debug/ultima-escritura`, { headers: cabecerasDePrueba() })
    ).json();
    expect(ultima.url).toBe(`/api/complejos/${BASE}/periodos/2026-11-01/emision`);
    expect((await emitir(BASE, pedido(), "2026-12-01")).status).toBe(404);
  });
});
