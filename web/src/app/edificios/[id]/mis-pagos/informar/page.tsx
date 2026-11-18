/**
 * Informar un pago (change 8, H-025): lee el edificio (para el nombre del menú) y las unidades por las
 * que la persona puede informar; las acciones se ligan al edificio acá. No escribe nada: abrir la
 * pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../lib/api/edificios";
import { unidadesParaInformar } from "../../../../../lib/api/pagos";
import { enviarPagoAction, leerComprobanteAction } from "./acciones";
import { PantallaInformarPago } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaInformarPago({ params }: Props) {
  const { id } = await params;
  const [edificio, unidades] = await Promise.all([edificioPorId(id), unidadesParaInformar(id)]);

  if (edificio.estado === "sin_sesion" || unidades.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe" || unidades.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (unidades.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="informar pagos en este edificio"
        permisoFaltante={unidades.permiso}
      />
    );
  }
  if (unidades.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar tus unidades." />;
  }

  return (
    <PantallaInformarPago
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      unidades={unidades.datos}
      accionLeer={leerComprobanteAction.bind(null, id)}
      accionEnviar={enviarPagoAction.bind(null, id)}
    />
  );
}
