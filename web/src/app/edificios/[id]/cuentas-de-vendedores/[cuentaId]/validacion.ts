/**
 * Lo que la pantalla del cobro y su acción comparten (sin `"use server"`). El importe se escribe con coma
 * decimal y viaja con punto y dos decimales; la API decide si es mayor que cero, si no supera la deuda y
 * si la fecha es posterior a hoy. Los mensajes por campo son de la pantalla: su 422 siempre dice "valor
 * inválido" (C05).
 */

export const MENSAJES_DE_CAMPO: Record<string, string | undefined> = {
  importe: "Poné un importe mayor a cero y que no supere la deuda de la cuenta.",
  fecha: "Poné una fecha válida, que no sea posterior a hoy.",
};

const _FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

/** `"20000,00"` -> `"20000.00"` y `"5.000,5"` -> `"5000.50"`; `null` si no es plata con a lo sumo dos
 * decimales. No decide si alcanza o si es positivo. */
export function importeParaApi(texto: string): string | null {
  const m = /^([0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,([0-9]{1,2}))?$/.exec(texto.trim());
  if (!m) return null;
  return `${(m[1] ?? "").replaceAll(".", "")}.${(m[2] ?? "").padEnd(2, "0")}`;
}

export function validarCobro(importe: string, fecha: string): Record<string, string> {
  const errores: Record<string, string> = {};
  if (importeParaApi(importe) === null) errores.importe = MENSAJES_DE_CAMPO.importe ?? "";
  if (!_FECHA.test(fecha)) errores.fecha = MENSAJES_DE_CAMPO.fecha ?? "";
  return errores;
}
