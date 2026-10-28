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

it('el ejemplo arranca en "0 de 7 pasos" y la barra avanza a "2 de 7"', () => {
  expect(AYUDA_RESUMEN.ejemplo).toContain("0 de 7 pasos");
  expect(AYUDA_RESUMEN.ejemplo).toContain("2 de 7");
});

it('ningún texto de la ayuda habla de "de 6"', () => {
  for (const texto of textosDeLaAyuda) {
    expect(texto).not.toMatch(/\bde 6\b/);
  }
});

it("el cierre habla de los siete pasos", () => {
  expect(AYUDA_RESUMEN.yDespues).toContain("siete pasos");
});
