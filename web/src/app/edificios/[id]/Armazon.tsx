/**
 * Layout común de las pantallas dentro de un edificio (D10): menú lateral
 * fijo + contenido. Composición pura (sin estado propio): `MenuDelEdificio`
 * ya es quien maneja su interactividad.
 */

import type { ReactNode } from "react";
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
    <div className="armazon-del-edificio">
      <MenuDelEdificio
        nombreEdificio={nombreEdificio}
        seccionActual={seccionActual}
        secciones={seccionesDelEdificio(id)}
      />
      <main className="armazon-del-edificio__contenido">{children}</main>
    </div>
  );
}
