/**
 * Lo que la pantalla del cambio de titular y su acción comparten (sin `"use server"`: un archivo de
 * acciones sólo exporta funciones asíncronas). La API contesta cualquier 422 con "valor inválido": los
 * mensajes por campo son de la pantalla (C05) y la validación de acá sólo evita un viaje inútil, nunca
 * decide: lo que la API sabe (fecha posterior a hoy, vendedores que no son propietarios, el mismo
 * email de los dos lados, un prorrateo repetido) lo dice ella.
 */

import type { PedidoDeCambio } from "../../../../../../lib/api/titularidad";

export const MENSAJES_DE_CAMPO: Record<string, string | undefined> = {
  fecha: "Poné una fecha válida, que no sea posterior a hoy.",
  vendedores: "Elegí al menos un vendedor entre los propietarios actuales.",
  compradores:
    "Revisá los compradores: tiene que haber al menos uno y ninguno puede ser también vendedor.",
  vendedor_deudor: "Elegí cuál de los vendedores queda con la deuda.",
  expensa_del_mes: "Ya hay un prorrateo para esta unidad en ese mes. Elegí la expensa entera.",
  deuda_previa: "Elegí qué pasa con la deuda de meses anteriores.",
};

export type BorradorDeCambio = {
  fecha: string;
  vendedores: string[];
  compradores: { nombre: string; email: string }[];
  expensa: "entera" | "prorrateo";
  deuda: "en_la_unidad" | "a_nombre_del_vendedor";
  deudor: string;
};

/** Hay que elegir quién queda con la deuda: más de un vendedor y algo que se le pasa (la deuda o el
 * prorrateo). Con uno solo no hay a quién elegir. */
export function hayQueElegirDeudor(borrador: BorradorDeCambio): boolean {
  return (
    borrador.vendedores.length > 1 &&
    (borrador.deuda === "a_nombre_del_vendedor" || borrador.expensa === "prorrateo")
  );
}

const _FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

export function validarBorrador(borrador: BorradorDeCambio): Record<string, string> {
  const errores: Record<string, string> = {};
  if (!_FECHA.test(borrador.fecha)) errores.fecha = MENSAJES_DE_CAMPO.fecha ?? "";
  if (borrador.vendedores.length === 0) errores.vendedores = MENSAJES_DE_CAMPO.vendedores ?? "";
  if (
    borrador.compradores.length === 0 ||
    borrador.compradores.some((c) => c.nombre.trim() === "")
  ) {
    errores.compradores = MENSAJES_DE_CAMPO.compradores ?? "";
  }
  if (hayQueElegirDeudor(borrador) && !borrador.vendedores.includes(borrador.deudor)) {
    errores.vendedor_deudor = MENSAJES_DE_CAMPO.vendedor_deudor ?? "";
  }
  return errores;
}

/** El cuerpo del pedido: el email vacío viaja como `null` y el deudor sólo cuando hay que elegirlo. */
export function pedidoDelBorrador(borrador: BorradorDeCambio): PedidoDeCambio {
  return {
    fecha: borrador.fecha,
    vendedores: borrador.vendedores,
    compradores: borrador.compradores.map((c) => ({
      nombre: c.nombre.trim(),
      email: c.email.trim() === "" ? null : c.email.trim(),
    })),
    expensa_del_mes: borrador.expensa,
    deuda_previa: borrador.deuda,
    ...(hayQueElegirDeudor(borrador) ? { vendedor_deudor: borrador.deudor } : {}),
  };
}
