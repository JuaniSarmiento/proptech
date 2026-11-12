/**
 * Importar el padrón desde Excel (change 5, H-007), a pedido de la API falsa: un UUID fijo por
 * resultado del `POST /api/complejos/{id}/importaciones`. Las lecturas que la pantalla necesita
 * (edificio, resumen) las contesta la API falsa como a cualquier edificio con la migración
 * `pendiente`. La API falsa no lee el Excel: lo que decide el resultado es el id del edificio.
 *
 * H-008 suma los de la comparación (801 a 803), H-009 los de la confirmación (901 a 904) y H-010 los
 * del ajuste de saldo inicial (1001 a 1003).
 */

import { readFileSync } from "node:fs";
import type { IncomingMessage, ServerResponse } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const IMPORTACION_ACEPTADA = "00000000-0000-0000-0000-000000000701";
export const IMPORTACION_RECHAZADA = "00000000-0000-0000-0000-000000000702";
export const IMPORTACION_SIN_PERMISO = "00000000-0000-0000-0000-000000000703";

const _IDS = new Set([IMPORTACION_ACEPTADA, IMPORTACION_RECHAZADA, IMPORTACION_SIN_PERMISO]);

const _XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const _PLANTILLA = join(dirname(fileURLToPath(import.meta.url)), "plantilla-padron.xlsx");

export type EscrituraRecibida = {
  metodo: string;
  url: string;
  contentType: string;
  cuerpo: string;
};

export function esEdificioDeImportacion(id: string): boolean {
  return _IDS.has(id);
}

// H-008: los tres edificios de la comparación de saldos (`importaciones/comparacion` y
// `importaciones/aceptacion-de-diferencias`). Las lecturas de la pantalla (edificio, resumen) las
// contesta la API falsa como a cualquier edificio con la migración `pendiente`.
export const COMPARACION_CON_DIFERENCIAS = "00000000-0000-0000-0000-000000000801";
export const COMPARACION_SIN_DIFERENCIAS = "00000000-0000-0000-0000-000000000802";
export const COMPARACION_SIN_PERMISO = "00000000-0000-0000-0000-000000000803";
const _IMPORTACION_COMPARADA = "00000000-0000-0000-0000-000000008801";
const _AVISO = "El primer interés del sistema cubre octubre de 2026";

const _IDS_DE_COMPARACION = new Set([
  COMPARACION_CON_DIFERENCIAS,
  COMPARACION_SIN_DIFERENCIAS,
  COMPARACION_SIN_PERMISO,
]);

export function esEdificioDeComparacion(id: string): boolean {
  return _IDS_DE_COMPARACION.has(id);
}

/** Dos diferencias de signo opuesto (`1A` +10.000, `2A` -10.000) que dejan los totales iguales. */
const _COMPARACION_CON_DIFERENCIAS = {
  importacion_id: _IMPORTACION_COMPARADA,
  unidades: [
    {
      unidad: "1A",
      unidad_id: "00000000-0000-0000-0000-00000000081a",
      borrador: "169000.00",
      control: "159000.00",
      diferencia: "10000.00",
      aviso: _AVISO,
    },
    {
      unidad: "1B",
      unidad_id: "00000000-0000-0000-0000-00000000081b",
      borrador: "105000.00",
      control: "105000.00",
      diferencia: "0.00",
      aviso: _AVISO,
    },
    {
      unidad: "2A",
      unidad_id: "00000000-0000-0000-0000-00000000082a",
      borrador: "52000.00",
      control: "62000.00",
      diferencia: "-10000.00",
      aviso: _AVISO,
    },
  ],
  total_borrador: "326000.00",
  total_control: "326000.00",
  unidades_con_diferencia: 2,
  requiere_aceptacion: true,
  aceptacion: null,
};

const _COMPARACION_SIN_DIFERENCIAS = {
  importacion_id: "00000000-0000-0000-0000-000000008802",
  unidades: [
    {
      unidad: "1A",
      unidad_id: "00000000-0000-0000-0000-00000000081a",
      borrador: "169000.00",
      control: "169000.00",
      diferencia: "0.00",
      aviso: null,
    },
  ],
  total_borrador: "169000.00",
  total_control: "169000.00",
  unidades_con_diferencia: 0,
  requiere_aceptacion: false,
  aceptacion: null,
};

