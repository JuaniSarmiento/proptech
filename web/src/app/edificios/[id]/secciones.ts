/**
 * Las secciones del menú lateral fijo dentro de un edificio (D10,
 * tarea 4.2), agrupadas como pide la enmienda del 20/10/2026: "El edificio"
 * (Resumen, Unidades, Grupos), "Liquidación" (Liquidaciones, H-017: sólo con
 * `ver_liquidaciones`; Pagos y Mis pagos, H-025: sólo con `confirmar_pago_informado` o
 * `informar_pago`; Morosidad, H-029, y Cuentas de vendedores, H-034: sólo con `ver_morosidad`) y "Configuración" (Categorías, Intereses y
 * vencimiento). "Confirmar sin saldos previos" NO va acá (D11): se llega
 * desde el resumen, nunca desde el menú.
 *
 * El ícono viaja como CLAVE, no como componente: `MenuDelEdificio` es un
 * componente de cliente y una función no se puede pasar del servidor al
 * cliente como prop.
 *
 * H-026: las cinco secciones de la configuración (Resumen, Unidades, Grupos, Categorías, Intereses y
 * vencimiento) piden `ver_configuracion_del_edificio`: la vecina ve sólo "Mis pagos".
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
      accion: "ver_configuracion_del_edificio",
      complejoId: id,
    },
    {
      clave: "unidades",
      etiqueta: "Unidades",
      href: `/edificios/${id}/unidades`,
      grupo: "El edificio",
      icono: "unidades",
      accion: "ver_configuracion_del_edificio",
      complejoId: id,
    },
    {
      clave: "grupos",
      etiqueta: "Grupos",
      href: `/edificios/${id}/grupos`,
      grupo: "El edificio",
      icono: "grupos",
      accion: "ver_configuracion_del_edificio",
      complejoId: id,
    },
    {
      clave: "liquidaciones",
      etiqueta: "Liquidaciones",
      href: `/edificios/${id}/liquidaciones`,
      grupo: "Liquidación",
      icono: "liquidaciones",
      accion: "ver_liquidaciones",
      complejoId: id,
    },
    {
      clave: "pagos",
      etiqueta: "Pagos",
      href: `/edificios/${id}/pagos`,
      grupo: "Liquidación",
      icono: "pagos",
      accion: "confirmar_pago_informado",
      complejoId: id,
    },
    {
      clave: "mis-pagos",
      etiqueta: "Mis pagos",
      href: `/edificios/${id}/mis-pagos`,
      grupo: "Liquidación",
      icono: "mis_pagos",
      accion: "informar_pago",
      complejoId: id,
    },
    {
      clave: "morosidad",
      etiqueta: "Morosidad",
      href: `/edificios/${id}/morosidad`,
      grupo: "Liquidación",
      icono: "morosidad",
      accion: "ver_morosidad",
      complejoId: id,
    },
    {
      clave: "cuentas-de-vendedores",
      etiqueta: "Cuentas de vendedores",
      href: `/edificios/${id}/cuentas-de-vendedores`,
      grupo: "Liquidación",
      icono: "cuentas_de_vendedores",
      accion: "ver_morosidad",
      complejoId: id,
    },
    {
      clave: "categorias",
      etiqueta: "Categorías",
      href: `/edificios/${id}/categorias`,
      grupo: "Configuración",
      icono: "categorias",
      accion: "ver_configuracion_del_edificio",
      complejoId: id,
    },
    {
      clave: "configuracion",
      etiqueta: "Intereses y vencimiento",
      href: `/edificios/${id}/configuracion`,
      grupo: "Configuración",
      icono: "configuracion",
      accion: "ver_configuracion_del_edificio",
      complejoId: id,
    },
  ];
}
