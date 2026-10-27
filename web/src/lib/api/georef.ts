/**
 * Georef del país (D3, tarea 6.1): provincia → departamento → localidad,
 * leídos de `GET /api/georef/*` (tarea 2.5). Sin `camposDePlata`: nada acá
 * es plata.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type OpcionGeoref = { id: string; nombre: string };

export async function provincias(): Promise<ResultadoApi<OpcionGeoref[]>> {
  return pedirApi<OpcionGeoref[]>("/api/georef/provincias");
}

export async function departamentosDe(provinciaId: string): Promise<ResultadoApi<OpcionGeoref[]>> {
  if (!esIdValido(provinciaId) && !/^[0-9]+$/.test(provinciaId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<OpcionGeoref[]>(
    `/api/georef/provincias/${encodeURIComponent(provinciaId)}/departamentos`,
  );
}

export async function localidadesDe(departamentoId: string): Promise<ResultadoApi<OpcionGeoref[]>> {
  if (!esIdValido(departamentoId) && !/^[0-9]+$/.test(departamentoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<OpcionGeoref[]>(
    `/api/georef/departamentos/${encodeURIComponent(departamentoId)}/localidades`,
  );
}
