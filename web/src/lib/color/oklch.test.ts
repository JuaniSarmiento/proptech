/**
 * Conversión OKLCH → sRGB y contraste WCAG 2.2 (D10, tarea 3.5): la base
 * matemática que usa `tokens.test.ts` para verificar 4,5:1 por cálculo, no
 * a ojo.
 */

import { describe, expect, it } from "vitest";
import { oklchASrgbLineal, razonDeContraste } from "./oklch";

describe("oklchASrgbLineal", () => {
  it("blanco OKLCH (L=1, C=0, H=0) da sRGB lineal (1,1,1)", () => {
    const [r, g, b] = oklchASrgbLineal(1, 0, 0);
    expect(r).toBeCloseTo(1, 3);
    expect(g).toBeCloseTo(1, 3);
    expect(b).toBeCloseTo(1, 3);
  });

  it("negro OKLCH (L=0, C=0, H=0) da sRGB lineal (0,0,0)", () => {
    const [r, g, b] = oklchASrgbLineal(0, 0, 0);
    expect(r).toBeCloseTo(0, 3);
    expect(g).toBeCloseTo(0, 3);
    expect(b).toBeCloseTo(0, 3);
  });
});

describe("razonDeContraste", () => {
  it("blanco contra negro da 21:1 (el máximo de la fórmula WCAG)", () => {
    const blanco = oklchASrgbLineal(1, 0, 0);
    const negro = oklchASrgbLineal(0, 0, 0);
    expect(razonDeContraste(blanco, negro)).toBeCloseTo(21, 1);
  });

  it("un color contra sí mismo da 1:1", () => {
    const gris = oklchASrgbLineal(0.5, 0.02, 40);
    expect(razonDeContraste(gris, gris)).toBeCloseTo(1, 3);
  });

  it("es simétrica: no importa qué color va primero", () => {
    const a = oklchASrgbLineal(0.97, 0.006, 75);
    const b = oklchASrgbLineal(0.22, 0.012, 55);
    expect(razonDeContraste(a, b)).toBeCloseTo(razonDeContraste(b, a), 6);
  });
});
