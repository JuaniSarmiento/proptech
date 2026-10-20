/**
 * "Mis edificios" (D1, D5, D11, tarea 4.1): lee la lista y, en paralelo, el
 * resumen de cada edificio para la columna de estados — ninguna regla de
 * negocio se calcula acá.
 */

import { ErrorDePantalla } from "../../componentes/ErrorDePantalla";
import { Estados } from "../../componentes/Estados";
import { listaDeEdificios } from "../../lib/api/edificios";
import { resumenDelEdificio } from "../../lib/api/resumen";
import { crearEdificioAction } from "./acciones";
import { type EdificioConEstado, PantallaMisEdificios } from "./Pantalla";

/**
 * SIN esto, Next.js intenta pre-renderizar esta ruta en `next build`
 * porque no tiene segmento dinámico (`[id]`), y la cachea como página
 * estática con lo que haya dado el `fetch` en ESE momento del build —
 * antes de que la API (o la API falsa) esté levantada. Gotcha real, visto
 * en Playwright (bloque C, 4.1): `next start` servía para siempre "No
 * pudimos cargar tus edificios.", la respuesta congelada de un `fetch`
 * fallido en build time, sin volver a pedir nada en ningún request real.
 * Las rutas `/edificios/[id]/...` no lo necesitan: el segmento dinámico
 * ya las vuelve dinámicas por sí solo.
 */
export const dynamic = "force-dynamic";

export default async function PaginaMisEdificios() {
  const lista = await listaDeEdificios();

  if (lista.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (lista.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar tus edificios." />;
  }

  const resumenes = await Promise.all(
    lista.datos.map((edificio) => resumenDelEdificio(edificio.id)),
  );

  const edificios: EdificioConEstado[] = lista.datos.map((edificio, indice) => {
    const resumen = resumenes[indice];
    if (!resumen || resumen.estado !== "ok") {
      return {
        id: edificio.id,
        nombre: edificio.nombre,
        localidad: edificio.localidad,
        cantidadUnidades: null,
        estadoCoeficientes: null,
        diferencia: null,
        estadoMigracion: null,
      };
    }
    return {
      id: edificio.id,
      nombre: edificio.nombre,
      localidad: edificio.localidad,
      cantidadUnidades: resumen.datos.cantidad_unidades,
      estadoCoeficientes: resumen.datos.informe.estado,
      diferencia: resumen.datos.informe.diferencia,
      estadoMigracion: resumen.datos.estado_migracion,
      pasosHechos: Object.values(resumen.datos.pasos).filter((paso) => paso === "hecho").length,
      listoParaLiquidar: resumen.datos.listo_para_liquidar,
    };
  });

  return <PantallaMisEdificios edificios={edificios} accionCrear={crearEdificioAction} />;
}
