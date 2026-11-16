/**
 * El PDF de la expensa (change 7, H-015): la lista de documentos de una liquidación emitida, el
 * reproceso, el enlace firmado y la descarga. El navegador nunca habla con la API ni ve el token de
 * sesión (D-036): lo hace el servidor de Next. El PDF no tiene dirección pública: se baja con un
 * enlace firmado que vence a los 15 minutos (D-070), y la descarga pasa por una ruta propia de la
 * web (`/documentos/descarga`) porque el borde (Caddy) no publica `/api/*`.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type VarianteDeDocumento = "completa" | "sin_extraordinaria";
export type EstadoDeDocumento = "pendiente" | "generado" | "fallido";

export type DocumentoDeExpensa = {
  documento_id: string;
  unidad_id: string;
  identificador: string;
  variante: VarianteDeDocumento;
  estado: EstadoDeDocumento;
  motivo: string | null;
};

const _VARIANTES = new Set<string>(["completa", "sin_extraordinaria"]);
const _ESTADOS = new Set<string>(["pendiente", "generado", "fallido"]);

/** La forma exacta de un token firmado: dos tramos de caracteres seguros para una dirección. Nada
 * más pasa a la API ni a la ruta de descarga (nunca se interpola un texto cualquiera). */
const _TOKEN = /^[A-Za-z0-9_-]{1,800}\.[0-9a-f]{64}$/;

function esDocumento(valor: unknown): valor is DocumentoDeExpensa {
  if (valor === null || typeof valor !== "object") return false;
  const d = valor as Record<string, unknown>;
  return (
    typeof d.documento_id === "string" &&
    esIdValido(d.documento_id) &&
    typeof d.identificador === "string" &&
    typeof d.variante === "string" &&
    _VARIANTES.has(d.variante) &&
    typeof d.estado === "string" &&
    _ESTADOS.has(d.estado) &&
    (d.motivo === null || typeof d.motivo === "string")
  );
}

/** Los documentos de la liquidación (uno por unidad y variante). Una respuesta con otra forma es
 * `fallo`, nunca un `ok` que la pantalla no sabría mostrar. */
export async function documentosDeLaLiquidacion(
  id: string,
  liquidacionId: string,
): Promise<ResultadoApi<DocumentoDeExpensa[]>> {
  if (!esIdValido(id) || !esIdValido(liquidacionId)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<DocumentoDeExpensa[]>(
    `/api/complejos/${encodeURIComponent(id)}/liquidaciones/${encodeURIComponent(liquidacionId)}/documentos`,
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  return Array.isArray(resultado.datos) && resultado.datos.every(esDocumento)
    ? resultado
    : { estado: "fallo" };
}

/** Pasa los fallidos a pendientes y encola todos los pendientes: 202 con cuántos. Un 503 (la cola no
 * contesta) llega como `fallo`. */
export async function reprocesarDocumentos(
  id: string,
  liquidacionId: string,
): Promise<ResultadoApi<{ encolados: number }>> {
  if (!esIdValido(id) || !esIdValido(liquidacionId)) {
    return { estado: "no_existe" };
  }
  return pedirApi(
    `/api/complejos/${encodeURIComponent(id)}/liquidaciones/${encodeURIComponent(liquidacionId)}/documentos/reproceso`,
    { metodo: "POST" },
  );
}

/** Pide el enlace firmado de un documento `generado`. Un 409 `no_generado` llega como conflicto. */
export async function enlaceDelDocumento(
  id: string,
  documentoId: string,
  variante: VarianteDeDocumento,
): Promise<ResultadoApi<{ url: string; vence_en: string }>> {
  if (!esIdValido(id) || !esIdValido(documentoId) || !_VARIANTES.has(variante)) {
    return { estado: "no_existe" };
  }
  return pedirApi(
    `/api/complejos/${encodeURIComponent(id)}/documentos/${encodeURIComponent(documentoId)}/enlace`,
    { metodo: "POST", cuerpo: { variante } },
  );
}

/** El token de un enlace `/api/documentos/descarga?token=...`, o `null` si la dirección no es la
 * esperada: la pantalla arma su propia ruta de descarga y no repite la de la API. */
export function tokenDelEnlace(url: string): string | null {
  const prefijo = "/api/documentos/descarga?token=";
  if (!url.startsWith(prefijo)) return null;
  const token = url.slice(prefijo.length);
  return _TOKEN.test(token) ? token : null;
}

export type DescargaDelDocumento =
  | { estado: "ok"; datos: ArrayBuffer; nombre: string }
  | { estado: "vencido" }
  | { estado: "invalido" }
  | { estado: "fallo" };

const _NOMBRE_DEL_PDF = /^attachment; filename="(expensa-[a-z0-9.-]+\.pdf)"$/;

/** Baja el PDF con el token firmado. Sin sesión: el token es la autorización (E13), así que no se
 * manda ninguna credencial. El nombre del archivo es el que decide la API (H-017: período, unidad y
 * variante); si no viene con esa forma, `expensa.pdf`. */
export async function descargarDocumento(token: string): Promise<DescargaDelDocumento> {
  if (!_TOKEN.test(token)) {
    return { estado: "invalido" };
  }
  const base = process.env.PROPTECH_URL_API_INTERNA;
  if (!base) {
    return { estado: "fallo" };
  }
  let respuesta: Response;
  try {
    respuesta = await fetch(`${base}/api/documentos/descarga?token=${token}`, {
      cache: "no-store",
    });
  } catch {
    return { estado: "fallo" };
  }
  if (respuesta.status === 410) return { estado: "vencido" };
  if (respuesta.status === 403) return { estado: "invalido" };
  if (respuesta.status !== 200) return { estado: "fallo" };
  try {
    const nombre = _NOMBRE_DEL_PDF.exec(respuesta.headers.get("content-disposition") ?? "")?.[1];
    return { estado: "ok", datos: await respuesta.arrayBuffer(), nombre: nombre ?? "expensa.pdf" };
  } catch {
    return { estado: "fallo" };
  }
}
