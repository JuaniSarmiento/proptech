"use server";

/** Provisorio del rojo de la tarea 4.3. */

import type { EstadoAjuste } from "./Pantalla";

export async function ajustarSaldoInicialAction(
  _complejoId: string,
  _unidadId: string,
  _estadoPrevio: EstadoAjuste,
  _formData: FormData,
): Promise<EstadoAjuste> {
  return null;
}
