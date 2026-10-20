/**
 * Grupos de reparto (D1, tarea 4.4): lee grupos, el padrón (para la
 * selección de unidades del panel) y el edificio (para el nombre del
 * menú) en paralelo; las acciones se ligan al `complejoId` y a los ids de
 * unidades disponibles acá.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { gruposDelEdificio } from "../../../../lib/api/grupos";
import { padronDelEdificio } from "../../../../lib/api/unidades";
import { crearGrupoAction, editarGrupoAction } from "./acciones";
import { PantallaGrupos } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaGrupos({ params }: Props) {
  const { id } = await params;
  const [edificio, grupos, padron] = await Promise.all([
    edificioPorId(id),
    gruposDelEdificio(id),
    padronDelEdificio(id),
  ]);

  if (grupos.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (grupos.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (grupos.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver los grupos de este edificio"
        permisoFaltante={grupos.permiso}
      />
    );
  }
  if (grupos.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar los grupos de reparto." />;
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";
  const unidadesDisponibles = padron.estado === "ok" ? padron.datos.unidades : [];
  const idsDisponibles = unidadesDisponibles.map((u) => u.id);

  return (
    <PantallaGrupos
      id={id}
      nombreEdificio={nombreEdificio}
      grupos={grupos.datos}
      unidadesDisponibles={unidadesDisponibles}
      accionCrear={crearGrupoAction.bind(null, id, idsDisponibles)}
      accionEditar={editarGrupoAction.bind(null, id, idsDisponibles)}
    />
  );
}