// H-009: los cuatro edificios de la confirmación (`importaciones/confirmacion` y, para llegar a ella,
// `importaciones/comparacion`). El 902 tiene la migración `confirmada` (el resumen lo dice): no
// recibe pedidos de importación.
export const CONFIRMACION_PENDIENTE = "00000000-0000-0000-0000-000000000901";
export const CONFIRMACION_CONFIRMADO = "00000000-0000-0000-0000-000000000902";
export const CONFIRMACION_CON_DIFERENCIAS = "00000000-0000-0000-0000-000000000903";
export const CONFIRMACION_SIN_PERMISO = "00000000-0000-0000-0000-000000000904";
const _IMPORTACION_A_CONFIRMAR = "00000000-0000-0000-0000-000000009901";

const _IDS_DE_CONFIRMACION = new Set([
  CONFIRMACION_PENDIENTE,
  CONFIRMACION_CONFIRMADO,
  CONFIRMACION_CON_DIFERENCIAS,
  CONFIRMACION_SIN_PERMISO,
]);

export function esEdificioDeConfirmacion(id: string): boolean {
  return _IDS_DE_CONFIRMACION.has(id);
}

/** Con la migración `confirmada` (el resumen cambia el estado y el paso 7): el 902 y, del ajuste de
 * H-010, el 1001 y el 1003. */
export function esEdificioConfirmado(id: string): boolean {
  return id === CONFIRMACION_CONFIRMADO || id === AJUSTE_CONFIRMADO || id === AJUSTE_SIN_PERMISO;
}

const _COMPARACION_A_CONFIRMAR = {
  ..._COMPARACION_SIN_DIFERENCIAS,
  importacion_id: _IMPORTACION_A_CONFIRMAR,
};

const _COMPARACION_CON_UNA_DIFERENCIA = {
  importacion_id: _IMPORTACION_A_CONFIRMAR,
  unidades: [
    {
      unidad: "1A",
      unidad_id: "00000000-0000-0000-0000-00000000081a",
      borrador: "169000.00",
      control: "159000.00",
      diferencia: "10000.00",
      aviso: null,
    },
  ],
  total_borrador: "169000.00",
  total_control: "159000.00",
  unidades_con_diferencia: 1,
  requiere_aceptacion: true,
  aceptacion: null,
};

// H-010: los tres edificios del ajuste de saldo inicial. El 1001 y el 1003 tienen la migración
// `confirmada` (el 1003 rechaza el ajuste con 403); el 1002 la tiene pendiente y no recibe pedidos.
// Cada uno trae una unidad `1A` con su id fijo, como la que nombra el contrato.
export const AJUSTE_CONFIRMADO = "00000000-0000-0000-0000-000000001001";
export const AJUSTE_PENDIENTE = "00000000-0000-0000-0000-000000001002";
export const AJUSTE_SIN_PERMISO = "00000000-0000-0000-0000-000000001003";
const _UNIDAD_1A_DE_AJUSTE: Record<string, string> = {
  [AJUSTE_CONFIRMADO]: "00000000-0000-0000-0000-000000100101",
  [AJUSTE_PENDIENTE]: "00000000-0000-0000-0000-000000100201",
  [AJUSTE_SIN_PERMISO]: "00000000-0000-0000-0000-000000100301",
};

export function esEdificioDeAjuste(id: string): boolean {
  return id in _UNIDAD_1A_DE_AJUSTE;
}

/** El padrón de los edificios del ajuste: una sola unidad, la `1A` del contrato. */
export function padronDeAjuste(id: string): unknown {
  return {
    unidades: [
      {
        id: _UNIDAD_1A_DE_AJUSTE[id],
        complejo_id: id,
        identificador: "1A",
        tipo: "departamento",
        piso: "1",
        coeficiente: "1.000000",
        superficie_m2: "60.00",
      },
    ],
    informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" },
  };
}

/** Contesta `unidades/{unidad}/ajustes-de-saldo-inicial` (POST) de los tres edificios del contrato
 * de H-010: 201 con el ajuste que se mandó (el importe y el motivo son los del cuerpo), salvo el
 * 1003, que da 403. El `POST` deja su cuerpo crudo en `guardar`. */
