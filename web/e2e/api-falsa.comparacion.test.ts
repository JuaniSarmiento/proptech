/**
 * La API falsa de la comparación de saldos (change 5, H-008): tres edificios del contrato, por
 * HTTP real. Los de H-007 (701 a 703) siguen contestando lo suyo.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const CON_DIFERENCIAS = "00000000-0000-0000-0000-000000000801";
const SIN_DIFERENCIAS = "00000000-0000-0000-0000-000000000802";
const SIN_PERMISO = "00000000-0000-0000-0000-000000000803";
const IMPORTACION = "00000000-0000-0000-0000-000000008801";
const AVISO = "El primer interés del sistema cubre octubre de 2026";

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
const aceptar = (id: string, cuerpo: unknown = { importacion_id: IMPORTACION }) =>
  pedir(`/api/complejos/${id}/importaciones/aceptacion-de-diferencias`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(cuerpo),
  });

describe("api-falsa · comparación de saldos", () => {
  it("801: dos diferencias de signo opuesto, aviso en las tres, totales iguales y por aceptar", async () => {
    const cuerpo = await cuerpoDe(await comparacionDe(CON_DIFERENCIAS), 200);
    expect(cuerpo.importacion_id).toBe(IMPORTACION);
    expect(
      cuerpo.unidades.map((u: Record<string, string>) => [
        u.unidad,
        u.borrador,
        u.control,
        u.diferencia,
        u.aviso,
      ]),
    ).toEqual([
      ["1A", "169000.00", "159000.00", "10000.00", AVISO],
      ["1B", "105000.00", "105000.00", "0.00", AVISO],
      ["2A", "52000.00", "62000.00", "-10000.00", AVISO],
    ]);
    expect([cuerpo.total_borrador, cuerpo.total_control]).toEqual(["326000.00", "326000.00"]);
    expect(cuerpo.unidades_con_diferencia).toBe(2);
    expect(cuerpo.requiere_aceptacion).toBe(true);
    expect(cuerpo.aceptacion).toBeNull();
  });

  it("802: sin diferencias, sin aviso y nada que aceptar", async () => {
    const cuerpo = await cuerpoDe(await comparacionDe(SIN_DIFERENCIAS), 200);
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
  });

  it("803: la comparación es la del 801", async () => {
    const cuerpo = await cuerpoDe(await comparacionDe(SIN_PERMISO), 200);
    expect(cuerpo.unidades_con_diferencia).toBe(2);
    expect(cuerpo.requiere_aceptacion).toBe(true);
  });

  it("aceptar: 201 en el 801, 403 sin_permiso en el 803, y el cuerpo crudo queda como última escritura", async () => {
    const aceptada = await cuerpoDe(await aceptar(CON_DIFERENCIAS), 201);
    expect(aceptada.diferencias).toHaveLength(2);
    const ultima = await (await pedir("/api/__debug/ultima-escritura")).json();
    expect(ultima.metodo).toBe("POST");
    expect(ultima.url).toBe(
      `/api/complejos/${CON_DIFERENCIAS}/importaciones/aceptacion-de-diferencias`,
    );
    expect(JSON.parse(ultima.cuerpo)).toEqual({ importacion_id: IMPORTACION });
    expect((await cuerpoDe(await aceptar(SIN_PERMISO), 403)).detail).toMatchObject({
      codigo: "sin_permiso",
      permiso_faltante: "aceptar_diferencias_de_saldos",
    });
  });

  it("los métodos que no son los de cada ruta dan 405 y un edificio que no es del contrato da 404", async () => {
    expect((await aceptar(CON_DIFERENCIAS)).status).toBe(201);
    expect(
      (
        await pedir(`/api/complejos/${CON_DIFERENCIAS}/importaciones/comparacion`, {
          method: "POST",
        })
      ).status,
    ).toBe(405);
    expect(
      (await pedir(`/api/complejos/${CON_DIFERENCIAS}/importaciones/aceptacion-de-diferencias`))
        .status,
    ).toBe(405);
    expect((await comparacionDe("00000000-0000-0000-0000-000000000899")).status).toBe(404);
  });

  it("la subida y la plantilla de H-007 siguen igual", async () => {
    const plantilla = await pedir(
      "/api/complejos/00000000-0000-0000-0000-000000000701/importaciones/plantilla",
    );
    expect(plantilla.status).toBe(200);
  });

  it("las lecturas de la pantalla (edificio y resumen) las contesta como un edificio con la migración pendiente", async () => {
    for (const id of [CON_DIFERENCIAS, SIN_DIFERENCIAS, SIN_PERMISO]) {
      const resumen = await cuerpoDe(await pedir(`/api/complejos/${id}/resumen`), 200);
      expect(resumen.estado_migracion).toBe("pendiente");
      expect((await pedir(`/api/complejos/${id}`)).status).toBe(200);
    }
  });
});
