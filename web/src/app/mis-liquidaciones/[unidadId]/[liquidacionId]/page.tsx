/**
 * La expensa de un mes (change 11, H-040): lee las unidades (el edificio de la unidad y el menú) y la
 * expensa. Abrirla distribuye la liquidación del lado de la API (D-074): la pantalla no hace nada
 * aparte. Una unidad o liquidación que no es de la persona, o que no existe, es un 404 sin ningún dato
 * (N01).
 */

import { notFound } from "next/navigation";
import { expensaDeLaUnidad, misUnidades } from "../../../../lib/api/vecino";
import { pantallaDeError } from "../../../_portal/errores";
import { PantallaExpensa } from "./Pantalla";

type Props = { params: Promise<{ unidadId: string; liquidacionId: string }> };

export default async function PaginaExpensa({ params }: Props) {
  const { unidadId, liquidacionId } = await params;
  const [unidades, expensa] = await Promise.all([
    misUnidades(),
    expensaDeLaUnidad(unidadId, liquidacionId),
  ]);
  const error = pantallaDeError([expensa, unidades], "No pudimos cargar tu expensa.");
  if (error || unidades.estado !== "ok" || expensa.estado !== "ok") return error;
  const unidad = unidades.datos.unidades.find((u) => u.unidad_id === unidadId);
  if (!unidad) notFound();
  return (
    <PantallaExpensa expensa={expensa.datos} unidad={unidad} unidades={unidades.datos.unidades} />
  );
}
