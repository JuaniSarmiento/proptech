"use server";

/**
 * Registrar un cargo cobrado de menos (change 7, H-017, sobre el `POST` de H-014): la server action
 * recibe el formulario del diálogo, valida lo que se puede validar sin la API y se lo pasa a ella; el
 * navegador nunca habla con la API ni ve el token (D-036). Se liga al `complejoId` con `.bind` desde
 * `page.tsx`; la unidad y la obligación de origen viajan en el formulario.
 *
 * El importe se escribe con coma decimal (`1500,00`) y viaja con punto (`1500.00`); la API sigue
 * validando (un 422 vuelve al campo que nombra). Un 409 o cualquier otro error se dice con un mensaje
 * propio, nunca con el texto de la API (L-007).
 */

import { revalidatePath } from "next/cache";
import { registrarCargoCobradoDeMenos } from "../../../../../lib/api/liquidaciones";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import { decimalParaApi } from "../../../../../lib/formato";
import {
  CONCEPTOS_DEL_CARGO,
  importeParaApi,
  MENSAJES_DEL_CARGO,
  MOTIVO_DEL_CARGO_MAXIMO,
} from "./cargo";
import type { EstadoDelCargo } from "./Pantalla";

const _CONFLICTOS: Record<string, string> = {
  operacion_id: "Este pedido ya se registró con otros datos. Volvé a cargar la pantalla.",
};

function fallo(error: string): EstadoDelCargo {
  return { error };
}

export async function cargoCobradoDeMenosAction(
  complejoId: string,
  _estadoPrevio: EstadoDelCargo,
  formData: FormData,
): Promise<EstadoDelCargo> {
  const operacionId = String(formData.get("operacion_id") ?? "");
  const unidadId = String(formData.get("unidad_id") ?? "");
  const origenId = String(formData.get("obligacion_origen_id") ?? "");
  if (operacionId === "" || unidadId === "" || origenId === "") {
    return fallo("No pudimos leer el pedido. Probá de nuevo.");
  }

  const importe = importeParaApi(decimalParaApi(String(formData.get("importe") ?? "").trim()));
  const componente = String(formData.get("componente") ?? "");
  const motivo = String(formData.get("motivo") ?? "").trim();

  const erroresPorCampo: Record<string, string> = {};
  if (importe === null) erroresPorCampo.importe = MENSAJES_DEL_CARGO.importe;
  if (!CONCEPTOS_DEL_CARGO.some((c) => c.valor === componente)) {
    erroresPorCampo.componente = MENSAJES_DEL_CARGO.componente;
  }
  if (motivo === "" || motivo.length > MOTIVO_DEL_CARGO_MAXIMO) {
    erroresPorCampo.motivo = MENSAJES_DEL_CARGO.motivo;
  }
  if (importe === null || Object.keys(erroresPorCampo).length > 0) {
    return { erroresPorCampo };
  }

  const resultado = await registrarCargoCobradoDeMenos(complejoId, unidadId, {
    operacion_id: operacionId,
    obligacion_origen_id: origenId,
    importe,
    componente,
    motivo,
  });

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/liquidaciones`);
    return { hecho: { importe: resultado.datos.importe, motivo: resultado.datos.motivo } };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés registrar cargos en este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(_CONFLICTOS[resultado.campo] ?? "No pudimos registrar el cargo. Probá de nuevo.");
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Esta unidad o su obligación ya no existe, o no tenés acceso.");
  }
  if (resultado.estado === "invalido") {
    const porCampo: Record<string, string> = {};
    for (const error of resultado.errores) {
      const mensaje = (MENSAJES_DEL_CARGO as Record<string, string | undefined>)[error.campo];
      if (mensaje) porCampo[error.campo] = mensaje;
    }
    return Object.keys(porCampo).length > 0
      ? { erroresPorCampo: porCampo }
      : fallo("No pudimos registrar el cargo. Revisá los datos y probá de nuevo.");
  }
  return fallo("No pudimos registrar el cargo. Probá de nuevo.");
}
