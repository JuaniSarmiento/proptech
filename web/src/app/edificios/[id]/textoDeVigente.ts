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

const _FORMAS_DE_CALCULO: Record<string, string> = {
  proporcional_por_dia: "Proporcional por día",
  mes_entero: "Mes entero",
};

/** La configuración vigente como renglones etiqueta/valor (pulido 3b, "El
 * recibo prolijo"): misma información que `textoDeVigente`, pero para leer
 * en columna en Intereses y vencimiento, no en una línea corrida. */
export function renglonesDeVigente(
  vigente: NonNullable<ConfiguracionVigente>,
): Array<{ etiqueta: string; valor: string }> {
  const doble =
    vigente.modalidad_de_vencimiento === "doble" &&
    vigente.dia_segundo_vencimiento !== null &&
    vigente.recargo_segundo_vencimiento !== null;
  return [
    { etiqueta: "Tasa de interés mensual", valor: `${tasa(vigente.tasa_mensual)} %` },
    { etiqueta: "Fondo de reserva", valor: `${tasa(vigente.porcentaje_fondo)} %` },
    { etiqueta: "Días de gracia", valor: String(vigente.dias_de_gracia) },
    {
      etiqueta: "Forma de cálculo",
      valor: _FORMAS_DE_CALCULO[vigente.forma_de_calculo] ?? vigente.forma_de_calculo,
    },
    {
      etiqueta: "Vencimiento",
      valor: doble
        ? `Día ${vigente.dia_de_vencimiento} y día ${vigente.dia_segundo_vencimiento} (recargo ${tasa(vigente.recargo_segundo_vencimiento as string)} %)`
        : `Día ${vigente.dia_de_vencimiento}`,
    },
  ];
}
