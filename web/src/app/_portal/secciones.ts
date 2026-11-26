/**
 * El menú del portal del vecino (change 11, H-040): cuatro enlaces, siempre los mismos, en un solo
 * grupo. "Mis pagos" vive dentro de un edificio (`/edificios/{id}/mis-pagos`): se arma con el edificio
 * de la PRIMERA unidad de la persona (el orden de `mis-unidades`) y, si no tiene ninguna, no se
 * muestra. Ninguna sección pide una acción: el portal ya es de quien tiene unidades; la API frena
 * igual lo que no le toca.
 */

import type { SeccionDelEdificio } from "../../componentes/MenuDelEdificio";

const GRUPO = "Mi cuenta";

export function seccionesDelPortal(edificioDeMisPagos: string | null): SeccionDelEdificio[] {
  return [
    { clave: "inicio", etiqueta: "Inicio", href: "/inicio", grupo: GRUPO, icono: "inicio" },
    {
      clave: "mis-liquidaciones",
      etiqueta: "Mis liquidaciones",
      href: "/mis-liquidaciones",
      grupo: GRUPO,
      icono: "mis_liquidaciones",
    },
    {
      clave: "comprobantes",
      etiqueta: "Comprobantes",
      href: "/comprobantes",
      grupo: GRUPO,
      icono: "comprobantes",
    },
    ...(edificioDeMisPagos === null
      ? []
      : [
          {
            clave: "mis-pagos",
            etiqueta: "Mis pagos",
            href: `/edificios/${edificioDeMisPagos}/mis-pagos`,
            grupo: GRUPO,
            icono: "mis_pagos" as const,
          },
        ]),
  ];
}
