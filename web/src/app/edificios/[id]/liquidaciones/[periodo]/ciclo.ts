"use server";

/**
 * Distribuir y anular una liquidación emitida (change 7, H-014): las server actions reciben el
 * formulario de su confirmación y se lo pasan a la API; el navegador nunca habla con ella ni ve el
 * token (D-036). Se ligan al edificio y a la liquidación con `.bind` desde `page.tsx`.
 *
 * Un 409 se dice con un mensaje propio, traducido de su código; el texto de la API nunca llega a la
 * pantalla (L-007). Al terminar bien se revalida la ruta: la pantalla vuelve a leer el estado.
 */

import { revalidatePath } from "next/cache";
import { anularLiquidacion, distribuirLiquidacion } from "../../../../../lib/api/liquidaciones";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import type { EstadoCiclo } from "./Pantalla";

const _MOTIVO_MAXIMO = 500;

const _CONFLICTOS: Record<string, string> = {
  ya_distribuida:
    "Esta liquidación ya está distribuida: desde ahí no se anula. Volvé a cargar la pantalla.",
  anulada: "Esta liquidación ya está anulada. Volvé a cargar la pantalla.",
  periodo_siguiente_emitido:
    "El período siguiente ya está emitido. Para anular este, primero anulá el siguiente.",
};

function fallo(error: string): EstadoCiclo {
  return { error };
}

function mensajeDeConflicto(motivo: string | undefined, porDefecto: string): string {
  return (motivo !== undefined ? _CONFLICTOS[motivo] : undefined) ?? porDefecto;
}

export async function distribuirLiquidacionAction(
  complejoId: string,
  liquidacionId: string,
  _estadoPrevio: EstadoCiclo,
  _formData: FormData,
): Promise<EstadoCiclo> {
  const resultado = await distribuirLiquidacion(complejoId, liquidacionId);
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    return { hecho: "distribuida" };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés distribuir la liquidación de este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(mensajeDeConflicto(resultado.motivo, "No pudimos distribuir la liquidación."));
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Esta liquidación ya no existe o no tenés acceso.");
  }
  return fallo("No pudimos distribuir la liquidación. Probá de nuevo.");
}

export async function anularLiquidacionAction(
  complejoId: string,
  liquidacionId: string,
  _estadoPrevio: EstadoCiclo,
  formData: FormData,
): Promise<EstadoCiclo> {
  const motivo = String(formData.get("motivo") ?? "").trim();
  if (motivo === "" || motivo.length > _MOTIVO_MAXIMO) {
    return fallo(`Escribí el motivo de la anulación (hasta ${_MOTIVO_MAXIMO} caracteres).`);
  }
  const resultado = await anularLiquidacion(complejoId, liquidacionId, motivo);
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    return { hecho: "anulada" };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés anular la liquidación de este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(mensajeDeConflicto(resultado.motivo, "No pudimos anular la liquidación."));
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Esta liquidación ya no existe o no tenés acceso.");
  }
  if (resultado.estado === "invalido") {
    return fallo("No pudimos leer el pedido. Revisá el motivo y probá de nuevo.");
  }
  return fallo("No pudimos anular la liquidación. Probá de nuevo.");
}
