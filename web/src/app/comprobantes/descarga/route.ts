/**
 * Descarga del comprobante de un pago (change 8, H-025): el servidor de Next pide el archivo a la API
 * con el token firmado del enlace y lo entrega para verlo en el navegador. Sin sesión a propósito: el
 * token firmado es la autorización, vence a los 15 minutos y lo verifica la API. El borde no publica
 * `/api/*`, así que el navegador llega acá y nunca a la API (igual que `/documentos/descarga`).
 */

import { descargarComprobante } from "../../../lib/api/pagos";

const _EXTENSION: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "application/pdf": "pdf",
};

export async function GET(pedido: Request): Promise<Response> {
  const token = new URL(pedido.url).searchParams.get("token") ?? "";
  const resultado = await descargarComprobante(token);
  if (resultado.estado === "ok") {
    return new Response(resultado.datos, {
      status: 200,
      headers: {
        "Content-Type": resultado.tipo,
        "Content-Disposition": `inline; filename="comprobante.${_EXTENSION[resultado.tipo] ?? "bin"}"`,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  }
  const estado = resultado.estado === "vencido" ? 410 : resultado.estado === "invalido" ? 403 : 502;
  return new Response(null, { status: estado, headers: { "Cache-Control": "no-store" } });
}
