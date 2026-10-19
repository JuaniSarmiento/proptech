/**
 * "Mis edificios" (tarea 4.1): lista, ver uno y crear (D2, D5). El resumen
 * de cada edificio (pasos, estado de coeficientes) vive en `resumen.ts`,
 * no acá: `GET /api/complejos` nunca trajo esos campos a propósito (D5 —
 * también lo ve el vecino, D-076).
 */

import { pedirApi, type ResultadoApi } from "./cliente";
import type { Edificio, EdificioDeLista } from "./tipos";

export async function listaDeEdificios(): Promise<ResultadoApi<EdificioDeLista[]>> {
  return pedirApi<EdificioDeLista[]>("/api/complejos");
}

export async function edificioPorId(id: string): Promise<ResultadoApi<Edificio>> {
  return pedirApi<Edificio>(`/api/complejos/${id}`);
}

export type DatosNuevoEdificio = { nombre: string; localidad: string };

export async function crearEdificio(
  datos: DatosNuevoEdificio,
): Promise<ResultadoApi<{ id: string }>> {
  return pedirApi<{ id: string }>("/api/complejos", { metodo: "POST", cuerpo: datos });
}
