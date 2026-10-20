"use server";

/**
 * Confirmar "sin saldos previos" (D1, tarea 4.7): la server action se liga
 * al `complejoId` con `.bind` desde `page.tsx`. Un 409 ("otro lo confirmó
 * en el medio") revalida igual que un `ok`: la pantalla vuelve a pedir el
 * resumen y, con el estado ya cambiado, muestra el estado en vez del
 * formulario (D11) — el mensaje acá es sólo para el instante antes de esa
 * revalidación.
 */

import { revalidatePath } from "next/cache";
import { confirmarSinSaldosPrevios } from "../../../../lib/api/edificios";
import { MENSAJE_SIN_SESION } from "../../../../lib/api/mensajes";
import type { EstadoConfirmacion } from "./Pantalla";

export async function confirmarSinSaldosPreviosAction(
  complejoId: string,
  _estadoPrevio: EstadoConfirmacion,
  _formData: FormData,
): Promise<EstadoConfirmacion> {
  const resultado = await confirmarSinSaldosPrevios(complejoId);

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/saldos-previos`);
    revalidatePath(`/edificios/${complejoId}`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "conflicto") {
    revalidatePath(`/edificios/${complejoId}/saldos-previos`);
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["Otra persona ya confirmó esto. Recargá la pantalla."],
    };
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés confirmar que el edificio arranca sin saldos previos."],
    };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresPorCampo: {}, erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos confirmar. Probá de nuevo."],
  };
}
