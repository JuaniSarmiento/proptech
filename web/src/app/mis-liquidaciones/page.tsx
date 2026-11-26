/**
 * Mis liquidaciones (change 11, H-040): lee `mis-unidades`. No escribe nada.
 */

import { misUnidades } from "../../lib/api/vecino";
import { pantallaDeError } from "../_portal/errores";
import { PantallaMisLiquidaciones } from "./Pantalla";

export default async function PaginaMisLiquidaciones() {
  const resultado = await misUnidades();
  const error = pantallaDeError([resultado], "No pudimos cargar tus unidades.");
  if (error || resultado.estado !== "ok") return error;
  return <PantallaMisLiquidaciones unidades={resultado.datos.unidades} />;
}
