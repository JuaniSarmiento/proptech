/**
 * Mis liquidaciones (change 11, H-040, C02): las unidades de la persona, cada una con su enlace a la
 * lista de sus liquidaciones emitidas.
 */

import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Panel } from "../../componentes/Panel";
import type { UnidadDelVecino } from "../../lib/api/vecino";
import { ArmazonDelPortal } from "../_portal/ArmazonDelPortal";
import { AYUDA_MIS_LIQUIDACIONES } from "./ayuda";

export function PantallaMisLiquidaciones({ unidades }: { unidades: UnidadDelVecino[] }) {
  return (
    <ArmazonDelPortal seccionActual="mis-liquidaciones" unidades={unidades}>
      <EncabezadoDePantalla
        titulo="Mis liquidaciones"
        ayuda={<Ayuda {...AYUDA_MIS_LIQUIDACIONES} />}
      />
      <Panel titulo="Tus unidades" descripcion="Elegí la unidad de la que querés ver las expensas.">
        {unidades.length === 0 ? (
          <p role="status" className="texto-secundario">
            Todavía no tenés unidades asociadas a tu cuenta.
          </p>
        ) : (
          <ul className="lista-de-unidades" aria-label="Mis unidades">
            {unidades.map((u) => (
              <li key={u.unidad_id} className="unidad-del-vecino unidad-del-vecino--simple">
                <div className="unidad-del-vecino__cabecera">
                  <p className="unidad-del-vecino__nombre">{u.identificador}</p>
                  <p className="texto-secundario">{u.edificio}</p>
                </div>
                <a className="unidad-del-vecino__enlace" href={`/mis-liquidaciones/${u.unidad_id}`}>
                  Ver liquidaciones de {u.identificador}
                </a>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </ArmazonDelPortal>
  );
}
