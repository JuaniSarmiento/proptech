"use server";

/**
 * Resolver un pago informado y ver su comprobante (change 8, H-025): las server actions hablan con la
 * API; el navegador nunca la ve ni ve el token de sesión (D-036). Se ligan al edificio con `.bind`
 * desde `page.tsx`. Mandan lo que la persona escribió, sin calcular nada.
 *
 * Un fallo se dice con un mensaje propio, traducido de su código; el texto de la API nunca llega a la
 * pantalla (L-007). Al terminar bien se revalida el edificio: la lista vuelve a leer el estado.
 */

import { revalidatePath } from "next/cache";
import { MENSAJE_SIN_SESION } from "../../../../lib/api/mensajes";
import {
  type AccionSobreUnPago,
  enlaceDelComprobante,
  resolverPago,
  tokenDelComprobante,
} from "../../../../lib/api/pagos";

const _MOTIVO_MINIMO = 3;
const _MOTIVO_MAXIMO = 500;

export type PedidoDeResolucion = {
  accion: AccionSobreUnPago;
  motivo?: string;
  desdeUnidadId?: string;
  haciaUnidadId?: string;
};

/** `hecho` dice qué quedó; `error` ya viene dicho para la pantalla. */
export type ResultadoDeResolucion = { hecho?: string; error?: string };

const _HECHO: Record<AccionSobreUnPago, string> = {
  confirmacion: "Pago confirmado.",
  rechazo: "Pago rechazado.",
  reversion: "Pago revertido.",
  reimputacion: "Pago reimputado.",
};

const _NO_PUDO: Record<AccionSobreUnPago, string> = {
  confirmacion: "No podés confirmar pagos de este edificio.",
  rechazo: "No podés rechazar pagos de este edificio.",
  reversion: "No podés revertir pagos de este edificio.",
  reimputacion: "No podés reimputar pagos de este edificio.",
};

const _FALLO: Record<AccionSobreUnPago, string> = {
  confirmacion: "No pudimos confirmar el pago. Probá de nuevo.",
  rechazo: "No pudimos rechazar el pago. Probá de nuevo.",
  reversion: "No pudimos revertir el pago. Probá de nuevo.",
  reimputacion: "No pudimos reimputar el pago. Probá de nuevo.",
};

const _CAMPOS: Record<string, string> = {
  motivo: "Escribí el motivo (entre 3 y 500 caracteres).",
  hacia_unidad_id: "Elegí otra unidad: tiene que ser distinta de la del pago.",
  desde_unidad_id: "El pago ya no tiene nada vigente en esa unidad.",
};

export async function resolverPagoAction(
  complejoId: string,
  pagoId: string,
  pedido: PedidoDeResolucion,
): Promise<ResultadoDeResolucion> {
  const { accion } = pedido;
  let cuerpo: Record<string, string> | undefined;
  if (accion !== "confirmacion") {
    const motivo = (pedido.motivo ?? "").trim();
    if (motivo.length < _MOTIVO_MINIMO || motivo.length > _MOTIVO_MAXIMO) {
      return { error: _CAMPOS.motivo };
    }
    cuerpo = { motivo };
    if (accion === "reimputacion") {
      if (!pedido.desdeUnidadId || !pedido.haciaUnidadId) {
        return { error: "Elegí la unidad de destino." };
      }
      cuerpo = {
        desde_unidad_id: pedido.desdeUnidadId,
        hacia_unidad_id: pedido.haciaUnidadId,
        motivo,
      };
    }
  }

  const resultado = await resolverPago(complejoId, pagoId, accion, cuerpo);

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    return { hecho: _HECHO[accion] };
  }
  if (resultado.estado === "sin_permiso") return { error: _NO_PUDO[accion] };
  if (resultado.estado === "sin_sesion") return { error: MENSAJE_SIN_SESION };
  if (resultado.estado === "no_existe") {
    return { error: "Este pago ya no existe o no tenés acceso." };
  }
  if (resultado.estado === "conflicto") {
    return { error: "El pago cambió de estado. Volvé a cargar la pantalla y revisalo." };
  }
  if (resultado.estado === "invalido") {
    const campo = resultado.errores[0]?.campo ?? "";
    return { error: _CAMPOS[campo] ?? "No pudimos leer el pedido. Revisá los datos." };
  }
  return { error: _FALLO[accion] };
}

/** El enlace firmado del comprobante, ya convertido a la ruta de la web que lo entrega. */
export type ResultadoDelComprobante = { ruta?: string; error?: string };

export async function verComprobanteAction(
  complejoId: string,
  pagoId: string,
): Promise<ResultadoDelComprobante> {
  const resultado = await enlaceDelComprobante(complejoId, pagoId);
  if (resultado.estado === "ok") {
    const token = tokenDelComprobante(resultado.datos.url);
    if (token === null) return { error: "No pudimos preparar el comprobante. Probá de nuevo." };
    return { ruta: `/comprobantes/descarga?token=${token}` };
  }
  if (resultado.estado === "sin_permiso") return { error: "No podés ver este comprobante." };
  if (resultado.estado === "sin_sesion") return { error: MENSAJE_SIN_SESION };
  if (resultado.estado === "no_existe") {
    return { error: "Este pago ya no existe o no tenés acceso." };
  }
  return { error: "No pudimos preparar el comprobante. Probá de nuevo." };
}
