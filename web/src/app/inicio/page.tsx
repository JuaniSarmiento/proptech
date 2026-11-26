/**
 * Inicio del portal del vecino (change 11, H-040): lee `mis-unidades`. No escribe nada: abrir la
 * pantalla es sólo mirar.
 */

import { misUnidades } from "../../lib/api/vecino";
import { pantallaDeError } from "../_portal/errores";
import { PantallaInicio } from "./Pantalla";

export default async function PaginaInicio() {
  const resultado = await misUnidades();
  const error = pantallaDeError([resultado], "No pudimos cargar tus unidades.");
  if (error || resultado.estado !== "ok") return error;
  return <PantallaInicio datos={resultado.datos} />;
}
