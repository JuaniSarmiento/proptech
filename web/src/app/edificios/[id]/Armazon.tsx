/**
 * Layout común de las pantallas dentro de un edificio (D10, enmienda del
 * 20/10/2026): el armazón general con el edificio en la barra superior y
 * el menú agrupado con íconos. Composición pura (sin estado propio).
 */

import type { ReactNode } from "react";
import { Armazon } from "../../../componentes/Armazon";
import { MenuDelEdificio } from "../../../componentes/MenuDelEdificio";
import { seccionesDelEdificio } from "./secciones";

type Props = {
  id: string;
  nombreEdificio: string;
  seccionActual: string;
  children: ReactNode;
};

export function ArmazonDelEdificio({ id, nombreEdificio, seccionActual, children }: Props) {
  return (
    <Armazon
      edificio={{ nombre: nombreEdificio }}
      menu={<MenuDelEdificio seccionActual={seccionActual} secciones={seccionesDelEdificio(id)} />}
    >
      {children}
    </Armazon>
  );
}