export function responderAjuste(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  unidadId: string,
  guardar: (escritura: EscrituraRecibida) => void,
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
    if (id === AJUSTE_SIN_PERMISO) {
      json(respuesta, 403, {
        detail: {
          codigo: "sin_permiso",
          detalle: "sin_permiso",
          permiso_faltante: "ajustar_saldo_inicial",
        },
      });
      return;
    }
    if (id === AJUSTE_PENDIENTE) {
      json(respuesta, 409, { detail: "conflicto", campo: "estado_migracion" });
      return;
    }
    let pedidoLeido: Record<string, unknown> = {};
    try {
      pedidoLeido = JSON.parse(cuerpo) as Record<string, unknown>;
    } catch {
      json(respuesta, 422, { detail: [{ type: "json_invalid", loc: ["body"] }] });
      return;
    }
    json(respuesta, 201, {
      ajuste_id: "00000000-0000-0000-0000-000000001a01",
      operacion_id: pedidoLeido.operacion_id,
      obligacion_id: "00000000-0000-0000-0000-000000001b01",
      cuenta_id: "00000000-0000-0000-0000-000000001c01",
      unidad_id: unidadId,
      importe: pedidoLeido.importe,
      componente: pedidoLeido.componente,
      periodo: "2026-10-01",
      vencimiento: "2026-11-12",
      motivo: pedidoLeido.motivo,
      registrado_por: "00000000-0000-0000-0000-000000000101",
      registrado_en: "2026-11-12T15:00:00+00:00",
    });
  });
}

/** Contesta `importaciones/comparacion` (GET) y `importaciones/confirmacion` (POST) de los cuatro
 * edificios del contrato de H-009. El `POST` deja su cuerpo crudo en `guardar`. */
export function responderConfirmacion(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  guardar: (escritura: EscrituraRecibida) => void,
): void {
  const metodo = pedido.method ?? "GET";
  if (resto === "importaciones/comparacion") {
    if (metodo !== "GET") {
      respuesta.writeHead(405).end();
      return;
    }
    json(
      respuesta,
      200,
      id === CONFIRMACION_CON_DIFERENCIAS
        ? _COMPARACION_CON_UNA_DIFERENCIA
        : _COMPARACION_A_CONFIRMAR,
    );
    return;
  }
  if (metodo !== "POST") {
    respuesta.writeHead(405).end();
    return;
  }
  const trozos: Buffer[] = [];
  pedido.on("data", (trozo: Buffer) => {
    trozos.push(trozo);
  });
  pedido.on("end", () => {
    guardar({
      metodo,
      url: pedido.url ?? "",
      contentType: String(pedido.headers["content-type"] ?? ""),
      cuerpo: Buffer.concat(trozos).toString("utf8"),
    });
    if (id === CONFIRMACION_SIN_PERMISO) {
      json(respuesta, 403, {
        detail: {
          codigo: "sin_permiso",
          detalle: "sin_permiso",
          permiso_faltante: "confirmar_saldos_iniciales",
        },
      });
      return;
    }
    if (id === CONFIRMACION_CONFIRMADO || id === CONFIRMACION_CON_DIFERENCIAS) {
      json(respuesta, 409, {
        detail: "conflicto",
        campo: id === CONFIRMACION_CONFIRMADO ? "estado_migracion" : "diferencias",
      });
      return;
    }
    json(respuesta, 201, {
      importacion_id: _IMPORTACION_A_CONFIRMAR,
      carga_id: "00000000-0000-0000-0000-000000009a01",
      estado_migracion: "confirmada",
      totales: { capital: "320000.00", interes_importado: "6000.00", credito: "6000.00" },
      confirmada_por: "00000000-0000-0000-0000-000000000101",
      confirmada_en: "2026-11-12T15:00:00+00:00",
    });
  });
}

/** Contesta `importaciones/comparacion` (GET) y `importaciones/aceptacion-de-diferencias` (POST)
 * de los tres edificios del contrato de H-008. El `POST` deja su cuerpo crudo en `guardar`. */
