"use client";

/** Provisorio del rojo de la tarea 4.3: todavía no pinta nada. */

export type EstadoAjuste = {
  error?: string;
  erroresPorCampo?: Record<string, string>;
  ajustado?: {
    importe: string;
    motivo: string;
  };
} | null;

export function PantallaAjuste(_props: Record<string, unknown>) {
  return null;
}
