/**
 * Preliquidación de un período (change 7, H-011): lee el edificio (para el nombre del menú) y la
 * preliquidación en paralelo; la acción de emitir (H-013) se liga al edificio y al período acá. Con el
 * período ya emitido (409 `periodo_emitido`, H-014) muestra la liquidación emitida, con distribuir y
 * anular. El segmento de la dirección es `AAAA-MM` (`2026-11`); a la API se le
 * pide el día 1 (`2026-11-01`). No escribe nada: abrir la pantalla es sólo mirar.
 */

import { notFound } from "next/navigation";
import { ErrorDePantalla } from "../../../../../componentes/ErrorDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { documentosDeLaLiquidacion } from "../../../../../lib/api/documentos";
import { edificioPorId } from "../../../../../lib/api/edificios";
import {
  liquidacionEmitida,
  liquidacionesDelEdificio,
  preliquidacionDelPeriodo,
} from "../../../../../lib/api/liquidaciones";
import { periodoEnPalabras } from "../../../../../lib/formato";
import { emitirLiquidacionAction } from "./acciones";
import { cargoCobradoDeMenosAction } from "./cargos";
import { anularLiquidacionAction, distribuirLiquidacionAction } from "./ciclo";
import { descargarDocumentoAction, reprocesarDocumentosAction } from "./documentos";
import {
  PantallaLiquidacionEmitida,
  PantallaPreliquidacion,
  PantallaSinPreliquidar,
} from "./Pantalla";

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
  if (preliquidacion.estado === "conflicto" && preliquidacion.motivo === "periodo_emitido") {
    // H-014: el período ya está emitido; en vez de la preliquidación, la liquidación emitida con su
    // estado. La lista viene de la más nueva a la más vieja; una anulada no cuenta (el período
    // vuelve a preliquidarse, así que acá siempre hay una sin anular).
    const lista = await liquidacionesDelEdificio(id);
    if (lista.estado === "sin_sesion") {
      return <Estados tipo="sinSesion" />;
    }
    const vigente =
      lista.estado === "ok"
        ? lista.datos.find((l) => l.periodo === `${periodo}-01` && l.estado !== "anulada")
        : undefined;
    if (vigente !== undefined) {
      const documentos = await documentosDeLaLiquidacion(id, vigente.liquidacion_id);
      if (documentos.estado === "sin_sesion") {
        return <Estados tipo="sinSesion" />;
      }
      // H-017: lo que paga cada unidad, tal como se guardó; si no se puede leer, la pantalla sigue
      // sin la tabla.
      const leida = await liquidacionEmitida(id, vigente.liquidacion_id);
      if (leida.estado === "sin_sesion") {
        return <Estados tipo="sinSesion" />;
      }
      return (
        <PantallaLiquidacionEmitida
          id={id}
          nombreEdificio={nombreEdificio}
          periodoEnPalabras={enPalabras}
          liquidacion={vigente}
          accionDistribuir={distribuirLiquidacionAction.bind(null, id, vigente.liquidacion_id)}
          accionAnular={anularLiquidacionAction.bind(null, id, vigente.liquidacion_id)}
          documentos={documentos.estado === "ok" ? documentos.datos : null}
          accionReprocesar={reprocesarDocumentosAction.bind(null, id, vigente.liquidacion_id)}
          accionDescargar={descargarDocumentoAction.bind(null, id)}
          unidades={leida.estado === "ok" ? leida.datos.unidades : null}
          accionCargo={cargoCobradoDeMenosAction.bind(null, id)}
        />
      );
    }
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
