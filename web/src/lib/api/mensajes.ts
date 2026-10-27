/**
 * Diccionario de mensajes en castellano simple por motivo (D2, tarea 4.1):
 * un 422/409 de la API llega a la pantalla ya traducido, nunca con el texto
 * de la API (L-007 — `cliente.ts` ya extrae sólo `type`/`campo`, vocabulario
 * cerrado; este diccionario es el último paso antes de mostrarlo).
 */

import type { ErrorDeCampo } from "./cliente";

const _MENSAJES: Record<string, string> = {
  missing: "Este dato es obligatorio.",
  string_too_short: "Es muy corto.",
  string_too_long: "Es muy largo.",
  value_error: "Este valor no es válido.",
  int_parsing: "Tiene que ser un número entero.",
  decimal_parsing: "Tiene que ser un número.",
  literal_error: "Elegí una de las opciones.",
  greater_than: "Tiene que ser mayor a cero.",
};

const _GENERICO = "Revisá este dato.";

/** `fuera_de_rango` (D3, tarea 3.5): la API manda `identificadores`, una
 * lista cerrada de datos propios del edificio (nunca texto libre ni el
 * valor del pedido, L-007) — la plantilla es nuestra, nunca el `msg` crudo
 * de la API, que `cliente.ts` ni siquiera expone. */
function _mensajeFueraDeRango(identificadores: string[]): string {
  return `Quedarían unidades fuera de rango: ${identificadores.join(", ")}.`;
}

/** R3C-8 (rompedor 3b): el mismo texto que ya usaba `crearEdificioAction`
 * para un 401 — hasta el 2b la API de producción siempre da 401, así que
 * cada escritura sin este mapeo invitaba a reintentar algo que nunca iba
 * a andar ("No pudimos guardar los datos. Probá de nuevo."). */
export const MENSAJE_SIN_SESION = "Tu sesión expiró. Iniciá sesión de nuevo.";

/** Traduce un `motivo` (el `type` de Pydantic, vocabulario cerrado) a
 * castellano simple; un motivo que no está en el diccionario da el mensaje
 * genérico, nunca el texto técnico. */
export function mensajeDeError(motivo: string): string {
  return _MENSAJES[motivo] ?? _GENERICO;
}

export type ErroresSeparados = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
};

/** Separa los errores de la API entre los que corresponden a un campo que
 * el formulario conoce (`camposConocidos`) y los que no: un error de un
 * campo desconocido va sólo al resumen, nunca marcando un campo de más
 * (D8, tarea 3.7). Misma forma que espera `Formulario` (D8), para pasarla
 * directo desde la server action de cada pantalla. */
export function erroresDeFormulario(
  errores: ErrorDeCampo[],
  camposConocidos: string[],
): ErroresSeparados {
  const erroresPorCampo: Record<string, string> = {};
  const erroresDesconocidos: string[] = [];
  for (const error of errores) {
    const mensaje =
      error.motivo === "fuera_de_rango" && error.identificadores
        ? _mensajeFueraDeRango(error.identificadores)
        : mensajeDeError(error.motivo);
    if (camposConocidos.includes(error.campo)) {
      erroresPorCampo[error.campo] = mensaje;
    } else {
      erroresDesconocidos.push(mensaje);
    }
  }
  return { erroresPorCampo, erroresDesconocidos };
}
