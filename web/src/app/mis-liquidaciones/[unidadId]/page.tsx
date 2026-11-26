/**
 * Las liquidaciones de una unidad (change 11, H-040): lee las unidades (el nombre de la unidad y el
 * menú) y sus liquidaciones. Una unidad que no es de la persona, o que no existe, es un 404 sin
 * ningún dato (N01). No escribe nada.
 */

import { notFound } from "next/navigation";
import { liquidacionesDeLaUnidad, misUnidades } from "../../../lib/api/vecino";
import { pantallaDeError } from "../../_portal/errores";
import { PantallaLiquidacionesDeLaUnidad } from "./Pantalla";

type Props = { params: Promise<{ unidadId: string }> };

export default async function PaginaLiquidacionesDeLaUnidad({ params }: Props) {
  const { unidadId } = await params;
  const [unidades, liquidaciones] = await Promise.all([
    misUnidades(),
    liquidacionesDeLaUnidad(unidadId),
  ]);
  const error = pantallaDeError([liquidaciones, unidades], "No pudimos cargar tus liquidaciones.");
  if (error || unidades.estado !== "ok" || liquidaciones.estado !== "ok") return error;
  const unidad = unidades.datos.unidades.find((u) => u.unidad_id === unidadId);
  if (!unidad) notFound();
  return (
    <PantallaLiquidacionesDeLaUnidad
      unidad={unidad}
      unidades={unidades.datos.unidades}
      liquidaciones={liquidaciones.datos}
    />
  );
}
