"use server";

/**
 * Los documentos de una liquidación emitida (change 7, H-015): reprocesar los que no se generaron y
 * pedir el enlace firmado de uno generado. Las server actions hablan con la API; el navegador nunca
 * la ve ni ve el token de sesión (D-036). Se ligan al edificio (y a la liquidación) con `.bind` desde
 * `page.tsx`.
 *
 * Un fallo se dice con un mensaje propio; el texto de la API nunca llega a la pantalla (L-007).
 */

import { revalidatePath } from "next/cache";
import {
  enlaceDelDocumento,
  reprocesarDocumentos,
  tokenDelEnlace,
  type VarianteDeDocumento,
} from "../../../../../lib/api/documentos";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import type { EstadoDeDescarga, EstadoDeReproceso } from "./Documentos";

export async function reprocesarDocumentosAction(
  complejoId: string,
  liquidacionId: string,
  _estadoPrevio: EstadoDeReproceso,
  _formData: FormData,
): Promise<EstadoDeReproceso> {
  const resultado = await reprocesarDocumentos(complejoId, liquidacionId);
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    return { encolados: resultado.datos.encolados };
  }
  if (resultado.estado === "sin_permiso") {
    return { error: "No podés reprocesar los documentos de este edificio." };
  }
  if (resultado.estado === "sin_sesion") {
    return { error: MENSAJE_SIN_SESION };
  }
  if (resultado.estado === "no_existe") {
    return { error: "Esta liquidación ya no existe o no tenés acceso." };
  }
  return { error: "No pudimos reprocesar los documentos. Probá de nuevo en un rato." };
}

export async function descargarDocumentoAction(
  complejoId: string,
  _estadoPrevio: EstadoDeDescarga,
  formData: FormData,
): Promise<EstadoDeDescarga> {
  const documentoId = String(formData.get("documento_id") ?? "");
  const variante = String(formData.get("variante") ?? "") as VarianteDeDocumento;
  const resultado = await enlaceDelDocumento(complejoId, documentoId, variante);
  if (resultado.estado === "ok") {
    const token = tokenDelEnlace(resultado.datos.url);
    if (token === null) {
      return { error: "No pudimos preparar la descarga. Probá de nuevo." };
    }
    // Un número nuevo en cada pedido: dos descargas seguidas del mismo documento son dos acciones.
    return { ruta: `/documentos/descarga?token=${token}`, pedido: Date.now() };
  }
  if (resultado.estado === "sin_permiso") {
    return { error: "No podés descargar este documento." };
  }
  if (resultado.estado === "conflicto") {
    return { error: "Este documento todavía no está generado. Probá de nuevo en un rato." };
  }
  if (resultado.estado === "sin_sesion") {
    return { error: MENSAJE_SIN_SESION };
  }
  if (resultado.estado === "no_existe") {
    return { error: "Este documento ya no existe o no tenés acceso." };
  }
  return { error: "No pudimos preparar la descarga. Probá de nuevo." };
}
