"use server";

/**
 * Ajustar el saldo inicial de una unidad (change 5, H-010): la server action recibe el formulario
 * de la confirmación (importe, concepto, motivo y la operación que eligió la pantalla), valida lo
 * que se puede validar sin la API y se lo pasa a ella; el navegador nunca habla con la API ni ve el
 * token (D-036). Se liga al `complejoId` y a la `unidadId` con `.bind` desde `page.tsx`.
 *
 * El importe se escribe con coma decimal (`5000,00`) y viaja con punto y dos decimales; la API
 * sigue validando escala y rango (un 422 vuelve al campo que nombra).
 */

import { revalidatePath } from "next/cache";
import { ajustarSaldoInicial } from "../../../../../../lib/api/importaciones";
import { MENSAJE_SIN_SESION } from "../../../../../../lib/api/mensajes";
import { decimalParaApi } from "../../../../../../lib/formato";
import type { EstadoAjuste } from "./Pantalla";
import { CONCEPTOS, importeParaApi, MENSAJES_DE_CAMPO, MOTIVO_MAXIMO } from "./validacion";

const _CONFLICTOS: Record<string, string> = {
  estado_migracion: "Los saldos iniciales de este edificio todavía no están confirmados.",
  operacion_id: "Este pedido ya se registró con otros datos. Volvé a cargar la pantalla.",
};

function fallo(error: string): EstadoAjuste {
  return { error };
}

export async function ajustarSaldoInicialAction(
  complejoId: string,
  unidadId: string,
  _estadoPrevio: EstadoAjuste,
  formData: FormData,
): Promise<EstadoAjuste> {
  const operacionId = String(formData.get("operacion_id") ?? "");
  if (operacionId === "") {
    return fallo("No pudimos leer el pedido. Probá de nuevo.");
  }

  const importe = importeParaApi(decimalParaApi(String(formData.get("importe") ?? "").trim()));
  const componente = String(formData.get("componente") ?? "");
  const motivo = String(formData.get("motivo") ?? "").trim();

  const erroresPorCampo: Record<string, string> = {};
  if (importe === null) erroresPorCampo.importe = MENSAJES_DE_CAMPO.importe;
  if (motivo === "" || motivo.length > MOTIVO_MAXIMO)
    erroresPorCampo.motivo = MENSAJES_DE_CAMPO.motivo;
  if (!CONCEPTOS.includes(componente)) erroresPorCampo.componente = MENSAJES_DE_CAMPO.componente;
  if (importe === null || Object.keys(erroresPorCampo).length > 0) {
    return { erroresPorCampo };
  }

  const resultado = await ajustarSaldoInicial(complejoId, unidadId, {
    operacion_id: operacionId,
    importe,
    componente,
    motivo,
  });

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/unidades`);
    return { ajustado: resultado.datos };
  }
  if (resultado.estado === "sin_permiso") {
    return fallo("No podés ajustar saldos en este edificio.");
  }
  if (resultado.estado === "conflicto") {
    return fallo(_CONFLICTOS[resultado.campo] ?? "No pudimos registrar el ajuste. Probá de nuevo.");
  }
  if (resultado.estado === "sin_sesion") {
    return fallo(MENSAJE_SIN_SESION);
  }
  if (resultado.estado === "no_existe") {
    return fallo("Esta unidad ya no existe o no tenés acceso.");
  }
  if (resultado.estado === "invalido") {
    const porCampo: Record<string, string> = {};
    for (const error of resultado.errores) {
      const mensaje = MENSAJES_DE_CAMPO[error.campo];
      if (mensaje) porCampo[error.campo] = mensaje;
    }
    return Object.keys(porCampo).length > 0
      ? { erroresPorCampo: porCampo }
      : fallo("No pudimos registrar el ajuste. Revisá los datos y probá de nuevo.");
  }
  return fallo("No pudimos registrar el ajuste. Probá de nuevo.");
}
