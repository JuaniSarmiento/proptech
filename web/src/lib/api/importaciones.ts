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

/** Los totales del edificio que cargó la confirmación (montos como texto con dos decimales). */
export type TotalesDeLaConfirmacion = {
  capital: string;
  interes_importado: string;
  credito: string;
};

export type ConfirmacionDeSaldos = {
  importacion_id: string;
  carga_id: string;
  estado_migracion: string;
  totales: TotalesDeLaConfirmacion;
  confirmada_por: string;
  confirmada_en: string;
};

/** Sólo `importacion_id` viaja a la API. Los totales son texto con dos decimales: si alguno no lo
 * es, el resultado es `fallo` en vez de un `ok` que la pantalla no sabría mostrar. Un id que no es
 * UUID es "no existe", sin pedido. */
export async function confirmarSaldos(
  id: string,
  importacionId: string,
): Promise<ResultadoApi<ConfirmacionDeSaldos>> {
  if (!esIdValido(id) || !esIdValido(importacionId)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<ConfirmacionDeSaldos>(
    `/api/complejos/${encodeURIComponent(id)}/importaciones/confirmacion`,
    { metodo: "POST", cuerpo: { importacion_id: importacionId } },
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  const { totales } = resultado.datos;
  const bien =
    typeof totales === "object" &&
    totales !== null &&
    esMonto(totales.capital) &&
    esMonto(totales.interes_importado) &&
    esMonto(totales.credito);
  return bien ? resultado : { estado: "fallo" };
}

export type AjusteDeSaldoInicial = {
  ajuste_id: string;
  operacion_id: string;
  obligacion_id: string;
  cuenta_id: string;
  unidad_id: string;
  importe: string;
  componente: string;
  periodo: string;
  vencimiento: string;
  motivo: string;
  registrado_por: string;
  registrado_en: string;
};

export type PedidoDeAjuste = {
  operacion_id: string;
  importe: string;
  componente: string;
  motivo: string;
};

/** Sólo los cuatro campos del pedido viajan a la API. El importe del ajuste es texto con dos
 * decimales: si no lo es, el resultado es `fallo` en vez de un `ok` que la pantalla no sabría
 * mostrar. Un id que no es UUID es "no existe", sin pedido. */
export async function ajustarSaldoInicial(
  id: string,
  unidadId: string,
  pedido: PedidoDeAjuste,
): Promise<ResultadoApi<AjusteDeSaldoInicial>> {
  if (!esIdValido(id) || !esIdValido(unidadId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<AjusteDeSaldoInicial>(
    `/api/complejos/${encodeURIComponent(id)}/unidades/${encodeURIComponent(unidadId)}/ajustes-de-saldo-inicial`,
    {
      metodo: "POST",
      cuerpo: {
        operacion_id: pedido.operacion_id,
        importe: pedido.importe,
        componente: pedido.componente,
        motivo: pedido.motivo,
      },
      camposDePlata: ["importe"],
    },
  );
}
