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
 * - 1301 (H-013, `aceptacion/H-013/CONTRATO.md`): la base con `gastos_en_revision` (bloqueante) y
 *   `gastos_sin_ia` (advertencia); además contesta `POST .../emision` con 201. 1101 también.
 * - 1401 y 1402 (H-014, `aceptacion/H-014/CONTRATO.md`): noviembre ya emitido (total 191.500,00),
 *   `emitida` en 1401 y `distribuida` en 1402; la preliquidación da 409 `periodo_emitido`, la lista de
 *   liquidaciones trae la suya y `POST .../distribucion` y `.../anulacion` contestan 200 y guardan la
 *   última escritura.
 * - 1401 ahora trae además `GET liquidaciones/{id}` con `unidades` (H-017, `aceptacion/H-017/CONTRATO.md`);
 *   1701 la lista con noviembre distribuida y octubre anulada; 1702 y 1703 como 1401 pero sin
 *   `ver_liquidaciones` y `corregir_movimiento` (1702) o sólo sin `corregir_movimiento` (1703); las
 *   acciones por edificio salen de `ACCIONES_POR_EDIFICIO`.
 * - 1501 (H-015, `aceptacion/H-015/CONTRATO.md`): noviembre emitido con dos documentos de `1A`, la
 *   completa `generado` y la sin extraordinaria `fallido` ("sin fuentes"); `POST .../reproceso`
 *   contesta 202 y `POST .../enlace` 201, y las dos guardan la última escritura.
 */

import type { IncomingMessage, ServerResponse } from "node:http";

export const PRELIQUIDACION_BASE = "00000000-0000-0000-0000-000000001101";
export const PRELIQUIDACION_FONDO_CERO = "00000000-0000-0000-0000-000000001102";
export const PRELIQUIDACION_SIN_ANTERIOR = "00000000-0000-0000-0000-000000001103";

export const PRELIQUIDACION_CON_CONTROLES = "00000000-0000-0000-0000-000000001201";
export const PRELIQUIDACION_CON_BLOQUEANTE = "00000000-0000-0000-0000-000000001301";

