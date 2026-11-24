/**
 * La morosidad de un edificio (change 10a, H-029): la lectura de H-027 y el Excel de H-028. La pantalla
 * sólo formatea: los montos llegan como texto con dos decimales y el total del resumen es el de la API,
 * nunca una suma de las filas (R07, D-046).
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type EtiquetaDeMorosidad =
  | "moroso_critico"
  | "con_deuda_vencida"
  | "deuda_de_intereses"
  | "bajo_umbral";

export type FilaDeMorosidad = {
  unidad_id: string;
  unidad: string;
  propietarios: string[];
  etiqueta: EtiquetaDeMorosidad;
  total_vencido: string;
  capital: string;
  intereses: string;
  liquidaciones_vencidas: number;
  vencida_desde: string;
  dias: number;
};

export type Morosidad = {
  fecha: string;
  intereses_al: string | null;
  resumen: { unidades_con_deuda: number; morosos_criticos: number; total_vencido: string };
  unidades: FilaDeMorosidad[];
};

const _ETIQUETAS = new Set<string>([
  "moroso_critico",
  "con_deuda_vencida",
  "deuda_de_intereses",
  "bajo_umbral",
]);
const _MONTO = /^-?[0-9]+\.[0-9]{2}$/;
const _FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

function esMonto(valor: unknown): boolean {
  return typeof valor === "string" && _MONTO.test(valor);
}

function filaValida(f: FilaDeMorosidad): boolean {
  return (
    typeof f.unidad === "string" &&
    Array.isArray(f.propietarios) &&
    f.propietarios.every((p) => typeof p === "string") &&
    _ETIQUETAS.has(f.etiqueta) &&
    esMonto(f.total_vencido) &&
    esMonto(f.capital) &&
    esMonto(f.intereses) &&
    Number.isInteger(f.liquidaciones_vencidas) &&
    Number.isInteger(f.dias) &&
    typeof f.vencida_desde === "string" &&
    _FECHA.test(f.vencida_desde)
  );
}

/**
 * La morosidad del edificio (H-027). Un monto que no es texto con dos decimales, una etiqueta que la
 * pantalla no conoce o una forma distinta es `fallo` en vez de un `ok` que no sabría mostrar. Un id que
 * no es UUID es "no existe", sin pedido.
 */
export async function morosidadDelEdificio(id: string): Promise<ResultadoApi<Morosidad>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<Morosidad>(
    `/api/complejos/${encodeURIComponent(id)}/morosidad`,
    {
      camposDePlata: ["resumen.total_vencido"],
    },
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  const { datos } = resultado;
  const bien =
    Array.isArray(datos.unidades) &&
    datos.unidades.every(filaValida) &&
    Number.isInteger(datos.resumen?.unidades_con_deuda) &&
    Number.isInteger(datos.resumen?.morosos_criticos) &&
    (datos.intereses_al === null || _FECHA.test(String(datos.intereses_al)));
  return bien ? resultado : { estado: "fallo" };
}

export type ExcelDeMorosidad = { bytes: ArrayBuffer; disposicion: string | null };

/** El Excel de la morosidad (H-028), con el `Content-Disposition` de la API. Un id que no es UUID es
 * "no existe", sin pedido. Sin sesión se devuelve el estado (la ruta de Next contesta 401). */
export async function excelDeLaMorosidad(id: string): Promise<ResultadoApi<ExcelDeMorosidad>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<ExcelDeMorosidad>(`/api/complejos/${encodeURIComponent(id)}/morosidad/excel`, {
    respuestaBinaria: true,
    conDisposicion: true,
    alNoAutenticar: "devolver",
  });
}
