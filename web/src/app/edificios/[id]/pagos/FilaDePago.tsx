/**
 * Un pago informado como renglón de una lista (change 8, H-025): el número de operación, el banco, la
 * fecha y las unidades, el monto, el estado en texto (nunca sólo color ni sólo ícono) y, si lo hubo, el
 * motivo del rechazo o de la reversión. Sólo formatea lo que llega de la API: no suma ni redondea (R07).
 * `acciones` son los botones que la pantalla quiera poner debajo (la bandeja del administrador).
 */

import { CircleCheck, CircleX, Clock, type LucideIcon, Undo2 } from "lucide-react";
import type { ReactNode } from "react";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import type { EstadoDelPago, PagoInformado } from "../../../../lib/api/pagos";
import { dinero, fecha } from "../../../../lib/formato";

export const TEXTO_DEL_ESTADO: Record<EstadoDelPago, string> = {
  informado: "Informado",
  confirmado: "Confirmado",
  rechazado: "Rechazado",
  revertido: "Revertido",
};

const ICONO_DEL_ESTADO: Record<EstadoDelPago, LucideIcon> = {
  informado: Clock,
  confirmado: CircleCheck,
  rechazado: CircleX,
  revertido: Undo2,
};

type Props = {
  pago: PagoInformado;
  acciones?: ReactNode;
  /** La bandeja dice dónde está hoy la plata de una parte reimputada (H-026). */
  mostrarDondeEsta?: boolean;
};

/** Los identificadores donde está hoy la plata de las partes que ya no están en su unidad original. */
export function dondeEstaHoy(pago: PagoInformado): string {
  return pago.partes
    .filter((parte) => parte.unidad_vigente_id !== parte.unidad_id)
    .map((parte) => parte.identificador_vigente)
    .join(", ");
}

export function FilaDePago({ pago, acciones, mostrarDondeEsta = false }: Props) {
  const unidades = pago.partes.map((parte) => parte.identificador).join(", ");
  const ahoraEn = mostrarDondeEsta ? dondeEstaHoy(pago) : "";
  return (
    <FilaConIcono
      icono={ICONO_DEL_ESTADO[pago.estado]}
      tono={pago.estado === "informado" ? "atencion" : "listo"}
      titulo={`Operación ${pago.numero_de_operacion}`}
      detalle={
        <>
          <span className="fila-de-pago__renglon">
            {pago.banco} · {fecha(pago.fecha_de_transferencia)}
            {unidades === ""
              ? ""
              : ` · ${pago.partes.length === 1 ? "Unidad" : "Unidades"} ${unidades}`}
          </span>
          {ahoraEn === "" ? null : (
            <span className="fila-de-pago__renglon">Ahora en {ahoraEn}</span>
          )}
          {pago.motivo ? (
            <span className="fila-de-pago__renglon">Motivo: {pago.motivo}</span>
          ) : null}
          {acciones ? <span className="acciones-de-la-fila">{acciones}</span> : null}
        </>
      }
      fin={
        <>
          <span className="numero-tabular fila-de-pago__monto">{dinero(pago.monto)}</span>
          <span className="fila-de-pago__estado">{TEXTO_DEL_ESTADO[pago.estado]}</span>
        </>
      }
    />
  );
}
