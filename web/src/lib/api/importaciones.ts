/**
 * Importar el padrón desde Excel (change 5, H-007): subir el archivo y bajar la plantilla. Los dos
 * pedidos salen del servidor de Next (D-036): el navegador nunca ve el token.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

/** Una advertencia de la importación: dice qué quedó cargado igual pero conviene mirar. */
export type AdvertenciaDeImportacion = {
  hoja: string | null;
  fila: number | null;
  columna: string | null;
  motivo: string;
};

export type ImportacionAceptada = {
  importacion_id: string;
  unidades_creadas: number;
  propietarios_creados: number;
  propietarios_reusados: number;
  filas_de_saldo: number;
  advertencias: AdvertenciaDeImportacion[];
};

/** Sólo `archivo` y `fecha_de_migracion` viajan a la API (nunca otro campo del formulario). */
export async function importarPadron(
  id: string,
  archivo: File,
  fechaDeMigracion: string,
): Promise<ResultadoApi<ImportacionAceptada>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo, archivo.name);
  cuerpo.append("fecha_de_migracion", fechaDeMigracion);
  return pedirApi<ImportacionAceptada>(`/api/complejos/${encodeURIComponent(id)}/importaciones`, {
    metodo: "POST",
    cuerpoMultipart: cuerpo,
  });
}

export async function plantillaDelPadron(id: string): Promise<ResultadoApi<ArrayBuffer>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<ArrayBuffer>(`/api/complejos/${encodeURIComponent(id)}/importaciones/plantilla`, {
    respuestaBinaria: true,
    alNoAutenticar: "devolver",
  });
}

export type UnidadComparada = {
  unidad: string;
  unidad_id: string;
  borrador: string;
  control: string;
  diferencia: string;
  aviso: string | null;
};

export type DiferenciaAceptada = {
  unidad: string;
  borrador: string;
  control: string;
  diferencia: string;
};

export type AceptacionDeDiferencias = {
  aceptacion_id: string;
  diferencias: DiferenciaAceptada[];
  aceptada_por: string;
  aceptada_en: string;
};

export type ComparacionDelBorrador = {
  importacion_id: string;
  unidades: UnidadComparada[];
  total_borrador: string;
  total_control: string;
  unidades_con_diferencia: number;
  requiere_aceptacion: boolean;
  aceptacion: AceptacionDeDiferencias | null;
};

const _MONTO = /^-?[0-9]+\.[0-9]{2}$/;

function esMonto(valor: unknown): boolean {
  return typeof valor === "string" && _MONTO.test(valor);
}

/** La comparación del borrador vigente (D6): los montos son texto con dos decimales; si alguno
 * no lo es, el resultado es `fallo` en vez de un `ok` que la pantalla no sabría mostrar. Un 404 es
 * "no hay borrador" (o el edificio no existe: la pantalla lo distingue con el edificio). */
export async function comparacionDelBorrador(
  id: string,
): Promise<ResultadoApi<ComparacionDelBorrador>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<ComparacionDelBorrador>(
    `/api/complejos/${encodeURIComponent(id)}/importaciones/comparacion`,
    { camposDePlata: ["total_borrador", "total_control"] },
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  const { unidades } = resultado.datos;
  const bien =
    Array.isArray(unidades) &&
    unidades.every((u) => esMonto(u.borrador) && esMonto(u.control) && esMonto(u.diferencia)) &&
    esMonto(resultado.datos.total_borrador) &&
    esMonto(resultado.datos.total_control);
  return bien ? resultado : { estado: "fallo" };
}

/** Sólo `importacion_id` viaja a la API. Un id que no es UUID es "no existe", sin pedido. */
export async function aceptarDiferencias(
  id: string,
  importacionId: string,
): Promise<ResultadoApi<AceptacionDeDiferencias>> {
  if (!esIdValido(id) || !esIdValido(importacionId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<AceptacionDeDiferencias>(
    `/api/complejos/${encodeURIComponent(id)}/importaciones/aceptacion-de-diferencias`,
    { metodo: "POST", cuerpo: { importacion_id: importacionId } },
  );
}
