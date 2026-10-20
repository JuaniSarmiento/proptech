/**
 * Contraste WCAG 2.2 AA de los tokens de color, por cálculo sobre los
 * valores REALES de `tokens.css` (D10, tarea 3.5): si alguien cambia un
 * valor y rompe 4,5:1, este test lo dice antes que un ojo lo note.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { oklchASrgbLineal, razonDeContraste } from "../lib/color/oklch";

const _TOKENS_CSS = readFileSync(join(__dirname, "tokens.css"), "utf-8");

/** Lee `--nombre: oklch(L% C H);` de `tokens.css`. Explota si el token no
 * está: un token ausente no puede dar "contraste ok" por omisión. */
function tokenOklch(nombre: string): readonly [number, number, number] {
  const patron = new RegExp(`--${nombre}:\\s*oklch\\(([0-9.]+)%\\s+([0-9.]+)\\s+([0-9.]+)\\)`);
  const coincidencia = _TOKENS_CSS.match(patron);
  if (!coincidencia) {
    throw new Error(`token --${nombre} no encontrado en tokens.css`);
  }
  const [, lPorciento, croma, tono] = coincidencia as unknown as [string, string, string, string];
  return [Number(lPorciento) / 100, Number(croma), Number(tono)];
}

function contrasteDeTokens(nombreA: string, nombreB: string): number {
  const [la, ca, ha] = tokenOklch(nombreA);
  const [lb, cb, hb] = tokenOklch(nombreB);
  return razonDeContraste(oklchASrgbLineal(la, ca, ha), oklchASrgbLineal(lb, cb, hb));
}

describe("contraste de los tokens de color (D10)", () => {
  it.each([
    ["color-tinta", "color-papel"],
    ["color-papel", "color-terracota"],
    ["color-terracota", "color-papel"],
    ["color-grafito", "color-papel"],
    ["color-advertencia", "color-papel"],
  ])("%s sobre %s llega a 4,5:1", (texto, fondo) => {
    expect(contrasteDeTokens(texto, fondo)).toBeGreaterThanOrEqual(4.5);
  });
});

describe("escala tipográfica aplicada (tarea 5.2)", () => {
  it("h1 usa --tipo-titular y h2 usa --tipo-titulo (D10: la escala declarada tiene que llegar a los títulos)", () => {
    expect(_TOKENS_CSS).toMatch(/\bh1\s*\{[^}]*font-size:\s*var\(--tipo-titular\)/);
    expect(_TOKENS_CSS).toMatch(/\bh2\s*\{[^}]*font-size:\s*var\(--tipo-titulo\)/);
  });
});

describe("prefers-reduced-motion (tarea 3.6)", () => {
  it("pone --duracion-transicion en 0ms dentro de @media (prefers-reduced-motion: reduce)", () => {
    const bloqueReducido = _TOKENS_CSS.match(
      /@media \(prefers-reduced-motion: reduce\)\s*\{[^}]*\{([^}]*)\}/,
    );
    expect(bloqueReducido).not.toBeNull();
    expect(bloqueReducido?.[1]).toMatch(/--duracion-transicion:\s*0ms/);
  });
});
