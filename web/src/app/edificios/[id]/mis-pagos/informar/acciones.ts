"use server";

/**
 * Informar un pago (change 8, H-025): las server actions suben el comprobante para su lectura y mandan
 * el pago. El navegador nunca habla con la API ni ve el token de sesión (D-036); se ligan al edificio con
 * `.bind` desde `page.tsx`. La pantalla no suma ni redondea ningún monto: lo que se manda es lo que la
 * persona escribió (sólo cambia la coma decimal por el punto) y si las partes no suman, lo dice la API.
 *
 * Un fallo se dice con un mensaje propio, traducido de su código; el texto de la API nunca llega a la
 * pantalla (L-007).
 */

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import {
  informarPago,
  type PropuestaDeLectura,
  subirComprobante,
} from "../../../../../lib/api/pagos";
import { decimalParaApi } from "../../../../../lib/formato";

export type ResultadoDeLectura =
  | { comprobanteId: string; lectura: "ok" | "fallida" | "sin_ia"; propuesta: PropuestaDeLectura }
  | { error: string };

export async function leerComprobanteAction(
  complejoId: string,
  formData: FormData,
): Promise<ResultadoDeLectura> {
  const archivo = formData.get("archivo");
  if (!(archivo instanceof File) || archivo.size === 0) {
    return { error: "Elegí el archivo del comprobante." };
  }
  const resultado = await subirComprobante(complejoId, archivo);
  if (resultado.estado === "ok") {
    return {
      comprobanteId: resultado.datos.comprobante_id,
      lectura: resultado.datos.lectura,
      propuesta: resultado.datos.propuesta,
    };
  }
  if (resultado.estado === "invalido") {
    return {
      error: "Subí una foto o un PDF del comprobante (JPG, PNG o PDF, de hasta 10 MB).",
    };
  }
  if (resultado.estado === "sin_permiso")
    return { error: "No podés informar pagos en este edificio." };
  if (resultado.estado === "sin_sesion") return { error: MENSAJE_SIN_SESION };
  if (resultado.estado === "no_existe") {
    return { error: "Este edificio ya no existe o no tenés acceso." };
  }
  return { error: "No pudimos subir el comprobante. Probá de nuevo." };
}

/** Lo que escribió la persona, tal cual: las partes son las unidades con importe. */
export type DatosDelPago = {
  comprobanteId: string;
  banco: string;
  numeroDeOperacion: string;
  fechaDeTransferencia: string;
  monto: string;
  cbuDeOrigen: string;
  partes: { unidadId: string; importe: string }[];
};

/** Un error por campo (con el nombre del campo de la pantalla) o sueltos, ya dichos para la pantalla. */
export type ResultadoDelEnvio = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
};

const _CAMPOS: Record<string, string> = {
  monto: "Escribí el monto con dos decimales, por ejemplo 43350,00.",
  fecha_de_transferencia:
    "Elegí la fecha de la transferencia: tiene que ser de los últimos 12 meses y no futura.",
  banco: "Escribí el banco (hasta 100 caracteres).",
  numero_de_operacion: "Escribí el número de operación (hasta 100 caracteres).",
  cbu_origen: "El CBU tiene 22 números.",
};

const _PARTES =
  "Las partes tienen que sumar el monto del pago, y cada unidad puede figurar una sola vez.";

function falla(
  erroresPorCampo: Record<string, string>,
  erroresDesconocidos: string[] = [],
): ResultadoDelEnvio {
  return { erroresPorCampo, erroresDesconocidos };
}

export async function enviarPagoAction(
  complejoId: string,
  datos: DatosDelPago,
): Promise<ResultadoDelEnvio> {
  const partes = datos.partes
    .map((parte) => ({ unidad_id: parte.unidadId, importe: decimalParaApi(parte.importe.trim()) }))
    .filter((parte) => parte.importe !== "");
  if (partes.length === 0) {
    return falla({}, ["Escribí el importe de al menos una unidad."]);
  }
  const cbu = datos.cbuDeOrigen.trim();

  const resultado = await informarPago(complejoId, {
    comprobante_id: datos.comprobanteId,
    banco: datos.banco.trim(),
    numero_de_operacion: datos.numeroDeOperacion.trim(),
    fecha_de_transferencia: datos.fechaDeTransferencia,
    monto: decimalParaApi(datos.monto.trim()),
    ...(cbu === "" ? {} : { cbu_origen: cbu }),
    partes,
  });

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}`);
    redirect(`/edificios/${complejoId}/mis-pagos`);
  }
  if (resultado.estado === "invalido") {
    const porCampo: Record<string, string> = {};
    const sueltos: string[] = [];
    for (const { campo } of resultado.errores) {
      if (campo === "partes") sueltos.push(_PARTES);
      else if (campo === "comprobante_id") {
        sueltos.push("El comprobante ya no se puede usar. Subilo de nuevo.");
      } else if (_CAMPOS[campo]) porCampo[campo] = _CAMPOS[campo];
      else sueltos.push("No pudimos leer el pedido. Revisá los datos.");
    }
    return falla(porCampo, sueltos);
  }
  if (resultado.estado === "conflicto") {
    return resultado.campo === "numero_de_operacion"
      ? falla({ numero_de_operacion: "Ese número de operación ya se informó." })
      : falla({}, ["No pudimos registrar el pago. Volvé a cargar la pantalla."]);
  }
  if (resultado.estado === "sin_permiso") {
    return falla({}, ["No podés informar pagos en este edificio."]);
  }
  if (resultado.estado === "sin_sesion") return falla({}, [MENSAJE_SIN_SESION]);
  if (resultado.estado === "no_existe") {
    return falla({}, ["Una de las unidades ya no existe o no tenés acceso."]);
  }
  return falla({}, ["No pudimos enviar el pago. Probá de nuevo."]);
}
