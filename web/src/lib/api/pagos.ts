/**
 * Los pagos informados (change 8, H-025): subir el comprobante, informar, listar y resolver (confirmar,
 * rechazar, revertir, reimputar), más el enlace firmado del comprobante. Los pedidos salen del servidor
 * de Next (D-036): el navegador nunca habla con la API ni ve el token de sesión. La pantalla no calcula
 * ni redondea ningún monto: manda lo que el usuario escribió y muestra lo que la API contesta (R07).
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type EstadoDelPago = "informado" | "confirmado" | "rechazado" | "revertido";

export type ParteDelPago = { unidad_id: string; identificador: string; importe: string };

export type PagoInformado = {
  pago_id: string;
  estado: EstadoDelPago;
  motivo: string | null;
  banco: string;
  numero_de_operacion: string;
  fecha_de_transferencia: string;
  monto: string;
  partes: ParteDelPago[];
};

export type UnidadParaInformar = { unidad_id: string; identificador: string };

/** Lo que la IA leyó del comprobante: cada dato puede venir vacío. */
export type PropuestaDeLectura = {
  banco: string | null;
  numero_de_operacion: string | null;
  fecha: string | null;
  monto: string | null;
  cbu_origen: string | null;
};

export type ComprobanteLeido = {
  comprobante_id: string;
  lectura: "ok" | "fallida" | "sin_ia";
  propuesta: PropuestaDeLectura;
};

export type PedidoDePago = {
  comprobante_id: string;
  banco: string;
  numero_de_operacion: string;
  fecha_de_transferencia: string;
  monto: string;
  cbu_origen?: string;
  partes: { unidad_id: string; importe: string }[];
};

const _ESTADOS = new Set<string>(["informado", "confirmado", "rechazado", "revertido"]);
const _LECTURAS = new Set<string>(["ok", "fallida", "sin_ia"]);

/** La forma exacta de un token firmado: dos tramos de caracteres seguros para una dirección. Nada
 * más pasa a la API ni a la ruta de descarga (nunca se interpola un texto cualquiera). */
const _TOKEN = /^[A-Za-z0-9_-]{1,800}\.[0-9a-f]{64}$/;

function esRegistro(valor: unknown): valor is Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor);
}

function esParte(valor: unknown): valor is ParteDelPago {
  return (
    esRegistro(valor) &&
    typeof valor.unidad_id === "string" &&
    typeof valor.identificador === "string" &&
    typeof valor.importe === "string"
  );
}

function esPago(valor: unknown): valor is PagoInformado {
  return (
    esRegistro(valor) &&
    typeof valor.pago_id === "string" &&
    esIdValido(valor.pago_id) &&
    typeof valor.estado === "string" &&
    _ESTADOS.has(valor.estado) &&
    (valor.motivo === null || typeof valor.motivo === "string") &&
    typeof valor.banco === "string" &&
    typeof valor.numero_de_operacion === "string" &&
    typeof valor.fecha_de_transferencia === "string" &&
    typeof valor.monto === "string" &&
    Array.isArray(valor.partes) &&
    valor.partes.every(esParte)
  );
}

function esUnidad(valor: unknown): valor is UnidadParaInformar {
  return (
    esRegistro(valor) &&
    typeof valor.unidad_id === "string" &&
    esIdValido(valor.unidad_id) &&
    typeof valor.identificador === "string"
  );
}

function textoOVacio(valor: unknown): string | null {
  return typeof valor === "string" ? valor : null;
}

/** Los pagos que la persona puede ver: todos los del edificio si es personal, los suyos si es vecina. */
export async function pagosDelEdificio(id: string): Promise<ResultadoApi<PagoInformado[]>> {
  if (!esIdValido(id)) return { estado: "no_existe" };
  const resultado = await pedirApi<PagoInformado[]>(
    `/api/complejos/${encodeURIComponent(id)}/pagos`,
  );
  if (resultado.estado !== "ok") return resultado;
  return Array.isArray(resultado.datos) && resultado.datos.every(esPago)
    ? resultado
    : { estado: "fallo" };
}

/** Las unidades por las que la persona puede informar un pago (sus unidades, o todas si es personal). */
export async function unidadesParaInformar(
  id: string,
): Promise<ResultadoApi<UnidadParaInformar[]>> {
  if (!esIdValido(id)) return { estado: "no_existe" };
  const resultado = await pedirApi<UnidadParaInformar[]>(
    `/api/complejos/${encodeURIComponent(id)}/pagos/unidades`,
  );
  if (resultado.estado !== "ok") return resultado;
  return Array.isArray(resultado.datos) && resultado.datos.every(esUnidad)
    ? resultado
    : { estado: "fallo" };
}

/** Sube el comprobante y pide su lectura. Un archivo que no es JPEG, PNG o PDF, o que pasa de 10 MB,
 * llega como `invalido` (campo `archivo`). */
