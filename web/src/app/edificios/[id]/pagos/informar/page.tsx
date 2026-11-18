/**
 * Informar un pago desde la bandeja (change 8, H-026): el administrador informa por un vecino con la misma
 * pantalla de H-025, con todas las unidades del edificio, y al enviar vuelve a la bandeja. Pide
 * `confirmar_pago_informado` (la pantalla lo mira en la sesión; la API lo exige igual). No escribe nada:
 * abrir la pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../lib/api/edificios";
import { unidadesParaInformar } from "../../../../../lib/api/pagos";
import {
  enviarPagoDesdeLaBandejaAction,
  leerComprobanteAction,
} from "../../mis-pagos/informar/acciones";
import { PantallaInformarPago } from "../../mis-pagos/informar/Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaInformarPagoDesdeLaBandeja({ params }: Props) {
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
    return <ErrorDePantalla mensaje="No pudimos cargar las unidades." />;
  }

  return (
    <PantallaInformarPago
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      unidades={unidades.datos}
      desde="pagos"
      accionLeer={leerComprobanteAction.bind(null, id)}
      accionEnviar={enviarPagoDesdeLaBandejaAction.bind(null, id)}
    />
  );
}
