/**
 * D7 (tarea 5.4, L-047): límites y patrones que la API también exige —
 * una sola constante por regla, usada en la ayuda, en el mensaje de error
 * previo al envío Y en el mensaje que llega de la API. Nunca sólo en el
 * mensaje genérico, y nunca sólo `maxLength`/`pattern` nativos del input
 * (dan una burbuja del navegador sin `aria-describedby`).
 *
 * Fuente de cada número: `backend/src/proptech_core/complejos/aplicacion/
 * unidades.py` (`identificador: Field(max_length=40)`) y `grupos.py`
 * (`PATRON_CLAVE`, `re.fullmatch(r"[a-z][a-z0-9_]{0,39}", ...)`).
 * `tipos.test.ts` ya guarda la forma de los fixtures contra la API real;
 * estos números no viajan en ningún fixture (son límites de ENTRADA, no de
 * lectura), así que quedan documentados acá con su origen exacto.
 */

export const IDENTIFICADOR_MAXIMO = 40;

export const COEFICIENTE_MAXIMO = 1;
export const COEFICIENTE_DECIMALES_MAXIMOS = 6;

export const PATRON_CLAVE = /^[a-z][a-z0-9_]{0,39}$/;
export const CLAVE_MAXIMO = 40;

export function identificadorDemasiadoLargo(valor: string): boolean {
  return valor.length > IDENTIFICADOR_MAXIMO;
}

/** Un coeficiente cargado como porcentaje ("50" o "100") en vez de la
 * proporción decimal que pide la API ("0.5", "1"). No es la única forma de
 * mandar un coeficiente inválido (la API valida el resto); esto sólo
 * agarra el error de tipeo más común antes de gastar un viaje a la API. */
export function pareceCoeficienteComoPorcentaje(texto: string): boolean {
  const numero = Number(texto.replace(",", "."));
  return Number.isFinite(numero) && numero > COEFICIENTE_MAXIMO;
}

export function claveInvalida(valor: string): boolean {
  return !PATRON_CLAVE.test(valor);
}
