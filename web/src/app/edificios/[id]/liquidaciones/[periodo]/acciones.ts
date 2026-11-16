"use server";

/**
 * Emitir la liquidación revisada (change 7, H-013): la server action recibe el formulario de la
 * confirmación (el `emision_id` que eligió la pantalla, la huella que se revisó, los bloqueantes
 * aceptados y, si se corre, el vencimiento con su motivo), valida lo que se puede validar sin la
 * API y se lo pasa a ella; el navegador nunca habla con la API ni ve el token (D-036). Se liga al
 * `complejoId` y al período (`AAAA-MM-01`) con `.bind` desde `page.tsx`.
 *
 * Un 409 se dice con un mensaje propio, traducido de su código; el texto de la API nunca llega a la
 * pantalla (L-007). No se revalida la preliquidación: ya emitida, la API la rechazaría con un 409 y
 * taparía la región "Liquidación emitida".
 */

import { revalidatePath } from "next/cache";
import { emitirLiquidacion, type PedidoDeEmision } from "../../../../../lib/api/liquidaciones";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import type { EstadoEmision } from "./Pantalla";

const _MOTIVO_MAXIMO = 500;

const _FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

const _CONFLICTOS: Record<string, string> = {
  huella:
    "La preliquidación cambió desde que la revisaste. Volvé a cargar la pantalla y revisala de nuevo.",
  alertas_aceptadas:
    "Los controles cambiaron desde que los revisaste. Volvé a cargar la pantalla y revisalos de nuevo.",
  periodo: "Este período ya no se puede emitir. Volvé a cargar la pantalla.",
  emision_id: "Este pedido ya se registró con otros datos. Volvé a cargar la pantalla.",
};

function fallo(error: string): EstadoEmision {
  return { error };
}

export async function emitirLiquidacionAction(
  complejoId: string,
  periodo: string,
  _estadoPrevio: EstadoEmision,
  formData: FormData,
): Promise<EstadoEmision> {
  const emisionId = String(formData.get("emision_id") ?? "");
  const huella = String(formData.get("huella") ?? "");
  if (emisionId === "" || huella === "") {
    return fallo("No pudimos leer el pedido. Probá de nuevo.");
  }
  const alertas = formData.getAll("alerta").map(String);
  const pedido: PedidoDeEmision = {
    emision_id: emisionId,
    huella,
    alertas_aceptadas: alertas,
  };
  if (formData.get("correr_vencimiento") !== null) {
    const fecha = String(formData.get("vencimiento_fecha") ?? "").trim();
    const motivo = String(formData.get("motivo_del_vencimiento") ?? "").trim();
    if (!_FECHA.test(fecha)) {
      return fallo("Elegí la fecha del nuevo vencimiento.");
    }
    if (motivo === "" || motivo.length > _MOTIVO_MAXIMO) {
      return fallo(`Escribí el motivo del nuevo vencimiento (hasta ${_MOTIVO_MAXIMO} caracteres).`);
    }
    pedido.vencimiento = { fecha, motivo };
  }

  const resultado = await emitirLiquidacion(complejoId, periodo, pedido);

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    return { emitida: resultado.datos };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés emitir la liquidación de este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(
      _CONFLICTOS[resultado.campo] ?? "No pudimos emitir la liquidación. Probá de nuevo.",
    );
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Este edificio ya no existe o no tenés acceso.");
  }
  if (resultado.estado === "invalido") {
    return fallo("No pudimos leer el pedido. Revisá los datos y probá de nuevo.");
  }
  return fallo("No pudimos emitir la liquidación. Probá de nuevo.");
}
