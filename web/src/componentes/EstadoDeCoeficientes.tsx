/**
 * Estado de R01 (D8, The Never Color Alone Rule, tarea 3.7): texto más la
 * diferencia, nunca sólo color. Lee `informe.diferencia` como TEXTO
 * decimal, igual que `formato.ts` (D6): nunca lo calcula.
 */

import { diferenciaComoPorcentaje } from "../lib/formato";

type Props = {
  estado: string;
  diferencia: string;
};

export function EstadoDeCoeficientes({ estado, diferencia }: Props) {
  if (estado === "ok") {
    return (
      <p className="estado-de-coeficientes estado-de-coeficientes--ok">Coeficientes al 100%</p>
    );
  }

  const texto = diferenciaComoPorcentaje(diferencia);

  if (estado === "advertencia") {
    return (
      <p className="estado-de-coeficientes estado-de-coeficientes--advertencia">
        Atención: {texto} para llegar a 100%
      </p>
    );
  }

  return (
    <p className="estado-de-coeficientes estado-de-coeficientes--fuera-de-tolerancia">
      Fuera de tolerancia: {texto} para llegar a 100%
    </p>
  );
}
