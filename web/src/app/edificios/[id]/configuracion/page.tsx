/**
 * Intereses y vencimiento (D1, tarea 4.6): lee la vigente, el historial y
 * el edificio (para el nombre del menú) en paralelo; la acción se liga al
 * `complejoId` acá.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { configuracionVigente, versionesDeConfiguracion } from "../../../../lib/api/configuracion";
import { edificioPorId } from "../../../../lib/api/edificios";
import { crearVersionDeConfiguracionAction } from "./acciones";
import { PantallaConfiguracion } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaConfiguracion({ params }: Props) {
  const { id } = await params;
  const [edificio, vigente, historial] = await Promise.all([
    edificioPorId(id),
    configuracionVigente(id),
    versionesDeConfiguracion(id),
  ]);

  if (historial.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (historial.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (historial.estado === "sin_permiso") {
    return <Estados tipo="sinPermiso" queNoPuede="ver la configuración de este edificio" />;
  }
  if (historial.estado !== "ok" || vigente.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar intereses y vencimiento." />;
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  return (
    <PantallaConfiguracion
      id={id}
      nombreEdificio={nombreEdificio}
      vigente={vigente.datos}
      historial={historial.datos}
      accionCrear={crearVersionDeConfiguracionAction.bind(null, id)}
    />
  );
}
