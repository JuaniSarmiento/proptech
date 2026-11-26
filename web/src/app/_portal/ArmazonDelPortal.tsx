/**
 * Layout común de las pantallas del portal del vecino (H-040): el armazón general con el menú "Portal
 * del vecino" y el registro del service worker. Composición pura, sin estado propio.
 */

import type { ReactNode } from "react";
import { Armazon } from "../../componentes/Armazon";
import { MenuDelEdificio } from "../../componentes/MenuDelEdificio";
import type { MisUnidades } from "../../lib/api/vecino";
import { RegistroDelServiceWorker } from "./RegistroDelServiceWorker";
import { seccionesDelPortal } from "./secciones";

type Props = {
  seccionActual: "inicio" | "mis-liquidaciones" | "comprobantes";
  /** Las unidades de la persona: el edificio de la primera es el de "Mis pagos". */
  unidades: MisUnidades["unidades"];
  children: ReactNode;
};

export function ArmazonDelPortal({ seccionActual, unidades, children }: Props) {
  return (
    <Armazon
      menu={
        <MenuDelEdificio
          nombreAccesible="Portal del vecino"
          seccionActual={seccionActual}
          secciones={seccionesDelPortal(unidades[0]?.complejo_id ?? null)}
        />
      }
    >
      <RegistroDelServiceWorker />
      <div className="portal">{children}</div>
    </Armazon>
  );
}
