/**
 * Fila con ícono (enmienda del 20/10/2026, como "Últimas actividades" de
 * Mercado Pago): ícono de línea en un círculo, un título y una línea gris
 * que explica; a la derecha, lo que la fila necesite (un estado, un número,
 * acciones). El ícono es decorativo (`aria-hidden`): el título siempre
 * dice lo mismo en texto.
 */

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  icono: LucideIcon;
  titulo: ReactNode;
  detalle?: ReactNode;
  fin?: ReactNode;
  /** Marca de estado para el CSS (p.ej. "falta" pinta el círculo). */
  tono?: "neutro" | "atencion" | "listo";
};

export function FilaConIcono({ icono: Icono, titulo, detalle, fin, tono = "neutro" }: Props) {
  return (
    <div className="fila-con-icono" data-tono={tono}>
      <span className="fila-con-icono__icono" aria-hidden="true">
        <Icono size={20} strokeWidth={1.75} />
      </span>
      <div className="fila-con-icono__textos">
        <div className="fila-con-icono__titulo">{titulo}</div>
        {detalle ? <div className="fila-con-icono__detalle">{detalle}</div> : null}
      </div>
      {fin ? <div className="fila-con-icono__fin">{fin}</div> : null}
    </div>
  );
}
