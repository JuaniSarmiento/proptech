/**
 * Historial de intereses y vencimiento (tarea 4.6): qué campos cambiaron
 * respecto de la versión anterior, comparando TEXTO (`!==` sobre el valor
 * tal cual lo da la API), nunca número (D6: ni `Number`, ni `parseFloat`,
 * ni aritmética sobre un valor de plata).
 */

import type { VersionDelHistorial } from "../../../../lib/api/tipos";

const _ETIQUETAS: Record<string, string> = {
  tasa_mensual: "tasa",
  dias_de_gracia: "días de gracia",
  forma_de_calculo: "forma de cálculo",
  porcentaje_fondo: "fondo de reserva",
  dia_de_vencimiento: "día de vencimiento",
  modalidad_de_vencimiento: "modalidad de vencimiento",
  dia_segundo_vencimiento: "segundo vencimiento",
  recargo_segundo_vencimiento: "recargo del segundo vencimiento",
};

const _CAMPOS = Object.keys(_ETIQUETAS) as Array<keyof typeof _ETIQUETAS>;

/** Campos que cambiaron entre `actual` y `anterior` (la versión
 * inmediatamente previa en el tiempo), en castellano simple. La primera
 * versión del historial (`anterior === null`) no tiene nada que comparar. */
export function camposCambiados(
  actual: VersionDelHistorial,
  anterior: VersionDelHistorial | null,
): string[] {
  if (anterior === null) {
    return [];
  }
  return _CAMPOS
    .filter(
      (campo) =>
        String(actual[campo as keyof VersionDelHistorial]) !==
        String(anterior[campo as keyof VersionDelHistorial]),
    )
    .map((campo) => _ETIQUETAS[campo] as string);
}
