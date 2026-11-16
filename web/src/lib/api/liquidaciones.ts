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

export type NivelDeControl = "duro" | "bloqueante" | "advertencia";

/** Un control antes de emitir (R34, H-012). El `detalle` es para quien lo necesite; la pantalla
 * muestra el nivel y el mensaje. */
export type ControlAntesDeEmitir = {
  codigo: string;
  nivel: NivelDeControl;
  mensaje: string;
  detalle: Record<string, unknown>;
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
  controles: ControlAntesDeEmitir[];
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

/** El vencimiento corrido al emitir (E8): la fecha nueva y su motivo (1 a 500 caracteres). */
export type VencimientoCorrido = { fecha: string; motivo: string };

/** Lo que viaja al emitir (H-013): el `emision_id` que eligió la pantalla, la huella de la
 * preliquidación revisada y los códigos de los bloqueantes aceptados. */
export type PedidoDeEmision = {
  emision_id: string;
  huella: string;
  alertas_aceptadas: string[];
  vencimiento?: VencimientoCorrido;
};

export type ObligacionEmitida = {
  unidad_id: string;
  identificador: string;
  ordinaria: string;
  fondo_de_reserva: string;
  extraordinaria: string;
  vencimiento: string;
};

export type EmisionRegistrada = {
  liquidacion_id: string;
  emision_id: string;
  periodo: string;
  vencimiento: string;
  huella: string;
  obligaciones: ObligacionEmitida[];
};

/**
 * Emite la preliquidación revisada (`AAAA-MM-01`). Un 409 trae su `campo` y `motivo`
 * (`preliquidacion_cambio`, `alertas_distintas`, `periodo_emitido`, `periodo_anterior_sin_emitir`);
 * un 422 `control_duro` llega como `fallo` (la pantalla no deja emitir con un duro activo). Los
 * importes son texto con dos decimales: si no lo son, el resultado es `fallo`. Un id que no es UUID,
 * o un período mal escrito, es "no existe", sin pedido.
 */
export async function emitirLiquidacion(
  id: string,
  periodo: string,
  pedido: PedidoDeEmision,
): Promise<ResultadoApi<EmisionRegistrada>> {
  if (!esIdValido(id) || !_PERIODO.test(periodo)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<EmisionRegistrada>(
    `/api/complejos/${encodeURIComponent(id)}/periodos/${periodo}/emision`,
    {
      metodo: "POST",
      cuerpo: {
        emision_id: pedido.emision_id,
        huella: pedido.huella,
        alertas_aceptadas: pedido.alertas_aceptadas,
        ...(pedido.vencimiento ? { vencimiento: pedido.vencimiento } : {}),
      },
    },
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  const { obligaciones } = resultado.datos;
  const bien =
    Array.isArray(obligaciones) &&
    obligaciones.every(
      (o) => esMonto(o.ordinaria) && esMonto(o.fondo_de_reserva) && esMonto(o.extraordinaria),
    );
  return bien ? resultado : { estado: "fallo" };
}

export type EstadoDeLaLiquidacion = "emitida" | "distribuida" | "anulada";

/** Una fila de `GET .../liquidaciones` (H-014): de la más nueva a la más vieja. */
export type LiquidacionDeLaLista = {
  liquidacion_id: string;
  periodo: string;
  estado: EstadoDeLaLiquidacion;
  total: string;
  emitida_en: string;
};

const _ESTADOS = new Set<string>(["emitida", "distribuida", "anulada"]);

/**
 * Las liquidaciones emitidas del edificio (H-014). El consejo sólo recibe las distribuidas (P39):
 * lo decide la API. Un total que no es texto con dos decimales, o un estado que la pantalla no
 * conoce, es `fallo` en vez de un `ok` que no sabría mostrar. Un id que no es UUID es "no existe".
 */
export async function liquidacionesDelEdificio(
  id: string,
): Promise<ResultadoApi<LiquidacionDeLaLista[]>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  const resultado = await pedirApi<LiquidacionDeLaLista[]>(
    `/api/complejos/${encodeURIComponent(id)}/liquidaciones`,
  );
  if (resultado.estado !== "ok") {
    return resultado;
  }
  const lista = resultado.datos;
  const bien =
    Array.isArray(lista) &&
    lista.every((l) => esMonto(l.total) && _ESTADOS.has(l.estado) && esIdValido(l.liquidacion_id));
  return bien ? resultado : { estado: "fallo" };
}

/** Distribuye a mano una liquidación emitida (E9). Un 409 trae `estado` y su `motivo`
 * (`ya_distribuida`, `anulada`). */
export async function distribuirLiquidacion(
  id: string,
  liquidacionId: string,
): Promise<ResultadoApi<{ estado: EstadoDeLaLiquidacion }>> {
  if (!esIdValido(id) || !esIdValido(liquidacionId)) {
    return { estado: "no_existe" };
  }
  return pedirApi(
    `/api/complejos/${encodeURIComponent(id)}/liquidaciones/${encodeURIComponent(liquidacionId)}/distribucion`,
    { metodo: "POST" },
  );
}

/** Anula una liquidación emitida con su motivo (E10). Un 409 trae `campo` y `motivo`
 * (`ya_distribuida`, `anulada`, `periodo_siguiente_emitido`). */
export async function anularLiquidacion(
  id: string,
  liquidacionId: string,
  motivo: string,
): Promise<ResultadoApi<{ estado: EstadoDeLaLiquidacion }>> {
  if (!esIdValido(id) || !esIdValido(liquidacionId)) {
    return { estado: "no_existe" };
  }
  return pedirApi(
    `/api/complejos/${encodeURIComponent(id)}/liquidaciones/${encodeURIComponent(liquidacionId)}/anulacion`,
    { metodo: "POST", cuerpo: { motivo } },
  );
}
