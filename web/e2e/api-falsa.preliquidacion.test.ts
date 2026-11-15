/**
 * La API falsa de la preliquidación (change 7, H-011): tres edificios del contrato, por HTTP real.
 * Un doble que no cierra al centavo engañaría a la pantalla, así que acá se prueba que sus sumas
 * cierran (en centavos enteros, nunca con punto flotante).
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

const BASE = "00000000-0000-0000-0000-000000001101";
const FONDO_CERO = "00000000-0000-0000-0000-000000001102";
const SIN_ANTERIOR = "00000000-0000-0000-0000-000000001103";

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

const preliquidacionDe = (id: string, periodo = "2026-11-01") =>
  fetch(`${origen}/api/complejos/${id}/periodos/${periodo}/preliquidacion`, {
    headers: cabecerasDePrueba(),
  });

function centavos(texto: string): bigint {
  expect(texto).toMatch(/^-?[0-9]+\.[0-9]{2}$/);
  return BigInt(texto.replace(".", ""));
}

type Unidad = Record<string, string | unknown[]>;

describe("api-falsa · preliquidación", () => {
  it("1101: la base de los ejemplos, unidad por unidad y con total 191.500,00", async () => {
    const respuesta = await preliquidacionDe(BASE);
    expect(respuesta.status).toBe(200);
    const cuerpo = await respuesta.json();
    expect(cuerpo.periodo).toBe("2026-11-01");
    expect(cuerpo.vencimiento).toBe("2026-11-10");
    expect(cuerpo.porcentaje_fondo).toBe("5.00");
    expect(cuerpo.huella).toMatch(/^[0-9a-f]{64}$/);
    expect(
      cuerpo.unidades.map((u: Unidad) => [u.identificador, u.total, u.fondo_de_reserva]),
    ).toEqual([
      ["1A", "43350.00", "1350.00"],
      ["1B", "48350.00", "1350.00"],
      ["2A", "62375.00", "2375.00"],
      ["2B", "37425.00", "1425.00"],
    ]);
    expect(cuerpo.unidades[1].cargos_particulares).toEqual([
      { concepto: "Multa", importe: "5000.00" },
    ]);
    expect(cuerpo.totales.total).toBe("191500.00");
    expect(cuerpo.bloques.ordinario.categorias[0]).toMatchObject({
      nombre: "Limpieza",
      importe: "90000.00",
      porcentaje: "69.23",
    });
    expect(cuerpo.controles).toEqual([]);
  });

  for (const [nombre, id] of [
    ["1101", BASE],
    ["1102", FONDO_CERO],
  ] as const) {
    it(`${nombre}: las sumas cierran al centavo`, async () => {
      const cuerpo = await (await preliquidacionDe(id)).json();
      const t = cuerpo.totales;
      const unidades: Unidad[] = cuerpo.unidades;
      const suma = (campo: string) =>
        unidades.reduce((acumulado, u) => acumulado + centavos(u[campo] as string), 0n);
      const cargos = unidades.reduce(
        (acumulado, u) =>
          acumulado +
          (u.cargos_particulares as { importe: string }[]).reduce(
            (a, c) => a + centavos(c.importe),
            0n,
          ),
        0n,
      );
      expect(suma("ordinaria") + suma("extraordinaria")).toBe(
        centavos(t.gastos) - centavos(t.notas_de_credito),
      );
      expect(suma("fondo_de_reserva")).toBe(centavos(t.fondo_de_reserva));
      expect(cargos).toBe(centavos(t.cargos_particulares));
      expect(centavos(t.prorrateado)).toBe(
        centavos(t.gastos) - centavos(t.notas_de_credito) + centavos(t.fondo_de_reserva),
      );
      expect(suma("total")).toBe(centavos(t.total));
      expect(centavos(t.total)).toBe(
        centavos(t.prorrateado) + centavos(t.cargos_particulares) + centavos(t.intereses),
      );
      for (const u of unidades) {
        expect(centavos(u.total as string)).toBe(
          centavos(u.ordinaria as string) +
            centavos(u.fondo_de_reserva as string) +
            centavos(u.extraordinaria as string) +
            (u.cargos_particulares as { importe: string }[]).reduce(
              (a, c) => a + centavos(c.importe),
              0n,
            ) +
            centavos(u.intereses as string),
        );
      }
    });
  }

  it("1102: la misma base con fondo 0%, sin fondo en ninguna unidad", async () => {
    const cuerpo = await (await preliquidacionDe(FONDO_CERO)).json();
    expect(cuerpo.porcentaje_fondo).toBe("0.00");
    expect(new Set(cuerpo.unidades.map((u: Unidad) => u.fondo_de_reserva))).toEqual(
      new Set(["0.00"]),
    );
    expect(cuerpo.totales.fondo_de_reserva).toBe("0.00");
    expect(cuerpo.unidades.map((u: Unidad) => u.ordinaria)).toEqual([
      "27000.00",
      "27000.00",
      "47500.00",
      "28500.00",
    ]);
  });

  it("1103: 409 con el motivo del período anterior sin emitir", async () => {
    const respuesta = await preliquidacionDe(SIN_ANTERIOR);
    expect(respuesta.status).toBe(409);
    expect(await respuesta.json()).toEqual({
      detail: "conflicto",
      campo: "periodo",
      motivo: "periodo_anterior_sin_emitir",
    });
  });

  it("otro período, o un edificio que no es del contrato, no existe en este doble", async () => {
    expect((await preliquidacionDe(BASE, "2026-12-01")).status).toBe(404);
    expect((await preliquidacionDe("00000000-0000-0000-0000-000000009999")).status).toBe(404);
  });

  it("sin sesión da 401, como el resto de la API falsa", async () => {
    const respuesta = await fetch(
      `${origen}/api/complejos/${BASE}/periodos/2026-11-01/preliquidacion`,
    );
    expect(respuesta.status).toBe(401);
  });
});
