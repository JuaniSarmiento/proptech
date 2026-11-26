"use server";

/**
 * Registrar el cobro a un vendedor (change 4d, H-034, H-033): la server action recibe el importe (con coma
 * decimal) y la fecha de la transferencia, y se los pasa a la API; el navegador nunca habla con ella ni ve
 * el token (D-036). Se liga al edificio y a la cuenta con `.bind` desde `page.tsx`. Devuelve el detalle que
 * contesta la API: la deuda nueva no la calcula la pantalla (R07).
 */

import { revalidatePath } from "next/cache";
import { MENSAJE_SIN_SESION } from "../../../../../lib/api/mensajes";
import { type DetalleDeCuenta, registrarCobroDeVendedor } from "../../../../../lib/api/titularidad";
import { importeParaApi, MENSAJES_DE_CAMPO, validarCobro } from "./validacion";

export type EstadoDelCobro = {
  error?: string;
  erroresPorCampo?: Record<string, string>;
  cuenta?: DetalleDeCuenta;
} | null;

export async function registrarCobroAction(
  complejoId: string,
  cuentaId: string,
  _estadoPrevio: EstadoDelCobro,
  formData: FormData,
): Promise<EstadoDelCobro> {
  const importeTexto = String(formData.get("importe") ?? "");
  const fecha = String(formData.get("fecha") ?? "");
  const locales = validarCobro(importeTexto, fecha);
  const importe = importeParaApi(importeTexto);
  if (importe === null || Object.keys(locales).length > 0) {
    return { erroresPorCampo: locales };
  }

  const resultado = await registrarCobroDeVendedor(complejoId, cuentaId, { importe, fecha });

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/cuentas-de-vendedores`);
    revalidatePath(`/edificios/${complejoId}/cuentas-de-vendedores/${cuentaId}`);
    return { cuenta: resultado.datos };
  }
  if (resultado.estado === "sin_permiso") {
    return { error: "No podés registrar cobros en este edificio." };
  }
  if (resultado.estado === "sin_sesion") {
    return { error: MENSAJE_SIN_SESION };
  }
  if (resultado.estado === "no_existe") {
    return { error: "Esta cuenta ya no existe o no tenés acceso." };
  }
  if (resultado.estado === "invalido") {
    const porCampo: Record<string, string> = {};
    for (const error of resultado.errores) {
      const mensaje = MENSAJES_DE_CAMPO[error.campo];
      if (mensaje) porCampo[error.campo] = mensaje;
    }
    return Object.keys(porCampo).length > 0
      ? { erroresPorCampo: porCampo }
      : { error: "No pudimos registrar el cobro. Revisá los datos y probá de nuevo." };
  }
  return { error: "No pudimos registrar el cobro. Probá de nuevo." };
}
