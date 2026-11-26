/**
 * El portal del vecino (change 11, H-040): lo que la persona debe, sus liquidaciones, sus pagos
 * confirmados y sus PDFs, de TODAS sus unidades (`/api/mis-unidades...`, H-038 y H-039). Los pedidos
 * salen del servidor de Next (D-036): el navegador nunca habla con la API ni ve el token. La pantalla
 * no calcula ni redondea ningún monto (R05, R07): muestra lo que la API contesta; el total del
 * conjunto lo suma la API. Cada respuesta con otra forma es `fallo`, nunca un `ok` que la pantalla no
 * sabría mostrar; una unidad o liquidación ajena es 404 (`no_existe`), sin distinguir de la inexistente.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type VinculoDelVecino = "propietario" | "inquilino";

export type UnidadDelVecino = {
  unidad_id: string;
  identificador: string;
  vinculo: VinculoDelVecino;
  complejo_id: string;
  edificio: string;
  total_a_pagar: string;
  vencimiento: string | null;
  deuda_anterior: string;
  intereses: string;
  credito_aplicable: string;
  credito_retenido: string;
};

export type ConjuntoDelVecino = {
  total_a_pagar: string;
  intereses: string;
  credito_aplicable: string;
  credito_retenido: string;
};

export type MisUnidades = {
  fecha: string;
  conjunto: ConjuntoDelVecino;
  unidades: UnidadDelVecino[];
};

export type LiquidacionDeLaLista = {
  liquidacion_id: string;
  periodo: string;
  vencimiento: string;
  total: string;
};

export type CategoriaDeLaExpensa = {
  categoria_id: string;
  nombre: string;
  importe: string;
  porcentaje: string;
};

export type BloqueDeLaExpensa = { subtotal: string; categorias: CategoriaDeLaExpensa[] };

export type GrupoDeLaExpensa = {
  grupo_id: string;
  nombre: string;
  ordinaria: string;
  /** Sólo el propietario: la API no se la manda al inquilino (D-170.2). */
  extraordinaria?: string;
};

export type CategoriaComparada = {
  categoria_id: string;
  nombre: string;
  bloque: "ordinario" | "extraordinario";
  importe: string;
  importe_anterior: string;
  diferencia: string;
};

export type ComparacionDeLaExpensa = {
  liquidacion_id: string;
  periodo: string;
  total_anterior: string;
  diferencia_total: string;
  categorias: CategoriaComparada[];
};

export type ExpensaDeLaUnidad = {
  liquidacion_id: string;
  complejo_id: string;
  unidad_id: string;
  identificador: string;
  periodo: string;
  vencimiento: string;
  vinculo: VinculoDelVecino;
  bloques: { ordinario: BloqueDeLaExpensa; extraordinario?: BloqueDeLaExpensa };
  grupos: GrupoDeLaExpensa[];
  ordinaria: string;
  cargos_particulares: { concepto: string; importe: string }[];
  fondo_de_reserva: string;
  extraordinaria?: string;
  intereses: string;
  total: string;
  comparacion: ComparacionDeLaExpensa | null;
};

export type PagoConfirmadoDelVecino = {
  pago_id: string;
  fecha_de_transferencia: string;
  importe: string;
  banco: string;
  numero_de_operacion: string;
};

export type PdfDelVecino = {
  documento_id: string;
  liquidacion_id: string;
  complejo_id: string;
  periodo: string;
  variante: "completa" | "sin_extraordinaria";
  url: string;
  vence_en: string;
};

const _MONTO = /^-?[0-9]+\.[0-9]{2}$/;
const _FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
/** El enlace firmado del 7: la única forma que la pantalla acepta para armar el `href`. */
const _ENLACE = /^\/api\/documentos\/descarga\?token=([A-Za-z0-9_-]{1,800}\.[0-9a-f]{64})$/;

function esRegistro(valor: unknown): valor is Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor);
}

function esMonto(valor: unknown): valor is string {
  return typeof valor === "string" && _MONTO.test(valor);
}

function esTexto(valor: unknown): valor is string {
  return typeof valor === "string";
}

function esId(valor: unknown): valor is string {
  return typeof valor === "string" && esIdValido(valor);
}

function esFecha(valor: unknown): valor is string {
  return typeof valor === "string" && _FECHA.test(valor);
}

