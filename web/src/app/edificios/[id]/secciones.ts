/**
 * Las cinco secciones del menú lateral fijo dentro de un edificio (D10,
 * tarea 4.2), agrupadas como pide la enmienda del 20/10/2026: "El edificio"
 * (Resumen, Unidades, Grupos) y "Configuración" (Categorías, Intereses y
 * vencimiento). "Confirmar sin saldos previos" NO va acá (D11): se llega
 * desde el resumen, nunca desde el menú.
 *
 * El ícono viaja como CLAVE, no como componente: `MenuDelEdificio` es un
 * componente de cliente y una función no se puede pasar del servidor al
 * cliente como prop.
 */

import type { SeccionDelEdificio } from "../../../componentes/MenuDelEdificio";

export function seccionesDelEdificio(id: string): SeccionDelEdificio[] {
  return [
    {
      clave: "resumen",
      etiqueta: "Resumen",
      href: `/edificios/${id}`,
      grupo: "El edificio",
      icono: "resumen",
    },
    {
      clave: "unidades",
      etiqueta: "Unidades",
      href: `/edificios/${id}/unidades`,
      grupo: "El edificio",
      icono: "unidades",
    },
    {
      clave: "grupos",
      etiqueta: "Grupos",
      href: `/edificios/${id}/grupos`,
      grupo: "El edificio",
      icono: "grupos",
    },
    {
      clave: "categorias",
      etiqueta: "Categorías",
      href: `/edificios/${id}/categorias`,
      grupo: "Configuración",
      icono: "categorias",
    },
    {
      clave: "configuracion",
      etiqueta: "Intereses y vencimiento",
      href: `/edificios/${id}/configuracion`,
      grupo: "Configuración",
      icono: "configuracion",
    },
  ];
}