const _IDS = new Set([
  PRELIQUIDACION_BASE,
  PRELIQUIDACION_FONDO_CERO,
  PRELIQUIDACION_SIN_ANTERIOR,
  PRELIQUIDACION_CON_CONTROLES,
  PRELIQUIDACION_CON_BLOQUEANTE,
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

const _CONTROLES_DE_1301 = [
  _CONTROLES[1],
  {
    codigo: "gastos_sin_ia",
    nivel: "advertencia",
    mensaje: "Hay 1 factura sin cargar",
    detalle: { cantidad: 1, gastos: ["00000000-0000-0000-0000-00000000d102"] },
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
  if (id === PRELIQUIDACION_CON_BLOQUEANTE) {
    json(respuesta, 200, { ...cuerpoDeLaBase(id), controles: _CONTROLES_DE_1301 });
    return;
  }
  json(respuesta, 200, id === PRELIQUIDACION_FONDO_CERO ? cuerpoSinFondo(id) : cuerpoDeLaBase(id));
}

const _UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** Lo que recibió el libro de cada unidad: la ordinaria más los cargos particulares (E15). */
function obligaciones(vencimiento: string) {
  return _UNIDADES.map((u) => ({
    unidad_id: u.unidad_id,
    identificador: u.identificador,
    ordinaria: u.identificador === "1B" ? "32000.00" : u.ordinaria,
    fondo_de_reserva: u.fondo_de_reserva,
    extraordinaria: u.extraordinaria,
    vencimiento,
  }));
}

/** Contesta `periodos/2026-11-01/emision` (POST) de 1101 y 1301 con 201, como la API real: el
 * pedido se valida (JSON, `emision_id` UUID, la huella de la preliquidación mostrada, las alertas
 * aceptadas exactamente las de los bloqueantes del escenario y el vencimiento corrido con su fecha y
 * su motivo). 1201 tiene un duro: 422 `control_duro`, aunque la pantalla no deja llegar. El cuerpo
 * crudo queda en `guardar` (`/api/__debug/ultima-escritura`). */
export function responderEmision(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  periodo: string,
  guardar: (escritura: {
    metodo: string;
    url: string;
    contentType: string;
    cuerpo: string;
  }) => void,
): void {
  if ((pedido.method ?? "GET") !== "POST") {
    respuesta.writeHead(405).end();
    return;
  }
  const trozos: Buffer[] = [];
  pedido.on("data", (trozo: Buffer) => {
    trozos.push(trozo);
  });
  pedido.on("end", () => {
    const cuerpo = Buffer.concat(trozos).toString("utf8");
    guardar({
      metodo: "POST",
      url: pedido.url ?? "",
      contentType: String(pedido.headers["content-type"] ?? ""),
      cuerpo,
    });
    if (periodo !== "2026-11-01") {
      respuesta.writeHead(404).end();
      return;
    }
    if (!/^application\/json/.test(String(pedido.headers["content-type"] ?? ""))) {
      json(respuesta, 422, { detail: [{ type: "json_invalid", loc: ["body"] }] });
      return;
    }
    let leido: Record<string, unknown>;
    try {
      leido = JSON.parse(cuerpo) as Record<string, unknown>;
    } catch {
      json(respuesta, 422, { detail: [{ type: "json_invalid", loc: ["body"] }] });
      return;
    }
    const alertas = leido.alertas_aceptadas;
    const corrida = leido.vencimiento as { fecha?: unknown; motivo?: unknown } | undefined | null;
    const motivoValido =
      corrida === undefined ||
      corrida === null ||
      (typeof corrida.fecha === "string" &&
        corrida.fecha >= "2026-11-01" &&
        typeof corrida.motivo === "string" &&
        corrida.motivo.trim().length >= 1 &&
        corrida.motivo.trim().length <= 500);
    if (
      typeof leido.emision_id !== "string" ||
      !_UUID.test(leido.emision_id) ||
      typeof leido.huella !== "string" ||
      !Array.isArray(alertas) ||
      !motivoValido
    ) {
      json(respuesta, 422, { detail: [{ type: "value_error", loc: ["body"] }] });
      return;
    }
    if (id === PRELIQUIDACION_CON_CONTROLES) {
      json(respuesta, 422, { detail: "control_duro", controles: ["saldos_iniciales_sin_validar"] });
      return;
    }
    const esperadas = id === PRELIQUIDACION_CON_BLOQUEANTE ? ["gastos_en_revision"] : [];
    if (leido.huella !== _HUELLA) {
      json(respuesta, 409, {
        detail: "conflicto",
        campo: "huella",
        motivo: "preliquidacion_cambio",
      });
      return;
    }
    if (JSON.stringify([...alertas].sort()) !== JSON.stringify(esperadas)) {
      json(respuesta, 409, {
        detail: "conflicto",
        campo: "alertas_aceptadas",
        motivo: "alertas_distintas",
      });
      return;
    }
    const vencimiento = corrida ? String(corrida.fecha) : "2026-11-10";
    json(respuesta, 201, {
      liquidacion_id: "00000000-0000-0000-0000-00000000e101",
      emision_id: leido.emision_id,
      periodo: "2026-11-01",
      vencimiento,
      huella: leido.huella,
      obligaciones: obligaciones(vencimiento),
    });
  });
}

// --- Distribuir y anular (H-014) -----------------------------------------------------------------

export const CICLO_EMITIDA = "00000000-0000-0000-0000-000000001401";
export const CICLO_DISTRIBUIDA = "00000000-0000-0000-0000-000000001402";
/** H-017: la lista con una distribuida y una anulada. */
export const LISTA_DE_LIQUIDACIONES = "00000000-0000-0000-0000-000000001701";
/** H-017: como 1401 sin `ver_liquidaciones` ni `corregir_movimiento`. */
export const EMITIDA_SIN_VER = "00000000-0000-0000-0000-000000001702";
/** H-017: como 1401 con `ver_liquidaciones` y sin `corregir_movimiento`. */
export const EMITIDA_SIN_CORREGIR = "00000000-0000-0000-0000-000000001703";
const _LIQUIDACION_EMITIDA = "00000000-0000-0000-0000-000000014011";
const _LIQUIDACION_DISTRIBUIDA = "00000000-0000-0000-0000-000000014021";
const _LIQUIDACION_SIN_VER = "00000000-0000-0000-0000-000000017021";
const _LIQUIDACION_SIN_CORREGIR = "00000000-0000-0000-0000-000000017031";
const _LIQUIDACION_DE_LA_LISTA = "00000000-0000-0000-0000-000000017011";
const _LIQUIDACION_ANULADA = "00000000-0000-0000-0000-000000017012";

const _EMITIDAS = new Set([CICLO_EMITIDA, EMITIDA_SIN_VER, EMITIDA_SIN_CORREGIR]);

export function esEdificioDeCiclo(id: string): boolean {
  return _EMITIDAS.has(id) || id === CICLO_DISTRIBUIDA;
}

/** H-017: las acciones que el edificio suma a la sesión (`por_edificio`). Un edificio que no está
 * acá no suma ninguna: la sesión de la API falsa las trae de a una para poder probar su ausencia. */
const _VER = "ver_liquidaciones";
const _CORREGIR = "corregir_movimiento";
export const ACCIONES_POR_EDIFICIO: Record<string, string[]> = {
  [PRELIQUIDACION_BASE]: [_VER, _CORREGIR],
  [PRELIQUIDACION_FONDO_CERO]: [_VER, _CORREGIR],
  [PRELIQUIDACION_SIN_ANTERIOR]: [_VER, _CORREGIR],
  [PRELIQUIDACION_CON_CONTROLES]: [_VER, _CORREGIR],
  [PRELIQUIDACION_CON_BLOQUEANTE]: [_VER, _CORREGIR],
  [CICLO_EMITIDA]: [_VER, _CORREGIR],
  [CICLO_DISTRIBUIDA]: [_VER, _CORREGIR],
  [LISTA_DE_LIQUIDACIONES]: [_VER, _CORREGIR],
  [EMITIDA_SIN_CORREGIR]: [_VER],
};

function liquidacionDelCiclo(id: string) {
  const ids: Record<string, string> = {
    [CICLO_EMITIDA]: _LIQUIDACION_EMITIDA,
    [EMITIDA_SIN_VER]: _LIQUIDACION_SIN_VER,
    [EMITIDA_SIN_CORREGIR]: _LIQUIDACION_SIN_CORREGIR,
  };
  return {
    liquidacion_id: ids[id] ?? _LIQUIDACION_DISTRIBUIDA,
    periodo: "2026-11-01",
    estado: _EMITIDAS.has(id) ? "emitida" : "distribuida",
    total: "191500.00",
    emitida_en: "2026-11-02T15:00:00+00:00",
  };
}

/** Lo que paga cada unidad en la emitida (H-017): los importes de la base de H-011, saldo anterior
 * `0.00`, y la obligación del libro de cada una (`1A`: `...140101`, con la unidad `...140111`). */
function unidadesDeLaEmitida() {
  return _UNIDADES.map((u, i) => ({
    unidad_id: `00000000-0000-0000-0000-00000014011${i + 1}`,
    identificador: u.identificador,
    ordinaria: u.ordinaria,
    fondo_de_reserva: u.fondo_de_reserva,
    extraordinaria: u.extraordinaria,
    cargos_particulares: u.cargos_particulares,
    intereses: u.intereses,
    saldo_anterior: "0.00",
    total: u.total,
    sin_obligacion: false,
    por_grupo: u.por_grupo,
    obligacion_id: `00000000-0000-0000-0000-00000014010${i + 1}`,
  }));
}

/** `GET liquidaciones` de 1701 (H-017): noviembre distribuida y octubre anulada. */
function listaDeLaLista() {
  return [
    {
      liquidacion_id: _LIQUIDACION_DE_LA_LISTA,
      periodo: "2026-11-01",
      estado: "distribuida",
      total: "191500.00",
      emitida_en: "2026-11-02T15:00:00+00:00",
    },
    {
      liquidacion_id: _LIQUIDACION_ANULADA,
      periodo: "2026-10-01",
      estado: "anulada",
      total: "180000.00",
      emitida_en: "2026-10-02T15:00:00+00:00",
    },
  ];
}

/** Contesta `GET liquidaciones` en 1701 (H-017). `false` si no es de su incumbencia. */
export function responderLista(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  resto: string,
): boolean {
  if ((pedido.method ?? "GET") === "GET" && resto === "liquidaciones") {
    json(respuesta, 200, listaDeLaLista());
    return true;
  }
  return false;
}

/**
 * Contesta lo del ciclo en 1401 y 1402: `GET periodos/2026-11-01/preliquidacion` (409
 * `periodo_emitido`), `GET liquidaciones` (la de noviembre) y `POST liquidaciones/{id}/distribucion`
 * y `.../anulacion` (200, y el cuerpo crudo a `guardar`). Devuelve `false` si no es de su incumbencia
 * (la API falsa sigue con el resto, como el detalle del edificio).
 */
export function responderCiclo(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  guardar: (escritura: {
    metodo: string;
    url: string;
    contentType: string;
    cuerpo: string;
  }) => void,
): boolean {
  const metodo = pedido.method ?? "GET";
  if (metodo === "GET" && resto === "periodos/2026-11-01/preliquidacion") {
    json(respuesta, 409, { detail: "conflicto", campo: "periodo", motivo: "periodo_emitido" });
    return true;
  }
  if (metodo === "GET" && resto === "liquidaciones") {
    json(respuesta, 200, [liquidacionDelCiclo(id)]);
    return true;
  }
  if (metodo === "GET" && resto === `liquidaciones/${liquidacionDelCiclo(id).liquidacion_id}`) {
    json(respuesta, 200, { ...liquidacionDelCiclo(id), unidades: unidadesDeLaEmitida() });
    return true;
  }
  const accion = /^liquidaciones\/([^/]+)\/(distribucion|anulacion)$/.exec(resto);
  if (metodo === "POST" && accion) {
    const trozos: Buffer[] = [];
    pedido.on("data", (trozo: Buffer) => {
      trozos.push(trozo);
    });
    pedido.on("end", () => {
      const cuerpo = Buffer.concat(trozos).toString("utf8");
      guardar({
        metodo: "POST",
        url: pedido.url ?? "",
        contentType: String(pedido.headers["content-type"] ?? ""),
        cuerpo,
      });
      if (accion[1] !== liquidacionDelCiclo(id).liquidacion_id) {
        respuesta.writeHead(404).end();
        return;
      }
      if (accion[2] === "anulacion") {
        let motivo: unknown;
        try {
          motivo = (JSON.parse(cuerpo) as { motivo?: unknown }).motivo;
        } catch {
          motivo = undefined;
        }
        if (typeof motivo !== "string" || motivo.trim() === "") {
          json(respuesta, 422, { detail: [{ type: "value_error", loc: ["body", "motivo"] }] });
          return;
        }
        json(respuesta, 200, { estado: "anulada" });
        return;
      }
      json(respuesta, 200, { estado: "distribuida" });
    });
    return true;
  }
  return false;
}

// --- Documentos de la expensa (H-015) ------------------------------------------------------------

export const DOCUMENTOS_DE_EXPENSA = "00000000-0000-0000-0000-000000001501";
const _LIQUIDACION_CON_DOCUMENTOS = "00000000-0000-0000-0000-000000015011";
const _DOCUMENTO_GENERADO = "00000000-0000-0000-0000-000000015101";
const _DOCUMENTO_FALLIDO = "00000000-0000-0000-0000-000000015102";

/** Un token con la forma de uno firmado (dos tramos, el segundo de 64 caracteres hexadecimales). */
export const TOKEN_DE_PRUEBA = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

export function esEdificioDeDocumentos(id: string): boolean {
  return id === DOCUMENTOS_DE_EXPENSA;
}

/**
 * Contesta lo de los documentos en 1501: `GET periodos/2026-11-01/preliquidacion` (409
 * `periodo_emitido`), `GET liquidaciones` (la de noviembre, emitida), `GET liquidaciones/{id}/documentos`
 * (los dos de `1A`), `POST liquidaciones/{id}/documentos/reproceso` (202 `{"encolados": 1}`) y
 * `POST documentos/{id}/enlace` (201 con una dirección de descarga de prueba). Las dos escrituras
 * llegan crudas a `guardar` (la última gana). Devuelve `false` si no es de su incumbencia.
 */
export function responderDocumentos(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  resto: string,
  guardar: (escritura: {
    metodo: string;
    url: string;
    contentType: string;
    cuerpo: string;
  }) => void,
): boolean {
  const metodo = pedido.method ?? "GET";
  if (metodo === "GET" && resto === "periodos/2026-11-01/preliquidacion") {
    json(respuesta, 409, { detail: "conflicto", campo: "periodo", motivo: "periodo_emitido" });
    return true;
  }
  if (metodo === "GET" && resto === "liquidaciones") {
    json(respuesta, 200, [
      {
        liquidacion_id: _LIQUIDACION_CON_DOCUMENTOS,
        periodo: "2026-11-01",
        estado: "emitida",
        total: "191500.00",
        emitida_en: "2026-11-02T15:00:00+00:00",
      },
    ]);
    return true;
  }
  if (metodo === "GET" && resto === `liquidaciones/${_LIQUIDACION_CON_DOCUMENTOS}/documentos`) {
    json(respuesta, 200, [
      {
        documento_id: _DOCUMENTO_GENERADO,
        unidad_id: "00000000-0000-0000-0000-000000015201",
        identificador: "1A",
        variante: "completa",
        estado: "generado",
        motivo: null,
      },
      {
        documento_id: _DOCUMENTO_FALLIDO,
        unidad_id: "00000000-0000-0000-0000-000000015201",
        identificador: "1A",
        variante: "sin_extraordinaria",
        estado: "fallido",
        motivo: "sin fuentes",
      },
    ]);
    return true;
  }
  const reproceso = resto === `liquidaciones/${_LIQUIDACION_CON_DOCUMENTOS}/documentos/reproceso`;
  const enlace = /^documentos\/([^/]+)\/enlace$/.exec(resto);
  if (metodo === "POST" && (reproceso || enlace)) {
    const trozos: Buffer[] = [];
    pedido.on("data", (trozo: Buffer) => {
      trozos.push(trozo);
    });
    pedido.on("end", () => {
      guardar({
        metodo: "POST",
        url: pedido.url ?? "",
        contentType: String(pedido.headers["content-type"] ?? ""),
        cuerpo: Buffer.concat(trozos).toString("utf8"),
      });
      if (reproceso) {
        json(respuesta, 202, { encolados: 1 });
        return;
      }
      if (enlace?.[1] !== _DOCUMENTO_GENERADO) {
        respuesta.writeHead(404).end();
        return;
      }
      json(respuesta, 201, {
        url: `/api/documentos/descarga?token=${TOKEN_DE_PRUEBA}`,
        vence_en: "2026-11-02T15:15:00+00:00",
      });
    });
    return true;
  }
  return false;
}
