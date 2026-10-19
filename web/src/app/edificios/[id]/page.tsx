/**
 * Resumen del edificio (D1, D5, tarea 4.2): lee el resumen y, en paralelo,
 * la configuración vigente para la línea de datos.
 */

import { ErrorDePantalla } from "../../../componentes/ErrorDePantalla";
import { Estados } from "../../../componentes/Estados";
import { configuracionVigente } from "../../../lib/api/configuracion";
import { resumenDelEdificio } from "../../../lib/api/resumen";
import { PantallaResumen } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaResumen({ params }: Props) {
  const { id } = await params;
  const [resumen, vigente] = await Promise.all([resumenDelEdificio(id), configuracionVigente(id)]);

  if (resumen.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (resumen.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (resumen.estado === "sin_permiso") {
    return <Estados tipo="sinPermiso" queNoPuede="ver este edificio" />;
  }
  if (resumen.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar el resumen de este edificio." />;
  }

  return (
    <PantallaResumen
      id={id}
      resumen={resumen.datos}
      vigente={vigente.estado === "ok" ? vigente.datos : null}
    />
  );
}
