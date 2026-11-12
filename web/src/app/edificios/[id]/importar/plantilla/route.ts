/**
 * Descarga de la plantilla de Excel (change 5, H-007): la pide el servidor de Next a la API con el
 * token de la sesión (D-036) y la entrega como archivo; el navegador nunca ve el token.
 */

import { plantillaDelPadron } from "../../../../../lib/api/importaciones";

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

type Contexto = { params: Promise<{ id: string }> };

export async function GET(_pedido: Request, { params }: Contexto): Promise<Response> {
  const { id } = await params;
  const resultado = await plantillaDelPadron(id);
  if (resultado.estado === "ok") {
    return new Response(resultado.datos, {
      status: 200,
      headers: {
        "Content-Type": XLSX,
        "Content-Disposition": 'attachment; filename="plantilla-padron.xlsx"',
        "Cache-Control": "no-store",
      },
    });
  }
  const estado =
    resultado.estado === "sin_sesion"
      ? 401
      : resultado.estado === "sin_permiso"
        ? 403
        : resultado.estado === "no_existe"
          ? 404
          : 502;
  return new Response(null, { status: estado });
}
