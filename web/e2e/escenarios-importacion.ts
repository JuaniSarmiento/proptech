/**
 * Importar el padrón desde Excel (change 5, H-007), a pedido de la API falsa: un UUID fijo por
 * resultado del `POST /api/complejos/{id}/importaciones`. Las lecturas que la pantalla necesita
 * (edificio, resumen) las contesta la API falsa como a cualquier edificio con la migración
 * `pendiente`. La API falsa no lee el Excel: lo que decide el resultado es el id del edificio.
 *
 * Los ids de H-008 a H-010 (comparación, confirmación, ajuste) los suman esas historias.
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
