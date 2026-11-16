/**
 * La API falsa de distribuir y anular (change 7, H-014): 1401 (emitida) y 1402 (distribuida) dan la
 * preliquidación de noviembre como 409 `periodo_emitido`, su liquidación en la lista, y contestan
 * `POST .../distribucion` y `.../anulacion` con 200 guardando la última escritura.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const EMITIDA = "00000000-0000-0000-0000-000000001401";
const DISTRIBUIDA = "00000000-0000-0000-0000-000000001402";
const LIQUIDACION_EMITIDA = "00000000-0000-0000-0000-000000014011";

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

const escribir = (ruta: string, cuerpo?: unknown) =>
  fetch(`${origen}${ruta}`, {
    method: "POST",
    headers: { ...cabecerasDePrueba(), "content-type": "application/json" },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });

describe("api-falsa · el ciclo de la liquidación", () => {
  it.each([EMITIDA, DISTRIBUIDA])("%s: noviembre emitido es 409 periodo_emitido", async (id) => {
    const r = await leer(`/api/complejos/${id}/periodos/2026-11-01/preliquidacion`);
    expect(r.status).toBe(409);
    expect(await r.json()).toEqual({
      detail: "conflicto",
      campo: "periodo",
      motivo: "periodo_emitido",
    });
  });

  it("la lista trae la liquidación de noviembre con su estado y su total", async () => {
    const emitida = await (await leer(`/api/complejos/${EMITIDA}/liquidaciones`)).json();
    expect(emitida).toHaveLength(1);
    expect(emitida[0]).toMatchObject({
      liquidacion_id: LIQUIDACION_EMITIDA,
      periodo: "2026-11-01",
      estado: "emitida",
      total: "191500.00",
    });
    const distribuida = await (await leer(`/api/complejos/${DISTRIBUIDA}/liquidaciones`)).json();
    expect(distribuida[0]).toMatchObject({
      liquidacion_id: "00000000-0000-0000-0000-000000014021",
      estado: "distribuida",
    });
  });

  it("distribuir contesta 200 y guarda la escritura", async () => {
    const r = await escribir(
      `/api/complejos/${EMITIDA}/liquidaciones/${LIQUIDACION_EMITIDA}/distribucion`,
    );
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({ estado: "distribuida" });
    const ultima = await (await leer("/api/__debug/ultima-escritura")).json();
    expect(ultima.url).toBe(
      `/api/complejos/${EMITIDA}/liquidaciones/${LIQUIDACION_EMITIDA}/distribucion`,
    );
  });

  it("anular pide un motivo y lo guarda", async () => {
    const ruta = `/api/complejos/${EMITIDA}/liquidaciones/${LIQUIDACION_EMITIDA}/anulacion`;
    expect((await escribir(ruta, { motivo: "  " })).status).toBe(422);
    expect((await escribir(ruta, {})).status).toBe(422);
    const r = await escribir(ruta, { motivo: "Se cargó mal una factura" });
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({ estado: "anulada" });
    const ultima = await (await leer("/api/__debug/ultima-escritura")).json();
    expect(JSON.parse(ultima.cuerpo)).toEqual({ motivo: "Se cargó mal una factura" });
  });

  it("una liquidación que no es la del escenario es 404", async () => {
    const r = await escribir(
      `/api/complejos/${EMITIDA}/liquidaciones/00000000-0000-0000-0000-000000009999/distribucion`,
    );
    expect(r.status).toBe(404);
  });

  it("no rompe 1101: su preliquidación sigue siendo la de siempre", async () => {
    const r = await leer(
      "/api/complejos/00000000-0000-0000-0000-000000001101/periodos/2026-11-01/preliquidacion",
    );
    expect(r.status).toBe(200);
  });
});
