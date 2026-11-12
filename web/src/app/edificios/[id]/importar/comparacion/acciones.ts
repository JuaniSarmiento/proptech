"use server";

/**
 * Aceptar las diferencias del borrador (change 5, H-008): la server action recibe el formulario
 * de la confirmación (sólo `importacion_id`) y se lo pasa a la API; el navegador nunca habla con
 * la API ni ve el token (D-036). La acción se liga al `complejoId` con `.bind` desde `page.tsx`.
 */

import { revalidatePath } from "next/cache";
import { aceptarDiferencias, confirmarSaldos } from "../../../../../lib/api/importaciones";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import type { EstadoAceptacion, EstadoConfirmacion } from "./Pantalla";

const _CONFLICTOS: Record<string, string> = {
  aceptacion: "Estas diferencias ya fueron aceptadas. Volvé a cargar la pantalla.",
  diferencias: "No hay diferencias para aceptar.",
  importacion_id:
    "Este borrador ya no es el vigente: se subió un archivo nuevo. Volvé a cargar la pantalla.",
  estado_migracion:
    "Los saldos de este edificio ya están resueltos: no se pueden aceptar diferencias.",
};

function fallo(error: string): { error: string } {
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

const _CONFLICTOS_DE_CONFIRMAR: Record<string, string> = {
  diferencias: "Hay diferencias sin aceptar. Aceptalas antes de confirmar.",
  importacion_id:
    "Este borrador ya no es el vigente: se subió un archivo nuevo. Volvé a cargar la pantalla.",
  saldos: "El archivo no trae saldos: no hay nada que confirmar.",
  estado_migracion:
    "Los saldos de este edificio ya están resueltos: no se pueden confirmar de nuevo.",
};

/**
 * Confirmar los saldos del borrador (change 5, H-009): igual que aceptar, recibe el formulario de
 * la confirmación (sólo `importacion_id`) y se lo pasa a la API. Al confirmar, la comparación deja de
 * existir (el borrador pasa a `confirmada`), así que sólo se revalida el resumen del edificio: la
 * pantalla se queda mostrando lo que devolvió la confirmación.
 */
export async function confirmarSaldosAction(
  complejoId: string,
  _estadoPrevio: EstadoConfirmacion,
  formData: FormData,
): Promise<EstadoConfirmacion> {
  const importacionId = formData.get("importacion_id");
  if (typeof importacionId !== "string" || importacionId === "") {
    return fallo("No pudimos leer el pedido. Probá de nuevo.");
  }

  const resultado = await confirmarSaldos(complejoId, importacionId);

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    return { confirmada: resultado.datos };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés confirmar saldos en este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(
      _CONFLICTOS_DE_CONFIRMAR[resultado.campo] ??
        "No pudimos confirmar los saldos. Probá de nuevo.",
    );
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Este edificio ya no existe o no tenés acceso.");
  }
  if (resultado.estado === "invalido") {
    return fallo(
      resultado.errores.some((error) => error.campo === "fecha_de_migracion")
        ? "La fecha de migración no es válida. Subí el archivo de nuevo con otra fecha."
        : "El libro no acepta algún dato del archivo. Subí el archivo de nuevo.",
    );
  }
  return fallo("No pudimos confirmar los saldos. Probá de nuevo.");
}