function esVinculo(valor: unknown): boolean {
  return valor === "propietario" || valor === "inquilino";
}

function esUnidad(valor: unknown): valor is UnidadDelVecino {
  return (
    esRegistro(valor) &&
    esId(valor.unidad_id) &&
    esTexto(valor.identificador) &&
    esVinculo(valor.vinculo) &&
    esId(valor.complejo_id) &&
    esTexto(valor.edificio) &&
    esMonto(valor.total_a_pagar) &&
    (valor.vencimiento === null || esFecha(valor.vencimiento)) &&
    esMonto(valor.deuda_anterior) &&
    esMonto(valor.intereses) &&
    esMonto(valor.credito_aplicable) &&
    esMonto(valor.credito_retenido)
  );
}

function esMisUnidades(valor: unknown): valor is MisUnidades {
  if (!esRegistro(valor) || !esFecha(valor.fecha)) return false;
  const c = valor.conjunto;
  return (
    esRegistro(c) &&
    esMonto(c.total_a_pagar) &&
    esMonto(c.intereses) &&
    esMonto(c.credito_aplicable) &&
    esMonto(c.credito_retenido) &&
    Array.isArray(valor.unidades) &&
    valor.unidades.every(esUnidad)
  );
}

function esLiquidacion(valor: unknown): valor is LiquidacionDeLaLista {
  return (
    esRegistro(valor) &&
    esId(valor.liquidacion_id) &&
    esFecha(valor.periodo) &&
    esFecha(valor.vencimiento) &&
    esMonto(valor.total)
  );
}

function esBloque(valor: unknown): valor is BloqueDeLaExpensa {
  return (
    esRegistro(valor) &&
    esMonto(valor.subtotal) &&
    Array.isArray(valor.categorias) &&
    valor.categorias.every(
      (c) =>
        esRegistro(c) &&
        esId(c.categoria_id) &&
        esTexto(c.nombre) &&
        esMonto(c.importe) &&
        esMonto(c.porcentaje),
    )
  );
}

function esGrupo(valor: unknown): valor is GrupoDeLaExpensa {
  return (
    esRegistro(valor) &&
    esId(valor.grupo_id) &&
    esTexto(valor.nombre) &&
    esMonto(valor.ordinaria) &&
    (valor.extraordinaria === undefined || esMonto(valor.extraordinaria))
  );
}

function esComparacion(valor: unknown): valor is ComparacionDeLaExpensa {
  return (
    esRegistro(valor) &&
    esId(valor.liquidacion_id) &&
    esFecha(valor.periodo) &&
    esMonto(valor.total_anterior) &&
    esMonto(valor.diferencia_total) &&
    Array.isArray(valor.categorias) &&
    valor.categorias.every(
      (c) =>
        esRegistro(c) &&
        esId(c.categoria_id) &&
        esTexto(c.nombre) &&
        (c.bloque === "ordinario" || c.bloque === "extraordinario") &&
        esMonto(c.importe) &&
        esMonto(c.importe_anterior) &&
        esMonto(c.diferencia),
    )
  );
}

function esExpensa(valor: unknown): valor is ExpensaDeLaUnidad {
  if (!esRegistro(valor)) return false;
  const b = valor.bloques;
  return (
    esId(valor.liquidacion_id) &&
    esId(valor.complejo_id) &&
    esId(valor.unidad_id) &&
    esTexto(valor.identificador) &&
    esFecha(valor.periodo) &&
    esFecha(valor.vencimiento) &&
    esVinculo(valor.vinculo) &&
    esRegistro(b) &&
    esBloque(b.ordinario) &&
    (b.extraordinario === undefined || esBloque(b.extraordinario)) &&
    Array.isArray(valor.grupos) &&
    valor.grupos.every(esGrupo) &&
    esMonto(valor.ordinaria) &&
    Array.isArray(valor.cargos_particulares) &&
    valor.cargos_particulares.every(
      (c) => esRegistro(c) && esTexto(c.concepto) && esMonto(c.importe),
    ) &&
    esMonto(valor.fondo_de_reserva) &&
    (valor.extraordinaria === undefined || esMonto(valor.extraordinaria)) &&
    esMonto(valor.intereses) &&
    esMonto(valor.total) &&
    (valor.comparacion === null || esComparacion(valor.comparacion))
  );
}

