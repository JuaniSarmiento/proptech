/**
 * Barra de progreso de la puesta a punto (enmienda del 20/10/2026): "3 de
 * 6 pasos" en texto y la barra como `progressbar` con sus valores, así el
 * lector de pantalla oye lo mismo que se ve. Los números son conteos de
 * pasos que ya vienen marcados por la API (nunca plata ni coeficientes).
 * El relleno usa `transform: scaleX` (nunca `width`): no se anima layout.
 */

import type { CSSProperties } from "react";
import { useId } from "react";

type Props = {
  hechos: number;
  total: number;
};

export function BarraDeProgreso({ hechos, total }: Props) {
  const idTexto = useId();
  const texto = `${hechos} de ${total} pasos`;
  const fraccion = total > 0 ? hechos / total : 0;
  return (
    <div className="barra-de-progreso">
      <p id={idTexto} className="barra-de-progreso__texto numero-tabular">
        {texto}
      </p>
      <div
        role="progressbar"
        aria-labelledby={idTexto}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={hechos}
        aria-valuetext={texto}
        className="barra-de-progreso__pista"
      >
        <div
          className="barra-de-progreso__relleno"
          style={{ "--progreso": fraccion } as CSSProperties}
        />
      </div>
    </div>
  );
}
