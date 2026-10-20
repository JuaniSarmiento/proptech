"use server";

/**
 * Alta, renombrado, activar/desactivar y reordenar categorías (D1, tarea
 * 4.5): las cuatro server actions se ligan al `complejoId` con `.bind`
 * desde `page.tsx`. Reordenar manda el orden COMPLETO que ya calculó
 * `Pantalla.tsx` (nunca la web decide el orden en el servidor: sólo lo
 * reenvía). Si la API confirma, revalida la ruta (D1).
 */

import { revalidatePath } from "next/cache";
import {
  crearCategoria,
  editarCategoria,
  reordenarCategorias,
} from "../../../../lib/api/categorias";
import type { ErrorDeCampo, ResultadoApi } from "../../../../lib/api/cliente";
import {
  erroresDeFormulario,
  MENSAJE_SIN_SESION,
  mensajeDeError,
} from "../../../../lib/api/mensajes";
import type { EstadoAccionDeLista, EstadoFormularioCategoria } from "./Pantalla";

const _CAMPOS_CONOCIDOS = ["clave", "nombre"];

const _MENSAJE_CONFLICTO: Record<string, string> = {
  clave: "Ya existe una categoría con esta clave.",
  nombre: "Ya existe una categoría con este nombre.",
};

function _mapearPanel(
  resultado: ResultadoApi<unknown>,
  complejoId: string,
): EstadoFormularioCategoria {
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/categorias`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "conflicto") {
    return {
      erroresPorCampo: {
        [resultado.campo]: _MENSAJE_CONFLICTO[resultado.campo] ?? "Este dato ya está en uso.",
      },
      erroresDesconocidos: [],
    };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], _CAMPOS_CONOCIDOS);
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés modificar las categorías de gasto."],
    };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresPorCampo: {}, erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos guardar los datos. Probá de nuevo."],
  };
}

function _mapearDeLista(
  resultado: ResultadoApi<unknown>,
  complejoId: string,
  mensajeSinPermiso: string,
): EstadoAccionDeLista {
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/categorias`);
    return { erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "sin_permiso") {
    return { erroresDesconocidos: [mensajeSinPermiso] };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  if (resultado.estado === "invalido") {
    return {
      erroresDesconocidos: resultado.errores.map((error) => mensajeDeError(error.motivo)),
    };
  }
  return { erroresDesconocidos: ["No pudimos guardar el cambio. Probá de nuevo."] };
}

export async function crearCategoriaAction(
  complejoId: string,
  _estadoPrevio: EstadoFormularioCategoria,
  formData: FormData,
): Promise<EstadoFormularioCategoria> {
  const resultado = await crearCategoria(complejoId, {
    clave: String(formData.get("clave") ?? ""),
    nombre: String(formData.get("nombre") ?? ""),
  });
  return _mapearPanel(resultado, complejoId);
}

export async function editarCategoriaAction(
  complejoId: string,
  _estadoPrevio: EstadoFormularioCategoria,
  formData: FormData,
): Promise<EstadoFormularioCategoria> {
  const categoriaId = String(formData.get("categoria_id") ?? "");
  const resultado = await editarCategoria(categoriaId, {
    nombre: String(formData.get("nombre") ?? ""),
  });
  return _mapearPanel(resultado, complejoId);
}

export async function cambiarEstadoCategoriaAction(
  complejoId: string,
  _estadoPrevio: EstadoAccionDeLista,
  formData: FormData,
): Promise<EstadoAccionDeLista> {
  const categoriaId = String(formData.get("categoria_id") ?? "");
  const activa = formData.get("activa") === "true";
  const resultado = await editarCategoria(categoriaId, { activa });
  return _mapearDeLista(resultado, complejoId, "No podés activar ni desactivar categorías.");
}

export async function reordenarCategoriasAction(
  complejoId: string,
  _estadoPrevio: EstadoAccionDeLista,
  formData: FormData,
): Promise<EstadoAccionDeLista> {
  const orden = formData.getAll("orden").map((valor) => String(valor));
  const resultado = await reordenarCategorias(complejoId, orden);
  return _mapearDeLista(resultado, complejoId, "No podés reordenar las categorías.");
}