function esPago(valor: unknown): valor is PagoConfirmadoDelVecino {
  return (
    esRegistro(valor) &&
    esId(valor.pago_id) &&
    esFecha(valor.fecha_de_transferencia) &&
    esMonto(valor.importe) &&
    esTexto(valor.banco) &&
    esTexto(valor.numero_de_operacion)
  );
}

function esPdf(valor: unknown): valor is PdfDelVecino {
  return (
    esRegistro(valor) &&
    esId(valor.documento_id) &&
    esId(valor.liquidacion_id) &&
    esId(valor.complejo_id) &&
    esFecha(valor.periodo) &&
    (valor.variante === "completa" || valor.variante === "sin_extraordinaria") &&
    typeof valor.url === "string" &&
    _ENLACE.test(valor.url) &&
    esTexto(valor.vence_en)
  );
}

function deLista<T>(
  resultado: ResultadoApi<unknown>,
  valido: (valor: unknown) => valor is T,
): ResultadoApi<T[]> {
  if (resultado.estado !== "ok") return resultado;
  return Array.isArray(resultado.datos) && resultado.datos.every(valido)
    ? { estado: "ok", datos: resultado.datos }
    : { estado: "fallo" };
}

/** Todas las unidades de la persona, con lo que debe en cada una y el total del conjunto. */
export async function misUnidades(): Promise<ResultadoApi<MisUnidades>> {
  const resultado = await pedirApi<unknown>("/api/mis-unidades");
  if (resultado.estado !== "ok") return resultado;
  return esMisUnidades(resultado.datos)
    ? { estado: "ok", datos: resultado.datos }
    : { estado: "fallo" };
}

/** Las liquidaciones emitidas del edificio de la unidad, la más nueva primero. */
export async function liquidacionesDeLaUnidad(
  unidadId: string,
): Promise<ResultadoApi<LiquidacionDeLaLista[]>> {
  if (!esIdValido(unidadId)) return { estado: "no_existe" };
  return deLista(
    await pedirApi<unknown>(`/api/mis-unidades/${encodeURIComponent(unidadId)}/liquidaciones`),
    esLiquidacion,
  );
}

/** La expensa de una liquidación para la unidad (abrirla la distribuye del lado de la API, D-074). */
export async function expensaDeLaUnidad(
  unidadId: string,
  liquidacionId: string,
): Promise<ResultadoApi<ExpensaDeLaUnidad>> {
  if (!esIdValido(unidadId) || !esIdValido(liquidacionId)) return { estado: "no_existe" };
  const resultado = await pedirApi<unknown>(
    `/api/mis-unidades/${encodeURIComponent(unidadId)}/liquidaciones/${encodeURIComponent(liquidacionId)}`,
  );
  if (resultado.estado !== "ok") return resultado;
  return esExpensa(resultado.datos)
    ? { estado: "ok", datos: resultado.datos }
    : { estado: "fallo" };
}

/** Los pagos confirmados de la unidad, del más nuevo al más viejo. */
export async function pagosConfirmadosDeLaUnidad(
  unidadId: string,
): Promise<ResultadoApi<PagoConfirmadoDelVecino[]>> {
  if (!esIdValido(unidadId)) return { estado: "no_existe" };
  return deLista(
    await pedirApi<unknown>(`/api/mis-unidades/${encodeURIComponent(unidadId)}/pagos`),
    esPago,
  );
}

/** Los PDFs de la unidad, con su enlace firmado (vence a los 15 minutos). */
export async function pdfsDeLaUnidad(unidadId: string): Promise<ResultadoApi<PdfDelVecino[]>> {
  if (!esIdValido(unidadId)) return { estado: "no_existe" };
  return deLista(
    await pedirApi<unknown>(`/api/mis-unidades/${encodeURIComponent(unidadId)}/documentos`),
    esPdf,
  );
}

/**
 * La dirección de la web para bajar el PDF: la del enlace firmado de la API con el prefijo de la ruta
 * propia de la web (`/documentos/descarga`), porque el borde no publica `/api/*` y el navegador nunca
 * debe recibir una dirección de la API. `null` si el enlace no tiene la forma del enlace firmado.
 */
export function direccionDeDescarga(url: string): string | null {
  const token = _ENLACE.exec(url)?.[1];
  return token === undefined ? null : `/documentos/descarga?token=${token}`;
}
