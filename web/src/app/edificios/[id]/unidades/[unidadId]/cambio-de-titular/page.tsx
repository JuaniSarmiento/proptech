/**
 * Cambiar titular de una unidad (change 4d, H-034): lee los cambios anteriores (que además decide el
 * permiso `registrar_cambio_de_titular`), el padrón (para saber qué unidad es) y `/api/personal` (los
 * propietarios actuales y los nombres de los vendedores del historial). La acción se liga al edificio y a
 * la unidad acá.
 */

import { ErrorDePantalla } from "../../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../../lib/api/edificios";
import { listarPersonal } from "../../../../../../lib/api/personal";
import { cambiosDeUnaUnidad } from "../../../../../../lib/api/titularidad";
import { padronDelEdificio } from "../../../../../../lib/api/unidades";
import { registrarCambioAction } from "./acciones";
import { PantallaCambioDeTitular } from "./Pantalla";

type Props = {
  params: Promise<{ id: string; unidadId: string }>;
};

export default async function PaginaCambioDeTitular({ params }: Props) {
  const { id, unidadId } = await params;
  const [edificio, cambios, padron, personal] = await Promise.all([
    edificioPorId(id),
    cambiosDeUnaUnidad(id, unidadId),
    padronDelEdificio(id),
    listarPersonal(),
  ]);

  if (cambios.estado === "sin_sesion" || padron.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (cambios.estado === "no_existe" || padron.estado === "no_existe") {
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
  if (personal.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver a los propietarios de la unidad"
        permisoFaltante={personal.permiso}
      />
    );
  }
  if (cambios.estado !== "ok" || padron.estado !== "ok" || personal.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la unidad." />;
  }

  const unidad = padron.datos.unidades.find((candidata) => candidata.id === unidadId);
  if (!unidad) {
    return <Estados tipo="noExiste" />;
  }

  const propietarios: { persona_id: string; nombre: string }[] = [];
  for (const persona of personal.datos) {
    const esPropietario = persona.asignaciones.some(
      (a) =>
        a.rol === "vecino" &&
        a.unidad_id === unidadId &&
        (a.vinculo ?? "propietario") === "propietario",
    );
    if (esPropietario)
      propietarios.push({ persona_id: persona.persona_id, nombre: persona.nombre });
  }
  const nombres: Record<string, string> = Object.fromEntries(
    personal.datos.map((persona) => [persona.persona_id, persona.nombre]),
  );

  return (
    <PantallaCambioDeTitular
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      identificadorDeUnidad={unidad.identificador}
      propietarios={propietarios}
      nombres={nombres}
      historial={cambios.datos}
      accionRegistrar={registrarCambioAction.bind(null, id, unidadId)}
    />
  );
}
