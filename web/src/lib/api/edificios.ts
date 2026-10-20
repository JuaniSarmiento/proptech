/**
 * "Mis edificios" (tarea 4.1): lista, ver uno y crear (D2, D5). El resumen
 * de cada edificio (pasos, estado de coeficientes) vive en `resumen.ts`,
 * no acá: `GET /api/complejos` nunca trajo esos campos a propósito (D5 —
 * también lo ve el vecino, D-076).
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";
import type { Edificio, EdificioDeLista } from "./tipos";

export async function listaDeEdificios(): Promise<ResultadoApi<EdificioDeLista[]>> {
  return pedirApi<EdificioDeLista[]>("/api/complejos");
}

export async function edificioPorId(id: string): Promise<ResultadoApi<Edificio>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<Edificio>(`/api/complejos/${encodeURIComponent(id)}`);
}

export type DatosNuevoEdificio = { nombre: string; localidad: string };

export async function crearEdificio(
  datos: DatosNuevoEdificio,
): Promise<ResultadoApi<{ id: string }>> {
  return pedirApi<{ id: string }>("/api/complejos", { metodo: "POST", cuerpo: datos });
}

/** Confirma "sin saldos previos" (D11, tarea 4.7): no se puede deshacer.
 * Un 409 significa que alguien más lo confirmó en el medio (la fila quedó
 * `FOR UPDATE` en el backend); la acción revalida la ruta para que la
 * pantalla muestre el estado real, nunca reintenta sola. */
export async function confirmarSinSaldosPrevios(
  id: string,
): Promise<ResultadoApi<{ id: string; estado_migracion: string }>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string; estado_migracion: string }>(
    `/api/complejos/${encodeURIComponent(id)}/estado-de-migracion/sin-saldos-previos`,
    { metodo: "POST" },
  );
}
