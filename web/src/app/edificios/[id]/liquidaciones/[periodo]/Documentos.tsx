"use client";

/**
 * Los documentos de una liquidación emitida (change 7, H-015): una fila por unidad y variante con su
 * estado en texto ("Pendiente", "Generado", "Fallido", con el motivo del fallo), "Reprocesar" para
 * los que no se generaron y "Descargar <unidad> · <variante>" para cada uno generado. La pantalla no
 * guarda ni arma el PDF: pide el enlace firmado y lo baja por la ruta de descarga de la web.
 * Reprocesar pide el permiso de emitir; descargar lo decide la API (propietario, inquilino, personal).
 */

import { useActionState, useEffect } from "react";
import { useFormStatus } from "react-dom";
import { Panel } from "../../../../../componentes/Panel";
import { permite, useSesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type {
  DocumentoDeExpensa,
  EstadoDeDocumento,
  VarianteDeDocumento,
} from "../../../../../lib/api/documentos";

/** Lo que devuelve reprocesar: el error ya dicho para la pantalla, o cuántos se encolaron. */
export type EstadoDeReproceso = { error?: string; encolados?: number } | null;

/** Lo que devuelve pedir una descarga: el error, o la ruta de la web que baja el PDF. `pedido` cambia
 * en cada pedido para que dos descargas seguidas del mismo documento sean dos acciones. */
export type EstadoDeDescarga = { error?: string; ruta?: string; pedido?: number } | null;

type AccionReprocesar = (
  estadoPrevio: EstadoDeReproceso,
  formData: FormData,
) => Promise<EstadoDeReproceso>;

type AccionDescargar = (
  estadoPrevio: EstadoDeDescarga,
  formData: FormData,
) => Promise<EstadoDeDescarga>;

const ESTADOS: Record<EstadoDeDocumento, string> = {
  pendiente: "Pendiente",
  generado: "Generado",
  fallido: "Fallido",
};

const VARIANTES: Record<VarianteDeDocumento, string> = {
  completa: "Completa",
  sin_extraordinaria: "Sin extraordinaria",
};

function BotonConEspera({
  texto,
  enCurso,
  clase,
}: {
  texto: string;
  enCurso: string;
  clase: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className={clase} disabled={pending} aria-busy={pending}>
      {pending ? enCurso : texto}
    </button>
  );
}

/** Baja el archivo sin dejar la pantalla: un enlace con `download` y sin pestaña nueva. */
function bajar(ruta: string) {
  const enlace = document.createElement("a");
  enlace.href = ruta;
  enlace.download = "";
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
}

function FilaDeDocumento({
  documento,
  accionDescargar,
}: {
  documento: DocumentoDeExpensa;
  accionDescargar: AccionDescargar;
}) {
  const [estado, descargar] = useActionState(accionDescargar, null);
  const pedido = estado?.pedido;
  const ruta = estado?.ruta;
  useEffect(() => {
    if (pedido !== undefined && ruta !== undefined) {
      bajar(ruta);
    }
  }, [pedido, ruta]);
  return (
    <li>
      <strong>{documento.identificador}</strong> · {VARIANTES[documento.variante]} ·{" "}
      <span>{ESTADOS[documento.estado]}</span>
      {documento.estado === "fallido" && documento.motivo ? (
        <span className="texto-secundario"> ({documento.motivo})</span>
      ) : null}
      {documento.estado === "generado" ? (
        <form action={descargar} className="formulario-en-linea">
          <input type="hidden" name="documento_id" value={documento.documento_id} />
          <input type="hidden" name="variante" value={documento.variante} />
          <BotonConEspera
            clase="boton-secundario"
            texto={`Descargar ${documento.identificador} · ${VARIANTES[documento.variante]}`}
            enCurso="Preparando…"
          />
        </form>
      ) : null}
      {estado?.error ? (
        <p role="alert" className="campo__error">
          {estado.error}
        </p>
      ) : null}
    </li>
  );
}

export function Documentos({
  id,
  documentos,
  accionReprocesar,
  accionDescargar,
}: {
  id: string;
  /** `null` si no se pudieron leer. */
  documentos: DocumentoDeExpensa[] | null;
  accionReprocesar?: AccionReprocesar;
  accionDescargar?: AccionDescargar;
}) {
  const sesion = useSesionDePantalla();
  const puedeReprocesar =
    accionReprocesar !== undefined && permite(sesion, "emitir_y_distribuir_liquidacion", id);
  const [estadoReproceso, reprocesar] = useActionState(
    accionReprocesar ?? (async () => null),
    null,
  );
  const reprocesarBoton = puedeReprocesar ? (
    <form action={reprocesar}>
      <BotonConEspera clase="boton-secundario" texto="Reprocesar" enCurso="Reprocesando…" />
    </form>
  ) : undefined;
  return (
    <Panel
      titulo="Documentos"
      descripcion="El PDF de la expensa de cada unidad. Se genera solo después de emitir y no cambia nunca; se baja con un enlace que vence a los 15 minutos."
      accion={reprocesarBoton}
    >
      {documentos === null ? (
        <p role="status" className="texto-secundario">
          No pudimos cargar los documentos. Volvé a cargar la pantalla.
        </p>
      ) : documentos.length === 0 ? (
        <p className="texto-secundario">Esta liquidación no tiene documentos.</p>
      ) : (
        <ul className="lista-de-filas">
          {documentos.map((documento) => (
            <FilaDeDocumento
              key={documento.documento_id}
              documento={documento}
              accionDescargar={accionDescargar ?? (async () => null)}
            />
          ))}
        </ul>
      )}
      {estadoReproceso?.encolados !== undefined ? (
        <p role="status">
          {estadoReproceso.encolados === 0
            ? "No había documentos para reprocesar."
            : `Se encolaron ${String(estadoReproceso.encolados)} documentos para generarse.`}
        </p>
      ) : null}
      {estadoReproceso?.error ? (
        <p role="alert" className="campo__error">
          {estadoReproceso.error}
        </p>
      ) : null}
    </Panel>
  );
}
