"use server";

/**
 * Alta de un edificio (D1, tarea 4.1): server action que llama al cliente
 * de la API y devuelve errores por campo; si la API confirma, redirige al
 * resumen del edificio nuevo ("al guardar lleva al resumen").
 */

import { redirect } from "next/navigation";
import { crearEdificio } from "../../lib/api/edificios";
import { erroresDeFormulario } from "../../lib/api/mensajes";
import type { EstadoCrearEdificio } from "./Pantalla";

const _CAMPOS_CONOCIDOS = ["nombre", "localidad"];

export async function crearEdificioAction(
  _estadoPrevio: EstadoCrearEdificio,
  formData: FormData,
): Promise<EstadoCrearEdificio> {
  const nombre = String(formData.get("nombre") ?? "");
  const localidad = String(formData.get("localidad") ?? "");
  const resultado = await crearEdificio({ nombre, localidad });

  if (resultado.estado === "ok") {
    redirect(`/edificios/${resultado.datos.id}`);
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores, _CAMPOS_CONOCIDOS);
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: [
        "No podés crear un edificio nuevo. Esto lo puede hacer el super admin de la empresa.",
      ],
    };
  }
  if (resultado.estado === "sin_sesion") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["Tu sesión expiró. Iniciá sesión de nuevo."],
    };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos guardar los datos. Probá de nuevo."],
  };
}
