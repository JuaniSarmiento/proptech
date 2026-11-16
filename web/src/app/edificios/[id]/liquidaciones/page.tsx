/**
 * Lista de liquidaciones del edificio (change 7, H-017): lee el edificio (para el nombre del menú)
 * y la lista en paralelo. No escribe nada: abrir la pantalla es sólo mirar.
 */

import { ErrorDePantalla } from "../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { edificioPorId } from "../../../../lib/api/edificios";
import { liquidacionesDelEdificio } from "../../../../lib/api/liquidaciones";
import { PantallaListaDeLiquidaciones } from "./Lista";
import { periodoParaPreparar } from "./periodos";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PaginaListaDeLiquidaciones({ params }: Props) {
  const { id } = await params;
  const [edificio, lista] = await Promise.all([edificioPorId(id), liquidacionesDelEdificio(id)]);

  if (edificio.estado === "sin_sesion" || lista.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (edificio.estado === "no_existe" || lista.estado === "no_existe") {
    return <Estados tipo="noExiste" />;
  }
  if (lista.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver las liquidaciones de este edificio"
        permisoFaltante={lista.permiso}
      />
    );
  }
  if (lista.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar las liquidaciones." />;
  }

  return (
    <PantallaListaDeLiquidaciones
      id={id}
      nombreEdificio={edificio.estado === "ok" ? edificio.datos.nombre : "Edificio"}
      liquidaciones={lista.datos}
      periodoParaPreparar={periodoParaPreparar(lista.datos)}
    />
  );
}
