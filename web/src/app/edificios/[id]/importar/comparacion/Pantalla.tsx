"use client";

import type { ComparacionDelBorrador } from "../../../../../lib/api/importaciones";

export type EstadoAceptacion = null;
type AccionAceptar = (
  estadoPrevio: EstadoAceptacion,
  formData: FormData,
) => Promise<EstadoAceptacion>;

type Props = {
  id: string;
  nombreEdificio: string;
  comparacion: ComparacionDelBorrador;
  accionAceptar: AccionAceptar;
};

export function PantallaComparacion(_props: Props) {
  return null;
}

export function PantallaSinBorrador(_props: { id: string; nombreEdificio: string }) {
  return null;
}
