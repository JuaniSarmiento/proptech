/**
 * La API falsa de los documentos de la expensa (change 7, H-015): 1501 da noviembre emitido con los
 * dos documentos de `1A` (uno generado y uno fallido), y contesta el reproceso (202) y el enlace (201)
 * guardando la última escritura.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { TOKEN_DE_PRUEBA } from "./escenarios-liquidacion";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const EDIFICIO = "00000000-0000-0000-0000-000000001501";
const LIQUIDACION = "00000000-0000-0000-0000-000000015011";
const GENERADO = "00000000-0000-0000-0000-000000015101";
const FALLIDO = "00000000-0000-0000-0000-000000015102";

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

describe("api-falsa · los documentos de la expensa", () => {
  it("antes de toda escritura la depuración da una escritura vacía, nunca null", async () => {
    const ultima = await (await leer("/api/__debug/ultima-escritura")).json();
    expect(ultima).toEqual({ metodo: "", url: "", contentType: "", cuerpo: "" });
  });

  it("noviembre emitido es 409 periodo_emitido y la lista trae su liquidación emitida", async () => {
    const r = await leer(`/api/complejos/${EDIFICIO}/periodos/2026-11-01/preliquidacion`);
    expect(r.status).toBe(409);
    const lista = await (await leer(`/api/complejos/${EDIFICIO}/liquidaciones`)).json();
    expect(lista).toHaveLength(1);
    expect(lista[0]).toMatchObject({ liquidacion_id: LIQUIDACION, estado: "emitida" });
  });

  it("los documentos son la completa generada y la sin extraordinaria fallida de 1A", async () => {
    const r = await leer(`/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}/documentos`);
    expect(r.status).toBe(200);
    expect(await r.json()).toMatchObject([
      { documento_id: GENERADO, identificador: "1A", variante: "completa", estado: "generado" },
      {
        documento_id: FALLIDO,
        identificador: "1A",
        variante: "sin_extraordinaria",
        estado: "fallido",
        motivo: "sin fuentes",
      },
    ]);
  });

  it("el reproceso contesta 202 y guarda la escritura", async () => {
    const r = await escribir(
      `/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}/documentos/reproceso`,
    );
    expect(r.status).toBe(202);
    expect(await r.json()).toEqual({ encolados: 1 });
    const ultima = await (await leer("/api/__debug/ultima-escritura")).json();
    expect(ultima.url).toBe(
      `/api/complejos/${EDIFICIO}/liquidaciones/${LIQUIDACION}/documentos/reproceso`,
    );
  });

  it("el enlace del generado contesta 201 con una dirección de descarga y guarda la escritura", async () => {
    const r = await escribir(`/api/complejos/${EDIFICIO}/documentos/${GENERADO}/enlace`, {
      variante: "completa",
    });
    expect(r.status).toBe(201);
    expect((await r.json()).url).toBe(`/api/documentos/descarga?token=${TOKEN_DE_PRUEBA}`);
    const ultima = await (await leer("/api/__debug/ultima-escritura")).json();
    expect(ultima.url).toBe(`/api/complejos/${EDIFICIO}/documentos/${GENERADO}/enlace`);
    expect(JSON.parse(ultima.cuerpo)).toEqual({ variante: "completa" });
  });

  it("el enlace de un documento que no existe es 404", async () => {
    const r = await escribir(`/api/complejos/${EDIFICIO}/documentos/${FALLIDO}/enlace`, {
      variante: "sin_extraordinaria",
    });
    expect(r.status).toBe(404);
  });
});
