/**
 * Comparación de saldos del borrador (change 5, H-008, D11): lee el edificio (para el nombre del
 * menú) y la comparación del borrador vigente en paralelo; las acciones de aceptar y de confirmar se
 * ligan al `complejoId` acá. Sin borrador vigente (404 de la comparación con el edificio visible) se dice y
 * se manda a importar.
 */

import { ErrorDePantalla } from "../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { edificioPorId } from "../../../../../lib/api/edificios";
import { comparacionDelBorrador } from "../../../../../lib/api/importaciones";
import { resumenDelEdificio } from "../../../../../lib/api/resumen";
import { aceptarDiferenciasAction, confirmarSaldosAction } from "./acciones";
import { PantallaComparacion, PantallaConfirmada, PantallaSinBorrador } from "./Pantalla";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaComparacion({ params }: Props) {
  const { id } = await params;
  const [edificio, comparacion] = await Promise.all([
    edificioPorId(id),
    comparacionDelBorrador(id),
  ]);

  if (edificio.estado === "sin_sesion" || comparacion.estado === "sin_sesion") {
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
  if (comparacion.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver la comparación de saldos de este edificio"
        permisoFaltante={comparacion.permiso}
      />
    );
  }

  const nombreEdificio = edificio.estado === "ok" ? edificio.datos.nombre : "Edificio";

  if (comparacion.estado === "no_existe") {
    // Confirmado el borrador deja de ser vigente: sin él, el edificio dice si ya está confirmado.
    const resumen = await resumenDelEdificio(id);
    if (resumen.estado === "ok" && resumen.datos.estado_migracion === "confirmada") {
      return <PantallaConfirmada id={id} nombreEdificio={nombreEdificio} />;
    }
    return <PantallaSinBorrador id={id} nombreEdificio={nombreEdificio} />;
  }
  if (comparacion.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar la comparación de saldos." />;
  }

  return (
    <PantallaComparacion
      id={id}
      nombreEdificio={nombreEdificio}
      comparacion={comparacion.datos}
      accionAceptar={aceptarDiferenciasAction.bind(null, id)}
      accionConfirmar={confirmarSaldosAction.bind(null, id)}
    />
  );
}
