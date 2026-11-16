/**
 * Los períodos de la lista de liquidaciones (H-017): el mes que se ofrece preparar. Todo con texto
 * `AAAA-MM`: un período nunca pasa por `Date` (se corre un día según la zona); sólo "hoy" sale del
 * reloj, y en la hora de Mendoza.
 */

import type { LiquidacionDeLaLista } from "../../../../lib/api/liquidaciones";

/** `"2026-11"` -> `"2026-12"`; `"2026-12"` -> `"2027-01"`. */
export function periodoSiguiente(periodo: string): string {
  const [anio, mes] = periodo.split("-").map(Number) as [number, number];
  return mes === 12
    ? `${anio + 1}-01`
    : `${String(anio).padStart(4, "0")}-${String(mes + 1).padStart(2, "0")}`;
}

/** El mes actual como `AAAA-MM`, en la hora de Mendoza. */
export function mesActualEnMendoza(ahora: Date = new Date()): string {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Argentina/Mendoza",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(ahora);
  const anio = partes.find((p) => p.type === "year")?.value ?? "";
  const mes = partes.find((p) => p.type === "month")?.value ?? "";
  return `${anio}-${mes}`;
}

/** El mes que se ofrece preparar: el siguiente al último período con una liquidación no anulada o,
 * si no hay ninguna, el mes actual. */
export function periodoParaPreparar(
  liquidaciones: LiquidacionDeLaLista[],
  ahora: Date = new Date(),
): string {
  const vigentes = liquidaciones
    .filter((l) => l.estado !== "anulada")
    .map((l) => l.periodo.slice(0, 7))
    .sort();
  const ultimo = vigentes.at(-1);
  return ultimo === undefined ? mesActualEnMendoza(ahora) : periodoSiguiente(ultimo);
}
