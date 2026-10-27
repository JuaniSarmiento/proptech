"use server";

/**
 * Alta y edición de un grupo (D1, D9, tarea 4.4). El alta es un solo
 * pedido (nombre, método, modo y unidades juntos, D9); la edición son dos
 * pedidos — si el segundo (las unidades) falla después de que el primero
 * (nombre y método) ya se guardó, la acción lo dice tal cual, nunca lo
 * oculta: "se guardaron el nombre y el método; las unidades no".
 */

import { revalidatePath } from "next/cache";
import type { ErrorDeCampo, ResultadoApi } from "../../../../lib/api/cliente";
import {
  crearGrupo,
  editarGrupo,
  fijarMiembrosDeGrupo,
  type MiembroAEnviar,
} from "../../../../lib/api/grupos";
import { erroresDeFormulario, MENSAJE_SIN_SESION } from "../../../../lib/api/mensajes";
import { decimalParaApi } from "../../../../lib/formato";
import type { EstadoAccionDeLista, EstadoFormularioGrupo } from "./Pantalla";

const _CAMPOS_DATOS = ["clave", "nombre", "metodo"];

function _modo(formData: FormData): "renormalizado" | "propios" {
  return formData.get("modo_de_coeficientes") === "propios" ? "propios" : "renormalizado";
}

function _unidadesSeleccionadas(
  formData: FormData,
  idsDisponibles: string[],
  modo: "renormalizado" | "propios",
): MiembroAEnviar[] {
  const seleccion: MiembroAEnviar[] = [];
  for (const unidadId of idsDisponibles) {
    if (formData.get(`unidad_${unidadId}`) !== "on") {
      continue;
    }
    const coeficiente =
      modo === "propios"
        ? decimalParaApi(String(formData.get(`coeficiente_${unidadId}`) ?? ""))
        : null;
    seleccion.push({ unidad_id: unidadId, coeficiente });
  }
  return seleccion;
}

function _mapearErrorDeDatos(resultado: ResultadoApi<unknown>): EstadoFormularioGrupo {
  if (resultado.estado === "conflicto") {
    return {
      erroresPorCampo: { [resultado.campo]: "Ya existe un grupo con esta clave." },
      erroresDesconocidos: [],
    };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], _CAMPOS_DATOS);
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés modificar los grupos de reparto."],
    };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresPorCampo: {}, erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos guardar los datos. Probá de nuevo."],
  };
}

function _mapearErrorDeMiembros(resultado: ResultadoApi<unknown>): string[] {
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], []).erroresDesconocidos;
  }
  if (resultado.estado === "sin_sesion") {
    return [MENSAJE_SIN_SESION];
  }
  return ["No pudimos guardar las unidades. Probá de nuevo."];
}

export async function crearGrupoAction(
  complejoId: string,
  idsDisponibles: string[],
  _estadoPrevio: EstadoFormularioGrupo,
  formData: FormData,
): Promise<EstadoFormularioGrupo> {
  const modo = _modo(formData);
  const resultado = await crearGrupo(complejoId, {
    // D7 (tarea 4.4): sin campo "clave" en el formulario (6.3) — se
    // autogenera en el backend a partir del nombre.
    nombre: String(formData.get("nombre") ?? ""),
    metodo: String(formData.get("metodo") ?? ""),
    modo_de_coeficientes: modo,
    unidades: _unidadesSeleccionadas(formData, idsDisponibles, modo),
  });
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/grupos`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  return _mapearErrorDeDatos(resultado);
}

export async function editarGrupoAction(
  complejoId: string,
  idsDisponibles: string[],
  _estadoPrevio: EstadoFormularioGrupo,
  formData: FormData,
): Promise<EstadoFormularioGrupo> {
  const grupoId = String(formData.get("grupo_id") ?? "");
  const modo = _modo(formData);

  const primero = await editarGrupo(grupoId, {
    nombre: String(formData.get("nombre") ?? ""),
    metodo: String(formData.get("metodo") ?? ""),
  });
  if (primero.estado !== "ok") {
    return _mapearErrorDeDatos(primero);
  }
  revalidatePath(`/edificios/${complejoId}/grupos`);

  const segundo = await fijarMiembrosDeGrupo(grupoId, {
    modo_de_coeficientes: modo,
    unidades: _unidadesSeleccionadas(formData, idsDisponibles, modo),
  });
  if (segundo.estado !== "ok") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: [
        "Se guardaron el nombre y el método; las unidades no.",
        ..._mapearErrorDeMiembros(segundo),
      ],
    };
  }
  revalidatePath(`/edificios/${complejoId}/grupos`);
  return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
}

/**
 * 6.3: desactivar/reactivar un grupo parcial (nunca "Generales" — esta
 * pantalla ni siquiera muestra el botón para él, y la base lo rechaza por
 * SQL si algo se equivoca más abajo). Mismo patrón que
 * `cambiarEstadoCategoriaAction` de `categorias/acciones.ts`.
 */
export async function cambiarEstadoGrupoAction(
  complejoId: string,
  _estadoPrevio: EstadoAccionDeLista,
  formData: FormData,
): Promise<EstadoAccionDeLista> {
  const grupoId = String(formData.get("grupo_id") ?? "");
  const activo = formData.get("activo") === "true";
  const resultado = await editarGrupo(grupoId, { activo });
  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/grupos`);
    return { erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "sin_permiso") {
    return { erroresDesconocidos: ["No podés activar ni desactivar grupos."] };
  }
  if (resultado.estado === "sin_sesion") {
    return { erroresDesconocidos: [MENSAJE_SIN_SESION] };
  }
  if (resultado.estado === "invalido") {
    return {
      erroresDesconocidos: erroresDeFormulario(resultado.errores as ErrorDeCampo[], [])
        .erroresDesconocidos,
    };
  }
  return { erroresDesconocidos: ["No pudimos guardar el cambio. Probá de nuevo."] };
}
