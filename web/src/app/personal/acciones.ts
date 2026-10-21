"use server";

/**
 * Invitar, revocar y quitar en Personal (D5, tarea 7.3): tres acciones
 * separadas (como D1 en otras pantallas), cada una revalida `/personal` al
 * confirmar la API, nunca antes.
 */

import { revalidatePath } from "next/cache";
import type { ErrorDeCampo, ResultadoApi } from "../../lib/api/cliente";
import { erroresDeFormulario, MENSAJE_SIN_SESION } from "../../lib/api/mensajes";
import {
  type AltaDePersona,
  invitarPersonal,
  quitarAsignacion,
  revocarInvitacion,
} from "../../lib/api/personal";
import type { EstadoAccionSimple, EstadoFormularioPersonal } from "./Pantalla";

const _CAMPOS_CONOCIDOS = ["nombre", "email", "rol", "alcance", "complejo_id"];

function _mapearInvitar(resultado: ResultadoApi<AltaDePersona>): EstadoFormularioPersonal {
  if (resultado.estado === "ok") {
    revalidatePath("/personal");
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "conflicto") {
    const mensaje =
      resultado.campo === "vinculo"
        ? "Ya está vinculada a esta unidad."
        : "Esta persona ya tiene asignado ese perfil.";
    return { erroresPorCampo: { [resultado.campo]: mensaje }, erroresDesconocidos: [] };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], _CAMPOS_CONOCIDOS);
  }
  if (resultado.estado === "sin_permiso") {
    return { erroresPorCampo: {}, erroresDesconocidos: ["No podés invitar personal."] };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresPorCampo: {}, erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos enviar la invitación. Probá de nuevo."],
  };
}

export async function invitarAction(
  _estadoPrevio: EstadoFormularioPersonal,
  formData: FormData,
): Promise<EstadoFormularioPersonal> {
  const alcance = String(formData.get("alcance") ?? "");
  const complejoId = String(formData.get("complejo_id") ?? "");
  const resultado = await invitarPersonal({
    nombre: String(formData.get("nombre") ?? ""),
    email: String(formData.get("email") ?? ""),
    rol: String(formData.get("rol") ?? ""),
    alcance,
    ...(alcance === "edificio" && complejoId ? { complejo_id: complejoId } : {}),
  });
  return _mapearInvitar(resultado);
}

function _mapearAccionSimple(
  resultado: ResultadoApi<unknown>,
  mensaje: string,
): EstadoAccionSimple {
  if (resultado.estado === "ok") {
    revalidatePath("/personal");
    return { ok: true };
  }
  if (resultado.estado === "no_existe") {
    revalidatePath("/personal");
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

export async function revocarAction(
  _estadoPrevio: EstadoAccionSimple,
  formData: FormData,
): Promise<EstadoAccionSimple> {
  const invitacionId = String(formData.get("invitacion_id") ?? "");
  const resultado = await revocarInvitacion(invitacionId);
  return _mapearAccionSimple(resultado, "No podés revocar invitaciones.");
}

export async function quitarAction(
  _estadoPrevio: EstadoAccionSimple,
  formData: FormData,
): Promise<EstadoAccionSimple> {
  const asignacionId = String(formData.get("asignacion_id") ?? "");
  const resultado = await quitarAsignacion(asignacionId);
  return _mapearAccionSimple(resultado, "No podés quitar personal.");
}
