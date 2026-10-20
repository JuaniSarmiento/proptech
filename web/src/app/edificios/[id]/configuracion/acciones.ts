"use server";

/**
 * Alta de una versión de configuración (D1, tarea 4.6): la server action se
 * liga al `complejoId` con `.bind` desde `page.tsx`. "Rige desde" lo valida
 * la API (422 en `vigente_desde`, D-ficha 4.6): esta acción nunca calcula
 * "hoy", sólo reenvía lo que mandó el formulario y traduce la respuesta.
 * Los campos numéricos que NO son plata (`dias_de_gracia`,
 * `dia_de_vencimiento`, `dia_segundo_vencimiento`) se convierten con el
 * parser entero de `Number` (D6 sólo prohíbe construir un `Number` o un
 * `parseFloat` directo, o un formateador de `Intl`, sobre texto decimal;
 * estos tres son enteros simples, no plata, y la API los exige como `int`
 * real, no como texto).
 */

import { revalidatePath } from "next/cache";
import type { ErrorDeCampo, ResultadoApi } from "../../../../lib/api/cliente";
import { crearVersionDeConfiguracion } from "../../../../lib/api/configuracion";
import { erroresDeFormulario } from "../../../../lib/api/mensajes";
import type { EstadoFormularioVersion } from "./Pantalla";

const _CAMPOS_CONOCIDOS = [
  "tasa_mensual",
  "dias_de_gracia",
  "forma_de_calculo",
  "porcentaje_fondo",
  "dia_de_vencimiento",
  "modalidad_de_vencimiento",
  "dia_segundo_vencimiento",
  "recargo_segundo_vencimiento",
  "vigente_desde",
];

function _enteroONulo(valor: FormDataEntryValue | null): number | null {
  const texto = String(valor ?? "").trim();
  return texto === "" ? null : Number.parseInt(texto, 10);
}

function _textoONulo(valor: FormDataEntryValue | null): string | null {
  const texto = String(valor ?? "").trim();
  return texto === "" ? null : texto;
}

export async function crearVersionDeConfiguracionAction(
  complejoId: string,
  _estadoPrevio: EstadoFormularioVersion,
  formData: FormData,
): Promise<EstadoFormularioVersion> {
  const modalidad = String(formData.get("modalidad_de_vencimiento") ?? "unico");
  const resultado: ResultadoApi<unknown> = await crearVersionDeConfiguracion(complejoId, {
    tasa_mensual: String(formData.get("tasa_mensual") ?? ""),
    dias_de_gracia: Number.parseInt(String(formData.get("dias_de_gracia") ?? "0"), 10),
    forma_de_calculo: String(formData.get("forma_de_calculo") ?? ""),
    porcentaje_fondo: String(formData.get("porcentaje_fondo") ?? ""),
    dia_de_vencimiento: Number.parseInt(String(formData.get("dia_de_vencimiento") ?? "0"), 10),
    modalidad_de_vencimiento: modalidad,
    dia_segundo_vencimiento:
      modalidad === "doble" ? _enteroONulo(formData.get("dia_segundo_vencimiento")) : null,
    recargo_segundo_vencimiento:
      modalidad === "doble" ? _textoONulo(formData.get("recargo_segundo_vencimiento")) : null,
    vigente_desde: String(formData.get("vigente_desde") ?? ""),
  });

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/configuracion`);
    return { erroresPorCampo: {}, erroresDesconocidos: [], ok: true };
  }
  if (resultado.estado === "invalido") {
    return erroresDeFormulario(resultado.errores as ErrorDeCampo[], _CAMPOS_CONOCIDOS);
  }
  if (resultado.estado === "sin_permiso") {
    return {
      erroresPorCampo: {},
      erroresDesconocidos: ["No podés cambiar la configuración de intereses y vencimiento."],
    };
  }
  return {
    erroresPorCampo: {},
    erroresDesconocidos: ["No pudimos guardar los datos. Probá de nuevo."],
  };
}