export function responderComparacion(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  guardar: (escritura: EscrituraRecibida) => void,
): void {
  const metodo = pedido.method ?? "GET";
  if (resto === "importaciones/comparacion") {
    if (metodo !== "GET") {
      respuesta.writeHead(405).end();
      return;
    }
    json(
      respuesta,
      200,
      id === COMPARACION_SIN_DIFERENCIAS
        ? _COMPARACION_SIN_DIFERENCIAS
        : _COMPARACION_CON_DIFERENCIAS,
    );
    return;
  }
  if (metodo !== "POST") {
    respuesta.writeHead(405).end();
    return;
  }
  const trozos: Buffer[] = [];
  pedido.on("data", (trozo: Buffer) => {
    trozos.push(trozo);
  });
  pedido.on("end", () => {
    guardar({
      metodo,
      url: pedido.url ?? "",
      contentType: String(pedido.headers["content-type"] ?? ""),
      cuerpo: Buffer.concat(trozos).toString("utf8"),
    });
    if (id === COMPARACION_SIN_PERMISO) {
      json(respuesta, 403, {
        detail: {
          codigo: "sin_permiso",
          detalle: "sin_permiso",
          permiso_faltante: "aceptar_diferencias_de_saldos",
        },
      });
      return;
    }
    json(respuesta, 201, {
      aceptacion_id: "00000000-0000-0000-0000-000000008a01",
      diferencias: [
        { unidad: "1A", borrador: "169000.00", control: "159000.00", diferencia: "10000.00" },
        { unidad: "2A", borrador: "52000.00", control: "62000.00", diferencia: "-10000.00" },
      ],
      aceptada_por: "00000000-0000-0000-0000-000000000101",
      aceptada_en: "2026-11-12T15:00:00+00:00",
    });
  });
}

function json(respuesta: ServerResponse, estado: number, cuerpo: unknown): void {
  respuesta.writeHead(estado, { "content-type": "application/json" }).end(JSON.stringify(cuerpo));
}

/** Contesta `importaciones` y `importaciones/plantilla` de los tres edificios del contrato. */
export function responderImportacion(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  guardar: (escritura: EscrituraRecibida) => void,
): void {
  const metodo = pedido.method ?? "GET";
  if (resto === "importaciones/plantilla") {
    if (metodo !== "GET") {
      respuesta.writeHead(405).end();
      return;
    }
    respuesta
      .writeHead(200, {
        "content-type": _XLSX,
        "content-disposition": 'attachment; filename="plantilla-padron.xlsx"',
      })
      .end(readFileSync(_PLANTILLA));
    return;
  }
  if (metodo !== "POST") {
    respuesta.writeHead(405).end();
    return;
  }
  const trozos: Buffer[] = [];
  pedido.on("data", (trozo: Buffer) => {
    trozos.push(trozo);
  });
  pedido.on("end", () => {
    const contentType = String(pedido.headers["content-type"] ?? "");
    guardar({
      metodo,
      url: pedido.url ?? "",
      contentType,
      cuerpo: Buffer.concat(trozos).toString("utf8"),
    });
    // Como la real: sin multipart no hay `archivo` (422 de FastAPI, antes de cualquier regla).
    if (!/^multipart\/form-data/.test(contentType)) {
      json(respuesta, 422, { detail: [{ type: "missing", loc: ["body", "archivo"] }] });
      return;
    }
    if (id === IMPORTACION_SIN_PERMISO) {
      json(respuesta, 403, {
        detail: {
          codigo: "sin_permiso",
          detalle: "sin_permiso",
          permiso_faltante: "importar_padron_y_saldos",
        },
      });
      return;
    }
    if (id === IMPORTACION_RECHAZADA) {
      json(respuesta, 422, {
        detail: [
          { hoja: "Unidades", fila: 9, columna: "Piso", motivo: "El piso no está en el edificio." },
          { hoja: "Unidades", fila: 3, columna: "Tipo", motivo: "El tipo no es válido." },
          {
            hoja: "Unidades",
            fila: 7,
            columna: "Superficie m2",
            motivo: "La superficie tiene que ser mayor que cero.",
          },
        ],
      });
      return;
    }
    json(respuesta, 201, {
      importacion_id: "00000000-0000-0000-0000-0000000007a1",
      unidades_creadas: 12,
      propietarios_creados: 10,
      propietarios_reusados: 0,
      filas_de_saldo: 0,
      advertencias: [],
    });
  });
}
