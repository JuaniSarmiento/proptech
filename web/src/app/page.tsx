import { redirect } from "next/navigation";
import { sesionActual } from "../lib/sesion";

/**
 * La raíz no tiene contenido propio (pulido-2, 3d): con sesión lleva a la lista de
 * edificios y sin sesión a la pantalla de ingreso. Pendiente de confirmar con Juani.
 */
export default async function Page() {
  const sesion = await sesionActual();
  redirect(sesion ? "/edificios" : "/ingresar");
}
