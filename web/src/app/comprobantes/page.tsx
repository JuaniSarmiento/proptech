/**
 * Comprobantes (change 11, H-040): lee las unidades y, de cada una, sus PDFs y sus pagos confirmados.
 * No escribe nada.
 */

import { misUnidades, pagosConfirmadosDeLaUnidad, pdfsDeLaUnidad } from "../../lib/api/vecino";
import { pantallaDeError } from "../_portal/errores";
import { type ComprobantesDeLaUnidad, PantallaComprobantes } from "./Pantalla";

export default async function PaginaComprobantes() {
  const unidades = await misUnidades();
  if (unidades.estado !== "ok") {
    return pantallaDeError([unidades], "No pudimos cargar tus comprobantes.");
  }
  const leidos = await Promise.all(
    unidades.datos.unidades.map(async (unidad) => {
      const [pdfs, pagos] = await Promise.all([
        pdfsDeLaUnidad(unidad.unidad_id),
        pagosConfirmadosDeLaUnidad(unidad.unidad_id),
      ]);
      return { unidad, pdfs, pagos };
    }),
  );
  const error = pantallaDeError(
    leidos.flatMap((l) => [l.pdfs, l.pagos]),
    "No pudimos cargar tus comprobantes.",
  );
  if (error) return error;
  const porUnidad: ComprobantesDeLaUnidad[] = [];
  for (const { unidad, pdfs, pagos } of leidos) {
    if (pdfs.estado === "ok" && pagos.estado === "ok") {
      porUnidad.push({ unidad, pdfs: pdfs.datos, pagos: pagos.datos });
    }
  }
  return <PantallaComprobantes unidades={unidades.datos.unidades} porUnidad={porUnidad} />;
}
