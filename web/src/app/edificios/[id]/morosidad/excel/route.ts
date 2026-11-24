/**
 * Descarga del Excel de la morosidad (change 10a, H-029): la pide el servidor de Next a la API con el
 * token de la sesión (D-036) y la entrega como archivo, con el nombre que decidió la API; el navegador
 * nunca ve el token.
 */

import { excelDeLaMorosidad } from "../../../../../lib/api/morosidad";

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const _DISPOSICION = /^attachment; filename="[A-Za-z0-9._-]{1,150}"$/;

type Contexto = { params: Promise<{ id: string }> };

export async function GET(_pedido: Request, { params }: Contexto): Promise<Response> {
  const { id } = await params;
  const resultado = await excelDeLaMorosidad(id);
  if (resultado.estado === "ok") {
    const { bytes, disposicion } = resultado.datos;
    return new Response(bytes, {
      status: 200,
      headers: {
        "Content-Type": XLSX,
        "Content-Disposition":
          disposicion !== null && _DISPOSICION.test(disposicion)
            ? disposicion
            : 'attachment; filename="morosidad.xlsx"',
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
  return new Response(null, { status: estado, headers: { "Cache-Control": "no-store" } });
}
