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
import {
  type AltaDePersona,
  altaDeVecino,
  quitarAsignacion,
  revocarInvitacion,
} from "../../../../lib/api/personal";
import { crearUnidad, editarUnidad } from "../../../../lib/api/unidades";
import { decimalParaApi } from "../../../../lib/formato";
import type {
  EstadoAccionSimple,
  EstadoFormularioUnidad,
  EstadoFormularioVecino,
} from "./Pantalla";

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

const _CAMPOS_VECINO = ["nombre", "email", "vinculo"];

export async function altaVecinoAction(
  complejoId: string,
  _estadoPrevio: EstadoFormularioVecino,
  formData: FormData,
): Promise<EstadoFormularioVecino> {
  const unidadId = String(formData.get("unidad_id") ?? "");
  const resultado: ResultadoApi<AltaDePersona> = await altaDeVecino(unidadId, {
    nombre: String(formData.get("nombre") ?? ""),
    email: String(formData.get("email") ?? ""),
    vinculo: String(formData.get("vinculo") ?? ""),
  });
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/unidades`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "conflicto") {
    return {
      erroresPorCampo: { [resultado.campo]: "Ya está vinculada a esta unidad." },
      erroresDesconocidos: [],
    };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], _CAMPOS_VECINO);
  }
  if (resultado.estado === "sin_permiso") {
    return { erroresPorCampo: {}, erroresDesconocidos: ["No podés agregar vecinos."] };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresPorCampo: {}, erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos agregar el vecino. Probá de nuevo."],
  };
}

function _mapearAccionSimple(
  resultado: ResultadoApi<unknown>,
  mensaje: string,
): EstadoAccionSimple {
  if (resultado.estado === "ok") {
    return { ok: true };
  }
  if (resultado.estado === "no_existe") {
    return { error: "Ya no está disponible. La lista se actualizó." };
  }
  if (resultado.estado === "sin_permiso") {
    return { error: mensaje };
  }
  if (resultado.estado === "sin_sesion") {
    return { error: MENSAJE_SIN_SESION };
  }
  return { error: "No pudimos completar la acción. Probá de nuevo." };
}

export async function revocarVecinoAction(
  complejoId: string,
  _estadoPrevio: EstadoAccionSimple,
  formData: FormData,
): Promise<EstadoAccionSimple> {
  const resultado = await revocarInvitacion(String(formData.get("invitacion_id") ?? ""));
  revalidatePath(`/edificios/${complejoId}/unidades`);
  return _mapearAccionSimple(resultado, "No podés revocar invitaciones.");
}

export async function quitarVecinoAction(
  complejoId: string,
  _estadoPrevio: EstadoAccionSimple,
  formData: FormData,
): Promise<EstadoAccionSimple> {
  const resultado = await quitarAsignacion(String(formData.get("asignacion_id") ?? ""));
  revalidatePath(`/edificios/${complejoId}/unidades`);
  return _mapearAccionSimple(resultado, "No podés quitar un vecino.");
}
