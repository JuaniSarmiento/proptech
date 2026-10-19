/**
 * "Los datos del edificio y la configuración vigente en una línea"
 * (shape, tarea 4.2): formato argentino sobre texto decimal (D6), nunca
 * `Number`/`parseFloat`.
 */

import type { ConfiguracionVigente } from "../../../lib/api/tipos";
import { tasa } from "../../../lib/formato";

export function textoDeVigente(vigente: ConfiguracionVigente): string {
  if (vigente === null) {
    return "Todavía no configuraste la tasa ni el vencimiento.";
  }
  const base = `Tasa ${tasa(vigente.tasa_mensual)} % · Fondo de reserva ${tasa(vigente.porcentaje_fondo)} % · Vencimiento día ${vigente.dia_de_vencimiento}`;
  if (
    vigente.modalidad_de_vencimiento === "doble" &&
    vigente.dia_segundo_vencimiento !== null &&
    vigente.recargo_segundo_vencimiento !== null
  ) {
    return `${base}, segundo vencimiento día ${vigente.dia_segundo_vencimiento} (recargo ${tasa(vigente.recargo_segundo_vencimiento)} %)`;
  }
  return base;
}
