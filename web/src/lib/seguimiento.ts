/**
 * El número de seguimiento (`request_id`) del lado de la web (D8).
 *
 * Mismas reglas que `proptech_core/compartido/seguimiento.py` (L-009): un
 * valor válido es un UUID en forma canónica (36 caracteres, `8-4-4-4-12`
 * hexadecimal). Se valida con una expresión anclada con `^...$`, sin la
 * bandera `m` (si no, `^`/`$` matchean en cada salto de línea y un valor con
 * un salto de línea embebido se aceptaría), y con clases `[0-9a-fA-F]`
 * explícitas (nunca `\d` ni la bandera `i`, que en Unicode podría aceptar
 * algo que no es ASCII). Se valida antes de normalizar a minúsculas
 * (L-008): nunca se recorta ni se pasa a minúsculas un valor para después
 * aceptarlo.
 */

const PATRON_UUID_CANONICO =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

/** Devuelve el valor normalizado a minúsculas si es un UUID canónico válido,
 * o `null` si no lo es (quien llama genera uno nuevo en ese caso). */
export function validarRequestId(valor: string): string | null {
  if (!PATRON_UUID_CANONICO.test(valor)) {
    return null;
  }
  return valor.toLowerCase();
}

/** Devuelve el `x-request-id` entrante si es un UUID válido, normalizado; si
 * no, genera uno nuevo con `crypto.randomUUID()`. */
export function requestIdDe(cabeceras: Headers): string {
  const entrante = cabeceras.get("x-request-id");
  const validado = entrante === null ? null : validarRequestId(entrante);
  return validado ?? crypto.randomUUID();
}

/** Arma las cabeceras para reenviar hacia la API: sólo `X-Request-ID`, con
 * el valor de `requestIdDe`. */
export function cabecerasHaciaLaApi(cabeceras: Headers): Headers {
  const nuevas = new Headers();
  nuevas.set("X-Request-ID", requestIdDe(cabeceras));
  return nuevas;
}
