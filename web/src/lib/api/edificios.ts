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

/** D3 (tarea 6.1): `localidad` ya no es una entrada (2.6) — el trío de
 * ubicación es obligatorio en toda alta, `calle_y_numero` es opcional, y
 * `pisos`/`subsuelos` también son obligatorios (3.2). */
export type DatosNuevoEdificio = {
  nombre: string;
  provincia_id: string;
  departamento_id: string;
  localidad_id: string;
  calle_y_numero?: string | null;
  pisos: number;
  subsuelos: number;
};

export async function crearEdificio(
  datos: DatosNuevoEdificio,
): Promise<ResultadoApi<{ id: string }>> {
  return pedirApi<{ id: string }>("/api/complejos", { metodo: "POST", cuerpo: datos });
}

/** D3 (tarea 6.1, 3.6): edición parcial — sólo los campos presentes. */
export type DatosEdicionEdificio = Partial<{
  nombre: string;
  provincia_id: string;
  departamento_id: string;
  localidad_id: string;
  calle_y_numero: string;
  pisos: number;
  subsuelos: number;
}>;

export async function editarEdificio(
  id: string,
  datos: DatosEdicionEdificio,
): Promise<ResultadoApi<{ id: string }>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(`/api/complejos/${encodeURIComponent(id)}`, {
    metodo: "PATCH",
    cuerpo: datos,
  });
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
