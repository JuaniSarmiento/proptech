"use server";

/**
 * Importar el padrón desde Excel (change 5, H-007): la server action recibe el formulario, valida
 * lo mínimo y se lo pasa a la API; el navegador nunca habla con la API ni ve el token (D-036). La
 * acción se liga al `complejoId` con `.bind` desde `page.tsx`.
 */

import { revalidatePath } from "next/cache";
import type { ErrorDeArchivo } from "../../../../lib/api/cliente";
import { importarPadron } from "../../../../lib/api/importaciones";
import { MENSAJE_SIN_SESION } from "../../../../lib/api/mensajes";
import type { EstadoImportacion } from "./Pantalla";

const _VACIO = { erroresPorCampo: {}, erroresDesconocidos: [] };

function rechazado(erroresDesconocidos: string[]): EstadoImportacion {
  return { ..._VACIO, erroresDesconocidos };
}

export async function importarPadronAction(
  complejoId: string,
  _estadoPrevio: EstadoImportacion,
  formData: FormData,
): Promise<EstadoImportacion> {
  const archivo = formData.get("archivo");
  const fecha = formData.get("fecha_de_migracion");
  const erroresPorCampo: Record<string, string> = {};
  if (!(archivo instanceof File) || archivo.size === 0) {
    erroresPorCampo.archivo = "Elegí el archivo de Excel.";
  }
  if (typeof fecha !== "string" || fecha === "") {
    erroresPorCampo.fecha_de_migracion = "Elegí la fecha de migración.";
  }
  if (Object.keys(erroresPorCampo).length > 0 || !(archivo instanceof File)) {
    return { erroresPorCampo, erroresDesconocidos: [] };
  }

  const resultado = await importarPadron(complejoId, archivo, String(fecha));

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    revalidatePath(`/edificios/${complejoId}/unidades`);
    revalidatePath(`/edificios/${complejoId}/grupos`);
    return { ..._VACIO, aceptada: resultado.datos };
  }
  if (resultado.estado === "rechazado") {
    const errores: ErrorDeArchivo[] = resultado.errores;
    return { ..._VACIO, rechazo: errores };
  }
  if (resultado.estado === "invalido") {
    const fechaMala = resultado.errores.some((e) => e.campo === "fecha_de_migracion");
    return fechaMala
      ? {
          erroresPorCampo: {
            fecha_de_migracion:
              "Elegí una fecha de migración válida: no puede ser posterior a hoy.",
          },
          erroresDesconocidos: [],
        }
      : rechazado(["No pudimos leer el pedido. Probá de nuevo."]);
  }
  if (resultado.estado === "conflicto") {
    return rechazado([
      resultado.campo === "archivo"
        ? "Este archivo ya se importó en este edificio."
        : "Los saldos de este edificio ya están resueltos: no se puede importar de nuevo.",
    ]);
  }
  if (resultado.estado === "sin_permiso") {
    return rechazado(["No podés importar en este edificio."]);
  }
  if (resultado.estado === "sin_sesion") {
    return rechazado([MENSAJE_SIN_SESION]);
  }
  if (resultado.estado === "no_existe") {
    return rechazado(["Este edificio ya no existe o no tenés acceso."]);
  }
  return rechazado(["No pudimos importar el archivo. Probá de nuevo."]);
}
