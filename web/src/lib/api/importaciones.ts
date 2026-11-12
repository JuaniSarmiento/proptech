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
