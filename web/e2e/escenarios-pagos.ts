/**
 * Pagos informados (change 8, H-025), a pedido de la API falsa: dos edificios del contrato
 * (`aceptacion/H-025/CONTRATO.md`, "API falsa"). Contestan las rutas de pagos como la API real; las
 * lecturas de la pantalla (edificio, resumen) las contesta la API falsa como a cualquier edificio.
 *
 * - 2501: la lectura del comprobante da `ok` (Banco Nación, 12345678, 2026-11-05, 43350.00, sin CBU, con
 *   el comprobante `...025900`).
 * - 2502: igual, pero la lectura da `fallida` con la propuesta vacía.
 *
 * `GET .../pagos/unidades`: para `user_vecina`, `1A` y `2B`; para el resto, las cuatro. `GET .../pagos`:
 * cinco pagos, uno por estado y un quinto confirmado y reimputado de `1A` a `2A` (H-026); cada parte trae
 * `unidad_vigente_id` e `identificador_vigente`. `POST .../pagos` da 201 si las partes suman el monto y 422 `partes` si no.
 * Confirmar, rechazar, revertir, reimputar y el enlace del comprobante responden como la API real
 * (409 `pago`/`estado` si el estado no lo admite). Todas las escrituras guardan la última escritura (de
 * la subida del comprobante sólo se guarda el método, la dirección y el tipo, nunca los bytes).
 */

import type { IncomingMessage, ServerResponse } from "node:http";
import { TOKEN_DE_PRUEBA } from "./escenarios-liquidacion";

export const PAGOS_CON_LECTURA = "00000000-0000-0000-0000-000000002501";
export const PAGOS_SIN_LECTURA = "00000000-0000-0000-0000-000000002502";

export const COMPROBANTE_LEIDO = "00000000-0000-0000-0000-000000025900";

const _UNIDADES = {
  "1A": "00000000-0000-0000-0000-000000025101",
  "1B": "00000000-0000-0000-0000-000000025102",
  "2A": "00000000-0000-0000-0000-000000025103",
  "2B": "00000000-0000-0000-0000-000000025104",
};

const _IDS = new Set([PAGOS_CON_LECTURA, PAGOS_SIN_LECTURA]);

export function esEdificioDePagos(id: string): boolean {
  return _IDS.has(id);
}

/** La acción que la sesión de `user_vecina` trae en estos dos edificios (y ninguna más). */
export const ACCIONES_DE_LA_VECINA: Record<string, string[]> = {
  [PAGOS_CON_LECTURA]: ["informar_pago"],
  [PAGOS_SIN_LECTURA]: ["informar_pago"],
};

const _PAGO_INFORMADO = "00000000-0000-0000-0000-000000025001";
const _PAGO_CONFIRMADO = "00000000-0000-0000-0000-000000025002";
const _PAGO_RECHAZADO = "00000000-0000-0000-0000-000000025003";
const _PAGO_REVERTIDO = "00000000-0000-0000-0000-000000025004";
const _PAGO_REIMPUTADO = "00000000-0000-0000-0000-000000025005";

function _pago(
  pagoId: string,
  estado: string,
  motivo: string | null,
  numero: string,
  monto: string,
  unidad: keyof typeof _UNIDADES,
  vigente: keyof typeof _UNIDADES = unidad,
) {
  return {
    pago_id: pagoId,
    estado,
    motivo,
    banco: "Banco Nación",
    numero_de_operacion: numero,
    fecha_de_transferencia: "2026-11-05",
    monto,
    comprobante_id: COMPROBANTE_LEIDO,
    informado_por: "00000000-0000-0000-0000-000000025800",
    informado_en: "2026-11-06T15:00:00+00:00",
    partes: [
      {
        unidad_id: _UNIDADES[unidad],
        identificador: unidad,
        importe: monto,
        unidad_vigente_id: _UNIDADES[vigente],
        identificador_vigente: vigente,
      },
    ],
  };
}

const _PAGOS = [
  _pago(_PAGO_INFORMADO, "informado", null, "11110001", "43350.00", "1A"),
  _pago(_PAGO_CONFIRMADO, "confirmado", null, "11110002", "37425.00", "2B"),
  _pago(
    _PAGO_RECHAZADO,
    "rechazado",
    "El monto no coincide con el comprobante",
    "11110003",
    "10000.00",
    "1A",
  ),
  _pago(_PAGO_REVERTIDO, "revertido", "Cheque rechazado", "11110004", "20000.00", "1B"),
  // H-026: confirmado y reimputado de 1A a 2A (la plata está hoy en 2A).
  _pago(_PAGO_REIMPUTADO, "confirmado", null, "11110005", "10000.00", "1A", "2A"),
];

function json(respuesta: ServerResponse, estado: number, cuerpo: unknown): void {
  respuesta.writeHead(estado, { "content-type": "application/json" }).end(JSON.stringify(cuerpo));
}

const _MONTO = /^[0-9]+\.[0-9]{2}$/;

/** Centavos de un texto `123.45`, o `null` si no lo es. La API falsa suma enteros, nunca flotantes. */
function centavos(texto: unknown): bigint | null {
  return typeof texto === "string" && _MONTO.test(texto) ? BigInt(texto.replace(".", "")) : null;
}

function conflicto(respuesta: ServerResponse): void {
  json(respuesta, 409, { detail: "conflicto", campo: "pago", motivo: "estado" });
}

function invalido(respuesta: ServerResponse, campo: string): void {
  json(respuesta, 422, { detail: [{ type: "value_error", loc: ["body", campo] }] });
}