export async function subirComprobante(
  id: string,
  archivo: File,
): Promise<ResultadoApi<ComprobanteLeido>> {
  if (!esIdValido(id)) return { estado: "no_existe" };
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo, archivo.name);
  const resultado = await pedirApi<ComprobanteLeido>(
    `/api/complejos/${encodeURIComponent(id)}/pagos/lectura`,
    { metodo: "POST", cuerpoMultipart: cuerpo },
  );
  if (resultado.estado !== "ok") return resultado;
  const d: unknown = resultado.datos;
  if (
    !esRegistro(d) ||
    typeof d.comprobante_id !== "string" ||
    !esIdValido(d.comprobante_id) ||
    typeof d.lectura !== "string" ||
    !_LECTURAS.has(d.lectura) ||
    !esRegistro(d.propuesta)
  ) {
    return { estado: "fallo" };
  }
  return {
    estado: "ok",
    datos: {
      comprobante_id: d.comprobante_id,
      lectura: d.lectura as ComprobanteLeido["lectura"],
      propuesta: {
        banco: textoOVacio(d.propuesta.banco),
        numero_de_operacion: textoOVacio(d.propuesta.numero_de_operacion),
        fecha: textoOVacio(d.propuesta.fecha),
        monto: textoOVacio(d.propuesta.monto),
        cbu_origen: textoOVacio(d.propuesta.cbu_origen),
      },
    },
  };
}

/** Informa el pago con lo que hay en pantalla. Un 422 trae el `campo` (por ejemplo `partes`); un 409
 * `numero_de_operacion` / `repetido`, que ese número ya se informó. */
export async function informarPago(
  id: string,
  pedido: PedidoDePago,
): Promise<ResultadoApi<{ pago_id: string; estado: string }>> {
  if (!esIdValido(id)) return { estado: "no_existe" };
  return pedirApi(`/api/complejos/${encodeURIComponent(id)}/pagos`, {
    metodo: "POST",
    cuerpo: pedido,
  });
}

export type AccionSobreUnPago = "confirmacion" | "rechazo" | "reversion" | "reimputacion";

/** Confirma, rechaza, revierte o reimputa un pago. Un 409 (`pago` / `estado`) dice que el pago ya no
 * está en el estado que la pantalla creía. */
export async function resolverPago(
  id: string,
  pagoId: string,
  accion: AccionSobreUnPago,
  cuerpo?: Record<string, string>,
): Promise<ResultadoApi<{ pago_id: string; estado: string }>> {
  if (!esIdValido(id) || !esIdValido(pagoId)) return { estado: "no_existe" };
  return pedirApi(
    `/api/complejos/${encodeURIComponent(id)}/pagos/${encodeURIComponent(pagoId)}/${accion}`,
    { metodo: "POST", ...(cuerpo === undefined ? {} : { cuerpo }) },
  );
}

/** Pide el enlace firmado del comprobante de un pago. */
export async function enlaceDelComprobante(
  id: string,
  pagoId: string,
): Promise<ResultadoApi<{ url: string; vence_en: string }>> {
  if (!esIdValido(id) || !esIdValido(pagoId)) return { estado: "no_existe" };
  return pedirApi(
    `/api/complejos/${encodeURIComponent(id)}/pagos/${encodeURIComponent(pagoId)}/comprobante/enlace`,
    { metodo: "POST" },
  );
}

/** El token de un enlace `/api/comprobantes/descarga?token=...`, o `null` si la dirección no es la
 * esperada: la pantalla arma su propia ruta de descarga y no repite la de la API. */
export function tokenDelComprobante(url: string): string | null {
  const prefijo = "/api/comprobantes/descarga?token=";
  if (!url.startsWith(prefijo)) return null;
  const token = url.slice(prefijo.length);
  return _TOKEN.test(token) ? token : null;
}

export type DescargaDelComprobante =
  | { estado: "ok"; datos: ArrayBuffer; tipo: string }
  | { estado: "vencido" }
  | { estado: "invalido" }
  | { estado: "fallo" };

const _TIPOS_DE_COMPROBANTE = new Set(["image/jpeg", "image/png", "application/pdf"]);

/** Baja el comprobante con el token firmado. Sin sesión: el token es la autorización, así que no se
 * manda ninguna credencial. El tipo es uno de los tres que la API guarda; otro es `fallo`. */
export async function descargarComprobante(token: string): Promise<DescargaDelComprobante> {
  if (!_TOKEN.test(token)) return { estado: "invalido" };
  const base = process.env.PROPTECH_URL_API_INTERNA;
  if (!base) return { estado: "fallo" };
  let respuesta: Response;
  try {
    respuesta = await fetch(`${base}/api/comprobantes/descarga?token=${token}`, {
      cache: "no-store",
    });
  } catch {
    return { estado: "fallo" };
  }
  if (respuesta.status === 410) return { estado: "vencido" };
  if (respuesta.status === 403) return { estado: "invalido" };
  if (respuesta.status !== 200) return { estado: "fallo" };
  const tipo = (respuesta.headers.get("content-type") ?? "").split(";")[0]?.trim() ?? "";
  if (!_TIPOS_DE_COMPROBANTE.has(tipo)) return { estado: "fallo" };
  try {
    return { estado: "ok", datos: await respuesta.arrayBuffer(), tipo };
  } catch {
    return { estado: "fallo" };
  }
}
