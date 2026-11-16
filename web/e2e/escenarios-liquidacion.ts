/**
 * Preliquidación de un período (change 7, H-011), a pedido de la API falsa: tres edificios del
 * contrato (`aceptacion/H-011/CONTRATO.md`, "API falsa"). Contestan sólo
 * `GET .../periodos/2026-11-01/preliquidacion`; las lecturas de la pantalla (edificio, resumen) las
 * contesta la API falsa como a cualquier edificio.
 *
 * - 1101: la base de los ejemplos (fondo 5%): `1A` 43.350,00, `1B` 48.350,00, `2A` 62.375,00 y `2B`
 *   37.425,00; total 191.500,00.
 * - 1102: la misma base con fondo 0%: sin fondo en ninguna unidad, los otros importes de la ordinaria
 *   y de la extraordinaria no cambian.
 * - 1103: 409 `periodo_anterior_sin_emitir`.
 * - 1201 (H-012, `aceptacion/H-012/CONTRATO.md`): la base con tres controles, uno de cada nivel.
 */

import type { IncomingMessage, ServerResponse } from "node:http";

export const PRELIQUIDACION_BASE = "00000000-0000-0000-0000-000000001101";
export const PRELIQUIDACION_FONDO_CERO = "00000000-0000-0000-0000-000000001102";
export const PRELIQUIDACION_SIN_ANTERIOR = "00000000-0000-0000-0000-000000001103";

export const PRELIQUIDACION_CON_CONTROLES = "00000000-0000-0000-0000-000000001201";

const _IDS = new Set([
  PRELIQUIDACION_BASE,
  PRELIQUIDACION_FONDO_CERO,
  PRELIQUIDACION_SIN_ANTERIOR,
  PRELIQUIDACION_CON_CONTROLES,
]);

const _CONTROLES = [
  {
    codigo: "saldos_iniciales_sin_validar",
    nivel: "duro",
    mensaje: "Faltan validar los saldos iniciales del edificio",
    detalle: { estado_migracion: "pendiente" },
  },
  {
    codigo: "gastos_en_revision",
    nivel: "bloqueante",
    mensaje: "Hay 1 factura leída con alertas",
    detalle: { cantidad: 1, gastos: ["00000000-0000-0000-0000-00000000d101"] },
  },
  {
    codigo: "gastos_sin_ia",
    nivel: "advertencia",
    mensaje: "Hay 2 facturas sin cargar",
    detalle: {
      cantidad: 2,
      gastos: ["00000000-0000-0000-0000-00000000d102", "00000000-0000-0000-0000-00000000d103"],
    },
  },
];

const _GENERALES = "00000000-0000-0000-0000-00000000a101";
const _ASCENSOR = "00000000-0000-0000-0000-00000000a102";
const _LIMPIEZA = "00000000-0000-0000-0000-00000000c101";
const _ASCENSOR_CATEGORIA = "00000000-0000-0000-0000-00000000c102";
const _PINTURA = "00000000-0000-0000-0000-00000000c103";
const _HUELLA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

export function esEdificioDePreliquidacion(id: string): boolean {
  return _IDS.has(id);
}

type Unidad = {
  unidad_id: string;
  identificador: string;
  ordinaria: string;
  fondo_de_reserva: string;
  extraordinaria: string;
  cargos_particulares: { concepto: string; importe: string }[];
  intereses: string;
  total: string;
  sin_obligacion: boolean;
  por_grupo: { grupo_id: string; ordinaria: string; extraordinaria: string }[];
};

const _UNIDADES: Unidad[] = [
  {
    unidad_id: "00000000-0000-0000-0000-00000000b101",
    identificador: "1A",
    ordinaria: "27000.00",
    fondo_de_reserva: "1350.00",
    extraordinaria: "15000.00",
    cargos_particulares: [],
    intereses: "0.00",
    total: "43350.00",
    sin_obligacion: false,
    por_grupo: [{ grupo_id: _GENERALES, ordinaria: "27000.00", extraordinaria: "15000.00" }],
  },
  {
    unidad_id: "00000000-0000-0000-0000-00000000b102",
    identificador: "1B",
    ordinaria: "27000.00",
    fondo_de_reserva: "1350.00",
    extraordinaria: "15000.00",
    cargos_particulares: [{ concepto: "Multa", importe: "5000.00" }],
    intereses: "0.00",
    total: "48350.00",
    sin_obligacion: false,
    por_grupo: [{ grupo_id: _GENERALES, ordinaria: "27000.00", extraordinaria: "15000.00" }],
  },
  {
    unidad_id: "00000000-0000-0000-0000-00000000b103",
    identificador: "2A",
    ordinaria: "47500.00",
    fondo_de_reserva: "2375.00",
    extraordinaria: "12500.00",
    cargos_particulares: [],
    intereses: "0.00",
    total: "62375.00",
    sin_obligacion: false,
    por_grupo: [
      { grupo_id: _GENERALES, ordinaria: "22500.00", extraordinaria: "12500.00" },
      { grupo_id: _ASCENSOR, ordinaria: "25000.00", extraordinaria: "0.00" },
    ],
  },
  {
    unidad_id: "00000000-0000-0000-0000-00000000b104",
    identificador: "2B",
    ordinaria: "28500.00",
    fondo_de_reserva: "1425.00",
    extraordinaria: "7500.00",
    cargos_particulares: [],
    intereses: "0.00",
    total: "37425.00",
    sin_obligacion: false,
    por_grupo: [
      { grupo_id: _GENERALES, ordinaria: "13500.00", extraordinaria: "7500.00" },
      { grupo_id: _ASCENSOR, ordinaria: "15000.00", extraordinaria: "0.00" },
    ],
  },
];

