/**
 * Ajustar el saldo inicial de una unidad (change 5, H-010, D11): lee el resumen (para
 * `estado_migracion`), el edificio (para el nombre del menú) y el padrón (para saber qué unidad es
 * y que sea de este edificio) en paralelo; la acción se liga al edificio y a la unidad acá.
 */

import { ErrorDePantalla } from "../../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../../lib/api/edificios";
import { resumenDelEdificio } from "../../../../../../lib/api/resumen";
import { padronDelEdificio } from "../../../../../../lib/api/unidades";
import { ajustarSaldoInicialAction } from "./acciones";
import { PantallaAjuste } from "./Pantalla";

type Props = {
  params: Promise<{ id: string; unidadId: string }>;
};

export default async function PaginaAjuste({ params }: Props) {
  const { id, unidadId } = await params;
  const [edificio, resumen, padron] = await Promise.all([
    edificioPorId(id),
    resumenDelEdificio(id),
    padronDelEdificio(id),
  ]);

  if (resumen.estado === "sin_sesion" || padron.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (resumen.estado === "no_existe" || padron.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (resumen.estado === "sin_permiso") {
    return (
      <Estados tipo="sinPermiso" queNoPuede="ver este edificio" permisoFaltante={resumen.permiso} />
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
  if (resumen.estado !== "ok" || padron.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la unidad." />;
  }

  const unidad = padron.datos.unidades.find((candidata) => candidata.id === unidadId);
  if (!unidad) {
    return <Estados tipo="noExiste" />;
  }
  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  return (
    <PantallaAjuste
      id={id}
      nombreEdificio={nombreEdificio}
      identificadorDeUnidad={unidad.identificador}
      estadoMigracion={resumen.datos.estado_migracion}
      accionAjustar={ajustarSaldoInicialAction.bind(null, id, unidadId)}
    />
  );
}
