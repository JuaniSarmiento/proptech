/**
 * Confirmar "sin saldos previos" (D1, D11, tarea 4.7): lee el resumen (para
 * `estado_migracion`) y el edificio (para el nombre del menú) en paralelo;
 * la acción se liga al `complejoId` acá.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { resumenDelEdificio } from "../../../../lib/api/resumen";
import { confirmarSinSaldosPreviosAction } from "./acciones";
import { PantallaSaldosPrevios } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaSaldosPrevios({ params }: Props) {
  const { id } = await params;
  const [edificio, resumen] = await Promise.all([edificioPorId(id), resumenDelEdificio(id)]);

  if (resumen.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (resumen.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (resumen.estado === "sin_permiso") {
    return (
      <Estados tipo="sinPermiso" queNoPuede="ver este edificio" permisoFaltante={resumen.permiso} />
    );
  }
  if (resumen.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar el estado del edificio." />;
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  return (
    <PantallaSaldosPrevios
      id={id}
      nombreEdificio={nombreEdificio}
      estadoMigracion={resumen.datos.estado_migracion}
      accionConfirmar={confirmarSinSaldosPreviosAction.bind(null, id)}
    />
  );
}