function cuerpoDeLaBase(edificio: string) {
  return {
    complejo_id: edificio,
    periodo: "2026-11-01",
    vencimiento: "2026-11-10",
    porcentaje_fondo: "5.00",
    huella: _HUELLA,
    totales: {
      gastos: "190000.00",
      notas_de_credito: "10000.00",
      fondo_de_reserva: "6500.00",
      prorrateado: "186500.00",
      cargos_particulares: "5000.00",
      intereses: "0.00",
      total: "191500.00",
    },
    bloques: {
      ordinario: {
        subtotal: "130000.00",
        categorias: [
          { categoria_id: _LIMPIEZA, nombre: "Limpieza", importe: "90000.00", porcentaje: "69.23" },
          {
            categoria_id: _ASCENSOR_CATEGORIA,
            nombre: "Ascensor",
            importe: "40000.00",
            porcentaje: "30.77",
          },
        ],
      },
      extraordinario: {
        subtotal: "50000.00",
        categorias: [
          { categoria_id: _PINTURA, nombre: "Pintura", importe: "50000.00", porcentaje: "100.00" },
        ],
      },
    },
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        metodo: "coeficiente",
        ordinario: "90000.00",
        extraordinario: "50000.00",
      },
      {
        grupo_id: _ASCENSOR,
        nombre: "Ascensor",
        metodo: "coeficiente",
        ordinario: "40000.00",
        extraordinario: "0.00",
      },
    ],
    unidades: _UNIDADES,
    controles: [],
  };
}

/** La misma base sin fondo: lo que el fondo sumaba a cada unidad se resta de su total y del de la
 * liquidación (los importes de la ordinaria y la extraordinaria no cambian). */
function cuerpoSinFondo(edificio: string) {
  const base = cuerpoDeLaBase(edificio);
  const sinFondo: Record<string, string> = {
    "1A": "42000.00",
    "1B": "47000.00",
    "2A": "60000.00",
    "2B": "36000.00",
  };
  return {
    ...base,
    porcentaje_fondo: "0.00",
    totales: {
      ...base.totales,
      fondo_de_reserva: "0.00",
      prorrateado: "180000.00",
      total: "185000.00",
    },
    unidades: _UNIDADES.map((u) => ({
      ...u,
      fondo_de_reserva: "0.00",
      total: sinFondo[u.identificador] ?? u.total,
    })),
  };
}

function json(respuesta: ServerResponse, estado: number, cuerpo: unknown): void {
  respuesta.writeHead(estado, { "content-type": "application/json" }).end(JSON.stringify(cuerpo));
}

/** Contesta `periodos/{periodo}/preliquidacion` (GET) de los tres edificios del contrato de H-011.
 * Sólo el período `2026-11-01`: otro no existe en este doble (404). */
export function responderPreliquidacion(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  periodo: string,
): void {
  if ((pedido.method ?? "GET") !== "GET") {
    respuesta.writeHead(405).end();
    return;
  }
  if (periodo !== "2026-11-01") {
    respuesta.writeHead(404).end();
    return;
  }
  if (id === PRELIQUIDACION_SIN_ANTERIOR) {
    json(respuesta, 409, {
      detail: "conflicto",
      campo: "periodo",
      motivo: "periodo_anterior_sin_emitir",
    });
    return;
  }
  if (id === PRELIQUIDACION_CON_CONTROLES) {
    json(respuesta, 200, { ...cuerpoDeLaBase(id), controles: _CONTROLES });
    return;
  }
  json(respuesta, 200, id === PRELIQUIDACION_FONDO_CERO ? cuerpoSinFondo(id) : cuerpoDeLaBase(id));
}
