/**
 * Padrón de unidades (D1, tarea 4.3): lee el padrón y el edificio (para el
 * nombre del menú) en paralelo; las acciones se ligan al `complejoId` acá.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { padronDelEdificio } from "../../../../lib/api/unidades";
import { crearUnidadAction, editarUnidadAction } from "./acciones";
import { PantallaPadron } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaPadron({ params }: Props) {
  const { id } = await params;
  const [edificio, padron] = await Promise.all([edificioPorId(id), padronDelEdificio(id)]);

  if (padron.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (padron.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (padron.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver el padrón de este edificio"
        permisoFaltante={padron.permiso}
      />
    );
  }
  if (padron.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar el padrón de unidades." />;
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  return (
    <PantallaPadron
      id={id}
      nombreEdificio={nombreEdificio}
      unidades={padron.datos.unidades}
      informe={padron.datos.informe}
      accionCrear={crearUnidadAction.bind(null, id)}
      accionEditar={editarUnidadAction.bind(null, id)}
    />
  );
}
