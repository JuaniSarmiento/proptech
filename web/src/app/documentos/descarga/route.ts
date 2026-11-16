/**
 * Descarga del PDF de la expensa (change 7, H-015): el servidor de Next pide el PDF a la API con el
 * token firmado del enlace y lo entrega como archivo. Sin sesión a propósito: el token firmado es la
 * autorización (E13), vence a los 15 minutos y lo verifica la API. El borde no publica `/api/*`, así
 * que el navegador llega acá y nunca a la API.
 */

import { descargarDocumento } from "../../../lib/api/documentos";

export async function GET(pedido: Request): Promise<Response> {
  const token = new URL(pedido.url).searchParams.get("token") ?? "";
  const resultado = await descargarDocumento(token);
  if (resultado.estado === "ok") {
    return new Response(resultado.datos, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": 'attachment; filename="expensa.pdf"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  }
  const estado = resultado.estado === "vencido" ? 410 : resultado.estado === "invalido" ? 403 : 502;
  return new Response(null, { status: estado, headers: { "Cache-Control": "no-store" } });
}
