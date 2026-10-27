/**
 * Grupos de reparto (D2, D9, tarea 4.4). Sin `camposDePlata` en la lectura:
 * la respuesta es un arreglo y `camposDePlata` sólo recorre un camino
 * punteado desde la raíz de un objeto (D2, 3.3) — sobre un arreglo daría
 * `fallo` por error, no por un dato roto.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";
import type { Grupo } from "./tipos";

export async function gruposDelEdificio(id: string): Promise<ResultadoApi<Grupo[]>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<Grupo[]>(`/api/complejos/${encodeURIComponent(id)}/grupos`);
}

export type MiembroAEnviar = { unidad_id: string; coeficiente: string | null };

export type DatosNuevoGrupo = {
  /** D7 (tarea 4.4, 6.3): opcional — sin campo "clave" en el formulario, se
   * deriva del nombre en el backend. La API sigue aceptando una clave
   * explícita (semilla, importador), nunca enviada desde esta pantalla. */
  clave?: string;
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
  if (!esIdValido(complejoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(`/api/complejos/${encodeURIComponent(complejoId)}/grupos`, {
    metodo: "POST",
    cuerpo: datos,
  });
}

export type CambiosGrupo = { nombre?: string; metodo?: string; activo?: boolean };

/** Edición, primer pedido (D9): sólo nombre/método. `grupoId` viene de un
 * campo oculto (`grupos/acciones.ts`, R3C-2). */
export async function editarGrupo(
  grupoId: string,
  cambios: CambiosGrupo,
): Promise<ResultadoApi<{ id: string }>> {
  if (!esIdValido(grupoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(`/api/grupos/${encodeURIComponent(grupoId)}`, {
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
  if (!esIdValido(grupoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(`/api/grupos/${encodeURIComponent(grupoId)}/unidades`, {
    metodo: "PUT",
    cuerpo: datos,
  });
}