/** Qué responde `POST .../pagos` a un cuerpo: 201 si las partes suman el monto, 422 `partes` si no. */
function informar(respuesta: ServerResponse, cuerpo: string): void {
  let datos: Record<string, unknown>;
  try {
    datos = JSON.parse(cuerpo) as Record<string, unknown>;
  } catch {
    json(respuesta, 422, { detail: [{ type: "json_invalid", loc: ["body"] }] });
    return;
  }
  const monto = centavos(datos.monto);
  if (monto === null) {
    invalido(respuesta, "monto");
    return;
  }
  const partes = Array.isArray(datos.partes) ? (datos.partes as Record<string, unknown>[]) : [];
  const importes = partes.map((parte) => centavos(parte.importe));
  if (partes.length === 0 || importes.includes(null)) {
    invalido(respuesta, "partes");
    return;
  }
  const suma = importes.reduce<bigint>((total, importe) => total + (importe ?? 0n), 0n);
  if (suma !== monto) {
    invalido(respuesta, "partes");
    return;
  }
  json(respuesta, 201, { pago_id: "00000000-0000-0000-0000-000000025099", estado: "informado" });
}

/**
 * Contesta las rutas de pagos de los dos edificios del contrato. Devuelve `false` si no es de su
 * incumbencia. `guardar` recibe cada escritura cruda (la última gana).
 */
export function responderPagos(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  identidad: string,
  guardar: (escritura: {
    metodo: string;
    url: string;
    contentType: string;
    cuerpo: string;
  }) => void,
): boolean {
  const metodo = pedido.method ?? "GET";
  if (metodo === "GET" && resto === "pagos/unidades") {
    const nombres = identidad === "user_vecina" ? ["1A", "2B"] : ["1A", "1B", "2A", "2B"];
    json(
      respuesta,
      200,
      nombres.map((n) => ({ unidad_id: _UNIDADES[n as keyof typeof _UNIDADES], identificador: n })),
    );
    return true;
  }
  if (metodo === "GET" && resto === "pagos") {
    json(respuesta, 200, _PAGOS);
    return true;
  }
  const accion = /^pagos\/([^/]+)\/(confirmacion|rechazo|reversion|reimputacion)$/.exec(resto);
  const enlace = /^pagos\/([^/]+)\/comprobante\/enlace$/.exec(resto);
  if (metodo === "POST" && (resto === "pagos" || resto === "pagos/lectura" || accion || enlace)) {
    const trozos: Buffer[] = [];
    pedido.on("data", (trozo: Buffer) => {
      trozos.push(trozo);
    });
    pedido.on("end", () => {
      const crudo = Buffer.concat(trozos).toString("utf8");
      const contentType = String(pedido.headers["content-type"] ?? "");
      const esSubida = resto === "pagos/lectura";
      guardar({
        metodo: "POST",
        url: pedido.url ?? "",
        contentType,
        cuerpo: esSubida ? "" : crudo,
      });
      if (esSubida) {
        const fallida = id === PAGOS_SIN_LECTURA;
        json(respuesta, 201, {
          comprobante_id: COMPROBANTE_LEIDO,
          lectura: fallida ? "fallida" : "ok",
          propuesta: fallida
            ? { banco: null, numero_de_operacion: null, fecha: null, monto: null, cbu_origen: null }
            : {
                banco: "Banco Nación",
                numero_de_operacion: "12345678",
                fecha: "2026-11-05",
                monto: "43350.00",
                cbu_origen: null,
              },
        });
        return;
      }
      if (resto === "pagos") {
        informar(respuesta, crudo);
        return;
      }
      const pagoId = (accion ?? enlace)?.[1] ?? "";
      const pago = _PAGOS.find((p) => p.pago_id === pagoId);
      if (!pago) {
        json(respuesta, 404, { detail: "no encontrado" });
        return;
      }
      if (enlace) {
        json(respuesta, 201, {
          url: `/api/comprobantes/descarga?token=${TOKEN_DE_PRUEBA}`,
          vence_en: "2026-11-18T15:15:00+00:00",
        });
        return;
      }
      const tipo = accion?.[2] ?? "";
      let cuerpo: Record<string, unknown> = {};
      try {
        cuerpo = crudo === "" ? {} : (JSON.parse(crudo) as Record<string, unknown>);
      } catch {
        json(respuesta, 422, { detail: [{ type: "json_invalid", loc: ["body"] }] });
        return;
      }
      const motivo = typeof cuerpo.motivo === "string" ? cuerpo.motivo.trim() : "";
      if (tipo !== "confirmacion" && (motivo.length < 3 || motivo.length > 500)) {
        invalido(respuesta, "motivo");
        return;
      }
      if (tipo === "reimputacion") {
        const mala =
          typeof cuerpo.desde_unidad_id !== "string"
            ? "desde_unidad_id"
            : typeof cuerpo.hacia_unidad_id !== "string" ||
                cuerpo.desde_unidad_id === cuerpo.hacia_unidad_id
              ? "hacia_unidad_id"
              : null;
        if (mala !== null) {
          invalido(respuesta, mala);
          return;
        }
      }
      const admite =
        tipo === "confirmacion" || tipo === "rechazo"
          ? pago.estado === "informado"
          : pago.estado === "confirmado";
      if (!admite) {
        conflicto(respuesta);
        return;
      }
      const estado = { confirmacion: "confirmado", rechazo: "rechazado", reversion: "revertido" }[
        tipo
      ];
      json(respuesta, 200, { pago_id: pagoId, estado: estado ?? pago.estado });
    });
    return true;
  }
  return false;
}
