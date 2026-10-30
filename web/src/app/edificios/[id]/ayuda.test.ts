import { expect, it } from "vitest";
import { AYUDA_RESUMEN } from "./ayuda";

// pulido-2 (3d), escenario "Ejemplo de la ayuda": el flujo real tiene siete pasos
// desde el 3c (ubicación, unidades, coeficientes, grupos, categorías, intereses y
// vencimiento, saldos previos); la ayuda no puede seguir hablando de seis.
const textosDeLaAyuda = [
  AYUDA_RESUMEN.paraQueSirve,
  ...AYUDA_RESUMEN.pasos,
  AYUDA_RESUMEN.ejemplo,
  AYUDA_RESUMEN.yDespues,
];

// 4.3 (F4 del rompedor): un edificio recién creado ya tiene hechos ubicación, grupos,
// categorías e intereses y vencimiento (`lectura.py`, fijado por
// `test_resumen_puesta_a_punto.py::test_edificio_recien_creado`): arranca en 4 de 7 y,
// con unidades (con piso) y coeficientes, queda en 6 de 7. Sólo se exige el texto; la
// sincronía automática con ese cálculo es deuda (C-26).
it('el ejemplo arranca en "4 de 7 pasos" y la barra queda en "6 de 7"', () => {
  expect(AYUDA_RESUMEN.ejemplo).toContain("arranca en 4 de 7 pasos");
  expect(AYUDA_RESUMEN.ejemplo).toContain("6 de 7");
  expect(AYUDA_RESUMEN.ejemplo).not.toMatch(/\b[02] de 7\b/);
});

it('ningún texto de la ayuda habla de "de 6"', () => {
  for (const texto of textosDeLaAyuda) {
    expect(texto).not.toMatch(/\bde 6\b/);
  }
});

it("el cierre habla de los siete pasos", () => {
  expect(AYUDA_RESUMEN.yDespues).toContain("siete pasos");
});
