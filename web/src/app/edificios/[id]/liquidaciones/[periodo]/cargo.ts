/**
 * Lo que el diálogo del "cargo cobrado de menos" y su acción comparten (sin `"use server"`: un
 * archivo de acciones sólo exporta funciones asíncronas). El importe se escribe con coma decimal y
 * viaja con punto y dos decimales, convertido por texto (el frontend no calcula montos).
 */

import { importeParaApi } from "../../unidades/[unidadId]/ajuste-de-saldo-inicial/validacion";

export const MOTIVO_DEL_CARGO_MAXIMO = 500;

export const CONCEPTOS_DEL_CARGO: { valor: string; texto: string }[] = [
  { valor: "ordinaria", texto: "Ordinaria" },
  { valor: "fondo_de_reserva", texto: "Fondo de reserva" },
  { valor: "extraordinaria", texto: "Extraordinaria" },
];

export const MENSAJES_DEL_CARGO = {
  importe: "Poné un importe mayor que cero, con hasta dos decimales. Ejemplo: 1500,00.",
  componente: "Elegí a qué concepto corresponde el cargo.",
  motivo: `Contá el motivo en pocas palabras (hasta ${MOTIVO_DEL_CARGO_MAXIMO} caracteres).`,
} as const;

export { importeParaApi };
