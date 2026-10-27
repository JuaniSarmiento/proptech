/**
 * D7 (tarea 5.4): el máximo de la web contra el contrato de la API.
 * `backend/src/proptech_core/complejos/aplicacion/unidades.py` exige
 * `identificador: Field(max_length=40)`; `grupos.py` exige
 * `re.fullmatch(r"[a-z][a-z0-9_]{0,39}", ...)` para la clave (40
 * caracteres: 1 + 39). Estos valores no viajan en ningún fixture (son
 * límites de ENTRADA, no de lectura, L-047) — se comparan acá contra el
 * número literal, documentado con su archivo de origen en `limites.ts`.
 */
import { expect, it } from "vitest";
import {
  CLAVE_MAXIMO,
  COEFICIENTE_MAXIMO,
  claveInvalida,
  IDENTIFICADOR_MAXIMO,
  identificadorDemasiadoLargo,
  PATRON_CLAVE,
  pareceCoeficienteComoPorcentaje,
} from "./limites";

it("identificador: 40, igual que unidades.py", () => {
  expect(IDENTIFICADOR_MAXIMO).toBe(40);
  expect(identificadorDemasiadoLargo("a".repeat(40))).toBe(false);
  expect(identificadorDemasiadoLargo("a".repeat(41))).toBe(true);
});

it("clave: mismo patrón que grupos.py (ASCII, empieza con letra, hasta 40)", () => {
  expect(CLAVE_MAXIMO).toBe(40);
  expect(PATRON_CLAVE.test("pileta")).toBe(true);
  expect(PATRON_CLAVE.test("pileta_1")).toBe(true);
  for (const invalida of ["Pileta", "pileta-1", "1pileta", "a".repeat(41)]) {
    expect(claveInvalida(invalida)).toBe(true);
  }
});

it("coeficiente: 0 a 1, nunca una proporción mayor a 1 (porcentaje mal cargado)", () => {
  expect(COEFICIENTE_MAXIMO).toBe(1);
  expect(pareceCoeficienteComoPorcentaje("0.5")).toBe(false);
  expect(pareceCoeficienteComoPorcentaje("1")).toBe(false);
  expect(pareceCoeficienteComoPorcentaje("50")).toBe(true);
  expect(pareceCoeficienteComoPorcentaje("100")).toBe(true);
});
