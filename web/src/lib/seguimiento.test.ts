/**
 * Tests de `web/src/lib/seguimiento.ts` contra la misma tabla de casos que
 * pytest (D8, L-008, L-009). Cambio 1c, tarea 6.1.
 *
 * Escenarios de `trazabilidad-y-logs`: Mismos casos en la web y en la API
 * (lado TypeScript); UUID con espacios, tabulaciones, saltos de línea o
 * dígitos no ASCII; De la web a la API (reenvío).
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { cabecerasHaciaLaApi, requestIdDe, validarRequestId } from "./seguimiento";

// web/src/lib/seguimiento.test.ts -> ../../../config/contratos/request-id.json
// (contexto de build de la web es web/, config/ no se puede importar: se lee
// con fs en tiempo de test).
const TABLA = fileURLToPath(new URL("../../../config/contratos/request-id.json", import.meta.url));

type Caso = { entrada: string; normalizado?: string; motivo: string };
type Tabla = { validos: Caso[]; invalidos: Caso[] };

function tabla(): Tabla {
  return JSON.parse(readFileSync(TABLA, "utf-8")) as Tabla;
}

// Mismos motivos obligatorios que exige backend/tests/unitarios/test_seguimiento.py.
const MOTIVOS_OBLIGATORIOS = [
  "vacio",
  "largo_35",
  "largo_37",
  "sin_guiones",
  "llaves",
  "espacio_alrededor",
  "tabulacion_alrededor",
  "salto_de_linea_inicio",
  "salto_de_linea_final",
  "digito_no_ascii",
  "letra_ancho_completo",
  "script",
  "comillas",
  "inyeccion_sql",
];

const PATRON_UUID_CANONICO =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

describe("la tabla de casos", () => {
  it("tiene al menos un caso de cada motivo obligatorio", () => {
    const motivosPresentes = new Set(tabla().invalidos.map((caso) => caso.motivo));
    const faltantes = MOTIVOS_OBLIGATORIOS.filter((motivo) => !motivosPresentes.has(motivo));
    expect(faltantes).toEqual([]);
  });
});

describe("validarRequestId", () => {
  it("acepta y normaliza cada caso válido de la tabla", () => {
    for (const caso of tabla().validos) {
      expect(validarRequestId(caso.entrada)).toBe(caso.normalizado);
    }
  });

  it("rechaza cada caso inválido de la tabla", () => {
    for (const caso of tabla().invalidos) {
      expect(validarRequestId(caso.entrada)).toBeNull();
    }
  });
});

describe("requestIdDe", () => {
  it("reenvía normalizado un request-id válido", () => {
    const cabeceras = new Headers({
      "x-request-id": "3F2C1A00-0001-4001-8001-000000000001",
    });
    expect(requestIdDe(cabeceras)).toBe("3f2c1a00-0001-4001-8001-000000000001");
  });

  it("genera uno nuevo con forma de UUID cuando falta el encabezado", () => {
    const resultado = requestIdDe(new Headers());
    expect(PATRON_UUID_CANONICO.test(resultado)).toBe(true);
  });

  it("genera uno nuevo con forma de UUID ante un valor malicioso", () => {
    const cabeceras = new Headers({ "x-request-id": "' OR 1=1 --" });
    const resultado = requestIdDe(cabeceras);
    expect(resultado).not.toBe("' OR 1=1 --");
    expect(PATRON_UUID_CANONICO.test(resultado)).toBe(true);
  });
});

describe("cabecerasHaciaLaApi", () => {
  it("arma X-Request-ID con el valor de requestIdDe", () => {
    const entrada = new Headers({
      "x-request-id": "3f2c1a00-0001-4001-8001-000000000001",
    });
    const salida = cabecerasHaciaLaApi(entrada);
    expect(salida.get("X-Request-ID")).toBe("3f2c1a00-0001-4001-8001-000000000001");
  });

  it("arma X-Request-ID nuevo cuando no hay encabezado de entrada", () => {
    const salida = cabecerasHaciaLaApi(new Headers());
    expect(PATRON_UUID_CANONICO.test(salida.get("X-Request-ID") ?? "")).toBe(true);
  });
});
