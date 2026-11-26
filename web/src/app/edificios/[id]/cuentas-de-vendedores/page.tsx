/**
 * Cuentas de vendedores (change 4d, H-034): lee el edificio (para el nombre del menú) y las cuentas en
 * paralelo. No escribe nada: abrir la pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { cuentasDeVendedores } from "../../../../lib/api/titularidad";
import { PantallaCuentasDeVendedores } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaCuentasDeVendedores({ params }: Props) {
  const { id } = await params;
  const [edificio, cuentas] = await Promise.all([edificioPorId(id), cuentasDeVendedores(id)]);

  if (edificio.estado === "sin_sesion" || cuentas.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe" || cuentas.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (cuentas.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver las cuentas de vendedores de este edificio"
        permisoFaltante={cuentas.permiso}
      />
    );
  }
  if (cuentas.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar las cuentas de vendedores." />;
  }

  return (
    <PantallaCuentasDeVendedores
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      cuentas={cuentas.datos.cuentas}
    />
  );
}
