"use server";

/**
 * Aceptar las diferencias del borrador (change 5, H-008): la server action recibe el formulario
 * de la confirmación (sólo `importacion_id`) y se lo pasa a la API; el navegador nunca habla con
 * la API ni ve el token (D-036). La acción se liga al `complejoId` con `.bind` desde `page.tsx`.
 */

import { revalidatePath } from "next/cache";
import { aceptarDiferencias } from "../../../../../lib/api/importaciones";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import type { EstadoAceptacion } from "./Pantalla";

const _CONFLICTOS: Record<string, string> = {
  aceptacion: "Estas diferencias ya fueron aceptadas. Volvé a cargar la pantalla.",
  diferencias: "No hay diferencias para aceptar.",
  importacion_id:
    "Este borrador ya no es el vigente: se subió un archivo nuevo. Volvé a cargar la pantalla.",
  estado_migracion:
    "Los saldos de este edificio ya están resueltos: no se pueden aceptar diferencias.",
};

function fallo(error: string): EstadoAceptacion {
  return { error };
}

export async function aceptarDiferenciasAction(
  complejoId: string,
  _estadoPrevio: EstadoAceptacion,
  formData: FormData,
): Promise<EstadoAceptacion> {
  const importacionId = formData.get("importacion_id");
  if (typeof importacionId !== "string" || importacionId === "") {
    return fallo("No pudimos leer el pedido. Probá de nuevo.");
  }

  const resultado = await aceptarDiferencias(complejoId, importacionId);

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/importar/comparacion`);
    return { aceptada: resultado.datos };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés aceptar diferencias en este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(
      _CONFLICTOS[resultado.campo] ?? "No pudimos aceptar las diferencias. Probá de nuevo.",
    );
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Este edificio ya no existe o no tenés acceso.");
  }
  if (resultado.estado === "invalido") {
    return fallo("No pudimos leer el pedido. Probá de nuevo.");
  }
  return fallo("No pudimos aceptar las diferencias. Probá de nuevo.");
}
