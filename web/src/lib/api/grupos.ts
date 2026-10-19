/**
 * Grupos de reparto (D2, D9, tarea 4.4). Sin `camposDePlata` en la lectura:
 * la respuesta es un arreglo y `camposDePlata` sólo recorre un camino
 * punteado desde la raíz de un objeto (D2, 3.3) — sobre un arreglo daría
 * `fallo` por error, no por un dato roto.
 */

import { pedirApi, type ResultadoApi } from "./cliente";
import type { Grupo } from "./tipos";

export async function gruposDelEdificio(id: string): Promise<ResultadoApi<Grupo[]>> {
  return pedirApi<Grupo[]>(`/api/complejos/${id}/grupos`);
}

export type MiembroAEnviar = { unidad_id: string; coeficiente: string | null };

export type DatosNuevoGrupo = {
  clave: string;
  nombre: string;
  metodo: string;
  modo_de_coeficientes: "renormalizado" | "propios";
  unidades: MiembroAEnviar[];
};

/** Alta: un solo pedido con nombre, método, modo y unidades juntos (D9: la
 * API lo acepta en el mismo `POST`, a diferencia de la edición). */
export async function crearGrupo(
  complejoId: string,
  datos: DatosNuevoGrupo,
): Promise<ResultadoApi<{ id: string }>> {
  return pedirApi<{ id: string }>(`/api/complejos/${complejoId}/grupos`, {
    metodo: "POST",
    cuerpo: datos,
  });
}

export type CambiosGrupo = { nombre?: string; metodo?: string };

/** Edición, primer pedido (D9): sólo nombre/método. */
export async function editarGrupo(
  grupoId: string,
  cambios: CambiosGrupo,
): Promise<ResultadoApi<{ id: string }>> {
  return pedirApi<{ id: string }>(`/api/grupos/${grupoId}`, {
    metodo: "PATCH",
    cuerpo: cambios,
  });
}

export type DatosDeMiembros = {
  modo_de_coeficientes: "renormalizado" | "propios";
  unidades: MiembroAEnviar[];
};

/** Edición, segundo pedido (D9): reemplaza los miembros del grupo. Si este
 * falla tras haber guardado el primero, el edificio queda con el nombre y
 * el método nuevos pero las unidades viejas — la server action avisa eso,
 * nunca lo oculta. */
export async function fijarMiembrosDeGrupo(
  grupoId: string,
  datos: DatosDeMiembros,
): Promise<ResultadoApi<{ id: string }>> {
  return pedirApi<{ id: string }>(`/api/grupos/${grupoId}/unidades`, {
    metodo: "PUT",
    cuerpo: datos,
  });
}
