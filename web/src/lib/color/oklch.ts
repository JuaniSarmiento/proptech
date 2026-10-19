/**
 * Conversión OKLCH → sRGB lineal y contraste WCAG 2.2 AA (D10, tarea 3.5).
 *
 * Fórmulas de Björn Ottosson (OKLab/OKLCH, dominio público). Se trabaja en
 * sRGB LINEAL de punta a punta porque la luminancia relativa de WCAG usa
 * justo esos coeficientes (0.2126/0.7152/0.0722) sobre el canal lineal: no
 * hace falta codificar a gamma y volver a decodificar.
 */

type RgbLineal = readonly [number, number, number];

function recortar(valor: number): number {
  return Math.min(1, Math.max(0, valor));
}

/** OKLCH (L en 0–1, C de croma, H en grados) a sRGB lineal (sin gamma),
 * recortado a [0,1]. */
export function oklchASrgbLineal(l: number, c: number, hGrados: number): RgbLineal {
  const hRad = (hGrados * Math.PI) / 180;
  const a = c * Math.cos(hRad);
  const b = c * Math.sin(hRad);

  const l_ = l + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = l - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = l - 0.0894841775 * a - 1.291485548 * b;

  const lCubo = l_ ** 3;
  const mCubo = m_ ** 3;
  const sCubo = s_ ** 3;

  const r = 4.0767416621 * lCubo - 3.3077115913 * mCubo + 0.2309699292 * sCubo;
  const g = -1.2684380046 * lCubo + 2.6097574011 * mCubo - 0.3413193965 * sCubo;
  const bl = -0.0041960863 * lCubo - 0.7034186147 * mCubo + 1.707614701 * sCubo;

  return [recortar(r), recortar(g), recortar(bl)];
}

/** Luminancia relativa de WCAG, sobre un canal sRGB YA lineal (0–1). */
function luminanciaRelativa([r, g, b]: RgbLineal): number {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razón de contraste WCAG entre dos colores en sRGB lineal: (L1+0.05)/(L2+0.05),
 * con el más claro siempre arriba. Simétrica. */
export function razonDeContraste(colorA: RgbLineal, colorB: RgbLineal): number {
  const luminanciaA = luminanciaRelativa(colorA);
  const luminanciaB = luminanciaRelativa(colorB);
  const [clara, oscura] =
    luminanciaA >= luminanciaB ? [luminanciaA, luminanciaB] : [luminanciaB, luminanciaA];
  return (clara + 0.05) / (oscura + 0.05);
}
