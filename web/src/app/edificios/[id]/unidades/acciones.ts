"use server";

/**
 * Alta y edición de una unidad (D1, D9-style dos acciones, tarea 4.3): la
 * server action se liga al `complejoId` con `.bind` desde `page.tsx`; la
 * edición manda el `id` de la unidad en un campo oculto del mismo
 * formulario (una sola acción compartida por todas las filas, en vez de
 * una función ligada por fila). Si la API confirma, revalida la ruta
 * (D1: la fila y la suma salen de la API, nunca de lo que mandó el form).
 */

import { revalidatePath } from "next/cache";
import type { ErrorDeCampo, ResultadoApi } from "../../../../lib/api/cliente";
import { erroresDeFormulario, MENSAJE_SIN_SESION } from "../../../../lib/api/mensajes";
import { crearUnidad, editarUnidad } from "../../../../lib/api/unidades";
import { decimalParaApi } from "../../../../lib/formato";
import type { EstadoFormularioUnidad } from "./Pantalla";

const _CAMPOS_CONOCIDOS = ["identificador", "tipo", "piso", "coeficiente", "superficie_m2"];

function _datosDelFormulario(formData: FormData) {
  return {
    identificador: String(formData.get("identificador") ?? ""),
    tipo: String(formData.get("tipo") ?? ""),
    piso: String(formData.get("piso") ?? ""),
    coeficiente: decimalParaApi(String(formData.get("coeficiente") ?? "")),
    superficie_m2: decimalParaApi(String(formData.get("superficie_m2") ?? "")),
  };
}

function _mapear(resultado: ResultadoApi<unknown>, complejoId: string): EstadoFormularioUnidad {
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/unidades`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "conflicto") {
    return {
      erroresPorCampo: { [resultado.campo]: "Ya existe una unidad con este identificador." },
      erroresDesconocidos: [],
    };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], _CAMPOS_CONOCIDOS);
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés modificar el padrón de unidades."],
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

export async function crearUnidadAction(
  complejoId: string,
  _estadoPrevio: EstadoFormularioUnidad,
  formData: FormData,
): Promise<EstadoFormularioUnidad> {
  const resultado = await crearUnidad(complejoId, _datosDelFormulario(formData));
  return _mapear(resultado, complejoId);
}

export async function editarUnidadAction(
  complejoId: string,
  _estadoPrevio: EstadoFormularioUnidad,
  formData: FormData,
): Promise<EstadoFormularioUnidad> {
  const unidadId = String(formData.get("unidad_id") ?? "");
  const resultado = await editarUnidad(unidadId, _datosDelFormulario(formData));
  return _mapear(resultado, complejoId);
}
