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
import { erroresDeFormulario } from "../../../../lib/api/mensajes";
import type { EstadoFormularioGrupo } from "./Pantalla";

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
      modo === "propios" ? String(formData.get(`coeficiente_${unidadId}`) ?? "") : null;
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
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos guardar los datos. Probá de nuevo."],
  };
}

function _mapearErrorDeMiembros(resultado: ResultadoApi<unknown>): string[] {
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], []).erroresDesconocidos;
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
    clave: String(formData.get("clave") ?? ""),
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
