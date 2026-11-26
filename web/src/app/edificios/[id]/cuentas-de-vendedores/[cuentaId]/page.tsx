/**
 * La cuenta de un vendedor (change 4d, H-034): lee el edificio (para el nombre del menú) y el detalle de
 * la cuenta en paralelo; el cobro se liga al edificio y a la cuenta acá.
 */

import { ErrorDePantalla } from "../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../lib/api/edificios";
import { cuentaDeVendedor } from "../../../../../lib/api/titularidad";
import { registrarCobroAction } from "./acciones";
import { PantallaCuentaDeVendedor } from "./Pantalla";

type Props = {
  params: Promise<{ id: string; cuentaId: string }>;
};

export default async function PaginaCuentaDeVendedor({ params }: Props) {
  const { id, cuentaId } = await params;
  const [edificio, cuenta] = await Promise.all([edificioPorId(id), cuentaDeVendedor(id, cuentaId)]);

  if (edificio.estado === "sin_sesion" || cuenta.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe" || cuenta.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (cuenta.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver esta cuenta de vendedor"
        permisoFaltante={cuenta.permiso}
      />
    );
  }
  if (cuenta.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la cuenta del vendedor." />;
  }

  return (
    <PantallaCuentaDeVendedor
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      cuenta={cuenta.datos}
      accionCobrar={registrarCobroAction.bind(null, id, cuentaId)}
    />
  );
}
