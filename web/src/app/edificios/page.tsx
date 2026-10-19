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
    };
  });

  return <PantallaMisEdificios edificios={edificios} accionCrear={crearEdificioAction} />;
}
