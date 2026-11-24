/**
 * La morosidad (change 10a, H-029), a pedido de la API falsa: dos edificios del contrato
 * (`aceptacion/H-029/CONTRATO.md`, "API falsa"). Contestan `GET .../morosidad` y `GET .../morosidad/excel`
 * como la API real; el resto (edificio, resumen) lo contesta la API falsa como a cualquier edificio.
 *
 * - 2701 "Torre Ficticia": cuatro filas y un total del resumen un centavo MÁS que la suma de las filas, a
 *   propósito: la pantalla muestra el de la API y nunca lo recalcula (N03).
 * - 2702 "Edificio al día": sin filas, sin fecha de intereses y el resumen en cero.
 *
 * Las dos rutas dan 403 con `permiso_faltante` a quien no tiene la acción: `user_vecina` no trae ninguna
 * de las dos; `user_consejo` trae `ver_morosidad` pero no `exportar_morosidad`. El super admin trae las
 * dos en todos los edificios (`_ACCIONES_DE_SUPER_ADMIN` de `api-falsa.ts`).
 */

import type { IncomingMessage, ServerResponse } from "node:http";

export const MOROSIDAD_CON_DEUDA = "00000000-0000-0000-0000-000000002701";
export const MOROSIDAD_AL_DIA = "00000000-0000-0000-0000-000000002702";

const _IDS = new Set([MOROSIDAD_CON_DEUDA, MOROSIDAD_AL_DIA]);

export function esEdificioDeMorosidad(id: string): boolean {
  return _IDS.has(id);
}

/** Las acciones de `user_consejo` en estos dos edificios (y ninguna más). */
const _DEL_CONSEJO = ["ver_configuracion_del_edificio", "ver_liquidaciones", "ver_morosidad"];
export const ACCIONES_DEL_CONSEJO: Record<string, string[]> = {
  [MOROSIDAD_CON_DEUDA]: _DEL_CONSEJO,
  [MOROSIDAD_AL_DIA]: _DEL_CONSEJO,
};

/** Las acciones de la morosidad que trae cada identidad (el super admin trae las dos). */
function accionesDe(identidad: string): string[] {
  if (identidad === "user_vecina") return [];
  if (identidad === "user_consejo") return ["ver_morosidad"];
  return ["ver_morosidad", "exportar_morosidad"];
}

const _FILA = (
  unidad: string,
  sufijo: string,
  propietarios: string[],
  etiqueta: string,
  total: string,
  capital: string,
  intereses: string,
  liquidaciones: number,
  desde: string,
  dias: number,
) => ({
  unidad_id: `00000000-0000-0000-0000-000000027${sufijo}`,
  unidad,
  propietarios,
  etiqueta,
  total_vencido: total,
  capital,
  intereses,
  liquidaciones_vencidas: liquidaciones,
  vencida_desde: desde,
  dias,
});

const _CON_DEUDA = {
  fecha: "2026-11-18",
  intereses_al: "2026-10-31",
  // 30812.34 + 40000.00 + 8000.00 + 300.00 = 79112.34: el resumen dice un centavo más a propósito.
  resumen: { unidades_con_deuda: 4, morosos_criticos: 1, total_vencido: "79112.35" },
  unidades: [
    _FILA(
      "1A",
      "101",
      ["Ana Prueba"],
      "moroso_critico",
      "30812.34",
      "30000.00",
      "812.34",
      3,
      "2026-09-10",
      69,
    ),
    _FILA(
      "1B",
      "102",
      ["Carla Prueba"],
      "con_deuda_vencida",
      "40000.00",
      "40000.00",
      "0.00",
      1,
      "2026-11-10",
      8,
    ),
    _FILA(
      "2B",
      "104",
      ["Ana Prueba"],
      "con_deuda_vencida",
      "8000.00",
      "8000.00",
      "0.00",
      1,
      "2026-11-10",
      8,
    ),
    _FILA("2A", "103", [], "bajo_umbral", "300.00", "300.00", "0.00", 1, "2026-11-10", 8),
  ],
};

const _AL_DIA = {
  fecha: "2026-11-18",
  intereses_al: null,
  resumen: { unidades_con_deuda: 0, morosos_criticos: 0, total_vencido: "0.00" },
  unidades: [],
};

function json(respuesta: ServerResponse, estado: number, cuerpo: unknown): void {
  respuesta.writeHead(estado, { "content-type": "application/json" }).end(JSON.stringify(cuerpo));
}

function sinPermiso(respuesta: ServerResponse, permiso: string): void {
  json(respuesta, 403, {
    detail: { codigo: "sin_permiso", detalle: "sin_permiso", permiso_faltante: permiso },
  });
}

/** Unos bytes que empiezan como un .xlsx (un zip): `PK\x03\x04`. */
const _XLSX = Buffer.concat([
  Buffer.from([0x50, 0x4b, 0x03, 0x04]),
  Buffer.from("excel de prueba"),
]);

/**
 * Contesta las rutas de la morosidad de los dos edificios del contrato. Devuelve `false` si no es de su
 * incumbencia.
 */
export function responderMorosidad(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  identidad: string,
): boolean {
  // La aceptación abre `liquidaciones` para ver el menú: sin liquidaciones emitidas, una lista vacía.
  if (resto === "liquidaciones" && pedido.method === "GET") {
    json(respuesta, 200, []);
    return true;
  }
  if (resto !== "morosidad" && resto !== "morosidad/excel") {
    return false;
  }
  if (pedido.method !== "GET") {
    respuesta.writeHead(405).end();
    return true;
  }
  const acciones = accionesDe(identidad);
  if (resto === "morosidad") {
    if (!acciones.includes("ver_morosidad")) {
      sinPermiso(respuesta, "ver_morosidad");
      return true;
    }
    json(respuesta, 200, id === MOROSIDAD_CON_DEUDA ? _CON_DEUDA : _AL_DIA);
    return true;
  }
  if (!acciones.includes("exportar_morosidad")) {
    sinPermiso(respuesta, "exportar_morosidad");
    return true;
  }
  respuesta
    .writeHead(200, {
      "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "content-disposition": 'attachment; filename="morosidad-torre-ficticia-2026-11-18.xlsx"',
    })
    .end(_XLSX);
  return true;
}
