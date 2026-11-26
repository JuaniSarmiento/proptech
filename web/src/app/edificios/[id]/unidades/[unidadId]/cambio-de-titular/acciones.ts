"use server";

/**
 * Registrar el cambio de titular de una unidad (change 4d, H-034): la server action recibe el borrador de
 * la pantalla, lo valida con lo mismo que el navegador y se lo pasa a la API; el navegador nunca habla con
 * ella ni ve el token (D-036). Se liga al edificio y a la unidad con `.bind` desde `page.tsx`. No calcula
 * nada: el aviso, lo trasladado y el prorrateo son los de la API.
 *
 * Un 422 de la API siempre dice "valor inválido": acá se traduce por campo (`loc`), nunca se muestra su
 * texto (L-007). `compradores.N.email` y compañía caen en el grupo "Compradores".
 */

import { revalidatePath } from "next/cache";
import { MENSAJE_SIN_SESION } from "../../../../../../lib/api/mensajes";
import {
  type CambioRegistrado,
  registrarCambioDeTitular,
} from "../../../../../../lib/api/titularidad";
import {
  type BorradorDeCambio,
  MENSAJES_DE_CAMPO,
  pedidoDelBorrador,
  validarBorrador,
} from "./validacion";

export type EstadoDelCambio = {
  error?: string;
  erroresPorCampo?: Record<string, string>;
  registrado?: CambioRegistrado;
} | null;

function esBorrador(valor: unknown): valor is BorradorDeCambio {
  if (valor === null || typeof valor !== "object") return false;
  const b = valor as Record<string, unknown>;
  return (
    typeof b.fecha === "string" &&
    Array.isArray(b.vendedores) &&
    b.vendedores.every((v) => typeof v === "string") &&
    Array.isArray(b.compradores) &&
    b.compradores.every(
      (c) =>
        c !== null &&
        typeof c === "object" &&
        typeof (c as { nombre?: unknown }).nombre === "string" &&
        typeof (c as { email?: unknown }).email === "string",
    ) &&
    (b.expensa === "entera" || b.expensa === "prorrateo") &&
    (b.deuda === "en_la_unidad" || b.deuda === "a_nombre_del_vendedor") &&
    typeof b.deudor === "string"
  );
}

export async function registrarCambioAction(
  complejoId: string,
  unidadId: string,
  _estadoPrevio: EstadoDelCambio,
  borrador: BorradorDeCambio,
): Promise<EstadoDelCambio> {
  if (!esBorrador(borrador)) {
    return { error: "No pudimos leer el pedido. Probá de nuevo." };
  }
  const locales = validarBorrador(borrador);
  if (Object.keys(locales).length > 0) {
    return { erroresPorCampo: locales };
  }

  const resultado = await registrarCambioDeTitular(
    complejoId,
    unidadId,
    pedidoDelBorrador(borrador),
  );

  if (resultado.estado === "ok") {
    revalidatePath(`/edificios/${complejoId}/unidades`);
    revalidatePath(`/edificios/${complejoId}/unidades/${unidadId}/cambio-de-titular`);
    revalidatePath(`/edificios/${complejoId}/cuentas-de-vendedores`);
    return { registrado: resultado.datos };
  }
  if (resultado.estado === "sin_permiso") {
    return { error: "No podés cambiar el titular de unidades de este edificio." };
  }
  if (resultado.estado === "sin_sesion") {
    return { error: MENSAJE_SIN_SESION };
  }
  if (resultado.estado === "no_existe") {
    return { error: "Esta unidad ya no existe o no tenés acceso." };
  }
  if (resultado.estado === "invalido") {
    const porCampo: Record<string, string> = {};
    for (const error of resultado.errores) {
      const campo = error.campo.split(".")[0] ?? "";
      const mensaje = MENSAJES_DE_CAMPO[campo];
      if (mensaje) porCampo[campo] = mensaje;
    }
    return Object.keys(porCampo).length > 0
      ? { erroresPorCampo: porCampo }
      : { error: "No pudimos registrar el cambio. Revisá los datos y probá de nuevo." };
  }
  return { error: "No pudimos registrar el cambio. Probá de nuevo." };
}
