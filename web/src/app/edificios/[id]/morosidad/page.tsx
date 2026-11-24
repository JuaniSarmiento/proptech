/**
 * Morosidad del edificio (change 10a, H-029): lee el edificio (para el nombre del menú) y la morosidad
 * en paralelo. No escribe nada: abrir la pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { morosidadDelEdificio } from "../../../../lib/api/morosidad";
import { PantallaMorosidad } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaMorosidad({ params }: Props) {
  const { id } = await params;
  const [edificio, morosidad] = await Promise.all([edificioPorId(id), morosidadDelEdificio(id)]);

  if (edificio.estado === "sin_sesion" || morosidad.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe" || morosidad.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (morosidad.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver la morosidad de este edificio"
        permisoFaltante={morosidad.permiso}
      />
    );
  }
  if (morosidad.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la morosidad." />;
  }

  return (
    <PantallaMorosidad
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      morosidad={morosidad.datos}
    />
  );
}
