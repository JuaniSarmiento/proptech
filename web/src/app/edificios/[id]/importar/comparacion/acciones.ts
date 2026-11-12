"use server";

import type { EstadoAceptacion } from "./Pantalla";

export async function aceptarDiferenciasAction(
  _complejoId: string,
  _estadoPrevio: EstadoAceptacion,
  _formData: FormData,
): Promise<EstadoAceptacion> {
  return null;
}
