/**
 * Mis pagos (change 8, H-025): lee el edificio (para el nombre del menú) y los pagos en paralelo. No
 * escribe nada: abrir la pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { pagosDelEdificio } from "../../../../lib/api/pagos";
import { PantallaMisPagos } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaMisPagos({ params }: Props) {
  const { id } = await params;
  const [edificio, pagos] = await Promise.all([edificioPorId(id), pagosDelEdificio(id)]);

  if (edificio.estado === "sin_sesion" || pagos.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe" || pagos.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (pagos.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver los pagos de este edificio"
        permisoFaltante={pagos.permiso}
      />
    );
  }
  if (pagos.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar tus pagos." />;
  }

  return (
    <PantallaMisPagos
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      pagos={pagos.datos}
    />
  );
}
