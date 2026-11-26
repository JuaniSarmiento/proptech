/**
 * Cambiar titular de una unidad (change 4d, H-034): lee los cambios anteriores (que además decide el
 * permiso `registrar_cambio_de_titular`), el padrón (para saber qué unidad es) y la ruta de propietarios de la
 * unidad (H-035; los nombres de los vendedores del historial vienen con `con_nombres=true`). La acción se liga al edificio y a
 * la unidad acá.
 */

import { ErrorDePantalla } from "../../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../../lib/api/edificios";
import { cambiosDeUnaUnidad, propietariosDeUnaUnidad } from "../../../../../../lib/api/titularidad";
import { padronDelEdificio } from "../../../../../../lib/api/unidades";
import { registrarCambioAction } from "./acciones";
import { PantallaCambioDeTitular } from "./Pantalla";

type Props = {
  params: Promise<{ id: string; unidadId: string }>;
};

export default async function PaginaCambioDeTitular({ params }: Props) {
  const { id, unidadId } = await params;
  const [edificio, cambios, padron, propietarios] = await Promise.all([
    edificioPorId(id),
    cambiosDeUnaUnidad(id, unidadId),
    padronDelEdificio(id),
    propietariosDeUnaUnidad(id, unidadId),
  ]);

  if (
    cambios.estado === "sin_sesion" ||
    padron.estado === "sin_sesion" ||
    propietarios.estado === "sin_sesion"
  ) {
    return <Estados tipo="sinSesion" />;
  }
  if (
    cambios.estado === "no_existe" ||
    padron.estado === "no_existe" ||
    propietarios.estado === "no_existe"
  ) {
    return <Estados tipo="noExiste" />;
  }
  if (cambios.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="cambiar el titular de esta unidad"
        permisoFaltante={cambios.permiso}
      />
    );
  }
  if (padron.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver el padrón de este edificio"
        permisoFaltante={padron.permiso}
      />
    );
  }
  if (propietarios.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver a los propietarios de la unidad"
        permisoFaltante={propietarios.permiso}
      />
    );
  }
  if (cambios.estado !== "ok" || padron.estado !== "ok" || propietarios.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la unidad." />;
  }

  const unidad = padron.datos.unidades.find((candidata) => candidata.id === unidadId);
  if (!unidad) {
    return <Estados tipo="noExiste" />;
  }

  return (
    <PantallaCambioDeTitular
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      identificadorDeUnidad={unidad.identificador}
      propietarios={propietarios.datos}
      historial={cambios.datos}
      accionRegistrar={registrarCambioAction.bind(null, id, unidadId)}
    />
  );
}
