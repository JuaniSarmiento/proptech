/**
 * La API falsa de los pagos informados (change 8, H-025): 2501 y 2502 contestan las rutas de pagos como
 * la API real y guardan la última escritura; `user_vecina` trae sólo `informar_pago` y ve sólo sus
 * unidades; la descarga del comprobante es pública y sólo da el archivo para el token de prueba.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { TOKEN_DE_PRUEBA } from "./escenarios-liquidacion";
import { ADMINISTRACION, cabecerasDePrueba, crearToken, PUBLICA } from "./sesion-local";

const EDIFICIO = "00000000-0000-0000-0000-000000002501";
const FALLIDA = "00000000-0000-0000-0000-000000002502";
const COMPROBANTE = "00000000-0000-0000-0000-000000025900";
const INFORMADO = "00000000-0000-0000-0000-000000025001";
const CONFIRMADO = "00000000-0000-0000-0000-000000025002";
const U1A = "00000000-0000-0000-0000-000000025101";
const U2A = "00000000-0000-0000-0000-000000025103";
const U2B = "00000000-0000-0000-0000-000000025104";

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

const leer = (ruta: string, sub?: string) =>
  fetch(`${origen}${ruta}`, {
    headers: sub
      ? {
          authorization: `Bearer ${crearToken({ sub })}`,
          "x-proptech-administracion": ADMINISTRACION,
        }
      : cabecerasDePrueba(),
  });

const escribir = (ruta: string, cuerpo?: unknown) =>
  fetch(`${origen}${ruta}`, {
    method: "POST",
    headers: { ...cabecerasDePrueba(), "content-type": "application/json" },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });

const ultima = async () => (await leer("/api/__debug/ultima-escritura")).json();

const pagos = (id = EDIFICIO) => `/api/complejos/${id}/pagos`;

describe("api-falsa · pagos informados", () => {
  it("las unidades: la vecina ve 1A y 2B; el resto, las cuatro", async () => {
    const vecina = await (await leer(`${pagos()}/unidades`, "user_vecina")).json();
    expect(vecina.map((u: { identificador: string }) => u.identificador)).toEqual(["1A", "2B"]);
    const resto = await (await leer(`${pagos()}/unidades`)).json();
    expect(resto.map((u: { identificador: string }) => u.identificador)).toEqual([
      "1A",
      "1B",
      "2A",
      "2B",
    ]);
  });

  it("la sesión de la vecina trae sólo informar_pago en los dos edificios; la del resto, no", async () => {
    const vecina = await (await leer("/api/sesion", "user_vecina")).json();
    expect(vecina.administraciones[0].acciones).toEqual({
      administracion: [],
      todos_los_edificios: [],
      por_edificio: { [EDIFICIO]: ["informar_pago"], [FALLIDA]: ["informar_pago"] },
    });
    const otro = await (await leer("/api/sesion")).json();
    const acciones = otro.administraciones[0].acciones;
    expect(acciones.todos_los_edificios).toContain("confirmar_pago_informado");
    expect(acciones.todos_los_edificios).not.toContain("informar_pago");
    expect(Object.values(acciones.por_edificio).flat()).not.toContain("informar_pago");
  });

  it("la lista tiene un pago por estado, con su motivo, y el reimputado de H-026", async () => {
    const lista = await (await leer(pagos())).json();
    expect(lista.map((p: { estado: string }) => p.estado)).toEqual([
      "informado",
      "confirmado",
      "rechazado",
      "revertido",
      "confirmado",
    ]);
    expect(lista[4]).toMatchObject({
      numero_de_operacion: "11110005",
      partes: [{ identificador: "1A", identificador_vigente: "2A" }],
    });
    expect(lista[0]).toMatchObject({
      numero_de_operacion: "11110001",
      monto: "43350.00",
      partes: [{ identificador: "1A" }],
    });
    expect(lista[1]).toMatchObject({ numero_de_operacion: "11110002", monto: "37425.00" });
    expect(lista[2].motivo).toBe("El monto no coincide con el comprobante");
    expect(lista[3].motivo).toBe("Cheque rechazado");
  });

  it("la lectura da ok con la propuesta en 2501 y fallida y vacía en 2502, sin guardar los bytes", async () => {
    const cuerpo = new FormData();
    cuerpo.append("archivo", new Blob([new Uint8Array(64)], { type: "image/png" }), "c.png");
    const ok = await fetch(`${origen}${pagos()}/lectura`, {
      method: "POST",
      headers: cabecerasDePrueba(),
      body: cuerpo,
    });
    expect(ok.status).toBe(201);
    expect(await ok.json()).toEqual({
      comprobante_id: COMPROBANTE,
      lectura: "ok",
      propuesta: {
        banco: "Banco Nación",
        numero_de_operacion: "12345678",
        fecha: "2026-11-05",
        monto: "43350.00",
        cbu_origen: null,
      },
    });
    expect(await ultima()).toMatchObject({ metodo: "POST", url: `${pagos()}/lectura`, cuerpo: "" });
    const cuerpo2 = new FormData();
    cuerpo2.append("archivo", new Blob([new Uint8Array(64)], { type: "image/png" }), "c.png");
    const fallida = await fetch(`${origen}${pagos(FALLIDA)}/lectura`, {
      method: "POST",
      headers: cabecerasDePrueba(),
      body: cuerpo2,
    });
    expect(await fallida.json()).toMatchObject({
      lectura: "fallida",
      propuesta: { banco: null, monto: null },
    });
  });

  it("informar: 201 si las partes suman el monto y 422 partes si no, sin redondear", async () => {
    const base = {
      comprobante_id: COMPROBANTE,
      banco: "B",
      numero_de_operacion: "1",
      fecha_de_transferencia: "2026-11-05",
      monto: "80775.00",
    };
    const bien = await escribir(pagos(), {
      ...base,
      partes: [
        { unidad_id: U1A, importe: "43350.00" },
        { unidad_id: U2B, importe: "37425.00" },
      ],
    });
    expect(bien.status).toBe(201);
    expect((await ultima()).url).toBe(pagos());
    const mal = await escribir(pagos(), {
      ...base,
      partes: [
        { unidad_id: U1A, importe: "43350.00" },
        { unidad_id: U2B, importe: "37000.00" },
      ],
    });
    expect(mal.status).toBe(422);
    expect((await mal.json()).detail[0].loc).toEqual(["body", "partes"]);
    expect((JSON.parse((await ultima()).cuerpo) as { partes: unknown[] }).partes).toHaveLength(2);
  });

  it("confirmar y rechazar sólo admiten un informado; revertir y reimputar, un confirmado", async () => {
    expect((await escribir(`${pagos()}/${INFORMADO}/confirmacion`)).status).toBe(200);
    expect((await ultima()).url).toBe(`${pagos()}/${INFORMADO}/confirmacion`);
    expect((await escribir(`${pagos()}/${CONFIRMADO}/confirmacion`)).status).toBe(409);
    const rechazo = await escribir(`${pagos()}/${INFORMADO}/rechazo`, { motivo: "No coincide" });
    expect(await rechazo.json()).toEqual({ pago_id: INFORMADO, estado: "rechazado" });
    expect((await escribir(`${pagos()}/${INFORMADO}/rechazo`, {})).status).toBe(422);
    const reversion = await escribir(`${pagos()}/${CONFIRMADO}/reversion`, { motivo: "Cheque" });
    expect(await reversion.json()).toEqual({ pago_id: CONFIRMADO, estado: "revertido" });
    expect((await escribir(`${pagos()}/${INFORMADO}/reversion`, { motivo: "Cheque" })).status).toBe(
      409,
    );
    const reimputacion = await escribir(`${pagos()}/${CONFIRMADO}/reimputacion`, {
      desde_unidad_id: U2B,
      hacia_unidad_id: U2A,
      motivo: "Era de 2A",
    });
    expect(reimputacion.status).toBe(200);
    expect(
      (
        await escribir(`${pagos()}/${CONFIRMADO}/reimputacion`, {
          desde_unidad_id: U2B,
          hacia_unidad_id: U2B,
          motivo: "Era de 2A",
        })
      ).status,
    ).toBe(422);
    expect(
      (await escribir(`${pagos()}/00000000-0000-0000-0000-00000000dead/rechazo`, {})).status,
    ).toBe(404);
  });

  it("el enlace del comprobante da la dirección de descarga y la descarga es pública", async () => {
    const r = await escribir(`${pagos()}/${INFORMADO}/comprobante/enlace`);
    expect(r.status).toBe(201);
    expect((await r.json()).url).toBe(`/api/comprobantes/descarga?token=${TOKEN_DE_PRUEBA}`);
    const descarga = await fetch(
      `${origen}/api/comprobantes/descarga?token=${encodeURIComponent(TOKEN_DE_PRUEBA)}`,
    );
    expect(descarga.status).toBe(200);
    expect(descarga.headers.get("content-type")).toBe("image/png");
    const otro = await fetch(`${origen}/api/comprobantes/descarga?token=otro`);
    expect(otro.status).toBe(403);
  });
});
