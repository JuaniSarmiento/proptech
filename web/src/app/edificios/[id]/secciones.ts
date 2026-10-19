/**
 * Las cinco secciones del menú lateral fijo dentro de un edificio (D10,
 * tarea 4.2): Resumen, Unidades, Grupos, Categorías e Intereses y
 * vencimiento. "Confirmar sin saldos previos" NO va acá (D11): se llega
 * desde el resumen, nunca desde el menú.
 */

import type { SeccionDelEdificio } from "../../../componentes/MenuDelEdificio";

export function seccionesDelEdificio(id: string): SeccionDelEdificio[] {
  return [
    { clave: "resumen", etiqueta: "Resumen", href: `/edificios/${id}` },
    { clave: "unidades", etiqueta: "Unidades", href: `/edificios/${id}/unidades` },
    { clave: "grupos", etiqueta: "Grupos", href: `/edificios/${id}/grupos` },
    { clave: "categorias", etiqueta: "Categorías", href: `/edificios/${id}/categorias` },
    {
      clave: "configuracion",
      etiqueta: "Intereses y vencimiento",
      href: `/edificios/${id}/configuracion`,
    },
  ];
}
