/**
 * Liquidación de un período (change 7, H-011): la preliquidación, lo que paga cada unidad antes de
 * emitir. La pantalla sólo formatea: los montos llegan como texto con dos decimales y nunca se
 * suman ni se comparan como números (R07, D-046).
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type CargoDeLaUnidad = { concepto: string; importe: string };

export type PorGrupoDeLaUnidad = { grupo_id: string; ordinaria: string; extraordinaria: string };

export type UnidadPreliquidada = {
  unidad_id: string;
  identificador: string;
  ordinaria: string;
  fondo_de_reserva: string;
  extraordinaria: string;
  cargos_particulares: CargoDeLaUnidad[];
  intereses: string;
  total: string;
  sin_obligacion: boolean;
  por_grupo: PorGrupoDeLaUnidad[];
};

export type CategoriaDelBloque = {
  categoria_id: string;
  nombre: string;
  importe: string;
  porcentaje: string;
};

export type BloqueDeGastos = { subtotal: string; categorias: CategoriaDelBloque[] };

export type GrupoPreliquidado = {
  grupo_id: string;
  nombre: string;
  metodo: string;
  ordinario: string;
  extraordinario: string;
};

export type TotalesDeLaPreliquidacion = {
  gastos: string;
  notas_de_credito: string;
  fondo_de_reserva: string;
  prorrateado: string;
  cargos_particulares: string;
  intereses: string;
  total: string;
};

export type Preliquidacion = {
  complejo_id: string;
  periodo: string;
  vencimiento: string;
  porcentaje_fondo: string;
  huella: string;
  totales: TotalesDeLaPreliquidacion;
  bloques: { ordinario: BloqueDeGastos; extraordinario: BloqueDeGastos };
  grupos: GrupoPreliquidado[];
  unidades: UnidadPreliquidada[];
  controles: unknown[];
};

const _MONTO = /^-?[0-9]+\.[0-9]{2}$/;
const _PERIODO = /^[0-9]{4}-(0[1-9]|1[0-2])-01$/;

function esMonto(valor: unknown): boolean {
  return typeof valor === "string" && _MONTO.test(valor);
}

function bloqueValido(bloque: BloqueDeGastos | undefined): boolean {
  return (
    bloque !== undefined &&
    esMonto(bloque.subtotal) &&
    Array.isArray(bloque.categorias) &&
    bloque.categorias.every((c) => esMonto(c.importe) && esMonto(c.porcentaje))
  );
}

function cuerpoValido(datos: Preliquidacion): boolean {
  return (
    Array.isArray(datos.unidades) &&
    datos.unidades.every(
      (u) =>
        esMonto(u.ordinaria) &&
        esMonto(u.fondo_de_reserva) &&
        esMonto(u.extraordinaria) &&
        esMonto(u.intereses) &&
        esMonto(u.total) &&
        Array.isArray(u.cargos_particulares) &&
        u.cargos_particulares.every((c) => esMonto(c.importe)),
    ) &&
    esMonto(datos.porcentaje_fondo) &&
    Array.isArray(datos.grupos) &&
    datos.grupos.every((g) => esMonto(g.ordinario) && esMonto(g.extraordinario)) &&
    bloqueValido(datos.bloques?.ordinario) &&
    bloqueValido(datos.bloques?.extraordinario)
  );
}

/**
 * La preliquidación de `periodo` (`AAAA-MM-01`). Un 409 trae su `motivo` (`periodo_emitido`,
 * `periodo_anterior_sin_emitir`): la pantalla lo traduce. Si algún monto no es texto con dos
 * decimales, el resultado es `fallo` en vez de un `ok` que la pantalla no sabría mostrar. Un id que
 * no es UUID, o un período mal escrito, es "no existe", sin pedido.
 */
export async function preliquidacionDelPeriodo(
  id: string,
  periodo: string,
): Promise<ResultadoApi<Preliquidacion>> {
  if (!esIdValido(id) || !_PERIODO.test(periodo)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<Preliquidacion>(
    `/api/complejos/${encodeURIComponent(id)}/periodos/${periodo}/preliquidacion`,
    {
      camposDePlata: [
        "totales.gastos",
        "totales.notas_de_credito",
        "totales.fondo_de_reserva",
        "totales.prorrateado",
        "totales.cargos_particulares",
        "totales.intereses",
        "totales.total",
      ],
    },
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  return cuerpoValido(resultado.datos) ? resultado : { estado: "fallo" };
}
