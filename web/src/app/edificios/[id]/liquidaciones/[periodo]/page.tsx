/**
 * Preliquidación de un período (change 7, H-011): lee el edificio (para el nombre del menú) y la
 * preliquidación en paralelo; la acción de emitir (H-013) se liga al edificio y al período acá. El segmento de la dirección es `AAAA-MM` (`2026-11`); a la API se le
 * pide el día 1 (`2026-11-01`). No escribe nada: abrir la pantalla es sólo mirar.
 */

import { notFound } from "next/navigation";
import { ErrorDePantalla } from "../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../lib/api/edificios";
import { preliquidacionDelPeriodo } from "../../../../../lib/api/liquidaciones";
import { periodoEnPalabras } from "../../../../../lib/formato";
import { emitirLiquidacionAction } from "./acciones";
import { PantallaPreliquidacion, PantallaSinPreliquidar } from "./Pantalla";

type Props = {
  params: Promise<{ id: string; periodo: string }>;
};

export default async function PaginaPreliquidacion({ params }: Props) {
  const { id, periodo } = await params;
  const enPalabras = periodoEnPalabras(periodo);
  if (enPalabras === null || periodo.length !== 7) {
    notFound();
  }
  const [edificio, preliquidacion] = await Promise.all([
    edificioPorId(id),
    preliquidacionDelPeriodo(id, `${periodo}-01`),
  ]);

  if (edificio.estado === "sin_sesion" || preliquidacion.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (edificio.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver este edificio"
        permisoFaltante={edificio.permiso}
      />
    );
  }
  if (preliquidacion.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver la preliquidación de este edificio"
        permisoFaltante={preliquidacion.permiso}
      />
    );
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  if (preliquidacion.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (preliquidacion.estado === "conflicto") {
    return (
      <PantallaSinPreliquidar
        id={id}
        nombreEdificio={nombreEdificio}
        periodoEnPalabras={enPalabras}
        campo={preliquidacion.campo}
        motivo={preliquidacion.motivo ?? ""}
      />
    );
  }
  if (preliquidacion.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la preliquidación." />;
  }

  return (
    <PantallaPreliquidacion
      id={id}
      nombreEdificio={nombreEdificio}
      periodoEnPalabras={enPalabras}
      preliquidacion={preliquidacion.datos}
      accionEmitir={emitirLiquidacionAction.bind(null, id, `${periodo}-01`)}
    />
  );
}
