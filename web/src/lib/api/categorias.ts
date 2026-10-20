/**
 * Categorías de gasto (D2, tarea 4.5): leer, crear, editar (renombrar y
 * activar/desactivar) y reordenar. Sin `camposDePlata`: la respuesta es un
 * arreglo, igual que `grupos.ts` (D2, 3.3).
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";
import type { Categoria } from "./tipos";

export async function categoriasDelEdificio(id: string): Promise<ResultadoApi<Categoria[]>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<Categoria[]>(`/api/complejos/${encodeURIComponent(id)}/categorias`);
}

export type DatosNuevaCategoria = { clave: string; nombre: string };

export async function crearCategoria(
  complejoId: string,
  datos: DatosNuevaCategoria,
): Promise<ResultadoApi<{ id: string }>> {
  if (!esIdValido(complejoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(`/api/complejos/${encodeURIComponent(complejoId)}/categorias`, {
    metodo: "POST",
    cuerpo: datos,
  });
}

export type CambiosCategoria = { nombre?: string; activa?: boolean };

/** R3C-2: `categoriaId` viene de un campo oculto (`categorias/acciones.ts`). */
export async function editarCategoria(
  categoriaId: string,
  cambios: CambiosCategoria,
): Promise<ResultadoApi<{ id: string }>> {
  if (!esIdValido(categoriaId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(`/api/categorias/${encodeURIComponent(categoriaId)}`, {
    metodo: "PATCH",
    cuerpo: cambios,
  });
}

/** Manda el orden COMPLETO (todas las categorías del edificio, D-ficha
 * 4.5): "subir"/"bajar" calculan la lista entera con el movimiento ya
 * aplicado, nunca sólo la categoría que se mueve. */
export async function reordenarCategorias(
  complejoId: string,
  orden: string[],
): Promise<ResultadoApi<{ id: string }>> {
  if (!esIdValido(complejoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(
    `/api/complejos/${encodeURIComponent(complejoId)}/categorias/orden`,
    { metodo: "PUT", cuerpo: { orden } },
  );
}
