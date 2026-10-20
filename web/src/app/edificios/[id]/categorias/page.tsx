/**
 * Categorías de gasto (D1, tarea 4.5): lee las categorías y el edificio
 * (para el nombre del menú) en paralelo; las cuatro acciones se ligan al
 * `complejoId` acá.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { categoriasDelEdificio } from "../../../../lib/api/categorias";
import { edificioPorId } from "../../../../lib/api/edificios";
import {
  cambiarEstadoCategoriaAction,
  crearCategoriaAction,
  editarCategoriaAction,
  reordenarCategoriasAction,
} from "./acciones";
import { PantallaCategorias } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaCategorias({ params }: Props) {
  const { id } = await params;
  const [edificio, categorias] = await Promise.all([edificioPorId(id), categoriasDelEdificio(id)]);

  if (categorias.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (categorias.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (categorias.estado === "sin_permiso") {
    return <Estados tipo="sinPermiso" queNoPuede="ver las categorías de este edificio" />;
  }
  if (categorias.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar las categorías de gasto." />;
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  return (
    <PantallaCategorias
      id={id}
      nombreEdificio={nombreEdificio}
      categorias={categorias.datos}
      accionCrear={crearCategoriaAction.bind(null, id)}
      accionEditar={editarCategoriaAction.bind(null, id)}
      accionEstado={cambiarEstadoCategoriaAction.bind(null, id)}
      accionReordenar={reordenarCategoriasAction.bind(null, id)}
    />
  );
}
