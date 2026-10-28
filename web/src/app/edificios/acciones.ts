"use server";

/**
 * Alta de un edificio (D1, tarea 4.1; D3, tarea 6.1): server action que
 * llama al cliente de la API y devuelve errores por campo; si la API
 * confirma, redirige al resumen del edificio nuevo ("al guardar lleva al
 * resumen"). D3: el trío de ubicación y `pisos`/`subsuelos` son
 * obligatorios en el alta (2.6, 3.2); `calle_y_numero` es opcional.
 */

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { crearEdificio, editarEdificio } from "../../lib/api/edificios";
import { erroresDeFormulario } from "../../lib/api/mensajes";
import type { EstadoEdicionEdificio } from "./[id]/Pantalla";
import type { EstadoCrearEdificio } from "./Pantalla";

const _CAMPOS_CONOCIDOS = [
  "nombre",
  "provincia_id",
  "departamento_id",
  "localidad_id",
  "calle_y_numero",
  "pisos",
  "subsuelos",
];

// R3C-6: un entero estricto, nunca `Number.parseInt` suelto (ver configuracion/acciones.ts).
const _ENTERO_ESTRICTO = /^\d+$/;

function _entero(valor: FormDataEntryValue | null): number {
  const texto = String(valor ?? "").trim();
  return _ENTERO_ESTRICTO.test(texto) ? Number.parseInt(texto, 10) : Number.NaN;
}

function _calleYNumero(formData: FormData): string | null {
  const texto = String(formData.get("calle_y_numero") ?? "").trim();
  return texto === "" ? null : texto;
}

export async function crearEdificioAction(
  _estadoPrevio: EstadoCrearEdificio,
  formData: FormData,
): Promise<EstadoCrearEdificio> {
  const resultado = await crearEdificio({
    nombre: String(formData.get("nombre") ?? ""),
    provincia_id: String(formData.get("provincia_id") ?? ""),
    departamento_id: String(formData.get("departamento_id") ?? ""),
    localidad_id: String(formData.get("localidad_id") ?? ""),
    calle_y_numero: _calleYNumero(formData),
    pisos: _entero(formData.get("pisos")),
    subsuelos: _entero(formData.get("subsuelos")),
  });

  if (resultado.estado === "ok") {
    redirect(`/edificios/${resultado.datos.id}`);
  }
  if (resultado.estado === "conflicto") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No pudimos crear el edificio. Probá de nuevo."],
    };
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

export async function editarEdificioAction(
  complejoId: string,
  _estadoPrevio: EstadoEdicionEdificio,
  formData: FormData,
): Promise<EstadoEdicionEdificio> {
  const resultado = await editarEdificio(complejoId, {
    nombre: String(formData.get("nombre") ?? ""),
    provincia_id: String(formData.get("provincia_id") ?? ""),
    departamento_id: String(formData.get("departamento_id") ?? ""),
    localidad_id: String(formData.get("localidad_id") ?? ""),
    calle_y_numero: _calleYNumero(formData) ?? undefined,
    pisos: _entero(formData.get("pisos")),
    subsuelos: _entero(formData.get("subsuelos")),
  });

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    revalidatePath(`/edificios/${complejoId}/resumen`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "conflicto") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No pudimos guardar los cambios. Probá de nuevo."],
    };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores, _CAMPOS_CONOCIDOS);
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés editar este edificio."],
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
