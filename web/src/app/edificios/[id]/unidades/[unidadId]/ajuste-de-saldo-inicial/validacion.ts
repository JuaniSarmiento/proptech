/**
 * Lo que la pantalla del ajuste y su acción comparten (sin `"use server"`: un archivo de acciones
 * sólo exporta funciones asíncronas). El importe se escribe con coma decimal y viaja con punto y
 * dos decimales; lo que no cierra como plata positiva con hasta dos decimales da `null` y no sale
 * del navegador ni del servidor de Next.
 */

export const CONCEPTOS = ["ordinaria", "fondo_de_reserva", "extraordinaria"];
export const MOTIVO_MAXIMO = 500;

const _MENSAJES = {
  importe: "Poné un importe mayor que cero, con hasta dos decimales. Ejemplo: 5000,00.",
  motivo: `Contá el motivo en pocas palabras (hasta ${MOTIVO_MAXIMO} caracteres).`,
  componente: "Elegí a qué concepto corresponde el ajuste.",
} as const;

export const MENSAJES_DE_CAMPO: Record<string, string | undefined> & typeof _MENSAJES = _MENSAJES;

/** `"5000.5"` -> `"5000.50"`; `null` si no es un importe positivo con a lo sumo dos decimales. */
export function importeParaApi(texto: string): string | null {
  const partes = /^([0-9]+)(?:\.([0-9]{1,2}))?$/.exec(texto);
  if (!partes) return null;
  const entera = partes[1] ?? "";
  const decimales = (partes[2] ?? "").padEnd(2, "0");
  return /[1-9]/.test(entera + decimales) ? `${entera}.${decimales}` : null;
}
