/**
 * Las liquidaciones de una unidad (change 11, H-040, C02): las emitidas del edificio, la más nueva
 * primero, con su vencimiento y el total de ESA unidad según su vínculo. El total llega de la API: la
 * pantalla no suma nada (N02).
 */

import { Ayuda } from "../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../componentes/Panel";
import type { LiquidacionDeLaLista, UnidadDelVecino } from "../../../lib/api/vecino";
import { dinero, fecha, periodoEnPalabras } from "../../../lib/formato";
import { ArmazonDelPortal } from "../../_portal/ArmazonDelPortal";
import { Cifras } from "../../_portal/Cifras";
import { AYUDA_LIQUIDACIONES_DE_LA_UNIDAD } from "../ayuda";

type Props = {
  unidad: UnidadDelVecino;
  unidades: UnidadDelVecino[];
  liquidaciones: LiquidacionDeLaLista[];
};

export function PantallaLiquidacionesDeLaUnidad({ unidad, unidades, liquidaciones }: Props) {
  return (
    <ArmazonDelPortal seccionActual="mis-liquidaciones" unidades={unidades}>
      <EncabezadoDePantalla
        titulo={`Liquidaciones de ${unidad.identificador}`}
        ayuda={<Ayuda {...AYUDA_LIQUIDACIONES_DE_LA_UNIDAD} />}
      />
      <p className="texto-secundario">{unidad.edificio}</p>
      <Panel titulo="Expensas emitidas" descripcion="De la más nueva a la más vieja.">
        {liquidaciones.length === 0 ? (
          <p role="status" className="texto-secundario">
            Todavía no hay liquidaciones emitidas.
          </p>
        ) : (
          <ul className="lista-de-liquidaciones" aria-label="Liquidaciones">
            {liquidaciones.map((l) => {
              const periodo = periodoEnPalabras(l.periodo) ?? l.periodo;
              return (
                <li key={l.liquidacion_id} className="liquidacion-del-vecino">
                  <div className="liquidacion-del-vecino__textos">
                    <p className="liquidacion-del-vecino__periodo">{periodo}</p>
                    <p className="texto-secundario">Vence el {fecha(l.vencimiento)}</p>
                  </div>
                  <Cifras cifras={[{ rotulo: "Total", valor: dinero(l.total) }]} />
                  <a
                    className="liquidacion-del-vecino__enlace"
                    href={`/mis-liquidaciones/${unidad.unidad_id}/${l.liquidacion_id}`}
                  >
                    Ver expensa de {periodo}
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </ArmazonDelPortal>
  );
}
