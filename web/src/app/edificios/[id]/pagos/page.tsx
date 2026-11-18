/**
 * Pagos, la bandeja del administrador (change 8, H-025): lee el edificio (para el nombre del menú), los
 * pagos y las unidades (para reimputar) en paralelo; las acciones se ligan al edificio acá. No escribe
 * nada: abrir la pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { pagosDelEdificio, unidadesParaInformar } from "../../../../lib/api/pagos";
import { resolverPagoAction, verComprobanteAction } from "./acciones";
import { PantallaPagos } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaPagos({ params }: Props) {
  const { id } = await params;
  const [edificio, pagos, unidades] = await Promise.all([
    edificioPorId(id),
    pagosDelEdificio(id),
    unidadesParaInformar(id),
  ]);

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
    return <ErrorDePantalla mensaje="No pudimos cargar los pagos." />;
  }

  return (
    <PantallaPagos
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      pagos={pagos.datos}
      unidades={unidades.estado === "ok" ? unidades.datos : []}
      accionResolver={resolverPagoAction.bind(null, id)}
      accionVerComprobante={verComprobanteAction.bind(null, id)}
    />
  );
}
