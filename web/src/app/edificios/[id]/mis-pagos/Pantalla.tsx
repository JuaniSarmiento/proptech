/**
 * Mis pagos (change 8, H-025): los pagos que la persona informó o puede ver de sus unidades, con su
 * estado en texto y el motivo de un rechazo o una reversión, y el camino para informar uno nuevo.
 */

import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../../componentes/Panel";
import type { PagoInformado } from "../../../../lib/api/pagos";
import { ArmazonDelEdificio } from "../Armazon";
import { FilaDePago } from "../pagos/FilaDePago";
import { AYUDA_MIS_PAGOS } from "./ayuda";

type Props = {
  id: string;
  nombreEdificio: string;
  pagos: PagoInformado[];
};

export function PantallaMisPagos({ id, nombreEdificio, pagos }: Props) {
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="mis-pagos">
      <EncabezadoDePantalla
        titulo="Mis pagos"
        ayuda={<Ayuda {...AYUDA_MIS_PAGOS} />}
        accionPrincipal={
          <a className="boton-principal" href={`/edificios/${id}/mis-pagos/informar`}>
            Informar un pago
          </a>
        }
      />
      <Panel
        titulo="Tus pagos"
        descripcion="Del más nuevo al más viejo, con lo que decidió el administrador."
      >
        {pagos.length === 0 ? (
          <p className="texto-secundario">Todavía no informaste ningún pago.</p>
        ) : (
          <ul className="lista-de-filas" aria-label="Pagos informados">
            {pagos.map((pago) => (
              <li key={pago.pago_id}>
                <FilaDePago pago={pago} />
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </ArmazonDelEdificio>
  );
}
