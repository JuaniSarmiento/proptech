/**
 * Lo que muestra cada pantalla del portal cuando la API no contesta `ok`: sin sesión o un fallo
 * (un 403 de estas rutas no existe: el portal es de quien tiene unidades). Una unidad o liquidación que no es de la persona (404) o un id mal formado es un 404 de la
 * pantalla (`notFound()`), sin ningún dato (N01). Devuelve `null` si el resultado es `ok`.
 */

import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { ErrorDePantalla } from "../../componentes/ErrorDePantalla";
import { Estados } from "../../componentes/Estados";
import type { ResultadoApi } from "../../lib/api/cliente";

export function pantallaDeError(
  resultados: ResultadoApi<unknown>[],
  mensajeDeFallo: string,
): ReactNode | null {
  if (resultados.some((r) => r.estado === "no_existe")) notFound();
  if (resultados.some((r) => r.estado === "sin_sesion")) return <Estados tipo="sinSesion" />;
  if (resultados.some((r) => r.estado !== "ok"))
    return <ErrorDePantalla mensaje={mensajeDeFallo} />;
  return null;
}
