/**
 * Padrón de unidades (D2, tarea 4.3): leer, crear y editar. `informe` es
 * plata (D2): si no es texto decimal, el resultado es `fallo`.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";
import type { Padron, Unidad } from "./tipos";

export async function padronDelEdificio(id: string): Promise<ResultadoApi<Padron>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<Padron>(`/api/complejos/${encodeURIComponent(id)}/unidades`, {
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
  if (!esIdValido(complejoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<Unidad>(`/api/complejos/${encodeURIComponent(complejoId)}/unidades`, {
    metodo: "POST",
    cuerpo: datos,
  });
}

export type CambiosUnidad = Partial<DatosUnidad>;

/** R3C-2 (rompedor 3b): `unidadId` viene de un campo OCULTO del formulario
 * (`unidades/acciones.ts`, `editarUnidadAction`), nunca de algo que la web
 * calculó — así que llega crudo hasta acá y tiene que validarse antes de
 * armar la ruta. */
export async function editarUnidad(
  unidadId: string,
  cambios: CambiosUnidad,
): Promise<ResultadoApi<Unidad>> {
  if (!esIdValido(unidadId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<Unidad>(`/api/unidades/${encodeURIComponent(unidadId)}`, {
    metodo: "PATCH",
    cuerpo: cambios,
  });
}
