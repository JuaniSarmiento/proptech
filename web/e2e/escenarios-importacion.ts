/**
 * Importar el padrón desde Excel (change 5, H-007), a pedido de la API falsa: un UUID fijo por
 * resultado del `POST /api/complejos/{id}/importaciones`. Las lecturas que la pantalla necesita
 * (edificio, resumen) las contesta la API falsa como a cualquier edificio con la migración
 * `pendiente`. La API falsa no lee el Excel: lo que decide el resultado es el id del edificio.
 *
 * H-008 suma los de la comparación (801 a 803). Los de H-009 y H-010 (confirmación, ajuste) los
 * suman esas historias.
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
