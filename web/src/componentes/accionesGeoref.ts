"use server";

/**
 * D3 (tarea 6.1): puente server action para que `SelectorDeUbicacion`
 * (componente de cliente) pueda pedir georef sin exponer la API al
 * navegador (D11 del 3a) — las tres funciones de `lib/api/georef.ts` son
 * de servidor; esto las hace invocables desde un componente de cliente.
 */

import { departamentosDe, localidadesDe, provincias } from "../lib/api/georef";

export async function provinciasAction() {
  return provincias();
}

export async function departamentosDeAction(provinciaId: string) {
  return departamentosDe(provinciaId);
}

export async function localidadesDeAction(departamentoId: string) {
  return localidadesDe(departamentoId);
}
