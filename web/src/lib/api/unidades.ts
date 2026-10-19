/**
 * Padrón de unidades (D2, tarea 4.3): leer, crear y editar. `informe` es
 * plata (D2): si no es texto decimal, el resultado es `fallo`.
 */

import { pedirApi, type ResultadoApi } from "./cliente";
import type { Padron, Unidad } from "./tipos";

export async function padronDelEdificio(id: string): Promise<ResultadoApi<Padron>> {
  return pedirApi<Padron>(`/api/complejos/${id}/unidades`, {
    camposDePlata: ["informe.suma", "informe.diferencia"],
  });
}

export type DatosUnidad = {
  identificador: string;
  tipo: string;
  piso: string;
  coeficiente: string;
  superficie_m2: string;
};

export async function crearUnidad(
  complejoId: string,
  datos: DatosUnidad,
): Promise<ResultadoApi<Unidad>> {
  return pedirApi<Unidad>(`/api/complejos/${complejoId}/unidades`, {
    metodo: "POST",
    cuerpo: datos,
  });
}

export type CambiosUnidad = Partial<DatosUnidad>;

export async function editarUnidad(
  unidadId: string,
  cambios: CambiosUnidad,
): Promise<ResultadoApi<Unidad>> {
  return pedirApi<Unidad>(`/api/unidades/${unidadId}`, {
    metodo: "PATCH",
    cuerpo: cambios,
  });
}
