/**
 * Lista de liquidaciones del edificio (change 7, H-017): cada una con su período en palabras, su
 * estado en texto (nunca sólo color) y su total, con un link al período salvo las anuladas; y el
 * link para preparar el mes que sigue. Sólo formatea lo que llega de la API (R07, D-046).
 */

import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../../componentes/Panel";
import type {
  EstadoDeLaLiquidacion,
  LiquidacionDeLaLista,
} from "../../../../lib/api/liquidaciones";
import { dinero, periodoEnPalabras } from "../../../../lib/formato";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_LISTA_DE_LIQUIDACIONES } from "./ayuda";

const ESTADOS: Record<EstadoDeLaLiquidacion, string> = {
  emitida: "Emitida",
  distribuida: "Distribuida",
  anulada: "Anulada",
};

type Props = {
  id: string;
  nombreEdificio: string;
  liquidaciones: LiquidacionDeLaLista[];
  /** El mes a preparar, `AAAA-MM`. */
  periodoParaPreparar: string;
};

export function PantallaListaDeLiquidaciones({
  id,
  nombreEdificio,
  liquidaciones,
  periodoParaPreparar,
}: Props) {
  const paraPreparar = periodoEnPalabras(periodoParaPreparar) ?? periodoParaPreparar;
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="liquidaciones">
      <EncabezadoDePantalla
        titulo="Liquidaciones"
        ayuda={<Ayuda {...AYUDA_LISTA_DE_LIQUIDACIONES} />}
        accionPrincipal={
          <a
            className="boton-principal"
            href={`/edificios/${id}/liquidaciones/${periodoParaPreparar}`}
          >
            Preparar la liquidación de {paraPreparar}
          </a>
        }
      />
      <Panel
        titulo="Períodos"
        descripcion="De la más nueva a la más vieja. Las anuladas quedan a la vista, sin acciones."
      >
        {liquidaciones.length === 0 ? (
          <p className="texto-secundario">Todavía no se emitió ninguna liquidación.</p>
        ) : (
          <ul className="lista-de-filas">
            {liquidaciones.map((liquidacion) => {
              const periodo = liquidacion.periodo.slice(0, 7);
              const enPalabras = periodoEnPalabras(periodo) ?? periodo;
              return (
                <li key={liquidacion.liquidacion_id}>
                  {liquidacion.estado === "anulada" ? (
                    <strong>{enPalabras}</strong>
                  ) : (
                    <a href={`/edificios/${id}/liquidaciones/${periodo}`}>{enPalabras}</a>
                  )}
                  <span className="texto-secundario"> · {ESTADOS[liquidacion.estado]} · </span>
                  <span className="numero-tabular">{dinero(liquidacion.total)}</span>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </ArmazonDelEdificio>
  );
}
